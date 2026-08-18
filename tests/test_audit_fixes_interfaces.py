"""Regression tests for the consensus interface/storage audit fixes (2026-08-18).

Covers, in audit rank order:
1. ai_kos_query SQL surface is read-only — non-SELECT / multi-statement SQL
   is refused (ValueError) and the dataset table survives; SELECTs work.
2. Blob slugs are validated before any path join — traversal slugs are
   refused and nothing is written outside the blob store.
3. Stored XSS in the Flask article renderer — article bodies/titles with
   `<script>` (or hostile wikilink text) render escaped, never raw.
4. Inbox clean is non-destructive — moving onto an existing same-named
   destination keeps the destination and writes a suffixed copy instead.
5. import_sqlite_db of a missing source file returns an error and does not
   create an empty database (or materialize an empty source file).
"""
import os
import tempfile
import uuid
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def temp_db():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def kb(tmp_path, monkeypatch):
    """Isolated knowledge base: tmp KB dir + tmp SQLite body DB + linking off.

    Mirrors the temp-KB recipe from test_audit_fixes_core.py: monkeypatch
    config._find_config/_config, articles.KNOWLEDGE_DIR and db._db_path/_conn,
    then invalidate the global article index so it rebuilds against the tmp
    dir on first access. Linking is disabled so no `## Related` section is
    ever written mid-test.
    """
    import yaml
    import ai_kos.config as cfg
    import ai_kos.articles as articles
    import ai_kos.db as db

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "paths": {
            "knowledge_dir": str(tmp_path / "knowledge"),
            "db_path": str(tmp_path / "datasets" / "ai-kos.db"),
        },
        "linking": {
            "mode": "similarity",
            "similarity_threshold": 1.5,
            "min_keyword_overlap": 999,
        },
    }))
    monkeypatch.setattr(cfg, "_find_config", lambda: cfg_file)
    monkeypatch.setattr(cfg, "_config", None)
    monkeypatch.setattr(articles, "KNOWLEDGE_DIR", str(tmp_path / "knowledge"))
    monkeypatch.setattr(db, "_db_path", str(tmp_path / "datasets" / "ai-kos.db"))
    monkeypatch.setattr(db, "_conn", None)
    articles._refresh_index()
    yield tmp_path
    if db._conn is not None:
        try:
            db._conn.close()
        except Exception:
            pass
        db._conn = None


def _base_data(slug: str, body: str, title: "str | None" = None, **overrides) -> dict:
    """Minimal valid base-article payload for create_article tests."""
    today = date.today()
    data = {
        "id": f"test-{slug}",
        "title": title or slug.replace("-", " ").title(),
        "slug": slug,
        "type": "base",
        "created_at": today,
        "updated_at": today,
        "reviewed_at": today,
        "next_review_at": today,
        "keywords": ["test", "audit", "fix"],
        "summary": f"Test article {slug}.",
        "provenance": [{"source": "manual", "origin_ref": "test"}],
        "content": body,
    }
    data.update(overrides)
    return data


# ── Fix 1: SELECT-only guard on the query surface ────────────────────────────

