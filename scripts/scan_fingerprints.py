#!/usr/bin/env python3
"""
AI Fingerprint Scanner — counts AI-favorite words and phrases in text,
compares against the AI-KOS fingerprint words dataset, and computes
a contamination score.

Prerequisites:
    The dataset must be ingested: ai-fingerprint-words (SQL-backed)

Usage:
    python3 scan_fingerprints.py <file.txt>
    python3 scan_fingerprints.py --stdin <<< "your text"
    python3 scan_fingerprints.py --help

Output:
    A report listing every fingerprint word found, its category and frequency ratio,
    plus an overall contamination score and recommendations.
"""

import re
import sys
import sqlite3
import argparse
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple


def load_fingerprints(db_path: str) -> List[Dict]:
    """Load all fingerprint words from the SQLite dataset."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT word, category, frequency_ratio, notes FROM ai_fingerprint_words"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def normalize_text(text: str) -> str:
    """Lowercase and collapse whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def find_fingerprints(text: str, fingerprints: List[Dict]) -> List[Dict]:
    """Scan text for fingerprint words/phrases, return matches."""
    normalized = normalize_text(text)
    matches = []

    for fp in fingerprints:
        word = fp["word"]
        # Handle multi-word phrases
        pattern = re.escape(word.replace("_", " "))
        count = len(re.findall(pattern, normalized))
        if count > 0:
            matches.append({
                **fp,
                "display": word.replace("_", " "),
                "count": count,
                "ratio": fp["frequency_ratio"],
            })

    # Sort by count * ratio (impact)
    matches.sort(key=lambda m: m["count"] * _parse_ratio(m["ratio"]), reverse=True)
    return matches


def _parse_ratio(ratio_str: str) -> float:
    """Convert '~50x' or '~10x' to float."""
    try:
        return float(ratio_str.replace("~", "").replace("x", ""))
    except (ValueError, AttributeError):
        return 1.0


def score_contamination(matches: List[Dict], total_words: int) -> Tuple[str, int, str]:
    """Compute contamination score from match severity."""
    if not matches:
        return "clean", 0, "No AI fingerprint words detected."

    total_impact = sum(m["count"] * _parse_ratio(m["ratio"]) for m in matches)
    density = total_impact / max(total_words, 1) * 100

    # Weighted: formulaic phrases and high-ratio words hurt more
    severe_count = sum(
        1 for m in matches
        if m["category"] == "formulaic_phrase" or _parse_ratio(m["ratio"]) >= 30
    )

    if severe_count >= 3 and density > 5:
        return "heavy", min(round(density * 10), 100), \
            f"{len(matches)} fingerprint words found ({severe_count} severe). Heavy AI contamination."
    elif severe_count >= 1 or density > 2:
        return "moderate", min(round(density * 5), 80), \
            f"{len(matches)} fingerprint words found ({severe_count} severe). Moderate AI contamination."
    elif matches:
        return "light", min(round(density * 2), 40), \
            f"{len(matches)} fingerprint words found. Light AI influence."
    return "clean", 0, "No AI fingerprint words detected."


