"""Regression tests for the remaining ATQ MED audit fixes (consensus,
.hermes/ai-kos-audit/SYNTHESIS.md, MED section) — one test per
behavior-touching fix:

1. `atq lanes --spawn shell` routes the command through classify() — a
   destructive command (>=T2) is gated/refused, never executed via `bash -c`.
2. QueueManager.heartbeat does NOT re-extend an already-expired lease — a
   dead worker's zombie heartbeat cannot hold the task forever; it stays
   reclaimable.
3. ATQ state file updates are atomic (temp + os.replace) and the spawn-count
   read-modify-write runs under an flock — concurrent updates never corrupt
   the file and counts are monotonic (no lost spawns).
4. Reap dead-letters after max_attempts — a task that keeps failing is
   terminal after N reaps, not retried a (N+1)th time.
"""

import json
import sqlite3
import threading
import time
from unittest.mock import patch

import pytest

from ai_kos.atq import _load_state, lanes, record_spawn
from ai_kos.atq_queue_manager import QueueManager, QueueConfig
from ai_kos.atq_safety import RiskTier
from tests.test_atq_queue_manager import SCHEMA, _insert_task, _status

BOARD = "med-board"


# Shared fixture (file-backed SQLite, same shape as test_atq_queue_manager).
@pytest.fixture
def qm(tmp_path):
    db_path = str(tmp_path / "atq-med.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return QueueManager(db_path)


# ── Fix 1: lanes --spawn safety gate ────────────────────────────────────

class TestLanesSpawnSafetyGate:
    def test_destructive_cmd_gated_not_executed(self, tmp_path):
        """A destructive command through the lanes spawn path is refused
        (>=T2), and the lane is never actually spawned."""
        marker = tmp_path / "marker.txt"
        marker.write_text("keep me")
        with patch("ai_kos.atq_lanes.LaneRegistry.spawn") as mock_spawn:
            result = lanes(spawn_lane="shell", cmd=f"rm -rf {marker}")
        assert result["gated"] is True
        assert result["tier"] == RiskTier.T2_IRREVERSIBLE.name
        assert "not auto-executed" in result["refused"]
        mock_spawn.assert_not_called()          # nothing was executed
        assert marker.exists()                   # the destructive op never ran

    def test_t3_hard_stop_also_gated(self, tmp_path):
        with patch("ai_kos.atq_lanes.LaneRegistry.spawn") as mock_spawn:
            result = lanes(spawn_lane="shell", cmd="sudo rm -rf /")
        assert result["gated"] is True
        assert result["tier"] == RiskTier.T3_HARD_STOP.name
        mock_spawn.assert_not_called()

    def test_gate_blocks_external_lane_prompt_too(self, tmp_path):
        """External CLI lanes receive cmd as a prompt — a destructive prompt
        must not reach the agent either."""
        with patch("ai_kos.atq_lanes.LaneRegistry.spawn") as mock_spawn:
            result = lanes(spawn_lane="codex", cmd="git push --force origin main")
        assert result["gated"] is True
        assert result["tier"] == RiskTier.T2_IRREVERSIBLE.name
        mock_spawn.assert_not_called()

    def test_safe_cmd_still_executes(self):
        """The gate must not break least-risk tiering: T0/T1 commands still
        run through the lane."""
        result = lanes(spawn_lane="shell", cmd="echo hi")
        assert "gated" not in result
        assert "hi" in result["result"]["stdout_preview"]


# ── Fix 2: heartbeat must not re-extend an expired lease ────────────────

class TestHeartbeatExpiredLease:
    def test_heartbeat_rejects_expired_lease(self, qm):
        now = int(time.time())
        _insert_task(qm, "t1")
        run_id = qm._claim_task("t1", "w1")

        # Backdate the lease so it has already expired.
        conn = qm._conn()
        conn.execute(
            "UPDATE tasks SET claim_expires = ?, last_heartbeat_at = ? "
            "WHERE id = 't1'",
            (now - 100, now - 100),
        )
        conn.commit()
        conn.close()

        # A zombie heartbeat must NOT extend the expired lease.
        assert qm.heartbeat("t1", run_id) is False
        task = _status(qm, "t1")
        assert task["claim_expires"] == now - 100   # unchanged
        assert task["status"] == "running"

        # The task stays reclaimable — the reaper takes it back.
        assert qm._reap_stalled() == ["t1"]
        assert _status(qm, "t1")["status"] == "ready"

    def test_heartbeat_still_extends_valid_lease(self, qm):
        """Control: the expiry guard must not break legitimate heartbeats."""
        _insert_task(qm, "t1")
        run_id = qm._claim_task("t1", "w1")
        before = _status(qm, "t1")["claim_expires"]
        time.sleep(1.1)  # land in a later integer second (flakiness guard)
        assert qm.heartbeat("t1", run_id) is True
        assert _status(qm, "t1")["claim_expires"] > before


# ── Fix 3: atomic state file + locked read-modify-write ─────────────────

class TestAtomicStateFile:
    def test_concurrent_record_spawn_no_corruption_no_lost_updates(self, tmp_path):
        n_threads, per_thread = 8, 25
        expected_total = n_threads * per_thread
        observed = []
        obs_lock = threading.Lock()

        with patch("ai_kos.atq.STATE_DIR", tmp_path), \
             patch("ai_kos.atq._day_key", return_value="2099-01-01"):
            def worker():
                for _ in range(per_thread):
                    record_spawn(BOARD)

            def reader():
                # Sample the live count while writers hammer the file.
                for _ in range(300):
                    state = _load_state(BOARD)
                    total = sum((state.get("spawns_today") or {}).values())
                    with obs_lock:
                        observed.append(total)

            threads = [threading.Thread(target=worker) for _ in range(n_threads)]
            reader_thread = threading.Thread(target=reader)
            for t in threads + [reader_thread]:
                t.start()
            for t in threads + [reader_thread]:
                t.join()

            state = _load_state(BOARD)
            assert sum(state["spawns_today"].values()) == expected_total
            # Counts only ever grow — no lost updates, no torn reads.
            assert observed == sorted(observed), (
                f"counts not monotonic: {observed}")
            # The file is always valid JSON (atomic replace leaves no torn doc).
            json.loads((tmp_path / f"atq-{BOARD}.json").read_text())
            # No temp files leaked behind.
            leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
            assert leftovers == []

    def test_tick_state_persisted_under_lock(self, tmp_path):
        """tick still persists tick_count/needs_human (locked tail) and does
        not clobber spawn counts recorded concurrently."""
        from ai_kos.atq import tick
        with patch("ai_kos.atq.STATE_DIR", tmp_path), \
             patch("ai_kos.atq._kanban_json", return_value=[]), \
             patch("ai_kos.atq._kanban"):
            tick(BOARD)
            record_spawn(BOARD)          # written after the tick's snapshot
            state = _load_state(BOARD)
        assert state["tick_count"] == 1
        assert sum(state["spawns_today"].values()) == 1  # not clobbered


# ── Fix 4: reap dead-letters after max_attempts ─────────────────────────

class TestReapDeadLetter:
    def test_reap_dead_letters_after_max_attempts(self, qm):
        qm.config.max_attempts = 3
        now = int(time.time())
        _insert_task(qm, "t1", status="running", claim_lock="w1",
                     claim_expires=now - 100, last_heartbeat_at=now - 1)
        conn = qm._conn()
        conn.execute(
            "INSERT INTO task_runs (task_id, status, started_at) "
            "VALUES ('t1','running',?)", (now - 200,))
        run_id = conn.execute(
            "SELECT id FROM task_runs WHERE task_id='t1'").fetchone()["id"]
        conn.execute("UPDATE tasks SET current_run_id = ? WHERE id='t1'",
                     (run_id,))
        conn.commit()
        conn.close()

        def re_mark_expired():
            conn = qm._conn()
            conn.execute(
                "UPDATE tasks SET status='running', claim_lock='w1', "
                "claim_expires=?, last_heartbeat_at=? WHERE id='t1'",
                (now - 100, now - 1))
            conn.commit()
            conn.close()

        # Reaps 1 & 2: still under max_attempts → requeued, retryable.
        assert qm._reap_stalled() == ["t1"]
        assert _status(qm, "t1")["status"] == "ready"
        assert _status(qm, "t1")["consecutive_failures"] == 1

        re_mark_expired()
        assert qm._reap_stalled() == ["t1"]
        assert _status(qm, "t1")["consecutive_failures"] == 2
        assert _status(qm, "t1")["status"] == "ready"

        # Reap 3: hits max_attempts → dead-lettered, NOT retried.
        re_mark_expired()
        assert qm._reap_stalled() == []        # not returned as re-queued
        task = _status(qm, "t1")
        assert task["status"] == "dead-lettered"
        assert task["consecutive_failures"] == 3
        assert task["current_run_id"] is None
        assert task["claim_lock"] is None

        # The dead-letter event was recorded.
        conn = qm._conn()
        ev = conn.execute(
            "SELECT kind FROM task_events WHERE task_id='t1' "
            "AND kind='dead-lettered'").fetchone()
        conn.close()
        assert ev is not None

        # Terminal: a further reap pass must NOT resurrect/retry it.
        assert qm._reap_stalled() == []
        assert _status(qm, "t1")["status"] == "dead-lettered"
