"""AI-KOS TaskQueue — SQLite-backed priority queue for inbox ingestion.

Adopts Cloudflare Queues' producer/consumer pattern:
- Files dropped in inbox/ are enqueued as tasks
- Worker dequeues → extract → classify → create article
- Failed tasks go to dead-letter queue with retry metadata
- Parallel processing via ThreadPoolExecutor

Uses the existing AI-KOS SQLite database — no new infrastructure.
"""

import logging
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ai_kos.config import get

logger = logging.getLogger("ai-kos.taskqueue")

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_MAX_RETRIES = 3
DEFAULT_WORKERS = 3
DEFAULT_RETRY_DELAY = 2  # seconds
TABLE_NAME = "tasks"


# ── Task Model ───────────────────────────────────────────────────────────────

@dataclass
class Task:
    """A single task in the ingestion queue."""
    id: Optional[int] = None
    filepath: str = ""
    priority: int = 0          # lower = higher priority
    status: str = "pending"    # pending | processing | completed | dead_letter
    attempts: int = 0
    max_retries: int = DEFAULT_MAX_RETRIES
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_error: Optional[str] = None
    result: Optional[str] = None  # created article slug


# ── TaskQueue ────────────────────────────────────────────────────────────────

class TaskQueue:
    """SQLite-backed priority queue for AI-KOS inbox processing.

    Usage:
        queue = TaskQueue()
        queue.enqueue("/path/to/file.pdf")
        queue.enqueue_many(["/path/a.md", "/path/b.docx"])

        def process(task: Task) -> str:
            from ai_kos.ingestion import extract
            result = extract(task.filepath)
            return result.get("slug", "processed")

        queue.process_all(handler=process)
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or self._default_db_path()
        self._lock = threading.Lock()
        self._init_db()

    def _default_db_path(self) -> str:
        knowledge_dir = get("paths", "knowledge_dir", default="knowledge")
        return str(Path(knowledge_dir) / "taskqueue.db")

    def _init_db(self):
        """Create tasks table if not exists."""
        with self._get_conn() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT {DEFAULT_MAX_RETRIES},
                    created_at TEXT,
                    updated_at TEXT,
                    last_error TEXT,
                    result TEXT
                )
            """)
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
                ON {TABLE_NAME}(status, priority, created_at)
            """)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def enqueue(self, filepath: str, priority: int = 0) -> Task:
        """Add a file to the ingestion queue.

        Args:
            filepath: Absolute path to the file
            priority: Lower number = higher priority (0 is default/highest)

        Returns:
            The created Task
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                f"INSERT INTO {TABLE_NAME} (filepath, priority, status, created_at, updated_at) "
                "VALUES (?, ?, 'pending', ?, ?)",
                (filepath, priority, now, now),
            )
            conn.commit()
            task_id = cursor.lastrowid

        return Task(
            id=task_id,
            filepath=filepath,
            priority=priority,
            status="pending",
            created_at=now,
            updated_at=now,
        )

    def enqueue_many(self, filepaths: List[str], priority: int = 0) -> List[Task]:
        """Add multiple files to the queue."""
        return [self.enqueue(fp, priority) for fp in filepaths]

    def dequeue(self) -> Optional[Task]:
        """Get the next pending task (highest priority, oldest first). Marks as processing."""
        with self._lock:
            with self._get_conn() as conn:
                row = conn.execute(
                    f"SELECT * FROM {TABLE_NAME} "
                    "WHERE status = 'pending' "
                    "ORDER BY priority ASC, created_at ASC "
                    "LIMIT 1"
                ).fetchone()

                if row is None:
                    return None

                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    f"UPDATE {TABLE_NAME} SET status = 'processing', updated_at = ?, attempts = attempts + 1 "
                    "WHERE id = ?",
                    (now, row["id"]),
                )
                conn.commit()

                return Task(
                    id=row["id"],
                    filepath=row["filepath"],
                    priority=row["priority"],
                    status="processing",
                    attempts=row["attempts"] + 1,
                    max_retries=row["max_retries"],
                    created_at=row["created_at"],
                    updated_at=now,
                )

    def complete(self, task_id: int, result: str = "") -> None:
        """Mark a task as completed."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE {TABLE_NAME} SET status = 'completed', updated_at = ?, result = ? "
                "WHERE id = ?",
                (now, result, task_id),
            )
            conn.commit()

    def fail(self, task_id: int, error: str) -> str:
        """Mark a task as failed. If retries remain, reset to pending. Otherwise, dead_letter.

        Returns the new status ('pending' or 'dead_letter').
        """
        with self._get_conn() as conn:
            row = conn.execute(
                f"SELECT attempts, max_retries FROM {TABLE_NAME} WHERE id = ?",
                (task_id,),
            ).fetchone()

            if row is None:
                return "unknown"

            now = datetime.now(timezone.utc).isoformat()
            if row["attempts"] >= row["max_retries"]:
                conn.execute(
                    f"UPDATE {TABLE_NAME} SET status = 'dead_letter', updated_at = ?, last_error = ? "
                    "WHERE id = ?",
                    (now, error, task_id),
                )
                conn.commit()
                return "dead_letter"
            else:
                # Reset to pending for retry with backoff delay
                delay = DEFAULT_RETRY_DELAY * (2 ** (row["attempts"] - 1))
                retry_at = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    f"UPDATE {TABLE_NAME} SET status = 'pending', updated_at = ?, last_error = ? "
                    "WHERE id = ?",
                    (now, error, task_id),
                )
                conn.commit()
                # Apply backoff — only re-dequeue after delay
                if delay > 0:
                    time.sleep(min(delay, 60))  # Cap at 60s
                return "pending"

    def process_one(self, task: Task, handler: Callable[[Task], Optional[str]]) -> bool:
        """Process a single task with the given handler.

        Args:
            task: The task to process
            handler: Callable that takes a Task and returns a result string or None

        Returns:
            True if successful, False if failed
        """
        assert task.id is not None, "Task must have a database ID"
        try:
            result = handler(task)
            self.complete(task.id, result or "processed")
            logger.info(f"TaskQueue: completed task {task.id}: {task.filepath}")
            return True
        except Exception as e:
            logger.warning(f"TaskQueue: task {task.id} failed: {e}")
            new_status = self.fail(task.id, str(e))
            if new_status == "dead_letter":
                logger.error(f"TaskQueue: task {task.id} moved to dead letter: {task.filepath}")
            return False

    def process_all(
        self,
        handler: Callable[[Task], Optional[str]],
        max_workers: int = DEFAULT_WORKERS,
    ) -> Dict[str, int]:
        """Process all pending tasks using a thread pool.

        Args:
            handler: Callable that takes a Task and returns result string or None
            max_workers: Number of worker threads

        Returns:
            Dict with 'completed', 'failed', 'dead_letter' counts
        """
        counts = {"completed": 0, "failed": 0, "dead_letter": 0}

        # Collect all pending tasks
        tasks = []
        while True:
            task = self.dequeue()
            if task is None:
                break
            tasks.append(task)

        if not tasks:
            return counts

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.process_one, task, handler): task for task in tasks}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    success = future.result()
                    if success:
                        counts["completed"] += 1
                    else:
                        # Check if it became dead_letter
                        with self._get_conn() as conn:
                            row = conn.execute(
                                f"SELECT status FROM {TABLE_NAME} WHERE id = ?",
                                (task.id,),
                            ).fetchone()
                            if row and row["status"] == "dead_letter":
                                counts["dead_letter"] += 1
                            else:
                                counts["failed"] += 1
                except Exception as e:
                    logger.error(f"TaskQueue: unexpected error for task {task.id}: {e}")
                    counts["failed"] += 1

        logger.info(f"TaskQueue: processed {len(tasks)} tasks — {counts}")
        return counts

    def scan_inbox(self, inbox_dir: Optional[str] = None) -> int:
        """Scan the inbox directory and enqueue all files not already queued.

        Returns: number of new files enqueued.
        """
        inbox = Path(inbox_dir) if inbox_dir else Path(get("paths", "inbox_dir", default="inbox"))
        if not inbox.exists():
            return 0

        # Get already-queued filepaths
        with self._get_conn() as conn:
            existing = set(
                row[0] for row in conn.execute(
                    f"SELECT filepath FROM {TABLE_NAME} WHERE status IN ('pending', 'processing')"
                ).fetchall()
            )

        count = 0
        for f in inbox.iterdir():
            if f.is_file() and str(f) not in existing:
                self.enqueue(str(f))
                count += 1

        if count:
            logger.info(f"TaskQueue: enqueued {count} new files from inbox")
        return count

    def stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        with self._get_conn() as conn:
            statuses = conn.execute(
                f"SELECT status, COUNT(*) as cnt FROM {TABLE_NAME} GROUP BY status"
            ).fetchall()
        return {row["status"]: row["cnt"] for row in statuses}

    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """List tasks, optionally filtered by status."""
        with self._get_conn() as conn:
            if status:
                rows = conn.execute(
                    f"SELECT * FROM {TABLE_NAME} WHERE status = ? ORDER BY priority ASC, created_at ASC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT * FROM {TABLE_NAME} ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()

        return [dict(row) for row in rows]

    def clear_completed(self) -> int:
        """Remove completed tasks from the queue. Returns count removed."""
        with self._get_conn() as conn:
            cursor = conn.execute(f"DELETE FROM {TABLE_NAME} WHERE status = 'completed'")
            conn.commit()
            return cursor.rowcount

    def retry_dead_letters(self) -> int:
        """Move dead-letter tasks back to pending with reset attempts. Returns count."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                f"UPDATE {TABLE_NAME} SET status = 'pending', attempts = 0, last_error = NULL "
                "WHERE status = 'dead_letter'"
            )
            conn.commit()
            return cursor.rowcount
