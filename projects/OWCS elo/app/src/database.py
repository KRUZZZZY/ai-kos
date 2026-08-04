from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import load_config, project_path


def database_path() -> Path:
    config = load_config()
    path = project_path(config["paths"]["database"])
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_name TEXT NOT NULL UNIQUE,
                faceit_id TEXT UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                current_rating REAL NOT NULL DEFAULT 1000,
                match_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS player_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                source_system TEXT NOT NULL,
                alias_text TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_system, alias_text COLLATE NOCASE)
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_system TEXT NOT NULL CHECK(source_system IN ('faceit', 'owcs')),
                source_match_id TEXT,
                match_datetime TEXT NOT NULL,
                competition_name TEXT NOT NULL,
                competition_type TEXT,
                best_of INTEGER NOT NULL,
                side_a_score INTEGER NOT NULL,
                side_b_score INTEGER NOT NULL,
                winning_side TEXT NOT NULL CHECK(winning_side IN ('a', 'b', 'draw')),
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                raw_payload_json TEXT,
                row_hash TEXT,
                import_error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_system, source_match_id)
            );

            CREATE TABLE IF NOT EXISTS match_rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
                side TEXT NOT NULL CHECK(side IN ('a', 'b')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(match_id, player_id)
            );

            CREATE TABLE IF NOT EXISTS rating_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                triggered_by TEXT NOT NULL,
                reason TEXT,
                config_snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS rating_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                side TEXT NOT NULL CHECK(side IN ('a', 'b')),
                avg_opponent_elo REAL NOT NULL,
                rating_before REAL NOT NULL,
                rating_after REAL NOT NULL,
                expected_score REAL NOT NULL,
                actual_score REAL NOT NULL,
                rating_delta REAL NOT NULL,
                rating_version INTEGER NOT NULL REFERENCES rating_versions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_system TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                status TEXT NOT NULL,
                items_seen INTEGER NOT NULL DEFAULT 0,
                items_inserted INTEGER NOT NULL DEFAULT 0,
                items_updated INTEGER NOT NULL DEFAULT 0,
                errors_json TEXT
            );

            CREATE TABLE IF NOT EXISTS manual_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                reason TEXT,
                approved_by TEXT,
                approved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS import_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_system TEXT NOT NULL,
                reference TEXT,
                message TEXT NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
