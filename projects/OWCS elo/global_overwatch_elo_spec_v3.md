# Global Overwatch Elo System

## Technical Specification (Local-First Version) — v3

---

# 1. Overview

## Purpose

Build a local-first application that maintains a unified Elo rating system for competitive Overwatch players using:

* Automated FACEIT League match ingestion (including per-match player rosters)
* Manual OWCS match entry with player rosters
* Historical recalculation from a complete match log

The system is intended for administrative use only and does not require a consumer-facing UI.

Players are tracked as fully independent individuals. There are no team entities — a player's Elo follows them regardless of which roster they appear on.

---

# 2. Core Requirements

The application must:

* Automatically sync FACEIT League matches including player rosters
* Allow fast local entry of OWCS matches with per-match player rosters
* Maintain a single global Elo pool per player
* Store all historical match and roster data
* Rebuild ratings from scratch at any time
* Detect duplicates and malformed entries
* Support player aliases across FACEIT and OWCS naming conventions
* Run entirely locally except for FACEIT API access
* Require minimal maintenance

---

# 3. System Architecture

## Architecture Style

Local-first desktop/server application.

## Recommended Stack

| Component          | Technology                         |
| ------------------ | ---------------------------------- |
| Backend            | Python 3.12                        |
| Framework          | FastAPI                            |
| Database           | SQLite                             |
| Task Runner        | APScheduler                        |
| Spreadsheet Import | openpyxl                           |
| Local UI           | Jinja2 HTML templates              |
| Deployment         | Docker or local Python environment |

### Stack rationale

**FastAPI over Django**: lightweight, no admin framework needed, natural for a data pipeline without user-facing views.

**APScheduler over Celery**: runs in-process with no broker dependency, sufficient for 5–15 minute polling intervals.

**SQLite only**: comfortably handles a local match and player log at this scale.

---

# 4. Data Sources

## 4.1 FACEIT

Source: FACEIT Data API

Used for:

* League matches
* Player rosters per match
* Match metadata
* Event metadata

The FACEIT API returns the participating players for each match (and in many cases per-round). The importer should extract player IDs and names at the match level at minimum, using per-round roster data where available.

### Sync Method

* Scheduled polling every 5–15 minutes
* Optional webhook support later

### Import Scope

Only completed matches are imported into the rating system.

---

## 4.2 OWCS

OWCS match data and player rosters are entered manually using a local spreadsheet workbook.

No cloud spreadsheet or internet service is used.

---

# 5. Local OWCS Workflow

## Workbook File

Example:

`owcs_matches.xlsx`

The workbook acts as a staging/input layer only.

The database remains the authoritative source of truth.

---

## 5.1 Workbook Structure

### Sheet: `Match Entry`

Each row represents one match. The ten player columns capture the full 5v5 roster for that match.

| Column       | Description                                        |
| ------------ | -------------------------------------------------- |
| match_date   | Date/time of match                                 |
| event_name   | Tournament or event                                |
| stage        | Group, playoff, finals, etc                        |
| player_a1    | Side A — player 1                                  |
| player_a2    | Side A — player 2                                  |
| player_a3    | Side A — player 3                                  |
| player_a4    | Side A — player 4                                  |
| player_a5    | Side A — player 5                                  |
| player_b1    | Side B — player 1                                  |
| player_b2    | Side B — player 2                                  |
| player_b3    | Side B — player 3                                  |
| player_b4    | Side B — player 4                                  |
| player_b5    | Side B — player 5                                  |
| score_a      | Maps won by side A                                 |
| score_b      | Maps won by side B                                 |
| best_of      | BO3, BO5, etc                                      |
| winning_side | a or b                                             |
| notes        | Optional notes                                     |
| status       | draft / ready / approved / rejected                |
| import_error | Auto-filled by importer; blank if no issues        |
| row_hash     | SHA-256 of key fields; used to detect silent edits |

Player name fields accept any known alias for a player. The importer resolves these against the `Player Alias Map` sheet. Unresolved names are flagged in `import_error` and held until manually mapped.

The `row_hash` is computed on import and compared on subsequent runs. A hash mismatch on a previously-imported row flags the row for review rather than silently re-importing or skipping it.

