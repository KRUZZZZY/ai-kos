"""ATQ queue manager tests — unit + integration (moved from scratch workspace,
fixture bug fixed: file-backed DB instead of shared-memory URI)."""

"""Shared schema + fixtures for the ATQ queue manager tests."""

import pytest

SCHEMA = """
CREATE TABLE tasks (
    id                   TEXT PRIMARY KEY,
    title                TEXT NOT NULL,
    body                 TEXT,
    assignee             TEXT,
    status               TEXT NOT NULL,
    priority             INTEGER DEFAULT 0,
    created_by           TEXT,
    created_at           INTEGER NOT NULL,
    started_at           INTEGER,
    completed_at         INTEGER,
    workspace_kind       TEXT NOT NULL DEFAULT 'scratch',
    workspace_path       TEXT,
    branch_name          TEXT,
    project_id           TEXT,
    claim_lock           TEXT,
    claim_expires        INTEGER,
    tenant               TEXT,
    result               TEXT,
    idempotency_key      TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    worker_pid           INTEGER,
    last_failure_error   TEXT,
    max_runtime_seconds  INTEGER,
    last_heartbeat_at    INTEGER,
    current_run_id       INTEGER,
    workflow_template_id TEXT,
    goal_mode            INTEGER DEFAULT 0,
    goal_max_turns       INTEGER,
    enabled_toolsets     TEXT,
    workdir              TEXT
);

CREATE TABLE task_runs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id             TEXT NOT NULL,
    profile             TEXT,
    step_key            TEXT,
    status              TEXT NOT NULL,
    claim_lock          TEXT,
    claim_expires       INTEGER,
    worker_pid          INTEGER,
    max_runtime_seconds INTEGER,
    last_heartbeat_at   INTEGER,
    started_at          INTEGER NOT NULL,
    ended_at            INTEGER,
    outcome             TEXT,
    summary             TEXT,
    metadata            TEXT,
    error               TEXT
);

CREATE TABLE task_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    TEXT NOT NULL,
    run_id     INTEGER,
    kind       TEXT NOT NULL,
    payload    TEXT,
    created_at INTEGER NOT NULL
);
"""


"""Unit tests for the ATQ queue manager (in-memory SQLite)."""

import sqlite3
import threading
import time

import pytest

from ai_kos.atq_queue_manager import QueueManager, QueueConfig, TASK_STATUSES



@pytest.fixture
def qm(tmp_path):
    """A QueueManager backed by a real on-disk SQLite file.

    NOTE: the previous shared-memory URI (``file:atq-test?mode=memory&cache=
    shared``) was a two-fold footgun: (1) QueueManager._conn() connects without
    ``uri=True``, so the URI string was treated as a literal FILENAME — a
    different, empty database; (2) closing the fixture's last connection
    destroyed the shared-memory DB. File-backed DBs sidestep both failure
    modes (connection lifecycle is irrelevant).
    """
    db_path = str(tmp_path / "atq-test.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return QueueManager(db_path)


def _insert_task(qm, task_id, status="ready", priority=0, assignee=None,
                 created_at=None, consecutive_failures=0,
                 claim_lock=None, claim_expires=None,
                 last_heartbeat_at=None, current_run_id=None, title=None):
    now = int(time.time())
    conn = qm._conn()
    try:
        conn.execute(
            "INSERT INTO tasks (id, title, assignee, status, priority, created_at, "
            "consecutive_failures, claim_lock, claim_expires, last_heartbeat_at, "
            "current_run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, title or task_id, assignee, status, priority,
             created_at if created_at is not None else now,
             consecutive_failures, claim_lock, claim_expires,
             last_heartbeat_at, current_run_id),
        )
        conn.commit()
    finally:
        conn.close()


