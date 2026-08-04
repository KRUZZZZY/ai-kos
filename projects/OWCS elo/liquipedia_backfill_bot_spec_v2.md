# Liquipedia Historical Backfill Bot

## Technical Specification — v2 (HTML Scraping)

---

# 1. Overview

## Purpose

Build a one-time backfill bot that scrapes historical Overwatch match data from Liquipedia's public HTML pages and writes it into the existing OWCS spreadsheet for approval through the standard import pipeline.

The bot is a data harvesting tool only. It does not interact with the Elo system directly. All ingested rows pass through the normal Match Entry → importer → approval → Elo rebuild flow defined in the main system spec.

No API key or account is required. The bot fetches and parses the same public HTML pages a browser would load.

---

## Scope

| Competition                 | From            | Notes                               |
| --------------------------- | --------------- | ----------------------------------- |
| All S/A-Tier tournaments    | January 2022    | Includes 2022 and 2023 seasons only |
| All B to D tier tournaments | August 11, 2023 | Any Overwatch event on Liquipedia   |

Matches before these cutoffs are ignored entirely and not written to the spreadsheet.

---

## Output

The bot appends rows to the `Match Entry` sheet of `owcs_matches.xlsx`. No direct database writes are made. All rows enter the system through the existing approval flow.

---

# 2. Data Source

## Liquipedia Public Pages

All data is fetched from `https://liquipedia.net/overwatch/`.

Liquipedia is a publicly accessible wiki. The bot must behave as a considerate scraper: low request rate, honest User-Agent header, and full respect for any `Retry-After` headers returned by the server.

### Relevant Page Types

| Page type             | URL pattern                                              | Used for                               |
| --------------------- | -------------------------------------------------------- | -------------------------------------- |
| Tournament portal     | `/overwatch/Portal:Tournaments`                          | Discover all competitions              |
| Tournament main page  | `/overwatch/<Tournament_Name>`                           | Find match result tables and stage structure |
| Tournament bracket    | `/overwatch/<Tournament_Name>/Bracket`                   | Playoff match results                  |
| Team page             | `/overwatch/<Team_Name>`                                 | Historical roster for fallback         |
| Player page           | `/overwatch/<Player_Name>`                               | Canonical name and alias confirmation  |

---

# 3. System Architecture

## Stack

| Component       | Technology                  |
| --------------- | --------------------------- |
| Language        | Python 3.12                 |
| HTTP client     | requests                    |
| HTML parser     | BeautifulSoup4 + lxml       |
| Spreadsheet I/O | openpyxl                    |
| Config          | config.yaml + env           |
| Logging         | Standard logging, file output |

The bot runs as a standalone script, separate from the main Elo application. It shares `config.yaml` for paths and writes to the same `owcs_matches.xlsx`.

---

## Run Modes

### `--mode backfill`

Full historical run. Crawls all in-scope tournaments, parses all match pages, writes output. Intended to be run once.

### `--mode incremental`

Crawls only tournaments and pages updated since the last successful run, tracked by `last_run_timestamp` in the bot's state file. Useful for ongoing non-FACEIT tournaments.

### `--mode dry-run`

Runs the full pipeline but writes nothing to the spreadsheet. Logs what would have been written. Use this first to validate coverage before committing.

---

# 4. Crawl and Parse Pipeline

```
Load tournament portal page
        ↓
Extract tournament links → filter by scope (type + date)
        ↓
For each tournament → fetch main page + bracket page
        ↓
Parse match result tables → extract match rows
        ↓
For each match → attempt per-match roster extraction from page HTML
        ↓
  [Roster found?]
  Yes → use exact roster         No → fetch team page, find active roster at match date
        ↓                                       ↓
  roster_confidence: exact          roster_confidence: inferred → flag for review
        ↓
Resolve player names → Player Alias Map
        ↓
Deduplicate against existing spreadsheet rows
        ↓
Write to Match Entry sheet
        ↓
Log run summary
```

---

## 4.1 Tournament Discovery

The bot fetches `/overwatch/Portal:Tournaments` and parses the HTML for tournament links. Liquipedia's portal page lists tournaments in grouped tables by year and tier.

For each discovered link the bot checks:

* Does the URL path correspond to OWL, Contenders, or another event?
* Does the tournament date fall within the scope cutoff for its competition type?

Out-of-scope links are skipped and logged. In-scope links are added to the crawl queue.

The bot stores processed tournament URLs in its state file to avoid reprocessing on incremental runs.

---

## 4.2 Match Page Parsing

For each in-scope tournament, the bot fetches the main tournament page and, where present, the `/Bracket` subpage.

Liquipedia match result tables follow broadly consistent HTML patterns across tournaments:

* Group stage results appear as `wikitable` elements with rows per match
* Bracket results appear in bracket-specific markup

The parser targets:

