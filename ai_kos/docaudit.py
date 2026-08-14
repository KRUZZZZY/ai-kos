"""Documentation coverage audit for AI-KOS.

Maps every ``ai_kos/*.py`` module to the knowledge-base articles that mention
it, then classifies each module's documentation coverage:

* DOCUMENTED   — a ``help`` article names the module (or one of its components)
* PARTIAL      — only non-help articles (process / mission / research-note /
                 plan / note / base) mention it
* UNDOCUMENTED — no article mentions it

Also flags stale hardcoded numbers found in help articles (e.g. "19 MCP tools",
"18 subcommands", "N tests") so they can be reviewed — it does NOT fix them.

Dependency-free (Python stdlib only) and intentionally fast: it scans the
YAML frontmatter (title / slug / keywords / summary) of every article with
plain-text + regex matching, so a full run completes in well under 5 seconds.

Usage:
    python3 -m ai_kos.docaudit            # human-readable report
    python3 -m ai_kos.docaudit --json     # machine-readable report
    ai-kos doc-audit                      # via the CLI (wired in cli.py)

Reusable entry point:
    from ai_kos.docaudit import audit
    result = audit()                      # dict of per-module findings
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Modules that are not part of the public package surface (build/one-shot
# utilities and the VS Code bridge), and therefore excluded from the audit.
EXCLUDE_MODULES = {
    "__init__",
    "restore_md_bodies",
    "migrate_to_db",
    "vscode_bridge",
}

# Extra search tokens per module, on top of the stem and its hyphenated /
# spaced variants which are derived automatically. These capture the
# "known components" a module maps to (e.g. linker -> auto-link, idf-linker;
# server -> dashboard, flask; search -> tf-idf).
EXTRA_ALIASES = {
    "articles": ["article", "crud", "article-types"],
    "batch_ingest": ["batch", "batch ingest", "batch-ingest"],
    "bibtex": ["bibliography", "bibtex-export"],
    "bindings": ["binding", "declarative-bindings", "pydantic-settings"],
    "blobs": ["blob", "blob-storage"],
    "cli": ["command-line", "subcommand", "argparse"],
    "config": ["configuration", "deep-merge"],
    "datasets": ["dataset", "sql-datasets", "time-series"],
    "db": ["sqlite", "database", "body-cache", "wal"],
    "deep_research": ["deep-research", "deep research"],
    "graph_data": ["graph-export", "graph-data", "nodes", "edges"],
    "graphs": ["graph-storage", "graph", "knowledge-graph", "shortest-path"],
    "ingestion": ["ingest", "ingestion", "extract"],
    "linker": ["auto-link", "auto-linker", "idf-linker", "wikilink"],
    "mcp_server": ["mcp", "mcp-server", "json-rpc"],
    "migrate": ["migration", "schema-migration", "versioning"],
    "paper_compare": ["paper-comparison", "paper comparison", "comparison"],
    "papers": ["paper", "full-text", "research-note"],
    "pipeline": ["research-pipeline", "durable-execution", "workflow"],
    "schemas": ["schema", "template", "pydantic", "validation"],
    "search": ["tf-idf", "tfidf", "cosine-similarity", "inverted-index"],
    "semantic": ["semantic-search", "embeddings", "faiss", "rrf"],
    "server": ["dashboard", "flask", "web", "frontend"],
    "taskqueue": ["task-queue", "task queue", "queue", "priority-queue"],
    "tasks": ["future-task", "task-manager", "task", "reminder"],
}

# Article types that count as a *dedicated* documentation signal.
HELP_TYPES = {"help"}

# Article types that count as a *partial* (mention-only) signal. Anything that
# matches but is neither help nor one of these still counts as PARTIAL — the
# distinction is that DOCUMENTED strictly requires a help article.
PARTIAL_TYPES = {
    "process",
    "mission",
    "research-note",
    "plan",
    "note",
    "base",
    "procedure",
}

# Patterns for stale hardcoded numbers we merely flag (not fix).
_STALE_PATTERNS = [
    re.compile(r"\b\d+\s+(?:MCP|JSON-RPC|json-rpc)\s+tools?\b", re.I),
    re.compile(r"\b\d+\s+tests?\b", re.I),
    re.compile(r"\b\d+\s+subcommands?\b", re.I),
    re.compile(r"\b\d+\s+backends?\b", re.I),
    re.compile(r"\b\d+\s+enums?\b", re.I),
    re.compile(r"\b\d+\s+sub-models?\b", re.I),
    re.compile(r"\b\d+\s+article types?\b", re.I),
    re.compile(r"\b\d+\s+(?:step|stage|phase)s?\b", re.I),
]


# --------------------------------------------------------------------------- #
# Frontmatter helpers (stdlib-only, no PyYAML dependency)
# --------------------------------------------------------------------------- #

def _extract_frontmatter(raw: str, suffix: str) -> str:
    """Return the YAML frontmatter block of an article file.

    ``.md`` files use a ``---``-delimited block; ``.yaml``/``.yml`` stubs are
    bare YAML, so the whole file is the frontmatter.
    """
    if suffix == ".md":
        m = re.match(r"^---\s*\n(.*?)\n---", raw, re.DOTALL)
        return m.group(1) if m else raw  # fall back to whole text if no block
    return raw


def _field(fm: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+?)\s*$", fm, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _multiline_field(fm: str, name: str) -> str:
    """Extract a possibly multi-line scalar (e.g. a folded ``summary``)."""
    m = re.search(rf"^{name}:\s*(.*?)(?=^[A-Za-z_][\w-]*:\s|\Z)",
                  fm, re.DOTALL | re.MULTILINE)
    return m.group(1).strip() if m else ""


def _keywords_block(fm: str) -> str:
    m = re.search(r"^keywords:\s*\n((?:[ \t]*-\s*.+\n?)+)", fm, re.MULTILINE)
    return m.group(1) if m else ""


def _article_search_text(fm: str) -> str:
    """The searchable text for an article: title + slug + keywords + summary.

    We deliberately search *only* these fields (per the coverage-audit spec),
    so that ``related:`` links and ``provenance:`` origin refs to *other*
    modules don't cause false-positive matches.
    """
    parts = [
        _field(fm, "title"),
        _field(fm, "slug"),
        _keywords_block(fm),
        _multiline_field(fm, "summary"),
    ]
    return "\n".join(parts).lower()


def _token_pattern(token: str) -> re.Pattern:
    """Compile a token to a word-boundary regex.

    Boundaries are ``[a-z0-9]`` so ``-``, ``_`` and spaces all act as
    delimiters: ``search`` never matches inside ``research``, but ``tf-idf``
    matches the hyphenated keyword ``tf-idf``.
    """
    return re.compile(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])")


# --------------------------------------------------------------------------- #
# Core audit logic
# --------------------------------------------------------------------------- #

def _module_tokens(stem: str) -> list[str]:
    tokens = {stem, stem.replace("_", "-"), stem.replace("_", " ")}
    tokens.update(EXTRA_ALIASES.get(stem, []))
    tokens.discard("")
    return sorted(tokens)


def audit(modules_dir=None, articles_dir=None) -> dict:
    """Run the module-by-module documentation coverage audit.

    Returns a dict with ``modules`` (per-module findings), ``counts`` and
    ``stale_numbers``. See module docstring for the classification rules.
    """
    pkg = Path(__file__).resolve().parent
    root = pkg.parent
    modules_dir = Path(modules_dir) if modules_dir else pkg
    articles_dir = (Path(articles_dir) if articles_dir
                    else root / "knowledge" / "bundles" / "general")

    # --- 1. Enumerate package modules ------------------------------------ #
    module_stems = sorted(
        p.name[:-3]
        for p in modules_dir.glob("*.py")
        if p.name[:-3] not in EXCLUDE_MODULES
    )

    # --- 2. Load + index every KB article -------------------------------- #
    articles = []  # (filename, type, slug, search_text)
    for path in sorted(articles_dir.glob("*")):
        if path.suffix not in (".md", ".yaml", ".yml"):
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        fm = _extract_frontmatter(raw, path.suffix)
        articles.append((
            path.name,
            _field(fm, "type").lower(),
            _field(fm, "slug"),
            _article_search_text(fm),
        ))

    # --- 3. Match each module to articles -------------------------------- #
    findings = {}
    for stem in module_stems:
        patterns = [_token_pattern(t) for t in _module_tokens(stem)]
        matches = []  # (article_type, slug)
        for _name, atype, aslug, text in articles:
            if any(p.search(text) for p in patterns):
                matches.append((atype or "unknown", aslug or _name))
        findings[stem] = _classify(stem, matches)

    # --- 4. Flag stale hardcoded numbers in help articles ---------------- #
    stale = _scan_stale_numbers(articles_dir)

    counts = {"documented": 0, "partial": 0, "undocumented": 0}
    for f in findings.values():
        counts[f["class"].lower()] += 1
    counts["total"] = len(findings)

    return {
        "modules": findings,
        "counts": counts,
        "stale_numbers": stale,
        "articles_scanned": len(articles),
        "modules_dir": str(modules_dir),
        "articles_dir": str(articles_dir),
    }


def _classify(stem: str, matches: list[tuple[str, str]]) -> dict:
    help_slugs = sorted({s for t, s in matches if t in HELP_TYPES})
    other_slugs = sorted({s for t, s in matches if t not in HELP_TYPES})
    if help_slugs:
        cls = "DOCUMENTED"
    elif matches:
        cls = "PARTIAL"
    else:
        cls = "UNDOCUMENTED"
    return {
        "module": stem,
        "class": cls,
        "help_slugs": help_slugs,
        "partial_slugs": other_slugs,
        "total_matches": len(matches),
    }


def _scan_stale_numbers(articles_dir: Path) -> list[dict]:
    """Find hardcoded counts in help articles (reported, not fixed)."""
    flagged = []
    for path in sorted(articles_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        fm = _extract_frontmatter(raw, ".md")
        if _field(fm, "type").lower() != "help":
            continue
        slug = _field(fm, "slug") or path.name
        for i, line in enumerate(raw.splitlines(), 1):
            for pat in _STALE_PATTERNS:
                for m in pat.finditer(line):
                    flagged.append({
                        "slug": slug,
                        "line": i,
                        "text": line.strip(),
                        "match": m.group(0),
                    })
    return flagged


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def render_report(result: dict, json_out: bool = False) -> str:
    if json_out:
        return json.dumps(result, indent=2, default=str)

    lines = []
    lines.append("AI-KOS documentation coverage audit")
    lines.append("=" * 60)

    # Table
    header = f"{'MODULE':<22} {'COVERAGE':<13} MATCHING ARTICLES"
    lines.append(header)
    lines.append("-" * len(header))
    for mod in sorted(result["modules"]):
        f = result["modules"][mod]
        cls = f["class"]
        # Show the primary evidence: help slugs for DOCUMENTED modules,
        # partial slugs otherwise. Anything else is summarised as "+N more".
        if cls == "DOCUMENTED":
            shown = f["help_slugs"]
            extra = len(f["partial_slugs"])
        else:
            shown = f["partial_slugs"]
            extra = 0
        slug_text = ", ".join(shown) if shown else "—"
        if extra:
            slug_text += f"  (+{extra} mention{'' if extra == 1 else 's'})"
        lines.append(f"{f['module']:<22} {cls:<13} {slug_text}")

    # Summary
    c = result["counts"]
    lines.append("")
    lines.append("Summary")
    lines.append("-" * 60)
    lines.append(f"  modules scanned : {c['total']}")
    lines.append(f"  articles scanned: {result['articles_scanned']}")
    lines.append(f"  DOCUMENTED      : {c['documented']}")
    lines.append(f"  PARTIAL         : {c['partial']}")
    lines.append(f"  UNDOCUMENTED    : {c['undocumented']}")

    # Stale numbers
    lines.append("")
    lines.append("Stale hardcoded numbers (flag only — review manually)")
    lines.append("-" * 60)
    if result["stale_numbers"]:
        for s in result["stale_numbers"]:
            lines.append(f"  {s['slug']}:{s['line']}  [{s['match']}]  {s['text']}")
    else:
        lines.append("  (none found)")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="ai_kos.docaudit",
        description="Audit documentation coverage of ai_kos modules.")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    p.add_argument("--modules-dir", help="Directory containing ai_kos modules")
    p.add_argument("--articles-dir", help="Directory containing KB articles")
    args = p.parse_args(argv)

    result = audit(modules_dir=args.modules_dir, articles_dir=args.articles_dir)
    print(render_report(result, json_out=args.json))
    return 0


if __name__ == "__main__":
    sys.exit(main())
