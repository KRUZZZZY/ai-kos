"""Tests for AI-KOS DeclarativeBindings — Pydantic Settings for tool config."""

import os
import tempfile
from pathlib import Path

import pytest

from ai_kos.bindings import (
    Bindings,
    get_bindings,
    reset_bindings,
    kb_path,
    inbox_path,
    templates_path,
)


@pytest.fixture(autouse=True)
def _reset():
    """Reset bindings singleton before each test."""
    reset_bindings()
    yield
    reset_bindings()


class TestBindingsDefaults:
    def test_default_values(self):
        b = Bindings()
        assert b.knowledge_dir == "knowledge"
        assert b.inbox_dir == "inbox"
        assert b.templates_dir == "templates"
        assert b.archive_dir == "archive"
        assert b.rejected_dir == "rejected"
        assert b.projects_dir == "projects"
        assert b.min_keyword_overlap == 2
        assert b.merge_threshold == 0.80
        assert b.semantic_enabled is True
        assert b.semantic_threshold == 0.7
        assert b.taskqueue_max_workers == 3
        assert b.taskqueue_max_retries == 3
        assert b.taskqueue_retry_delay == 2.0

    def test_custom_values(self):
        b = Bindings(
            knowledge_dir="/custom/kb",
            min_keyword_overlap=5,
            taskqueue_max_workers=8,
        )
        assert b.knowledge_dir == "/custom/kb"
        assert b.min_keyword_overlap == 5
        assert b.taskqueue_max_workers == 8
        # Other values remain default
        assert b.inbox_dir == "inbox"

    def test_validation_min_keyword_overlap(self):
        with pytest.raises(Exception):
            Bindings(min_keyword_overlap=0)

    def test_validation_merge_threshold(self):
        with pytest.raises(Exception):
            Bindings(merge_threshold=1.5)


class TestBindingsFromEnv:
    def test_env_override(self):
        os.environ["AI_KOS_KNOWLEDGE_DIR"] = "/env/kb"
        os.environ["AI_KOS_MIN_KEYWORD_OVERLAP"] = "4"
        try:
            b = Bindings()
            assert b.knowledge_dir == "/env/kb"
            assert b.min_keyword_overlap == 4
        finally:
            del os.environ["AI_KOS_KNOWLEDGE_DIR"]
            del os.environ["AI_KOS_MIN_KEYWORD_OVERLAP"]


class TestBindingsFromConfigYaml:
    def test_loads_paths_from_config(self):
        config = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        config.write("""
paths:
  knowledge_dir: custom_knowledge
  inbox_dir: custom_inbox
  archive_dir: custom_archive
linking:
  min_keyword_overlap: 4
  merge_threshold: 0.85
""")
        config.close()

        try:
            b = Bindings.from_config_yaml(config.name)
            assert b.knowledge_dir == "custom_knowledge"
            assert b.inbox_dir == "custom_inbox"
            assert b.archive_dir == "custom_archive"
            assert b.min_keyword_overlap == 4
            assert b.merge_threshold == 0.85
            # Unspecified values remain default
            assert b.templates_dir == "templates"
        finally:
            os.unlink(config.name)

    def test_missing_config_returns_defaults(self):
        b = Bindings.from_config_yaml("/tmp/nonexistent_config.yaml")
        assert b.knowledge_dir == "knowledge"


class TestBindingsSingleton:
    def test_get_bindings_returns_singleton(self):
        b1 = get_bindings()
        b2 = get_bindings()
        assert b1 is b2

    def test_reset_bindings(self):
        b1 = get_bindings()
        reset_bindings()
        b2 = get_bindings()
        assert b1 is not b2

    def test_get_bindings_loads_config(self, tmp_path):
        config = tmp_path / "config.yaml"
        config.write_text("""
paths:
  knowledge_dir: singleton_test_kb
""")
        # Change to tmp_path so config.yaml is found
        old_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            b = get_bindings()
            assert b.knowledge_dir == "singleton_test_kb"
        finally:
            os.chdir(old_cwd)


class TestConvenienceHelpers:
    def test_kb_path_explicit_wins(self):
        result = kb_path(explicit="/explicit/path")
        assert result == "/explicit/path"

    def test_kb_path_falls_back_to_binding(self):
        result = kb_path()
        # Binding resolves relative to project root (where config.yaml is)
        assert result.endswith("knowledge")

    def test_inbox_path(self):
        assert inbox_path().endswith("inbox")
        assert inbox_path(explicit="/custom") == "/custom"

    def test_templates_path(self):
        assert templates_path().endswith("templates")
        assert templates_path(explicit="/custom") == "/custom"


class TestResolvePath:
    def test_absolute_path_returned_as_is(self):
        b = Bindings()
        assert b.resolve_path("/absolute/path") == "/absolute/path"

    def test_relative_path_resolves_to_project_root(self):
        b = Bindings()
        resolved = b.resolve_path("relative/path")
        assert resolved.endswith("relative/path")
        # Should start with the project root
        assert Path(resolved).is_absolute() or "/" in resolved
