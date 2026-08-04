from __future__ import annotations

import json
from statistics import mean

from .config import load_config
from .database import get_db


def expected_score(player_rating: float, opponent_average: float) -> float:
    return 1 / (1 + 10 ** ((opponent_average - player_rating) / 400))


def stage_multiplier(competition_type: str | None, config: dict) -> float:
    text = (competition_type or "").lower()
    if any(word in text for word in ("playoff", "final", "knockout")):
        return float(config["weights"]["playoffs"])
    return 1.0


def rebuild_ratings(triggered_by: str = "rebuild_full", reason: str = "Manual rebuild") -> int:
    config = load_config()
    start = float(config["elo"]["starting_rating"])
    base_k = float(config["elo"]["k_factor"])
    provisional_matches = int(config["elo"]["provisional_matches"])

    with get_db() as db:
        version = db.execute(
            """
            INSERT INTO rating_versions(triggered_by, reason, config_snapshot_json)
            VALUES (?, ?, ?)
            """,
            (triggered_by, reason, json.dumps(config, sort_keys=True)),
        ).lastrowid
        db.execute("DELETE FROM rating_snapshots WHERE rating_version = ?", (version,))
        db.execute("UPDATE players SET current_rating = ?, match_count = 0", (start,))

        ratings = {row["id"]: start for row in db.execute("SELECT id FROM players")}
        counts = {player_id: 0 for player_id in ratings}
        matches = db.execute(
            """
            SELECT * FROM matches
            WHERE status = 'approved'
            ORDER BY match_datetime ASC, id ASC
            """
        ).fetchall()

        for match in matches:
            rosters = db.execute(
                """
                SELECT mr.side, p.id AS player_id
                FROM match_rosters mr
                JOIN players p ON p.id = mr.player_id
                WHERE mr.match_id = ?
                ORDER BY mr.side, p.canonical_name
                """,
                (match["id"],),
            ).fetchall()
            side_a = [row["player_id"] for row in rosters if row["side"] == "a"]
            side_b = [row["player_id"] for row in rosters if row["side"] == "b"]
            if len(side_a) < 5 or len(side_b) < 5:
                continue

            a_average = mean(ratings[player_id] for player_id in side_a)
            b_average = mean(ratings[player_id] for player_id in side_b)
            source_weight = float(config["weights"].get(match["source_system"], 1.0))
            multiplier = stage_multiplier(match["competition_type"], config)

            pending_updates: list[tuple[int, str, float, float, float, float, float, float]] = []
            for player_id in side_a + side_b:
                side = "a" if player_id in side_a else "b"
                opponent_average = b_average if side == "a" else a_average
                before = ratings[player_id]
                expected = expected_score(before, opponent_average)
                if match["winning_side"] == "draw":
                    actual = 0.5
                else:
                    actual = 1.0 if match["winning_side"] == side else 0.0
                k = base_k * (2 if counts[player_id] < provisional_matches else 1)
                delta = k * source_weight * multiplier * (actual - expected)
                after = before + delta
                pending_updates.append((player_id, side, opponent_average, before, after, expected, actual, delta))

            for player_id, side, opponent_average, before, after, expected, actual, delta in pending_updates:
                ratings[player_id] = after
                counts[player_id] = counts[player_id] + 1
                db.execute(
                    """
                    INSERT INTO rating_snapshots(
                        match_id, player_id, side, avg_opponent_elo, rating_before,
                        rating_after, expected_score, actual_score, rating_delta, rating_version
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (match["id"], player_id, side, opponent_average, before, after, expected, actual, delta, version),
                )

        for player_id, rating in ratings.items():
            db.execute(
                "UPDATE players SET current_rating = ?, match_count = ? WHERE id = ?",
                (rating, counts[player_id], player_id),
            )
        return int(version)
