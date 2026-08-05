"""Tests for AI-KOS schema migration system."""

import tempfile
from pathlib import Path

import pytest

from ai_kos.migrate import (
    run_migrations,
    list_pending,
    CURRENT_SCHEMA_VERSION,
    register,
)


@pytest.fixture
def kb_dir():
    """Create a temporary knowledge directory with sample articles."""
    d = Path(tempfile.mkdtemp())
    bundles = d / "bundles" / "general"
    bundles.mkdir(parents=True)

    # Article without schema_version
    (bundles / "no_version.md").write_text("""---
id: aaa
title: No Version
slug: no_version
type: base
created_at: 2026-01-01
updated_at: 2026-01-01
reviewed_at: 2026-01-01
next_review_at: 2027-01-01
keywords: [test]
summary: A test article
provenance: [test]
stability: moderate
---

Body content here.
""")

    # Article already at current version
    (bundles / "current.md").write_text(f"""---
id: bbb
title: Current Version
slug: current
type: base
created_at: 2026-01-01
updated_at: 2026-01-01
reviewed_at: 2026-01-01
next_review_at: 2027-01-01
keywords: [test]
summary: Already migrated
provenance: [test]
stability: moderate
schema_version: {CURRENT_SCHEMA_VERSION}
---

Already at current version.
""")

    # Article with version 0 (explicit zero)
    (bundles / "zero.md").write_text("""---
id: ccc
title: Zero Version
slug: zero
type: base
created_at: 2026-01-01
updated_at: 2026-01-01
reviewed_at: 2026-01-01
next_review_at: 2027-01-01
keywords: [test]
summary: Version zero
provenance: [test]
stability: moderate
schema_version: 0
---

Version zero body.
""")

    return str(d)


class TestMigrationBasics:
    def test_detect_pending_articles(self, kb_dir):
        pending = list_pending(knowledge_dir=kb_dir)
        assert len(pending) == 2  # no_version and zero
        slugs = {p["slug"] for p in pending}
        assert "no_version" in slugs
        assert "zero" in slugs
        assert "current" not in slugs

    def test_migrate_adds_schema_version(self, kb_dir):
        result = run_migrations(knowledge_dir=kb_dir)
        assert result["scanned"] == 3
        assert result["migrated"] == 2  # no_version and zero
        assert result["skipped"] == 1   # current already at v1
        assert result["errors"] == 0

        # Verify the migrated articles now have schema_version
        import yaml
        for slug in ["no_version", "zero"]:
            path = Path(kb_dir) / "bundles" / "general" / f"{slug}.md"
            content = path.read_text()
            fm = yaml.safe_load(content.split("---")[1])
            assert fm["schema_version"] == CURRENT_SCHEMA_VERSION

        # Current article unchanged
        path = Path(kb_dir) / "bundles" / "general" / "current.md"
        content = path.read_text()
        fm = yaml.safe_load(content.split("---")[1])
        assert fm["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_migrate_is_idempotent(self, kb_dir):
        # Run once
        r1 = run_migrations(knowledge_dir=kb_dir)
        assert r1["migrated"] == 2

        # Run again — should skip all
        r2 = run_migrations(knowledge_dir=kb_dir)
        assert r2["migrated"] == 0
        assert r2["skipped"] == 3

    def test_dry_run_does_not_write(self, kb_dir):
        result = run_migrations(knowledge_dir=kb_dir, dry_run=True)
        assert result["migrated"] == 2

        # Verify files were NOT modified
        path = Path(kb_dir) / "bundles" / "general" / "no_version.md"
        content = path.read_text()
        assert "schema_version" not in content.split("---")[1]

        details = {d["filepath"]: d for d in result["details"]}
        assert any(d["status"] == "would_migrate" for d in result["details"])

    def test_empty_knowledge_dir(self, tmp_path):
        result = run_migrations(knowledge_dir=str(tmp_path))
        assert result["scanned"] == 0
        assert result["migrated"] == 0

    def test_list_pending_empty(self, tmp_path):
        pending = list_pending(knowledge_dir=str(tmp_path))
        assert pending == []


class TestCustomMigration:
    def test_register_and_run_custom_migration(self, kb_dir):
        """Test that custom migrations can be registered and applied."""
        register_count = []

        @register(version=2, name="add_custom_field")
        def _add_custom(fm, body):
            fm["custom_field"] = "hello"
            register_count.append(1)
            return fm, body

        # First apply v1 — all 3 articles get schema_version: 1
        run_migrations(knowledge_dir=kb_dir, target_version=1)

        # Then apply v2 — all 3 now need v2 migration
        result = run_migrations(knowledge_dir=kb_dir, target_version=2)
        assert result["migrated"] == 3

        # Verify custom field was added
        import yaml
        path = Path(kb_dir) / "bundles" / "general" / "no_version.md"
        fm = yaml.safe_load(path.read_text().split("---")[1])
        assert fm["custom_field"] == "hello"
        assert fm["schema_version"] == 2

        # Clean up: remove the test migration from registry
        from ai_kos import migrate
        migrate._migrations[:] = [(v, n, f) for v, n, f in migrate._migrations if v != 2]