def generate_report(matches: List[Dict], total_words: int, text: str) -> str:
    level, score, description = score_contamination(matches, total_words)
    normalized = normalize_text(text)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

    lines = []
    lines.append("=" * 60)
    lines.append("  AI FINGERPRINT SCAN REPORT")
    lines.append("=" * 60)
    lines.append(f"  Words scanned:  {total_words}")
    lines.append(f"  Matches found:  {len(matches)}")
    lines.append(f"  Score:          {score}/100  [{level.upper()}]")
    lines.append(f"  → {description}")
    lines.append("")

    if not matches:
        lines.append("  No AI fingerprint words detected. Text appears clean.")
        return "\n".join(lines)

    # Group by category
    by_category: Dict[str, List[Dict]] = {}
    for m in matches:
        cat = m["category"]
        by_category.setdefault(cat, []).append(m)

    category_labels = {
        "formulaic_phrase": "FORMULAIC PHRASES (strongest AI signal)",
        "transition": "TRANSITION WORDS",
        "hedge": "HEDGE / IMPORTANCE WORDS",
        "verb": "AI-FAVORITE VERBS",
        "adverb": "OVERUSED ADVERBS",
        "positive_adjective": "OVERLY-POSITIVE ADJECTIVES",
        "intensifier": "INTENSIFIERS",
    }

    for cat in ("formulaic_phrase", "transition", "hedge", "verb",
                "adverb", "positive_adjective", "intensifier"):
        cat_matches = by_category.get(cat, [])
        if not cat_matches:
            continue
        label = category_labels.get(cat, cat.upper())
        lines.append(f"  ── {label} ──")
        for m in cat_matches:
            marker = "▐" if _parse_ratio(m["ratio"]) >= 30 else "▎"
            lines.append(
                f"    {marker} \"{m['display']}\"  ×{m['count']}  "
                f"({m['ratio']} more common in AI)"
            )
        lines.append("")

    # Sentence-level annotations
    if score >= 30:
        lines.append("  ── AFFECTED SENTENCES ──")
        for i, sent in enumerate(sentences):
            sent_lower = sent.lower()
            hits = [fp for fp in matches if fp["display"] in sent_lower]
            if hits:
                words = ", ".join(f'"{h["display"]}"' for h in hits[:3])
                lines.append(f"    [{i+1}] {sent[:100]}{'...' if len(sent)>100 else ''}")
                lines.append(f"         → contains: {words}")
        lines.append("")

    # Fix suggestions
    lines.append("  ── FIXES ──")
    suggestions = []
    if any(m["category"] == "formulaic_phrase" for m in matches):
        suggestions.append("• Delete every formulaic phrase. 'It is worth noting that' → delete entirely.")
    if any(m["category"] == "transition" for m in matches):
        suggestions.append("• Replace 'moreover/furthermore' with 'also'. Replace 'consequently' with 'so'.")
    if any(m["category"] == "verb" for m in matches):
        suggestions.append("• Replace 'utilize' with 'use'. 'Demonstrate' → 'show'. 'Leverage' → 'use'.")
    if any(m["category"] == "hedge" for m in matches):
        suggestions.append("• Cut 'crucial', 'significant', 'robust' — if something matters, explain why.")
    if any(m["category"] == "positive_adjective" for m in matches):
        suggestions.append("• Replace hyperbole ('groundbreaking', 'transformative') with concrete facts.")

    for s in suggestions:
        lines.append(f"  {s}")

    if not suggestions and matches:
        lines.append("  • Light contamination — review highlighted words and consider alternatives.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Scan text for AI fingerprint words and phrases"
    )
    parser.add_argument("file", nargs="?", help="Text file to scan")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--json", action="store_true", help="Output raw matches as JSON")
    parser.add_argument(
        "--db", default="datasets/ai-kos.db",
        help="Path to AI-KOS SQLite database with ai_fingerprint_words table"
    )
    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
    elif args.file:
        with open(args.file) as f:
            text = f.read()
    else:
        parser.print_help()
        sys.exit(1)

    if not Path(args.db).exists():
        print(f"ERROR: Database not found: {args.db}")
        print("Run: ai_kos_ingest_csv on inbox/ai-fingerprint-words.csv first")
        sys.exit(1)

    fingerprints = load_fingerprints(args.db)
    words = re.findall(r"[a-zA-Z']+", text)
    matches = find_fingerprints(text, fingerprints)

    if args.json:
        import json
        print(json.dumps({
            "total_words": len(words),
            "matches": matches,
            "contamination_score": score_contamination(matches, len(words))[1],
        }, indent=2))
    else:
        print(generate_report(matches, len(words), text))


if __name__ == "__main__":
    main()
