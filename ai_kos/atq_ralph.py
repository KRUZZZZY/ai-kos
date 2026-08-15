"""Ralph report envelope — one objective → a sequence of fresh children.

Mirrors DeepSeek Harness ``tool-ralph``: a single **immutable** objective is
handed to a *fresh* child each round, with a structured report (the "envelope")
carrying status + summary + evidence + next steps + blockers as the only
handoff between rounds. The parent conversation is **never** seeded into a
child — each round starts from the objective + the previous report only.

Deterministic helpers live here; the actual child spawn is the caller's (a
kanban ``subdelegate`` or an ATQ lane). ``validate_ralph_report`` enforces the
dsh invariant that *invalid, missing, or oversized reports fail the workflow
instead of being truncated*.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger("ai-kos.atq_ralph")

RALPH_STATUSES = ("continue", "complete", "blocked")


class RalphError(Exception):
    """Invalid, missing, or oversized Ralph report."""


class RalphBudgetError(RalphError):
    """The round budget was exceeded while the objective was still running."""


@dataclass
class RalphReport:
    """The per-round envelope a child returns to its parent."""

    status: str  # one of RALPH_STATUSES
    summary: str
    evidence: str = ""
    next_steps: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, payload: str) -> "RalphReport":
        data = json.loads(payload)
        return cls(**data)


def validate_ralph_report(data: dict, max_handoff_chars: int = 20000) -> RalphReport:
    """Validate and normalize a Ralph report dict into a RalphReport.

    Raises ``RalphError`` on: unknown status, missing/empty summary,
    non-list ``next_steps``/``blockers``, or an oversized serialized
    report (over ``max_handoff_chars``). Never truncates — it fails instead.
    """
    if not isinstance(data, dict):
        raise RalphError("report must be a dict")
    status = data.get("status")
    if status not in RALPH_STATUSES:
        raise RalphError(f"unknown status: {status!r}")
    summary = data.get("summary")
    if not summary or not str(summary).strip():
        raise RalphError("summary is required and must be non-empty")
    next_steps = data.get("next_steps", [])
    blockers = data.get("blockers", [])
    if not isinstance(next_steps, list):
        raise RalphError("next_steps must be a list")
    if not isinstance(blockers, list):
        raise RalphError("blockers must be a list")

    report = RalphReport(
        status=str(status),
        summary=str(summary),
        evidence=str(data.get("evidence") or ""),
        next_steps=[str(s) for s in next_steps],
        blockers=[str(s) for s in blockers],
    )
    serialized = report.to_json()
    if len(serialized) > max_handoff_chars:
        raise RalphError(
            f"report too large ({len(serialized)} chars > {max_handoff_chars})"
        )
    return report


def ralph_handoff(objective: str, round_no: int, max_rounds: int,
                  workspace: str, previous: RalphReport | None = None) -> str:
    """Build the immutable per-round prompt handed to the next child.

    Contains only: the objective, the round number/cap, the workspace-as-
    authority instruction, and the serialized previous report (or a "no
    previous round" marker). The parent conversation is intentionally never
    included — each child is fresh.
    """
    lines = [
        "# Ralph round",
        "",
        f"Objective: {objective}",
        "",
        f"Round: {round_no} / {max_rounds}",
        "",
        f"Workspace: {workspace}",
        "",
        "You are the authoritative worker for this workspace. Operate only "
        "within the workspace, and report your outcome through the Ralph "
        "report envelope (status: continue | complete | blocked).",
    ]
    if previous is None:
        lines += ["", "Previous round: no previous round"]
    else:
        lines += ["", "Previous round report:", previous.to_json()]
    return "\n".join(lines)


class RalphLoop:
    """A bounded sequence of Ralph rounds over one immutable objective."""

    def __init__(self, objective: str, max_rounds: int = 256,
                 workspace: Path | str | None = None) -> None:
        self.objective = objective
        self.max_rounds = max_rounds
        self.workspace = Path(workspace) if workspace is not None else Path.cwd()
        self.round = 0
        self.report: RalphReport | None = None
        self.budget_limited = False

    def next_round(self) -> str:
        """Advance the round counter and return the handoff for that round.

        Raises ``RalphBudgetError`` when the round cap is reached/exceeded.
        """
        if self.round >= self.max_rounds:
            self.budget_limited = True
            raise RalphBudgetError(f"round budget exceeded ({self.max_rounds} rounds)")
        self.round += 1
        return ralph_handoff(self.objective, self.round, self.max_rounds,
                             str(self.workspace), self.report)

    def feed(self, report: RalphReport) -> str:
        """Record a child's report; return the next handoff or a terminal reason.

        ``complete``/``blocked`` end the loop and return a terminal reason.
        ``continue`` advances to the next round and returns its handoff; if
        the cap is hit while still continuing, ``budget_limited`` is set and a
        budget-limited reason is returned instead of raising.
        """
        self.report = report
        if report.status == "complete":
            return f"complete: {report.summary}"
        if report.status == "blocked":
            return f"blocked: {report.summary}"
        try:
            return self.next_round()
        except RalphBudgetError:
            self.budget_limited = True
            return f"budget_limited: {report.summary}"

    def run_once(self, spawn_fn) -> dict:
        """Run one round: build handoff → spawn → validate → advance.

        ``spawn_fn(objective, handoff)`` returns a ``RalphReport`` or a dict
        (dicts are validated via ``validate_ralph_report``).
        """
        handoff = self.next_round()
        raw = spawn_fn(self.objective, handoff)
        if isinstance(raw, RalphReport):
            report = raw
        else:
            report = validate_ralph_report(raw)
        self.report = report
        return {"round": self.round, "handoff": handoff,
                "report": report, "status": report.status}


__all__ = [
    "RALPH_STATUSES",
    "RalphError",
    "RalphBudgetError",
    "RalphReport",
    "RalphLoop",
    "validate_ralph_report",
    "ralph_handoff",
]
