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
    "linking": {
        # Legacy keys (unchanged semantics in idf/count modes)
        "mode": "similarity",            # NEW: "similarity" | "idf" | "count" (legacy preserved byte-for-byte)
        "min_keyword_overlap": 2,
        "merge_threshold": 0.80,
        "bridge_threshold": 0.20,
        "idf_link_threshold": 5.5,
        # ── NEW: similarity mode (§1.8) ──
        "similarity_threshold": 0.10,   # recalibrated on live corpus (2026-08-18): 838 undirected edges, orphans 18, max deg 15 — §3.6 window
        "tier_weights": {"subject": 0.6, "article": 1.4},
        "min_evidence": {"shared_article_keywords": 1, "shared_subject_keywords": 3},
        "subject_df_floor": 0,           # 0 = auto (ceil(sqrt(N))); positive int = explicit df floor
        # Curated subject terms, additive with the df rule (plan §1.8 seed list):
        # tda, ai-kos, persistent-homology, vectorization, benchmark, pipeline,
        # persistence-diagram, deep-learning, mcp, hermes, atq, sqlite
        "subject_seed_lexicon": [
            "tda", "ai-kos", "persistent-homology", "vectorization", "benchmark",
            "pipeline", "persistence-diagram", "deep-learning", "mcp", "hermes",
            "atq", "sqlite",
        ],
        "orphan_rescue": True,
        "orphan_rescue_floor": 0.10,
        "link_budget": {
            "min_cap": 3,
            "max_cap": 20,
            "type_base": {
                "mission": 12, "base": 10, "help": 8, "process": 8,
                "plan": 6, "procedure": 6, "research-note": 5, "note": 4,
            },
            "length_factor": {"floor": 0.5, "ceiling": 1.25, "words_per_unit": 600},
            "importance": {"explicit_field": "importance", "derived": True},
        },
        "merge": {
            "article_tier_jaccard_threshold": 0.70,
            "legacy_overlap_threshold": 0.80,
        },
    },
    "article": {
        "max_paragraphs": 5,
        "min_keywords": 3,               # unchanged value, now article-tier floor
        "target_keywords": 10,           # NEW
        "max_keywords": 15,              # CHANGED 8 → 15 (legalizes existing 9-15-keyword articles)
        "min_subject_keywords": 2,       # NEW
        "target_subject_keywords": 5,    # NEW
        "max_subject_keywords": 8,       # NEW
        "summary_max_chars": 300,
    },
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
    # Isolation knob (audit finding #8): AI_KOS_KNOWLEDGE_DIR overrides the
    # knowledge dir so tests/embedders never touch the production knowledge/
    # tree. Env wins over config.yaml — it is the most explicit, per-invocation
    # setting. Consumers (TaskManager, TaskQueue, audit, semantic, …) resolve
    # their DB/log paths through get("paths", "knowledge_dir").
    kd = os.environ.get("AI_KOS_KNOWLEDGE_DIR")
    if kd:
        cfg["paths"]["knowledge_dir"] = kd
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
