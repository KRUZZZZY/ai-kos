#!/usr/bin/env python3
"""
de_ai.py — Algorithmic multi-sweep AI-text reducer.

Applies 4 deterministic transformation passes, each targeting a specific
linguistic dimension where AI text deviates from human norms. Each sweep
produces a checkpoint file. Scores are computed before and after.

Sweeps:
  1. BURSTINESS  — vary sentence lengths (split/merge)
  2. VOCABULARY  — replace AI fingerprint words with human alternatives
  3. SYNTAX      — inject pronouns, auxiliaries, contractions
  4. TONE        — add doubt, personal references, emotional range

Usage:
    python3 de_ai.py input.txt                    # interactive mode
    python3 de_ai.py input.txt --auto             # run all sweeps, show final diff
    python3 de_ai.py input.txt --sweep 1          # run only sweep 1
    python3 de_ai.py input.txt --dry-run          # show what would change, don't write

Output:
    Checkpoints saved as input.deai-1.txt, input.deai-2.txt, etc.
    Each checkpoint shows before/after scores for all 3 checkers.
"""

import re
import sys
import os
import sqlite3
import argparse
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


# ── Project root (for finding scripts and db) ──

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DB_PATH = PROJECT_ROOT / "datasets" / "ai-kos.db"


# ═══════════════════════════════════════════════════════════════════
# FINGERPRINT DATABASE
# ═══════════════════════════════════════════════════════════════════

def load_substitution_map() -> Dict[str, str]:
    """Load AI→human word substitutions, merging DB entries with hardcoded defaults."""
    subs = dict(SUBSTITUTIONS)  # Start with full hardcoded dict

    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            "SELECT word, category FROM ai_fingerprint_words"
        ).fetchall()
        conn.close()

        for word, category in rows:
            display = word.replace("_", " ")
            # DB entries override hardcoded if they match a key
            if display in SUBSTITUTIONS:
                subs[display] = SUBSTITUTIONS[display]

    return subs


# ── Human alternatives for every fingerprint word ──

SUBSTITUTIONS: Dict[str, str] = {
    # Transitions
    "moreover": "also",
    "furthermore": "also",
    "consequently": "so",
    "additionally": "also",
    "notably": "",
    # Hedges
    "crucial": "key",
    "significant": "large",
    "robust": "solid",
    "comprehensive": "thorough",
    "interestingly": "",
    # Intensifiers
    "remarkable": "striking",
    "invaluable": "useful",
    "profound": "deep",
    "pivotal": "central",
    "transformative": "big",
    "groundbreaking": "new",
    "unprecedented": "unusual",
    # Verbs (base + common inflections)
    "demonstrate": "show",
    "demonstrates": "shows",
    "demonstrated": "showed",
    "demonstrating": "showing",
    "showcase": "show",
    "showcases": "shows",
    "showcased": "showed",
    "highlight": "point to",
    "highlights": "points to",
    "highlighted": "pointed to",
    "delve": "look into",
    "delves": "looks into",
    "delved": "looked into",
    "explore": "look at",
    "explores": "looks at",
    "explored": "looked at",
    "leveraging": "using",
    "leverage": "use",
    "leverages": "uses",
    "leveraged": "used",
    "utilize": "use",
    "utilizes": "uses",
    "utilized": "used",
    "utilizing": "using",
    "facilitate": "help",
    "facilitates": "helps",
    "facilitated": "helped",
    "foster": "build",
    "fosters": "builds",
    "fostered": "built",
    "garner": "get",
    "garners": "gets",
    "garnered": "got",
    "notably": "",
    # Adverbs
    "undoubtedly": "clearly",
    "invariably": "always",
    "fundamentally": "basically",
    # Formulaic phrases (full removal)
    "it is worth noting that": "",
    "it is important to note": "",
    "in other words": "",
    "in today's world": "now",
    "in conclusion": "finally",
    "as we have seen": "",
    "dive deep into": "examine",
    "a testament to": "shows",
    "plays a crucial role": "matters",
    "in the landscape of": "in",
    "has emerged as": "became",
    "a myriad of": "many",
}