* Match date — typically in a `<span>` with a `data-timestamp` attribute or similar date cell
* Team names — extracted from team logo `<span>` titles or team name cells
* Scores — map win counts per side
* Best of — inferred from the score cells or explicitly stated in the match header
* Stage label — extracted from the section heading above the match table

Where `data-timestamp` attributes are present they are preferred over visible date text as they give unambiguous UTC timestamps.

---

## 4.3 Roster Resolution

### Step 1 — Per-match explicit roster from page HTML

Some Liquipedia tournament pages list the players who participated in each match, either in a match sub-table or a dedicated `/Rosters` subpage. The parser checks for these structures first.

If found: `roster_confidence = exact`

---

### Step 2 — Active roster fallback via team page

If no per-match roster is present, the bot fetches `/overwatch/<Team_Name>` for both teams. Team pages include a roster history section listing player additions and departures with dates.

The bot finds the roster active at the match date: the set of players whose join date is before or on the match date and whose leave date is after the match date (or absent, indicating they were still on the roster).

If found: `roster_confidence = inferred`

These rows are written with `status = draft` and:

```
roster_inferred: active roster as of <date> used; please verify
```

---

### Step 3 — Partial roster

If the team page roster history yields fewer than 5 players for a given date (e.g. incomplete Liquipedia data), the bot fills the available slots and leaves the rest blank.

`roster_confidence = partial`

```
roster_partial: only N/5 players resolved for side A; manual fill required
```

---

### Step 4 — No roster available

If no roster data can be found at all, all player fields are left blank and the row is written with `status = draft`:

```
roster_missing: no roster data found; manual entry required
```

---

## 4.4 Player Name Resolution

After roster resolution, each player name is checked against the `Player Alias Map` sheet.

* Matched names (exact or alias) are replaced with the canonical name.
* Unmatched names are written as-is into the player slot and flagged:

```
unresolved_player: 'RawName' not in alias map
```

The row is set to `status = draft`. Unrecognised names are resolved via the Player Alias Manager before the row can be approved.

---

## 4.5 Deduplication

Before writing a row, the bot checks the existing `Match Entry` sheet for a potential duplicate using:

* Same event name
* Same match date (within a 1-hour window)
* Overlapping player sets (≥ 8 of 10 players match)

Likely duplicates are skipped and logged:

```
duplicate_suspected: matches row <N>
```

---

## 4.6 Elo Weight Assignment

Liquipedia-sourced rows are written to the OWCS spreadsheet and inherit the OWCS source weight (1.20) when processed by the importer. No separate weight is needed.

---

# 5. Rate Limiting and Scraping Etiquette

The bot must behave respectfully toward Liquipedia's servers. It is a volunteer-maintained wiki.

### Request Rate

A minimum delay of **3 seconds** between all HTTP requests is enforced unconditionally. This is not configurable below 2 seconds.

### User-Agent

All requests identify the bot honestly:

```
User-Agent: ow-elo-backfill-bot/1.0 (private research tool; not for redistribution)
```

### Retry Behaviour

| Response      | Behaviour                                                    |
| ------------- | ------------------------------------------------------------ |
| 429           | Read `Retry-After` header; wait that duration + 10s; retry  |
| 503           | Wait 30s; retry up to 3 times                                |
| 5xx (other)   | Wait 15s; retry up to 3 times; then log and skip page        |
| Connection error | Wait 10s; retry up to 3 times; then log and skip page     |

### Caching

All successfully fetched HTML pages are cached locally to `./cache/liquipedia/<url_hash>.html`. On subsequent runs (including dry-run and incremental), cached pages are served from disk rather than re-fetched. Cache entries expire after 7 days.

This dramatically reduces load on Liquipedia's servers across multiple development and validation runs and speeds up the dry-run → backfill iteration cycle.

---

# 6. HTML Parsing Robustness

Liquipedia's HTML is wiki-generated and inconsistent across tournaments and years. The parser must be defensively written.

### General principles

* Never assume a specific tag structure will be present. Use `.find()` with fallbacks rather than chained index access.
* Always strip and normalise whitespace from extracted text.
* If a required field (date, score, team name) cannot be extracted from a match row, skip the match and log it with the raw HTML fragment for manual inspection.
* Log a warning whenever an unexpected page structure is encountered, even if parsing succeeds, so layout changes can be tracked over time.

### Known layout variations

| Variation                          | Handling                                               |
| ---------------------------------- | ------------------------------------------------------ |
| `data-timestamp` present           | Use as authoritative date                              |
| `data-timestamp` absent            | Parse visible date text; fall back to tournament month |
| Score in separate map-result cells | Sum map wins per side                                  |
| Score as single "X-Y" string       | Split on hyphen                                        |
| Team name in `title` attribute     | Preferred over inner text                              |
| Team name as image alt text only   | Use alt text with a warning log                        |
| Bracket page absent                | Skip bracket fetch; log tournament as group-stage only |

