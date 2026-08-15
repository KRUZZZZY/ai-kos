"""Tests for ai_kos.atq_ralph — the Ralph report envelope.

Mirrors dsh tool-ralph: one immutable objective → a sequence of fresh
children with structured handoff. Deterministic helpers only — the actual
child spawn is the caller's (kanban subdelegate or lane).

Covers:
- validate_ralph_report accepts a valid report and rejects each bad field
- ralph_handoff contains objective + workspace + cap + previous summary, and
  never seeds the parent conversation (previous=None case)
- RalphLoop: next_round raises past cap; feed(complete) returns a terminal
  reason; the budget_limited path fires when the cap is hit while continuing
- run_once builds the handoff, calls a stub spawn_fn, validates, advances
- Worker.complete_report / block_report write the report artifact and call
  complete()/block() with a rendered summary
- RalphReport JSON roundtrip preserves equality
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_kos.atq_ralph import (
    RalphBudgetError,
    RalphError,
    RalphLoop,
    RalphReport,
    ralph_handoff,
    validate_ralph_report,
)
from ai_kos.atq_worker import Worker


def _valid_report(**overrides):
    data = {
        "status": "continue",
        "summary": "made progress",
        "evidence": "ran tests",
        "next_steps": ["run more"],
        "blockers": [],
    }
    data.update(overrides)
    return data


# ── validate ─────────────────────────────────────────────────────────────

def test_validate_accepts_valid():
    r = validate_ralph_report(_valid_report())
    assert isinstance(r, RalphReport)
    assert r.status == "continue"
    assert r.summary == "made progress"
    assert r.next_steps == ["run more"]


def test_validate_rejects_unknown_status():
    with pytest.raises(RalphError):
        validate_ralph_report(_valid_report(status="nope"))


def test_validate_rejects_missing_or_empty_summary():
    with pytest.raises(RalphError):
        validate_ralph_report(_valid_report(summary=""))
    with pytest.raises(RalphError):
        validate_ralph_report(_valid_report(summary="   "))
    with pytest.raises(RalphError):
        validate_ralph_report({"status": "complete"})


def test_validate_rejects_non_list_fields():
    with pytest.raises(RalphError):
        validate_ralph_report(_valid_report(next_steps="not a list"))
    with pytest.raises(RalphError):
        validate_ralph_report(_valid_report(blockers="not a list"))


def test_validate_rejects_oversized_handoff():
    huge = "x" * 25000
    with pytest.raises(RalphError):
        validate_ralph_report(_valid_report(evidence=huge))


def test_validate_rejects_non_dict():
    with pytest.raises(RalphError):
        validate_ralph_report("not a dict")


# ── handoff ──────────────────────────────────────────────────────────────

def test_handoff_contains_objective_workspace_cap_previous():
    prev = RalphReport(status="continue", summary="round 1 done", evidence="e",
                       next_steps=["n"], blockers=[])
    h = ralph_handoff("build a thing", 2, 10, "/tmp/ws", prev)
    assert "build a thing" in h
    assert "/tmp/ws" in h
    assert "2 / 10" in h
    assert "round 1 done" in h


def test_handoff_previous_none_no_parent_leak():
    h = ralph_handoff("objective here", 1, 10, "/tmp/ws", None)
    assert "no previous round" in h
    # parent conversation is never seeded — no transcript/context leakage
    assert "parent" not in h.lower()
    assert "conversation" not in h.lower()


# ── RalphLoop ────────────────────────────────────────────────────────────

def test_loop_next_round_raises_past_cap():
    loop = RalphLoop("obj", max_rounds=1)
    loop.next_round()  # round 1
    with pytest.raises(RalphBudgetError):
        loop.next_round()  # past cap


def test_loop_feed_complete_returns_terminal():
    loop = RalphLoop("obj", max_rounds=10)
    loop.next_round()
    out = loop.feed(RalphReport(status="complete", summary="all done"))
    assert "complete" in out
    assert "all done" in out


def test_loop_feed_blocked_returns_terminal():
    loop = RalphLoop("obj", max_rounds=10)
    loop.next_round()
    out = loop.feed(RalphReport(status="blocked", summary="stuck", blockers=["x"]))
    assert "blocked" in out


def test_loop_budget_limited_when_cap_hit_while_continuing():
    loop = RalphLoop("obj", max_rounds=1)
    loop.next_round()
    out = loop.feed(RalphReport(status="continue", summary="still going"))
    assert loop.budget_limited is True
    assert "budget_limited" in out


def test_run_once_advances_and_validates(tmp_path):
    loop = RalphLoop("obj", max_rounds=5, workspace=tmp_path)

    def spawn_fn(objective, handoff):
        assert objective == "obj"
        assert "Round: 1 / 5" in handoff
        return {"status": "complete", "summary": "did it", "evidence": "ok"}

    result = loop.run_once(spawn_fn)
    assert result["round"] == 1
    assert result["status"] == "complete"
    assert isinstance(result["report"], RalphReport)
    assert loop.round == 1


def test_run_once_rejects_invalid_report():
    loop = RalphLoop("obj", max_rounds=5)

    def bad_spawn(objective, handoff):
        return {"status": "nonsense", "summary": "x"}

    with pytest.raises(RalphError):
        loop.run_once(bad_spawn)


# ── JSON roundtrip ───────────────────────────────────────────────────────

def test_report_json_roundtrip():
    r = RalphReport(status="continue", summary="s", evidence="e",
                    next_steps=["a", "b"], blockers=["c"])
    r2 = RalphReport.from_json(r.to_json())
    assert r2 == r
    assert r2.next_steps == ["a", "b"]


# ── Worker integration ───────────────────────────────────────────────────

def test_worker_complete_report_writes_artifact_and_completes(tmp_path):
    w = Worker("t_abc", workdir=tmp_path)
    report = RalphReport(status="complete", summary="done", evidence="e" * 500,
                         next_steps=[], blockers=[])
    calls = []
    with patch.object(w, "complete", side_effect=lambda r: calls.append(r)):
        w.complete_report(report)
    assert len(calls) == 1
    rendered = calls[0]
    assert "[complete]" in rendered
    assert "done" in rendered
    assert "e" * 300 in rendered  # evidence truncated to 300 chars
    artifact = tmp_path / "t_abc-report.json"
    assert artifact.exists()
    assert RalphReport.from_json(artifact.read_text()) == report


def test_worker_block_report_writes_artifact_and_blocks(tmp_path):
    w = Worker("t_abc", workdir=tmp_path)
    report = RalphReport(status="blocked", summary="stuck", blockers=["x"])
    calls = []
    with patch.object(w, "block", side_effect=lambda r: calls.append(r)):
        w.block_report(report)
    assert len(calls) == 1
    assert "[blocked]" in calls[0]
    assert (tmp_path / "t_abc-report.json").exists()


def test_worker_ralph_spawn_embeds_handoff(tmp_path):
    w = Worker("t_abc", workdir=tmp_path)
    handoff = ralph_handoff("obj", 1, 3, str(tmp_path), None)
    with patch.object(w, "subdelegate", return_value="t_child1") as sd:
        with patch.object(w, "comment", return_value=""):
            child = w.ralph_spawn("Round 1", "obj", handoff, "delegtest", parent="t_abc")
    assert child == "t_child1"
    body = sd.call_args[0][1]
    assert "obj" in body
    assert "Round: 1 / 3" in body
    assert str(tmp_path) in body


def test_worker_ralph_spawn_reads_child_report(tmp_path):
    w = Worker("t_abc", workdir=tmp_path)
    handoff = ralph_handoff("obj", 1, 3, str(tmp_path), None)
    report = RalphReport(status="complete", summary="child done")
    (tmp_path / "t_child1-report.json").write_text(report.to_json())
    with patch.object(w, "subdelegate", return_value="t_child1"):
        with patch.object(w, "comment", return_value="") as comment:
            child = w.ralph_spawn("Round 1", "obj", handoff, "delegtest", parent="t_abc")
    assert child == "t_child1"
    assert any("child done" in c[0][0] for c in comment.call_args_list)