# ═══════════════════════════════════════════════════════════════════
# CORE TEXT UTILITIES
# ═══════════════════════════════════════════════════════════════════

def get_sentences(text: str) -> List[str]:
    raw = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in raw if len(s.split()) >= 2]


def get_words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def word_count(text: str) -> int:
    return len(get_words(text))


def reconstruct(sentences: List[str]) -> str:
    return " ".join(sentences)


# ═══════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Scores:
    variance_human_pct: int = 0
    fingerprint_score: int = 0
    fingerprint_matches: int = 0
    noun_pronoun_ratio: float = 0.0
    functional_pct: float = 0.0
    adj_pct: float = 0.0
    total_words: int = 0

    def summary(self) -> str:
        return (
            f"  variance: {self.variance_human_pct}% human  |  "
            f"fingerprints: {self.fingerprint_score}/100 ({self.fingerprint_matches} hits)  |  "
            f"syntax: n:p={self.noun_pronoun_ratio:.1f}  func={self.functional_pct:.0f}%  "
            f"adj={self.adj_pct:.0f}%  |  words: {self.total_words}"
        )


def score_text(text: str) -> Scores:
    """Run all three checkers and parse scores."""
    s = Scores()
    s.total_words = word_count(text)

    # Variance
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_variance.py"), "--stdin", "--json"],
            input=text, capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            scores = {}
            for key, (h_lo, h_hi), (a_lo, a_hi) in [
                ("sentence_std", (8, 15), (5, 8)),
                ("sentence_cv", (0.30, 0.70), (0.25, 0.45)),
                ("ttr", (0.65, 0.85), (0.50, 0.65)),
                ("hapax_ratio", (0.35, 0.55), (0.25, 0.40)),
                ("avg_word_len", (4.2, 5.5), (4.5, 5.8)),
            ]:
                val = data.get(key, 0)
                if h_lo <= val <= h_hi:
                    scores[key] = "human" if not (a_lo <= val <= a_hi) else "overlap"
                elif a_lo <= val <= a_hi:
                    scores[key] = "ai"
                else:
                    h_c = (h_lo + h_hi) / 2
                    a_c = (a_lo + a_hi) / 2
                    scores[key] = "human" if abs(val - h_c) < abs(val - a_c) else "ai"
            hc = sum(1 for v in scores.values() if v == "human")
            oc = sum(1 for v in scores.values() if v == "overlap")
            s.variance_human_pct = round((hc + oc * 0.5) / len(scores) * 100)
    except Exception:
        pass

    # Fingerprints
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "scan_fingerprints.py"), "--stdin", "--json"],
            input=text, capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            s.fingerprint_score = data.get("contamination_score", 0)
            s.fingerprint_matches = len(data.get("matches", []))
    except Exception:
        pass

    # Syntax
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_syntax.py"), "--stdin", "--json"],
            input=text, capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            s.noun_pronoun_ratio = data.get("noun_pronoun_ratio", 0)
            s.functional_pct = data.get("functional_ratio", 0)
            s.adj_pct = data.get("adj_ratio", 0)
    except Exception:
        pass

    return s


# ═══════════════════════════════════════════════════════════════════
# SWEEP 1: BURSTINESS — vary sentence lengths
# ═══════════════════════════════════════════════════════════════════

