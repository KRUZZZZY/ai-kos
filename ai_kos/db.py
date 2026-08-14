"""AI-KOS database layer — SQLite body storage for article content.

Pattern: module-level connection with WAL mode, busy_timeout, row_factory.
Following the SQLite conventions established in tasks.py and server.py.

The database lives under datasets/ (configurable via config.yaml paths.db_path).
Each article's body is stored in the `bodies` table, keyed by slug.
Frontmatter metadata stays in .md stub files on disk — this module only handles body content.
"""

import sqlite3
import threading
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ai-kos.db")

# Module-level state
_conn: Optional[sqlite3.Connection] = None
_lock = threading.Lock()
_db_path: Optional[str] = None


def _get_db_path() -> str:
    """Resolve db_path from config or default to datasets/ai-kos.db."""
    global _db_path
    if _db_path is not None:
        return _db_path
    try:
        from ai_kos.config import get
        _db_path = get("paths", "db_path", default="datasets/ai-kos.db")
    except Exception:
        _db_path = "datasets/ai-kos.db"
    assert _db_path is not None
    return _db_path


def get_conn() -> sqlite3.Connection:
    """Get or create the module-level SQLite connection (WAL, 5s timeout)."""
    global _conn
    if _conn is not None:
        return _conn
    db_path = _get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(db_path, check_same_thread=False)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA busy_timeout=5000")
    _conn.row_factory = sqlite3.Row
    _ensure_schema(_conn)
    logger.debug(f"Database connected: {db_path}")
    return _conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create bodies table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bodies (
            slug        TEXT PRIMARY KEY,
            body        TEXT NOT NULL DEFAULT '',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    conn.commit()


def set_body(slug: str, body: str) -> None:
    """Insert or replace body content for an article (upsert on slug)."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    with _lock:
        conn.execute(
            """INSERT INTO bodies (slug, body, created_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(slug) DO UPDATE SET
               body = excluded.body, updated_at = excluded.updated_at""",
            (slug, body, now, now),
        )
        conn.commit()


def get_body(slug: str) -> Optional[str]:
    """Retrieve body content for an article. Returns None if not found."""
    conn = get_conn()
    row = conn.execute("SELECT body FROM bodies WHERE slug = ?", (slug,)).fetchone()
    return row["body"] if row else None


def delete_body(slug: str) -> bool:
    """Delete body content. Returns True if a row was deleted."""
    conn = get_conn()
    with _lock:
        cur = conn.execute("DELETE FROM bodies WHERE slug = ?", (slug,))
        conn.commit()
        return cur.rowcount > 0


def body_stats() -> dict:
    """Return stats about stored bodies (for health checks)."""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as n FROM bodies").fetchone()["n"]
    total_size = conn.execute(
        "SELECT COALESCE(SUM(LENGTH(body)), 0) as sz FROM bodies"
    ).fetchone()["sz"]
    return {"total_bodies": total, "total_body_bytes": total_size}


def close() -> None:
    """Close the database connection (for testing/cleanup)."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
