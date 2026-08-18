"""AI-KOS ATQ — Agent Task Queue bridge.

Bridges AI-KOS missions (the knowledge/planning layer) to the Hermes kanban
execution queue (claims, leases, heartbeats, dispatcher, swarm verifier).

Roles in the queue:
  - queue manager (atq-manager profile, local LLM): runs `atq tick` on a cron
    schedule, promotes triage via `hermes kanban decompose`, creates follow-up
    tasks, escalates blocked work, enforces budgets, writes run reports.
  - planner: `hermes kanban decompose` (aux LLM) fans a triage root out into a
    task graph routed to worker profiles.
  - workers (deepseek-pro via kanban dispatch): claim, execute, complete.
  - tester (atq-tester profile): swarm verifier gates completion.

Deterministic by design: this module makes NO LLM calls itself. All judgment
(decompose, follow-up creation) is delegated to kanban's aux-LLM decompose or
to the atq-manager profile session. The tick loop is safe to run from cron.

Usage (CLI):
    ai-kos atq submit <mission-slug> [--board <slug>]
    ai-kos atq tick [--board <slug>] [--max-dispatch 3] [--daily-cap 30]
    ai-kos atq status [--board <slug>]
    ai-kos atq report <mission-slug> [--board <slug>]
    ai-kos atq lanes [--spawn <lane> --cmd "<shell>"]

Or as a module:
    from ai_kos.atq import submit, tick, status, report
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

try:
    import fcntl  # POSIX advisory file locks (Linux/macOS)
except ImportError:  # pragma: no cover — non-POSIX fallback
    fcntl = None

from ai_kos.config import get

logger = logging.getLogger("ai-kos.atq")

STATE_DIR = Path(os.environ.get("ATQ_STATE_DIR", str(Path.home() / ".hermes" / "atq")))

# Defaults (per ATQ autonomy protocol — tune from failure data)
DEFAULT_MAX_DISPATCH = 3          # concurrent workers
DEFAULT_DAILY_CAP = 30            # spawns per mission per day
DEFAULT_MAX_RUNTIME_MINUTES = 120 # 2h wall-clock per task

# Mission root task title prefix — idempotency anchor for submit
ROOT_PREFIX = "[mission] "


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _kanban(cmd_args: List[str], board: Optional[str] = None,
            timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a `hermes kanban ...` command; raise on failure.

    `--board` is a TOP-LEVEL kanban flag: it goes before the subcommand.
    """
    argv = ["hermes", "kanban"]
    if board:
        argv += ["--board", board]
    argv += cmd_args
    logger.debug("running: %s", " ".join(argv))
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            f"kanban {' '.join(cmd_args)} failed ({proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc


def _kanban_json(cmd_args: List[str], board: Optional[str] = None,
                 timeout: int = 120) -> Any:
    proc = _kanban(cmd_args + ["--json"], board=board, timeout=timeout)
    out = proc.stdout.strip()
    if not out:
        return []
    return json.loads(out)


def _state_path(board: str) -> Path:
    return STATE_DIR / f"atq-{board}.json"


def _load_state(board: str) -> dict:
    p = _state_path(board)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"tick_count": 0, "spawns_today": {}, "last_tick": None, "paused": False,
            "needs_human": [], "created_at": _now()}


