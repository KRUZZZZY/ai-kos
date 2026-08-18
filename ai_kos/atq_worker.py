"""ATQ reference worker — claim → execute → report → release.

A worker agent's canonical implementation of the ATQ worker protocol (see
``docs/atq-worker-protocol.md``). Can be used as a library (``Worker`` class)
or as a CLI:

    python3 -m ai_kos.atq_worker --board <slug> --task <t_id> --cmd "<shell>"
    python3 -m ai_kos.atq_worker --board <slug> --task <t_id> \
        --subdelegate "Title|Body|profile" --subdelegate "..."

Sub-delegation: each ``--subdelegate`` creates a child card via the kanban CLI
and dispatches it (the same mechanics the atq-director MCP tool exposes), then
the worker aggregates every child's completion result before releasing the
parent. This is the concrete "direct agents" mechanism a queue-manager agent
gets via the atq-director MCP server.

Protocol guarantees enforced here:
- artifact naming ``<task_id>-<artifact>.<ext>`` (no-clobber convention)
- side-effect log before side effects (idempotency)
- T0/T1 auto-act; T2 escalates to block instead of executing
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from ai_kos.atq import record_spawn, spawn_gate
from ai_kos.atq_ralph import RalphReport
from ai_kos.atq_safety import RiskTier, classify

TASK_ID_RE = re.compile(r"\b(t_[a-z0-9]+)\b")


def _run(cmd: list[str], timeout: int = 120) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": f"timed out after {timeout}s"}
    return {"exit_code": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def _kanban(board: str, sub: str, *args: str, timeout: int = 120) -> dict:
    """hermes kanban --board <slug> <sub> [args...] — board is a TOP-LEVEL flag."""
    return _run(["hermes", "kanban", "--board", board, sub, *args], timeout=timeout)


def _task_id(text: str) -> str | None:
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("id"):
            return str(data["id"])
    except (json.JSONDecodeError, AttributeError):
        pass
    m = TASK_ID_RE.search(text)
    return m.group(1) if m else None


class Worker:
    """Reference ATQ worker bound to one claimed kanban card."""

    def __init__(self, task_id: str, board: str = "default",
                 workdir: Path | None = None, author: str = "atq-worker"):
        self.task_id = task_id
        self.board = board
        self.workdir = workdir or Path.cwd()
        self.author = author
        self.side_effect_log: list[dict] = []
        # Persisted side-effect log (audit finding: in-memory only). Task-
        # scoped file in the claim workspace, so a crash + re-claim skips
        # already-applied effects instead of re-running them.
        self._effects_path = self.workdir / f"{self.task_id}-side-effects.json"
        self._load_effects()

    # ── protocol steps ────────────────────────────────────────────────────

    def claim(self, ttl: int = 3600) -> bool:
        """ready → running with an exclusive lock (the claim IS the lock).

        Returns True only when the claim was actually acquired. A lost claim
        race (already claimed by another worker) or a non-claimable card
        leaves ``self.claimed`` False and the worker MUST NOT execute — run()
        refuses without it.
        """
        r = _kanban(self.board, "claim", "--ttl", str(ttl), self.task_id)
        combined = (r["stdout"] + "\n" + r["stderr"]).lower()
        self.claimed = r["exit_code"] == 0 and "cannot claim" not in combined
        return self.claimed

    def heartbeat(self) -> bool:
        """Extend the lease. False when the run/lease is no longer ours."""
        r = _kanban(self.board, "heartbeat", self.task_id)
        combined = (r["stdout"] + "\n" + r["stderr"]).lower()
        return r["exit_code"] == 0 and "cannot" not in combined

    def comment(self, body: str) -> str:
        return _kanban(self.board, "comment", "--author", self.author,
                       self.task_id, body)["stdout"]

    def complete(self, result: str) -> str:
        self._log_effect("complete", result)
        return _kanban(self.board, "complete", self.task_id, result)["stdout"]

    def block(self, reason: str) -> str:
        """T2 escalation: park the card, never execute destructive actions."""
        self._log_effect("block", reason)
        return _kanban(self.board, "block", self.task_id, reason)["stdout"]

    # ── artifact + idempotency helpers ────────────────────────────────────

    def artifact_path(self, name: str) -> Path:
        """No-clobber artifact naming: <task_id>-<name> in the claim workspace."""
        p = self.workdir / f"{self.task_id}-{name}"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def write_artifact(self, name: str, content: str) -> Path:
        p = self.artifact_path(name)
        p.write_text(content)
        self._log_effect("write_artifact", str(p))
        return p

    def _log_effect(self, kind: str, detail: str) -> None:
        self.side_effect_log.append({"kind": kind, "detail": detail, "at": time.time()})
        self._persist_effects()

    def _load_effects(self) -> None:
        """Restore the persisted side-effect log (crash/retry idempotency)."""
        try:
            if self._effects_path.exists():
                data = json.loads(self._effects_path.read_text())
                if isinstance(data, list):
                    self.side_effect_log = [e for e in data if isinstance(e, dict)]
        except (json.JSONDecodeError, OSError):
            self.side_effect_log = []

    def _persist_effects(self) -> None:
        """Write the side-effect log to the claim workspace (task-scoped,
        no-clobber naming) so a re-claimed/re-dispatched task skips effects
        already applied. Best-effort: persistence must never break the worker."""
        try:
            self.workdir.mkdir(parents=True, exist_ok=True)
            self._effects_path.write_text(json.dumps(self.side_effect_log, default=str))
        except OSError:
            pass

    def already_applied(self, kind: str, detail: str) -> bool:
        """Idempotency check: skip side effects already applied on a retry."""
        return any(e["kind"] == kind and e["detail"] == detail for e in self.side_effect_log)

    # ── sub-delegation ────────────────────────────────────────────────────

    def subdelegate(self, title: str, body: str, assignee: str,
                    parent: str | None = None) -> str | None:
        """Create + dispatch a child card for another worker (profile).

        Mirrors the atq-director MCP tool atq_spawn_worker. Returns the child
        task id, or None on failure. Refuses (no card created) when the spawn
        gate is closed — paused kill-switch or daily cap (audit finding #5).
        """
        allowed, reason = spawn_gate(self.board)
        if not allowed:
            self.comment(f"subdelegate refused: {reason}")
            return None
        args = ["--body", body, "--assignee", assignee]
        if parent:
            args += ["--parent", parent]
        r = _kanban(self.board, "create", "--json", *args, title, timeout=180)
        if r["exit_code"] != 0:
            self.comment(f"subdelegate failed: {r['stderr'] or r['stdout']}")
            return None
        child_id = _task_id(r["stdout"])
        if not child_id:
            return None
        # --max is a live concurrency cap (running + spawns) — use 2 so the
        # new card can spawn even with one card already running on the board.
        disp = _kanban(self.board, "dispatch", "--max", "2", "--json", timeout=180)
        if disp["exit_code"] == 0:
            record_spawn(self.board)
        self.comment(f"subdelegated -> {child_id} (assignee={assignee})\ndispatch: "
                     f"{disp['stdout'][:200] or disp['stderr'][:200]}")
        self._log_effect("subdelegate", child_id)
        return child_id

    def aggregate(self, child_ids: list[str], poll_seconds: int = 15,
                  max_wait_seconds: int = 600) -> list[dict]:
        """Poll children until done/blocked, collect their result summaries.

        Status is parsed from the card's ``status:`` field — never substring
        matched against the body (a running card whose body mentions the word
        "blocked" must not be misclassified).
        """
        status_re = re.compile(r"status:\s+([a-z-]+)", re.I)
        results = []
        deadline = time.time() + max_wait_seconds
        pending = list(child_ids)
        while pending and time.time() < deadline:
            # Heartbeat each poll iteration (audit finding #7): aggregation is
            # the longest-running phase; without a lease keep-alive a slow
            # aggregate is reclaimed and the parent re-dispatched (double-run).
            if not self.heartbeat():
                break  # lease lost — stop polling; caller sees pending as timeout
            for cid in list(pending):
                r = _kanban(self.board, "show", cid)
                text = r["stdout"]
                m = status_re.search(text)
                status = m.group(1).lower() if m else "running"
                if status == "done":
                    results.append({"child": cid, "status": "done", "detail": text[-400:]})
                    pending.remove(cid)
                elif status == "blocked":
                    results.append({"child": cid, "status": "blocked", "detail": text[-400:]})
                    pending.remove(cid)
            if pending:
                time.sleep(poll_seconds)
        for cid in pending:
            results.append({"child": cid, "status": "timeout"})
        return results

    # ── Ralph envelope ────────────────────────────────────────────────────

    def complete_report(self, report: RalphReport) -> str:
        """Persist a Ralph report artifact, then complete() with a rendered summary.

        Writes ``<task_id>-report.json`` (the ``RalphReport`` envelope) and
        calls ``complete()`` with ``status + summary + evidence[:300]``.
        """
        self.write_artifact("report.json", report.to_json())
        rendered = f"[{report.status}] {report.summary}"
        if report.evidence:
            rendered += f" — {report.evidence[:300]}"
        return self.complete(rendered)

    def block_report(self, report: RalphReport) -> str:
        """Persist a Ralph report artifact, then block() with a rendered summary."""
        self.write_artifact("report.json", report.to_json())
        rendered = f"[{report.status}] {report.summary}"
        if report.evidence:
            rendered += f" — {report.evidence[:300]}"
        return self.block(rendered)

    def read_child_report(self, child_id: str) -> RalphReport | None:
        """Read a child's ``<child_id>-report.json`` from the workspace."""
        p = self.workdir / f"{child_id}-report.json"
        if not p.exists():
            return None
        try:
            return RalphReport.from_json(p.read_text())
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def ralph_spawn(self, title: str, objective: str, handoff: str,
                    assignee: str, parent: str | None = None) -> str | None:
        """Subdelegate one Ralph round, embedding the handoff in the child body.

        Thin wrapper over ``subdelegate()``: the child receives the immutable
        objective + per-round handoff as its body and is expected to report
        via ``complete_report()``/``block_report()`` (which writes
        ``<child_id>-report.json``). The child's report is read back
        best-effort — the child may still be running at this point.
        """
        body = (f"Objective: {objective}\n\n{handoff}\n\n"
                "Report your outcome via the Ralph envelope "
                "(complete_report / block_report).")
        child_id = self.subdelegate(title, body, assignee, parent=parent)
        if not child_id:
            return None
        report = self.read_child_report(child_id)
        if report is not None:
            self.comment(f"child {child_id} report: [{report.status}] {report.summary}")
        return child_id

    # ── runner ────────────────────────────────────────────────────────────

    def run(self, cmd: str | None = None,
            subdelegates: list[tuple[str, str, str]] | None = None) -> int:
        """Full protocol run. Returns 0 on success, 1 on failure/block."""
        if not getattr(self, "claimed", False):
            self.block("refusing to execute without a successful claim (the claim IS the lock)")
            return 1
        self.comment("worker start (claim held)")
        # Audit invariant (model-visible ⟺ logged): record the objective handed
        # to this worker so every model-visible input is reconstructable.
        try:
            from ai_kos.audit import log_model_visible
            log_model_visible(
                source="atq-worker",
                content=cmd or f"subdelegates={json.dumps(subdelegates or [])}",
                meta={"task_id": self.task_id,
                      "lane": "shell" if cmd else "subdelegate"},
            )
        except Exception:  # noqa: BLE001 — audit must never break the worker
            pass
        # Heartbeat at run start (audit finding #7): long-running work must
        # keep the lease alive or it is reclaimed and re-dispatched (double
        # execution). A failed heartbeat means the lease is no longer ours —
        # abort rather than clobber the run that took over.
        if not self.heartbeat():
            self.block("lease lost at run start — aborting to avoid double-run")
            return 1
        if cmd:
            if self.already_applied("execute", cmd):
                self.comment("skipping already-applied execute (idempotent retry)")
            else:
                tier = classify(cmd)
                if tier >= RiskTier.T2_IRREVERSIBLE:
                    # Least-risk gate: never execute irreversible/destructive
                    # commands — park the card and escalate instead.
                    self.block(f"refusing T{tier.value} command (least-risk gate): {cmd[:120]}")
                    return 1
                if not self.heartbeat():
                    self.block("lease lost before execute — aborting to avoid double-run")
                    return 1
                out = _run(["bash", "-c", cmd], timeout=600)
                if not self.heartbeat():
                    self.block("lease lost after execute — aborting")
                    return 1
                evidence = self.write_artifact("output.txt", out["stdout"][:2000])
                self.comment(f"executed: {cmd}\nexit={out['exit_code']}\nevidence: {evidence}")
                if out["exit_code"] != 0:
                    self.block(f"command failed (exit={out['exit_code']}): {out['stderr'][:300]}")
                    return 1
                # Idempotency (audit finding: decorative log): record the
                # executed command so a re-claimed/re-dispatched task does not
                # re-run an already-applied side effect.
                self._log_effect("execute", cmd)
        children = []
        for title, body, assignee in (subdelegates or []):
            cid = self.subdelegate(title, body, assignee, parent=self.task_id)
            if cid:
                children.append(cid)
        if children:
            results = self.aggregate(children)
            summary = json.dumps(results, indent=2, default=str)
            self.write_artifact("aggregation.json", summary)
            self.comment(f"aggregated {len(results)} children:\n{summary[:1500]}")
            if any(r["status"] != "done" for r in results):
                self.block("sub-delegates not all done")
                return 1
        self.complete(f"done: cmd={cmd!r} children={children}")
        return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ai_kos.atq_worker", description=__doc__)
    p.add_argument("--board", default="default")
    p.add_argument("--task", required=True)
    p.add_argument("--cmd", default=None, help="shell command to execute as the task")
    p.add_argument("--subdelegate", action="append", default=[],
                   help="'Title|Body|assignee' — repeatable; creates+dispatches a child card")
    p.add_argument("--workdir", default=None, help="claim workspace (default: cwd)")
    args = p.parse_args(argv)

    workdir = Path(args.workdir) if args.workdir else Path.cwd()
    w = Worker(args.task, board=args.board, workdir=workdir)
    subs = []
    for spec in args.subdelegate:
        parts = [s.strip() for s in spec.split("|")]
        if len(parts) == 3:
            subs.append((parts[0], parts[1], parts[2]))
        else:
            print(f"bad --subdelegate spec (need Title|Body|assignee): {spec!r}", file=sys.stderr)
            return 2
    print(w.claim())
    if not w.claimed:
        print(f"cannot claim {args.task} — aborting (card not claimable or already claimed)",
              file=sys.stderr)
        return 1
    return w.run(cmd=args.cmd, subdelegates=subs)


if __name__ == "__main__":
    sys.exit(main())