def sweep_burstiness(text: str) -> str:
    """Increase sentence length variance by splitting/merging."""
    sentences = get_sentences(text)
    if len(sentences) < 4:
        return text

    lengths = [len(s.split()) for s in sentences]
    mean_len = sum(lengths) / len(lengths)

    result = []
    i = 0
    while i < len(sentences):
        s = sentences[i]
        wc = lengths[i]

        # If we have fewer than 4 sentences, force at least one split/merge
        force_action = len(sentences) < 5 and i == 0

        # Split long sentences (> mean + 3)
        if wc > mean_len + 3 and (i == 0 or lengths[i-1] > mean_len - 1 or force_action):
            words_list = s.split()
            mid = len(words_list) // 2
            # Find a good split point near the middle (after comma, semicolon, or "and"/"but")
            split_at = mid
            for j in range(mid, min(mid + 8, len(words_list))):
                if words_list[j].rstrip(",") in (",", ";") or words_list[j].lower() in ("and", "but", "or", "yet", "so"):
                    split_at = j + 1
                    break
            if mid < split_at < len(words_list) - 2:
                first_half = " ".join(words_list[:split_at]).rstrip(",;")
                second_half = " ".join(words_list[split_at:])
                # Only split if both fragments are at least 5 words
                if len(first_half.split()) >= 5 and len(second_half.split()) >= 5:
                    result.append(first_half + ".")
                    result.append(second_half[0].upper() + second_half[1:] if len(second_half) > 1 else second_half)
                    i += 1
                    continue

        # If two consecutive similar-length sentences, merge them
        if (i + 1 < len(sentences) and
            wc < mean_len and lengths[i+1] < mean_len):
            merged = s.rstrip(".") + " and " + sentences[i+1].lower().lstrip()
            if not merged.endswith("."):
                merged += "."
            result.append(merged)
            i += 2
            continue

        result.append(s)
        i += 1

    return reconstruct(result)


# ═══════════════════════════════════════════════════════════════════
# SWEEP 2: VOCABULARY — replace fingerprint words
# ═══════════════════════════════════════════════════════════════════

def sweep_vocabulary(text: str) -> str:
    """Replace AI fingerprint words with human alternatives."""
    subs = load_substitution_map()
    if not subs:
        subs = SUBSTITUTIONS

    result = text
    # Sort by length (longest first) to avoid partial matches
    for ai_word in sorted(subs.keys(), key=len, reverse=True):
        replacement = subs[ai_word]
        # Case-insensitive replacement with word boundary awareness
        pattern = re.compile(
            r'\b' + re.escape(ai_word) + r'\b',
            re.IGNORECASE
        )

        def replace_match(m):
            matched = m.group(0)
            if replacement == "":
                # Just return empty string — sub() handles the removal
                return ""
            # Preserve capitalization
            if matched[0].isupper():
                return replacement.capitalize()
            return replacement

        result = pattern.sub(replace_match, result)

    # Clean up artifacts from removals: double spaces, comma-space, double periods,
    # orphaned commas at sentence starts, lowercase sentence starts after removals
    result = re.sub(r'  +', ' ', result)
    result = re.sub(r' ,', ',', result)
    result = re.sub(r' \.', '.', result)
    result = re.sub(r'\.\.+', '.', result)
    result = re.sub(r',\s*,', ',', result)
    result = re.sub(r'\.,\s', '. ', result)  # fix "., " after removal
    # Context-aware post-correction: revert substitutions that produce
    # known-awkward academic bigrams where the original word is correct.
    _CONTEXT_GUARDS = [
        (r'\b(practically|statistically|clinically|economically)\s+large\b',
         lambda m: m.group(0).replace('large', 'significant')),
        (r'\b(statistical)\s+large\b',
         lambda m: m.group(0).replace('large', 'significance')),
    ]
    for pattern, replacer in _CONTEXT_GUARDS:
        result = re.sub(pattern, replacer, result, flags=re.IGNORECASE)
    # Fix double spaces again after all transformations
    result = re.sub(r'  +', ' ', result)
    # Ensure first letter is uppercase
    if result and result[0].islower():
        result = result[0].upper() + result[1:]

    return result


# ═══════════════════════════════════════════════════════════════════
# SWEEP 3: SYNTAX — inject pronouns and auxiliaries
# ═══════════════════════════════════════════════════════════════════

