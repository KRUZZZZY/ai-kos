"""Tests for ai_kos.tasks — urgency-graded tasks with 6-stage workflow."""
import os
import tempfile
import pytest
from ai_kos.tasks import TaskManager, TaskStatus, TaskUrgency, FutureTask


@pytest.fixture
def tm():
    """Create a TaskManager with a temp DB, cleaned up after test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    mgr = TaskManager(db_path=path)
    yield mgr
    mgr._get_conn().close()
    try:
        os.unlink(path)
    except OSError:
        pass


class TestTaskManagerInit:
    def test_creates_tables(self, tm):
        conn = tm._get_conn()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "future_tasks" in names
        assert "task_articles" in names
        assert "task_schema_version" in names
        conn.close()


class TestTaskCreate:
    def test_create_minimal(self, tm):
        task = tm.create("Test task", article_slugs=["test-article"])
        assert task.id == 1
        assert task.title == "Test task"
        assert task.status == "research"
        assert task.urgency == "green"
        assert task.priority == 0
        assert task.description == ""
        assert task.article_slugs == ["test-article"]
        assert task.tags == []

    def test_create_with_description(self, tm):
        task = tm.create("Read papers", article_slugs=["test-article"], description="Read the TDA papers")
        assert task.description == "Read the TDA papers"

    def test_create_with_urgency_and_tags(self, tm):
        task = tm.create("Critical fix", article_slugs=["test-article"], urgency="red", tags=["bug", "urgent"])
        assert task.urgency == "red"
        assert task.tags == ["bug", "urgent"]

    def test_create_with_data(self, tm):
        task = tm.create("Analyze results", article_slugs=["test-article"], data_summary="Found 3 anomalies",
                         image_paths=["/tmp/chart.png"])
        assert task.data_summary == "Found 3 anomalies"
        assert task.image_paths == ["/tmp/chart.png"]

    def test_create_with_articles(self, tm):
        task = tm.create("Read papers", article_slugs=["tda-intro", "persistent-homology"])
        assert task.article_slugs == ["persistent-homology", "tda-intro"]

        conn = tm._get_conn()
        rows = conn.execute(
            "SELECT article_slug FROM task_articles WHERE task_id=? ORDER BY article_slug",
            (task.id,),
        ).fetchall()
        assert [r["article_slug"] for r in rows] == ["persistent-homology", "tda-intro"]
        conn.close()

    def test_create_with_priority_and_due(self, tm):
        task = tm.create("Urgent", article_slugs=["test-article"], priority=1, due_date="2026-12-01")
        assert task.priority == 1
        assert task.due_date == "2026-12-01"

    def test_create_deduplicates(self, tm):
        task = tm.create("Dedup", article_slugs=["foo", "foo", "bar", "bar"],
                         tags=["a", "a", "b"])
        assert task.article_slugs == ["bar", "foo"]
        assert task.tags == ["a", "b"]


class TestTaskGet:
    def test_get_existing(self, tm):
        tm.create("Hello", article_slugs=["test-article"])
        task = tm.get(1)
        assert task is not None
        assert task.title == "Hello"

    def test_get_with_articles(self, tm):
        tm.create("With articles", article_slugs=["alpha", "beta"])
        task = tm.get(1)
        assert task.article_slugs == ["alpha", "beta"]

    def test_get_missing(self, tm):
        assert tm.get(999) is None


class TestTaskList:
    def test_list_all(self, tm):
        tm.create("A", article_slugs=["test-article"])
        tm.create("B", article_slugs=["test-article"])
        tm.advance(1)  # A: research → ready
        tasks = tm.list_tasks()
        assert len(tasks) == 2

    def test_list_by_status(self, tm):
        tm.create("A", article_slugs=["test-article"])
        tm.create("B", article_slugs=["test-article"])
        tm.advance(1)  # A: research → ready
        research = tm.list_tasks(status="research")
        assert len(research) == 1
        assert research[0].title == "B"
        ready = tm.list_tasks(status="ready")
        assert len(ready) == 1
        assert ready[0].title == "A"

    def test_list_by_urgency(self, tm):
        tm.create("Red task", article_slugs=["test-article"], urgency="red")
        tm.create("Green task", article_slugs=["test-article"], urgency="green")
        assert len(tm.list_tasks(urgency="red")) == 1
        assert len(tm.list_tasks(urgency="green")) == 1

    def test_list_empty(self, tm):
        assert tm.list_tasks() == []

    def test_list_respects_limit(self, tm):
        for i in range(5):
            tm.create(f"Task {i}", article_slugs=["test-article"])
        tasks = tm.list_tasks(limit=3)
        assert len(tasks) == 3


class TestTaskWorkflow:
    def test_advance_through_workflow(self, tm):
        tm.create("Pipeline", article_slugs=["test-article"])
        assert tm.get(1).status == "research"
        tm.advance(1)
        assert tm.get(1).status == "ready"
        tm.advance(1)
        assert tm.get(1).status == "in_progress"
        tm.advance(1)
        assert tm.get(1).status == "qa"
        tm.advance(1)
        assert tm.get(1).status == "qa_passed"
        assert tm.get(1).completed_at is not None
        with pytest.raises(ValueError, match="final status"):
            tm.advance(1)

    def test_block_and_unblock(self, tm):
        tm.create("Stuck", article_slugs=["test-article"])
        tm.block(1)
        assert tm.get(1).status == "blocked"
        tm.set_status(1, "research")
        assert tm.get(1).status == "research"

    def test_invalid_transition(self, tm):
        tm.create("Skip", article_slugs=["test-article"])
        with pytest.raises(ValueError, match="Invalid transition"):
            tm.set_status(1, "qa")  # can't jump from research → qa

    def test_complete_convenience(self, tm):
        tm.create("Done", article_slugs=["test-article"])
        tm.complete(1)
        assert tm.get(1).status == "qa_passed"


class TestTaskDelete:
    def test_delete_cascades_articles(self, tm):
        tm.create("With articles", article_slugs=["foo", "bar"])
        tm.delete(1)
        assert tm.get(1) is None
        conn = tm._get_conn()
        rows = conn.execute("SELECT * FROM task_articles WHERE task_id=1").fetchall()
        assert len(rows) == 0
        conn.close()

    def test_delete_missing_no_error(self, tm):
        tm.delete(999)  # should not raise
