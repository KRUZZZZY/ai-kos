from __future__ import annotations

import json
import os
from datetime import datetime
from urllib.parse import quote

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import load_config, project_path
from .database import get_db, init_db
from .elo import rebuild_ratings
from .services import approve_match, create_match, get_or_create_player, import_owcs_workbook, reject_match, resolve_player

app = FastAPI(title="Global Overwatch Elo")
templates = Jinja2Templates(directory="app/src/templates")
app.mount("/static", StaticFiles(directory="app/src/static"), name="static")
scheduler = BackgroundScheduler()


def query_all(sql: str, params: tuple = ()) -> list:
    with get_db() as db:
        return db.execute(sql, params).fetchall()


def sorted_player_values(form, side: str) -> list[str]:
    prefix = f"player_{side}"
    numbered: list[tuple[int, str]] = []
    for key, value in form.multi_items():
        if not key.startswith(prefix):
            continue
        suffix = key.removeprefix(prefix)
        if not suffix.isdigit():
            continue
        name = str(value).strip()
        if name:
            numbered.append((int(suffix), name))
    return [name for _index, name in sorted(numbered)]


def scheduled_owcs_import() -> None:
    try:
        import_owcs_workbook()
    except Exception as exc:
        with get_db() as db:
            db.execute(
                """
                INSERT INTO sync_runs(source_system, status, items_seen, items_inserted, items_updated, finished_at, errors_json)
                VALUES ('owcs', 'failure', 0, 0, 0, CURRENT_TIMESTAMP, ?)
                """,
                (json.dumps({"error": str(exc)}),),
            )


@app.on_event("startup")
def startup() -> None:
    init_db()
    config = load_config()
    scheduler.add_job(scheduled_owcs_import, "interval", minutes=int(config["sync"]["owcs_import_interval_minutes"]), id="owcs_import", replace_existing=True)
    scheduler.start()


@app.on_event("shutdown")
def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, notice: str | None = None) -> HTMLResponse:
    stats = {
        "players": query_all("SELECT COUNT(*) AS total FROM players")[0]["total"],
        "approved_matches": query_all("SELECT COUNT(*) AS total FROM matches WHERE status = 'approved'")[0]["total"],
        "pending_matches": query_all("SELECT COUNT(*) AS total FROM matches WHERE status = 'pending'")[0]["total"],
        "issues": query_all("SELECT COUNT(*) AS total FROM import_issues WHERE resolved = 0")[0]["total"],
    }
    leaders = query_all(
        """
        SELECT canonical_name, current_rating, match_count
        FROM players
        ORDER BY current_rating DESC, canonical_name
        LIMIT 10
        """
    )
    latest = query_all(
        """
        SELECT id, match_datetime, competition_name, side_a_score, side_b_score, winning_side, status
        FROM matches
        ORDER BY match_datetime DESC, id DESC
        LIMIT 8
        """
    )
    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats, "leaders": leaders, "latest": latest, "notice": notice})


@app.get("/ratings", response_class=HTMLResponse)
def ratings(request: Request) -> HTMLResponse:
    config = load_config()
    provisional_cutoff = int(config["elo"]["provisional_matches"])
    players = query_all(
        """
        SELECT id, canonical_name, current_rating, match_count, faceit_id, active
        FROM players
        ORDER BY current_rating DESC, canonical_name
        """
    )
    return templates.TemplateResponse("ratings.html", {"request": request, "players": players, "provisional_cutoff": provisional_cutoff})


@app.get("/matches", response_class=HTMLResponse)
def matches(request: Request) -> HTMLResponse:
    rows = query_all(
        """
        SELECT m.*, 
               GROUP_CONCAT(CASE WHEN mr.side = 'a' THEN p.canonical_name END, ', ') AS side_a,
               GROUP_CONCAT(CASE WHEN mr.side = 'b' THEN p.canonical_name END, ', ') AS side_b
        FROM matches m
        LEFT JOIN match_rosters mr ON mr.match_id = m.id
        LEFT JOIN players p ON p.id = mr.player_id
        GROUP BY m.id
        ORDER BY m.match_datetime DESC, m.id DESC
        """
    )
    return templates.TemplateResponse("matches.html", {"request": request, "matches": rows})


@app.get("/matches/new", response_class=HTMLResponse)
def new_match(request: Request, error: str | None = None) -> HTMLResponse:
    players = query_all("SELECT id, canonical_name FROM players ORDER BY canonical_name")
    return templates.TemplateResponse("match_form.html", {"request": request, "players": players, "error": error})


@app.post("/matches/new")
async def create_manual_match(request: Request):
    try:
        form = await request.form()
        a_names = sorted_player_values(form, "a")
        b_names = sorted_player_values(form, "b")
        side_a = [resolve_player(name, "owcs") or get_or_create_player(name, "owcs") for name in a_names]
        side_b = [resolve_player(name, "owcs") or get_or_create_player(name, "owcs") for name in b_names]
        payload = {
            "source_system": "owcs",
            "source_match_id": None,
            "match_datetime": datetime.fromisoformat(str(form.get("match_datetime"))).isoformat(),
            "competition_name": str(form.get("competition_name") or ""),
            "competition_type": str(form.get("competition_type") or ""),
            "best_of": int(form.get("best_of") or 0),
            "side_a_score": int(form.get("side_a_score") or 0),
            "side_b_score": int(form.get("side_b_score") or 0),
            "winning_side": str(form.get("winning_side") or ""),
            "status": str(form.get("status") or "approved"),
            "raw_payload_json": json.dumps({"side_a": a_names, "side_b": b_names}),
        }
        create_match(payload, side_a, side_b)
    except Exception as exc:
        return RedirectResponse(f"/matches/new?error={quote(str(exc))}", status_code=303)
    return RedirectResponse("/matches", status_code=303)