def sweep_syntax(text: str) -> str:
    """Increase functional morphology: pronouns, auxiliaries, contractions."""
    sentences = get_sentences(text)
    if len(sentences) < 3:
        return text

    result = []
    # Track last subject for pronoun replacement
    last_subject_noun = None

    for i, s in enumerate(sentences):
        modified = s

        # 1. Replace "it is" → "it's" (every other occurrence to avoid overdoing it)
        if i % 2 == 0:
            modified = re.sub(r'\bit is\b', "it's", modified, count=1, flags=re.IGNORECASE)
            modified = re.sub(r'\bthat is\b', "that's", modified, count=1, flags=re.IGNORECASE)
            modified = re.sub(r'\bwe are\b', "we're", modified, count=1, flags=re.IGNORECASE)
            modified = re.sub(r'\bthey are\b', "they're", modified, count=1, flags=re.IGNORECASE)

        # 2. Replace "do not" → "don't", "cannot" → "can't" (sparingly)
        if "do not" in modified and i % 3 == 0:
            modified = modified.replace("do not", "don't", 1)
        if "cannot" in modified and i % 3 == 1:
            modified = modified.replace("cannot", "can't", 1)

        # 3. No-op: auxiliary injection removed. Blindly prepending "may" to
        #    "is"/"are" produces ungrammatical output ("may is", "may are").
        #    Contractions (step 1-2) handle the functional morphology boost safely.

        result.append(modified)

    return reconstruct(result)


# ═══════════════════════════════════════════════════════════════════
# SWEEP 4: TONE — add emotional variation
# ═══════════════════════════════════════════════════════════════════

def sweep_tone(text: str) -> str:
    """Add doubt, personal references, and emotional range."""
    sentences = get_sentences(text)
    if len(sentences) < 3:
        return text

    result = []
    for i, s in enumerate(sentences):
        modified = s

        # 1. First substantive sentence: add a personal reference
        if i == 1 and len(s.split()) > 5:
            if not re.search(r'\b(I|we|my|our)\b', modified, re.IGNORECASE):
                modified = "I think " + modified[0].lower() + modified[1:]

        # 2. Mid-text: inject doubt on a strong claim
        if i == len(sentences) // 2 and len(s.split()) > 8:
            if not any(w in modified.lower() for w in ("might", "perhaps", "maybe", "could", "possible")):
                modified = modified.rstrip(".") + ", though this may not hold in all cases."

        # 3. Final sentence: add a qualifying remark
        if i == len(sentences) - 1 and len(s.split()) > 5:
            if not any(w in modified.lower() for w in ("however", "but", "although", "yet")):
                words = modified.split()
                if len(words) > 6:
                    # Insert "Still," at the start if it's a concluding statement
                    if any(modified.lower().startswith(w) for w in ("this", "these", "the", "our", "in")):
                        modified = "Still, " + modified[0].lower() + modified[1:]

        result.append(modified)

    return reconstruct(result)


# ═══════════════════════════════════════════════════════════════════
# ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════

SWEEPS = [
    ("burstiness", sweep_burstiness, "Vary sentence lengths for natural rhythm"),
    ("vocabulary", sweep_vocabulary, "Replace AI fingerprint words with human alternatives"),
    ("syntax", sweep_syntax, "Inject pronouns, auxiliaries, and contractions"),
    ("tone", sweep_tone, "Add doubt, personal references, and emotional range"),
]

CHECKPOINT_PATTERN = "{base}.deai-{n}.txt"


