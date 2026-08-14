"""
ATQ (Agent Task Queue) queue manager.

Lease-based dispatch, stalled-task reaping, dead-lettering, and run reports
over a SQLite-backed task database. No external dependencies beyond the
Python standard library.

The schema consumed here matches the Hermes kanban DB (``tasks``,
``task_runs``, ``task_events``). This module is intentionally independent of
that package so it can be tested against an in-memory SQLite database.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import sqlite3
import json
import time
import threading
import logging

logger = logging.getLogger(__name__)

# Task states recognised by the queue. ``dead-lettered`` is a terminal state
# reached after ``max_attempts`` consecutive failures.
TASK_STATUSES = ["triage", "ready", "running", "blocked", "done", "dead-lettered"]

# Outcome values recorded on task_runs.outcome.
OUTCOME_COMPLETED = "completed"
OUTCOME_BLOCKED = "blocked"
OUTCOME_CRASHED = "crashed"
OUTCOME_TIMED_OUT = "timed_out"
OUTCOME_SPAWN_FAILED = "spawn_failed"
OUTCOME_GAVE_UP = "gave_up"
OUTCOME_RECLAIMED = "reclaimed"

# Event kinds recorded on task_events.kind.
EVENT_CREATED = "created"
EVENT_PROMOTED = "promoted"
EVENT_CLAIMED = "claimed"
EVENT_SPAWNED = "spawned"
EVENT_HEARTBEAT = "heartbeat"
EVENT_COMPLETED = "completed"
EVENT_BLOCKED = "blocked"
EVENT_CRASHED = "crashed"
EVENT_RECLAIMED = "reclaimed"
EVENT_DEAD_LETTERED = "dead-lettered"

# Success outcomes — when a run finishes with these the task is considered done.
_SUCCESS_OUTCOMES = {OUTCOME_COMPLETED}


@dataclass
class QueueConfig:
    """Runtime dispatch policy for the queue manager."""

    poll_interval: float = 5.0          # seconds between main-loop ticks
    lease_duration: int = 7200          # seconds a lease is valid (default 2h)
    max_attempts: int = 3               # consecutive failures before dead-letter
    stale_timeout: int = 3600           # reclaim when no heartbeat within this window
                                        # (MUST be < lease_duration so the heartbeat-
                                        # staleness reap can fire before lease expiry)
    max_concurrent_workers: int = 10    # global worker budget cap
    per_assignee_cap: int = 0           # max concurrent tasks per assignee (0 = unlimited)


class QueueManager:
    """Lease-based task dispatcher over a SQLite queue database.

    The manager is a low-level engine; it exposes explicit primitives
    (``claim``/``dispatch``/``reap``/``finish``/``heartbeat``) that a
    higher-level scheduler loop can drive. No built-in loop or
    ``run_forever`` convenience exists — drive the per-tick methods from
    your own scheduler.
    """

    def __init__(self, db_path: str, config: Optional[QueueConfig] = None):
        self.db_path = db_path
        self.config = config or QueueConfig()
        self._running = False
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ #
    # Connection handling
    # ------------------------------------------------------------------ #
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @staticmethod
    def _now() -> int:
        return int(time.time())

    # ------------------------------------------------------------------ #
    # Event recording
    # ------------------------------------------------------------------ #
    @staticmethod
    def _record_event(conn: sqlite3.Connection, task_id: str, kind: str,
                      run_id: Optional[int] = None, payload: Optional[dict] = None) -> None:
        conn.execute(
            "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (task_id, run_id, kind,
             json.dumps(payload) if payload is not None else None,
             QueueManager._now()),
        )

    # ------------------------------------------------------------------ #
    # Lease-based atomic claim
    # ------------------------------------------------------------------ #
    def _claim_task(self, task_id: str, worker_id: str) -> Optional[int]:
        """Claim a ready task atomically.

        A single conditional ``UPDATE`` guarantees only one winner per race;
        the run row and ``claimed`` event are written in the same transaction.
        Returns the new run id on success, or ``None`` if the task was already
        claimed / not claimable.
        """
        now = self._now()
        expires = now + self.config.lease_duration

        with self._lock:
            conn = self._conn()
            try:
                # 1) Atomically win the claim. Only a task that is ``ready``
                #    and has no active run can be claimed.
                cur = conn.execute(
                    "UPDATE tasks SET "
                    "  status = 'running', "
                    "  claim_lock = ?, "
                    "  claim_expires = ?, "
                    "  started_at = COALESCE(started_at, ?), "
                    "  last_heartbeat_at = ? "
                    "WHERE id = ? AND status = 'ready' AND current_run_id IS NULL",
                    (worker_id, expires, now, now, task_id),
                )
                if cur.rowcount == 0:
                    return None

                # 2) Create the run row (same transaction).
                cur = conn.execute(
                    "INSERT INTO task_runs (task_id, status, claim_lock, claim_expires, "
                    "  last_heartbeat_at, started_at) VALUES (?, 'running', ?, ?, ?, ?)",
                    (task_id, worker_id, expires, now, now),
                )
                run_id = cur.lastrowid

                # 3) Point the task at its current run.
                conn.execute(
                    "UPDATE tasks SET current_run_id = ? WHERE id = ?",
                    (run_id, task_id),
                )

                self._record_event(conn, task_id, EVENT_CLAIMED, run_id,
                                   {"worker_id": worker_id, "lease_duration": self.config.lease_duration})
                conn.commit()
                logger.info("claimed task %s (run %s, worker %s)", task_id, run_id, worker_id)
                return run_id
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    # Reaping stalled tasks
    # ------------------------------------------------------------------ #
    def _reap_stalled(self) -> List[str]:
        """Reclaim stalled/expired running tasks.

        A task is considered stalled when its lease has expired
        (``claim_expires < now``) OR it has not heartbeated within
        ``stale_timeout`` when a heartbeat was expected (a task that was never
        heartbeated is only reclaimed on lease expiry). Reaped tasks return to
        ``ready``, their consecutive-failure counter is incremented, and a
        ``reclaimed`` event is recorded.
        """
        now = self._now()
        stale_floor = now - self.config.stale_timeout

        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(
                    "SELECT id FROM tasks WHERE status = 'running' AND ("
                    "  claim_expires IS NOT NULL AND claim_expires < ? "
                    "  OR (last_heartbeat_at IS NOT NULL AND last_heartbeat_at < ?)"
                    ")",
                    (now, stale_floor),
                ).fetchall()

                reaped = []
                for row in rows:
                    task_id = row["id"]
                    conn.execute(
                        "UPDATE tasks SET status = 'ready', claim_lock = NULL, "
                        "  claim_expires = NULL, current_run_id = NULL, "
                        "  consecutive_failures = consecutive_failures + 1 "
                        "WHERE id = ?",
                        (task_id,),
                    )
                    # Mark the active run as reclaimed.
                    conn.execute(
                        "UPDATE task_runs SET status = 'reclaimed', "
                        "  outcome = ?, ended_at = ? "
                        "WHERE task_id = ? AND ended_at IS NULL",
                        (OUTCOME_RECLAIMED, now, task_id),
                    )
                    self._record_event(conn, task_id, EVENT_RECLAIMED,
                                       payload={"reason": "lease_expired_or_stale"})
                    reaped.append(task_id)

                conn.commit()
                for task_id in reaped:
                    logger.warning("reaped stalled task %s", task_id)
                return reaped
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    # Dead-lettering
    # ------------------------------------------------------------------ #
    def _dead_letter(self, task_id: str, reason: str) -> bool:
        """Move a failed task to dead-letter status.

        The task transitions only if its recorded ``consecutive_failures`` has
        reached ``max_attempts``. Returns True if the task was dead-lettered,
        False otherwise.
        """
        with self._lock:
            conn = self._conn()
            try:
                row = conn.execute(
                    "SELECT consecutive_failures FROM tasks WHERE id = ?",
                    (task_id,),
                ).fetchone()
                if row is None:
                    return False

                failures = row["consecutive_failures"]
                if failures < self.config.max_attempts:
                    return False

                conn.execute(
                    "UPDATE tasks SET status = 'dead-lettered', "
                    "  claim_lock = NULL, claim_expires = NULL, current_run_id = NULL, "
                    "  last_failure_error = ? WHERE id = ?",
                    (reason, task_id),
                )
                self._record_event(conn, task_id, EVENT_DEAD_LETTERED,
                                   payload={"reason": reason, "failures": failures})
                conn.commit()
                logger.error("dead-lettered task %s after %d failures: %s",
                             task_id, failures, reason)
                return True
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #
    def _dispatch_ready(self, available_workers: int) -> List[Dict]:
        """Claim and transition the highest-priority ready tasks.

        Tasks are selected in priority order (lowest number first, then oldest
        ``created_at``). Dispatch respects the global worker budget and the
        optional per-assignee cap. Returns a list of dispatch records
        ``{task_id, worker_id, run_id, assignee, priority}``.
        """
        if available_workers <= 0:
            return []

        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(
                    "SELECT id, assignee, priority FROM tasks "
                    "WHERE status = 'ready' "
                    "ORDER BY priority ASC, created_at ASC",
                ).fetchall()

                dispatched = []
                per_assignee: Dict[str, int] = {}

                for row in rows:
                    if len(dispatched) >= available_workers:
                        break

                    task_id = row["id"]
                    assignee = row["assignee"] or ""
                    priority = row["priority"]

                    # Per-assignee cap check.
                    if self.config.per_assignee_cap > 0:
                        if per_assignee.get(assignee, 0) >= self.config.per_assignee_cap:
                            continue

                    # Count currently-running tasks for this assignee (defense
                    # in depth alongside the in-loop counter, in case another
                    # manager instance holds leases not seen here yet).
                    running = conn.execute(
                        "SELECT COUNT(*) AS c FROM tasks WHERE assignee = ? AND status = 'running'",
                        (assignee,),
                    ).fetchone()["c"]
                    if self.config.per_assignee_cap > 0 and running >= self.config.per_assignee_cap:
                        continue

                    worker_id = f"worker-{task_id}-{int(time.time() * 1000)}"
                    run_id = self._claim_task_locked(conn, task_id, worker_id)
                    if run_id is None:
                        continue  # lost a race; skip

                    per_assignee[assignee] = per_assignee.get(assignee, 0) + 1
                    dispatched.append({
                        "task_id": task_id,
                        "worker_id": worker_id,
                        "run_id": run_id,
                        "assignee": assignee,
                        "priority": priority,
                    })

                conn.commit()
                if dispatched:
                    logger.info("dispatched %d task(s)", len(dispatched))
                return dispatched
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _claim_task_locked(self, conn: sqlite3.Connection, task_id: str,
                           worker_id: str) -> Optional[int]:
        """Claim a task using an already-open connection (no lock re-entry)."""
        now = self._now()
        expires = now + self.config.lease_duration

        cur = conn.execute(
            "UPDATE tasks SET "
            "  status = 'running', "
            "  claim_lock = ?, "
            "  claim_expires = ?, "
            "  started_at = COALESCE(started_at, ?), "
            "  last_heartbeat_at = ? "
            "WHERE id = ? AND status = 'ready' AND current_run_id IS NULL",
            (worker_id, expires, now, now, task_id),
        )
        if cur.rowcount == 0:
            return None

        cur = conn.execute(
            "INSERT INTO task_runs (task_id, status, claim_lock, claim_expires, "
            "  last_heartbeat_at, started_at) VALUES (?, 'running', ?, ?, ?, ?)",
            (task_id, worker_id, expires, now, now),
        )
        run_id = cur.lastrowid

        conn.execute(
            "UPDATE tasks SET current_run_id = ? WHERE id = ?",
            (run_id, task_id),
        )

        self._record_event(conn, task_id, EVENT_CLAIMED, run_id,
                           {"worker_id": worker_id,
                            "lease_duration": self.config.lease_duration})
        return run_id

    # ------------------------------------------------------------------ #
    # Finish a run
    # ------------------------------------------------------------------ #
    def _finish_run(self, task_id: str, run_id: int, outcome: str,
                    summary: Optional[str] = None,
                    error: Optional[str] = None) -> bool:
        """Mark a run as finished and update the owning task.

        - ``completed`` (or any success outcome) → task ``done``.
        - failure outcomes → increment ``consecutive_failures``; if still under
          ``max_attempts`` reset the claim so the task is re-dispatchable,
          otherwise dead-letter it.

        Returns True if the transition was applied.
        """
        now = self._now()
        with self._lock:
            conn = self._conn()
            try:
                row = conn.execute(
                    "SELECT id FROM task_runs WHERE id = ? AND task_id = ? AND ended_at IS NULL",
                    (run_id, task_id),
                ).fetchone()
                if row is None:
                    # Already finished or run/task mismatch.
                    return False

                # Update the run.
                conn.execute(
                    "UPDATE task_runs SET status = ?, outcome = ?, ended_at = ?, "
                    "  summary = ?, error = ? WHERE id = ?",
                    (outcome, outcome, now, summary, error, run_id),
                )

                if outcome in _SUCCESS_OUTCOMES:
                    conn.execute(
                        "UPDATE tasks SET status = 'done', completed_at = ?, "
                        "  claim_lock = NULL, claim_expires = NULL, current_run_id = NULL "
                        "WHERE id = ?",
                        (now, task_id),
                    )
                    self._record_event(conn, task_id, EVENT_COMPLETED, run_id,
                                       {"outcome": outcome, "summary": summary})
                    conn.commit()
                    logger.info("task %s completed (run %s)", task_id, run_id)
                    return True

                # Failure path.
                conn.execute(
                    "UPDATE tasks SET consecutive_failures = consecutive_failures + 1, "
                    "  last_failure_error = ? WHERE id = ?",
                    (error or outcome, task_id),
                )
                failures = conn.execute(
                    "SELECT consecutive_failures FROM tasks WHERE id = ?",
                    (task_id,),
                ).fetchone()["consecutive_failures"]

                kind = EVENT_BLOCKED if outcome == OUTCOME_BLOCKED else EVENT_CRASHED
                self._record_event(conn, task_id, kind, run_id,
                                   {"outcome": outcome, "summary": summary, "failures": failures})

                conn.commit()

                if outcome == OUTCOME_BLOCKED:
                    # Blocked tasks stay blocked for a human; not auto-requeued.
                    conn.execute(
                        "UPDATE tasks SET status = 'blocked' WHERE id = ?",
                        (task_id,),
                    )
                    conn.commit()
                    return True

                if failures >= self.config.max_attempts:
                    return self._dead_letter(task_id, error or outcome)
                else:
                    # Reset the claim so it becomes dispatchable again.
                    conn.execute(
                        "UPDATE tasks SET status = 'ready', claim_lock = NULL, "
                        "  claim_expires = NULL, current_run_id = NULL WHERE id = ?",
                        (task_id,),
                    )
                    conn.commit()
                    logger.info("task %s failure %d/%d, re-queued",
                                task_id, failures, self.config.max_attempts)
                    return True
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    # Heartbeat
    # ------------------------------------------------------------------ #
    def heartbeat(self, task_id: str, run_id: int) -> bool:
        """Worker check-in: extend the lease and update heartbeat timestamp.

        Returns True if the heartbeat was accepted (task is running and the
        run id is the task's current run), False otherwise.
        """
        now = self._now()
        expires = now + self.config.lease_duration
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    "UPDATE tasks SET claim_expires = ?, last_heartbeat_at = ? "
                    "WHERE id = ? AND status = 'running' AND current_run_id = ?",
                    (expires, now, task_id, run_id),
                )
                if cur.rowcount == 0:
                    return False

                conn.execute(
                    "UPDATE task_runs SET claim_expires = ?, last_heartbeat_at = ? "
                    "WHERE id = ?",
                    (expires, now, run_id),
                )
                self._record_event(conn, task_id, EVENT_HEARTBEAT, run_id,
                                   {"expires": expires})
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    # Run report
    # ------------------------------------------------------------------ #
    def get_run_report(self, since: Optional[int] = None) -> Dict:
        """Aggregate dispatch statistics over a time window.

        Returns counts of runs by outcome (completed / crashed / timed_out /
        reclaimed / dead-lettered), the retry distribution, total dispatched,
        and a per-assignee breakdown. ``since`` is a unix timestamp; when
        omitted, the full history is reported.
        """
        now = self._now()
        since = since if since is not None else 0

        with self._lock:
            conn = self._conn()
            try:
                # Outcome distribution from task_runs.
                outcome_rows = conn.execute(
                    "SELECT outcome, COUNT(*) AS c FROM task_runs "
                    "WHERE started_at >= ? AND outcome IS NOT NULL "
                    "GROUP BY outcome",
                    (since,),
                ).fetchall()

                by_outcome = {r["outcome"]: r["c"] for r in outcome_rows}

                # Total dispatched = runs started in window.
                total_dispatched = conn.execute(
                    "SELECT COUNT(*) AS c FROM task_runs WHERE started_at >= ?",
                    (since,),
                ).fetchone()["c"]

                # Dead-letter counts. Respect the report window: count the
                # dead-letter EVENTS since ``since``; full-history reports fall
                # back to the current-state task count (backward compatible).
                if since is None:
                    dead_letters = conn.execute(
                        "SELECT COUNT(*) AS c FROM tasks WHERE status = 'dead-lettered'",
                    ).fetchone()["c"]
                else:
                    dead_letters = conn.execute(
                        "SELECT COUNT(DISTINCT task_id) AS c FROM task_events "
                        "WHERE kind = 'dead-lettered' AND created_at >= ?",
                        (since,),
                    ).fetchone()["c"]

                # Retry distribution — how many tasks had N runs (retries = runs - 1).
                retry_rows = conn.execute(
                    "SELECT task_id, COUNT(*) AS runs FROM task_runs "
                    "WHERE started_at >= ? GROUP BY task_id",
                    (since,),
                ).fetchall()
                retry_distribution: Dict[str, int] = {}
                for r in retry_rows:
                    retries = r["runs"] - 1
                    bucket = str(retries) if retries <= 5 else "6+"
                    retry_distribution[bucket] = retry_distribution.get(bucket, 0) + 1

                # Per-assignee breakdown: task_runs carries the WORKER claim id
                # in profile; the task's assignee lives on tasks. Join through.
                assignee_rows = conn.execute(
                    "SELECT t.assignee, "
                    "  SUM(CASE WHEN r.outcome = 'completed' THEN 1 ELSE 0 END) AS completed, "
                    "  SUM(CASE WHEN r.outcome IN ('crashed','timed_out','reclaimed') THEN 1 ELSE 0 END) AS failed "
                    "FROM task_runs r JOIN tasks t ON t.id = r.task_id "
                    "WHERE r.started_at >= ? AND t.assignee IS NOT NULL "
                    "GROUP BY t.assignee",
                    (since,),
                ).fetchall()
                per_assignee = {
                    r["assignee"]: {"completed": r["completed"] or 0,
                                    "failed": r["failed"] or 0}
                    for r in assignee_rows
                }

                # Current queue state.
                status_rows = conn.execute(
                    "SELECT status, COUNT(*) AS c FROM tasks GROUP BY status",
                ).fetchall()
                queue_state = {r["status"]: r["c"] for r in status_rows}

                return {
                    "generated_at": now,
                    "since": since,
                    "total_dispatched": total_dispatched,
                    "outcomes": by_outcome,
                    "dead_lettered": dead_letters,
                    "retry_distribution": retry_distribution,
                    "per_assignee": per_assignee,
                    "queue_state": queue_state,
                }
            finally:
                conn.close()
