"""AI-KOS linker — automatic [[wikilink]] creation between articles sharing ≥3 keywords.

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

MIN_KEYWORD_OVERLAP = 3       # articles with ≥3 shared keywords get linked
MERGE_THRESHOLD = 0.80        # >80% keyword overlap → flag as merge candidate


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


def _calculate_links(articles: List[ArticleMeta]) -> Dict[str, Set[str]]:
    """For each article, compute the slugs it should link to (≥3 shared keywords)."""
    new_links: Dict[str, Set[str]] = {a.slug: set() for a in articles}
    merge_candidates: List[Tuple[str, str, float]] = []

    for i, a in enumerate(articles):
        for j in range(i + 1, len(articles)):
            b = articles[j]
            overlap = a.keywords & b.keywords
            if len(overlap) >= MIN_KEYWORD_OVERLAP:
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
    """Update the `related` field in an article's frontmatter."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        if not content.startswith('---'):
            return False

        parts = content.split('---', 2)
        if len(parts) < 2:
            return False

        import yaml
        fm = yaml.safe_load(parts[1]) or {}
        fm['related'] = new_related

        new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
        body = parts[2] if len(parts) > 2 else ""
        new_content = f"---\n{new_fm}\n---{body}"

        with open(filepath, 'w') as f:
            f.write(new_content)
        return True
    except Exception as e:
        logger.error(f"Patch error {filepath}: {e}")
        return False


def link_all(knowledge_dir: str = "knowledge") -> dict:
    """Scan all articles, compute links, and patch files. Idempotent."""
    articles = []
    for md in Path(knowledge_dir).rglob("*.md"):
        meta = _parse_article(str(md))
        if meta and meta.keywords:
            articles.append(meta)

    if not articles:
        return {"status": "no_articles", "count": 0}

    new_links, merge_candidates = _calculate_links(articles)

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
    }


def get_linked(slug: str, knowledge_dir: str = "knowledge") -> List[str]:
    """Return all articles linked to the given slug."""
    for md in Path(knowledge_dir).rglob(f"{slug}.md"):
        meta = _parse_article(str(md))
        if meta:
            return meta.related
    return []
