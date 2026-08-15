"""Tests for ai_kos.skill_backup — SKILL.md → process-article generation."""

import json
from pathlib import Path

import pytest

from ai_kos.skill_backup import (
    USAGE_FILE,
    build_article_dict,
    backup_skills,
    skill_backup,
    _extract_steps,
    _parse_skill,
    _sanitize_slug,
)

SAMPLE_SKILL = """---
name: sample-proc
description: Run the sample procedure when you need to do the thing.
version: 1.0.0
tags: [sample, procedure, demo]
required_environment_variables: [SAMPLE_KEY]
required_commands: [sample-cli]
---

# Sample Proc

## When to use
- Use when you need to do the thing.

## Workflow (numbered, exact)
1. Check the thing exists.
2. Run sample-cli with the flag.
3. Verify the output.
4. Clean up.

## Pitfalls
- Never skip step 2.
"""


def _write_skill(tmp_path: Path, name: str, content: str) -> Path:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(content)
    return p


class TestSanitize:
    def test_lowercases_and_hyphenates(self):
        assert _sanitize_slug("AI-KOS v1.7!") == "ai-kos-v1-7"

    def test_empty_falls_back(self):
        assert _sanitize_slug("") == "skill-backup"

    def test_dots_underscores_stripped(self):
        assert _sanitize_slug("my_skill.name") == "my-skill-name"


class TestParseSkill:
    def test_parses_frontmatter_and_body(self, tmp_path):
        p = _write_skill(tmp_path, "sample-proc", SAMPLE_SKILL)
        skill = _parse_skill(p)
        assert skill["name"] == "sample-proc"
        assert skill["title"] == "sample-proc"
        assert "Workflow" in skill["body"]
        assert skill["env"] == ["SAMPLE_KEY"]
        assert skill["cmds"] == ["sample-cli"]

    def test_no_frontmatter_returns_empty(self, tmp_path):
        p = tmp_path / "plain" / "SKILL.md"
        p.parent.mkdir()
        p.write_text("# no frontmatter")
        assert _parse_skill(p) == {}


class TestExtractSteps:
    def test_numbered_items_picked(self):
        body = "1. First\n2. Second\n- Third bullet"
        steps = _extract_steps(body)
        assert steps == ["First", "Second", "Third bullet"]

    def test_falls_back_to_headings_when_few_items(self):
        body = "## One\n## Two\n## Three\n## Four"
        assert _extract_steps(body) == ["One", "Two", "Three", "Four"]

    def test_caps_at_max(self):
        body = "\n".join(f"{i}. step {i}" for i in range(50))
        assert len(_extract_steps(body)) == 30


class TestBuildArticleDict:
    def test_full_shape(self, tmp_path):
        p = _write_skill(tmp_path, "sample-proc", SAMPLE_SKILL)
        skill = _parse_skill(p)
        data = build_article_dict(skill, p)
        assert data["slug"] == "skill-sample-proc"
        assert data["type"] == "process"
        assert "sample" in data["keywords"]
        assert len(data["keywords"]) >= 3
        assert len(data["summary"]) <= 300
        assert data["provenance"] == [{"source": "import", "origin_ref": str(p)}]
        assert "Check the thing exists." in data["steps"]
        assert data["outcome"]
        assert data["prerequisites"] == ["SAMPLE_KEY", "sample-cli"]

    def test_slug_namespaced(self, tmp_path):
        p = _write_skill(tmp_path, "ai-kos", SAMPLE_SKILL.replace("sample-proc", "ai-kos"))
        data = build_article_dict(_parse_skill(p), p)
        assert data["slug"] == "skill-ai-kos"

    def test_keywords_fall_back_to_description(self, tmp_path):
        no_tags = "---\nname: security-audit\ndescription: Blind security audit of a codebase with deep clone and git archaeology.\n---\n\n1. Do the audit."
        p = _write_skill(tmp_path, "security-audit", no_tags)
        data = build_article_dict(_parse_skill(p), p)
        assert len(data["keywords"]) >= 3
        assert "audit" in data["keywords"]

    def test_steps_never_empty(self, tmp_path):
        p = _write_skill(tmp_path, "bare", "---\nname: bare\ntags: [a, b, c]\n---\n\nNo steps here.")
        data = build_article_dict(_parse_skill(p), p)
        assert len(data["steps"]) >= 1


