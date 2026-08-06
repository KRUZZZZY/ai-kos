"""AI-KOS paper comparison — find agreements, contradictions, and gaps between research notes.

Usage:
    compare_papers("slug-a", "slug-b") → {relationship, detail, shared_keywords}
    find_contradictions(topic) → list of paper pairs with contradictory claims
    promote_ready(top_k) → list of topics with enough notes for synthesis
"""

from typing import List, Dict, Optional, Set
from ai_kos.articles import _get_index


def compare_papers(slug_a: str, slug_b: str) -> dict:
    """Compare two research-note articles and identify their relationship.

    Returns a dict with relationship type and detail.
    """
    idx = _get_index()
    fm_a = idx.frontmatter(slug_a)
    fm_b = idx.frontmatter(slug_b)

    if not fm_a or not fm_b:
        return {"error": "One or both articles not found"}

    kw_a = set(fm_a.get("keywords", []))
    kw_b = set(fm_b.get("keywords", []))
    shared = kw_a & kw_b

    # If they share a target_base_slug, they're on the same topic
    same_topic = fm_a.get("target_base_slug") and fm_a.get("target_base_slug") == fm_b.get("target_base_slug")

    # Check paper_comparisons for existing relationship
    comparisons_a = fm_a.get("paper_comparisons", [])
    for comp in comparisons_a:
        if isinstance(comp, dict) and comp.get("other_slug") == slug_b:
            return {
                "slug_a": slug_a, "slug_b": slug_b,
                "relationship": comp.get("relationship", "unknown"),
                "detail": comp.get("detail", ""),
                "shared_keywords": sorted(shared),
                "same_topic": same_topic,
            }

    # Default: papers that share keywords are "related" but unclassified
    return {
        "slug_a": slug_a, "slug_b": slug_b,
        "relationship": "unclassified" if shared else "unrelated",
        "detail": f"Share {len(shared)} keywords: {sorted(shared)}" if shared else "No shared keywords",
        "shared_keywords": sorted(shared),
        "same_topic": same_topic,
    }


def find_contradictions(topic_slug: Optional[str] = None) -> List[dict]:
    """Find all paper pairs with explicitly marked contradictions or gaps.

    If topic_slug is provided, only check notes with that target_base_slug.
    """
    idx = _get_index()
    contradictions = []

    for slug_a, fm_a in idx._frontmatter.items():
        if fm_a.get("type") != "research-note":
            continue
        if topic_slug and fm_a.get("target_base_slug") != topic_slug:
            continue

        comparisons = fm_a.get("paper_comparisons", [])
        for comp in comparisons:
            if isinstance(comp, dict) and comp.get("relationship") in ("contradicts", "gap"):
                slug_b = comp.get("other_slug")
                contradictions.append({
                    "a": slug_a,
                    "b": slug_b,
                    "relationship": comp["relationship"],
                    "detail": comp.get("detail", ""),
                })

    return contradictions


def promote_ready(min_notes: int = 5) -> List[dict]:
    """Find topics that have enough research notes for synthesis into a base article.

    Returns topics sorted by note count, with details about which notes are ready.
    """
    idx = _get_index()
    topics: Dict[str, List[str]] = {}

    for slug, fm in idx._frontmatter.items():
        if fm.get("type") != "research-note":
            continue
        target = fm.get("target_base_slug")
        if not target:
            continue
        topics.setdefault(target, []).append(slug)

    ready = []
    for target, notes in sorted(topics.items(), key=lambda x: len(x[1]), reverse=True):
        if len(notes) >= min_notes:
            # Check how many are synthesized
            synthesized = sum(1 for s in notes
                            if idx.frontmatter(s).get("reading_status") == "synthesized")
            ready.append({
                "target_base_slug": target,
                "note_count": len(notes),
                "notes": notes[:10],  # first 10
                "synthesized_count": synthesized,
                "ready": len(notes) >= min_notes,
            })

    return ready


def reading_status_stats() -> dict:
    """Get statistics on reading status across all research-note articles."""
    idx = _get_index()
    counts = {"unread": 0, "skimmed": 0, "annotated": 0, "synthesized": 0}
    by_status: Dict[str, List[str]] = {k: [] for k in counts}

    for slug, fm in idx._frontmatter.items():
        if fm.get("type") != "research-note":
            continue
        status = fm.get("reading_status", "unread")
        if status in counts:
            counts[status] += 1
            by_status[status].append(slug)

    return {
        "total_research_notes": sum(counts.values()),
        "by_status": counts,
        "unread_slugs": by_status["unread"][:20],
        "ready_for_synthesis": sum(counts[k] for k in ["annotated", "synthesized"]),
    }
