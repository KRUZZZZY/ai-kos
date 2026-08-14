#!/usr/bin/env python3
"""
Sentence Variance Checker — measures burstiness and structural uniformity
in text against known human-writing benchmarks.

Based on research findings:
  - Human texts: mean sentence length 15-25 words, std 8-15 (high variance)
  - AI texts: mean 18-22 words, std 5-8 (low variance — "burstiness" deficit)
  - AI texts: lower Type-Token Ratio (more repetition)
  - AI texts: more uniform sentence length distribution (lower coefficient of variation)

Usage:
    python3 check_variance.py <file.txt>
    python3 check_variance.py --stdin <<< "your text here"
    python3 check_variance.py --help

Output:
    A report comparing the input text's metrics against human and AI benchmarks,
    with a human-likelihood percentage and specific recommendations.
"""

import re
import sys
import math
import argparse
from collections import Counter
from typing import List, Dict, Tuple


# ── Human benchmarks (derived from 2024-2026 linguistic research) ──

HUMAN_BENCHMARKS = {
    "sentence_mean": (15, 25),       # acceptable range
    "sentence_std": (8, 15),         # expected std range (high = bursty)
    "sentence_cv": (0.3, 0.7),       # coefficient of variation
    "ttr": (0.65, 0.85),             # type-token ratio (lexical diversity)
    "hapax_ratio": (0.35, 0.55),     # words used exactly once / total types
    "avg_word_len": (4.2, 5.5),      # chars per word
}

AI_BENCHMARKS = {
    "sentence_mean": (18, 22),
    "sentence_std": (5, 8),
    "sentence_cv": (0.25, 0.45),
    "ttr": (0.50, 0.65),
    "hapax_ratio": (0.25, 0.40),
    "avg_word_len": (4.5, 5.8),
}


def get_sentences(text: str) -> List[str]:
    """Split text into sentences on .!? with newlines."""
    raw = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in raw if len(s.split()) >= 3]


def get_words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def compute_metrics(text: str) -> Dict:
    sentences = get_sentences(text)
    words = get_words(text)

    if len(sentences) < 3:
        return {"error": "Need at least 3 sentences for meaningful analysis"}

    sent_lengths = [len(s.split()) for s in sentences]
    n = len(sent_lengths)
    mean_sl = sum(sent_lengths) / n
    variance = sum((x - mean_sl) ** 2 for x in sent_lengths) / n
    std_sl = math.sqrt(variance)
    cv_sl = std_sl / mean_sl if mean_sl > 0 else 0

    total_words = len(words)
    unique_words = len(set(words))
    ttr = unique_words / total_words if total_words > 0 else 0

    word_counts = Counter(words)
    hapax = sum(1 for w, c in word_counts.items() if c == 1)
    hapax_ratio = hapax / total_words if total_words > 0 else 0

    word_lens = [len(w) for w in words]
    avg_word_len = sum(word_lens) / len(word_lens) if word_lens else 0

    # Top repeated words
    top_repeated = word_counts.most_common(10)
    repetition_ratio = sum(c for _, c in top_repeated[:5]) / total_words if total_words else 0

    return {
        "sentences": n,
        "total_words": total_words,
        "unique_words": unique_words,
        "sentence_mean": round(mean_sl, 1),
        "sentence_std": round(std_sl, 1),
        "sentence_cv": round(cv_sl, 3),
        "sentence_range": (min(sent_lengths), max(sent_lengths)),
        "ttr": round(ttr, 3),
        "hapax_ratio": round(hapax_ratio, 3),
        "avg_word_len": round(avg_word_len, 1),
        "repetition_ratio": round(repetition_ratio, 3),
        "top_repeated": top_repeated[:5],
        "sent_lengths": sent_lengths,
    }


def score_metric(value: float, human_range: Tuple[float, float],
                 ai_range: Tuple[float, float]) -> str:
    """Classify a metric as human-like, AI-like, or borderline."""
    h_lo, h_hi = human_range
    a_lo, a_hi = ai_range

    # Check overlap between ranges
    if h_lo <= value <= h_hi:
        # It's in human range. But is it also in AI range?
        if a_lo <= value <= a_hi:
            return "overlap"
        return "human"
    elif a_lo <= value <= a_hi:
        return "ai"
    else:
        # Outside both — check which it's closer to
        h_center = (h_lo + h_hi) / 2
        a_center = (a_lo + a_hi) / 2
        return "human" if abs(value - h_center) < abs(value - a_center) else "ai"


