from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.yaml"


DEFAULT_CONFIG: dict[str, Any] = {
    "elo": {"starting_rating": 1000, "k_factor": 24, "provisional_matches": 10},
    "weights": {"faceit": 1.0, "owcs": 1.2, "playoffs": 1.15},
    "sync": {"faceit_interval_minutes": 10, "owcs_import_interval_minutes": 5},
    "faceit": {"api_key": "${FACEIT_API_KEY}", "base_url": "https://open.faceit.com/data/v4"},
    "paths": {
        "database": "./app/data/database.sqlite3",
        "workbook": "./app/data/owcs_matches.xlsx",
        "logs": "./app/logs/",
    },
    "liquipedia": {
        "base_url": "https://liquipedia.net",
        "rate_limit_seconds": 3.0,
        "jitter_min_seconds": -1.0,
        "jitter_max_seconds": 15.0,
        "jitter_mode_seconds": 10.0,
        "max_retries": 3,
        "cache_dir": "./cache/liquipedia",
        "cache_ttl_days": 7,
        "state_file": "./app/data/liquipedia_bot_state.json",
    },
    "backfill": {
        "owl_from": "2022-01-01",
        "contenders_from": "2022-01-01",
        "open_tournaments_from": "2023-08-11",
    },
}


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    return value


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
    else:
        loaded = {}

    config = DEFAULT_CONFIG.copy()
    for section, values in loaded.items():
        if isinstance(values, dict) and isinstance(config.get(section), dict):
            config[section] = {**config[section], **values}
        else:
            config[section] = values
    return _expand(config)


def project_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path
