"""AI-KOS linker — automatic typed [[wikilink]] creation between articles sharing >=N keywords.

v1.7: typed relations (see-also edges auto-created), link_count computation,
supersession auto-setting on merge detection, lifecycle management.

Scans all knowledge articles, finds pairs with keyword overlap, and creates
bidirectional typed [[wikilinks]] in the `related` frontmatter field.
Also handles dedup detection: articles with very high keyword overlap (>80%)
are flagged as merge candidates and their loser gets lifecycle=superseded.
"""

import os, re, logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field as dc_field

logger = logging.getLogger("ai-kos.linker")

MERGE_THRESHOLD = 0.80


def _get_default_overlap() -> int:
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
    related: List[dict]  # v1.7: list of {slug, type} dicts
    title: str = ""

    def related_slugs(self) -> Set[str]:
        """Extract bare slugs from related edges."""
        return {r.get("slug", r) if isinstance(r, dict) else r for r in self.related}


def _parse_article(filepath: str) -> ArticleMeta | None:
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
        related = fm.get('related', [])
        # Normalize: strings → {slug, type: see-also}
        normalized = []
        for r in related:
            if isinstance(r, str):
                normalized.append({"slug": r, "type": "see-also"})
            elif isinstance(r, dict):
                if "type" not in r:
                    r = dict(r, type="see-also")
                normalized.append(r)
        return ArticleMeta(
            slug=fm.get('slug', Path(filepath).stem),
            filepath=filepath,
            keywords=set(fm.get('keywords', [])),
            related=normalized,
            title=fm.get('title', ''),
        )
    except Exception as e:
        logger.warning(f"Parse error {filepath}: {e}")
        return None


def _calculate_links(articles: List[ArticleMeta], min_overlap: int = 2) -> tuple:
    """For each article, compute typed edges (see-also for >=min_overlap keywords)."""
    new_links: Dict[str, Set[str]] = {a.slug: set() for a in articles}
    merge_candidates: List[Tuple[str, str, float]] = []

    for i, a in enumerate(articles):
        for j in range(i + 1, len(articles)):
            b = articles[j]
            overlap = a.keywords & b.keywords
            if len(overlap) >= min_overlap:
                new_links[a.slug].add(b.slug)
                new_links[b.slug].add(a.slug)

            if a.keywords and b.keywords:
                min_size = min(len(a.keywords), len(b.keywords))
                if min_size > 0:
                    ratio = len(overlap) / min_size
                    if ratio > MERGE_THRESHOLD:
                        merge_candidates.append((a.slug, b.slug, round(ratio, 2)))

    return new_links, merge_candidates


def _compute_link_counts(articles: List[ArticleMeta]) -> Dict[str, int]:
    """Count inbound wikilinks for each article."""
    counts: Dict[str, int] = {a.slug: 0 for a in articles}
    for a in articles:
        for target_slug in a.related_slugs():
            if target_slug in counts:
                counts[target_slug] += 1
    return counts


def _patch_file(
    filepath: str,
    article: ArticleMeta,
    new_related_slugs: Set[str],
    link_count: int = 0,
    superseded_by: str | None = None,
    lifecycle: str | None = None,
) -> bool:
    """Update related, link_count, and optionally lifecycle/superseded_by in frontmatter."""
    try:
        import yaml

        with open(filepath, 'r') as f:
            content = f.read()

        if not content.startswith('---'):
            return False

        parts = content.split('---', 2)
        if len(parts) < 2:
            return False

        fm = yaml.safe_load(parts[1]) or {}

        # Build typed related edges: keep existing types, add new ones as see-also
        existing_by_slug: Dict[str, str] = {}
        for r in fm.get('related', []):
            if isinstance(r, dict):
                existing_by_slug[r.get("slug", "")] = r.get("type", "see-also")
            elif isinstance(r, str):
                existing_by_slug[r] = "see-also"

        new_related = []
        for slug in sorted(new_related_slugs):
            edge_type = existing_by_slug.get(slug, "see-also")
            new_related.append({"slug": slug, "type": edge_type})
        # Also preserve edges where we link TO something not in the overlap set
        # (manually-added edges of other types)
        for slug, etype in existing_by_slug.items():
            if slug not in new_related_slugs and etype != "see-also":
                new_related.append({"slug": slug, "type": etype})

        fm['related'] = new_related
        fm['link_count'] = link_count

        if superseded_by:
            fm['superseded_by'] = superseded_by
            fm['lifecycle'] = 'superseded'
        if lifecycle:
            fm['lifecycle'] = lifecycle

        new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
        body = parts[2] if len(parts) > 2 else ""

        # Strip existing ## Related section
        body = re.sub(r'\n## Related\n.*', '', body, flags=re.DOTALL)

        # Append wikilinks for Obsidian graph view
        if new_related:
            wikilinks = ' '.join(f'[[{r["slug"]}]]' for r in new_related)
            body = body.rstrip() + f'\n\n## Related\n{wikilinks}\n'

        new_content = f"---\n{new_fm}\n---{body}"

        with open(filepath, 'w') as f:
            f.write(new_content)
        return True
    except Exception as e:
        logger.error(f"Patch error {filepath}: {e}")
        return False


def link_all(knowledge_dir: str = "knowledge", min_overlap: int | None = None) -> dict:
    """Scan all articles, compute typed links, patch files. Idempotent.

    v1.7: auto-sets lifecycle=superseded on merge losers, computes link_count.
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
    link_counts = _compute_link_counts(articles)

    changes = 0
    # Identify losers in merge pairs (shorter slug is "loser" — heuristic)
    losers: Dict[str, str] = {}
    for a_slug, b_slug, ratio in merge_candidates:
        loser = a_slug if len(a_slug) > len(b_slug) else b_slug
        winner = b_slug if loser == a_slug else a_slug
        losers[loser] = winner

    for article in articles:
        current_slugs = article.related_slugs()
        target_slugs = new_links.get(article.slug, set())

        edge_changed = current_slugs != target_slugs
        is_loser = article.slug in losers
        # Skip supersede if already superseded to the same winner
        already_superseded = False
        if is_loser:
            import yaml
            try:
                with open(article.filepath) as f:
                    fm = yaml.safe_load(f.read().split('---')[1]) or {}
                if fm.get('lifecycle') == 'superseded' and fm.get('superseded_by') == losers[article.slug]:
                    already_superseded = True
            except Exception:
                pass
        has_supersede = is_loser and not already_superseded
        lc = link_counts.get(article.slug, 0)

        if edge_changed or has_supersede:
            kw = {"superseded_by": losers.get(article.slug)} if has_supersede else {}
            if _patch_file(article.filepath, article, target_slugs, link_count=lc, **kw):
                changes += 1
                logger.info(f"Linked {article.slug}: {len(current_slugs)}→{len(target_slugs)} edges, link_count={lc}")
        elif lc != 0:
            # Update link_count silently (don't count as a change)
            _patch_file(article.filepath, article, target_slugs, link_count=lc)

    return {
        "status": "done",
        "articles_scanned": len(articles),
        "articles_changed": changes,
        "total_links_created": sum(len(v) for v in new_links.values()),
        "merge_candidates": [{"a": a, "b": b, "overlap": r} for a, b, r in merge_candidates],
        "min_overlap_used": min_overlap,
    }


def get_linked(slug: str, knowledge_dir: str = "knowledge") -> List[str]:
    for md in Path(knowledge_dir).rglob(f"{slug}.md"):
        meta = _parse_article(str(md))
        if meta:
            return list(meta.related_slugs())
    return []
