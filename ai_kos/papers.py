"""AI-KOS paper full-text storage — preserves extracted PDF text for search.

Pattern: stores the complete extracted text from academic papers in a
`papers` table in datasets/ai-kos.db, keyed by article slug. This fills
the gap where research-note summaries (~400 words) lose 95% of the
original paper content.

Usage:
    from ai_kos.papers import store_paper_text, search_papers, paper_stats
    store_paper_text(slug="adams-2017", title="Persistence Images", text="...")
    results = search_papers("persistence images stability")
    stats = paper_stats()
"""

import sqlite3
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ai-kos.papers")


def _get_conn() -> sqlite3.Connection:
    """Get database connection, ensuring papers table exists."""
    from ai_kos.db import get_conn as db_conn
    conn = db_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            slug         TEXT PRIMARY KEY,
            title        TEXT NOT NULL,
            full_text    TEXT NOT NULL,
            char_count   INTEGER NOT NULL DEFAULT 0,
            pdf_path     TEXT,
            extracted_at TEXT NOT NULL,
            FOREIGN KEY (slug) REFERENCES bodies(slug) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_papers_char_count ON papers(char_count)
    """)
    return conn


# ── CRUD ────────────────────────────────────────────────────────────────────

def store_paper_text(
    slug: str,
    title: str,
    text: str,
    pdf_path: Optional[str] = None,
) -> dict:
    """Store full extracted paper text. Upserts — replaces if slug exists."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    text = text.strip()
    char_count = len(text)

    conn.execute("""
        INSERT OR REPLACE INTO papers (slug, title, full_text, char_count, pdf_path, extracted_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (slug, title, text, char_count, pdf_path, now))
    conn.commit()

    logger.info(f"Stored paper '{slug}': {char_count:,} chars")
    return {"slug": slug, "char_count": char_count, "stored": True}


def get_paper_text(slug: str) -> Optional[dict]:
    """Retrieve full paper text by article slug."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT slug, title, full_text, char_count, pdf_path, extracted_at FROM papers WHERE slug = ?",
        (slug,)
    ).fetchone()
    if not row:
        return None
    return {
        "slug": row["slug"],
        "title": row["title"],
        "full_text": row["full_text"],
        "char_count": row["char_count"],
        "pdf_path": row["pdf_path"],
        "extracted_at": row["extracted_at"],
    }


def search_papers(query: str, top_k: int = 10) -> list[dict]:
    """Full-text search across all stored paper bodies.
    
    Uses SQLite LIKE for substring matching. For production use, consider
    adding an FTS5 virtual table, but LIKE is sufficient for <100 papers.
    """
    conn = _get_conn()
    # Split query into words for AND-style matching
    terms = [t.strip() for t in re.split(r'[\s,;:]+', query) if len(t.strip()) >= 2]
    if not terms:
        return []

    # Build LIKE conditions — all terms must appear somewhere in the text
    conditions = " AND ".join([f"full_text LIKE '%' || ? || '%'" for t in terms])
    sql = f"""
        SELECT slug, title, char_count, pdf_path, extracted_at,
               substr(full_text, 1, 200) as snippet
        FROM papers
        WHERE {conditions}
        ORDER BY char_count DESC
        LIMIT ?
    """
    rows = conn.execute(sql, terms + [top_k]).fetchall()

    results = []
    for row in rows:
        snippet = row["snippet"] or ""
        # Try to find a better contextual snippet if possible
        # (snippet is already substr(full_text, 1, 200) from the query)
        results.append({
            "slug": row["slug"],
            "title": row["title"],
            "char_count": row["char_count"],
            "snippet": snippet[:300] if snippet else "",
            "pdf_path": row["pdf_path"],
        })
    return results


def paper_stats() -> dict:
    """Get statistics about stored papers."""
    conn = _get_conn()
    row = conn.execute("""
        SELECT COUNT(*) as total,
               COALESCE(SUM(char_count), 0) as total_chars,
               COALESCE(AVG(char_count), 0) as avg_chars,
               MAX(char_count) as max_chars,
               MIN(char_count) as min_chars
        FROM papers
    """).fetchone()
    return {
        "total_papers": row["total"],
        "total_chars": row["total_chars"],
        "avg_chars": int(row["avg_chars"]),
        "max_chars": row["max_chars"],
        "min_chars": row["min_chars"],
    }


