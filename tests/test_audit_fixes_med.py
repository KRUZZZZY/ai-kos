"""Regression tests for the MED consensus audit fixes (2026-08-18) — CORE
data-integrity/correctness subset.

Covers:
1. update_article / delete_article on .yaml backend stubs (whole-dict files)
   must work without raising and preserve other fields.
2. linker .yaml supersede idempotency: a .yaml merge-loser must not be
   re-superseded on every run (articles_changed converges to 0).
3. stale link_count corrected to 0 when the last inbound link drops.
4. dead config keys (target_keywords, target_subject_keywords, max_paragraphs,
   summary_max_chars, linking.link_budget.importance.explicit_field) are read
   by the code that should consume them.
"""
import logging
from datetime import date
from pathlib import Path

import pytest
import yaml


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _write_md(path, slug, keywords, subject_keywords=None, related=None, **extra):
    """Minimal markdown article with v2-capable frontmatter (mirrors
    test_linker_v2.make_article)."""
    fm = {
        "slug": slug,
        "title": slug,
        "type": "base",
        "keywords": keywords,
        "summary": f"About {slug}",
        "confidence": 0.8,
        "retrieval_count": 0,
        "lifecycle": "current",
        "schema_version": 2,
    }
    if subject_keywords:
        fm["subject_keywords"] = subject_keywords
    if related is not None:
        fm["related"] = related
    fm.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        + yaml.dump(fm, default_flow_style=False, sort_keys=False)
        + f"---\n\nBody about {slug}.\n"
    )


