"""AI-KOS Future Task System — urgency-graded tasks with research-to-QA workflow.

SQLite-backed. Tasks reference knowledge articles via a junction table,
support tagging, data attachments (summary + images), and a 6-stage workflow.

Usage:
    from ai_kos.tasks import TaskManager

    tm = TaskManager()
    task = tm.create("Benchmark TDA pipelines",
                     urgency="red", tags=["benchmark", "tda"],
                     article_slugs=["persistent-homology"])
    tm.advance(task.id, "ready")
"""

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_kos.config import get

logger = logging.getLogger("ai-kos.tasks")


class TaskUrgency(str, Enum):
    """How critical a task is to workflow progression."""
    RED = "red"        # Blocking — prevents workflow from proceeding
    YELLOW = "yellow"  # Hindering — slows something down massively
    GREEN = "green"    # Normal — just needs doing


class TaskStatus(str, Enum):
    """6-stage task lifecycle from research through QA sign-off."""
    RESEARCH = "research"        # Needs investigation before work can start
    READY = "ready"              # Can be commenced
    IN_PROGRESS = "in_progress"  # Work has started
    QA = "qa"                    # Needs human eyes or further testing
    QA_PASSED = "qa_passed"      # Done — verified complete
    BLOCKED = "blocked"          # Cannot/shouldn't proceed for external reasons


STATUS_ORDER = ["research", "ready", "in_progress", "qa", "qa_passed"]
"""Forward progression order. blocked sits outside this flow."""


@dataclass
class FutureTask:
    """A task with urgency, workflow state, tags, and optional data attachments."""
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    status: str = "research"          # TaskStatus value
    urgency: str = "green"            # TaskUrgency value
    priority: int = 0                 # 0=highest
    due_date: Optional[str] = None    # ISO date YYYY-MM-DD
    tags: List[str] = field(default_factory=list)
    article_slugs: List[str] = field(default_factory=list)
    project_slug: Optional[str] = None  # mission article this task belongs to
    data_summary: str = ""            # Free-text or JSON summary of attached data
    image_paths: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None