class TestQueryTableReadOnly:
    """Fix 1: ai_kos_query must never execute non-SELECT / multi-statement SQL."""

    @pytest.fixture
    def seeded_db(self, temp_db):
        from ai_kos.datasets import create_table, insert_rows
        create_table(temp_db, "birds", [
            {"name": "species", "type": "TEXT"},
            {"name": "count", "type": "INTEGER"},
        ])
        insert_rows(temp_db, "birds", [
            {"species": "Corvus corax", "count": 100},
            {"species": "Pica; pica", "count": 200},
        ])
        return temp_db

    def test_select_still_works(self, seeded_db):
        from ai_kos.datasets import query_table
        rows = query_table(seeded_db, "SELECT * FROM birds ORDER BY count")
        assert len(rows) == 2
        assert rows[0]["species"] == "Corvus corax"

    def test_drop_table_refused_and_table_survives(self, seeded_db):
        from ai_kos.datasets import query_table, table_stats
        with pytest.raises(ValueError):
            query_table(seeded_db, "DROP TABLE birds")
        assert table_stats(seeded_db, "birds") is not None  # table survived

    def test_insert_refused_and_rows_survive(self, seeded_db):
        from ai_kos.datasets import query_table
        with pytest.raises(ValueError):
            query_table(seeded_db, "INSERT INTO birds VALUES ('Duck', 3)")
        rows = query_table(seeded_db, "SELECT COUNT(*) AS n FROM birds")
        assert rows[0]["n"] == 2

    def test_other_write_statements_refused(self, seeded_db):
        from ai_kos.datasets import query_table
        for sql in (
            "UPDATE birds SET count = 0",
            "DELETE FROM birds",
            "CREATE TABLE evil (x TEXT)",
            "ALTER TABLE birds ADD COLUMN y TEXT",
            "PRAGMA table_info(birds)",
            "EXPLAIN SELECT 1",
            "   ",
            "",
        ):
            with pytest.raises(ValueError):
                query_table(seeded_db, sql)

    def test_multi_statement_refused(self, seeded_db):
        from ai_kos.datasets import query_table, table_stats
        with pytest.raises(ValueError):
            query_table(seeded_db, "SELECT 1; DROP TABLE birds")
        assert table_stats(seeded_db, "birds") is not None

    def test_with_delete_refused(self, seeded_db):
        from ai_kos.datasets import query_table, table_stats
        with pytest.raises(ValueError):
            query_table(seeded_db, "WITH c AS (SELECT 1) DELETE FROM birds")
        assert table_stats(seeded_db, "birds") is not None

    def test_semicolon_inside_literal_is_allowed(self, seeded_db):
        """A `;` inside a string literal must not trip the single-statement check."""
        from ai_kos.datasets import query_table
        rows = query_table(seeded_db, "SELECT * FROM birds WHERE species = 'Pica; pica'")
        assert len(rows) == 1
        assert rows[0]["species"] == "Pica; pica"

    def test_mcp_handler_refuses_drop(self, kb):
        """End-to-end through the ai_kos_query dispatch path."""
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetRef, DatasetColumn
        from ai_kos import datasets

        db_path = str(kb / "datasets" / "query.db")
        datasets.create_table(db_path, "items", [{"name": "v", "type": "TEXT"}])
        datasets.insert_rows(db_path, "items", [{"v": "hello"}])

        r = create_article("base", _base_data(
            "query-me", "sql stub body",
            dataset=DatasetRef(db=db_path, table="items",
                               columns=[DatasetColumn(name="v", type="TEXT")]),
            backend="sql",
        ))
        assert r["status"] == "created"

        from ai_kos.mcp_server import _dispatch_tool
        with pytest.raises(ValueError):
            _dispatch_tool("ai_kos_query", {"slug": "query-me", "sql": "DROP TABLE items"})
        assert datasets.table_stats(db_path, "items") is not None

        out = _dispatch_tool("ai_kos_query", {"slug": "query-me", "sql": "SELECT * FROM items"})
        assert out["count"] == 1
        assert out["rows"][0]["v"] == "hello"


# ── Fix 2: blob slug path traversal ──────────────────────────────────────────

class TestBlobSlugValidation:
    """Fix 2: slugs must be validated before any path join."""

    @pytest.fixture
    def src_file(self, tmp_path):
        src = tmp_path / "payload.bin"
        src.write_bytes(b"blob data")
        return src

    def test_traversal_slug_rejected_nothing_written(self, tmp_path, src_file):
        from ai_kos.blobs import store_blob
        blob_dir = tmp_path / "blobs"
        with pytest.raises(ValueError):
            store_blob(str(src_file), str(blob_dir), slug="../../escape")
        # No file written inside the store...
        assert not blob_dir.exists() or not any(blob_dir.iterdir())
        # ...and nothing escaped outside it (old bug wrote escape-*.bin here)
        assert not any(tmp_path.parent.glob("escape-*.bin"))

    def test_backslash_slug_rejected(self, tmp_path, src_file):
        from ai_kos.blobs import store_blob
        with pytest.raises(ValueError):
            store_blob(str(src_file), str(tmp_path / "blobs"), slug="..\\escape")

    def test_dotdot_component_rejected(self, tmp_path, src_file):
        from ai_kos.blobs import store_blob
        with pytest.raises(ValueError):
            store_blob(str(src_file), str(tmp_path / "blobs"), slug="a/../escape")

    def test_empty_slug_rejected(self, tmp_path, src_file):
        from ai_kos.blobs import store_blob
        with pytest.raises(ValueError):
            store_blob(str(src_file), str(tmp_path / "blobs"), slug="")
        with pytest.raises(ValueError):
            store_blob(str(src_file), str(tmp_path / "blobs"), slug="   ")

    def test_normal_slug_still_works(self, tmp_path, src_file):
        from ai_kos.blobs import store_blob
        ref = store_blob(str(src_file), str(tmp_path / "blobs"), slug="safe-slug")
        assert Path(ref["path"]).parent == tmp_path / "blobs"
        assert Path(ref["path"]).exists()

    def test_mcp_ingest_blob_refuses_traversal(self, kb):
        """store_blob raising must surface as an error, not a blob write."""
        from ai_kos.blobs import store_blob
        src = kb / "payload.bin"
        src.write_bytes(b"x")
        with pytest.raises(ValueError):
            store_blob(str(src), slug="../../escape")