@contextmanager
def _state_lock(board: str) -> Iterator[None]:
    """Exclusive advisory lock around a state read-modify-write (audit MED).

    Locks a dedicated ``<state>.lock`` file (never the state file itself) so
    the atomic ``os.replace`` of the state file cannot swap the inode out from
    under a concurrent locker. Serializes concurrent ``record_spawn``/``tick``
    writers so spawn counts are never lost to a read-modify-write race. Falls
    back to a no-op on platforms without ``flock`` (the atomic replace still
    prevents torn/corrupt files there).
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = _state_path(board).with_suffix(".lock")
    fh = open(lock_path, "w")
    try:
        if fcntl is not None:
            fcntl.flock(fh, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def _save_state(board: str, state: dict) -> None:
    """Persist state atomically: write a temp file, then ``os.replace``.

    Readers can never observe a torn/partial JSON document (concurrent ticks
    used to corrupt the file via read-modify-write); callers that also mutate
    should hold ``_state_lock`` around the whole read-modify-write.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    p = _state_path(board)
    fd, tmp_name = tempfile.mkstemp(dir=str(STATE_DIR), prefix=p.name + ".",
                                    suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(state, fh, indent=2, default=str)
        os.replace(tmp_name, p)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _day_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _board_flag(board: Optional[str]) -> List[str]:
    return ["--board", board] if board else []


def spawn_gate(board: str = "default", daily_cap: int = DEFAULT_DAILY_CAP) -> tuple:
    """Single gate every spawn path must pass (audit finding #5).

    ``tick``, ``atq_spawn_worker``, ``atq_dispatch`` and
    ``Worker.subdelegate`` all route their spawns through this check so the
    paused kill-switch and the daily spawn cap cannot be bypassed by a direct
    dispatch path. Returns ``(allowed: bool, reason: str)``.
    """
    state = _load_state(board)
    if state.get("paused"):
        return False, "queue paused (kill-switch) — spawn refused"
    day = _day_key()
    used = int(state.get("spawns_today", {}).get(day, 0) or 0)
    if used >= daily_cap:
        return False, f"daily spawn cap reached ({used}/{daily_cap})"
    return True, f"{used}/{daily_cap} spawns used today"


def record_spawn(board: str = "default", n: int = 1) -> None:
    """Account n spawns against the daily cap (persisted in the state file).

    Called by every successful spawn so the cap is enforced across ALL paths,
    not just the tick loop. The read-modify-write runs under ``_state_lock``
    so concurrent ticks cannot lose spawn counts.
    """
    with _state_lock(board):
        state = _load_state(board)
        day = _day_key()
        used = int(state.setdefault("spawns_today", {}).get(day, 0) or 0)
        state["spawns_today"][day] = used + n
        _save_state(board, state)


def ensure_board(board: str, description: str = "") -> None:
    """Create the kanban board if missing (idempotent)."""
    try:
        _kanban(["boards", "create", board, "--description", description])
        logger.info("created board %s", board)
    except RuntimeError as exc:
        if "already exists" in str(exc).lower():
            return
        raise


def _mission_article(slug: str) -> dict:
    """Read an AI-KOS mission article; raise if missing or wrong type.

    Returns frontmatter + body. Mission-specific fields (purpose, success
    criteria, architecture) live in the BODY markdown sections, not the
    frontmatter.
    """
    from ai_kos.articles import read_article

    art = read_article(slug)
    if not art:
        raise ValueError(f"mission article not found: {slug}")
    fm = art.get("frontmatter") or {}
    if fm.get("type") != "mission":
        raise ValueError(f"{slug} is type={fm.get('type')}, expected 'mission'")
    fm["_body"] = art.get("body") or ""
    return fm


def _body_section(body: str, header: str) -> str:
    """Extract a markdown section (## Header) from the body (case-insensitive)."""
    import re as _re

    m = _re.search(rf"^##\s+{_re.escape(header)}\s*$(.*?)(?=^##\s|\Z)", body,
                   _re.MULTILINE | _re.DOTALL | _re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _body_criteria(body: str) -> List[str]:
    """Extract numbered/list items from a markdown section."""
    items = []
    for line in _body_section(body, "Success criteria").splitlines():
        line = line.strip()
        if not line:
            continue
        # strip "1)" / "1." / "- " / "* " prefixes
        import re as _re

        cleaned = _re.sub(r"^(?:\d+[).]|[-*])\s*", "", line)
        if cleaned:
            items.append(cleaned)
    return items


# ── submit ────────────────────────────────────────────────────────────────

def submit(mission_slug: str, board: Optional[str] = None) -> dict:
    """Submit an AI-KOS mission to the execution queue.

    Creates a kanban board (if missing) and one triage root task carrying the
    mission purpose + success criteria. The planner (decompose) fans the root
    out into concrete worker tasks. Idempotent: re-submitting finds the
    existing root task and leaves it alone.
    """
    art = _mission_article(mission_slug)
    board = board or f"mission-{mission_slug}"
    ensure_board(board, description=art.get("title", mission_slug))

    body = art.get("_body") or ""
    criteria = _body_criteria(body)
    purpose = _body_section(body, "Purpose")
    body_parts = [f"# {art.get('title', mission_slug)}",
                  "", "## Purpose", purpose or "(no purpose section)",
                  "", "## Success criteria"]
    for i, c in enumerate(criteria, 1):
        body_parts.append(f"{i}. {c}")
    body = "\n".join(body_parts)

    root_title = ROOT_PREFIX + art.get("title", mission_slug)

    # Idempotency: skip if a root task for this mission already exists
    existing = _kanban_json(["list"], board=board)
    for task in existing:
        if task.get("title") == root_title and task.get("status") != "done":
            return {"status": "exists", "root_id": task["id"], "board": board}

    proc = _kanban(["create", root_title,
                    "--body", body,
                    "--assignee", "atq-manager",
                    "--triage",
                    "--created-by", "atq-submit"], board=board)
    import re as _re
    m = _re.search(r"\b(t_[a-z0-9]+)\b", proc.stdout)
    root_id = m.group(1) if m else "?"
    return {"status": "created", "root_id": root_id, "board": board}


# ── tick ──────────────────────────────────────────────────────────────────

def tick(board: str = "default", max_dispatch: int = DEFAULT_MAX_DISPATCH,
         daily_cap: int = DEFAULT_DAILY_CAP) -> dict:
    """One queue-manager loop iteration (safe to run from cron).

    1. Decompose triage roots (planner fan-out).
    2. Re-dispatch ready tasks (respecting paused state + daily cap).
    3. Collect blocked tasks that need a human.
    4. Persist state (crash-safe: everything else lives in kanban DB).
    """
    state = _load_state(board)
    result: Dict[str, Any] = {"board": board, "decomposed": [], "spawned": 0,
                              "needs_human": [], "paused": state.get("paused", False)}

    tasks = _kanban_json(["list"], board=board)

    # 1) Triage -> decompose (planner). `kanban decompose` exits 0 even on
    #    LLM failure ("malformed JSON") — check stderr so we don't record a
    #    phantom decomposition.
    for task in tasks:
        if task.get("status") == "triage":
            try:
                proc = _kanban(["decompose", task["id"]], board=board, timeout=180)
                err = (proc.stderr or "").strip()
                if err:
                    logger.warning("decompose %s reported: %s", task["id"], err)
                    result.setdefault("decompose_errors", []).append(
                        {"id": task["id"], "error": err})
                else:
                    result["decomposed"].append(task["id"])
            except RuntimeError as exc:
                logger.warning("decompose %s failed: %s", task["id"], exc)
                result.setdefault("decompose_errors", []).append(
                    {"id": task["id"], "error": str(exc)})

    # 2) Blocked -> needs_human (dependency blocks are handled by kanban itself)
    for task in tasks:
        if task.get("status") == "blocked":
            result["needs_human"].append({"id": task["id"], "title": task.get("title")})

    # 3) Budget check before dispatch — through the same gate ALL spawn paths
    #    use (paused kill-switch + daily cap), so direct dispatch cannot
    #    bypass the limits tick enforces.
    allowed, reason = spawn_gate(board, daily_cap=daily_cap)
    if not allowed:
        if state.get("paused"):
            result["paused"] = True
            logger.info("queue paused — no dispatch this tick")
        else:
            logger.info("spawn gate: %s", reason)
    else:
        day = _day_key()
        used = int(state.get("spawns_today", {}).get(day, 0) or 0)
        allowed_n = min(max_dispatch, daily_cap - used)
        try:
            proc = _kanban(["dispatch", "--max", str(allowed_n)], board=board)
            spawned = 0
            for line in proc.stdout.splitlines():
                if line.strip().startswith("Spawned:"):
                    spawned = int(line.split(":")[1].strip() or 0)
            result["spawned"] = spawned
            if spawned:
                record_spawn(board, spawned)
        except RuntimeError as exc:
            logger.warning("dispatch failed: %s", exc)

    # Persist state under the lock, re-loading fresh so a concurrent tick's
    # spawn counts / pause flag are never clobbered by our stale snapshot
    # (audit MED: non-atomic read-modify-write lost spawn counts).
    with _state_lock(board):
        fresh = _load_state(board)
        fresh["tick_count"] = int(fresh.get("tick_count", 0) or 0) + 1
        fresh["last_tick"] = _now()
        fresh["needs_human"] = result["needs_human"]
        _save_state(board, fresh)
    return result


# ── status ────────────────────────────────────────────────────────────────

def status(board: str = "default") -> str:
    """Human-readable queue summary."""
    tasks = _kanban_json(["list"], board=board)
    by_status: Dict[str, int] = {}
    for t in tasks:
        by_status[t.get("status", "?")] = by_status.get(t.get("status", "?"), 0) + 1
    state = _load_state(board)
    lines = [f"ATQ board: {board}", "─" * 40,
             "by status: " + json.dumps(by_status)]
    if state.get("paused"):
        lines.append("PAUSED — no dispatch until unpaused")
    lines.append(f"last tick: {state.get('last_tick', 'never')}  ticks: {state.get('tick_count', 0)}")
    spawns = state.get("spawns_today", {})
    if spawns:
        lines.append("spawns today: " + ", ".join(f"{k}={v}" for k, v in sorted(spawns.items())))
    if state.get("needs_human"):
        lines.append(f"needs human ({len(state['needs_human'])}):")
        for t in state["needs_human"]:
            lines.append(f"  - {t['id']}  {t['title']}")
    return "\n".join(lines)


# ── report ────────────────────────────────────────────────────────────────

def report(mission_slug: str, board: Optional[str] = None) -> str:
    """Write a run report (markdown) for a mission and return its path.

    The report summarizes board state, throughput, and what needs a human.
    Persisting it as an AI-KOS article is the queue manager's job (LLM mode);
    the deterministic part lives here.
    """
    board = board or f"mission-{mission_slug}"
    art = _mission_article(mission_slug)
    tasks = _kanban_json(["list"], board=board)
    by_status: Dict[str, int] = {}
    for t in tasks:
        by_status[t.get("status", "?")] = by_status.get(t.get("status", "?"), 0) + 1

    done = [t for t in tasks if t.get("status") == "done"]
    blocked = [t for t in tasks if t.get("status") == "blocked"]

    lines = [
        f"# ATQ run report — {art.get('title', mission_slug)}",
        "",
        f"Generated: {_now()}  |  board: `{board}`",
        "",
        "## Summary",
        f"- tasks: {len(tasks)}  done: {len(done)}  blocked: {len(blocked)}",
        f"- by status: {json.dumps(by_status)}",
        "",
        "## Done",
    ]
    for t in done:
        lines.append(f"- {t['id']} {t.get('title')}")
    lines += ["", "## Blocked (needs human)", ""]
    for t in blocked:
        lines.append(f"- {t['id']} {t.get('title')}")
    lines += ["", "## Success criteria", ""]
    for i, c in enumerate(_body_criteria(art.get("_body") or ""), 1):
        lines.append(f"{i}. {c}")
    lines += ["", "## Protocol notes",
              "- 24h+ unattended: state is in kanban SQLite + this report; manager crash resumes next tick.",
              "- At-least-once: workers must be idempotent (side-effect log).",
              "- T2 destructive actions park as blocked; nothing auto-destructive ran."]

    out_dir = STATE_DIR / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{mission_slug}-{_now()[:10]}.md"
    path.write_text("\n".join(lines))
    return str(path)


# ── lanes ─────────────────────────────────────────────────────────────────

def lanes(spawn_lane: Optional[str] = None, cmd: Optional[str] = None) -> dict:
    """List registered ATQ worker lanes + statuses, or spawn one on demand.

    With no ``spawn_lane``, returns ``{"lanes": [...], "statuses": [...]}``.
    With ``spawn_lane``, runs ``cmd`` through that lane (the shell lane is the
    default and runs ``bash -c <cmd>``; external CLI lanes receive ``cmd`` as
    a single prompt argument) and returns the LaneResult.

    Safety gate (audit MED): every spawn command is routed through the
    ``classify()`` risk classifier BEFORE execution. A command classified
    >=T2 (irreversible/destructive) is refused — returned as ``gated`` with
    the tier — and never executed, neither via ``bash -c`` nor as a prompt
    that an external agent CLI could act on.
    """
    import dataclasses

    from ai_kos.atq_lanes import (LaneRegistry, LaneSpec, lane_status_all,
                                  register_default_lanes)
    from ai_kos.atq_safety import RiskTier, classify

    registry = LaneRegistry()
    register_default_lanes(registry)
    if spawn_lane:
        if spawn_lane == "shell":
            spec_cmd = ["bash", "-c", cmd or ""]
        else:
            spec_cmd = [cmd or ""]
        tier = classify(cmd or "")
        if tier >= RiskTier.T2_IRREVERSIBLE:
            logger.warning("lanes spawn %s refused: command classified %s",
                           spawn_lane, tier.name)
            return {"lane": spawn_lane, "gated": True, "tier": tier.name,
                    "refused": f"command classified {tier.name} — "
                               f"destructive/irreversible commands are not "
                               f"auto-executed",
                    "cmd": cmd}
        spec = LaneSpec(name=spawn_lane, cmd=spec_cmd)
        result = registry.spawn(spawn_lane, spec)
        return {"lane": spawn_lane, "result": dataclasses.asdict(result)}
    statuses = lane_status_all(registry)
    return {"lanes": registry.list(),
            "statuses": [dataclasses.asdict(s) for s in statuses]}


# ── CLI ───────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="atq", description="AI-KOS Agent Task Queue bridge")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("submit", help="Submit a mission article to the queue")
    ps.add_argument("mission_slug")
    ps.add_argument("--board")

    pt = sub.add_parser("tick", help="One queue-manager loop iteration")
    pt.add_argument("--board", default="default")
    pt.add_argument("--max-dispatch", type=int, default=DEFAULT_MAX_DISPATCH)
    pt.add_argument("--daily-cap", type=int, default=DEFAULT_DAILY_CAP)

    pst = sub.add_parser("status", help="Queue status summary")
    pst.add_argument("--board", default="default")

    pr = sub.add_parser("report", help="Write a run report for a mission")
    pr.add_argument("mission_slug")
    pr.add_argument("--board")

    pl = sub.add_parser("lanes", help="List ATQ worker lanes + statuses, or spawn one")
    pl.add_argument("--spawn", default=None, help="lane to spawn (default: shell)")
    pl.add_argument("--cmd", dest="lane_cmd", default=None,
                    help="shell command / prompt to run via --spawn")

    args = p.parse_args(argv)
    try:
        if args.cmd == "submit":
            print(json.dumps(submit(args.mission_slug, args.board), default=str))
        elif args.cmd == "tick":
            print(json.dumps(tick(args.board, args.max_dispatch, args.daily_cap), default=str))
        elif args.cmd == "status":
            print(status(args.board))
        elif args.cmd == "report":
            print(report(args.mission_slug, args.board))
        elif args.cmd == "lanes":
            print(json.dumps(lanes(args.spawn, args.lane_cmd), default=str))
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