@app.post("/matches/{match_id}/approve")
def approve(match_id: int):
    approve_match(match_id)
    return RedirectResponse("/queue", status_code=303)


@app.post("/matches/{match_id}/reject")
def reject(match_id: int):
    reject_match(match_id)
    return RedirectResponse("/queue", status_code=303)


@app.get("/queue", response_class=HTMLResponse)
def queue(request: Request) -> HTMLResponse:
    rows = query_all(
        """
        SELECT m.*, 
               GROUP_CONCAT(CASE WHEN mr.side = 'a' THEN p.canonical_name END, ', ') AS side_a,
               GROUP_CONCAT(CASE WHEN mr.side = 'b' THEN p.canonical_name END, ', ') AS side_b
        FROM matches m
        LEFT JOIN match_rosters mr ON mr.match_id = m.id
        LEFT JOIN players p ON p.id = mr.player_id
        WHERE m.status = 'pending'
        GROUP BY m.id
        ORDER BY m.match_datetime ASC, m.id ASC
        """
    )
    return templates.TemplateResponse("queue.html", {"request": request, "matches": rows})


@app.get("/aliases", response_class=HTMLResponse)
def aliases(request: Request, error: str | None = None) -> HTMLResponse:
    players = query_all("SELECT id, canonical_name FROM players ORDER BY canonical_name")
    aliases = query_all(
        """
        SELECT pa.*, p.canonical_name
        FROM player_aliases pa
        JOIN players p ON p.id = pa.player_id
        ORDER BY p.canonical_name, pa.alias_text
        """
    )
    return templates.TemplateResponse("aliases.html", {"request": request, "players": players, "aliases": aliases, "error": error})


@app.post("/aliases")
def add_alias(canonical_name: str = Form(...), alias_text: str = Form(...), source_system: str = Form("manual")):
    try:
        get_or_create_player(canonical_name, source_system, alias_text)
        rebuild_ratings("alias_change", f"Alias added for {canonical_name}")
    except Exception as exc:
        return RedirectResponse(f"/aliases?error={str(exc)}", status_code=303)
    return RedirectResponse("/aliases", status_code=303)


@app.get("/rebuild", response_class=HTMLResponse)
def rebuild_page(request: Request) -> HTMLResponse:
    versions = query_all("SELECT * FROM rating_versions ORDER BY created_at DESC, id DESC LIMIT 50")
    return templates.TemplateResponse("rebuild.html", {"request": request, "versions": versions})


@app.post("/rebuild/full")
def rebuild_full(reason: str = Form("Manual full rebuild")):
    rebuild_ratings("rebuild_full", reason)
    return RedirectResponse("/rebuild", status_code=303)


@app.post("/imports/owcs")
def import_owcs():
    try:
        result = import_owcs_workbook()
        notice = f"OWCS import complete: {result['rows_imported']} imported, {result['rows_rejected']} rejected."
    except Exception as exc:
        notice = f"OWCS import failed: {exc}"
    return RedirectResponse(f"/?notice={notice}", status_code=303)


@app.get("/errors", response_class=HTMLResponse)
def errors(request: Request) -> HTMLResponse:
    issues = query_all("SELECT * FROM import_issues WHERE resolved = 0 ORDER BY created_at DESC LIMIT 100")
    sync_runs = query_all("SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 50")
    return templates.TemplateResponse("errors.html", {"request": request, "issues": issues, "sync_runs": sync_runs})


@app.get("/liquipedia", response_class=HTMLResponse)
def liquipedia_page(request: Request) -> HTMLResponse:
    config = load_config()
    state_path = project_path(config["liquipedia"]["state_file"])
    cache_path = project_path(config["liquipedia"]["cache_dir"])
    log_path = project_path(config["paths"]["logs"]) / "liquipedia_bot.log"
    state = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {"error": "State file is not valid JSON."}
    return templates.TemplateResponse(
        "liquipedia.html",
        {
            "request": request,
            "state": state,
            "state_path": state_path,
            "cache_path": cache_path,
            "log_path": log_path,
            "cache_exists": cache_path.exists(),
            "log_exists": log_path.exists(),
            "workbook_path": project_path(config["paths"]["workbook"]),
            "rate_limit": config["liquipedia"]["rate_limit_seconds"],
        },
    )


@app.get("/health", response_class=HTMLResponse)
async def health(request: Request) -> HTMLResponse:
    config = load_config()
    workbook_path = project_path(config["paths"]["workbook"])
    database_path = project_path(config["paths"]["database"])
    faceit_status = "not configured"
    api_key = os.getenv("FACEIT_API_KEY")
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=4) as client:
                response = await client.get(
                    f"{config['faceit']['base_url']}/search/championships",
                    headers={"Authorization": f"Bearer {api_key}"},
                    params={"game": "ow2", "limit": 1},
                )
            faceit_status = "reachable" if response.status_code < 500 else f"server error {response.status_code}"
        except Exception as exc:
            faceit_status = f"unreachable: {exc}"
    last_sync = query_all("SELECT * FROM sync_runs ORDER BY finished_at DESC LIMIT 1")
    return templates.TemplateResponse(
        "health.html",
        {
            "request": request,
            "workbook_path": workbook_path,
            "workbook_exists": workbook_path.exists(),
            "database_path": database_path,
            "database_exists": database_path.exists(),
            "scheduler_alive": scheduler.running,
            "faceit_status": faceit_status,
            "last_sync": last_sync[0] if last_sync else None,
        },
    )
