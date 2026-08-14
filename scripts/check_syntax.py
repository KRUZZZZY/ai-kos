#!/usr/bin/env python3
"""
Nominal Density & Syntax Checker — measures noun-to-pronoun ratios,
adjective density, and auxiliary verb usage against human benchmarks.

Based on research (Georgiou 2025, Munoz-Ortiz 2024):
  - AI text: higher nominal density (more nouns, fewer pronouns/auxiliaries)
  - AI text: more adjectives and adjectival modifiers
  - Human text: heavier functional morphology (more pronouns, auxiliaries)

Usage:
    python3 check_syntax.py <file.txt>
    python3 check_syntax.py --stdin <<< "your text"
"""

import re
import sys
import argparse
from collections import Counter
from typing import Dict, List, Tuple


# ── Word lists ──

COMMON_NOUNS = {
    "system", "model", "data", "result", "method", "approach", "analysis",
    "performance", "evaluation", "dataset", "architecture", "framework",
    "algorithm", "component", "configuration", "implementation", "parameter",
    "technique", "strategy", "process", "function", "structure", "network",
    "application", "solution", "task", "problem", "feature", "metric",
    "accuracy", "error", "training", "inference", "layer", "module",
    "representation", "distribution", "classification", "detection",
    "generation", "prediction", "optimization", "validation", "experiment",
    "finding", "limitation", "contribution", "domain", "context",
    "evidence", "hypothesis", "insight", "mechanism", "phenomenon",
    "property", "relationship", "pattern", "trend", "variation",
}

PRONOUNS = {
    "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their",
    "mine", "yours", "hers", "ours", "theirs",
    "myself", "yourself", "himself", "herself", "itself",
    "ourselves", "yourselves", "themselves",
    "this", "that", "these", "those",  # demonstratives
    "who", "whom", "whose", "which", "what",  # interrogative/relative
    "someone", "anyone", "everyone", "no one", "nobody",
    "something", "anything", "everything", "nothing",
}

AUXILIARIES = {
    "be", "am", "is", "are", "was", "were", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did", "doing",
    "can", "could", "will", "would", "shall", "should",
    "may", "might", "must",
    "not", "n't",  # negation (counts as functional)
    # Contractions
    "i'm", "you're", "he's", "she's", "it's", "we're", "they're",
    "i've", "you've", "we've", "they've",
    "i'd", "you'd", "he'd", "she'd", "we'd", "they'd",
    "i'll", "you'll", "he'll", "she'll", "we'll", "they'll",
    "ain't", "won't", "shan't",
    "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't",
    "weren't", "haven't", "hasn't", "hadn't", "can't", "couldn't",
    "wouldn't", "shouldn't", "mightn't", "mustn't",
}

ADJECTIVES = {
    "new", "good", "high", "old", "great", "big", "small", "large",
    "long", "short", "early", "late", "young", "different", "important",
    "major", "key", "significant", "robust", "comprehensive",
    "extensive", "detailed", "careful", "thorough", "rigorous",
    "novel", "innovative", "effective", "efficient", "optimal",
    "superior", "improved", "enhanced", "advanced", "modern",
    "traditional", "conventional", "standard", "typical",
    "various", "several", "numerous", "multiple",
    "simple", "complex", "difficult", "easy", "hard",
    "clear", "obvious", "apparent", "evident",
    "possible", "likely", "unlikely", "potential",
    "specific", "particular", "general", "overall",
    "current", "previous", "future", "recent", "prior",
    "available", "suitable", "appropriate", "relevant",
    "common", "rare", "unique", "distinct", "similar",
}


def get_words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def count_categories(words: List[str]) -> Dict:
    total = len(words)
    noun_count = sum(1 for w in words if w in COMMON_NOUNS)
    pronoun_count = sum(1 for w in words if w in PRONOUNS)
    aux_count = sum(1 for w in words if w in AUXILIARIES)
    adj_count = sum(1 for w in words if w in ADJECTIVES)

    return {
        "total": total,
        "nouns": noun_count,
        "pronouns": pronoun_count,
        "auxiliaries": aux_count,
        "adjectives": adj_count,
        "noun_ratio": round(noun_count / max(total, 1) * 100, 1),
        "pronoun_ratio": round(pronoun_count / max(total, 1) * 100, 1),
        "aux_ratio": round(aux_count / max(total, 1) * 100, 1),
        "adj_ratio": round(adj_count / max(total, 1) * 100, 1),
        "noun_pronoun_ratio": round(noun_count / max(pronoun_count, 1), 1),
        "functional_ratio": round((pronoun_count + aux_count) / max(total, 1) * 100, 1),
    }


