"""Tests for ai_kos.skills — skill catalog + loader (KB provider + registry)."""

import pytest
from pathlib import Path


def _setup_kb(tmp_path, monkeypatch):
    """Create a tmp knowledge dir with a few skill-typed articles."""
    from datetime import date
    import uuid
    kd = str(tmp_path / "knowledge")
    monkeypatch.setattr("ai_kos.articles.KNOWLEDGE_DIR", kd)
    monkeypatch.setattr("ai_kos.linker.KNOWLEDGE_DIR", kd, raising=False)

    from ai_kos.articles import create_article, _refresh_index
    _refresh_index()

    today = date.today()
    base = {
        "id": str(uuid.uuid4()),
        "created_at": today, "updated_at": today, "reviewed_at": today,
        "next_review_at": date(2027, 1, 1),
        "provenance": [{"source": "manual"}],
    }

    create_article("procedure", {**base, "title": "Deploy Service", "slug": "deploy-service",
        "keywords": ["deploy", "service"], "summary": "How to deploy the service.",
        "task_id": 1, "objective": "Deploy the service.", "approach": "Run the script.",
        "verification": "Check health."})
    create_article("process", {**base, "title": "Backup Procedure", "slug": "backup-procedure",
        "keywords": ["backup", "ops"], "summary": "How to run backups.",
        "steps": ["Step 1", "Step 2"], "outcome": "Backup complete."})
    create_article("base", {**base, "title": "Knowledge Graph", "slug": "knowledge-graph",
        "keywords": ["graph", "knowledge"], "summary": "What a knowledge graph is.",
        "content": "A knowledge graph is a structured representation of facts."})
    create_article("research-note", {**base, "title": "Research: Spill", "slug": "research-spill",
        "keywords": ["spill", "research"], "summary": "Notes on spill.",
        "topic": "Spill", "key_notes": ["note 1"]})
    create_article("note", {**base, "title": "Scratch Note", "slug": "scratch-note",
        "keywords": ["scratch"], "summary": "A temporary note.",
        "content": "temp content"})
    return kd


class TestKBProvider:
    def test_catalog_rank_ordering(self, tmp_path, monkeypatch):
        _setup_kb(tmp_path, monkeypatch)
        from ai_kos.skills import skill_catalog
        cats = skill_catalog()
        names = [c.name for c in cats]
        # procedure(100) < process(80) < base(40) < research-note(20)
        assert names.index("deploy-service") < names.index("backup-procedure")
        assert names.index("backup-procedure") < names.index("knowledge-graph")
        assert names.index("knowledge-graph") < names.index("research-spill")

    def test_catalog_excludes_non_skill_types(self, tmp_path, monkeypatch):
        _setup_kb(tmp_path, monkeypatch)
        from ai_kos.skills import skill_catalog
        names = [c.name for c in skill_catalog()]
        assert "scratch-note" not in names  # 'note' has no rank

    def test_candidate_shape(self, tmp_path, monkeypatch):
        _setup_kb(tmp_path, monkeypatch)
        from ai_kos.skills import skill_catalog
        cats = {c.name: c for c in skill_catalog()}
        c = cats["deploy-service"]
        assert c.rank == 100
        assert c.slug == "deploy-service"
        assert c.provider == "kb-articles"
        assert c.description == "How to deploy the service."

    def test_skill_load_roundtrip(self, tmp_path, monkeypatch):
        _setup_kb(tmp_path, monkeypatch)
        from ai_kos.skills import skill_load
        sd = skill_load("deploy-service")
        assert sd is not None
        assert sd.name == "deploy-service"
        assert "Deploy Service" in sd.body
        assert sd.meta["type"] == "procedure"
        assert sd.meta["slug"] == "deploy-service"

    def test_skill_load_unknown_returns_none(self, tmp_path, monkeypatch):
        _setup_kb(tmp_path, monkeypatch)
        from ai_kos.skills import skill_load
        assert skill_load("does-not-exist") is None