def _write_yaml(path, data):
    """Whole-dict .yaml backend stub (no `---` frontmatter delimiters)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def _fm(path):
    """Read frontmatter from a .md or whole-dict .yaml file."""
    content = Path(path).read_text()
    if str(path).endswith(".yaml"):
        return yaml.safe_load(content) or {}
    return yaml.safe_load(content.split("---", 2)[1]) or {}


@pytest.fixture
def kb(tmp_path, monkeypatch):
    """Isolated knowledge base: tmp KB dir + tmp SQLite body DB + linking off
    (similarity_threshold=1.5 filters every pair). Mirrors the temp-KB probe
    recipe used across the audit-fix suites."""
    import ai_kos.config as cfg
    import ai_kos.articles as articles
    import ai_kos.db as db

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "paths": {
            "knowledge_dir": str(tmp_path / "knowledge"),
            "db_path": str(tmp_path / "datasets" / "ai-kos.db"),
            "archive_dir": str(tmp_path / "archive"),
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


@pytest.fixture
def kb_link(tmp_path, monkeypatch):
    """Like `kb` but linking ENABLED (default similarity config, threshold
    0.10) — for link_all end-to-end convergence tests."""
    import ai_kos.config as cfg
    import ai_kos.articles as articles
    import ai_kos.db as db

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "paths": {
            "knowledge_dir": str(tmp_path / "knowledge"),
            "db_path": str(tmp_path / "datasets" / "ai-kos.db"),
            "archive_dir": str(tmp_path / "archive"),
        },
        "linking": {
            "mode": "similarity",
            "similarity_threshold": 0.10,
            "orphan_rescue": True,
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


def _base_data(slug: str, **overrides) -> dict:
    """Minimal valid base-article payload (mirrors test_audit_fixes_core)."""
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


# ── Fix 1: update_article / delete_article on .yaml backend stubs ────────────

class TestYamlStubUpdateDelete:
    def test_update_article_on_yaml_stub_works_and_preserves_fields(self, kb):
        from ai_kos.articles import update_article, _refresh_index

        stub_dir = kb / "knowledge" / "bundles" / "general"
        stub = stub_dir / "sql-stub.yaml"
        _write_yaml(stub, {
            "slug": "sql-stub",
            "title": "SQL Stub",
            "backend": "sql",
            "type": "base",
            "keywords": ["sql", "stub", "dataset"],
            "summary": "A dataset stub.",
            "dataset": {"db": "datasets/ai-kos.db", "table": "stub_table"},
            "custom_field": "keep-me",
        })
        _refresh_index()

        # OLD code: content.split('---', 2) → IndexError on a whole-dict .yaml
        r = update_article("sql-stub", {"title": "Updated Stub Title"})
        assert r["status"] == "updated"

        # Still a whole-dict file (no `---` frontmatter delimiters introduced)
        raw = stub.read_text()
        assert "---" not in raw.replace("\n", "")
        fm = yaml.safe_load(raw) or {}
        assert fm["title"] == "Updated Stub Title"
        # Other fields preserved
        assert fm["slug"] == "sql-stub"
        assert fm["backend"] == "sql"
        assert fm["keywords"] == ["sql", "stub", "dataset"]
        assert fm["summary"] == "A dataset stub."
        assert fm["dataset"] == {"db": "datasets/ai-kos.db", "table": "stub_table"}
        assert fm["custom_field"] == "keep-me"
        # update_article bookkeeping applied
        assert fm["version"] == 2
        assert fm["updated_at"] == date.today().isoformat()

    def test_update_article_md_roundtrip_unchanged(self, kb):
        """Sanity: the .md path of update_article still round-trips the body."""
        from ai_kos.articles import create_article, update_article

        r = create_article("base", _base_data("md-update", content="BODY LINE ONE.\n\nBODY LINE TWO."))
        assert r["status"] == "created"
        fp = Path(r["filepath"])
        before_body = fp.read_text().split("---", 2)[2]

        ur = update_article("md-update", {"title": "Renamed"})
        assert ur["status"] == "updated"
        after_body = fp.read_text().split("---", 2)[2]
        assert before_body == after_body  # body byte-identical
        assert "Renamed" in fp.read_text().split("---", 2)[1]

    def test_delete_article_on_yaml_stub_works_with_cold_index(self, kb):
        """A .yaml stub outside bundles/general + a cold index must still be
        deletable (filesystem fallback) and must not crash."""
        from ai_kos.articles import delete_article, _get_index, _refresh_index

        stub = kb / "knowledge" / "bundles" / "datasets" / "deep-stub.yaml"
        _write_yaml(stub, {
            "slug": "deep-stub",
            "title": "Deep Stub",
            "type": "base",
            "keywords": ["deep", "stub"],
            "summary": "Stub in a non-general bundle.",
        })
        _refresh_index()
        # Simulate a cold/stale index: drop the slug so _slug_path falls back
        # to bundles/general (miss) and delete_article must find the file by
        # filesystem search + read its frontmatter directly.
        _get_index().remove("deep-stub")

        r = delete_article("deep-stub")
        assert r["status"] == "deleted"
        assert not stub.exists()
        archived = kb / "archive" / "deep-stub.yaml"
        assert archived.exists()
        assert _fm(archived)["title"] == "Deep Stub"


# ── Fix 2: linker .yaml supersede idempotency ────────────────────────────────

class TestYamlSupersedeIdempotency:
    def test_yaml_merge_loser_superseded_once_then_converges(self, kb_link):
        from ai_kos.linker import link_all

        kd = kb_link / "knowledge"
        shared = ["a", "b", "c", "d", "e"]
        _write_md(kd / "bundles" / "general" / "win.md", "win", shared)
        _write_yaml(kd / "bundles" / "general" / "loser.yaml", {
            "slug": "loser",
            "title": "Loser",
            "type": "base",
            "keywords": shared,
            "summary": "Merge loser stored as a .yaml stub.",
            "schema_version": 2,
        })

        r1 = link_all(str(kd), mode="similarity")
        assert r1["articles_changed"] > 0
        assert any(
            m["a"] == "loser" or m["b"] == "loser" for m in r1["merge_candidates"]
        )

        # Loser superseded exactly once, pointing at the winner
        fm = _fm(kd / "bundles" / "general" / "loser.yaml")
        assert fm["lifecycle"] == "superseded"
        assert fm["superseded_by"] == "win"

        # OLD code: split('---')[1] IndexError on .yaml → already_superseded
        # never True → loser re-superseded every run → articles_changed never 0
        r2 = link_all(str(kd), mode="similarity")
        assert r2["articles_changed"] == 0
        # Still superseded to the same winner, not churned
        fm2 = _fm(kd / "bundles" / "general" / "loser.yaml")
        assert fm2["lifecycle"] == "superseded"
        assert fm2["superseded_by"] == "win"

        r3 = link_all(str(kd), mode="similarity")
        assert r3["articles_changed"] == 0


# ── Fix 3: stale link_count corrected to 0 ───────────────────────────────────

class TestLinkCountCorrectedToZero:
    def test_link_count_becomes_zero_after_last_inbound_link_removed(self, kb_link):
        from ai_kos.linker import link_all

        kd = kb_link / "knowledge"
        a_path = kd / "bundles" / "general" / "a.md"
        b_path = kd / "bundles" / "general" / "b.md"
        _write_md(a_path, "a", ["alpha"], subject_keywords=["tda", "ai-kos", "sqlite"])
        _write_md(b_path, "b", ["beta"], subject_keywords=["tda", "ai-kos", "sqlite"])

        # Run 1: edge created (3 shared subject keywords ≥ min_evidence 3).
        # link_count is computed pre-patch, so run 1 writes 0; run 2 promotes
        # it to the true inbound count (1) via the silent patch.
        link_all(str(kd), mode="similarity")
        link_all(str(kd), mode="similarity")
        assert _fm(a_path)["link_count"] == 1
        assert _fm(b_path)["link_count"] == 1
        assert {x["slug"] for x in _fm(a_path)["related"]} == {"b"}

        # Remove the ONLY inbound link of BOTH articles: hand-edit both files
        # so no `related` edge remains and the shared subject tier is gone
        # (the algorithm must not re-create the edge).
        _write_md(a_path, "a", ["alpha"], subject_keywords=["tda", "ai-kos", "sqlite"], related=[])
        _write_md(b_path, "b", ["beta"], subject_keywords=["zeta", "eta", "theta"], related=[])

        # OLD code: `elif lc != 0` skipped the write when the true recomputed
        # count was 0 → stale link_count=1 stuck forever. Fixed: the true
        # recomputed count (0) is written on the next link_all.
        r3 = link_all(str(kd), mode="similarity")
        assert r3["articles_changed"] == 0
        assert _fm(a_path)["link_count"] == 0
        assert _fm(b_path)["link_count"] == 0
        assert _fm(a_path)["related"] == []
        assert _fm(b_path)["related"] == []


# ── Fix 4: dead config keys wired into consumers ─────────────────────────────

class TestDeadConfigKeysWired:
    def test_keys_retained_in_default_config_and_read_somewhere(self, monkeypatch):
        """Each retained key must be grep-able as a real get() read in the
        consuming module, and must still be present in _DEFAULT_CONFIG."""
        import ai_kos.config as cfg
        import ai_kos.articles as articles
        import ai_kos.linker as linker

        src_articles = Path(articles.__file__).read_text()
        src_linker = Path(linker.__file__).read_text()

        assert 'get("article", "target_keywords"' in src_articles
        assert 'get("article", "target_subject_keywords"' in src_articles
        assert 'get("article", "max_paragraphs"' in src_articles
        assert 'get("article", "summary_max_chars"' in src_articles
        assert 'get("linking", "link_budget", "importance", "explicit_field"' in src_linker

        monkeypatch.setattr(cfg, "_find_config", lambda: None)
        monkeypatch.setattr(cfg, "_config", None)
        c = cfg.load()
        for key in ("target_keywords", "target_subject_keywords",
                    "max_paragraphs", "summary_max_chars"):
            assert key in c["article"]
        assert c["linking"]["link_budget"]["importance"]["explicit_field"] == "importance"

    def test_summary_max_chars_validated_on_create(self, kb, monkeypatch):
        """summary_max_chars is the effective summary bound in create_article."""
        import ai_kos.config as cfg
        from ai_kos.articles import create_article

        cfg_file = kb / "config.yaml"
        user = yaml.safe_load(cfg_file.read_text())
        user["article"] = {"summary_max_chars": 20}
        cfg_file.write_text(yaml.dump(user))
        monkeypatch.setattr(cfg, "_config", None)

        long_summary = "This summary is deliberately far longer than twenty characters."
        r = create_article("base", _base_data("too-long", summary=long_summary))
        assert r.get("error", "").startswith("Summary too long")
        assert f"summary_max_chars=20" in r["error"]

        ok = create_article("base", _base_data("just-right", summary="Short summary."))
        assert ok["status"] == "created"

    def test_max_paragraphs_advisory_warning(self, kb, caplog):
        """max_paragraphs drives base-article paragraph guidance (advisory)."""
        from ai_kos.articles import create_article

        eight_paras = "\n\n".join(f"Paragraph {i}." for i in range(8))
        with caplog.at_level(logging.WARNING, logger="ai-kos.articles"):
            r = create_article("base", _base_data("long-body", content=eight_paras))
        assert r["status"] == "created"
        assert "exceeds max_paragraphs=5" in caplog.text

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="ai-kos.articles"):
            create_article("base", _base_data("short-body", content="One.\n\nTwo."))
        assert "exceeds max_paragraphs" not in caplog.text

    def test_target_keyword_advisory_warning(self, kb, caplog):
        """target_keywords drives the below-target advisory in _warn_keyword_counts."""
        from ai_kos.articles import create_article

        with caplog.at_level(logging.WARNING, logger="ai-kos.articles"):
            create_article("base", _base_data("few-kw", keywords=["lonely"]))
        assert "below target 10" in caplog.text

        caplog.clear()
        twelve = [f"kw{i:02d}" for i in range(12)]
        with caplog.at_level(logging.WARNING, logger="ai-kos.articles"):
            create_article("base", _base_data("enough-kw", keywords=twelve))
        assert "below target" not in caplog.text

    def test_explicit_field_configurable(self, kb_link, monkeypatch):
        """linking.link_budget.importance.explicit_field names the frontmatter
        field that carries the explicit importance override."""
        import ai_kos.config as cfg
        from ai_kos.linker import _parse_article

        cfg_file = kb_link / "config.yaml"
        user = yaml.safe_load(cfg_file.read_text())
        user.setdefault("linking", {})["link_budget"] = {
            "importance": {"explicit_field": "priority", "derived": True},
        }
        cfg_file.write_text(yaml.dump(user))
        monkeypatch.setattr(cfg, "_config", None)

        kd = kb_link / "knowledge"
        _write_md(kd / "bundles" / "general" / "p.md", "p", ["x"], priority=4)
        meta = _parse_article(str(kd / "bundles" / "general" / "p.md"))
        assert meta is not None
        assert meta.importance == 4  # read from the configured field, not 'importance'

        # Default field name still works when the config key is absent
        cfg_file2 = kb_link / "config2.yaml"
        cfg_file2.write_text(yaml.dump({"paths": {"knowledge_dir": str(kd)}}))
        monkeypatch.setattr(cfg, "_find_config", lambda: cfg_file2)
        monkeypatch.setattr(cfg, "_config", None)
        _write_md(kd / "bundles" / "general" / "q.md", "q", ["y"], importance=3)
        meta2 = _parse_article(str(kd / "bundles" / "general" / "q.md"))
        assert meta2 is not None
        assert meta2.importance == 3