# ── Fix 3: stored XSS in the Flask article renderer ──────────────────────────

class TestArticleRendererXSS:
    """Fix 3: article-controlled strings must render escaped, never raw."""

    @pytest.fixture
    def client(self, kb):
        from ai_kos.server import app, _article_cache
        _article_cache.clear()
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    @staticmethod
    def _create(kb, slug, body, title="XSS Article"):
        from ai_kos.articles import create_article
        r = create_article("base", _base_data(slug, body, title=title))
        assert r["status"] == "created"

    def test_script_in_body_renders_escaped(self, kb, client):
        slug = "xss-body"
        self._create(kb, slug, "Safe intro.\n\n<script>alert(1)</script>\n\nMore text.")
        resp = client.get(f"/articles/{slug}")
        assert resp.status_code == 200
        data = resp.data
        assert b"<script>alert(1)</script>" not in data
        assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in data
        assert b"Safe intro" in data

    def test_script_in_title_escaped(self, kb, client):
        slug = "xss-title"
        self._create(kb, slug, "Body text.", title="<script>alert(2)</script>")
        resp = client.get(f"/articles/{slug}")
        assert resp.status_code == 200
        assert b"<script>alert(2)</script>" not in resp.data
        assert b"&lt;script&gt;alert(2)&lt;/script&gt;" in resp.data

    def test_wikilink_slug_cannot_break_out_of_href(self, kb, client):
        slug = "xss-wikilink"
        self._create(kb, slug, 'See [[x" onmouseover="alert(3)]] for details.')
        resp = client.get(f"/articles/{slug}")
        assert resp.status_code == 200
        data = resp.data
        # The hostile quote inside the href must be entity-escaped, so the
        # attribute cannot break out (space follows the escaped quote).
        assert b'onmouseover="' not in data
        assert b'&#34; onmouseover=' in data
        assert b'href="/articles/x&#34;' in data

    def test_url_with_quotes_escaped_in_href(self, kb, client):
        slug = "xss-url"
        self._create(kb, slug, 'Visit https://example.com/?q="><img src=x onerror=alert(4)> now.')
        resp = client.get(f"/articles/{slug}")
        assert resp.status_code == 200
        data = resp.data
        # The raw tag must be gone and the href must not contain a raw quote
        assert b'<img src=x' not in data
        assert b'?q="><img' not in data
        # The escaped form survives in the href
        assert b'?q=&#34;&gt;&lt;img' in data


# ── Fix 4: non-destructive inbox clean ───────────────────────────────────────

