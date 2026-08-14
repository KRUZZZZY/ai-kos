"""Tests for ai_kos.atq_director — MCP server wrapping the hermes kanban CLI.

Pure-function + mocked-subprocess coverage (the server never touches a real
board in tests): task-id parsing, error rendering, board-snapshot parsing,
the spawn_worker create+dispatch flow (including the --max live-cap fix), and
the ai-kos binary resolution for atq_tick.
"""

import json
from unittest.mock import patch

import pytest

from ai_kos import atq_director


# ── parsing helpers ───────────────────────────────────────────────────────

def test_task_id_from_json():
    assert atq_director._task_id_from('{"id": "t_abc123"}') == "t_abc123"


def test_task_id_from_regex_fallback():
    assert atq_director._task_id_from("Created t_xyz789 (triage, assignee=delegtest)") == "t_xyz789"


def test_task_id_none_when_no_match():
    assert atq_director._task_id_from("no task here") is None


def test_fmt_renders_errors():
    out = atq_director._fmt({"exit_code": 2, "stdout": "", "stderr": "boom"})
    assert "exit=2" in out and "boom" in out


def test_fmt_renders_success_stdout():
    out = atq_director._fmt({"exit_code": 0, "stdout": "ok", "stderr": ""})
    assert out == "ok"


# ── tools (mocked subprocess) ────────────────────────────────────────────

def test_atq_status_parses_list():
    fake = {"exit_code": 0, "stdout": json.dumps([
        {"id": "t_1", "status": "ready", "assignee": "a", "title": "T"},
        {"id": "t_2", "status": "done", "assignee": "b", "title": "U"}]), "stderr": ""}
    with patch.object(atq_director, "_run", return_value=fake):
        out = atq_director.atq_status("board-x")
    assert 'counts: {"ready": 1, "done": 1}' in out
    assert "t_1" in out and "t_2" in out


def test_atq_workers_lists_only_running():
    fake = {"exit_code": 0, "stdout": json.dumps([
        {"id": "t_1", "status": "running", "assignee": "a", "title": "R"},
        {"id": "t_2", "status": "done", "assignee": "b", "title": "D"}]), "stderr": ""}
    with patch.object(atq_director, "_run", return_value=fake):
        out = atq_director.atq_workers("board-x")
    assert "t_1" in out and "t_2" not in out


def test_spawn_worker_creates_then_dispatches_with_cap2():
    """spawn_worker must dispatch with --max 2 (live concurrency cap — a board
    with one running card spawns nothing under --max 1)."""
    calls = []

    def fake_run(cmd, timeout=120):
        calls.append(cmd)
        if "create" in cmd:
            return {"exit_code": 0, "stdout": '{"id": "t_child1"}', "stderr": ""}
        return {"exit_code": 0, "stdout": "spawned 1", "stderr": ""}

    with patch.object(atq_director, "_run", side_effect=fake_run):
        out = atq_director.atq_spawn_worker("board-x", "Title", "Body", "delegtest")
    assert "t_child1" in out
    dispatch_calls = [c for c in calls if "dispatch" in c]
    assert dispatch_calls, "dispatch must run after create"
    assert "--max" in dispatch_calls[0]
    assert dispatch_calls[0][dispatch_calls[0].index("--max") + 1] == "2"


def test_spawn_worker_reports_create_failure():
    with patch.object(atq_director, "_run", return_value={
            "exit_code": 1, "stdout": "", "stderr": "bad board"}):
        out = atq_director.atq_spawn_worker("board-x", "T", "B", "p")
    assert "create failed" in out


def test_atq_tick_uses_resolved_binary():
    with patch.object(atq_director, "_run",
                      return_value={"exit_code": 0, "stdout": "ok", "stderr": ""}) as r:
        with patch.object(atq_director, "_ai_kos_bin", return_value="/opt/bin/ai-kos"):
            atq_director.atq_tick("board-x")
    cmd = r.call_args[0][0]
    assert cmd[0] == "/opt/bin/ai-kos"
    assert "tick" in cmd


def test_dispatch_passes_dry_run_flag():
    with patch.object(atq_director, "_run",
                      return_value={"exit_code": 0, "stdout": "{}", "stderr": ""}) as r:
        atq_director.atq_dispatch("board-x", max_n=3, dry_run=True)
    cmd = r.call_args[0][0]
    assert "--dry-run" in cmd and "--max" in cmd
    assert cmd[cmd.index("--max") + 1] == "3"
