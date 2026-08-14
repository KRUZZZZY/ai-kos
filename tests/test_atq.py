"""Tests for ai_kos.atq — Agent Task Queue bridge.

Pure-function tests (body parsing, criteria extraction) + mocked-subprocess
tests (submit idempotency, tick flow, budget counters). No real kanban calls.
"""

import json
from unittest.mock import patch

import pytest

from ai_kos.atq import (
    _body_criteria,
    _body_section,
    _load_state,
    _save_state,
    submit,
    tick,
)

MISSION_BODY = """## Purpose
Do the thing.

## Architecture
Layers.

## Success Criteria
- A mission runs end-to-end unattended
- Leases expire and tasks are re-dispatched
1) Numbered criteria also work
"""


def test_body_section_extracts_case_insensitive():
    assert "Do the thing." in _body_section(MISSION_BODY, "Purpose")
    assert "Layers." in _body_section(MISSION_BODY, "architecture")  # lowercase header


def test_body_section_missing_returns_empty():
    assert _body_section(MISSION_BODY, "Nope") == ""


def test_body_criteria_parses_dash_and_numbered_items():
    criteria = _body_criteria(MISSION_BODY)
    assert len(criteria) == 3
    assert criteria[0] == "A mission runs end-to-end unattended"
    assert criteria[1] == "Leases expire and tasks are re-dispatched"
    assert criteria[2] == "Numbered criteria also work"


def test_body_criteria_empty_when_no_section():
    assert _body_criteria("## Purpose\nNo criteria here") == []


class FakeProc:
    def __init__(self, stdout="", stderr=""):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = 0


@patch("ai_kos.atq._kanban_json", return_value=[])
@patch("ai_kos.atq._kanban")
def test_submit_creates_root_with_criteria(mock_kanban, mock_json):
    fake = FakeProc(stdout="Created t_abc123  (triage, assignee=atq-manager)")
    mock_kanban.return_value = fake

    with patch("ai_kos.atq._mission_article", return_value={
        "title": "Test Mission", "type": "mission", "_body": MISSION_BODY,
    }):
        result = submit("test-mission")

    assert result["status"] == "created"
    assert result["root_id"] == "t_abc123"
    assert result["board"] == "mission-test-mission"
    # root task created with triage + criteria in body
    create_call = mock_kanban.call_args[0][0]
    assert "--triage" in create_call
    body = create_call[create_call.index("--body") + 1]
    assert "A mission runs end-to-end unattended" in body


@patch("ai_kos.atq._kanban_json", return_value=[
    {"id": "t_root", "title": "[mission] Test Mission", "status": "todo",
     "assignee": "atq-manager"},
])
@patch("ai_kos.atq._kanban")
def test_submit_idempotent_when_root_exists(mock_kanban, mock_json):
    with patch("ai_kos.atq._mission_article", return_value={
        "title": "Test Mission", "type": "mission", "_body": MISSION_BODY,
    }):
        result = submit("test-mission")
    assert result["status"] == "exists"
    assert result["root_id"] == "t_root"
    # ensure_board runs (boards create) but NO root task create is attempted
    calls = [c[0][0] for c in mock_kanban.call_args_list]
    assert calls == [["boards", "create", "mission-test-mission",
                      "--description", "Test Mission"]]


@patch("ai_kos.atq._kanban_json", return_value=[
    {"id": "t_triage", "status": "triage", "title": "root"},
    {"id": "t_blocked", "status": "blocked", "title": "needs human"},
    {"id": "t_ready", "status": "ready", "title": "work"},
])
@patch("ai_kos.atq._kanban")
def test_tick_decomposes_triage_and_reports_blocked(mock_kanban, mock_json, tmp_path):
    # NOTE: stacked @patch injects bottom-up: (mock_kanban, mock_json, fixture...)
    mock_kanban.side_effect = [FakeProc(), FakeProc(stdout="Spawned: 1")]
    with patch("ai_kos.atq.STATE_DIR", tmp_path):
        result = tick("test-board", max_dispatch=3, daily_cap=10)
        # state persisted (read inside the patched STATE_DIR)
        state = _load_state("test-board")
        assert state["tick_count"] == 1
        assert state["needs_human"][0]["id"] == "t_blocked"

    assert result["decomposed"] == ["t_triage"]
    assert result["needs_human"] == [{"id": "t_blocked", "title": "needs human"}]
    assert result["spawned"] == 1
    # dispatch was called with the budget-limited max
    dispatch_args = mock_kanban.call_args_list[1][0][0]
    assert dispatch_args[:2] == ["dispatch", "--max"]
    assert dispatch_args[2] == "3"


@patch("ai_kos.atq._kanban_json", return_value=[
    {"id": "t_ready", "status": "ready", "title": "work"},
])
@patch("ai_kos.atq._kanban")
def test_tick_paused_does_not_dispatch(mock_kanban, mock_json, tmp_path):
    state = {"paused": True, "spawns_today": {}, "needs_human": [],
             "tick_count": 0, "last_tick": None}
    (tmp_path / "atq-test-paused.json").write_text(json.dumps(state))
    with patch("ai_kos.atq.STATE_DIR", tmp_path):
        result = tick("test-paused")

    assert result["paused"] is True
    assert result["spawned"] == 0
    mock_kanban.assert_not_called()


@patch("ai_kos.atq._kanban_json", return_value=[])
@patch("ai_kos.atq._kanban")
def test_tick_daily_cap_stops_dispatch(mock_kanban, mock_json, tmp_path):
    state = {"paused": False, "spawns_today": {"2099-01-01": 10},
             "needs_human": [], "tick_count": 0, "last_tick": None}
    (tmp_path / "atq-test-cap.json").write_text(json.dumps(state))
    with patch("ai_kos.atq.STATE_DIR", tmp_path), \
         patch("ai_kos.atq._day_key", return_value="2099-01-01"):
        result = tick("test-cap", daily_cap=10)

    assert result["spawned"] == 0
    mock_kanban.assert_not_called()


def test_state_roundtrip(tmp_path):
    with patch("ai_kos.atq.STATE_DIR", tmp_path):
        _save_state("b", {"tick_count": 3, "paused": False})
        assert _load_state("b")["tick_count"] == 3