---

### Sheet: `Player Alias Map`

| Column          | Description              |
| --------------- | ------------------------ |
| canonical_player | Internal canonical name |
| alias_text      | External alias or handle |
| source          | owcs / faceit / manual   |
| approved        | yes/no                   |

---

### Sheet: `Import Log`

| Column        | Description        |
| ------------- | ------------------ |
| import_time   | Timestamp          |
| rows_seen     | Total rows         |
| rows_imported | Successful imports |
| rows_rejected | Failed imports     |
| notes         | Import notes       |

---

# 6. Database Schema

All primary keys use auto-increment integers. FACEIT's own string player and match IDs are stored as string references in the relevant `source_*_id` fields.

---

## 6.1 players

| Field           | Type     |
| --------------- | -------- |
| id              | integer  |
| canonical_name  | string   |
| faceit_id       | string   |
| active          | boolean  |
| created_at      | datetime |

`faceit_id` is nullable for players who have only appeared in manually-entered OWCS matches.

---

## 6.2 player_aliases

| Field         | Type     |
| ------------- | -------- |
| id            | integer  |
| player_id     | FK       |
| source_system | string   |
| alias_text    | string   |
| approved      | boolean  |
| created_at    | datetime |

---

## 6.3 matches

Teams are not stored. Each match is a record of a competed fixture between two anonymous sides (A and B), with the rosters stored separately in `match_rosters`.

| Field            | Type                          |
| ---------------- | ----------------------------- |
| id               | integer                       |
| source_system    | faceit / owcs                 |
| source_match_id  | string                        |
| match_datetime   | datetime                      |
| competition_name | string                        |
| competition_type | string                        |
| best_of          | integer                       |
| side_a_score     | integer                       |
| side_b_score     | integer                       |
| winning_side     | a / b                         |
| status           | pending / approved / rejected |
| raw_payload_json | JSON                          |
| created_at       | datetime                      |
| updated_at       | datetime                      |

---

## 6.4 match_rosters

One row per player per match. Links each player to a match and records which side they played on.

| Field      | Type     |
| ---------- | -------- |
| id         | integer  |
| match_id   | FK       |
| player_id  | FK       |
| side       | a / b    |
| created_at | datetime |

Each valid match must have exactly 5 rows with `side = a` and 5 rows with `side = b`. The importer validates this before committing.

---

## 6.5 rating_snapshots

One row per player per match, capturing the rating change that match produced.

| Field            | Type                    |
| ---------------- | ----------------------- |
| id               | integer                 |
| match_id         | FK                      |
| player_id        | FK                      |
| side             | a / b                   |
| avg_opponent_elo | float                   |
| rating_before    | float                   |
| rating_after     | float                   |
| expected_score   | float                   |
| actual_score     | float                   |
| rating_delta     | float                   |
| rating_version   | FK → rating_versions.id |

`avg_opponent_elo` is stored at snapshot time so rebuilds can be audited and past calculations verified.

---

## 6.6 rating_versions

Each full rebuild or configuration change increments the version and creates a record here.

| Field                | Type     |
| -------------------- | -------- |
| id                   | integer  |
| triggered_by         | string   |
| reason               | text     |
| config_snapshot_json | JSON     |
| created_at           | datetime |

`triggered_by` values: `rebuild_full`, `rebuild_partial`, `config_change`, `alias_change`, `match_edit`.

---

## 6.7 sync_runs

| Field          | Type            |
| -------------- | --------------- |
| id             | integer         |
| source_system  | string          |
| started_at     | datetime        |
| finished_at    | datetime        |
| status         | success/failure |
| items_seen     | integer         |
| items_inserted | integer         |
| items_updated  | integer         |
| errors_json    | JSON            |

---

## 6.8 manual_overrides

| Field       | Type     |
| ----------- | -------- |
| id          | integer  |
| match_id    | FK       |
| field_name  | string   |
| old_value   | string   |
| new_value   | string   |
| reason      | text     |
| approved_by | string   |
| approved_at | datetime |

---

# 7. Match Ingestion Pipeline

## 7.1 FACEIT Import Flow

### Scheduled Sync