class TestNonDestructiveMove:
    """Fix 4: moving onto an existing same-named destination must not destroy it."""

    def test_cli_safe_move_file_keeps_destination(self, tmp_path):
        from ai_kos.cli import _safe_move
        src = tmp_path / "note.md"
        src.write_text("NEW CONTENT")
        dst = tmp_path / "archive" / "note.md"
        dst.parent.mkdir()
        dst.write_text("OLD CONTENT")

        _safe_move(src, dst)

        assert dst.read_text() == "OLD CONTENT"                       # preserved
        assert (tmp_path / "archive" / "note-1.md").read_text() == "NEW CONTENT"
        assert not src.exists()

    def test_cli_safe_move_uses_next_free_suffix(self, tmp_path):
        from ai_kos.cli import _safe_move
        dst_dir = tmp_path / "archive"
        dst_dir.mkdir()
        (dst_dir / "f.txt").write_text("original")
        (dst_dir / "f-1.txt").write_text("first collision")
        src = tmp_path / "f.txt"
        src.write_text("third")

        _safe_move(src, dst_dir / "f.txt")

        assert (dst_dir / "f.txt").read_text() == "original"
        assert (dst_dir / "f-1.txt").read_text() == "first collision"
        assert (dst_dir / "f-2.txt").read_text() == "third"

    def test_cli_safe_move_dir_never_rmtree_target(self, tmp_path):
        from ai_kos.cli import _safe_move
        src = tmp_path / "proj"
        src.mkdir()
        (src / "main.py").write_text("src code")
        dst = tmp_path / "projects" / "proj"
        dst.mkdir(parents=True)
        (dst / "keep.txt").write_text("KEEP ME")

        _safe_move(src, dst)

        assert (dst / "keep.txt").read_text() == "KEEP ME"            # not rmtree'd
        assert (tmp_path / "projects" / "proj-1" / "main.py").read_text() == "src code"
        assert not src.exists()

    def test_mcp_mv_keeps_destination(self, tmp_path):
        from ai_kos.mcp_server import _mv
        src = tmp_path / "data.md"
        src.write_text("INCOMING")
        dst = tmp_path / "archive" / "data.md"
        dst.parent.mkdir()
        dst.write_text("EXISTING")

        _mv(src, dst)

        assert dst.read_text() == "EXISTING"
        assert (tmp_path / "archive" / "data-1.md").read_text() == "INCOMING"
        assert not src.exists()

    def test_cmd_clean_archives_without_overwrite(self, tmp_path, monkeypatch, capsys):
        import ai_kos.config as cfg
        inbox = tmp_path / "inbox"
        archive = tmp_path / "archive"
        rejected = tmp_path / "rejected"
        projects = tmp_path / "projects"
        for d in (inbox, archive, rejected, projects):
            d.mkdir()
        (inbox / "note.md").write_text("NEW CONTENT")
        (archive / "note.md").write_text("OLD CONTENT")

        paths = {
            "inbox_dir": str(inbox), "archive_dir": str(archive),
            "rejected_dir": str(rejected), "projects_dir": str(projects),
        }
        monkeypatch.setattr(cfg, "get",
                            lambda section, key, default=None: paths.get(key, default))

        from ai_kos.cli import cmd_clean
        cmd_clean(None)

        assert (archive / "note.md").read_text() == "OLD CONTENT"
        assert (archive / "note-1.md").read_text() == "NEW CONTENT"
        assert not (inbox / "note.md").exists()


# ── Fix 5: import_sqlite_db missing-source false success ─────────────────────

class TestImportSqliteMissingSource:
    """Fix 5: a missing source DB must error, not create an empty DB."""

    def test_missing_source_returns_error_no_files_created(self, tmp_path):
        from ai_kos.datasets import import_sqlite_db
        missing = tmp_path / "does-not-exist.db"
        target = tmp_path / "datasets" / "ai-kos.db"

        result = import_sqlite_db(str(missing), str(target))

        assert "error" in result
        assert "not found" in result["error"]
        # No empty source file materialized, no empty target DB created
        assert not missing.exists()
        assert not target.exists()

    def test_missing_source_target_never_has_tables(self, tmp_path):
        from ai_kos.datasets import import_sqlite_db, list_tables
        target = tmp_path / "target.db"

        result = import_sqlite_db(str(tmp_path / "nope.sqlite"), str(target))

        assert "error" in result
        if target.exists():  # belt-and-braces: even if created, no tables
            assert list_tables(str(target)) == []

    def test_valid_source_still_imports(self, tmp_path):
        import sqlite3
        from ai_kos.datasets import import_sqlite_db, table_stats
        src = tmp_path / "src.db"
        conn = sqlite3.connect(str(src))
        conn.execute("CREATE TABLE t (v TEXT)")
        conn.execute("INSERT INTO t VALUES ('x')")
        conn.commit()
        conn.close()

        target = tmp_path / "out.db"
        result = import_sqlite_db(str(src), str(target))

        assert result["tables_imported"] == 1
        assert table_stats(str(target), "t")["row_count"] == 1

    def test_mcp_handler_returns_error_for_missing_file(self, kb):
        from ai_kos.mcp_server import _dispatch_tool
        out = _dispatch_tool("ai_kos_ingest_sqlite", {
            "filepath": str(kb / "missing.db"),
            "slug_prefix": "x", "title_prefix": "X", "keywords": ["k"],
        })
        err = out.get("error", "")
        assert "not found" in err
