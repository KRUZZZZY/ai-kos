"""Regression tests for the consensus core-audit fixes (2026-08-18).

Covers, in audit rank order:
1. read_article must NOT rewrite the body — a `## Related` section (and any
   manual content below it) survives a read byte-for-byte; only the two
   usage counters (retrieval_count / last_accessed) may change.
2. create_article refuses duplicate slugs (no more silent overwrite) unless
   an explicit overwrite=True is passed; markdown creates must not write
   into an existing .yaml backend stub.
3. persist_research validates input (empty question / zero findings / blank
   key_claims -> error dict, no article created) and normalizes finding
   field names across the pipeline shape (source_title/source_url) and the
   MCP shape (title/url).
4. PROCEDURE articles keep their body (objective/approach/verification), and
   create_with_procedure never overwrites an existing procedure article on a
   duplicate task title.
"""
import os
import tempfile
from datetime import date
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def kb(tmp_path, monkeypatch):
    """Isolated knowledge base: tmp KB dir + tmp SQLite body DB + linking off.

    Mirrors the temp-KB probe recipe: monkeypatch config._find_config/_config,
    articles.KNOWLEDGE_DIR and db._db_path/_conn, then invalidate the global
    article index so it rebuilds against the tmp dir on first access.
    Linking is disabled via similarity_threshold=1.5 — cosine similarity is
    bounded by 1.0, so `_rank_candidates` filters every pair (before orphan
    rescue even sees them) and no article ever gets a `## Related` section
    written mid-test.
    """
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
    # Close the tmp connection opened during the test; monkeypatch restores
    # the module-level prod connection afterwards.
    if db._conn is not None:
        try:
            db._conn.close()
        except Exception:
            pass
        db._conn = None