def run_sweeps(
    text: str,
    input_path: str,
    sweeps_to_run: List[int],
    interactive: bool = True,
    dry_run: bool = False,
) -> str:
    """Run the specified sweeps, with optional human review between each."""
    current = text
    base = os.path.splitext(input_path)[0]

    print(f"\n{'='*60}")
    print(f"  DE-AI SWEEPS — {Path(input_path).name}")
    print(f"{'='*60}")

    # Baseline
    print("\n  BASELINE SCORES:")
    baseline = score_text(current)
    print(baseline.summary())

    for sweep_idx in sweeps_to_run:
        if sweep_idx < 1 or sweep_idx > 4:
            print(f"  ERROR: Invalid sweep number {sweep_idx} (1-4)")
            continue

        name, func, desc = SWEEPS[sweep_idx - 1]

        print(f"\n  ── SWEEP {sweep_idx}: {name.upper()} ──")
        print(f"  {desc}")

        before = current
        current = func(current)

        # Score after sweep
        after_scores = score_text(current)

        # Show delta
        print(f"\n  AFTER {name}:")
        print(after_scores.summary())
        print(f"  Δ variance: {after_scores.variance_human_pct - baseline.variance_human_pct:+d}%  "
              f"Δ fingerprints: {after_scores.fingerprint_score - baseline.fingerprint_score:+d}  "
              f"Δ n:p: {after_scores.noun_pronoun_ratio - baseline.noun_pronoun_ratio:+.1f}")

        # Show diff excerpt
        if not dry_run:
            before_words = word_count(before)
            after_words = word_count(current)
            print(f"  Words: {before_words} → {after_words} ({after_words - before_words:+d})")

        # Save checkpoint if not dry run
        ckpt_path = None
        if not dry_run:
            ckpt_path = CHECKPOINT_PATTERN.format(base=base, n=sweep_idx)
            with open(ckpt_path, 'w') as f:
                f.write(current)
            print(f"  → saved: {ckpt_path}")

        # Interactive review
        if interactive and not dry_run and sweep_idx < max(sweeps_to_run) and ckpt_path:
            print(f"\n  ── REVIEW CHECKPOINT ──")
            print(f"  File: {ckpt_path}")
            print(f"  Read it, edit if needed, then press Enter to continue...")
            try:
                input()
                # Reload in case user edited
                if os.path.exists(ckpt_path):
                    with open(ckpt_path) as f:
                        current = f.read()
                baseline = score_text(current)  # update baseline for next sweep
            except (EOFError, KeyboardInterrupt):
                print("\n  Interrupted. Final checkpoint saved.")
                return current

    # Final
    print(f"\n{'='*60}")
    print(f"  FINAL SCORES:")
    final = score_text(current)
    print(final.summary())
    print(f"  Δ from baseline: variance {final.variance_human_pct - score_text(text).variance_human_pct:+d}%  "
          f"fingerprints {final.fingerprint_score - score_text(text).fingerprint_score:+d}  "
          f"n:p {final.noun_pronoun_ratio - score_text(text).noun_pronoun_ratio:+.1f}")

    if not dry_run:
        final_path = CHECKPOINT_PATTERN.format(base=base, n="final")
        with open(final_path, 'w') as f:
            f.write(current)
        print(f"  → final: {final_path}")

    return current


def main():
    parser = argparse.ArgumentParser(
        description="Algorithmic multi-sweep AI-text reducer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 de_ai.py essay.txt              # interactive — pause after each sweep
  python3 de_ai.py essay.txt --auto       # run all 4 sweeps, show final diff
  python3 de_ai.py essay.txt --sweep 1    # run only burstiness sweep
  python3 de_ai.py essay.txt --dry-run    # show what would change, don't write
        """,
    )
    parser.add_argument("file", help="Input text file")
    parser.add_argument("--auto", action="store_true", help="Run all sweeps without pausing")
    parser.add_argument("--sweep", type=int, choices=[1, 2, 3, 4], action="append",
                        help="Run only this sweep (repeatable: --sweep 2 --sweep 4)")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing files")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    with open(args.file) as f:
        text = f.read()

    if not text.strip():
        print("ERROR: Empty file")
        sys.exit(1)

    sweeps_to_run = args.sweep if args.sweep else [1, 2, 3, 4]

    run_sweeps(
        text=text,
        input_path=args.file,
        sweeps_to_run=sweeps_to_run,
        interactive=not args.auto,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