1. Query FACEIT API
2. Pull recent completed matches
3. Store raw payloads
4. Normalize match structure
5. Extract player rosters from payload
6. Resolve player aliases (match FACEIT IDs and names to canonical players)
7. Validate roster completeness (exactly 5 per side)
8. Validate scores
9. Queue for approval
10. Commit approved matches and rosters
11. Trigger Elo recalculation

---

## 7.2 OWCS Import Flow

### Local Spreadsheet Import

1. Read workbook from local path
2. Parse rows from `Match Entry`
3. Validate fields and player columns
4. Resolve player aliases for all 10 player name fields
5. Detect duplicates and hash-changed rows
6. Flag invalid rows (written back to `import_error`)
7. Import approved rows and create `match_rosters` entries
8. Trigger Elo recalculation

---

# 8. Elo Rating System

## 8.1 Base Formula

Expected score for a player on side A:

`Ea = 1 / (1 + 10^((avg_Rb - Ra) / 400))`

Where `avg_Rb` is the mean current rating of the 5 players on side B at the time of the match.

Rating update:

`Ra' = Ra + (K × W × M × (Sa - Ea))`

This calculation is performed independently for each of the 10 players in the match. Players on side B use the mean rating of side A as their reference.

---

## 8.2 Variables

| Variable  | Meaning                                          |
| --------- | ------------------------------------------------ |
| K         | Base volatility                                  |
| W         | Source weight                                    |
| M         | Match importance multiplier                      |
| Sa        | Actual result for this player (see §8.4)         |
| avg_Rb    | Mean Elo of the 5 opposing players at match time |

---

## 8.3 Default Configuration

| Setting             | Value |
| ------------------- | ----- |
| Starting Elo        | 1000  |
| Base K              | 24    |
| Provisional Matches | 10    |
| FACEIT Weight       | 1.00  |
| OWCS Weight         | 1.20  |
| Playoff Multiplier  | 1.15  |

---

## 8.4 Actual Score (Sa) Values

Sa represents the match outcome for an individual player:

| Outcome | Sa value |
| ------- | -------- |
| Win     | 1.0      |
| Loss    | 0.0      |
| Draw    | 0.5      |

All players on the winning side receive Sa = 1.0. All players on the losing side receive Sa = 0.0. Draws are not expected in standard Overwatch competition but are handled for completeness.

**Margin of victory**: score_a and score_b are stored for record-keeping but do not currently affect Sa, W, or M. A 3-0 and a 3-2 result carry identical Elo weight per player. If margin-weighted scoring is added in future, it should be gated behind a config flag to preserve rebuild reproducibility.

---

## 8.5 Provisional Matches

A player's first 10 matches (configurable via `provisional_matches`) are treated as provisional:

* The K factor is doubled during provisional matches to allow ratings to converge faster from the starting value
* Provisional players are flagged in the rating table but are not excluded from it
* Once a player exits provisional status, their rating carries forward normally

---

# 9. Rating Rebuild System

## Requirement

The system must support full historical rebuilds.

### Rebuild Triggers

* Match edited or deleted
* Player alias changed
* Weight configuration changed
* Historical import added

---

## Rebuild Process

1. Create a new record in `rating_versions` with the trigger reason and current config snapshot
2. Reset all player ratings to starting value
3. Sort matches chronologically
4. For each approved match, compute `avg_Rb` from each side's ratings at that point in time
5. Apply Elo update to all 10 players
6. Write rating snapshots (linked to the new version id)
7. Store updated results

Player ratings during a rebuild are computed in strict chronological order so that each match uses the ratings that existed immediately before it, not the final rebuilt values.

---

# 10. Player Identity Rules

## Canonical Players

Every player has one canonical identity in the system regardless of how many aliases, handles, or name variations they have used across different events or platforms.

---

## Player Aliases

Aliases map external names (FACEIT handles, OWCS rosters, alternate spellings) to a single canonical player record.

Unknown names encountered during import enter the review queue until manually mapped. Matches referencing unresolved players cannot be committed.

---

## Handle Changes

If a player changes their in-game name, the old name is stored as a historical alias. Their Elo history is unaffected.

---

# 11. Validation Rules

## Match Validation

Reject:

