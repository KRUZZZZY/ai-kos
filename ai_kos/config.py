"""Config loader for AI-KOS. Reads config.yaml from project root or cwd."""

import copy
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

_DEFAULT_CONFIG = {
    "qdrant": {"host": "localhost", "port": 6333, "collection": "ai_kos"},
    "embedding": {"dense_model": "nomic-embed-text", "dense_dim": 768, "sparse_model": "bm25"},
    "chunking": {"child_tokens": 512, "parent_tokens": 2048, "max_sections": 10},
    "reranker": {"enabled": True, "model": "ms-marco-MiniLM-L-6-v2", "candidate_k": 30, "top_n": 8},
    "search": {"default_top_k": 50, "fusion": "rrf"},
    "decay": {"lambda_stable": 0.01, "lambda_moderate": 0.05, "lambda_volatile": 0.15, "critical": 0.3},
    "linking": {"min_keyword_overlap": 2, "merge_threshold": 0.80},
    "article": {"max_paragraphs": 5, "min_keywords": 3, "max_keywords": 8, "summary_max_chars": 300},
    "paths": {
        "inbox_dir": "inbox", "knowledge_dir": "knowledge", "templates_dir": "templates",
        "archive_dir": "archive", "rejected_dir": "rejected", "projects_dir": "projects",
        "db_path": "datasets/ai-kos.db",
    },
}

_config: Optional[Dict[str, Any]] = None

def _find_config() -> Optional[Path]:
    for root in [os.getcwd(), str(Path(__file__).parent.parent)]:
        p = Path(root) / "config.yaml"
        if p.exists():
            return p
    return None

def load() -> Dict[str, Any]:
    global _config
    if _config is not None:
        return _config
    cfg = copy.deepcopy(_DEFAULT_CONFIG)
    path = _find_config()
    if path:
        with open(path) as f:
            user = yaml.safe_load(f) or {}
        _deep_merge(cfg, user)
    _config = cfg
    return cfg

def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v

def get(*keys: str, default: Any = None) -> Any:
    cfg = load()
    node = cfg
    for k in keys:
        if isinstance(node, dict):
            node = node.get(k)
            if node is None:
                return default
        else:
            return default
    return node
