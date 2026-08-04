# Global Overwatch Elo

Local-first FastAPI + SQLite admin app for a unified Overwatch player Elo pool.

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.src.main:app --reload
```

Then open `http://127.0.0.1:8001`.

The app initializes `app/data/database.sqlite3` automatically. OWCS workbook imports expect `app/data/owcs_matches.xlsx` with `Match Entry`, `Player Alias Map`, and optional `Import Log` sheets.

## Liquipedia Backfill Bot

Run a dry-run first:

```powershell
python -m app.src.liquipedia_bot --mode dry-run
```

Parse one tournament page instead of crawling discovery pages:

```powershell
python -m app.src.liquipedia_bot --mode dry-run --page /overwatch/ASBN/2026/Overwatch_Community_League
```

Validate against a saved page such as `Example.html`:

```powershell
python -m app.src.liquipedia_bot --mode dry-run --html-file Example.html
```

Write the terminal-style output to a troubleshooting file:

```powershell
python -m app.src.liquipedia_bot --mode dry-run --terminal-doc app/logs/liquipedia_dry_run.txt
```

Write discovered rows to the OWCS workbook:

```powershell
python -m app.src.liquipedia_bot --mode backfill
```

The bot fetches public Liquipedia HTML with a base delay plus random jitter, caches pages under `cache/liquipedia`, and appends only to the `Match Entry` workbook sheet. Rows still require the normal spreadsheet import and approval flow before affecting Elo.
