"""AI-KOS linker — automatic [[wikilink]] creation between articles sharing >=N keywords.

Scans all knowledge articles, finds pairs with keyword overlap, and creates
bidirectional [[wikilinks]] in the `related` frontmatter field of each article.
Also handles dedup detection: articles with very high keyword overlap (>80%)
are flagged as potential merge candidates.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger("ai-kos.linker")

MERGE_THRESHOLD = 0.80  # >80% keyword overlap → flag as merge candidate


def _get_default_overlap() -> int:
    """Read min_keyword_overlap from config, falling back to 2."""
    try:
        from ai_kos.config import get
        return get("linking", "min_keyword_overlap", default=2)
    except Exception:
        return 2


@dataclass
class ArticleMeta:
    slug: str
    filepath: str
    keywords: Set[str]
    related: List[str]  # current wikilinks
    title: str = ""


def _parse_article(filepath: str) -> ArticleMeta | None:
    """Parse frontmatter from a markdown file, extract slug + keywords + related."""
    import yaml
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        if not content.startswith('---'):
            return None
        parts = content.split('---', 2)
        if len(parts) < 2:
            return None
        fm = yaml.safe_load(parts[1]) or {}
        return ArticleMeta(
            slug=fm.get('slug', Path(filepath).stem),
            filepath=filepath,
            keywords=set(fm.get('keywords', [])),
            related=fm.get('related', []),
            title=fm.get('title', ''),
        )
    except Exception as e:
        logger.warning(f"Parse error {filepath}: {e}")
        return None


def _calculate_links(articles: List[ArticleMeta], min_overlap: int = 2) -> tuple:
    """For each article, compute the slugs it should link to (>= min_overlap shared keywords)."""
    new_links: Dict[str, Set[str]] = {a.slug: set() for a in articles}
    merge_candidates: List[Tuple[str, str, float]] = []

    for i, a in enumerate(articles):
        for j in range(i + 1, len(articles)):
            b = articles[j]
            overlap = a.keywords & b.keywords
            if len(overlap) >= min_overlap:
                new_links[a.slug].add(b.slug)
                new_links[b.slug].add(a.slug)

            # Check for merge candidates (>80% overlap on the smaller set)
            if a.keywords and b.keywords:
                min_size = min(len(a.keywords), len(b.keywords))
                if min_size > 0:
                    ratio = len(overlap) / min_size
                    if ratio > MERGE_THRESHOLD:
                        merge_candidates.append((a.slug, b.slug, round(ratio, 2)))

    return new_links, merge_candidates


def _patch_file(filepath: str, article: ArticleMeta, new_related: List[str]) -> bool:
    """Update the `related` field in frontmatter and append [[wikilinks]] to body for Obsidian graph view."""
    try:
        import re
        import yaml

        with open(filepath, 'r') as f:
            content = f.read()

        if not content.startswith('---'):
            return False

        parts = content.split('---', 2)
        if len(parts) < 2:
            return False

        fm = yaml.safe_load(parts[1]) or {}
        fm['related'] = new_related

        new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
        body = parts[2] if len(parts) > 2 else ""

        # Strip existing ## Related section so we don't duplicate
        body = re.sub(r'\n## Related\n.*', '', body, flags=re.DOTALL)

        # Append wikilinks for Obsidian graph view
        if new_related:
            wikilinks = ' '.join(f'[[{slug}]]' for slug in sorted(new_related))
            body = body.rstrip() + f'\n\n## Related\n{wikilinks}\n'

        new_content = f"---\n{new_fm}\n---{body}"

        with open(filepath, 'w') as f:
            f.write(new_content)
        return True
    except Exception as e:
        logger.error(f"Patch error {filepath}: {e}")
        return False


def link_all(knowledge_dir: str = "knowledge", min_overlap: int | None = None) -> dict:
    """Scan all articles, compute links, and patch files. Idempotent.

    Args:
        knowledge_dir: Path to knowledge articles.
        min_overlap: Shared keyword threshold. Reads config if None, defaults to 2.
    """
    if min_overlap is None:
        min_overlap = _get_default_overlap()

    articles = []
    for md in Path(knowledge_dir).rglob("*.md"):
        meta = _parse_article(str(md))
        if meta and meta.keywords:
            articles.append(meta)

    if not articles:
        return {"status": "no_articles", "count": 0}

    new_links, merge_candidates = _calculate_links(articles, min_overlap)

    changes = 0
    link_map = {}
    for article in articles:
        current = set(article.related)
        target = new_links.get(article.slug, set())
        if current != target:
            if _patch_file(article.filepath, article, sorted(target)):
                changes += 1
                link_map[article.slug] = sorted(target)
                logger.info(f"Linked {article.slug}: {len(current)}→{len(target)} wikilinks")

    return {
        "status": "done",
        "articles_scanned": len(articles),
        "articles_changed": changes,
        "total_links_created": sum(len(v) for v in new_links.values()),
        "merge_candidates": [{"a": a, "b": b, "overlap": r} for a, b, r in merge_candidates],
        "min_overlap_used": min_overlap,
    }


def get_linked(slug: str, knowledge_dir: str = "knowledge") -> List[str]:
    """Return all articles linked to the given slug."""
    for md in Path(knowledge_dir).rglob(f"{slug}.md"):
        meta = _parse_article(str(md))
        if meta:
            return meta.related
    return []