def generate_report(counts: Dict) -> str:
    # Human benchmarks (approximate, from research)
    # Human: 5-12% pronouns, 8-15% auxiliaries, noun:pronoun ratio < 2:1
    # AI: 2-5% pronouns, 5-8% auxiliaries, noun:pronoun ratio > 3:1

    lines = []
    lines.append("=" * 55)
    lines.append("  NOMINAL DENSITY & SYNTAX REPORT")
    lines.append("=" * 55)
    lines.append(f"  Total words:        {counts['total']}")
    lines.append("")
    lines.append(f"  Nouns:      {counts['nouns']:3d}  ({counts['noun_ratio']:5.1f}%)")
    lines.append(f"  Pronouns:   {counts['pronouns']:3d}  ({counts['pronoun_ratio']:5.1f}%)  human: 5-12%  ai: 2-5%")
    lines.append(f"  Auxiliaries:{counts['auxiliaries']:3d}  ({counts['aux_ratio']:5.1f}%)  human: 8-15%  ai: 5-8%")
    lines.append(f"  Adjectives: {counts['adjectives']:3d}  ({counts['adj_ratio']:5.1f}%)")
    lines.append("")
    lines.append(f"  Noun:Pronoun ratio:   {counts['noun_pronoun_ratio']:.1f}:1  human: <2:1  ai: >3:1")
    lines.append(f"  Functional words:     {counts['functional_ratio']:.1f}%  human: 15-25%  ai: 8-12%")
    lines.append("")

    # Scoring
    issues = []
    if counts["pronoun_ratio"] < 3:
        issues.append("CRITICAL: Pronoun ratio too low. Add 'I', 'we', 'it', 'they' throughout.")
    elif counts["pronoun_ratio"] < 5:
        issues.append("WARNING: Pronoun ratio below human baseline. Consider adding more.")
    if counts["noun_pronoun_ratio"] > 3:
        issues.append("CRITICAL: Noun-to-pronoun ratio indicates heavy nominal density (AI-like).")
    elif counts["noun_pronoun_ratio"] > 2:
        issues.append("WARNING: Noun-to-pronoun ratio elevated. Add pronouns, reduce noun chains.")
    if counts["aux_ratio"] < 5:
        issues.append("CRITICAL: Auxiliary usage below human range. Add 'can', 'will', 'might', 'should'.")
    if counts["functional_ratio"] < 12:
        issues.append("WARNING: Functional morphology below human baseline. More pronouns + auxiliaries needed.")

    if issues:
        for i in issues:
            lines.append(f"  ⚠ {i}")
    else:
        lines.append("  ✓ All metrics within human ranges.")

    # Concrete fix suggestions
    lines.append("")
    lines.append("  FIXES:")
    if counts["noun_pronoun_ratio"] > 2:
        lines.append("    • Replace noun chains: 'the model performance evaluation' → 'how well it performs'")
        lines.append("    • Add subject pronouns: 'The system processes...' → 'It processes...'")
    if counts["aux_ratio"] < 8:
        lines.append("    • Add auxiliaries: 'The method works' → 'The method can work' or 'might work'")
        lines.append("    • Use contractions: 'it is' → 'it's', 'we have' → 'we've'")
    if counts["adj_ratio"] > 8:
        lines.append("    • Cut stacked adjectives: 'comprehensive rigorous evaluation' → 'evaluation'")
        lines.append("    • Replace adjectives with evidence: 'significant improvement' → '94% accuracy'")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check text for AI-like nominal density and syntax patterns"
    )
    parser.add_argument("file", nargs="?", help="Text file to analyze")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--json", action="store_true", help="Output raw counts as JSON")
    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
    elif args.file:
        with open(args.file) as f:
            text = f.read()
    else:
        parser.print_help()
        sys.exit(1)

    words = get_words(text)
    counts = count_categories(words)

    if args.json:
        import json
        print(json.dumps(counts, indent=2))
    else:
        print(generate_report(counts))


if __name__ == "__main__":
    main()