class TaskManager:
    """SQLite-backed manager with urgency-graded tasks and 6-stage workflow.

    Usage:
        tm = TaskManager()
        task = tm.create("Benchmark TDA", urgency="red", tags=["tda", "benchmark"])
        tm.advance(task.id, "ready")
        tm.list_tasks(status="research")
    """

    SCHEMA_VERSION = 3

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or self._default_db_path()
        self._lock = threading.Lock()
        self._init_db()
        self._migrate()

    def _default_db_path(self) -> str:
        knowledge_dir = get("paths", "knowledge_dir", default="knowledge")
        return str(Path(knowledge_dir) / "future_tasks.db")

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS future_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'research',
                    urgency TEXT DEFAULT 'green',
                    priority INTEGER DEFAULT 0,
                    due_date TEXT,
                    tags TEXT DEFAULT '[]',
                    data_summary TEXT DEFAULT '',
                    image_paths TEXT DEFAULT '[]',
                    project_slug TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_articles (
                    task_id INTEGER NOT NULL,
                    article_slug TEXT NOT NULL,
                    PRIMARY KEY (task_id, article_slug),
                    FOREIGN KEY (task_id) REFERENCES future_tasks(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)
            # Index created in _migrate() after columns are guaranteed to exist
            conn.commit()

    def _migrate(self):
        """Add columns that may be missing from v1 schema."""
        with self._get_conn() as conn:
            current = conn.execute(
                "SELECT version FROM task_schema_version"
            ).fetchone()
            current_ver = current["version"] if current else 1

            if current_ver < 2:
                existing = {r["name"] for r in conn.execute(
                    "PRAGMA table_info('future_tasks')"
                ).fetchall()}

                migrations = [
                    ("urgency", "TEXT DEFAULT 'green'"),
                    ("tags", "TEXT DEFAULT '[]'"),
                    ("data_summary", "TEXT DEFAULT ''"),
                    ("image_paths", "TEXT DEFAULT '[]'"),
                ]
                for col_name, col_def in migrations:
                    if col_name not in existing:
                        conn.execute(
                            f"ALTER TABLE future_tasks ADD COLUMN {col_name} {col_def}"
                        )

                # Update index
                conn.execute("DROP INDEX IF EXISTS idx_tasks_status_priority")
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_status_urgency
                    ON future_tasks(status, urgency, priority, created_at)
                """)

                # Migrate old status values
                conn.execute(
                    "UPDATE future_tasks SET status='research' WHERE status='pending'"
                )
                conn.execute(
                    "UPDATE future_tasks SET status='qa_passed' WHERE status='completed'"
                )
                conn.execute(
                    "UPDATE future_tasks SET status='blocked' WHERE status='cancelled'"
                )

                conn.execute(
                    "INSERT OR REPLACE INTO task_schema_version (version) VALUES (2)"
                )
                conn.commit()
                logger.info("Migrated task schema to v2")

            if current_ver < 3:
                existing = {r["name"] for r in conn.execute(
                    "PRAGMA table_info('future_tasks')"
                ).fetchall()}
                if "project_slug" not in existing:
                    conn.execute(
                        "ALTER TABLE future_tasks ADD COLUMN project_slug TEXT"
                    )
                conn.execute(
                    "INSERT OR REPLACE INTO task_schema_version (version) VALUES (3)"
                )
                conn.commit()
                logger.info("Migrated task schema to v3")

    def _row_opt(self, row, key: str, default=None):
        """Safe accessor for sqlite3.Row (no .get() method)."""
        return row[key] if key in row.keys() else default

    @staticmethod
    def _serialize_list(lst: Optional[List[str]]) -> str:
        return json.dumps(sorted(set(lst or [])), ensure_ascii=False)

    @staticmethod
    def _deserialize_list(raw: Optional[str]) -> List[str]:
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _valid_transition(current: str, target: str) -> bool:
        """Check if status transition is valid (sequential forward only)."""
        if target == "blocked":
            return current != "qa_passed"  # can block from any state except done
        if current == "blocked":
            return target in ("research", "ready")  # unblock back to start
        if target == current:
            return False
        if current not in STATUS_ORDER or target not in STATUS_ORDER:
            return False
        # Only allow advancing by exactly one step
        return STATUS_ORDER.index(target) == STATUS_ORDER.index(current) + 1

    @staticmethod
    def _next_status(current: str) -> Optional[str]:
        """Get the next status in the workflow, or None if at end."""
        if current not in STATUS_ORDER:
            return None
        idx = STATUS_ORDER.index(current)
        return STATUS_ORDER[idx + 1] if idx + 1 < len(STATUS_ORDER) else None

    # ── CRUD ─────────────────────────────────────────────────────────────

    def create(
        self,
        title: str,
        description: str = "",
        urgency: str = "green",
        priority: int = 0,
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None,
        article_slugs: Optional[List[str]] = None,
        data_summary: str = "",
        image_paths: Optional[List[str]] = None,
        project_slug: Optional[str] = None,
    ) -> FutureTask:
        """Create a new task. Requires at least one article_slug for documentation."""
        now = datetime.now(timezone.utc).isoformat()
        slugs = sorted(set(article_slugs or []))
        if not slugs:
            raise ValueError("At least one article_slug is required to document the task")
        tag_list = sorted(set(tags or []))
        img_list = sorted(set(image_paths or []))

        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO future_tasks
                   (title, description, status, urgency, priority, due_date,
                    tags, data_summary, image_paths, project_slug, created_at, updated_at)
                   VALUES (?, ?, 'research', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, description, urgency, priority, due_date,
                 self._serialize_list(tag_list), data_summary,
                 self._serialize_list(img_list), project_slug, now, now),
            )
            task_id = cursor.lastrowid
            for slug in slugs:
                conn.execute(
                    "INSERT OR IGNORE INTO task_articles (task_id, article_slug) VALUES (?, ?)",
                    (task_id, slug),
                )
            conn.commit()

        return FutureTask(
            id=task_id, title=title, description=description,
            status="research", urgency=urgency, priority=priority,
            due_date=due_date, tags=tag_list,
            article_slugs=slugs, data_summary=data_summary,
            image_paths=img_list, project_slug=project_slug,
            created_at=now, updated_at=now,
        )

    def create_with_procedure(
        self,
        title: str,
        objective: str,
        approach: str,
        verification: str,
        description: str = "",
        urgency: str = "green",
        priority: int = 0,
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None,
        extra_slugs: Optional[List[str]] = None,
        data_summary: str = "",
        image_paths: Optional[List[str]] = None,
    ) -> tuple[FutureTask, str]:
        """Create a task AND its procedure article in one call.

        Returns (task, procedure_slug). Creates the task first (to get its ID),
        then creates the procedure article with the real task_id embedded.
        """
        from ai_kos.articles import create_article
        from datetime import date as _date
        import uuid as _uuid, re

        # Sanitize slug
        proc_slug = re.sub(r'[^a-z0-9-]', '', f"proc-{title.lower().replace(' ', '-')[:60]}")[:80]
        tag_list = (tags or []) + ["procedure", "task"]

        # Create the task FIRST to get a real ID, then create the procedure
        # We temporarily attach a placeholder slug, then swap it out
        today = _date.today()

        # Step 1: Create procedure article with placeholder task_id
        result = create_article("procedure", {
            "id": str(_uuid.uuid4()),
            "title": f"Procedure: {title}",
            "slug": proc_slug,
            "type": "procedure",
            "created_at": today, "updated_at": today,
            "reviewed_at": today,
            "next_review_at": today.replace(year=today.year + 1),
            "keywords": tag_list[:8],
            "summary": f"Implementation guide for task: {title}",
            "task_id": 0,
            "objective": objective,
            "approach": approach,
            "verification": verification,
            "provenance": [{"source": "manual", "origin_ref": "task-manager"}],
            "confidence": 0.9,
        })

        proc_slug_real = result.get("slug", proc_slug)

        # Step 2: Create the task with the procedure slug attached
        task = self.create(
            title=title, description=description, urgency=urgency,
            priority=priority, due_date=due_date, tags=tags,
            article_slugs=[proc_slug_real] + (extra_slugs or []),
            data_summary=data_summary, image_paths=image_paths,
        )

        # Step 3: Patch the procedure article's task_id in the file directly
        from ai_kos.articles import _get_index
        idx = _get_index()
        idx._ensure_built()
        fp = idx._paths.get(proc_slug_real)
        if fp and Path(fp).exists():
            with open(fp, 'r') as f:
                raw = f.read()
            raw = raw.replace("task_id: 0", f"task_id: {task.id}")
            with open(fp, 'w') as f:
                f.write(raw)

        return task, proc_slug_real

    def get(self, task_id: int) -> Optional[FutureTask]:
        """Get a single task by ID, including attached article slugs."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM future_tasks WHERE id=?", (task_id,)
            ).fetchone()
            if row is None:
                return None
            article_rows = conn.execute(
                "SELECT article_slug FROM task_articles WHERE task_id=? ORDER BY article_slug",
                (task_id,),
            ).fetchall()

        return FutureTask(
            id=row["id"], title=row["title"], description=row["description"],
            status=row["status"], urgency=self._row_opt(row, "urgency", "green"),
            priority=row["priority"], due_date=row["due_date"],
            tags=self._deserialize_list(self._row_opt(row, "tags")),
            article_slugs=[r["article_slug"] for r in article_rows],
            data_summary=self._row_opt(row, "data_summary", ""),
            image_paths=self._deserialize_list(self._row_opt(row, "image_paths")),
            project_slug=row["project_slug"] if "project_slug" in row.keys() else None,
            created_at=row["created_at"], updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )

    def list_tasks(
        self, status: Optional[str] = None, urgency: Optional[str] = None,
        project_slug: Optional[str] = None, limit: int = 100,
    ) -> List[FutureTask]:
        """List tasks with optional status, urgency, and project filters."""
        with self._get_conn() as conn:
            conditions = []
            params = []
            if status:
                conditions.append("status = ?")
                params.append(status)
            if urgency:
                conditions.append("urgency = ?")
                params.append(urgency)
            if project_slug:
                conditions.append("project_slug = ?")
                params.append(project_slug)
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            sql = (
                f"SELECT * FROM future_tasks {where} "
                "ORDER BY CASE urgency WHEN 'red' THEN 0 WHEN 'yellow' THEN 1 ELSE 2 END, "
                "priority ASC, created_at ASC LIMIT ?"
            )
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()

            tasks = []
            for row in rows:
                article_rows = conn.execute(
                    "SELECT article_slug FROM task_articles WHERE task_id=? ORDER BY article_slug",
                    (row["id"],),
                ).fetchall()
                tasks.append(FutureTask(
                    id=row["id"], title=row["title"], description=row["description"],
                    status=row["status"], urgency=self._row_opt(row, "urgency", "green"),
                    priority=row["priority"], due_date=row["due_date"],
                    tags=self._deserialize_list(self._row_opt(row, "tags")),
                    article_slugs=[r["article_slug"] for r in article_rows],
                    data_summary=self._row_opt(row, "data_summary", ""),
                    image_paths=self._deserialize_list(self._row_opt(row, "image_paths")),
                    project_slug=row["project_slug"] if "project_slug" in row.keys() else None,
                    created_at=row["created_at"], updated_at=row["updated_at"],
                    completed_at=row["completed_at"],
                ))
        return tasks

    def list_projects(self) -> List[dict]:
        """Get all projects (missions with tasks) with task stats.

        Returns list of {mission_slug, mission_title, task_count, done_count,
        blocked_count, red_count, yellow_count, total_tasks}.
        """
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT project_slug,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'qa_passed' THEN 1 ELSE 0 END) as done,
                       SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
                       SUM(CASE WHEN urgency = 'red' THEN 1 ELSE 0 END) as red,
                       SUM(CASE WHEN urgency = 'yellow' THEN 1 ELSE 0 END) as yellow
                FROM future_tasks
                WHERE project_slug IS NOT NULL
                GROUP BY project_slug
                ORDER BY red DESC, total DESC
            """).fetchall()

        projects = []
        for row in rows:
            slug = row["project_slug"]
            # Try to get mission title
            title = slug
            try:
                from ai_kos.articles import _get_index
                idx = _get_index()
                idx._ensure_built()
                fm = idx._frontmatter.get(slug)
                if fm:
                    title = fm.get("title", slug)
            except Exception:
                pass

            projects.append({
                "slug": slug,
                "title": title,
                "total": row["total"],
                "done": row["done"],
                "blocked": row["blocked"],
                "red": row["red"],
                "yellow": row["yellow"],
                "completion_pct": round(row["done"] / row["total"] * 100) if row["total"] else 0,
            })
        return projects

    def advance(self, task_id: int) -> FutureTask:
        """Move task to the next status in the workflow. Raises ValueError if at end or invalid."""
        task = self.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        nxt = self._next_status(task.status)
        if nxt is None:
            raise ValueError(f"Task {task_id} is already at final status ({task.status})")
        return self._update_status(task_id, nxt)

    def set_status(self, task_id: int, status: str) -> FutureTask:
        """Set task to a specific status. Validates the transition."""
        task = self.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        if not self._valid_transition(task.status, status):
            raise ValueError(
                f"Invalid transition: {task.status} → {status}"
            )
        return self._update_status(task_id, status)

    def _update_status(self, task_id: int, status: str) -> FutureTask:
        """Update task status. Sets completed_at when reaching qa_passed."""
        now = datetime.now(timezone.utc).isoformat()
        completed_at = now if status == "qa_passed" else None
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE future_tasks SET status=?, updated_at=?, completed_at=? WHERE id=?",
                (status, now, completed_at, task_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Task {task_id} not found")
            conn.commit()
        result = self.get(task_id)
        assert result is not None
        return result

    def complete(self, task_id: int) -> FutureTask:
        """Mark a task as qa_passed (done). Convenience for old API."""
        return self._update_status(task_id, "qa_passed")

    def block(self, task_id: int) -> FutureTask:
        """Mark a task as blocked."""
        return self._update_status(task_id, "blocked")

    def delete(self, task_id: int) -> None:
        """Delete a task and its article attachments (CASCADE)."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM future_tasks WHERE id=?", (task_id,))
            conn.commit()