* Fewer or more than 5 players on either side
* Any unresolved player alias
* Impossible scores
* Missing winning side
* Duplicate source IDs
* Same player appearing on both sides
* Incomplete series

---

## Duplicate Detection

Primary detection:

* source system + source match ID

Secondary detection:

* same set of players
* same score
* same timestamp window

**Edited row detection (OWCS only)**:

* row_hash mismatch on a previously-imported row triggers a flag rather than a silent re-import or skip

---

# 12. Admin Interface

## Required Pages

### Match Queue

* Pending imports
* Approve/reject with roster preview

### Player Alias Manager

* Merge aliases
* Create canonical player records
* Resolve unmatched names from import queue

### Rating Table

* Current player ratings
* Rank and rating change
* Provisional flag shown

### Match History

* Chronological match list
* Per-match roster
* Rating deltas per player

### Rebuild Controls

* Partial rebuild
* Full rebuild
* Rebuild history log (from `rating_versions`)

### Error Dashboard

* Failed imports
* Unresolved player aliases
* Malformed rows
* Roster completeness failures

### Health Status

* FACEIT API reachability
* Workbook path validity
* Scheduler alive check
* Last successful sync timestamp

---

# 13. Local File Structure

```text
/app
    /data
        owcs_matches.xlsx
        database.sqlite3

    /imports
        faceit/
        owcs/

    /logs
        importer.log
        rebuild.log

    /backups
        daily/
        monthly/

    /src
```

---

# 14. Scheduled Jobs

## FACEIT Sync

Frequency:

* Every 10 minutes

---

## Workbook Import

Frequency:

* Every 5 minutes, or manual button

---

## Backup Job

Frequency:

* Daily

Backup includes:

* SQLite DB
* OWCS workbook
* Logs

---

# 15. Configuration File

Example `config.yaml`

```yaml
elo:
  starting_rating: 1000
  k_factor: 24
  provisional_matches: 10

weights:
  faceit: 1.0
  owcs: 1.2
  playoffs: 1.15

sync:
  faceit_interval_minutes: 10
  owcs_import_interval_minutes: 5

faceit:
  api_key: "${FACEIT_API_KEY}"
  base_url: "https://open.faceit.com/data/v4"

paths:
  workbook: "./data/owcs_matches.xlsx"
  logs: "./logs/"
```

The FACEIT API key must be set via the `FACEIT_API_KEY` environment variable. It must never be committed to version control.

---

# 16. Logging Requirements

The system must log:

* Imports (match and roster)
* Rebuilds
* Rejected rows
* Alias merges and new mappings
* Manual overrides
* API failures
* Health check results

Logs are written locally to disk.

---

# 17. Backup Strategy

Daily backups include:

* Database
* Workbook
* Configuration
* Logs

Retention:

* 7 daily backups
* 3 monthly backups

Full rebuilds from the match log are possible at any time, so aggressive backup retention is unnecessary.

---

# 18. Recommended MVP Build Order

## Phase 1

* Database schema
* Elo engine (individual player, average opponent method)
* Basic player alias resolver stub
* Manual match entry with player roster columns
* Rating table

---

## Phase 2

* Spreadsheet importer (with row_hash change detection)
* Full alias resolution and player alias management
* Duplicate detection and roster completeness validation

---

## Phase 3

* FACEIT sync with player roster extraction
* Scheduled jobs
* Rebuild system (with rating_versions log)

---

## Phase 4

* Admin dashboard improvements
* Health status page
* Analytics
* Export tools

---

# 19. Recommended Future Features

Optional later additions:

* Role-level Elo (tank / support / DPS)
* Margin-of-victory weighting (config-flagged)
* Season snapshots
* Per-player match history page
* Head-to-head player records
* Web dashboard
* API endpoints
* Monte Carlo predictions
* Strength-of-schedule metrics

---

# 20. Final Recommended Deployment

## Recommended Initial Setup

Single local machine:

* Python backend (FastAPI + APScheduler)
* SQLite database
* Local OWCS workbook
* Docker optional
* FACEIT API sync enabled (API key via environment variable)

This setup is:

* Simple
* Resilient
* Offline-capable for OWCS entry
* Easy to maintain and audit
* Fully rebuildable from match and roster history