def _status(qm, task_id):
    conn = qm._conn()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _run(qm, run_id):
    conn = qm._conn()
    try:
        row = conn.execute("SELECT * FROM task_runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Atomic claim
# --------------------------------------------------------------------------- #
def test_atomic_claim_single_winner(qm):
    _insert_task(qm, "t1")

    results = []
    lock = threading.Lock()

    def claim(worker):
        rid = qm._claim_task("t1", worker)
        with lock:
            results.append((worker, rid))

    threads = [threading.Thread(target=claim, args=(f"w{i}",)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    winners = [rid for (w, rid) in results if rid is not None]
    assert len(winners) == 1, f"expected exactly one winner, got {results}"

    task = _status(qm, "t1")
    assert task["status"] == "running"
    assert task["current_run_id"] == winners[0]
    assert task["claim_lock"] is not None


def test_claim_returns_none_when_not_ready(qm):
    _insert_task(qm, "t1", status="running")
    assert qm._claim_task("t1", "w1") is None


# --------------------------------------------------------------------------- #
# Lease expiry / reaping
# --------------------------------------------------------------------------- #
def test_lease_expiry_reap(qm):
    now = int(time.time())
    _insert_task(qm, "t1", status="running", claim_lock="w1",
                 claim_expires=now - 100, last_heartbeat_at=now - 1,
                 consecutive_failures=1)
    # attach a current run
    conn = qm._conn()
    conn.execute("INSERT INTO task_runs (task_id, status, started_at) VALUES ('t1','running',?)", (now - 200,))
    run_id = conn.execute("SELECT id FROM task_runs WHERE task_id='t1'").fetchone()["id"]
    conn.execute("UPDATE tasks SET current_run_id = ? WHERE id='t1'", (run_id,))
    conn.commit()
    conn.close()

    reaped = qm._reap_stalled()
    assert reaped == ["t1"]

    task = _status(qm, "t1")
    assert task["status"] == "ready"
    assert task["claim_lock"] is None
    assert task["consecutive_failures"] == 2
    assert task["current_run_id"] is None

    run = _run(qm, run_id)
    assert run["outcome"] == "reclaimed"


def test_reap_respects_active_heartbeat(qm):
    now = int(time.time())
    _insert_task(qm, "t1", status="running", claim_lock="w1",
                 claim_expires=now + 1000, last_heartbeat_at=now, consecutive_failures=0)

    reaped = qm._reap_stalled()
    assert reaped == []
    assert _status(qm, "t1")["status"] == "running"


def test_reap_stale_no_heartbeat(qm):
    now = int(time.time())
    # lease still valid, but no heartbeat within stale_timeout (14400s default)
    _insert_task(qm, "t1", status="running", claim_lock="w1",
                 claim_expires=now + 1000, last_heartbeat_at=now - 20000)

    reaped = qm._reap_stalled()
    assert reaped == ["t1"]
    assert _status(qm, "t1")["status"] == "ready"


# --------------------------------------------------------------------------- #
# Dead-lettering
# --------------------------------------------------------------------------- #
def test_dead_letter_after_max_attempts(qm):
    _insert_task(qm, "t1", status="running", consecutive_failures=3)
    qm.config.max_attempts = 3

    assert qm._dead_letter("t1", "too many failures") is True
    assert _status(qm, "t1")["status"] == "dead-lettered"

    # The event was recorded.
    conn = qm._conn()
    ev = conn.execute(
        "SELECT kind FROM task_events WHERE task_id='t1' AND kind='dead-lettered'"
    ).fetchone()
    conn.close()
    assert ev is not None


def test_dead_letter_respects_threshold(qm):
    _insert_task(qm, "t1", status="running", consecutive_failures=2)
    qm.config.max_attempts = 3

    assert qm._dead_letter("t1", "not yet") is False
    assert _status(qm, "t1")["status"] == "running"


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
def test_dispatch_priority_order(qm):
    # lower priority number = higher priority
    _insert_task(qm, "low", priority=10, created_at=100)
    _insert_task(qm, "mid", priority=5, created_at=200)
    _insert_task(qm, "high", priority=1, created_at=300)

    dispatched = qm._dispatch_ready(available_workers=3)
    order = [d["task_id"] for d in dispatched]
    assert order == ["high", "mid", "low"]


def test_dispatch_respects_concurrent_cap(qm):
    for i in range(20):
        _insert_task(qm, f"t{i}", priority=0)
    qm.config.max_concurrent_workers = 5

    dispatched = qm._dispatch_ready(available_workers=5)
    assert len(dispatched) == 5

    running = _count_status(qm, "running")
    assert running == 5


def _count_status(qm, status):
    conn = qm._conn()
    try:
        return conn.execute("SELECT COUNT(*) c FROM tasks WHERE status=?", (status,)).fetchone()["c"]
    finally:
        conn.close()


def test_dispatch_skips_already_running(qm):
    _insert_task(qm, "t1", status="running")
    _insert_task(qm, "t2")

    dispatched = qm._dispatch_ready(available_workers=2)
    assert [d["task_id"] for d in dispatched] == ["t2"]


# --------------------------------------------------------------------------- #
# Heartbeat
# --------------------------------------------------------------------------- #
def test_heartbeat_extends_lease(qm):
    _insert_task(qm, "t1")
    run_id = qm._claim_task("t1", "w1")

    before = _status(qm, "t1")["claim_expires"]
    # Sleep >1s so the heartbeat lands in a later wall-clock second than the
    # claim (claim_expires is in integer seconds — 0.05s was flaky).
    time.sleep(1.1)
    assert qm.heartbeat("t1", run_id) is True

    after = _status(qm, "t1")["claim_expires"]
    assert after > before

    run = _run(qm, run_id)
    assert run["claim_expires"] == after


def test_heartbeat_rejects_wrong_run(qm):
    _insert_task(qm, "t1")
    run_id = qm._claim_task("t1", "w1")
    assert qm.heartbeat("t1", run_id + 999) is False


# --------------------------------------------------------------------------- #
# Finish run
# --------------------------------------------------------------------------- #
def test_finish_run_success(qm):
    _insert_task(qm, "t1")
    run_id = qm._claim_task("t1", "w1")

    assert qm._finish_run("t1", run_id, "completed", "all good") is True
    assert _status(qm, "t1")["status"] == "done"

    run = _run(qm, run_id)
    assert run["outcome"] == "completed"


def test_finish_run_failure_requeues_until_dead_letter(qm):
    _insert_task(qm, "t1")
    qm.config.max_attempts = 3

    # Crash three times; after the 3rd it should dead-letter.
    for i in range(1, 4):
        run_id = qm._claim_task("t1", f"w{i}")
        qm._finish_run("t1", run_id, "crashed", f"crash {i}")
        task = _status(qm, "t1")
        if i < 3:
            assert task["status"] == "ready", f"attempt {i} should requeue"
            assert task["consecutive_failures"] == i
        else:
            assert task["status"] == "dead-lettered"
            assert task["consecutive_failures"] == 3


# --------------------------------------------------------------------------- #
# Run report
# --------------------------------------------------------------------------- #
def test_run_report_counts(qm):
    # task A completes
    _insert_task(qm, "A", assignee="alice")
    rid_a = qm._claim_task("A", "w1")
    qm._finish_run("A", rid_a, "completed", "ok")

    # task B crashes once, gets re-dispatched and completes
    _insert_task(qm, "B", assignee="bob")
    rid_b1 = qm._claim_task("B", "w2")
    qm._finish_run("B", rid_b1, "crashed", "boom")
    rid_b2 = qm._claim_task("B", "w3")
    qm._finish_run("B", rid_b2, "completed", "recovered")

    # task C dead-letters
    _insert_task(qm, "C", assignee="alice", consecutive_failures=3)
    qm._dead_letter("C", "permanent failure")

    report = qm.get_run_report()

    assert report["outcomes"].get("completed") == 2
    assert report["outcomes"].get("crashed") == 1
    assert report["total_dispatched"] == 3
    assert report["dead_lettered"] == 1

    # retry distribution: A=0 retries, B=1 retry, C=0 runs in window
    # (dead-lettered via _dead_letter has no run rows) — 2 tasks with 0 retries,
    # 1 task with 1 retry.
    assert report["retry_distribution"].get("0") == 1   # A
    assert report["retry_distribution"].get("1") == 1   # B
    # C has no run rows because it was dead-lettered directly.

    assert report["per_assignee"]["alice"]["completed"] == 1
    assert report["per_assignee"]["bob"]["completed"] == 1

    assert report["queue_state"].get("done") == 2
    assert report["queue_state"].get("dead-lettered") == 1


def test_run_report_since_filters(qm):
    now = int(time.time())
    _insert_task(qm, "old", created_at=now - 100000)
    rid = qm._claim_task("old", "w1")

    # backdate the run so it falls outside the window
    conn = qm._conn()
    conn.execute("UPDATE task_runs SET started_at = ? WHERE id = ?", (now - 100000, rid))
    conn.commit()
    conn.close()
    qm._finish_run("old", rid, "completed", "old")

    _insert_task(qm, "recent")
    rid2 = qm._claim_task("recent", "w2")
    qm._finish_run("recent", rid2, "completed", "recent")

    report = qm.get_run_report(since=now - 5000)
    assert report["total_dispatched"] == 1
    assert report["outcomes"].get("completed") == 1

"""Integration tests for the ATQ queue manager against a real SQLite file."""

import sqlite3
import threading
import time

import pytest

from ai_kos.atq_queue_manager import QueueManager, QueueConfig



@pytest.fixture
def qm_file(tmp_path):
    """QueueManager against a real on-disk SQLite file."""
    db_path = str(tmp_path / "atq.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return QueueManager(db_path)


def _status(qm, task_id):
    conn = qm._conn()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def test_end_to_end_crash_and_recover(qm_file):
    """A task that crashes is re-dispatched and eventually completes."""
    qm = qm_file
    qm.config.max_attempts = 3

    # A succeeds first try, B crashes twice then succeeds, C is blocked forever.
    _insert_task(qm, "A", assignee="alice")
    _insert_task(qm, "B", assignee="bob")
    _insert_task(qm, "C", assignee="carol")

    # 1) Dispatch picks up tasks up to the worker budget.
    dispatched = qm._dispatch_ready(available_workers=2)
    task_ids = {d["task_id"] for d in dispatched}
    assert "A" in task_ids and "B" in task_ids
    assert "C" not in task_ids  # only 2 workers available
    assert len(dispatched) == 2

    # 2) Finish A successfully.
    a_dispatch = next(d for d in dispatched if d["task_id"] == "A")
    assert qm._finish_run("A", a_dispatch["run_id"], "completed", "done") is True
    assert _status(qm, "A")["status"] == "done"

    # 3) Simulate B crashing twice — it should be re-dispatched each time.
    b_dispatch = next(d for d in dispatched if d["task_id"] == "B")
    for i in range(2):
        qm._finish_run("B", b_dispatch["run_id"], "crashed", f"crash {i + 1}")
        assert _status(qm, "B")["status"] == "ready"  # re-queued (still under limit)
        # reclaim it for the next attempt
        b_dispatch["run_id"] = qm._claim_task("B", "bob")

    # 4) Final attempt succeeds.
    assert qm._finish_run("B", b_dispatch["run_id"], "completed", "recovered") is True
    assert _status(qm, "B")["status"] == "done"
    assert _status(qm, "B")["consecutive_failures"] == 2  # retains history

    # 5) C is still ready (was never dispatched due to budget).
    assert _status(qm, "C")["status"] == "ready"

    # 6) Finish C blocked — it should go to blocked state, not dead-letter.
    c_run = qm._claim_task("C", "carol")
    qm._finish_run("C", c_run, "blocked", "waiting on human")
    assert _status(qm, "C")["status"] == "blocked"

    # 7) Run report reflects everything.
    report = qm.get_run_report()
    assert report["outcomes"].get("completed") == 2
    assert report["outcomes"].get("crashed") == 2
    assert report["outcomes"].get("blocked") == 1
    assert report["dead_lettered"] == 0


def test_task_crashes_until_dead_letter(qm_file):
    qm = qm_file
    qm.config.max_attempts = 3

    _insert_task(qm, "A")
    for i in range(3):
        run_id = qm._claim_task("A", f"w{i}")
        qm._finish_run("A", run_id, "crashed", f"boom {i}")
        if i < 2:
            assert _status(qm, "A")["status"] == "ready"

    assert _status(qm, "A")["status"] == "dead-lettered"
    assert qm.get_run_report()["dead_lettered"] == 1


def test_no_data_clobbering(qm_file):
    """Two workers racing for the same ready task: exactly one wins."""
    qm = qm_file
    _insert_task(qm, "shared")

    results = []
    barrier = threading.Barrier(2)

    def worker(wid):
        barrier.wait()  # maximise contention
        results.append((wid, qm._claim_task("shared", wid)))

    ts = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    winners = [rid for (wid, rid) in results if rid is not None]
    assert len(winners) == 1

    task = _status(qm, "shared")
    assert task["status"] == "running"
    assert task["current_run_id"] == winners[0]

    # Only one run row and one claimed event exist.
    conn = qm._conn()
    runs = conn.execute("SELECT COUNT(*) c FROM task_runs WHERE task_id='shared'").fetchone()["c"]
    events = conn.execute(
        "SELECT COUNT(*) c FROM task_events WHERE task_id='shared' AND kind='claimed'"
    ).fetchone()["c"]
    conn.close()
    assert runs == 1
    assert events == 1
