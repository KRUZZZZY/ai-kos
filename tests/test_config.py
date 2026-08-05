"""Tests for AI-KOS config — defaults, custom config, merging."""

import tempfile, os, yaml
from pathlib import Path


class TestConfigDefaults:
    def test_default_values(self):
        import ai_kos.config as cfg
        cfg._config = None
        orig_find = cfg._find_config
        cfg._find_config = lambda: None
        try:
            c = cfg.load()
            assert c["linking"]["min_keyword_overlap"] == 2   # default, not overridden
            assert c["linking"]["merge_threshold"] == 0.80
            assert c["article"]["max_paragraphs"] == 5
            assert c["paths"]["knowledge_dir"] == "knowledge"
        finally:
            cfg._find_config = orig_find
            cfg._config = None

    def test_get_helper(self):
        import ai_kos.config as cfg
        cfg._config = None
        orig_find = cfg._find_config
        cfg._find_config = lambda: None
        try:
            assert cfg.get("linking", "min_keyword_overlap") == 2
            assert cfg.get("paths", "knowledge_dir") == "knowledge"
            assert cfg.get("nonexistent", "key", default="fallback") == "fallback"
        finally:
            cfg._find_config = orig_find
            cfg._config = None

    def test_get_returns_default_for_missing_nested(self):
        from ai_kos.config import get, _config
        import ai_kos.config as cfg
        cfg._config = None
        assert get("bogus", "nested", "deep", default=42) == 42

    def test_load_is_idempotent(self):
        import ai_kos.config as cfg
        cfg._config = None
        c1 = cfg.load()
        c2 = cfg.load()
        assert c1 is c2


class TestConfigWithCustomFile:
    def test_loads_custom_config(self, tmp_path):
        """Custom config deep-merges over defaults: overrides override, additions add, untouched stay."""
        import ai_kos.config as cfg
        cfg._config = None

        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump({
            "linking": {"min_keyword_overlap": 5},
            "paths": {"custom_path": "/tmp/custom"},
        }))

        # Monkey-patch the config finder
        original_find = cfg._find_config
        cfg._find_config = lambda: config_path

        try:
            c = cfg.load()
            # Override merged
            assert c["linking"]["min_keyword_overlap"] == 5
            # Original preserved
            assert c["linking"]["merge_threshold"] == 0.80
            # New key added
            assert c["paths"]["custom_path"] == "/tmp/custom"
            # knowledge_dir present (from defaults — "knowledge" without ambient config)
            assert "knowledge_dir" in c["paths"]
        finally:
            cfg._find_config = original_find
            cfg._config = None

    def test_deep_merge_nested(self):
        from ai_kos.config import _deep_merge

        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}}
        _deep_merge(base, override)

        assert base["a"]["x"] == 1      # preserved
        assert base["a"]["y"] == 99     # overridden
        assert base["a"]["z"] == 100    # added
        assert base["b"] == 3           # untouched
