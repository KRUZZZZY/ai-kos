"""Tests for AI-KOS schemas — validation, all 7 article types, edge cases."""

import pytest
from datetime import date, timedelta
from ai_kos.schemas import (
    BaseArticle, ProcessArticle, PlanArticle, HelpArticle,
    ResearchNoteArticle, NoteArticle, MissionArticle,
    ArticleType, Stability, SensitivityLabel,
    _BaseFrontmatter, article_to_markdown,
)

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
NEXT_YEAR = TODAY.replace(year=TODAY.year + 1)

BASE_DATA = {
    "id": "abc-123",
    "title": "Test Article",
    "slug": "test-article",
    "type": ArticleType.BASE,
    "created_at": YESTERDAY,
    "updated_at": TODAY,
    "reviewed_at": TODAY,
    "next_review_at": NEXT_YEAR,
    "keywords": ["test", "article", "example"],
    "summary": "A test article for validation.",
    "provenance": [{"source": "manual", "origin_ref": "test_source.md"}],
}


class TestBaseFrontmatter:
    def test_valid_base_article(self):
        a = BaseArticle(content="This is the article content.", **BASE_DATA)
        assert a.title == "Test Article"
        assert a.slug == "test-article"
        assert a.content == "This is the article content."

    def test_keywords_auto_lowercase_dedup(self):
        a = BaseArticle(
            content="test",
            **{**BASE_DATA, "keywords": ["TEST", "Test", "example"]},
        )
        assert a.keywords == ["test", "example"]

    def test_slug_pattern_rejects_uppercase(self):
        with pytest.raises(ValueError):
            BaseArticle(content="x", **{**BASE_DATA, "slug": "Bad-Slug"})

    def test_slug_pattern_rejects_spaces(self):
        with pytest.raises(ValueError):
            BaseArticle(content="x", **{**BASE_DATA, "slug": "bad slug"})

    def test_confidence_range(self):
        with pytest.raises(ValueError):
            BaseArticle(content="x", **{**BASE_DATA, "confidence": 1.5})

    def test_confidence_out_of_range_low(self):
        with pytest.raises(ValueError):
            BaseArticle(content="x", **{**BASE_DATA, "confidence": -0.1})

    def test_dates_must_be_ordered(self):
        with pytest.raises(ValueError, match="reviewed_at >= created_at"):
            BaseArticle(
                content="x",
                **{**BASE_DATA, "reviewed_at": BASE_DATA["created_at"] - timedelta(days=1)},
            )

    def test_gap_requires_question(self):
        with pytest.raises(ValueError, match="gap_question"):
            BaseArticle(
                content="x",
                **{**BASE_DATA, "gap": True, "gap_priority": 0.5},
            )

    def test_gap_requires_priority(self):
        with pytest.raises(ValueError, match="gap_priority"):
            BaseArticle(
                content="x",
                **{**BASE_DATA, "gap": True, "gap_question": "What?",
                "gap_priority": None},
            )

    def test_default_confidence(self):
        a = BaseArticle(
            content="x",
            **{k: v for k, v in BASE_DATA.items() if k != "confidence"},
        )
        assert a.confidence == 0.8

    def test_default_stability(self):
        a = BaseArticle(
            content="x",
            **{k: v for k, v in BASE_DATA.items() if k != "stability"},
        )
        assert a.stability == Stability.MODERATE

    def test_default_sensitivity(self):
        a = BaseArticle(
            content="x",
            **{k: v for k, v in BASE_DATA.items() if k != "sensitivity_label"},
        )
        assert a.sensitivity_label == SensitivityLabel.INTERNAL

    def test_summary_too_long(self):
        with pytest.raises(ValueError):
            BaseArticle(
                content="x",
                **{**BASE_DATA, "summary": "x" * 400},
            )


class TestAllArticleTypes:
    def test_process_article(self):
        a = ProcessArticle(
            steps=["Step one", "Step two"],
            outcome="It works.",
            **BASE_DATA,
        )
        assert a.steps == ["Step one", "Step two"]
        assert a.outcome == "It works."

    def test_process_article_empty_steps(self):
        with pytest.raises(ValueError):
            ProcessArticle(steps=[], outcome="Done.", **BASE_DATA)

    def test_plan_article(self):
        a = PlanArticle(
            goal="Build something great.",
            phases=["Phase 1", "Phase 2"],
            milestones=["M1"],
            risks=["Risk 1"],
            **BASE_DATA,
        )
        assert a.goal == "Build something great."
        assert len(a.phases) == 2

    def test_help_article(self):
        a = HelpArticle(
            project="AI-KOS",
            component="Linker",
            explanation="How the linker works.",
            examples=["Example 1"],
            **BASE_DATA,
        )
        assert a.project == "AI-KOS"
        assert a.component == "Linker"

    def test_research_note(self):
        a = ResearchNoteArticle(
            topic="Deep Research",
            key_notes=["Note 1", "Note 2"],
            open_questions=["Q1"],
            sources=["https://example.com"],
            **BASE_DATA,
        )
        assert a.topic == "Deep Research"
        assert len(a.key_notes) == 2

    def test_note_article(self):
        a = NoteArticle(
            content="Temporary thought.",
            related_project="AI-KOS",
            actionable=True,
            **BASE_DATA,
        )
        assert a.actionable is True

    def test_mission_article(self):
        a = MissionArticle(
            project="AI-KOS",
            purpose="Build a self-building KB.",
            architecture="Python package with MCP server.",
            dependencies=["pydantic"],
            success_criteria=["All tests pass"],
            **BASE_DATA,
        )
        assert a.project == "AI-KOS"
        assert "Python package" in a.architecture


class TestArticleToMarkdown:
    def test_base_article_markdown(self):
        a = BaseArticle(content="Hello world.", **BASE_DATA)
        md = article_to_markdown(a)
        assert md.startswith("---")
        assert "Hello world." in md
        assert "type/base" in md  # Obsidian tag

    def test_process_article_markdown(self):
        # Don't use BASE_DATA.type since it's ArticleType.BASE
        data = {k: v for k, v in BASE_DATA.items() if k != "type"}
        a = ProcessArticle(
            steps=["Do X", "Do Y"],
            outcome="Success.",
            **data,
        )
        md = article_to_markdown(a)
        assert "## Outcome" in md
        assert "Do X" in md
        assert "## Steps" in md

    def test_related_generates_wikilinks(self):
        a = BaseArticle(
            content="x",
            **{**BASE_DATA, "related": ["alpha", "beta"]},
        )
        md = article_to_markdown(a)
        assert "[[alpha]]" in md
        assert "[[beta]]" in md
