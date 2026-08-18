"""Regression tests for the ATQ + test-isolation audit fixes (consensus,
.hermes/ai-kos-audit/SYNTHESIS.md) — one test per behavior-touching fix:

1. atq_safety destructive denylist — `find … -delete`/`-exec`,
   `rm --recursive --force`, `rmdir -p`, `shred -u`, `git push --force`
   (flag anywhere), `shutil.rmtree` one-liners are NEVER T0/T1.
2. Single spawn gate — paused kill-switch + daily cap enforced on the direct
   dispatch paths: atq_spawn_worker, atq_dispatch, Worker.subdelegate.
3. Worker heartbeats in the run loop (aggregate polling) so long-running work
   is not reclaimed; lease loss aborts before executing.
4. config honors AI_KOS_KNOWLEDGE_DIR → TaskManager resolves its DB inside
   the isolated dir instead of production knowledge/future_tasks.db.
5. Side-effect log wired into the execute path AND persisted across worker
   instances — executing twice never double-executes the side effect.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_kos import atq_director
from ai_kos.atq import _load_state, record_spawn, spawn_gate
from ai_kos.atq_safety import RiskTier, classify
from ai_kos.atq_worker import Worker

BOARD = "test-board"


# ── Fix 1: destructive-pattern denylist ─────────────────────────────────

class TestDestructiveDenylist:
    @pytest.mark.parametrize("cmd", [
        "find . -delete",
        "find /data -name '*.tmp' -delete",
        "find . -exec rm {} \\;",
        "find . -execdir rm -rf {} +",
        "cd /x && find . -delete",
        "rm --recursive --force /x",
        "rm -rf --force /x",
        "rm --recursive /x",
        "rmdir -p /x/y",
        "rmdir --parents /x/y",
        "rmdir /x",
        "shred -u secret.txt",
        "shred --remove secret.txt",
        "git push origin main --force",
        "git push -f origin main",
        "GIT PUSH -F origin main",
        "python3 -c \"import shutil; shutil.rmtree('/x')\"",
        "python3 -c \"import os; os.remove('/x')\"",
        "python3 -c \"import os; os.unlink('/x')\"",
    ])
    def test_destructive_never_t0_t1(self, cmd):
        tier = classify(cmd)
        assert tier >= RiskTier.T2_IRREVERSIBLE, (
            f"{cmd!r} classified {tier.name} — destructive commands must "
            f"never be T0/T1")

    @pytest.mark.parametrize("cmd", [
        "find . -name '*.py'",
        "find /var/log -type f",
        "find . -maxdepth 2 -print",
        "git push origin main",
        "git status",
        "cat file.txt",
        "grep -r 'shutil.rmtree' docs/",
        "ls -la",
        "echo hi > workspace/out.txt",
    ])
    def test_read_only_and_reversible_untouched(self, cmd):
        """The denylist must not break the least-risk tiering for genuinely
        safe commands."""
        assert classify(cmd) <= RiskTier.T1_REVERSIBLE, f"{cmd!r} over-blocked"

    def test_t3_absolute_stops_still_win(self):
        assert classify("sudo rm -rf /") == RiskTier.T3_HARD_STOP
        assert classify("rm -rf /tmp/x") == RiskTier.T2_IRREVERSIBLE


# ── Fix 2: single spawn gate ────────────────────────────────────────────

class TestSpawnGate:
    def _write_state(self, tmp_path, board=BOARD, paused=False, used=0, day="2099-01-01"):
        state = {"paused": paused, "spawns_today": {day: used} if used else {},
                 "needs_human": [], "tick_count": 0, "last_tick": None}
        (tmp_path / f"atq-{board}.json").write_text(json.dumps(state))

    def test_gate_allows_when_open(self, tmp_path):
        with patch("ai_kos.atq.STATE_DIR", tmp_path):
            allowed, reason = spawn_gate(BOARD, daily_cap=10)
        assert allowed
        assert "spawns used today" in reason

    def test_gate_refuses_when_paused(self, tmp_path):
        self._write_state(tmp_path, paused=True)
        with patch("ai_kos.atq.STATE_DIR", tmp_path):
            allowed, reason = spawn_gate(BOARD)
        assert not allowed
        assert "paused" in reason

    def test_gate_refuses_at_cap(self, tmp_path):
        self._write_state(tmp_path, used=5)
        with patch("ai_kos.atq.STATE_DIR", tmp_path), \
             patch("ai_kos.atq._day_key", return_value="2099-01-01"):
            allowed, _ = spawn_gate(BOARD, daily_cap=5)
        assert not allowed

    def test_record_spawn_counts_toward_cap(self, tmp_path):
        with patch("ai_kos.atq.STATE_DIR", tmp_path):
            assert spawn_gate(BOARD, daily_cap=2)[0]
            record_spawn(BOARD)
            assert spawn_gate(BOARD, daily_cap=2)[0]
            record_spawn(BOARD)
            allowed, reason = spawn_gate(BOARD, daily_cap=2)
        assert not allowed
        assert "cap reached (2/2)" in reason


class TestSpawnGateDirector:
    def test_atq_spawn_worker_refused_when_paused(self, tmp_path):
        state = {"paused": True, "spawns_today": {}}
        (tmp_path / "atq-board-x.json").write_text(json.dumps(state))
        with patch("ai_kos.atq.STATE_DIR", tmp_path):
            with patch.object(atq_director, "_run") as r:
                out = atq_director.atq_spawn_worker("board-x", "T", "B", "p")
        assert "spawn refused" in out
        r.assert_not_called()

    def test_atq_spawn_worker_refused_when_cap_reached(self, tmp_path):
        # default daily cap is 30 — used=30 means the cap is exhausted
        state = {"paused": False, "spawns_today": {"2099-01-01": 30}}
        (tmp_path / "atq-board-x.json").write_text(json.dumps(state))
        with patch("ai_kos.atq.STATE_DIR", tmp_path), \
             patch("ai_kos.atq._day_key", return_value="2099-01-01"):
            with patch.object(atq_director, "_run") as r:
                out = atq_director.atq_spawn_worker("board-x", "T", "B", "p")
        assert "spawn refused" in out
        r.assert_not_called()

    def test_atq_spawn_worker_records_spawn_when_allowed(self, tmp_path):
        def fake_run(cmd, timeout=120):
            if "create" in cmd:
                return {"exit_code": 0, "stdout": '{"id": "t_child1"}', "stderr": ""}
            return {"exit_code": 0, "stdout": "spawned 1", "stderr": ""}

        with patch("ai_kos.atq.STATE_DIR", tmp_path), \
             patch("ai_kos.atq._day_key", return_value="2099-01-01"):
            with patch.object(atq_director, "_run", side_effect=fake_run):
                atq_director.atq_spawn_worker("board-x", "T", "B", "p")
            state = _load_state("board-x")
        assert state["spawns_today"]["2099-01-01"] == 1

    def test_atq_dispatch_refused_when_paused(self, tmp_path):
        state = {"paused": True, "spawns_today": {}}
        (tmp_path / "atq-board-x.json").write_text(json.dumps(state))
        with patch("ai_kos.atq.STATE_DIR", tmp_path):
            with patch.object(atq_director, "_run") as r:
                out = atq_director.atq_dispatch("board-x", max_n=2)
        assert "dispatch refused" in out
        r.assert_not_called()

    def test_atq_dispatch_records_spawned_count(self, tmp_path):
        with patch("ai_kos.atq.STATE_DIR", tmp_path), \
             patch("ai_kos.atq._day_key", return_value="2099-01-01"):
            with patch.object(atq_director, "_run", return_value={
                    "exit_code": 0, "stdout": "Spawned: 3", "stderr": ""}):
                atq_director.atq_dispatch("board-x", max_n=2)
            state = _load_state("board-x")
        assert state["spawns_today"]["2099-01-01"] == 3


class TestSpawnGateWorkerSubdelegate:
    def test_subdelegate_refused_when_paused(self, tmp_path):
        state = {"paused": True, "spawns_today": {}}
        (tmp_path / "atq-test-board.json").write_text(json.dumps(state))
        w = Worker("t_abc123", board=BOARD, workdir=tmp_path)
        with patch("ai_kos.atq.STATE_DIR", tmp_path):
            with patch("ai_kos.atq_worker._run") as r:
                with patch.object(w, "comment", return_value="") as c:
                    cid = w.subdelegate("Sub", "body", "p")
        assert cid is None
        r.assert_not_called()
        assert any("refused" in str(x) for x in c.call_args_list)

    def test_subdelegate_refused_at_cap(self, tmp_path):
        # default daily cap is 30 — used=30 means the cap is exhausted
        state = {"paused": False, "spawns_today": {"2099-01-01": 30}}
        (tmp_path / "atq-test-board.json").write_text(json.dumps(state))
        w = Worker("t_abc123", board=BOARD, workdir=tmp_path)
        with patch("ai_kos.atq.STATE_DIR", tmp_path), \
             patch("ai_kos.atq._day_key", return_value="2099-01-01"):
            with patch("ai_kos.atq_worker._run") as r:
                with patch.object(w, "comment", return_value=""):
                    cid = w.subdelegate("Sub", "body", "p")
        assert cid is None
        r.assert_not_called()

    def test_subdelegate_records_spawn_when_allowed(self, tmp_path):
        w = Worker("t_abc123", board=BOARD, workdir=tmp_path)
        with patch("ai_kos.atq.STATE_DIR", tmp_path), \
             patch("ai_kos.atq._day_key", return_value="2099-01-01"):
            with patch("ai_kos.atq_worker._run", side_effect=lambda cmd, timeout=120: (
                {"exit_code": 0, "stdout": '{"id": "t_child1"}', "stderr": ""}
                if "create" in cmd else
                {"exit_code": 0, "stdout": "spawned 1", "stderr": ""})):
                with patch.object(w, "comment", return_value=""):
                    cid = w.subdelegate("Sub", "body", "p")
            state = _load_state(BOARD)
        assert cid == "t_child1"
        assert state["spawns_today"]["2099-01-01"] == 1


# ── Fix 3: worker heartbeat in the run loop ─────────────────────────────

class TestWorkerHeartbeat:
    @pytest.fixture
    def worker(self, tmp_path):
        w = Worker("t_abc123", board=BOARD, workdir=tmp_path, author="tester")
        w.claimed = True
        return w

    def test_run_heartbeats_through_execution(self, worker):
        hb = []
        with patch("ai_kos.atq_worker._run", side_effect=lambda cmd, timeout=120: (
                {"exit_code": 0, "stdout": "hi", "stderr": ""})):
            with patch.object(worker, "comment", return_value=""):
                with patch.object(worker, "heartbeat",
                                 side_effect=lambda: hb.append(True) or True):
                    rc = worker.run(cmd="echo hi")
        assert rc == 0
        assert len(hb) >= 2, "run loop must heartbeat (start + around execute)"

    def test_aggregate_heartbeats_while_polling(self, worker):
        hb = []
        with patch("ai_kos.atq_worker._run", side_effect=lambda cmd, timeout=120: (
                {"exit_code": 0, "stdout": "status:    done", "stderr": ""}
                if "show" in cmd else
                {"exit_code": 0, "stdout": "ok", "stderr": ""})):
            with patch.object(worker, "heartbeat",
                             side_effect=lambda: hb.append(True) or True):
                with patch("ai_kos.atq_worker.time.sleep", return_value=None):
                    results = worker.aggregate(["t_child1"], poll_seconds=0,
                                               max_wait_seconds=30)
        assert results[0]["status"] == "done"
        assert hb, "aggregate must heartbeat each poll iteration"

    def test_lease_loss_aborts_before_executing(self, worker):
        """A failed heartbeat (lease reclaimed) must abort BEFORE the command
        reaches the shell — executing would double-run the new owner."""
        with patch("ai_kos.atq_worker._run") as r:
            with patch.object(worker, "heartbeat", return_value=False):
                with patch.object(worker, "block", return_value="BLOCKED") as block:
                    rc = worker.run(cmd="echo hi")
        assert rc == 1
        block.assert_called_once()
        assert "lease" in block.call_args[0][0]
        bash_calls = [c for c in r.call_args_list if c.args[0][0] == "bash"]
        assert not bash_calls, "must not execute after losing the lease"


# ── Fix 4: test isolation — AI_KOS_KNOWLEDGE_DIR honored ────────────────

class TestKnowledgeDirIsolation:
    def test_config_honors_ai_kos_knowledge_dir(self, monkeypatch, tmp_path):
        import ai_kos.config as cfg
        monkeypatch.setenv("AI_KOS_KNOWLEDGE_DIR", str(tmp_path))
        cfg._config = None
        try:
            assert cfg.load()["paths"]["knowledge_dir"] == str(tmp_path)
            # TaskManager resolves its DB inside the isolated dir — never the
            # production knowledge/future_tasks.db.
            from ai_kos.tasks import TaskManager
            tm = TaskManager()
            assert Path(tm._db_path) == tmp_path / "future_tasks.db"
        finally:
            cfg._config = None
            monkeypatch.delenv("AI_KOS_KNOWLEDGE_DIR")

    def test_task_queue_resolves_db_inside_knowledge_dir(self, monkeypatch, tmp_path):
        import ai_kos.config as cfg
        monkeypatch.setenv("AI_KOS_KNOWLEDGE_DIR", str(tmp_path))
        cfg._config = None
        try:
            from ai_kos.taskqueue import TaskQueue
            assert TaskQueue()._db_path == str(tmp_path / "taskqueue.db")
        finally:
            cfg._config = None
            monkeypatch.delenv("AI_KOS_KNOWLEDGE_DIR")


# ── Fix 5: side-effect log wired into execute + persisted ───────────────

class TestSideEffectLog:
    @pytest.fixture
    def worker(self, tmp_path):
        w = Worker("t_abc123", board=BOARD, workdir=tmp_path, author="tester")
        w.claimed = True
        return w

    def _ok_run(self, cmd="echo hi"):
        return lambda c, timeout=120: {"exit_code": 0, "stdout": "hi", "stderr": ""}

    def test_execute_effect_logged_after_success(self, worker):
        with patch("ai_kos.atq_worker._run", side_effect=self._ok_run()):
            with patch.object(worker, "comment", return_value=""):
                with patch.object(worker, "heartbeat", return_value=True):
                    assert worker.run(cmd="echo hi") == 0
        assert any(e["kind"] == "execute" and e["detail"] == "echo hi"
                   for e in worker.side_effect_log), (
            "the execute path must log its side effect (was decorative)")

    def test_execute_not_logged_when_command_fails(self, worker):
        def fail(cmd, timeout=120):
            return {"exit_code": 1, "stdout": "", "stderr": "boom"}
        with patch("ai_kos.atq_worker._run", side_effect=fail):
            with patch.object(worker, "comment", return_value=""):
                with patch.object(worker, "heartbeat", return_value=True):
                    with patch.object(worker, "block", return_value="BLOCKED"):
                        rc = worker.run(cmd="false")
        assert rc == 1
        assert not any(e["kind"] == "execute" for e in worker.side_effect_log)

    def test_retry_skips_execute_same_worker(self, worker):
        """Fix 5 regression: executing twice must not double-execute."""
        comments = []
        with patch("ai_kos.atq_worker._run", side_effect=self._ok_run()) as r:
            with patch.object(worker, "comment", side_effect=lambda b: comments.append(b)):
                with patch.object(worker, "heartbeat", return_value=True):
                    assert worker.run(cmd="echo hi") == 0
                    assert worker.run(cmd="echo hi") == 0
        bash_calls = [c for c in r.call_args_list if c.args[0][0] == "bash"]
        assert len(bash_calls) == 1, "retry re-executed an applied side effect"
        assert any("skipping already-applied" in c for c in comments)

    def test_crash_restart_skips_execute_from_persisted_log(self, tmp_path):
        """A fresh Worker (crash + re-claim, same workspace) must skip effects
        the previous run persisted — at-least-once across processes."""
        w1 = Worker("t_abc123", board=BOARD, workdir=tmp_path)
        w1.claimed = True
        with patch("ai_kos.atq_worker._run", side_effect=self._ok_run()):
            with patch.object(w1, "comment", return_value=""):
                with patch.object(w1, "heartbeat", return_value=True):
                    assert w1.run(cmd="echo hi") == 0
        log_file = tmp_path / "t_abc123-side-effects.json"
        assert log_file.exists(), "side-effect log must persist to the workspace"

        w2 = Worker("t_abc123", board=BOARD, workdir=tmp_path)  # crash + re-claim
        w2.claimed = True
        with patch("ai_kos.atq_worker._run", side_effect=self._ok_run()) as r:
            with patch.object(w2, "comment", return_value=""):
                with patch.object(w2, "heartbeat", return_value=True):
                    assert w2.run(cmd="echo hi") == 0
        bash_calls = [c for c in r.call_args_list if c.args[0][0] == "bash"]
        assert not bash_calls, "re-dispatched task must not re-run the side effect"
