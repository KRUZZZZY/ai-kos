"""AI-KOS DeclarativeBindings — Pydantic Settings for MCP tool configuration.

Adopts Cloudflare's "bindings" pattern:
- Tools are wired to knowledge base paths via config, not per-call params
- Loaded from config.yaml or environment variables (AI_KOS_* prefix)
- Explicit per-call parameters override bindings
- Backward compatible: bindings are optional, existing behavior unchanged

Usage:
    from ai_kos.bindings import get_bindings
    bindings = get_bindings()
    path = bindings.knowledge_dir  # "knowledge" (from config or env)
"""

import logging
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("ai-kos.bindings")


class Bindings(BaseSettings):
    """Declarative bindings for AI-KOS tool configuration.

    Resolution order: env var > config.yaml > hardcoded default.
    Pydantic Settings handles env var overrides natively — no manual detection needed.

    Environment variables use AI_KOS_ prefix:
        AI_KOS_KNOWLEDGE_DIR=/custom/knowledge
        AI_KOS_INBOX_DIR=/custom/inbox
    """

    model_config = SettingsConfigDict(
        env_prefix="AI_KOS_",
        env_nested_delimiter="__",
    )

    # ── Path Bindings ─────────────────────────────────────────────────
    knowledge_dir: str = Field(default="knowledge", description="Root directory for knowledge articles")
    inbox_dir: str = Field(default="inbox", description="Directory for files awaiting ingestion")
    templates_dir: str = Field(default="templates", description="Directory for article templates")
    archive_dir: str = Field(default="archive", description="Directory for archived source files")
    rejected_dir: str = Field(default="rejected", description="Directory for rejected files")
    projects_dir: str = Field(default="projects", description="Directory for project files")

    # ── Pipeline Bindings ─────────────────────────────────────────────
    pipelines_dir: str = Field(default="pipelines", description="Pipeline state directory (under knowledge_dir)")

    # ── Search Bindings ───────────────────────────────────────────────
    min_keyword_overlap: int = Field(default=2, ge=1, le=10, description="Minimum shared keywords to auto-link")
    merge_threshold: float = Field(default=0.80, ge=0.0, le=1.0, description="Keyword overlap ratio for merge candidates")
    semantic_enabled: bool = Field(default=True, description="Enable semantic vector search when deps available")
    semantic_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum cosine similarity for semantic results")

    # ── TaskQueue Bindings ────────────────────────────────────────────
    taskqueue_max_workers: int = Field(default=3, ge=1, le=16, description="Max worker threads for task queue")
    taskqueue_max_retries: int = Field(default=3, ge=1, le=10, description="Max retry attempts per task")
    taskqueue_retry_delay: float = Field(default=2.0, ge=0.1, le=300.0, description="Base retry delay in seconds")

    def resolve_path(self, path: str) -> str:
        """Resolve a relative path against the project root. Absolute paths returned as-is."""
        p = Path(path)
        if p.is_absolute():
            return path
        project_root = self._find_project_root()
        return str(project_root / path)

    def _find_project_root(self) -> Path:
        """Walk up from cwd to find the project root (config.yaml or pyproject.toml)."""
        cwd = Path.cwd()
        for candidate in [cwd, *cwd.parents]:
            if (candidate / "config.yaml").exists() or (candidate / "pyproject.toml").exists():
                return candidate
        return cwd

    @classmethod
    def from_config_yaml(cls, config_path: Optional[str] = None) -> "Bindings":
        """Load bindings from config.yaml, with env var overrides handled by Pydantic Settings.

        Resolution: env vars (AI_KOS_*) > config.yaml values > hardcoded defaults.
        Pydantic Settings handles env var priority natively — no manual detection.
        """
        import yaml

        # Find and parse config.yaml
        yaml_values = {}
        if config_path:
            path = Path(config_path)
        else:
            path = None
            for candidate in [Path.cwd(), *Path.cwd().parents]:
                p = candidate / "config.yaml"
                if p.exists():
                    path = p
                    break

        if path and path.exists():
            with open(path) as f:
                config = yaml.safe_load(f) or {}

            # Map config.yaml sections to binding fields
            paths = config.get("paths", {})
            path_map = {
                "knowledge_dir": "knowledge_dir", "inbox_dir": "inbox_dir",
                "templates_dir": "templates_dir", "archive_dir": "archive_dir",
                "rejected_dir": "rejected_dir", "projects_dir": "projects_dir",
            }
            for yaml_key, binding_key in path_map.items():
                if yaml_key in paths:
                    yaml_values[binding_key] = paths[yaml_key]

            linking = config.get("linking", {})
            if "min_keyword_overlap" in linking:
                yaml_values["min_keyword_overlap"] = linking["min_keyword_overlap"]
            if "merge_threshold" in linking:
                yaml_values["merge_threshold"] = linking["merge_threshold"]

        # Construct with YAML values — Pydantic Settings automatically overlays env vars
        return cls(**yaml_values)


# ── Singleton ────────────────────────────────────────────────────────────────

_bindings: Optional[Bindings] = None


def get_bindings(config_path: Optional[str] = None) -> Bindings:
    """Get the global bindings singleton. Loads config.yaml on first call."""
    global _bindings
    if _bindings is None:
        _bindings = Bindings.from_config_yaml(config_path)
        logger.debug(f"Bindings loaded: knowledge_dir={_bindings.knowledge_dir}")
    return _bindings


def reset_bindings():
    """Reset the bindings singleton (useful for testing)."""
    global _bindings
    _bindings = None


# ── Convenience Helpers ──────────────────────────────────────────────────────

def kb_path(explicit: Optional[str] = None) -> str:
    """Get the effective knowledge base path: explicit override > binding > default."""
    return explicit or get_bindings().knowledge_dir


def inbox_path(explicit: Optional[str] = None) -> str:
    return explicit or get_bindings().inbox_dir


def templates_path(explicit: Optional[str] = None) -> str:
    return explicit or get_bindings().templates_dir
