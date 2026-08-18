"""Corpus-level acceptance checks for the v2 linker (plan §4.2 item 14).

NOT a pytest unit test — run manually AFTER the tier migration + relink
(plan §6 steps 15-19), from the repo root:

    python3 -m tests.corpus_acceptance

Asserts on the live corpus:
  - total edges ∈ [700, 1050]
  - max out-degree ≤ 20 (budget max cap)
  - orphans ≤ 30
  - no article lost its manual (non-see-also) edges
  - link_count == inbound related count for a 10-article sample
  - link_all idempotency (second dry run: articles_changed == 0)

Exits non-zero with a report on any failed check.
"""

import sys
from collections import Counter
from pathlib import Path

import yaml

from ai_kos.config import get


def load_articles(knowledge_dir: str):
    """Parse every knowledge article (md + yaml) into (filepath, frontmatter)."""
    articles = []
    for ext in ("*.md", "*.yaml"):
        for p in Path(knowledge_dir).rglob(ext):
            content = p.read_text()
            if p.suffix == ".yaml":
                fm = yaml.safe_load(content) or {}
            elif content.startswith("---"):
                fm = yaml.safe_load(content.split("---", 2)[1]) or {}
            else:
                continue
            articles.append((str(p), fm))
    return articles


def main() -> int:
    knowledge_dir = get("paths", "knowledge_dir", default="knowledge")
    articles = load_articles(knowledge_dir)
    slugs = {fm.get("slug", Path(fp).stem) for fp, fm in articles}

    # Edges from `related` frontmatter (as persisted after relink)
    out_edges = {}
    manual_edges = {}
    for fp, fm in articles:
        slug = fm.get("slug", Path(fp).stem)
        out_edges[slug] = set()
        manual_edges[slug] = set()
        for r in fm.get("related", []) or []:
            r_slug = r.get("slug", r) if isinstance(r, dict) else r
            r_type = r.get("type", "see-also") if isinstance(r, dict) else "see-also"
            if not isinstance(r_slug, str):
                continue
            out_edges[slug].add(r_slug)
            if r_type != "see-also":
                manual_edges[slug].add(r_slug)

    total_edges = sum(len(v) for v in out_edges.values()) // 2  # bidirectional pairs
    degrees = [len(v) for v in out_edges.values() if len(v) > 0]
    orphans = [s for s, v in out_edges.items() if not v]

    # Inbound counts over all related edges (link_count semantics, §5.6)
    inbound = Counter()
    for edges in out_edges.values():
        for target in edges:
            if target in slugs:
                inbound[target] += 1

    checks = []
    checks.append(("total edges in [700, 1050]", 700 <= total_edges <= 1050, f"{total_edges}"))
    checks.append(("max out-degree ≤ 20", max(degrees, default=0) <= 20, f"{max(degrees, default=0)}"))
    checks.append(("orphans ≤ 30", len(orphans) <= 30, f"{len(orphans)}"))

    # Manual edges preserved: every manual edge's target still exists in related
    missing_manual = 0
    for slug, edges in manual_edges.items():
        missing_manual += len(edges - out_edges[slug])
    checks.append(("no manual (non-see-also) edge lost", missing_manual == 0, f"{missing_manual} missing"))

    # link_count == inbound related count (10-article sample)
    sample = sorted(slugs)[:10]
    mismatched = 0
    for fp, fm in articles:
        slug = fm.get("slug", Path(fp).stem)
        if slug in sample and fm.get("link_count", 0) != inbound.get(slug, 0):
            mismatched += 1
    checks.append(("link_count == inbound related (10-article sample)",
                   mismatched == 0, f"{mismatched} mismatched"))

    # Idempotency: dry-run second pass must not find anything to change
    from ai_kos.linker import link_all
    report = link_all(knowledge_dir, dry_run=True)
    checks.append(("link_all idempotent (dry-run articles_changed == 0)",
                   report.get("articles_changed", -1) == 0,
                   f"articles_changed={report.get('articles_changed')}"))

    print(f"Corpus: {len(articles)} articles, {total_edges} edges, "
          f"max degree {max(degrees, default=0)}, {len(orphans)} orphans")
    failed = False
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        failed = failed or not ok
    if failed:
        print("\nACCEPTANCE FAILED")
        return 1
    print("\nACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
