from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.src.liquipedia_bot import (
    LiquipediaBot,
    Tournament,
    clean,
    extract_infobox_value,
    extract_page_title,
    extract_participant_rosters,
    extract_tournament_date_hint,
    is_tournament_path,
    liquipedia_path,
    make_soup,
    tournaments_from_index,
)


def cache_name(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html"


def candidate_match_rows(soup):
    nodes = list(soup.select(".brkts-match"))
    for table in soup.select("table.wikitable, table.matchlist, div.bracket"):
        if table.name == "table":
            nodes.extend(table.select("tr"))
        else:
            nodes.extend(table.select(".bracket-game, .bracket-popup-body"))
    seen = set()
    unique = []
    for node in nodes:
        marker = id(node)
        if marker not in seen:
            seen.add(marker)
            unique.append(node)
    return unique


def row_mentions_roster_gap(text: str) -> bool:
    return bool(re.search(r"\b(TBD|N/?A|no roster|without roster|disbanded|forfeit|walkover|withdraw)\b", text, re.IGNORECASE))


def row_mentions_dnp(text: str) -> bool:
    return bool(re.search(r"\b(DNP|did not play|didn['’]?t play|did not participate)\b", text, re.IGNORECASE))


def summarize_page(bot: LiquipediaBot, page: str) -> dict:
    path = liquipedia_path(page, bot.base_url)
    url = urljoin(bot.base_url, path)
    html = bot.fetch(path)
    if not html:
        return {"page": page, "path": path, "url": url, "fetched": False}

    soup = make_soup(html)
    title = extract_page_title(soup) or path.rsplit("/", 1)[-1].replace("_", " ")
    start_date = extract_infobox_value(soup, "Start Date")
    rosters = extract_participant_rosters(soup)
    tournaments = tournaments_from_index(soup)
    tournament = Tournament(title=title, path=path, date_hint=start_date)
    matches = bot.parse_tournament_html(html, tournament, path)
    row_texts = [clean(node.get_text(" ", strip=True)) for node in candidate_match_rows(soup)]
    dnp_rows = [text for text in row_texts if row_mentions_dnp(text)]
    roster_gap_rows = [text for text in row_texts if row_mentions_roster_gap(text)]
    missing_roster_matches = [
        match
        for match in matches
        if len(match.players_a) < 5 or len(match.players_b) < 5 or match.roster_confidence in {"missing", "partial"}
    ]

    return {
        "page": page,
        "path": path,
        "url": url,
        "cache_file": str(bot.cache_path(url)),
        "cache_name": cache_name(url),
        "fetched": True,
        "title": title,
        "start_date": start_date,
        "html_bytes": len(html.encode("utf-8", errors="replace")),
        "tournament_links": len(tournaments),
        "tournament_link_samples": [
            {"title": item.title, "path": item.path, "tier": item.tier, "date_hint": item.date_hint}
            for item in tournaments[:12]
        ],
        "all_anchor_tournament_path_count": sum(1 for anchor in soup.find_all("a", href=True) if is_tournament_path(clean(anchor.get("href", "")))),
        "roster_entries": len(rosters),
        "matches": len(matches),
        "confidence": dict(Counter(match.roster_confidence for match in matches)),
        "missing_or_partial_roster_matches": [
            {
                "date": match.match_date,
                "stage": match.stage,
                "teams": f"{match.team_a} vs {match.team_b}",
                "score": f"{match.score_a}-{match.score_b}",
                "roster_confidence": match.roster_confidence,
                "side_a_players": len(match.players_a),
                "side_b_players": len(match.players_b),
            }
            for match in missing_roster_matches[:20]
        ],
        "match_samples": [
            {
                "date": match.match_date,
                "stage": match.stage,
                "teams": f"{match.team_a} vs {match.team_b}",
                "score": f"{match.score_a}-{match.score_b}",
                "best_of": match.best_of,
                "roster_confidence": match.roster_confidence,
                "side_a_players": len(match.players_a),
                "side_b_players": len(match.players_b),
            }
            for match in matches[:10]
        ],
        "candidate_match_rows": len(row_texts),
        "dnp_row_count": len(dnp_rows),
        "dnp_samples": dnp_rows[:8],
        "roster_gap_row_count": len(roster_gap_rows),
        "roster_gap_samples": roster_gap_rows[:8],
    }


def summarize_html_file(bot: LiquipediaBot, html_file: Path) -> dict:
    html = html_file.read_text(encoding="utf-8", errors="replace")
    soup = make_soup(html)
    title = extract_page_title(soup) or html_file.stem
    tournament = Tournament(title=title, path=str(html_file))
    date_hint, date_hint_source = extract_tournament_date_hint(soup, tournament, str(html_file))
    rosters = extract_participant_rosters(soup)
    bracket_nodes = soup.select(".brkts-match")
    timestamped_bracket_nodes = sum(1 for node in bracket_nodes if node.select_one("[data-timestamp]"))
    matches = bot.parse_tournament_html(html, Tournament(title=title, path=str(html_file), date_hint=date_hint), str(html_file))
    return {
        "file": str(html_file),
        "title": title,
        "html_bytes": len(html.encode("utf-8", errors="replace")),
        "date_hint": date_hint,
        "date_hint_source": date_hint_source,
        "start_date": extract_infobox_value(soup, "Start Date"),
        "date": extract_infobox_value(soup, "Date"),
        "dates": extract_infobox_value(soup, "Dates"),
        "roster_entries": len(rosters),
        "bracket_nodes": len(bracket_nodes),
        "timestamped_bracket_nodes": timestamped_bracket_nodes,
        "candidate_match_rows": len(candidate_match_rows(soup)),
        "matches": len(matches),
        "confidence": dict(Counter(match.roster_confidence for match in matches)),
        "match_samples": [
            {
                "date": match.match_date,
                "stage": match.stage,
                "teams": f"{match.team_a} vs {match.team_b}",
                "score": f"{match.score_a}-{match.score_b}",
                "roster_confidence": match.roster_confidence,
                "side_a_players": len(match.players_a),
                "side_b_players": len(match.players_b),
            }
            for match in matches[:8]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Liquipedia parser behavior without writing workbook rows.")
    parser.add_argument("pages", nargs="*")
    parser.add_argument("--cache-dir", default="", help="Summarize cached Liquipedia HTML files instead of fetching pages.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum cached HTML files to inspect.")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    bot = LiquipediaBot("dry-run", pages=[])
    results = []
    if args.cache_dir:
        cache_dir = Path(args.cache_dir)
        cache_files = sorted(cache_dir.glob("*.html"))
        if args.limit > 0:
            cache_files = cache_files[: args.limit]
        results.extend(summarize_html_file(bot, path) for path in cache_files)
    results.extend(summarize_page(bot, page) for page in args.pages)
    text = json.dumps(results, indent=2, ensure_ascii=False)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
