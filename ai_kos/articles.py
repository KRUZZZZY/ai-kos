"""AI-KOS article store — CRUD for knowledge articles + auto-linking on write.

Uses an in-memory index of slug→filepath + frontmatter cache for O(1) lookups.
The index is built once on first access and incrementally updated on writes.

v1.7: typed relations, usage signals, version history, review cadence, access filtering.
"""

import os, uuid, logging, yaml
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Optional, List, Dict

from ai_kos.schemas import (
    ArticleType, ARTICLE_CLASSES, TEMPLATES, article_to_markdown,
    DEFAULT_REVIEW_INTERVALS, VersionEntry,
)
from ai_kos.config import get

logger = logging.getLogger("ai-kos.articles")
KNOWLEDGE_DIR = get("paths", "knowledge_dir", default="knowledge")


# ── In-Memory Article Index ──────────────────────────────────────────────────

class _ArticleIndex:
    """Cached slug→filepath + frontmatter index. Built once, updated incrementally."""

    def __init__(self):
        self._paths: Dict[str, str] = {}
        self._frontmatter: Dict[str, dict] = {}
        self._built = False

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
                "summary": fm.get("summary", ""),
                "related": fm.get("related", []),
                "filepath": self._paths[slug],
                "doc_type": fm.get("doc_type"),
                "lifecycle": fm.get("lifecycle", "current"),
                "sensitivity_label": fm.get("sensitivity_label", "internal"),
                "link_count": fm.get("link_count", 0),
                "superseded_by": fm.get("superseded_by"),
            })
        return sorted(results, key=lambda r: r["title"])

    def stats(self) -> dict:
        """Compute stats from cached frontmatter. v1.7: link_count-based orphans."""
        self._ensure_built()
        by_type: Dict[str, int] = {}
        by_stability: Dict[str, int] = {}
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
            return
        self._paths.clear()
        self._frontmatter.clear()
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
        self._built = True
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
    return str(Path(KNOWLEDGE_DIR) / "bundles" / "general" / f"{slug}.md")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_review_interval(article_type: str) -> int:
    """Get review_interval_days for a type, falling back to defaults."""
    try:
        at = ArticleType(article_type)
        return DEFAULT_REVIEW_INTERVALS.get(at, 365)
    except Exception:
        return 365


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


# ── CRUD Operations ──────────────────────────────────────────────────────────

def create_article(article_type: str, data: dict) -> dict:
    cls = ARTICLE_CLASSES.get(ArticleType(article_type))
    if not cls:
        return {"error": f"Unknown article type: {article_type}"}
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

    try:
        article = cls(**data)
    except Exception as e:
        return {"error": f"Validation failed: {e}"}

    md_content = article_to_markdown(article)
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


def read_article(slug: str) -> dict | None:
    filepath = _slug_path(slug)
    try:
        with open(filepath) as f:
            content = f.read()
    except FileNotFoundError:
        return None
    if not content.startswith('---'):
        return {"slug": slug, "error": "No frontmatter"}
    parts = content.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2] if len(parts) > 2 else ""

    # v1.7: bump usage signals
    fm['retrieval_count'] = fm.get('retrieval_count', 0) + 1
    fm['last_accessed'] = date.today().isoformat()

    # Write back updated frontmatter
    import re
    new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    body_clean = re.sub(r'\n## Related\n.*', '', body, flags=re.DOTALL) if '## Related' in body else body
    new_content = f"---\n{new_fm}\n---{body_clean}"
    with open(filepath, 'w') as f:
        f.write(new_content)

    _get_index().upsert(slug, filepath, fm)

    return {"slug": slug, "filepath": filepath, "frontmatter": fm, "body": body.strip(), "raw": content}


def update_article(slug: str, updates: dict) -> dict:
    """Update an article's frontmatter. v1.7: auto-increment version, recompute review."""
    filepath = _slug_path(slug)
    try:
        with open(filepath) as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"Article not found: {slug}"}

    parts = content.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
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
    body = parts[2] if len(parts) > 2 else ""
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
        return {"error": f"Article not found: {slug}"}
    archive_dir = Path(get("paths", "archive_dir", default="archive"))
    archive_dir.mkdir(exist_ok=True)
    dest = archive_dir / Path(filepath).name
    shutil.move(filepath, str(dest))

    _get_index().remove(slug)

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
