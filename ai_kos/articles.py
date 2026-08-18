"""AI-KOS article store — CRUD for knowledge articles + auto-linking on write.

Uses an in-memory index of slug→filepath + frontmatter cache for O(1) lookups.
The index is built once on first access and incrementally updated on writes.

v1.7: typed relations, usage signals, version history, review cadence, access filtering.
"""

import os, time, uuid, logging, yaml
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Optional, List, Dict

from ai_kos.schemas import (
    ArticleType, ARTICLE_CLASSES, TEMPLATES, article_to_markdown,
    DEFAULT_REVIEW_INTERVALS, VersionEntry,
)
from ai_kos.config import get
from ai_kos import db as _db

logger = logging.getLogger("ai-kos.articles")
KNOWLEDGE_DIR = get("paths", "knowledge_dir", default="knowledge")


# ── In-Memory Article Index ──────────────────────────────────────────────────

class _ArticleIndex:
    """Cached slug→filepath + frontmatter index. Built once, updated incrementally."""

    def __init__(self):
        self._paths: Dict[str, str] = {}
        self._frontmatter: Dict[str, dict] = {}
        self._built = False
        self._built_at = 0.0

    @property
    def slugs(self) -> List[str]:
        self._ensure_built()
        return list(self._paths)

    def filepath(self, slug: str) -> Optional[str]:
        self._ensure_built()
        return self._paths.get(slug)

    def frontmatter(self, slug: str) -> Optional[dict]:
        self._ensure_built()
        return self._frontmatter.get(slug)

    def list_all(self) -> List[dict]:
        """Return lightweight article summaries (no body content)."""
        self._ensure_built()
        results = []
        for slug, fm in self._frontmatter.items():
            results.append({
                "slug": slug,
                "title": fm.get("title", slug),
                "type": fm.get("type", ""),
                "keywords": fm.get("keywords", []),
                "subject_keywords": fm.get("subject_keywords", []),
                "summary": fm.get("summary", ""),
                "related": fm.get("related", []),
                "filepath": self._paths[slug],
                "doc_type": fm.get("doc_type"),
                "lifecycle": fm.get("lifecycle", "current"),
                "sensitivity_label": fm.get("sensitivity_label", "internal"),
                "link_count": fm.get("link_count", 0),
                "superseded_by": fm.get("superseded_by"),
                "updated_at": str(fm.get("updated_at", "")),
                "created_at": str(fm.get("created_at", "")),
                "retrieval_count": fm.get("retrieval_count", 0),
                "next_review_at": str(fm.get("next_review_at", "")),
                "doi": fm.get("doi"),
                "backend": fm.get("backend", "md"),
                "dataset": fm.get("dataset"),
                "blob": fm.get("blob"),
                "graph": fm.get("graph"),
            })
        return sorted(results, key=lambda r: r["title"])

    def stats(self) -> dict:
        """Compute stats from cached frontmatter. v1.7: link_count-based orphans + reading_status breakdown."""
        self._ensure_built()
        by_type: Dict[str, int] = {}
        by_stability: Dict[str, int] = {}
        by_reading_status: Dict[str, int] = {"unread": 0, "skimmed": 0, "annotated": 0, "synthesized": 0}
        buckets = {"0.0-0.3": 0, "0.3-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
        past_review, gaps = [], []
        total_kw, total_links = 0, 0

        for slug, fm in self._frontmatter.items():
            t = fm.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            s = fm.get("stability", "moderate")
            by_stability[s] = by_stability.get(s, 0) + 1
            c = fm.get("confidence", 0.5)
            if c < 0.3:       buckets["0.0-0.3"] += 1
            elif c < 0.6:     buckets["0.3-0.6"] += 1
            elif c < 0.8:     buckets["0.6-0.8"] += 1
            else:             buckets["0.8-1.0"] += 1
            try:
                nr = date.fromisoformat(str(fm.get("next_review_at", "2099-01-01")))
                if nr < date.today():
                    past_review.append(slug)
            except Exception:
                pass
            if fm.get("gap"):
                gaps.append(slug)
            total_kw += len(fm.get("keywords", []))
            total_links += len(fm.get("related", []))
            rs = fm.get("reading_status", "unread")
            if rs in by_reading_status:
                by_reading_status[rs] += 1

        # v1.7: orphans = articles with link_count==0 (no inbound links), not empty related
        orphans = [slug for slug, fm in self._frontmatter.items()
                   if fm.get("link_count", len(fm.get("related", []))) == 0]
        n = max(1, len(self._frontmatter))
        return {
            "total_articles": len(self._frontmatter),
            "by_type": by_type,
            "by_stability": by_stability,
            "confidence_distribution": buckets,
            "articles_past_review": past_review,
            "gap_articles": gaps,
            "orphans": orphans,
            "reading_status": by_reading_status,
            "total_keywords": total_kw,
            "total_links": total_links,
            "avg_keywords": round(total_kw / n, 1),
            "avg_links": round(total_links / n, 1),
        }

    def upsert(self, slug: str, filepath: str, frontmatter: dict) -> None:
        self._paths[slug] = filepath
        self._frontmatter[slug] = frontmatter

    def remove(self, slug: str) -> None:
        self._paths.pop(slug, None)
        self._frontmatter.pop(slug, None)

    def invalidate(self) -> None:
        self._built = False

    def _ensure_built(self) -> None:
        if self._built:
            # Staleness check: rebuild if any source file changed since the
            # index was built (audit 2026-08-15 — the MCP daemon cached 337
            # articles while disk held 382; writers from other processes
            # must become visible on the next read).
            try:
                newest = max(
                    (p.stat().st_mtime for p in Path(KNOWLEDGE_DIR).rglob("*.md")),
                    default=0.0,
                )
                newest = max(
                    newest,
                    max(
                        (p.stat().st_mtime for p in Path(KNOWLEDGE_DIR).rglob("*.yaml")),
                        default=0.0,
                    ),
                )
                if newest <= self._built_at:
                    return
            except OSError:
                return
        self._paths.clear()
        self._frontmatter.clear()
        # Scan .md files (markdown articles)
        for md in Path(KNOWLEDGE_DIR).rglob("*.md"):
            try:
                with open(md) as f:
                    content = f.read()
                if not content.startswith("---"):
                    continue
                fm = yaml.safe_load(content.split("---")[1]) or {}
                slug = fm.get("slug", md.stem)
                self._paths[slug] = str(md)
                self._frontmatter[slug] = fm
            except Exception:
                continue
        # Scan .yaml files (SQL-backed dataset articles)
        for yf in Path(KNOWLEDGE_DIR).rglob("*.yaml"):
            try:
                with open(yf) as f:
                    fm = yaml.safe_load(f) or {}
                slug = fm.get("slug", yf.stem)
                self._paths[slug] = str(yf)
                self._frontmatter[slug] = fm
            except Exception:
                continue
        self._built = True
        self._built_at = time.time()
        logger.debug(f"ArticleIndex built: {len(self._paths)} articles")


_index = _ArticleIndex()


def _get_index() -> _ArticleIndex:
    return _index


def _refresh_index() -> None:
    _index.invalidate()


# ── Path Resolution ──────────────────────────────────────────────────────────

def _slug_path(slug: str) -> str:
    idx = _get_index()
    path = idx.filepath(slug)
    if path:
        return path
    # Default: .md for markdown articles
    md_path = Path(KNOWLEDGE_DIR) / "bundles" / "general" / f"{slug}.md"
    if md_path.exists():
        return str(md_path)
    # Default: .md for new articles. For reads, also check .yaml
    # for pre-existing SQL/blob/json/graph stubs (frontmatter-only).
    yaml_path = Path(KNOWLEDGE_DIR) / "bundles" / "general" / f"{slug}.yaml"
    return str(yaml_path) if yaml_path.exists() else str(md_path.parent / f"{slug}.md")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_review_interval(article_type: str) -> int:
    """Get review_interval_days for a type, falling back to defaults."""
    try:
        at = ArticleType(article_type)
        return DEFAULT_REVIEW_INTERVALS.get(at, 365)
    except Exception:
        return 365


def _warn_keyword_counts(article) -> None:
    """Advisory tier-count warnings for create_article (§2.8) — mirrors the schema's
    loose enforcement: warn on out-of-bounds counts, never fail.

    `subject_keywords` is optional, so an absent (empty) list does not warn; a
    present-but-out-of-bounds list does.

    Audit fix 2026-08-18: the `target_keywords` / `target_subject_keywords`
    config keys were dead (read nowhere) — they now drive a below-target
    advisory so authors learn the ideal count even when within the hard bounds.
    """
    n_kw = len(article.keywords)
    min_kw = get("article", "min_keywords", default=3)
    max_kw = get("article", "max_keywords", default=15)
    if n_kw < min_kw or n_kw > max_kw:
        logger.warning(
            f"Article {article.slug}: {n_kw} keywords outside advisory bounds [{min_kw}, {max_kw}]"
        )
    target_kw = get("article", "target_keywords", default=10)
    if n_kw < target_kw:
        logger.warning(
            f"Article {article.slug}: {n_kw} keywords below target {target_kw} (advisory)"
        )
    n_sk = len(article.subject_keywords)
    min_sk = get("article", "min_subject_keywords", default=2)
    max_sk = get("article", "max_subject_keywords", default=8)
    if n_sk and (n_sk < min_sk or n_sk > max_sk):
        logger.warning(
            f"Article {article.slug}: {n_sk} subject_keywords outside advisory bounds [{min_sk}, {max_sk}]"
        )
    target_sk = get("article", "target_subject_keywords", default=5)
    if n_sk and n_sk < target_sk:
        logger.warning(
            f"Article {article.slug}: {n_sk} subject_keywords below target {target_sk} (advisory)"
        )


def _compute_next_review(today: date, interval_days: Optional[int], article_type: str) -> date:
    """Compute next_review_at from today + review_interval_days."""
    interval = interval_days if interval_days else _get_review_interval(article_type)
    return today.replace(year=today.year + (interval // 365), month=today.month, day=today.day) \
        if interval >= 365 else date.fromordinal(today.toordinal() + interval)


def _make_history_entry(version: int, note: str = "created") -> VersionEntry:
    """Create a compact version history entry."""
    return VersionEntry(
        v=version,
        at=datetime.now(timezone.utc),
        by="agent:kruzzzy",
        note=note,
    )


def _extract_body_for_db(article) -> str:
    """Extract human-readable body content from a Pydantic article for SQLite storage."""
    atype = article.type
    if atype == ArticleType.BASE or atype == ArticleType.NOTE:
        return getattr(article, 'content', '')
    elif atype == ArticleType.HELP:
        return getattr(article, 'explanation', '')
    elif atype == ArticleType.MISSION:
        return getattr(article, 'architecture', '')
    else:
        # PROCESS, PLAN, RESEARCH_NOTE — serialize via formatter
        return article_to_markdown(article).split('---', 2)[-1].strip()


def _inject_sql_placeholders(article_type: str, data: dict) -> None:
    """Set required body fields to empty placeholders for SQL-backed articles."""
    if article_type in ("base", "note"):
        data.setdefault("content", "[SQL-backed dataset — see table data]")
    elif article_type == "help":
        data.setdefault("explanation", "[SQL-backed dataset — see table data]")
        data.setdefault("project", "datasets")
        data.setdefault("component", data.get("dataset", {}).get("table", ""))
    elif article_type == "mission":
        data.setdefault("architecture", "[SQL-backed dataset — see table data]")
        data.setdefault("purpose", data.get("summary", ""))
        data.setdefault("project", "datasets")
    elif article_type == "process":
        data.setdefault("steps", ["[SQL-backed dataset — see table data]"])
        data.setdefault("outcome", data.get("summary", ""))
    elif article_type == "plan":
        data.setdefault("goal", data.get("summary", ""))
    elif article_type == "research-note":
        data.setdefault("topic", data.get("summary", ""))
        data.setdefault("key_notes", ["[SQL-backed dataset — see table data]"])


# ── CRUD Operations ──────────────────────────────────────────────────────────

def create_article(article_type: str, data: dict, overwrite: bool = False) -> dict:
    cls = ARTICLE_CLASSES.get(ArticleType(article_type))
    if not cls:
        return {"error": f"Unknown article type: {article_type}"}

    # Audit fix 2026-08-18: slug-collision guard. A duplicate slug used to
    # silently truncate the existing article (open(..., 'w')), and could even
    # write markdown INTO an existing .yaml backend stub. Refuse unless the
    # caller explicitly passes overwrite=True.
    if not overwrite:
        slug = data.get("slug")
        if slug:
            existing = _slug_path(slug)
            if existing and os.path.exists(existing):
                return {"error": f"article already exists: {slug}"}

    if 'id' not in data:
        data['id'] = str(uuid.uuid4())
    today = date.today()
    for k in ['created_at', 'updated_at', 'reviewed_at']:
        data.setdefault(k, today)

    # v1.7: review cadence
    interval = data.get('review_interval_days')
    data.setdefault('next_review_at', _compute_next_review(today, interval, article_type))

    # v1.7: version + history
    ver = data.get('version', 1)
    if 'history' not in data or not data['history']:
        data['history'] = [_make_history_entry(ver, "created")]

    # v1.7: coerce provenance to list of dicts
    if 'provenance' in data:
        prov = data['provenance']
        if isinstance(prov, list):
            data['provenance'] = [
                {"source": "manual", "origin_ref": p} if isinstance(p, str) else p
                for p in prov
            ]

    # v1.7: coerce related to list of {slug, type} dicts
    if 'related' in data:
        data['related'] = [
            {"slug": r, "type": "see-also"} if isinstance(r, str) else r
            for r in data['related']
        ]

    # SQL-backed articles don't need markdown body — inject placeholders
    if data.get("backend") in ("sql", "json", "blob", "graph"):
        _inject_sql_placeholders(article_type, data)

    # Audit fix 2026-08-18: summary_max_chars is the effective summary bound
    # (configurable; the schema's pydantic max_length=300 is the hard ceiling).
    summary_max = get("article", "summary_max_chars", default=300)
    summary_text = data.get("summary")
    if isinstance(summary_text, str) and len(summary_text) > summary_max:
        return {"error": f"Summary too long: {len(summary_text)} chars exceeds summary_max_chars={summary_max}"}

    try:
        article = cls(**data)
    except Exception as e:
        return {"error": f"Validation failed: {e}"}

    # Advisory keyword-count warnings (never hard-fail) — v2 tier bounds, §1.8
    _warn_keyword_counts(article)

    # Audit fix 2026-08-18: max_paragraphs (dead config key) now drives the
    # base/note paragraph guidance — advisory only, never a hard fail (§2.8).
    max_par = get("article", "max_paragraphs", default=5)
    if article.type in (ArticleType.BASE, ArticleType.NOTE):
        body_text = getattr(article, "content", "") or ""
        n_par = len([p for p in str(body_text).split("\n\n") if p.strip()])
        if n_par > max_par:
            logger.warning(
                f"Article {article.slug}: {n_par} paragraphs exceeds max_paragraphs={max_par} (advisory)"
            )

    backend = data.get("backend", "md")

    if backend == "sql":
        return _create_sql_article(article, article_type)
    elif backend in ("blob", "json", "graph"):
        return _create_yaml_only_article(article, article_type, backend)
    else:
        return _create_md_article(article, article_type)


def _create_md_article(article, article_type: str) -> dict:
    """Create a standard markdown-backed article."""
    md_content = article_to_markdown(article)

    # Also store body in SQLite as an additional backend
    _db.set_body(article.slug, _extract_body_for_db(article))
    filepath = _slug_path(article.slug)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(md_content)

    # Update in-memory index
    try:
        fm = yaml.safe_load(md_content.split("---")[1]) or {}
    except Exception:
        fm = {}
    _get_index().upsert(article.slug, filepath, fm)

    logger.info(f"Created {article_type}: {article.slug}")
    from ai_kos.linker import link_all
    link_result = link_all(KNOWLEDGE_DIR)
    return {
        "status": "created", "slug": article.slug, "type": article_type,
        "filepath": filepath, "keywords": article.keywords, "linking": link_result,
    }


def _create_sql_article(article, article_type: str) -> dict:
    """Create a SQL-backed dataset article with .yaml stub + SQL table."""
    from ai_kos import datasets

    dataset = article.dataset
    if not dataset:
        return {"error": "dataset is required when backend=sql"}

    # Create the SQL table
    col_dicts = [{"name": c.name, "type": c.type} for c in dataset.columns]
    datasets.create_table(dataset.db, dataset.table, col_dicts)

    # Write a .yaml stub (frontmatter only, no markdown body)
    filepath = _slug_path(article.slug)
    if filepath.endswith('.md'):
        filepath = filepath[:-3] + '.yaml'
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    yaml_content = _article_to_yaml_stub(article)
    with open(filepath, 'w') as f:
        f.write(yaml_content)

    # Update in-memory index
    try:
        fm = yaml.safe_load(yaml_content) or {}
    except Exception:
        fm = {}
    _get_index().upsert(article.slug, filepath, fm)

    logger.info(f"Created SQL-backed {article_type}: {article.slug} → {dataset.db}/{dataset.table}")
    from ai_kos.linker import link_all
    link_result = link_all(KNOWLEDGE_DIR)
    return {
        "status": "created", "slug": article.slug, "type": article_type,
        "filepath": filepath, "backend": "sql",
        "database": dataset.db, "table": dataset.table,
        "keywords": article.keywords, "linking": link_result,
    }


def _create_yaml_only_article(article, article_type: str, backend_label: str) -> dict:
    """Create an article with a .yaml stub only (no markdown, no SQL table).

    Used by blob, json, and graph backends where data is stored externally.
    """
    filepath = _slug_path(article.slug)
    if filepath.endswith('.md'):
        filepath = filepath[:-3] + '.yaml'
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    yaml_content = _article_to_yaml_stub(article)
    with open(filepath, 'w') as f:
        f.write(yaml_content)

    try:
        fm = yaml.safe_load(yaml_content) or {}
    except Exception:
        fm = {}
    _get_index().upsert(article.slug, filepath, fm)

    logger.info(f"Created {backend_label}-backed {article_type}: {article.slug}")
    from ai_kos.linker import link_all
    link_result = link_all(KNOWLEDGE_DIR)
    return {
        "status": "created", "slug": article.slug, "type": article_type,
        "filepath": filepath, "backend": backend_label,
        "keywords": article.keywords, "linking": link_result,
    }


def _article_to_yaml_stub(article) -> str:
    """Serialize frontmatter as a clean YAML file (for SQL-backed articles)."""
    data = article.model_dump(mode='json')
    fm = {k: v for k, v in data.items() if v is not None}

    from ai_kos.schemas import _serialize_provenance, _serialize_related
    if 'provenance' in fm:
        fm['provenance'] = _serialize_provenance(fm['provenance'])
    if 'related' in fm:
        fm['related'] = _serialize_related(fm['related'])
    if 'history' in fm and isinstance(fm.get('history'), list):
        fm['history'] = [
            h.model_dump(mode='json') if hasattr(h, 'model_dump') else h
            for h in fm['history']
        ]
    if 'dataset' in fm and isinstance(fm['dataset'], dict):
        # Serialize DatasetRef columns
        if 'columns' in fm['dataset']:
            fm['dataset']['columns'] = [
                c.model_dump(mode='json') if hasattr(c, 'model_dump') else c
                for c in fm['dataset']['columns']
            ]

    # Remove markdown body fields (not relevant for SQL articles)
    body_fields = set(TEMPLATES[article.type]["human_fields"])
    for k in list(fm.keys()):
        if k in body_fields:
            del fm[k]

    # Add tags
    fm['tags'] = [f'type/{article.type.value}', 'backend/sql']
    if fm.get('doc_type'):
        fm['tags'].append(f'doc/{fm["doc_type"]}')

    return yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()


def read_article(slug: str) -> dict | None:
    filepath = _slug_path(slug)
    try:
        with open(filepath) as f:
            content = f.read()
    except FileNotFoundError:
        return None

    # .yaml files: SQL-backed articles — frontmatter only, no body
    if filepath.endswith('.yaml'):
        fm = yaml.safe_load(content) or {}
        body = ""
    elif not content.startswith('---'):
        return {"slug": slug, "error": "No frontmatter"}
    else:
        parts = content.split('---', 2)
        fm = yaml.safe_load(parts[1]) or {}
        body = parts[2] if len(parts) > 2 else ""

    # v1.7: bump usage signals
    fm['retrieval_count'] = fm.get('retrieval_count', 0) + 1
    fm['last_accessed'] = date.today().isoformat()

    # Write back updated frontmatter ONLY — never rewrite the body.
    # (Audit fix 2026-08-18: the old path re.sub'd everything below
    # `## Related` out of the body on every read, permanently destroying
    # any manual content placed after that heading. The body must
    # round-trip byte-identical; only the two usage counters may change.)
    new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    if filepath.endswith('.yaml'):
        new_content = new_fm
    else:
        new_content = f"---\n{new_fm}\n---{body}"
    with open(filepath, 'w') as f:
        f.write(new_content)

    _get_index().upsert(slug, filepath, fm)

    # SQL-backed articles: return table preview instead of markdown body
    if fm.get("backend") == "sql" and fm.get("dataset"):
        from ai_kos import datasets
        ds = fm["dataset"]
        table_data = datasets.query_table(
            ds["db"], f'SELECT * FROM "{ds["table"]}" LIMIT 50'
        )
        stats = datasets.table_stats(ds["db"], ds["table"])
        return {
            "slug": slug, "filepath": filepath, "frontmatter": fm,
            "backend": "sql", "dataset": ds,
            "row_count": stats["row_count"] if stats else 0,
            "columns": stats["columns"] if stats else [],
            "preview": table_data,
            "raw": content,
        }

    # Blob-backed articles: return file metadata + extracted text
    if fm.get("backend") == "blob" and fm.get("blob"):
        blob = fm["blob"]
        return {
            "slug": slug, "filepath": filepath, "frontmatter": fm,
            "backend": "blob", "blob": blob,
            "file_exists": os.path.exists(blob.get("path", "")),
            "body": blob.get("extracted_text", ""),
            "raw": content,
        }

    # JSON-backed articles: return full document + stats
    if fm.get("backend") == "json" and fm.get("dataset"):
        from ai_kos import datasets
        ds = fm["dataset"]
        doc = datasets.get_json_doc(ds["db"], ds["table"], slug)
        stats = datasets.json_stats(ds["db"], ds["table"], slug)
        return {
            "slug": slug, "filepath": filepath, "frontmatter": fm,
            "backend": "json", "dataset": ds,
            "data": doc, "stats": stats,
            "raw": content,
        }

    # Graph-backed articles: return stats + sample nodes
    if fm.get("backend") == "graph" and fm.get("graph"):
        from ai_kos import graphs
        ds = fm.get("dataset", {})
        g = fm["graph"]
        gstats = graphs.graph_stats(ds["db"], ds["table"])
        return {
            "slug": slug, "filepath": filepath, "frontmatter": fm,
            "backend": "graph", "graph": g,
            "stats": gstats,
            "raw": content,
        }

    return {"slug": slug, "filepath": filepath, "frontmatter": fm, "body": body.strip(), "raw": content}


def update_article(slug: str, updates: dict) -> dict:
    """Update an article's frontmatter. v1.7: auto-increment version, recompute review.

    Audit fix 2026-08-18: .yaml backend stubs are whole-dict files — the old
    `content.split('---', 2)` raised IndexError on them. Load the whole dict as
    frontmatter with an empty body (mirrors migrate._load_fm) and write the
    whole dict back, exactly like read_article already does.
    """
    filepath = _slug_path(slug)
    try:
        with open(filepath) as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"Article not found: {slug}"}

    is_yaml = filepath.endswith('.yaml')
    if is_yaml:
        fm = yaml.safe_load(content) or {}
        body = ""
    elif not content.startswith('---'):
        return {"error": f"No frontmatter in {filepath}"}
    else:
        parts = content.split('---', 2)
        fm = yaml.safe_load(parts[1]) or {}
        body = parts[2] if len(parts) > 2 else ""
    fm.update(updates)
    today = date.today()
    fm['updated_at'] = today.isoformat()

    # v1.7: auto-increment version + append history
    prev_version = fm.get('version', 1)
    new_version = prev_version + 1
    fm['version'] = new_version
    history = fm.get('history', [])
    history.append(_make_history_entry(new_version, "updated").model_dump(mode='json'))
    fm['history'] = history

    # v1.7: recompute next_review_at from review_interval_days
    interval = fm.get('review_interval_days')
    article_type = fm.get('type', 'base')
    fm['next_review_at'] = _compute_next_review(today, interval, article_type).isoformat()

    new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    if is_yaml:
        new_content = new_fm
    else:
        new_content = f"---\n{new_fm}\n---{body}"
    with open(filepath, 'w') as f:
        f.write(new_content)

    _get_index().upsert(slug, filepath, fm)

    from ai_kos.linker import link_all
    link_result = link_all(KNOWLEDGE_DIR)
    return {"status": "updated", "slug": slug, "linking": link_result}


def delete_article(slug: str) -> dict:
    import shutil
    filepath = _slug_path(slug)
    if not os.path.exists(filepath):
        # Audit fix 2026-08-18: a cold/stale index (or a .yaml stub outside
        # bundles/general) used to make deletion report "not found" even though
        # the article existed on disk. Fall back to a direct filesystem search
        # (prefer .md, then .yaml — mirrors _slug_path's precedence).
        for ext in (".md", ".yaml"):
            hits = [str(p) for p in Path(KNOWLEDGE_DIR).rglob(f"{slug}{ext}")]
            if hits:
                filepath = hits[0]
                break
    if not os.path.exists(filepath):
        return {"error": f"Article not found: {slug}"}

    # Check if SQL-backed and drop the table. Audit fix 2026-08-18: read the
    # frontmatter extension-aware (whole-dict for .yaml) instead of relying
    # solely on the index, which may be stale/not built — backend cleanup must
    # still run (and must never crash) on a .yaml stub.
    fm = _get_index().frontmatter(slug) or {}
    if not fm:
        try:
            with open(filepath) as f:
                content = f.read()
            if filepath.endswith('.yaml'):
                fm = yaml.safe_load(content) or {}
            elif content.startswith('---'):
                parts = content.split('---', 2)
                fm = yaml.safe_load(parts[1]) or {}
        except Exception:
            fm = {}
    if fm.get("backend") == "sql" and fm.get("dataset"):
        from ai_kos import datasets
        ds = fm["dataset"]
        datasets.drop_table(ds["db"], ds["table"])
    elif fm.get("backend") == "blob" and fm.get("blob"):
        from ai_kos.blobs import delete_blob
        delete_blob(fm["blob"]["path"])
    elif fm.get("backend") == "json" and fm.get("dataset"):
        import sqlite3
        ds = fm["dataset"]
        conn = sqlite3.connect(ds["db"])
        conn.execute(f'DELETE FROM "{ds["table"]}" WHERE slug = ?', (slug,))
        conn.commit()
        conn.close()
    elif fm.get("backend") == "graph" and fm.get("dataset"):
        from ai_kos.graphs import drop_graph
        drop_graph(fm["dataset"]["db"], fm["dataset"]["table"])

    archive_dir = Path(get("paths", "archive_dir", default="archive"))
    archive_dir.mkdir(exist_ok=True)
    dest = archive_dir / Path(filepath).name
    shutil.move(filepath, str(dest))

    _get_index().remove(slug)
    _db.delete_body(slug)

    logger.info(f"Deleted {slug} → {dest}")
    from ai_kos.linker import link_all
    link_all(KNOWLEDGE_DIR)
    return {"status": "deleted", "slug": slug, "moved_to": str(dest)}


def list_articles(
    article_type: Optional[str] = None,
    keyword: Optional[str] = None,
    access: Optional[str] = None,
    doc_type: Optional[str] = None,
    lifecycle: Optional[str] = None,
) -> List[dict]:
    """List all articles with optional v1.7 filters."""
    results = _get_index().list_all()
    if article_type:
        results = [r for r in results if r["type"] == article_type]
    if keyword:
        results = [r for r in results if keyword.lower() in [k.lower() for k in r.get("keywords", [])]]
    if access:
        # Filter: only return articles at or below the requested access level
        levels = {"public": 0, "internal": 1, "confidential": 2}
        req_level = levels.get(access, 1)
        results = [r for r in results if levels.get(r.get("sensitivity_label", "internal"), 1) <= req_level]
    if doc_type:
        results = [r for r in results if r.get("doc_type") == doc_type]
    if lifecycle:
        results = [r for r in results if r.get("lifecycle") == lifecycle]
    return results


def find_merge_candidates(slug: str) -> List[dict]:
    fm = _get_index().frontmatter(slug)
    if not fm:
        return []
    target_kw = set(fm.get("keywords", []))
    if not target_kw:
        return []
    candidates = []
    for other_slug, other_fm in _get_index()._frontmatter.items():
        if other_slug == slug:
            continue
        other_kw = set(other_fm.get("keywords", []))
        if not other_kw:
            continue
        overlap = target_kw & other_kw
        ratio = len(overlap) / min(len(target_kw), len(other_kw))
        if ratio > 0.5:
            candidates.append({
                "slug": other_slug,
                "title": other_fm.get("title", ""),
                "shared_keywords": sorted(overlap),
                "overlap_ratio": round(ratio, 2),
            })
    return sorted(candidates, key=lambda c: c["overlap_ratio"], reverse=True)


def stats() -> dict:
    return _get_index().stats()