def generate_report(metrics: Dict) -> str:
    if "error" in metrics:
        return f"ERROR: {metrics['error']}"

    lines = []
    lines.append("=" * 55)
    lines.append("  SENTENCE VARIANCE REPORT")
    lines.append("=" * 55)
    lines.append(f"  Sentences:      {metrics['sentences']}")
    lines.append(f"  Total words:    {metrics['total_words']}")
    lines.append(f"  Unique words:   {metrics['unique_words']}  (TTR: {metrics['ttr']})")
    lines.append("")

    # Score each metric
    scores = {}
    for key in ("sentence_std", "sentence_cv", "ttr", "hapax_ratio", "avg_word_len"):
        val = metrics[key]
        result = score_metric(val, HUMAN_BENCHMARKS[key], AI_BENCHMARKS[key])
        scores[key] = result

    human_count = sum(1 for v in scores.values() if v == "human")
    overlap_count = sum(1 for v in scores.values() if v == "overlap")
    ai_count = sum(1 for v in scores.values() if v == "ai")
    total = len(scores)
    human_pct = round((human_count + overlap_count * 0.5) / total * 100)

    lines.append(f"  Sentence mean:  {metrics['sentence_mean']} words")
    lines.append(f"  Sentence std:   {metrics['sentence_std']}  [{scores['sentence_std']}]  human: 8-15  ai: 5-8")
    lines.append(f"  Sentence CV:    {metrics['sentence_cv']}  [{scores['sentence_cv']}]  human: 0.30-0.70  ai: 0.25-0.45")
    lines.append(f"  Range:          {metrics['sentence_range'][0]}–{metrics['sentence_range'][1]} words")
    lines.append("")
    lines.append(f"  TTR:            {metrics['ttr']}  [{scores['ttr']}]  human: 0.65-0.85  ai: 0.50-0.65")
    lines.append(f"  Hapax ratio:    {metrics['hapax_ratio']}  [{scores['hapax_ratio']}]  human: 0.35-0.55  ai: 0.25-0.40")
    lines.append(f"  Avg word len:   {metrics['avg_word_len']}  [{scores['avg_word_len']}]  human: 4.2-5.5  ai: 4.5-5.8")
    lines.append("")
    lines.append(f"  Top words:      {', '.join(f'{w}({c}x)' for w, c in metrics['top_repeated'])}")
    lines.append("")
    lines.append(f"  → HUMAN-LIKELIHOOD: {human_pct}%  ({human_count} human, {overlap_count} overlap, {ai_count} ai)")
    lines.append("")

    # Recommendations
    if ai_count > 0 or overlap_count >= 3:
        lines.append("  RECOMMENDATIONS:")
        if scores["sentence_std"] in ("ai", "overlap"):
            lines.append("    • Vary sentence length more aggressively. Mix 3-word and 30-word sentences.")
        if scores["ttr"] in ("ai",):
            lines.append("    • Increase lexical diversity. Use more synonyms, fewer repetitions.")
        if scores["hapax_ratio"] in ("ai",):
            lines.append("    • Introduce more one-off words. AI reuses vocabulary; humans invent.")
        if scores["avg_word_len"] in ("ai",):
            lines.append("    • Use shorter, punchier words. AI defaults to Latinate vocabulary.")
        lines.append("")

    # Sentence length histogram
    lengths = metrics["sent_lengths"]
    if lengths:
        bins = {}
        for l in lengths:
            bucket = (l // 5) * 5
            bins[bucket] = bins.get(bucket, 0) + 1
        lines.append("  Sentence length distribution:")
        max_bucket = max(bins.keys()) if bins else 0
        for b in sorted(bins):
            bar = "█" * bins[b]
            lines.append(f"    {b:3d}-{b+4:3d}: {bar} ({bins[b]})")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check text for AI-like sentence uniformity (burstiness analysis)"
    )
    parser.add_argument("file", nargs="?", help="Text file to analyze")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--json", action="store_true", help="Output raw metrics as JSON")
    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
    elif args.file:
        with open(args.file) as f:
            text = f.read()
    else:
        parser.print_help()
        sys.exit(1)

    metrics = compute_metrics(text)
    if args.json:
        import json
        print(json.dumps(metrics, indent=2))
    else:
        print(generate_report(metrics))


if __name__ == "__main__":
    main()
