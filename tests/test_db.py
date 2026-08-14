"""Tests for AI-KOS database layer (body storage in SQLite)."""
import tempfile
import os
import pytest


@pytest.fixture
def temp_db(monkeypatch):
    """Create a temporary database for isolated testing."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    import ai_kos.db as db_mod
    db_mod._db_path = db_path
    db_mod._conn = None  # force reconnect

    yield db_path

    # Cleanup
    db_mod.close()
    os.unlink(db_path)
    db_mod._db_path = None
    db_mod._conn = None


class TestBodyCRUD:
    def test_set_and_get(self, temp_db):
        from ai_kos.db import set_body, get_body
        set_body("test-slug", "# Hello World\n\nSome content.")
        result = get_body("test-slug")
        assert result == "# Hello World\n\nSome content."

    def test_get_missing_returns_none(self, temp_db):
        from ai_kos.db import get_body
        assert get_body("nonexistent") is None

    def test_set_overwrites(self, temp_db):
        from ai_kos.db import set_body, get_body
        set_body("test-slug", "Version 1")
        set_body("test-slug", "Version 2")
        assert get_body("test-slug") == "Version 2"

    def test_delete_removes(self, temp_db):
        from ai_kos.db import set_body, get_body, delete_body
        set_body("test-slug", "Content")
        assert delete_body("test-slug") is True
        assert get_body("test-slug") is None

    def test_delete_missing_returns_false(self, temp_db):
        from ai_kos.db import delete_body
        assert delete_body("nonexistent") is False

    def test_body_stats(self, temp_db):
        from ai_kos.db import set_body, body_stats
        set_body("a", "Hello")
        set_body("b", "World!")
        stats = body_stats()
        assert stats["total_bodies"] == 2
        assert stats["total_body_bytes"] == 11  # 5 + 6

    def test_empty_body(self, temp_db):
        from ai_kos.db import set_body, get_body
        set_body("empty", "")
        assert get_body("empty") == ""

    def test_body_with_unicode(self, temp_db):
        from ai_kos.db import set_body, get_body
        body = "Persistence landscapes — H₀ and H₁ features"
        set_body("unicode", body)
        assert get_body("unicode") == body

    def test_concurrent_slugs(self, temp_db):
        from ai_kos.db import set_body, get_body
        set_body("a", "A content")
        set_body("b", "B content")
        assert get_body("a") == "A content"
        assert get_body("b") == "B content"
