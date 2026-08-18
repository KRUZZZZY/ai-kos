"""ATQ safety escalation + least-risk enforcement layer.

Implements the safety half of the ATQ worker protocol (docs/atq-worker-
protocol.md, P1/P2): every action is classified T0–T3, agents default to the
least-risky action, and irreversible/destructive attempts are BLOCKED and
ESCALATED — the queue pauses and raises an alert instead of executing
silently. Human questions are capped per run (configurable, default 3); when
the cap is exceeded the queue pauses and alerts.

Usage (library):

    from ai_kos.atq_safety import SafetyGuard, RiskTier

    guard = SafetyGuard(question_threshold=3)
    tier, allowed, reason = guard.check("rm -rf /tmp/x")   # (T2, False, ...)
    guard.check("echo hi")                                  # (T0, True, ...)
    guard.request_escalation("rm -rf /tmp/x", question=...,
                             candidates=[...], recommended=...)
    guard.paused  # True once the threshold is exceeded
    guard.resume()  # after human intervention

The queue manager hook ``handle_escalation`` implements the default-and-
escalate rule: approve when the recommended action is T0/T1-compatible,
otherwise park as blocked.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Optional


class RiskTier(IntEnum):
    """Least-risk classification (P1). Higher = riskier."""

    T0_READ_ONLY = 0      # read file, list, search, GET
    T1_REVERSIBLE = 1     # workspace edit, comment, create/dispatch cards, tests
    T2_IRREVERSIBLE = 2   # rm -rf, DROP/TRUNCATE, force-push, prod mutation
    T3_HARD_STOP = 3      # budget cap, sandbox escape — runtime refuses


# Action-pattern -> tier. Anything not matched defaults to T1_REVERSIBLE
# (conservative for agent work; the runtime still enforces its own gates).
_PATTERNS: list[tuple[re.Pattern, RiskTier]] = [
    # T3: absolute stops (never allowed, regardless of human)
    (re.compile(r"\b(sudo\s+rm\s+-rf\s*/\s*$|mkfs\.|dd\s+if=.*\s+of=/dev/|:\\(\\)\s*\\{\\s*:\\|:&\\}\\s*;)"), RiskTier.T3_HARD_STOP),
    # T2: irreversible / destructive
    (re.compile(r"\brm\s+-rf\b"), RiskTier.T2_IRREVERSIBLE),
    (re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", re.I), RiskTier.T2_IRREVERSIBLE),
    (re.compile(r"\bTRUNCATE\b", re.I), RiskTier.T2_IRREVERSIBLE),
    (re.compile(r"\bgit\s+push\s+(-f|--force)\b"), RiskTier.T2_IRREVERSIBLE),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), RiskTier.T2_IRREVERSIBLE),
    (re.compile(r"\bDELETE\s+FROM\b", re.I), RiskTier.T2_IRREVERSIBLE),
    (re.compile(r"\b(?:rm|unlink)\s+-[a-z]*[rf]", re.I), RiskTier.T2_IRREVERSIBLE),
    (re.compile(r"\bchmod\s+[0-7]{3}\s+/(?:etc|usr|bin|boot)"), RiskTier.T2_IRREVERSIBLE),
    # T0: read-only
    (re.compile(r"^(?:cat|ls|grep|rg|find|diff|git\s+status|git\s+log|head|tail|wc|ps|stat)\b"), RiskTier.T0_READ_ONLY),
]

# Destructive-pattern denylist — audit finding #4 (consensus): the generic
# rules let `find … -delete` ride the read-only T0 allowlist, and
# `rm --recursive --force`, `rmdir -p`, `shred -u`, `git push origin main
# --force` (flag after refspec) fell through to T1 auto-act. Anything that
# deletes / overwrites / force-pushes must NEVER be T0/T1 — these patterns
# are checked BEFORE the generic rules and promote to T2 (park-for-review).
# Deliberately conservative: an over-blocked action parks for a human, an
# under-blocked destructive action runs unattended.
_DESTRUCTIVE_PATTERNS: list[tuple[re.Pattern, RiskTier]] = [
    # find with -delete / -exec / -execdir / -ok / -okdir executes side
    # effects — must never ride the read-only `find` allowlist.
    (re.compile(r"(?:^|[;&|\n]\s*)find\b[^\n;|]*\s-(?:delete|exec|execdir|ok|okdir)\b"),
     RiskTier.T2_IRREVERSIBLE),
    # rm long-form recursive/force flags (rm --recursive --force, rm -rf
    # --force, rm --dir …); short-flag forms are caught by the generic rule.
    (re.compile(r"\brm\b[^\n;|]*\s--(?:recursive|force|dir)\b"),
     RiskTier.T2_IRREVERSIBLE),
    # rmdir removes directories (with -p/--parents, parents too).
    (re.compile(r"\brmdir\b(?:[^\n;|]*\s(?:-p|--parents)\b)?"),
     RiskTier.T2_IRREVERSIBLE),
    # shred overwrites file contents irreversibly (even without -u/--remove).
    (re.compile(r"\bshred\b"), RiskTier.T2_IRREVERSIBLE),
    # git push with any force flag, anywhere in the command
    # (git push origin main --force, git push -f, GIT PUSH -F …).
    (re.compile(r"\bgit\s+push\b[^\n;|]*\s(?:--force(?:-with-lease)?|-f)\b", re.I),
     RiskTier.T2_IRREVERSIBLE),
    # python one-liners that delete trees/files.
    (re.compile(r"\bpython3?\b[\s\S]{0,300}?\bshutil\.rmtree\s*\("),
     RiskTier.T2_IRREVERSIBLE),
    (re.compile(r"\bpython3?\b[\s\S]{0,300}?\bos\.(?:remove|unlink|rmdir)\s*\("),
     RiskTier.T2_IRREVERSIBLE),
]


def classify(action: str, explicit_tier: Optional[RiskTier] = None) -> RiskTier:
    """Classify an action string into a risk tier.

    An explicit tier (agent-declared) wins; otherwise the action is matched
    against known dangerous/read-only patterns and defaults to T1. T3
    absolute stops are checked first, then the destructive denylist (so a
    deletes/overwrites/force-push action is promoted to ≥T2 even when a
    generic read-only allowlist pattern like ``find`` would otherwise match),
    then the remaining generic rules.
    """
    if explicit_tier is not None:
        return RiskTier(explicit_tier)
    for pattern, tier in _PATTERNS:
        if tier == RiskTier.T3_HARD_STOP and pattern.search(action):
            return tier
    for pattern, tier in _DESTRUCTIVE_PATTERNS:
        if pattern.search(action):
            return tier
    for pattern, tier in _PATTERNS:
        if pattern.search(action):
            return tier
    return RiskTier.T1_REVERSIBLE


@dataclass
class Escalation:
    """A single escalation record (P2/P6 format)."""

    action: str
    question: str
    candidates: list[str] = field(default_factory=list)
    recommended: str = ""
    created_at: float = field(default_factory=time.time)
    approved: Optional[bool] = None  # None=pending, True=approved, False=rejected


@dataclass
class SafetyGuard:
    """Enforces least-risk; blocks + escalates irreversible actions.

    State machine: running -> paused (on T2 escalation or question-threshold
    breach) -> running (after ``resume()``, i.e. human intervention).
    """

    question_threshold: int = 3
    max_actions: int = 20          # P3 step cap — 21st action hard-stops
    alerts: list[dict] = field(default_factory=list)
    escalations: list[Escalation] = field(default_factory=list)
    paused: bool = False
    _action_count: int = 0

    # ── core check ────────────────────────────────────────────────────────

    def check(self, action: str, explicit_tier: Optional[RiskTier] = None):
        """Gate an action. Returns (tier, allowed, reason).

        - T0/T1: allowed (auto-act). T1 still logs the action.
        - T2: blocked; escalation raised; queue pauses on the FIRST T2.
        - T3: hard-stop; queue pauses; alert raised; never allowed.
        - Over the step cap (max_actions): hard-stop.
        """
        self._action_count += 1
        tier = classify(action, explicit_tier)

        if self._action_count > self.max_actions:
            self.paused = True
            self.alerts.append({"kind": "step_cap", "action": action,
                                "count": self._action_count})
            return RiskTier.T3_HARD_STOP, False, f"step cap {self.max_actions} exceeded"

        if tier == RiskTier.T3_HARD_STOP:
            self.paused = True
            self.alerts.append({"kind": "hard_stop", "action": action, "tier": "T3"})
            return tier, False, "hard-stop: runtime refuses"

        if tier == RiskTier.T2_IRREVERSIBLE:
            esc = self.request_escalation(
                action,
                question=f"Action is irreversible (T2): {action!r}. Approve?",
                recommended="Do NOT execute; park the task as blocked instead.",
            )
            self.paused = True
            self.alerts.append({"kind": "destructive_attempt", "action": action,
                                "escalation": len(self.escalations)})
            return tier, False, f"blocked (T2) -> escalation {len(self.escalations)}"

        return tier, True, "auto-act (least-risk)"

    # ── escalation hooks ──────────────────────────────────────────────────

    def request_escalation(self, action: str, question: str,
                           candidates: Optional[list[str]] = None,
                           recommended: str = "") -> Escalation:
        """Agent hook to request escalation (P2). Pauses when over threshold."""
        esc = Escalation(action=action, question=question,
                         candidates=list(candidates or []),
                         recommended=recommended)
        self.escalations.append(esc)
        if len(self.escalations) > self.question_threshold:
            self.paused = True
            self.alerts.append({
                "kind": "question_threshold",
                "count": len(self.escalations),
                "threshold": self.question_threshold,
            })
        return esc

    def handle_escalation(self, escalation: Escalation) -> bool:
        """Queue-manager hook (default-and-escalate): approve the recommended
        default when it is T0/T1-compatible, otherwise park (reject)."""
        recommended_tier = classify(escalation.recommended)
        approved = recommended_tier <= RiskTier.T1_REVERSIBLE
        escalation.approved = approved
        if not approved:
            self.alerts.append({"kind": "parked", "action": escalation.action})
        return approved

    def resume(self) -> None:
        """Human intervention: unpause and reset the per-run question budget."""
        self.paused = False
        self.escalations.clear()

    def status(self) -> dict:
        return {
            "paused": self.paused,
            "escalations": len(self.escalations),
            "alerts": len(self.alerts),
            "actions_taken": self._action_count,
            "threshold": self.question_threshold,
        }
