"""Tests for AI-KOS TaskQueue — SQLite priority queue for inbox ingestion."""

import os
import tempfile
import time
from pathlib import Path

import pytest

from ai_kos.taskqueue import (
    Task,
    TaskQueue,
    DEFAULT_MAX_RETRIES,
)


def _temp_queue_dir() -> str:
    return str(Path(tempfile.mkdtemp()) / "taskqueue.db")


class TestTask:
    def test_defaults(self):
        t = Task(filepath="/tmp/test.md")
        assert t.status == "pending"
        assert t.attempts == 0
        assert t.priority == 0
        assert t.max_retries == DEFAULT_MAX_RETRIES

    def test_custom_priority(self):
        t = Task(filepath="/tmp/test.md", priority=5)
        assert t.priority == 5


class TestTaskQueue:
    def test_enqueue_and_dequeue(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        t = q.enqueue("/tmp/test.md")
        assert t.id is not None
        assert t.status == "pending"

        t2 = q.dequeue()
        assert t2 is not None
        assert t2.id == t.id
        assert t2.status == "processing"
        assert t2.filepath == "/tmp/test.md"

    def test_dequeue_empty_returns_none(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        assert q.dequeue() is None

    def test_enqueue_many(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        paths = ["/tmp/a.md", "/tmp/b.md", "/tmp/c.md"]
        tasks = q.enqueue_many(paths)
        assert len(tasks) == 3
        assert all(t.id is not None for t in tasks)

    def test_priority_ordering(self):
        """Higher priority (lower number) tasks are dequeued first."""
        q = TaskQueue(db_path=_temp_queue_dir())
        q.enqueue("/tmp/low.md", priority=10)
        q.enqueue("/tmp/high.md", priority=0)
        q.enqueue("/tmp/med.md", priority=5)

        t1 = q.dequeue()
        assert t1.filepath == "/tmp/high.md"  # priority 0 first
        t2 = q.dequeue()
        assert t2.filepath == "/tmp/med.md"   # priority 5 second
        t3 = q.dequeue()
        assert t3.filepath == "/tmp/low.md"   # priority 10 last

    def test_complete(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        t = q.enqueue("/tmp/ok.md")
        q.dequeue()  # Mark as processing
        q.complete(t.id, "article-123")

        s = q.stats()
        assert s.get("completed", 0) == 1

    def test_fail_with_retries(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        t = q.enqueue("/tmp/retry.md", priority=0)
        q.dequeue()  # Mark as processing
        new_status = q.fail(t.id, "Temporary error")
        assert new_status == "pending"  # Still has retries

        # Should be dequeued again
        t2 = q.dequeue()
        assert t2 is not None
        assert t2.attempts == 2

    def test_fail_max_retries_to_dead_letter(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        t = q.enqueue("/tmp/dead.md", priority=0)

        for i in range(DEFAULT_MAX_RETRIES):
            task = q.dequeue()
            assert task is not None
            assert task.attempts == i + 1
            status = q.fail(task.id, f"Error {i+1}")
            if i < DEFAULT_MAX_RETRIES - 1:
                assert status == "pending"
            else:
                assert status == "dead_letter"

        # Should not be dequeued again
        assert q.dequeue() is None

        s = q.stats()
        assert s.get("dead_letter", 0) == 1

    def test_process_one_success(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        t = q.enqueue("/tmp/success.md")
        task = q.dequeue()

        def handler(task: Task):
            return "processed-ok"

        success = q.process_one(task, handler)
        assert success
        assert q.stats().get("completed", 0) == 1

    def test_process_one_failure_with_retry(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        t = q.enqueue("/tmp/flaky.md")
        task = q.dequeue()

        def handler(task: Task):
            raise ValueError("Flaky failure")

        success = q.process_one(task, handler)
        assert not success
        # Should be reset to pending (first failure, retries remain)
        s = q.stats()
        assert s.get("pending", 0) >= 1

    def test_process_all_with_threads(self):
        """Process multiple tasks with thread pool."""
        q = TaskQueue(db_path=_temp_queue_dir())

        # Create some test files
        tmpdir = tempfile.mkdtemp()
        files = []
        for i in range(10):
            fpath = os.path.join(tmpdir, f"test_{i}.txt")
            with open(fpath, "w") as f:
                f.write(f"Content {i}")
            files.append(fpath)

        q.enqueue_many(files)

        def handler(task: Task):
            return f"done-{Path(task.filepath).name}"

        counts = q.process_all(handler, max_workers=3)
        assert counts["completed"] == 10
        assert counts["failed"] == 0

    def test_process_all_with_mixed_failures(self):
        """Some tasks succeed, some fail permanently."""
        q = TaskQueue(db_path=_temp_queue_dir())

        tmpdir = tempfile.mkdtemp()
        files = []
        for i in range(5):
            fpath = os.path.join(tmpdir, f"test_{i}.txt")
            with open(fpath, "w") as f:
                f.write(f"Content {i}")
            files.append(fpath)

        q.enqueue_many(files)

        fail_count = [0]

        def handler(task: Task):
            name = Path(task.filepath).name
            if "test_0" in name or "test_1" in name:
                raise RuntimeError("Permanent failure")
            return f"done-{name}"

        # Run multiple times to exhaust retries on failing tasks
        for _ in range(DEFAULT_MAX_RETRIES):
            counts = q.process_all(handler, max_workers=2)

        final = q.stats()
        # 2 should be dead_letter, 3 completed
        assert final.get("dead_letter", 0) == 2
        assert final.get("completed", 0) == 3

    def test_scan_inbox(self, tmp_path):
        """Scan inbox directory and enqueue files."""
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "a.md").write_text("# Hello")
        (inbox / "b.pdf").write_text("dummy pdf")
        (inbox / "c.docx").write_text("dummy docx")

        q = TaskQueue(db_path=str(tmp_path / "taskqueue.db"))
        count = q.scan_inbox(inbox_dir=str(inbox))
        assert count == 3

        # Second scan should not duplicate
        count2 = q.scan_inbox(inbox_dir=str(inbox))
        assert count2 == 0

    def test_scan_inbox_skips_already_queued(self):
        inbox = Path(tempfile.mkdtemp()) / "inbox"
        inbox.mkdir()
        (inbox / "only.md").write_text("# Only")

        q = TaskQueue(db_path=_temp_queue_dir())
        q.enqueue(str(inbox / "only.md"))

        count = q.scan_inbox(inbox_dir=str(inbox))
        assert count == 0  # Already queued

    def test_scan_inbox_nonexistent(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        count = q.scan_inbox(inbox_dir="/tmp/does_not_exist_xyz")
        assert count == 0

    def test_stats(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        q.enqueue("/tmp/a.md")
        q.enqueue("/tmp/b.md")
        q.enqueue("/tmp/c.md")

        s = q.stats()
        assert s.get("pending", 0) == 3

        q.dequeue()
        s2 = q.stats()
        assert s2.get("processing", 0) == 1
        assert s2.get("pending", 0) == 2

    def test_list_tasks(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        q.enqueue("/tmp/x.md")
        q.enqueue("/tmp/y.md")

        tasks = q.list_tasks(status="pending")
        assert len(tasks) == 2
        assert tasks[0]["filepath"] in ("/tmp/x.md", "/tmp/y.md")

    def test_list_tasks_all(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        q.enqueue("/tmp/z.md")
        tasks = q.list_tasks()
        assert len(tasks) == 1

    def test_clear_completed(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        t = q.enqueue("/tmp/done.md")
        task = q.dequeue()
        q.complete(task.id, "done")

        assert q.stats().get("completed", 0) == 1
        removed = q.clear_completed()
        assert removed == 1
        assert q.stats().get("completed", 0) == 0

    def test_retry_dead_letters(self):
        q = TaskQueue(db_path=_temp_queue_dir())
        t = q.enqueue("/tmp/zombie.md")

        # Force to dead_letter manually by exhausting retries
        for i in range(DEFAULT_MAX_RETRIES):
            task = q.dequeue()
            q.fail(task.id, "err")

        assert q.stats().get("dead_letter", 0) == 1

        count = q.retry_dead_letters()
        assert count == 1

        s = q.stats()
        assert s.get("pending", 0) == 1
        assert s.get("dead_letter", 0) == 0

    def test_concurrent_enqueue(self):
        """Multiple enqueues from different threads should not conflict."""
        import threading

        q = TaskQueue(db_path=_temp_queue_dir())
        errors = []

        def enqueue_n(n: int):
            try:
                for i in range(n):
                    q.enqueue(f"/tmp/thread_{threading.get_ident()}_{i}.md")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=enqueue_n, args=(5,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = q.stats()
        assert stats.get("pending", 0) == 20