@pytest.fixture
def tm():
    """TaskManager with a temp DB (mirrors tests/test_tasks.py)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    from ai_kos.tasks import TaskManager
    mgr = TaskManager(db_path=path)
    yield mgr
    mgr._get_conn().close()
    try:
        os.unlink(path)
    except OSError:
        pass


def _base_data(slug: str, **overrides) -> dict:
    """Minimal valid base-article payload for create_article tests."""
    today = date.today()
    data = {
        "id": f"test-{slug}",
        "title": slug.replace("-", " ").title(),
        "slug": slug,
        "type": "base",
        "created_at": today,
        "updated_at": today,
        "reviewed_at": today,
        "next_review_at": today,
        "keywords": ["test", "audit", "fix"],
        "summary": f"Test article {slug}.",
        "provenance": [{"source": "manual", "origin_ref": "test"}],
        "content": f"Body content for {slug}.",
    }
    data.update(overrides)
    return data


def _procedure_data(slug: str, task_id: int = 1, **overrides) -> dict:
    """Minimal valid procedure-article payload for create_article tests."""
    today = date.today()
    data = {
        "id": f"test-{slug}",
        "title": slug.replace("-", " ").title(),
        "slug": slug,
        "type": "procedure",
        "created_at": today,
        "updated_at": today,
        "reviewed_at": today,
        "next_review_at": today,
        "keywords": ["test", "procedure"],
        "summary": f"Implementation guide for {slug}.",
        "provenance": [{"source": "manual", "origin_ref": "test"}],
        "task_id": task_id,
        "objective": "Achieve the goal.",
        "approach": "Step one, then step two.",
        "verification": "Check the result.",
    }
    data.update(overrides)
    return data


class TestReadArticlePreservesBody:
    """Fix 1: read_article must not strip `## Related` or rewrite the body."""

    def test_related_section_and_body_survive_read(self, kb):
        from ai_kos.articles import create_article, read_article

        slug = "related-article"
        r = create_article("base", _base_data(slug, content="Some manual body.\n\nMore content."))
        assert r["status"] == "created"
        fp = Path(r["filepath"])

        # Simulate the linker's output: a `## Related` wikilink section PLUS
        # manual content placed BELOW it (the audit bug destroyed the latter).
        extra = (
            "\n\n## Related\n[[other-article]] [[third-article]]\n\n"
            "Manual note below the related section that must survive."
        )
        with open(fp, "a") as f:
            f.write(extra)

        before = fp.read_text()
        result = read_article(slug)
        after = fp.read_text()

        assert result is not None
        # Usage counters bumped
        assert result["frontmatter"]["retrieval_count"] == 1
        assert result["frontmatter"]["last_accessed"] == date.today().isoformat()

        # Body (everything after the closing `---`) is byte-identical
        before_body = before.split("---", 2)[2]
        after_body = after.split("---", 2)[2]
        assert before_body == after_body
        assert "## Related" in after_body
        assert "[[other-article]] [[third-article]]" in after_body
        assert "Manual note below the related section that must survive." in after_body

    def test_read_twice_is_idempotent_on_body(self, kb):
        from ai_kos.articles import create_article, read_article

        slug = "idempotent-body"
        r = create_article("base", _base_data(slug, content="Stable body text."))
        assert r["status"] == "created"
        fp = Path(r["filepath"])

        read_article(slug)
        after_one = fp.read_text()
        read_article(slug)
        after_two = fp.read_text()

        # Only the retrieval_count line may differ between the two reads
        assert after_one.split("---", 2)[2] == after_two.split("---", 2)[2]
        assert "retrieval_count: 1" in after_one
        assert "retrieval_count: 2" in after_two


class TestCreateArticleCollisionGuard:
    """Fix 2: create_article refuses duplicate slugs unless overwrite=True."""

    def test_duplicate_slug_refused_and_original_unchanged(self, kb):
        from ai_kos.articles import create_article

        slug = "collision-article"
        r1 = create_article("base", _base_data(slug, content="FIRST BODY"))
        assert r1["status"] == "created"
        fp = Path(r1["filepath"])
        original = fp.read_text()

        r2 = create_article("base", _base_data(slug, content="SECOND BODY"))
        assert r2.get("error") == f"article already exists: {slug}"
        # Original file untouched — no truncation, no overwrite
        assert fp.read_text() == original
        assert "FIRST BODY" in fp.read_text()

    def test_overwrite_flag_replaces(self, kb):
        from ai_kos.articles import create_article, read_article

        slug = "overwrite-article"
        r1 = create_article("base", _base_data(slug, content="OLD CONTENT"))
        assert r1["status"] == "created"

        r2 = create_article("base", _base_data(slug, content="NEW CONTENT"), overwrite=True)
        assert r2["status"] == "created"
        assert "NEW CONTENT" in read_article(slug)["body"]

    def test_md_create_refused_when_yaml_stub_exists(self, kb):
        """A markdown create must not write INTO an existing .yaml backend stub."""
        from ai_kos.articles import create_article, _refresh_index

        stub_dir = kb / "knowledge" / "bundles" / "general"
        stub_dir.mkdir(parents=True, exist_ok=True)
        stub = stub_dir / "sql-collide.yaml"
        stub.write_text(yaml.dump({
            "slug": "sql-collide", "title": "SQL Stub", "backend": "sql",
            "type": "base", "keywords": ["sql", "stub"], "summary": "stub",
        }))
        _refresh_index()

        r = create_article("base", _base_data("sql-collide", content="markdown body"))
        assert r.get("error") == "article already exists: sql-collide"
        assert not (stub_dir / "sql-collide.md").exists()
        assert "SQL Stub" in stub.read_text()  # stub untouched


class TestPersistResearchValidation:
    """Fix 3: persist_research validates input + normalizes finding fields."""

    @staticmethod
    def _result(question="What is the answer?", findings=None, synthesis="Synthesis text."):
        from ai_kos.deep_research import ResearchResult
        return ResearchResult(
            id="test", plan_id="test", question=question,
            sub_questions=["sq1"], findings=findings or [],
            cross_references=[], synthesis=synthesis, knowledge_gaps=[],
        )

    def test_empty_question_returns_error_and_creates_nothing(self, kb):
        from ai_kos.deep_research import persist_research
        out = persist_research(self._result(
            question="   ",
            findings=[{"key_claim": "claim", "title": "T", "url": "U"}],
        ))
        assert "error" in out
        assert not list(Path(kb).rglob("*.md"))

    def test_no_findings_returns_error_and_creates_nothing(self, kb):
        from ai_kos.deep_research import persist_research
        out = persist_research(self._result(findings=[]))
        assert "error" in out
        assert not list(Path(kb).rglob("*.md"))

    def test_blank_key_claims_return_error_and_creates_nothing(self, kb):
        from ai_kos.deep_research import persist_research
        out = persist_research(self._result(findings=[
            {"key_claim": "   ", "title": "T", "url": "U"},
        ]))
        assert "error" in out
        assert not list(Path(kb).rglob("*.md"))

    def test_pipeline_shape_source_fields_produce_sources(self, kb):
        """Findings carrying source_title/source_url (pipeline shape) must flow
        into the research-note's sources / key_notes instead of empty strings."""
        from ai_kos.deep_research import persist_research
        from ai_kos.articles import read_article

        findings = [{
            "sub_question_idx": 0,
            "source_url": "https://example.com/paper",
            "source_title": "The Paper Title",
            "key_claim": "The key claim",
            "evidence": "Evidence here",
        }]
        out = persist_research(self._result(findings=findings))
        assert "research_note" in out

        art = read_article(out["research_note"])
        body = art["body"]
        # ## Sources line carries the normalized title + url
        assert "The Paper Title: https://example.com/paper" in body
        # key_notes entry carries the claim + title
        assert "The key claim [The Paper Title]" in body

    def test_mcp_shape_title_url_still_works(self, kb):
        """Backward compat: the MCP tool's title/url shape keeps working."""
        from ai_kos.deep_research import persist_research
        from ai_kos.articles import read_article

        findings = [{
            "sub_question_idx": 0,
            "url": "https://example.org/mcp",
            "title": "MCP Source",
            "key_claim": "MCP claim",
            "evidence": "MCP evidence",
        }]
        out = persist_research(self._result(findings=findings))
        assert "research_note" in out
        body = read_article(out["research_note"])["body"]
        assert "MCP Source: https://example.org/mcp" in body