class TestSkillRegistry:
    @staticmethod
    def _stub_provider(name, cand_name, desc, rank, body, slug=None):
        from ai_kos.skills import SkillCandidate, SkillDefinition
        class P:
            def __init__(self):
                self.name = name
            def list(self):
                return [SkillCandidate(cand_name, desc, rank, name, slug or cand_name)]
            def get(self, c):
                return SkillDefinition(cand_name, body, {})
        return P()

    def test_catalog_sorted_by_rank_then_name(self):
        from ai_kos.skills import SkillRegistry
        r = SkillRegistry()
        r.register(self._stub_provider("p", "low", "d", 10, "b"), layer="global")
        r.register(self._stub_provider("p2", "high-b", "d", 90, "b"), layer="global")
        r.register(self._stub_provider("p3", "high-a", "d", 90, "b"), layer="global")
        cats = r.catalog()
        names = [c.name for c in cats]
        assert names == ["high-a", "high-b", "low"]  # rank desc, name asc

    def test_layer_precedence_scope_wins(self):
        from ai_kos.skills import SkillRegistry
        r = SkillRegistry()
        r.register(self._stub_provider("global-p", "foo", "global", 50, "GLOBAL"), layer="global")
        r.register(self._stub_provider("scope-p", "foo", "scope", 50, "SCOPE"), layer="scope")
        cats = r.catalog()
        foos = [c for c in cats if c.name == "foo"]
        assert len(foos) == 1
        assert foos[0].provider == "scope-p"
        assert r.load("foo").body == "SCOPE"

    def test_layer_precedence_registration_order_agnostic(self):
        from ai_kos.skills import SkillRegistry
        r = SkillRegistry()
        r.register(self._stub_provider("scope-p", "foo", "scope", 50, "SCOPE"), layer="scope")
        r.register(self._stub_provider("global-p", "foo", "global", 50, "GLOBAL"), layer="global")
        assert r.load("foo").body == "SCOPE"

    def test_invalidate_bumps_version(self):
        from ai_kos.skills import SkillRegistry
        r = SkillRegistry()
        v1 = r.catalog_version()
        r.invalidate()
        v2 = r.catalog_version()
        assert v2 > v1

    def test_load_missing_returns_none(self):
        from ai_kos.skills import SkillRegistry
        r = SkillRegistry()
        assert r.load("nope") is None

    def test_unknown_layer_raises(self):
        from ai_kos.skills import SkillRegistry
        r = SkillRegistry()
        with pytest.raises(ValueError):
            r.register(self._stub_provider("p", "x", "d", 1, "b"), layer="bogus")


class TestMcpDispatch:
    def test_skill_catalog_dispatch(self, tmp_path, monkeypatch):
        _setup_kb(tmp_path, monkeypatch)
        from ai_kos.mcp_server import _dispatch_tool
        result = _dispatch_tool("ai_kos_skill_catalog", {})
        assert "skills" in result
        assert "total" in result
        assert "version" in result
        assert result["total"] >= 4
        names = [s["name"] for s in result["skills"]]
        assert "deploy-service" in names
        assert "scratch-note" not in names

    def test_skill_load_dispatch(self, tmp_path, monkeypatch):
        _setup_kb(tmp_path, monkeypatch)
        from ai_kos.mcp_server import _dispatch_tool
        result = _dispatch_tool("ai_kos_skill_load", {"name": "deploy-service"})
        assert "skill" in result
        assert result["skill"]["name"] == "deploy-service"
        assert "body" in result["skill"]
        assert "meta" in result["skill"]

    def test_skill_load_dispatch_missing(self, tmp_path, monkeypatch):
        _setup_kb(tmp_path, monkeypatch)
        from ai_kos.mcp_server import _dispatch_tool
        result = _dispatch_tool("ai_kos_skill_load", {"name": "does-not-exist"})
        assert result == {"error": "skill not found"}
