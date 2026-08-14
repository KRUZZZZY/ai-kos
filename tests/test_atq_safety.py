"""Tests for ai_kos.atq_safety — least-risk enforcement + escalation.

Covers the safety card's acceptance criteria:
- unit: destructive actions are blocked and the queue pauses
- integration-style: a simulated worker's destructive attempt pauses the
  queue and raises an alert; human resume() lets safe work continue
- question-threshold breach pauses and alerts
"""

import pytest

from ai_kos.atq_safety import SafetyGuard, RiskTier, classify


# ── classification ───────────────────────────────────────────────────────

def test_classify_known_tiers():
    assert classify("cat file.txt") == RiskTier.T0_READ_ONLY
    assert classify("git status") == RiskTier.T0_READ_ONLY
    assert classify("echo hi > workspace/out.txt") == RiskTier.T1_REVERSIBLE
    assert classify("rm -rf /tmp/x") == RiskTier.T2_IRREVERSIBLE
    assert classify("DROP TABLE users") == RiskTier.T2_IRREVERSIBLE
    assert classify("git push --force origin main") == RiskTier.T2_IRREVERSIBLE
    assert classify("sudo rm -rf /") == RiskTier.T3_HARD_STOP


def test_classify_explicit_tier_wins():
    assert classify("echo hi", explicit_tier=RiskTier.T2_IRREVERSIBLE) == RiskTier.T2_IRREVERSIBLE


# ── unit: destructive blocked + queue pauses ─────────────────────────────

def test_t0_t1_actions_auto_act():
    g = SafetyGuard()
    tier, allowed, reason = g.check("cat file.txt")
    assert tier == RiskTier.T0_READ_ONLY and allowed
    tier, allowed, _ = g.check("echo hi")
    assert tier == RiskTier.T1_REVERSIBLE and allowed
    assert not g.paused


def test_destructive_action_blocked_and_pauses():
    g = SafetyGuard()
    tier, allowed, reason = g.check("rm -rf /tmp/x")
    assert tier == RiskTier.T2_IRREVERSIBLE
    assert not allowed
    assert g.paused, "queue must pause on a destructive attempt"
    assert "blocked" in reason
    assert len(g.escalations) == 1


def test_hard_stop_never_allowed():
    g = SafetyGuard()
    tier, allowed, _ = g.check("sudo rm -rf /")
    assert tier == RiskTier.T3_HARD_STOP
    assert not allowed
    assert g.paused
    assert any(a["kind"] == "hard_stop" for a in g.alerts)


def test_step_cap_hard_stops():
    g = SafetyGuard(max_actions=3)
    for _ in range(3):
        g.check("echo ok")
    tier, allowed, reason = g.check("echo one-more")
    assert tier == RiskTier.T3_HARD_STOP and not allowed
    assert "step cap" in reason


# ── question threshold ───────────────────────────────────────────────────

def test_question_threshold_breach_pauses_and_alerts():
    g = SafetyGuard(question_threshold=3)
    for i in range(3):
        g.request_escalation(f"act{i}", "question?")
        assert not g.paused  # at threshold: still running
    g.request_escalation("act4", "question?")
    assert g.paused
    assert any(a["kind"] == "question_threshold" for a in g.alerts)


# ── queue-manager hook: default-and-escalate ─────────────────────────────

def test_handle_escalation_approves_t1_default():
    g = SafetyGuard()
    esc = g.request_escalation("weird", "Approve?", recommended="comment and park")
    assert g.handle_escalation(esc) is True
    assert esc.approved is True


def test_handle_escalation_parks_t2_recommendation():
    g = SafetyGuard()
    esc = g.request_escalation("weird", "Approve?", recommended="rm -rf /tmp/x")
    assert g.handle_escalation(esc) is False
    assert esc.approved is False
    assert any(a["kind"] == "parked" for a in g.alerts)


# ── resume after human intervention ──────────────────────────────────────

def test_resume_after_human_intervention():
    g = SafetyGuard()
    g.check("rm -rf /tmp/x")          # pauses
    assert g.paused
    g.resume()                        # human clears it
    assert not g.paused
    tier, allowed, _ = g.check("echo safe-again")
    assert allowed                     # safe work continues
    assert len(g.escalations) == 0     # per-run budget reset


# ── integration-style: simulated worker ──────────────────────────────────

def test_worker_destructive_attempt_pauses_queue_and_alerts():
    """A worker that attempts a destructive action gets blocked; the queue
    pauses and an alert is raised; after resume the worker's safe steps run."""
    guard = SafetyGuard(question_threshold=3)
    worker_steps = ["echo start", "read config", "rm -rf /data/prod", "echo done"]

    results = []
    for step in worker_steps:
        tier, allowed, reason = guard.check(step)
        if allowed:
            results.append(("executed", step, tier))
        else:
            results.append(("blocked", step, reason))
            break

    assert results[-1][0] == "blocked"
    assert "rm -rf" in results[-1][1]
    assert guard.paused
    assert len(guard.alerts) >= 1, "an alert must be raised"

    # human intervention -> queue resumes, remaining safe steps proceed
    guard.resume()
    tier, allowed, _ = guard.check("echo done")
    assert allowed
    assert guard.status()["paused"] is False