---

# 7. Spreadsheet Output

The bot appends rows to the `Match Entry` sheet of `owcs_matches.xlsx`. Existing rows are never modified or deleted.

## Additional Column

| Column            | Description                                  |
| ----------------- | -------------------------------------------- |
| roster_confidence | `exact` / `inferred` / `partial` / `missing` |

This column is written by the bot and helps the admin prioritise which rows need manual attention. It has no effect on the importer.

---

## Row Status on Write

| Condition                                    | status written |
| -------------------------------------------- | -------------- |
| Full exact roster, all names resolved        | `ready`        |
| Inferred or partial roster                   | `draft`        |
| Any unresolved player name                   | `draft`        |
| Missing roster                               | `draft`        |

---

# 8. State File

The bot maintains `./data/liquipedia_bot_state.json`:

```json
{
  "last_run_timestamp": "2025-01-01T00:00:00Z",
  "processed_tournament_urls": [
    "/overwatch/Overwatch_League/2022",
    "/overwatch/Overwatch_Contenders/2022/North_America"
  ],
  "total_matches_written": 1842,
  "total_matches_skipped": 37
}
```

Updated at the end of every successful run.

---

# 9. Configuration

```yaml
liquipedia:
  base_url: "https://liquipedia.net"
  rate_limit_seconds: 3.0
  max_retries: 3
  cache_dir: "./cache/liquipedia"
  cache_ttl_days: 7
  state_file: "./data/liquipedia_bot_state.json"

backfill:
  owl_from: "2022-01-01"
  contenders_from: "2022-01-01"
  open_tournaments_from: "2023-08-11"
```

No API key or credentials are required.

---

# 10. Logging

Logs to `./logs/liquipedia_bot.log`.

Run summary:

```
[BACKFILL COMPLETE]
Tournaments processed  : 84
Matches found          : 1912
  → exact roster       : 1103
  → inferred roster    : 621
  → partial roster     : 144
  → missing roster     : 44
Rows written (ready)   : 1103
Rows written (draft)   : 809
Rows skipped (dup)     : 37
Rows skipped (scope)   : 0
Pages served from cache: 312
Unresolved players     : 218
Parse warnings         : 41
Errors                 : 3
Duration               : 58m 02s
```

---

# 11. Error Handling

| Error type                   | Behaviour                                                        |
| ---------------------------- | ---------------------------------------------------------------- |
| 429 / rate limited           | Honour `Retry-After`; wait + retry                               |
| 5xx server error             | Retry up to 3 times; log and skip page                           |
| Page not found (404)         | Log and skip; do not retry                                       |
| Parse failure on match row   | Log raw HTML fragment; skip match; continue                      |
| Parse failure on entire page | Log URL and error; skip tournament page; continue                |
| Spreadsheet write failure    | Halt run; log error; preserve partial output                     |
| State file write failure     | Log warning; next incremental run may reprocess some tournaments |

The bot is re-runnable. Cached pages prevent redundant fetches and duplicate detection prevents double-writing.

---

# 12. Known Limitations

**HTML fragility**: Unlike a structured API, HTML scraping breaks when Liquipedia changes its page layout. The parser should be maintained if Liquipedia updates its tournament or team page templates. The parse warning log helps surface these changes early.

**Roster accuracy for older matches**: Liquipedia roster history data quality degrades for older events, particularly OWL 2022. Inferred rosters should be treated as approximate until manually verified.

**Sub and stand-in appearances**: The active roster fallback cannot detect when a substitute player appeared in a specific match. These will be silently incorrect. The `roster_confidence: inferred` flag exists to surface these for review.

**Tournament coverage**: Smaller open tournaments from August 2023 onwards may be absent or have incomplete data on Liquipedia. Missing events should be entered manually via the normal OWCS workflow.

**Player name variations**: Liquipedia handles often differ from FACEIT handles. A bulk alias mapping session will likely be needed after the first backfill run.

**Run duration**: With a 3-second delay between requests and no cached pages, a full backfill may take 1–3 hours. The cache makes subsequent dry-run and partial re-runs much faster.

---

# 13. Recommended Run Order

1. Run `--mode dry-run` to validate tournament discovery and estimate row counts without writing anything
2. Inspect the dry-run log for parse warnings and unexpected page structures; fix the parser if needed
3. Run `--mode backfill` during off-hours to avoid peak load on Liquipedia
4. Review the log summary and triage `draft` rows by `roster_confidence`
5. Resolve unrecognised player aliases in bulk via the Player Alias Manager
6. Approve `ready` rows in batches by competition, oldest first
7. Trigger a single full Elo rebuild once all desired rows are approved
8. Schedule `--mode incremental` as needed for ongoing non-FACEIT tournaments
