"""Tests for AI-KOS search — tokenizer, TF-IDF scoring, index building, compare."""

import tempfile, os, yaml
from pathlib import Path
from ai_kos.search import tokenize, SearchIndex, search as search_fn, compare as compare_fn


def make_kb_article(base_dir: str, slug: str, title: str, keywords: list[str],
                    summary: str = "", body: str = "", atype: str = "base"):
    """Create a knowledge article file."""
    fm = {
        "slug": slug, "title": title, "type": atype,
        "keywords": keywords, "summary": summary,
        "related": [],
    }
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, f"{slug}.md")
    with open(path, "w") as f:
        f.write("---\n")
        f.write(yaml.dump(fm, default_flow_style=False, sort_keys=False))
        f.write("---\n\n")
        f.write(body)
    return path


class TestTokenizer:
    def test_lowercases(self):
        assert tokenize("Hello WORLD") == ["hello", "world"]

    def test_removes_stop_words(self):
        tokens = tokenize("the quick brown fox is here")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "quick" in tokens

    def test_removes_short_tokens(self):
        tokens = tokenize("a bc def")
        assert "a" not in tokens
        assert "bc" in tokens
        assert "def" in tokens

    def test_extracts_alphanumeric(self):
        tokens = tokenize("hello world!!! 123 test")
        assert "123" in tokens
        assert "hello" in tokens

    def test_empty_input(self):
        assert tokenize("") == []


class TestSearchIndex:
    def test_build_and_search(self, tmp_path):
        kd = str(tmp_path)
        make_kb_article(kd, "python-testing", "Python Testing",
                        ["python", "testing", "pytest"],
                        "How to test Python code",
                        "Python unittest and pytest are popular frameworks.")
        make_kb_article(kd, "rust-concurrency", "Rust Concurrency",
                        ["rust", "concurrency", "async"],
                        "Rust async programming",
                        "Rust uses tokio for async runtime and channels for concurrency.")

        idx = SearchIndex()
        idx.build(kd)

        results = idx.search("python testing", top_k=5)
        assert len(results) > 0
        assert results[0]["slug"] == "python-testing"
        assert results[0]["score"] > 0

    def test_search_filters_by_type(self, tmp_path):
        kd = str(tmp_path)
        make_kb_article(kd, "one", "One", ["alpha"], atype="base")
        make_kb_article(kd, "two", "Two", ["alpha"], atype="process")

        idx = SearchIndex()
        idx.build(kd)

        all_results = idx.search("alpha")
        assert len(all_results) == 2

        filtered = idx.search("alpha", article_type="process")
        assert len(filtered) == 1
        assert filtered[0]["slug"] == "two"

    def test_build_is_incremental(self, tmp_path):
        kd = str(tmp_path)
        make_kb_article(kd, "first", "First", ["xx", "yy"])

        idx = SearchIndex()
        assert idx.build(kd) == 1

        make_kb_article(kd, "second", "Second", ["zz", "ww"])
        assert idx.build(kd) == 2

        results = idx.search("zz")
        assert results[0]["slug"] == "second"

    def test_force_rebuild(self, tmp_path):
        kd = str(tmp_path)
        make_kb_article(kd, "a", "A", ["xx"])

        idx = SearchIndex()
        idx.build(kd)
        assert idx.build(kd, force=True) == 1

    def test_empty_query(self):
        idx = SearchIndex()
        assert idx.search("") == []

    def test_no_docs(self, tmp_path):
        kd = str(tmp_path / "empty")
        os.makedirs(kd)
        idx = SearchIndex()
        assert idx.build(kd) == 0
        assert idx.search("anything") == []

    def test_compare_finds_similar(self, tmp_path):
        kd = str(tmp_path)
        make_kb_article(kd, "python-basics", "Python Basics",
                        ["python", "basics", "programming"],
                        body="Python is a high-level programming language. "
                             "It supports multiple paradigms including OOP and functional.")
        make_kb_article(kd, "python-advanced", "Python Advanced",
                        ["python", "advanced", "programming"],
                        body="Advanced Python topics include decorators, generators, "
                             "and metaclasses for metaprogramming.")
        make_kb_article(kd, "rust-intro", "Rust Intro",
                        ["rust", "systems", "programming"],
                        body="Rust is a systems programming language focused on safety.")

        idx = SearchIndex()
        idx.build(kd)

        similar = idx.compare("python-basics", top_k=5)
        assert len(similar) >= 1
        # python-advanced should be most similar
        assert similar[0]["slug"] == "python-advanced"

    def test_compare_unknown_slug(self):
        idx = SearchIndex()
        assert idx.compare("nonexistent") == []


class TestSearchModuleAPI:
    def test_search_module_function(self, tmp_path, monkeypatch):
        """Test the convenience search() function works."""
        from ai_kos import search as search_mod

        kd = str(tmp_path / "knowledge")
        make_kb_article(kd, "test", "Test", ["alpha", "beta"])

        # Build an index from our tmp dir and monkeypatch get_index to return it
        idx = search_mod.SearchIndex()
        idx.build(kd)
        monkeypatch.setattr(search_mod, "get_index", lambda: idx)

        results = search_mod.search("alpha")
        assert len(results) >= 1
        assert results[0]["slug"] == "test"

    def test_compare_module_function(self, tmp_path, monkeypatch):
        from ai_kos import search as search_mod

        kd = str(tmp_path / "knowledge")
        make_kb_article(kd, "a", "A", ["python"], body="Python content")
        make_kb_article(kd, "b", "B", ["python", "code"], body="Python code content")

        idx = search_mod.SearchIndex()
        idx.build(kd)
        monkeypatch.setattr(search_mod, "get_index", lambda: idx)

        results = search_mod.compare("a")
        assert len(results) >= 1