class TestProcedureArticleBody:
    """Fix 4a: PROCEDURE articles must keep their body on write."""

    def test_procedure_body_roundtrips(self, kb):
        from ai_kos.articles import create_article, read_article

        r = create_article("procedure", _procedure_data(
            "proc-body-test", task_id=7,
            objective="Achieve the goal.",
            approach="Step one, then step two.",
            verification="Check the result.",
        ))
        assert r["status"] == "created"

        art = read_article("proc-body-test")
        body = art["body"]
        assert "## Objective" in body and "Achieve the goal." in body
        assert "## Approach" in body and "Step one, then step two." in body
        assert "## Verification" in body and "Check the result." in body

    def test_sqlite_body_is_non_empty_for_procedure(self, kb):
        """_extract_body_for_db routes PROCEDURE through the formatter too."""
        from ai_kos.articles import create_article
        from ai_kos import db

        r = create_article("procedure", _procedure_data(
            "proc-db-test", task_id=9, objective="Obj", approach="App", verification="Ver",
        ))
        assert r["status"] == "created"
        stored = db.get_body("proc-db-test") or ""
        assert "Obj" in stored
        assert "App" in stored
        assert "Ver" in stored


class TestCreateWithProcedure:
    """Fix 4b: create_with_procedure keeps the body + never overwrites on a
    duplicate task title."""

    def test_creates_task_and_procedure_with_body(self, kb, tm):
        from ai_kos.articles import read_article

        task, slug = tm.create_with_procedure(
            "Deploy the widget",
            objective="Ship it",
            approach="Run the deploy script",
            verification="Health check passes",
        )
        assert task.id >= 1
        assert slug == "proc-deploy-the-widget"
        assert slug in task.article_slugs

        art = read_article(slug)
        assert art is not None
        assert "Ship it" in art["body"]
        assert "## Approach" in art["body"]
        assert "Health check passes" in art["body"]

    def test_duplicate_title_does_not_overwrite(self, kb, tm):
        from ai_kos.articles import read_article

        task1, slug1 = tm.create_with_procedure(
            "Same title task",
            objective="ORIGINAL OBJECTIVE",
            approach="A1",
            verification="V1",
        )
        body1 = read_article(slug1)["body"]

        task2, slug2 = tm.create_with_procedure(
            "Same title task",
            objective="SECOND OBJECTIVE",
            approach="A2",
            verification="V2",
        )
        # Second call got a uniquified slug instead of clobbering the first
        assert slug2 != slug1
        assert "SECOND OBJECTIVE" in read_article(slug2)["body"]

        # First procedure article is untouched
        assert read_article(slug1)["body"] == body1
        assert "ORIGINAL OBJECTIVE" in read_article(slug1)["body"]