class TestSkillBackup:
    def test_dry_run_writes_nothing(self, tmp_path, monkeypatch):
        p = _write_skill(tmp_path, "sample-proc", SAMPLE_SKILL)
        called = []
        import ai_kos.articles as arts
        monkeypatch.setattr(arts, "create_article", lambda *a, **k: called.append(a) or {"slug": "x"})
        monkeypatch.setattr(arts, "read_article", lambda s: None)
        out = skill_backup(p, dry_run=True)
        assert "dry_run" in out
        assert called == []  # create_article never called

    def test_existing_slug_skipped(self, tmp_path, monkeypatch):
        p = _write_skill(tmp_path, "sample-proc", SAMPLE_SKILL)
        import ai_kos.articles as arts
        monkeypatch.setattr(arts, "read_article", lambda s: {"slug": s})
        out = skill_backup(p)
        assert out["skipped"] == "skill-sample-proc"

    def test_creates_article(self, tmp_path, monkeypatch):
        p = _write_skill(tmp_path, "sample-proc", SAMPLE_SKILL)
        captured = {}
        import ai_kos.articles as arts
        monkeypatch.setattr(arts, "read_article", lambda s: None)
        monkeypatch.setattr(arts, "create_article", lambda t, d: captured.update(type=t, data=d) or d)
        out = skill_backup(p)
        assert captured["type"] == "process"
        assert captured["data"]["slug"] == "skill-sample-proc"

    def test_parse_error_reported(self, tmp_path, monkeypatch):
        p = tmp_path / "bad" / "SKILL.md"
        p.parent.mkdir()
        p.write_text("# no frontmatter")
        import ai_kos.articles as arts
        monkeypatch.setattr(arts, "read_article", lambda s: None)
        out = skill_backup(p)
        assert "error" in out


class TestBackupSkills:
    def _fake_registry(self, tmp_path, monkeypatch, existing=()):
        """Usage.json marks only 'mine' as agent-created; read_article is a stub."""
        d = tmp_path / "skills"
        d.mkdir()
        (d / USAGE_FILE).write_text(json.dumps({"mine": {"created_by": "agent"},
                                                 "theirs": {"created_by": None}}))
        _write_skill(d, "mine", SAMPLE_SKILL.replace("sample-proc", "mine"))
        _write_skill(d, "theirs", SAMPLE_SKILL.replace("sample-proc", "theirs"))
        import ai_kos.articles as arts
        created = []
        monkeypatch.setattr(arts, "read_article", lambda s: None if s not in existing else {"slug": s})
        monkeypatch.setattr(arts, "create_article",
                            lambda t, d: created.append(d["slug"]) or {"slug": d["slug"]})
        return d, created

    def test_only_agent_created_by_default(self, tmp_path, monkeypatch):
        d, created = self._fake_registry(tmp_path, monkeypatch)
        res = backup_skills(skills_dir=d)
        assert created == ["skill-mine"]
        assert "skill-theirs" not in created

    def test_all_flag_includes_bundled(self, tmp_path, monkeypatch):
        d, created = self._fake_registry(tmp_path, monkeypatch)
        backup_skills(skills_dir=d, only_agent_created=False)
        assert set(created) == {"skill-mine", "skill-theirs"}

    def test_dry_run_no_creates(self, tmp_path, monkeypatch):
        d, created = self._fake_registry(tmp_path, monkeypatch)
        res = backup_skills(skills_dir=d, dry_run=True)
        assert created == []
        assert res["dry_run"] == ["skill-mine"]

    def test_limit(self, tmp_path, monkeypatch):
        d, created = self._fake_registry(tmp_path, monkeypatch)
        res = backup_skills(skills_dir=d, limit=1)
        assert len(created) == 1
        assert res["total"] == 1

    def test_idempotent_second_run_skips(self, tmp_path, monkeypatch):
        d, created = self._fake_registry(tmp_path, monkeypatch)
        backup_skills(skills_dir=d)
        # second run: read_article now finds the created slug
        import ai_kos.articles as arts
        monkeypatch.setattr(arts, "read_article", lambda s: {"slug": s})
        res = backup_skills(skills_dir=d)
        assert res["created"] == []
        assert res["skipped"] == ["skill-mine"]
