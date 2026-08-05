"""AI-KOS article store — CRUD for knowledge articles + auto-linking on write.

Uses an in-memory index of slug→filepath + frontmatter cache for O(1) lookups.
The index is built once on first access and incrementally updated on writes.
"""

import os, uuid, logging, yaml
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Optional, List, Dict

from ai_kos.schemas import ArticleType, ARTICLE_CLASSES, TEMPLATES, article_to_markdown
from ai_kos.config import get

logger = logging.getLogger("ai-kos.articles")
KNOWLEDGE_DIR = get("paths", "knowledge_dir", default="knowledge")


# ── In-Memory Article Index ──────────────────────────────────────────────────

class _ArticleIndex:
    """Cached slug→filepath + frontmatter index. Built once, updated incrementally.

    Solves the O(n) rglob/YAML-parse problem: at 71 articles it's imperceptible,
    at 500+ it becomes noticeable. This makes all lookups O(1).
    """

    def __init__(self):
        self._paths: Dict[str, str] = {}       # slug → absolute filepath
        self._frontmatter: Dict[str, dict] = {} # slug → parsed frontmatter
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
            })
        return sorted(results, key=lambda r: r["title"])

    def stats(self) -> dict:
        """Compute stats from cached frontmatter."""
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

        orphans = [slug for slug, fm in self._frontmatter.items() if not fm.get("related")]
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
        """Add or update an entry in the index."""
        self._paths[slug] = filepath
        self._frontmatter[slug] = frontmatter

    def remove(self, slug: str) -> None:
        """Remove an entry from the index."""
        self._paths.pop(slug, None)
        self._frontmatter.pop(slug, None)

    def invalidate(self) -> None:
        """Force full rebuild on next access."""
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
    """Force a full index rebuild (call after external file changes)."""
    _index.invalidate()


# ── Path Resolution ──────────────────────────────────────────────────────────

def _slug_path(slug: str) -> str:
    """O(1) lookup: return the filepath for a slug, or a fallback path for creation."""
    idx = _get_index()
    path = idx.filepath(slug)
    if path:
        return path
    return str(Path(KNOWLEDGE_DIR) / "bundles" / "general" / f"{slug}.md")


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
    data.setdefault('next_review_at', today.replace(year=today.year + 1))
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
    fm = yaml.safe_load(md_content.split("---")[1]) or {}
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
    return {"slug": slug, "filepath": filepath, "frontmatter": fm, "body": body.strip(), "raw": content}


def update_article(slug: str, updates: dict) -> dict:
    """Update an article's frontmatter. Uses EAFP (try open) instead of LBYL (exists check)."""
    filepath = _slug_path(slug)
    try:
        with open(filepath) as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"Article not found: {slug}"}

    parts = content.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    fm.update(updates)
    fm['updated_at'] = date.today().isoformat()
    new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    body = parts[2] if len(parts) > 2 else ""
    new_content = f"---\n{new_fm}\n---{body}"
    with open(filepath, 'w') as f:
        f.write(new_content)

    # Update in-memory index
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


def list_articles(article_type: Optional[str] = None, keyword: Optional[str] = None) -> List[dict]:
    """List all articles, optionally filtered. Uses in-memory index — O(1) after first call."""
    results = _get_index().list_all()
    if article_type:
        results = [r for r in results if r["type"] == article_type]
    if keyword:
        results = [r for r in results if keyword.lower() in [k.lower() for k in r.get("keywords", [])]]
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
    """Health statistics from in-memory index."""
    return _get_index().stats()
