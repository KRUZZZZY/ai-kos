"""Tests for ai_kos.atq_worker — the reference ATQ worker.

Covers the protocol's core guarantees without touching a real kanban:
- state machine: run() executes, comments, completes; failure blocks
- artifact isolation: two workers never collide (task-id prefixes)
- sub-delegation: children are created and results aggregated (mocked CLI)
- idempotency: retries skip already-applied side effects
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_kos.atq_worker import Worker


@pytest.fixture
def worker(tmp_path):
    w = Worker("t_abc123", board="test-board", workdir=tmp_path, author="tester")
    w.claimed = True  # run() refuses to execute without a successful claim
    return w


def _fake_run(results: dict):
    """Return a _run replacement returning canned outputs per command prefix."""
    def fake(cmd, timeout=120):
        key = " ".join(cmd)
        for prefix, out in results.items():
            if key.startswith(prefix):
                if isinstance(out, dict):
                    return out
                return {"exit_code": 0, "stdout": out, "stderr": ""}
        return {"exit_code": 0, "stdout": "(unmocked) " + key, "stderr": ""}
    return fake


# ── artifact isolation (no-clobber) ──────────────────────────────────────

def test_artifact_names_are_task_scoped(tmp_path):
    """Two workers in the SAME directory still produce disjoint files."""
    a = Worker("t_aaa111", workdir=tmp_path)
    b = Worker("t_bbb222", workdir=tmp_path)
    pa = a.write_artifact("output.txt", "A")
    pb = b.write_artifact("output.txt", "B")
    assert pa.name == "t_aaa111-output.txt"
    assert pb.name == "t_bbb222-output.txt"
    assert pa != pb
    assert pa.read_text() == "A" and pb.read_text() == "B"


def test_artifact_parent_dir_created(tmp_path):
    w = Worker("t_aaa111", workdir=tmp_path / "nested" / "dir")
    p = w.artifact_path("x.json")
    assert p.parent.exists()


# ── state machine: execute → comment → complete / block ─────────────────

def test_run_completes_on_success(worker):
    calls = []
    with patch("ai_kos.atq_worker._run", side_effect=_fake_run({
        "hermes kanban --board test-board complete": "COMPLETED",
    })):
        with patch.object(worker, "comment", side_effect=lambda b: calls.append(("comment", b))):
            with patch.object(worker, "complete", side_effect=lambda r: calls.append(("complete", r))) as complete:
                rc = worker.run(cmd="echo hi")
    assert rc == 0
    assert any(c[0] == "comment" and "exit=0" in c[1] for c in calls)
    complete.assert_called_once()
    assert complete.call_args[0][0].startswith("done:")


def test_run_blocks_on_failure(worker):
    with patch("ai_kos.atq_worker._run", side_effect=_fake_run({
        "bash -c": {"exit_code": 1, "stdout": "", "stderr": "boom"}
    })):
        with patch.object(worker, "block", return_value="BLOCKED") as block:
            rc = worker.run(cmd="false")
    assert rc == 1
    block.assert_called_once()
    assert "boom" in block.call_args[0][0]


def test_run_refuses_t2_command_without_executing(worker):
    """Least-risk gate: destructive commands are blocked, never executed."""
    with patch("ai_kos.atq_worker._run", side_effect=_fake_run({})) as r:
        with patch.object(worker, "block", return_value="BLOCKED") as block:
            rc = worker.run(cmd="rm -rf /tmp/x")
    assert rc == 1
    block.assert_called_once()
    assert "least-risk" in block.call_args[0][0]
    bash_calls = [c for c in r.call_args_list if c.args[0][0] == "bash"]
    assert not bash_calls, "destructive command must never reach the shell"


def test_run_refuses_without_claim():
    """A worker that lost the claim race must not execute side effects."""
    w = Worker("t_abc123", board="test-board")  # claimed stays False
    with patch.object(w, "block", return_value="BLOCKED") as block:
        rc = w.run(cmd="echo hi")
    assert rc == 1
    block.assert_called_once()
    assert "claim" in block.call_args[0][0]


def test_claim_returns_false_on_failure(worker):
    with patch("ai_kos.atq_worker._run", side_effect=_fake_run({
        "hermes kanban --board test-board claim": "cannot claim t_abc123: status=todo",
    })):
        assert worker.claim() is False
    assert worker.claimed is False


def test_idempotent_retry_skips_repeat_execution(worker):
    """A retried worker must not re-run an already-applied command.

    Counts bash executions across BOTH runs — the audit flagged the earlier
    snapshot-between-runs version as vacuous (it never observed run 2).
    """
    with patch("ai_kos.atq_worker._run", side_effect=_fake_run({})) as r:
        with patch.object(worker, "comment", return_value=""):
            with patch.object(worker, "write_artifact"):
                worker.run(cmd="echo hi")
                worker.run(cmd="echo hi")
    exec_calls = [c for c in r.call_args_list if c.args[0][0] == "bash"]
    assert len(exec_calls) == 1, "command executed twice on retry"


# ── sub-delegation + aggregation ─────────────────────────────────────────

def test_subdelegate_creates_child_and_dispatches(worker, tmp_path):
    """subdelegate() creates a card, parses the id, and dispatches it."""
    with patch("ai_kos.atq.STATE_DIR", tmp_path):
        with patch("ai_kos.atq_worker._run", side_effect=_fake_run({
            "hermes kanban --board test-board create": '{"id": "t_child99"}',
            "hermes kanban --board test-board dispatch": "spawned 1",
        })):
            with patch.object(worker, "comment", return_value=""):
                cid = worker.subdelegate("Subtask", "do it", "delegtest", parent="t_abc123")
    assert cid == "t_child99"
    assert any(e["kind"] == "subdelegate" and e["detail"] == "t_child99"
               for e in worker.side_effect_log)


def test_aggregate_collects_done_and_timeout(worker):
    calls = {"n": 0}

    def fake(cmd, timeout=120):
        calls["n"] += 1
        cid = cmd[-1]
        if calls["n"] < 4:
            return {"exit_code": 0, "stdout": f"status:    running\nid: {cid}", "stderr": ""}
        return {"exit_code": 0, "stdout": f"status:    done\nid: {cid}\nresult: ok", "stderr": ""}

    with patch("ai_kos.atq_worker._run", side_effect=fake):
        with patch("ai_kos.atq_worker.time.sleep", return_value=None):
            results = worker.aggregate(["t_child1", "t_child2"], poll_seconds=0,
                                       max_wait_seconds=30)
    assert {r["child"]: r["status"] for r in results} == {
        "t_child1": "done", "t_child2": "done"}


def test_aggregate_ignores_blocked_in_body_text(worker):
    """A running card whose BODY mentions 'blocked' must not be classified
    blocked — status is parsed from the status field only."""
    calls = {"n": 0}

    def fake(cmd, timeout=120):
        calls["n"] += 1
        cid = cmd[-1]
        body = (f"Task {cid}: this card is blocked forever\n  status:    running\n"
                f"Body:\nworkers should not be blocked by this text")
        if calls["n"] >= 2:
            body = body.replace("status:    running", "status:    done")
        return {"exit_code": 0, "stdout": body, "stderr": ""}

    with patch("ai_kos.atq_worker._run", side_effect=fake):
        with patch("ai_kos.atq_worker.time.sleep", return_value=None):
            results = worker.aggregate(["t_child1"], poll_seconds=0, max_wait_seconds=30)
    assert results[0]["status"] == "done", "body text must not flip status to blocked"


def test_run_with_subdelegates_aggregates_and_completes(worker, tmp_path):
    def fake(cmd, timeout=120):
        key = " ".join(cmd)
        if key.startswith("hermes kanban --board test-board create"):
            return {"exit_code": 0, "stdout": '{"id": "t_child1"}', "stderr": ""}
        if key.startswith("hermes kanban --board test-board show"):
            return {"exit_code": 0, "stdout": "status:    done", "stderr": ""}
        if key.startswith("hermes kanban --board test-board complete"):
            return {"exit_code": 0, "stdout": "COMPLETED", "stderr": ""}
        return {"exit_code": 0, "stdout": "ok", "stderr": ""}

    with patch("ai_kos.atq.STATE_DIR", tmp_path):
        with patch("ai_kos.atq_worker._run", side_effect=fake):
            with patch.object(worker, "comment", return_value=""):
                rc = worker.run(subdelegates=[("Sub", "body", "delegtest")])
    assert rc == 0
    agg = worker.workdir / "t_abc123-aggregation.json"
    assert agg.exists()
    data = json.loads(agg.read_text())
    assert data[0]["status"] == "done"


def test_aggregate_blocked_child_blocks_parent(worker, tmp_path):
    def fake(cmd, timeout=120):
        key = " ".join(cmd)
        if key.startswith("hermes kanban --board test-board create"):
            return {"exit_code": 0, "stdout": '{"id": "t_child1"}', "stderr": ""}
        if key.startswith("hermes kanban --board test-board show"):
            return {"exit_code": 0, "stdout": "status:    blocked", "stderr": ""}
        return {"exit_code": 0, "stdout": "ok", "stderr": ""}

    with patch("ai_kos.atq.STATE_DIR", tmp_path):
        with patch("ai_kos.atq_worker._run", side_effect=fake):
            with patch.object(worker, "comment", return_value=""):
                with patch.object(worker, "block", return_value="BLOCKED") as block:
                    rc = worker.run(subdelegates=[("Sub", "body", "delegtest")])
    assert rc == 1
    block.assert_called_once()
