"""Tests for AI-KOS linker — keyword overlap, merge detection, link_all."""

import tempfile, os, yaml
from pathlib import Path
from ai_kos.linker import (
    _parse_article, _calculate_links, link_all, ArticleMeta,
    MIN_KEYWORD_OVERLAP, MERGE_THRESHOLD,
)


def make_article(path: str, slug: str, keywords: list[str], related: list[str] | None = None):
    """Create a temporary markdown article with frontmatter."""
    if related is None:
        related = []
    fm = {
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "type": "base",
        "keywords": keywords,
        "related": related or [],
        "summary": f"Article about {slug}",
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("---\n")
        f.write(yaml.dump(fm, default_flow_style=False, sort_keys=False))
        f.write("---\n\nBody content.\n")


class TestParseArticle:
    def test_parses_valid_article(self, tmp_path):
        p = tmp_path / "test.md"
        make_article(str(p), "test", ["alpha", "beta"])
        meta = _parse_article(str(p))
        assert meta is not None
        assert meta.slug == "test"
        assert meta.keywords == {"alpha", "beta"}
        assert meta.related == []

    def test_parses_related(self, tmp_path):
        p = tmp_path / "linked.md"
        make_article(str(p), "linked", ["x", "y", "z"], related=["a", "b"])
        meta = _parse_article(str(p))
        assert meta.related == ["a", "b"]

    def test_returns_none_for_no_frontmatter(self, tmp_path):
        p = tmp_path / "plain.md"
        p.write_text("Just plain text.")
        assert _parse_article(str(p)) is None

    def test_returns_none_for_missing_file(self):
        assert _parse_article("/nonexistent/file.md") is None


class TestCalculateLinks:
    def test_no_overlap_no_links(self):
        articles = [
            ArticleMeta("a", "", {"x", "y", "z"}, []),
            ArticleMeta("b", "", {"p", "q", "r"}, []),
        ]
        links, merges = _calculate_links(articles)
        assert links["a"] == set()
        assert links["b"] == set()
        assert merges == []

    def test_exact_three_shared_creates_link(self):
        articles = [
            ArticleMeta("a", "", {"x", "y", "z"}, []),
            ArticleMeta("b", "", {"x", "y", "z", "w"}, []),
        ]
        links, merges = _calculate_links(articles)
        assert links["a"] == {"b"}
        assert links["b"] == {"a"}

    def test_two_shared_no_link(self):
        articles = [
            ArticleMeta("a", "", {"x", "y"}, []),
            ArticleMeta("b", "", {"x", "y", "z"}, []),
        ]
        links, merges = _calculate_links(articles)
        assert links["a"] == set()

    def test_merge_candidate_detected(self):
        # 4 keywords each, overlap=4, ratio=1.0 > 0.80
        articles = [
            ArticleMeta("a", "", {"a", "b", "c", "d"}, []),
            ArticleMeta("b", "", {"a", "b", "c", "d"}, []),
        ]
        links, merges = _calculate_links(articles)
        assert len(merges) == 1
        assert merges[0][2] >= MERGE_THRESHOLD

    def test_no_merge_candidate_below_threshold(self):
        articles = [
            ArticleMeta("a", "", {"a", "b", "c", "d", "e"}, []),
            ArticleMeta("b", "", {"a", "b", "f", "g", "h"}, []),
        ]
        links, merges = _calculate_links(articles)
        assert merges == []

    def test_bidirectional_links(self):
        articles = [
            ArticleMeta("a", "", {"1", "2", "3"}, []),
            ArticleMeta("b", "", {"1", "2", "3", "4"}, []),
            ArticleMeta("c", "", {"1", "2", "3", "5"}, []),
        ]
        links, merges = _calculate_links(articles)
        assert links["a"] == {"b", "c"}
        assert links["b"] == {"a", "c"}
        assert links["c"] == {"a", "b"}


class TestLinkAll:
    def test_link_all_creates_links(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        make_article(str(kd / "a.md"), "a", ["python", "testing", "ai"])
        make_article(str(kd / "b.md"), "b", ["python", "testing", "ai"])
        make_article(str(kd / "c.md"), "c", ["rust", "systems", "embedded"])

        result = link_all(str(kd))

        assert result["articles_scanned"] == 3
        assert result["total_links_created"] > 0

        # Verify a.md was patched with links to b
        with open(kd / "a.md") as f:
            content = f.read()
        fm = yaml.safe_load(content.split("---")[1])
        assert "b" in fm["related"]

        # c should not link to anything (no overlap)
        with open(kd / "c.md") as f:
            content = f.read()
        fm = yaml.safe_load(content.split("---")[1])
        assert fm["related"] == []

    def test_link_all_idempotent(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        make_article(str(kd / "x.md"), "x", ["a", "b", "c"])
        make_article(str(kd / "y.md"), "y", ["a", "b", "c", "d"])

        result1 = link_all(str(kd))
        result2 = link_all(str(kd))

        assert result2["articles_changed"] == 0
        assert result2["total_links_created"] == result1["total_links_created"]

    def test_link_all_empty_dir(self, tmp_path):
        kd = tmp_path / "empty"
        kd.mkdir()
        result = link_all(str(kd))
        assert result["status"] == "no_articles"