def list_papers() -> list[dict]:
    """List all stored papers with metadata."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT slug, title, char_count, pdf_path, extracted_at FROM papers ORDER BY char_count DESC"
    ).fetchall()
    return [{
        "slug": r["slug"],
        "title": r["title"],
        "char_count": r["char_count"],
        "pdf_path": r["pdf_path"],
        "extracted_at": r["extracted_at"],
    } for r in rows]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_snippet(text: str, term: str, context: int = 150) -> str:
    """Extract a snippet around the first occurrence of term."""
    idx = text.lower().find(term.lower())
    if idx < 0:
        return text[:300]
    start = max(0, idx - context)
    end = min(len(text), idx + len(term) + context)
    snippet = text[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


# ── Backfill from PDFs ──────────────────────────────────────────────────────

def backfill_from_pdfs(pdf_dir: Optional[str] = None) -> dict:
    """Extract and store text from all PDFs in rejected/ that aren't already stored.
    
    Matches PDFs to existing research-note slugs by filename pattern.
    """
    from ai_kos.ingestion import extract as ingest_extract
    from ai_kos.articles import list_articles

    if pdf_dir is None:
        from ai_kos.config import get
        pdf_dir = get("paths", "rejected_dir", default="rejected")

    pdf_path = Path(str(pdf_dir))
    if not pdf_path.exists():
        return {"error": f"Directory not found: {pdf_dir}", "stored": 0}

    # Build slug→title lookup from existing research-notes
    articles = {a["slug"]: a["title"] for a in list_articles(article_type='research-note')}

    stored = 0
    skipped = 0
    errors = 0

    for pdf_file in sorted(pdf_path.glob("*.pdf")):
        # Check if already stored
        conn = _get_conn()
        exists = conn.execute("SELECT 1 FROM papers WHERE pdf_path = ?", (str(pdf_file),)).fetchone()
        if exists:
            skipped += 1
            continue

        # Extract text
        try:
            result = ingest_extract(str(pdf_file))
            text = result.get("raw_content", "")
            if len(text.strip()) < 500:
                errors += 1
                continue

            # Try to find matching slug from filename
            # Patterns: "01_Conti_2022_..." → look for slug containing "conti-2022"
            stem = pdf_file.stem
            slug = _guess_slug(stem, articles)
            title = articles.get(slug, pdf_file.stem)

            store_paper_text(
                slug=slug or stem.lower().replace("_", "-"),
                title=title,
                text=text,
                pdf_path=str(pdf_file),
            )
            stored += 1
        except Exception as e:
            logger.warning(f"Backfill failed for {pdf_file.name}: {e}")
            errors += 1

    return {"stored": stored, "skipped": skipped, "errors": errors}


def _guess_slug(filename_stem: str, articles: dict) -> Optional[str]:
    """Guess article slug from PDF filename pattern.
    
    "01_Conti_2022_TDA_Pipeline" → search for slug containing "conti-2022"
    "05_Ali_2023_Vectorization_Survey" → search for slug containing "ali-2023"
    """
    parts = filename_stem.split("_")
    for i, part in enumerate(parts):
        if part[0].isupper() and len(part) > 2 and i + 1 < len(parts):
            try:
                year = int(parts[i + 1])
                author = part.lower()
                for slug in articles:
                    if author in slug and str(year) in slug:
                        return slug
            except ValueError:
                pass
    return None


# ── Source document storage (archive consolidation) ─────────────────────────

def search_sources(query: str, top_k: int = 10) -> list[dict]:
    """Search across archived source documents (former archive/ .md files)."""
    conn = _get_conn()
    terms = [t.strip() for t in re.split(r'[\s,;:]+', query) if len(t.strip()) >= 2]
    if not terms:
        return []
    conditions = " AND ".join(["full_text LIKE '%' || ? || '%'" for _ in terms])
    sql = f"""
        SELECT filename, char_count, substr(full_text, 1, 300) as snippet
        FROM sources
        WHERE {conditions}
        ORDER BY char_count DESC LIMIT ?
    """
    rows = conn.execute(sql, terms + [top_k]).fetchall()
    return [{"filename": r["filename"], "char_count": r["char_count"],
             "snippet": r["snippet"][:300]} for r in rows]


def source_stats() -> dict:
    """Stats for archived source documents."""
    conn = _get_conn()
    r = conn.execute("SELECT COUNT(*), COALESCE(SUM(char_count),0), COALESCE(AVG(char_count),0) FROM sources").fetchone()
    return {"total": r[0], "total_chars": r[1], "avg_chars": int(r[2])}
