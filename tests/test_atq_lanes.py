"""Tests for ai_kos.atq_lanes — ATQ worker lanes (external CLI agents + shell).

Covers the lane registry and deterministic spawn wrappers without invoking
any real LLM-backed CLI:
- registry register/get/list + duplicate + unknown-name rejection
- ShellLane.spawn runs a real command and returns exit_code + capped preview
- ShellLane failure returns non-zero exit_code without raising
- missing-CLI lanes (shutil.which → None) return exit_code 127, never raise
- register_default_lanes always registers shell; external lanes only when found
- lane_status_all returns (name, status, detail) shaped records
- stdout preview is capped at 2000 chars; full output lands in the artifact
- the `ai-kos atq lanes` CLI lists lanes/statuses and can spawn on demand
"""

import json
from pathlib import Path

import pytest

from ai_kos.atq_lanes import (
    ClaudeCodeLane,
    CodexLane,
    LaneError,
    LaneRegistry,
    LaneSpec,
    OpenCodeLane,
    ShellLane,
    lane_status_all,
    register_default_lanes,
)


# ── registry ─────────────────────────────────────────────────────────────

def test_registry_register_get_list():
    reg = LaneRegistry()
    shell = ShellLane()
    reg.register(shell)
    assert reg.list() == ["shell"]
    assert reg.get("shell") is shell


def test_registry_rejects_duplicate():
    reg = LaneRegistry()
    reg.register(ShellLane())
    with pytest.raises(LaneError):
        reg.register(ShellLane())


def test_registry_get_unknown_raises():
    reg = LaneRegistry()
    with pytest.raises(LaneError):
        reg.get("nope")


def test_registry_spawn_unknown_raises():
    reg = LaneRegistry()
    with pytest.raises(LaneError):
        reg.spawn("nope", LaneSpec(name="nope", cmd=["echo", "hi"]))


def test_registry_list_is_insertion_ordered():
    reg = LaneRegistry()
    reg.register(ShellLane())
    reg.register(CodexLane())
    reg.register(ClaudeCodeLane())
    assert reg.list() == ["shell", "codex", "claude"]


# ── ShellLane ────────────────────────────────────────────────────────────

def test_shell_lane_runs_real_command(tmp_path):
    spec = LaneSpec(name="shell", cmd=["bash", "-c", "echo hello"],
                    task_id="t_abc", workdir=tmp_path)
    res = ShellLane().spawn(spec)
    assert res.exit_code == 0
    assert "hello" in res.stdout_preview
    assert res.lane == "shell"
    assert res.ran_at  # non-empty timestamp
    # full output artifact written at <task_id>-lane-<lane>.out
    assert res.artifact is not None
    assert Path(res.artifact).name == "t_abc-lane-shell.out"
    assert Path(res.artifact).exists()


def test_shell_lane_failure_no_raise(tmp_path):
    spec = LaneSpec(name="shell", cmd=["bash", "-c", "exit 3"], workdir=tmp_path)
    res = ShellLane().spawn(spec)
    assert res.exit_code == 3


def test_shell_lane_no_task_context_skips_artifact(tmp_path):
    spec = LaneSpec(name="shell", cmd=["bash", "-c", "echo hi"])
    res = ShellLane().spawn(spec)
    assert res.exit_code == 0
    assert res.artifact is None


def test_stdout_preview_capped():
    spec = LaneSpec(name="shell", cmd=["python3", "-c", "print('x' * 5000)"])
    res = ShellLane().spawn(spec)
    assert len(res.stdout_preview) <= 2000


# ── external CLI lanes ───────────────────────────────────────────────────

def test_missing_cli_lane_returns_127(monkeypatch):
    monkeypatch.setattr("ai_kos.atq_lanes.shutil.which", lambda binary: None)
    spec = LaneSpec(name="codex", cmd=["do the thing"])
    res = CodexLane().spawn(spec)
    assert res.exit_code == 127
    assert "not found" in res.stdout_preview
    assert res.artifact is None


def test_missing_cli_lane_never_raises(monkeypatch):
    monkeypatch.setattr("ai_kos.atq_lanes.shutil.which", lambda binary: None)
    for lane in (CodexLane(), ClaudeCodeLane(), OpenCodeLane()):
        res = lane.spawn(LaneSpec(name=lane.name, cmd=["prompt"]))
        assert res.exit_code == 127


# ── default registration ─────────────────────────────────────────────────

def test_register_default_lanes_always_shell_only_when_no_cli(monkeypatch):
    monkeypatch.setattr("ai_kos.atq_lanes.shutil.which", lambda binary: None)
    reg = LaneRegistry()
    register_default_lanes(reg)
    assert reg.list() == ["shell"]


def test_register_default_lanes_registers_codex_when_found(monkeypatch):
    def fake_which(binary):
        return f"/usr/bin/{binary}" if binary == "codex" else None
    monkeypatch.setattr("ai_kos.atq_lanes.shutil.which", fake_which)
    reg = LaneRegistry()
    register_default_lanes(reg)
    assert "shell" in reg.list()
    assert "codex" in reg.list()
    assert "claude" not in reg.list()
    assert "opencode" not in reg.list()


# ── status enumeration ───────────────────────────────────────────────────

def test_lane_status_all_shape(monkeypatch):
    monkeypatch.setattr("ai_kos.atq_lanes.shutil.which", lambda binary: None)
    reg = LaneRegistry()
    register_default_lanes(reg)
    statuses = lane_status_all(reg)
    assert isinstance(statuses, list)
    assert len(statuses) == 1
    s = statuses[0]
    assert s.name == "shell"
    assert s.status in ("running", "idle", "ready")
    assert isinstance(s.detail, str)


# ── CLI integration (ai-kos atq lanes) ───────────────────────────────────

def test_atq_lanes_cli_lists_registry(monkeypatch, capsys):
    from ai_kos import atq
    monkeypatch.setattr("ai_kos.atq_lanes.shutil.which", lambda binary: None)
    rc = atq.main(["lanes"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "shell" in data["lanes"]
    assert data["statuses"][0]["name"] == "shell"


def test_atq_lanes_cli_spawns_shell(monkeypatch, capsys):
    from ai_kos import atq
    monkeypatch.setattr("ai_kos.atq_lanes.shutil.which", lambda binary: None)
    rc = atq.main(["lanes", "--spawn", "shell", "--cmd", "echo hi"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["lane"] == "shell"
    assert "hi" in data["result"]["stdout_preview"]
