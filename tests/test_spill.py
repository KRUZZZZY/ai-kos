"""Tests for ai_kos.spill — oversized tool output → session-scoped file + preview."""

import pytest
from pathlib import Path


class TestSpill:
    def test_spill_retrieve_roundtrip(self, tmp_path):
        from ai_kos.spill import spill, retrieve
        ref = spill("hello world", "extract", spill_dir=str(tmp_path / "spills"),
                    session_id="s1")
        assert retrieve(ref.locator, spill_dir=str(tmp_path / "spills")) == "hello world"

    def test_preview_truncation_and_marker(self, tmp_path):
        from ai_kos.spill import spill
        ref = spill("abcdefghij", "x", spill_dir=str(tmp_path / "spills"), preview_chars=4)
        assert ref.truncated is True
        assert ref.preview.startswith("abcd")
        assert "truncated" in ref.preview
        assert "…" in ref.preview

    def test_preview_not_truncated_when_small(self, tmp_path):
        from ai_kos.spill import spill
        ref = spill("short", "x", spill_dir=str(tmp_path / "spills"), preview_chars=100)
        assert ref.truncated is False
        assert ref.preview == "short"

    def test_locator_format(self, tmp_path):
        from ai_kos.spill import spill
        ref = spill("data", "results", spill_dir=str(tmp_path / "spills"), session_id="sess-1")
        assert ref.locator.startswith("spill:sess-1/")
        assert ref.locator.endswith(".txt")
        assert "results" in ref.locator

    def test_size_bytes_recorded(self, tmp_path):
        from ai_kos.spill import spill
        text = "hello"
        ref = spill(text, "x", spill_dir=str(tmp_path / "spills"))
        assert ref.size_bytes == len(text.encode("utf-8"))
        assert Path(ref.path).exists()

    def test_retrieve_unknown_locator_raises(self, tmp_path):
        from ai_kos.spill import retrieve, SpillError
        with pytest.raises(SpillError):
            retrieve("spill:nope/missing.txt", spill_dir=str(tmp_path / "spills"))

    def test_retrieve_non_spill_locator_raises(self, tmp_path):
        from ai_kos.spill import retrieve, SpillError
        with pytest.raises(SpillError):
            retrieve("not-a-locator", spill_dir=str(tmp_path / "spills"))

    def test_session_scoped_dirs_isolate(self, tmp_path):
        from ai_kos.spill import spill
        r1 = spill("a", "n", spill_dir=str(tmp_path / "spills"), session_id="one")
        r2 = spill("b", "n", spill_dir=str(tmp_path / "spills"), session_id="two")
        assert r1.locator != r2.locator
        assert "spill:one/" in r1.locator
        assert "spill:two/" in r2.locator


class TestSpillPolicy:
    def test_small_text_passes_through(self, tmp_path):
        from ai_kos.spill import apply_spill_policy, SpillRef
        out = apply_spill_policy("small text", "x", max_chars=100,
                                 spill_dir=str(tmp_path / "spills"))
        assert out == "small text"
        assert not isinstance(out, SpillRef)

    def test_large_text_returns_ref(self, tmp_path):
        from ai_kos.spill import apply_spill_policy, SpillRef
        out = apply_spill_policy("x" * 200, "big", max_chars=100,
                                 spill_dir=str(tmp_path / "spills"))
        assert isinstance(out, SpillRef)
        assert out.locator.startswith("spill:")


class TestDefaultSpillDir:
    def test_config_override(self, tmp_path, monkeypatch):
        from ai_kos import config
        custom = str(tmp_path / "custom-spills")
        monkeypatch.setattr(config, "_config", {"paths": {"spills_dir": custom}})
        from ai_kos.spill import default_spill_dir
        assert default_spill_dir() == Path(custom)

    def test_fallback_default(self, monkeypatch):
        from ai_kos import config
        monkeypatch.setattr(config, "_config", None)
        monkeypatch.setattr(config, "_find_config", lambda: None)
        from ai_kos.spill import default_spill_dir
        assert str(default_spill_dir()).endswith("datasets/spills")


class TestDeepResearchIntegration:
    def test_spill_if_large(self, tmp_path):
        from ai_kos.deep_research import spill_if_large
        from ai_kos.spill import SpillRef
        assert spill_if_large("short", "extract",
                              spill_dir=str(tmp_path / "spills")) == "short"
        ref = spill_if_large("x" * 5000, "extract", spill_dir=str(tmp_path / "spills"))
        assert isinstance(ref, SpillRef)
        assert ref.locator.startswith("spill:")

    def test_spill_if_large_threshold_boundary(self, tmp_path):
        from ai_kos.deep_research import spill_if_large
        from ai_kos.spill import SpillRef
        # exactly at threshold → unchanged
        assert spill_if_large("x" * 4000, "extract",
                              spill_dir=str(tmp_path / "spills")) == "x" * 4000
        # one over → ref
        ref = spill_if_large("x" * 4001, "extract", spill_dir=str(tmp_path / "spills"))
        assert isinstance(ref, SpillRef)
