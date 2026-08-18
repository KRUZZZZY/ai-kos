"""AI-KOS article schema migration system.

v1.7: adds v2 migration for typed relations, lifecycle, provenance enum,
usage signals, review cadence, Diátaxis, and edit history.
v2 linker: `migrate_keyword_tiers` — a corpus-wide TWO-PASS migration that splits
flat `keywords` into `subject_keywords` + article-tier `keywords` (df-rule or
seed lexicon) and backfills `related_pinned` with legacy see-also edges the v2
algorithm would not recompute.

Usage:
    ai-kos migrate              # apply pending migrations
    ai-kos migrate --dry-run    # preview changes without writing
    ai-kos migrate --tiers      # also run the keyword-tier migration
"""

import logging
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ai_kos.config import get

logger = logging.getLogger("ai-kos.migrate")

CURRENT_SCHEMA_VERSION = 3

# ── Migration Registry ───────────────────────────────────────────────────────

_migrations: List[Tuple[int, str, Callable[[dict, str], Tuple[dict, str]]]] = []


def register(version: int, name: str):
    def decorator(fn: Callable[[dict, str], Tuple[dict, str]]):
        _migrations.append((version, name, fn))
        _migrations.sort(key=lambda x: x[0])
        return fn
    return decorator


# ── Built-in Migrations ──────────────────────────────────────────────────────

@register(version=1, name="add_schema_version")
def _add_schema_version(fm: dict, body: str) -> Tuple[dict, str]:
    """Migration v1: Add schema_version field to all articles."""
    if "schema_version" not in fm:
        fm["schema_version"] = 1
    return fm, body


@register(version=2, name="v17_typed_relations_plus")
def _v17_migration(fm: dict, body: str) -> Tuple[dict, str]:
    """Migration v2: Transform v1.6 format to v1.7 typed relations + all new fields.

    Changes:
      - related: List[str] → List[{slug, type: see-also}]
      - provenance: List[str] → List[{source: manual, origin_ref: str}]
      - Add lifecycle: current, superseded_by: null
      - Add doc_type: null
      - Add review_interval_days: computed from type
      - Add version: 1, history: [initial entry]
      - Add link_count: 0, last_accessed: null
      - Bump schema_version to 2
    """
    # Convert related from List[str] to List[{slug, type}]
    related = fm.get('related', [])
    if related and isinstance(related[0] if related else None, str):
        fm['related'] = [{"slug": r, "type": "see-also"} for r in related]
    elif related:
        # Already dicts, ensure type field
        fm['related'] = [
            dict(r, type=r.get('type', 'see-also')) if isinstance(r, dict)
            else {"slug": r, "type": "see-also"}
            for r in related
        ]

    # Convert provenance from List[str] to List[{source, origin_ref}]
    provenance = fm.get('provenance', [])
    if provenance and isinstance(provenance[0] if provenance else None, str):
        fm['provenance'] = [{"source": "manual", "origin_ref": p} for p in provenance]
    elif provenance:
        fm['provenance'] = [
            dict(p, source=p.get('source', 'manual')) if isinstance(p, dict)
            else {"source": "manual", "origin_ref": str(p)}
            for p in provenance
        ]

    # Lifecycle
    if 'lifecycle' not in fm:
        fm['lifecycle'] = 'current'
    if 'superseded_by' not in fm:
        fm['superseded_by'] = None

    # Diátaxis
    if 'doc_type' not in fm:
        fm['doc_type'] = None

    # Usage signals
    if 'link_count' not in fm:
        fm['link_count'] = 0
    if 'last_accessed' not in fm:
        fm['last_accessed'] = None

    # Review cadence — compute from type
    if 'review_interval_days' not in fm:
        _DEFAULTS = {'base': 365, 'process': 180, 'plan': 90, 'help': 365,
                     'research-note': 180, 'note': 90, 'mission': 365}
        atype = fm.get('type', 'base')
        fm['review_interval_days'] = _DEFAULTS.get(atype, 365)

    # Edit history
    if 'version' not in fm:
        fm['version'] = 1
    if 'history' not in fm:
        from datetime import datetime, timezone
        fm['history'] = [{
            'v': 1,
            'at': datetime.now(timezone.utc).isoformat(),
            'by': 'agent:kruzzzy',
            'note': 'Migrated to v1.7 schema',
        }]

    # Confidence
    if 'confidence' not in fm:
        fm['confidence'] = 0.8

    fm['schema_version'] = 2
    return fm, body


@register(version=3, name="v17_paper_ingestion_fields")
def _v3_migration(fm: dict, body: str) -> Tuple[dict, str]:
    """Migration v3: Add reading_status, doi, and paper_comparisons fields."""
    if 'reading_status' not in fm:
        fm['reading_status'] = 'unread'
    if 'doi' not in fm:
        fm['doi'] = None
    if 'paper_comparisons' not in fm:
        fm['paper_comparisons'] = []
    fm['schema_version'] = 3
    return fm, body


# ── Migration Engine ─────────────────────────────────────────────────────────

def _parse_article(filepath: str) -> Tuple[Optional[dict], Optional[str]]:
    import yaml
    try:
        with open(filepath) as f:
            content = f.read()
        if not content.startswith("---"):
            return None, None
        parts = content.split("---", 2)
        fm = yaml.safe_load(parts[1]) or {}
        body = parts[2] if len(parts) > 2 else ""
        return fm, body
    except Exception as e:
        logger.warning(f"Migrate: skip {filepath}: {e}")
        return None, None


def _write_article(filepath: str, fm: dict, body: str) -> None:
    import yaml
    new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    content = f"---\n{new_fm}\n---{body}"
    tmp = filepath + ".migrate_tmp"
    with open(tmp, 'w') as f:
        f.write(content)
    os.replace(tmp, filepath)


def _article_needs_migration(fm: dict, target_version: int) -> bool:
    current = fm.get("schema_version", 0)
    return current < target_version


# ── v2 keyword-tier migration (corpus-wide, two-pass) ────────────────────────

def _load_fm(filepath: str) -> Tuple[Optional[dict], Optional[str]]:
    """Load frontmatter + body for .md (frontmatter block) and .yaml (whole dict)."""
    import yaml
    try:
        with open(filepath) as f:
            content = f.read()
        if filepath.endswith(".yaml"):
            fm = yaml.safe_load(content) or {}
            return fm, ""
        if not content.startswith("---"):
            return None, None
        parts = content.split("---", 2)
        fm = yaml.safe_load(parts[1]) or {}
        body = parts[2] if len(parts) > 2 else ""
        return fm, body
    except Exception as e:
        logger.warning(f"Migrate: skip {filepath}: {e}")
        return None, None


def _write_frontmatter(filepath: str, fm: dict, body: str) -> None:
    """Whole-dict frontmatter rewrite (never regex the keywords block — §3.4)."""
    import yaml
    new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    if filepath.endswith(".yaml"):
        content = new_fm
    else:
        content = f"---\n{new_fm}\n---{body}"
    tmp = filepath + ".migrate_tmp"
    with open(tmp, 'w') as f:
        f.write(content)
    os.replace(tmp, filepath)


def _assert_no_keyword_loss(old_kws: List[str], new_kws: List[str], subject: List[str], slug: str) -> None:
    """No-data-loss invariant (§2.5): set(old) == set(new) ∪ set(subject), all str."""
    if not all(isinstance(k, str) for k in new_kws) or not all(isinstance(k, str) for k in subject):
        raise ValueError(f"Tier migration produced non-string keywords for {slug}")
    if set(old_kws) != set(new_kws) | set(subject):
        raise ValueError(
            f"Tier migration lost keywords for {slug}: "
            f"old={sorted(set(old_kws))} new∪subject={sorted(set(new_kws) | set(subject))}"
        )


def migrate_keyword_tiers(knowledge_dir: Optional[str] = None, dry_run: bool = False) -> Dict:
    """Two-pass keyword-tier migration (§2.5). Needs corpus-wide df, so it is NOT
    a @register per-file migration.

    Pass 1 (read-only): parse all articles, compute document frequencies over
    flat `keywords`, build the subject lexicon (df >= ceil(sqrt(N)) OR seed
    lexicon), compute per-article subject/article splits (all-subject corner keeps
    top-3-by-idf as article tier) and the `related_pinned` backfill (existing
    see-also edges the v2 algorithm would not recompute, computed in-memory via
    `_calculate_links_v2` on the parsed corpus — dry).
    Pass 2 (write): rewrite frontmatter ONLY (whole-dict yaml dump, sort_keys=False),
    insert `subject_keywords` + `related_pinned` right after `keywords`, bump
    `schema_version` → 3, append a history entry. `dry_run=True` writes nothing.
    """
    kd = knowledge_dir or get("paths", "knowledge_dir", default="knowledge")
    kb_path = Path(kd)

    # ── Pass 1: corpus-wide analysis (in memory) ──────────────────────────────
    entries = []  # (filepath, fm, body, old_kws)
    for ext in ("*.md", "*.yaml"):
        for f in sorted(kb_path.rglob(ext)):
            fm, body = _load_fm(str(f))
            if fm is None:
                continue
            entries.append((str(f), fm, body, list(fm.get("keywords", []) or [])))

    n_total = len(entries)
    n = sum(1 for _fp, _fm, _body, old in entries if old)  # keyword-bearing only — mirrors link_all's N (§1.1 df floor)
    df: Dict[str, int] = {}
    for _fp, fm, _body, _old in entries:
        for kw in fm.get("keywords", []) or []:
            if isinstance(kw, str):
                df[kw] = df.get(kw, 0) + 1
    floor = math.ceil(math.sqrt(n)) if n else 0
    seeds = set(get("linking", "subject_seed_lexicon", default=[]))
    lexicon = {k for k, c in df.items() if c >= floor} | seeds

    # v2 reference edge set (what the linker would produce on the unmigrated corpus)
    from ai_kos.linker import _parse_article as _linker_parse, _calculate_links_v2
    metas = []
    for fp, _fm, _body, _old in entries:
        meta = _linker_parse(fp)
        if meta and meta.keywords:
            metas.append(meta)
    v2_links, _v2_merges = _calculate_links_v2(metas) if metas else ({}, [])

    stats = {
        "status": "dry_run" if dry_run else "done",
        "scanned": n_total,
        "migrated": 0,
        "skipped": 0,
        "errors": 0,
        "subject_keyword_instances": 0,
        "article_keyword_instances": 0,
        "related_pinned_backfilled": 0,
        "all_subject_corner": [],
        "by_type": {},
        "details": [],
    }

    plans = []  # (filepath, body, new_fm, old_kws) — written only when not dry_run
    for fp, fm, body, old_kws in entries:
        # Idempotency gate: skip files already tier-migrated (they carry the
        # tier fields). Keyed on FIELD PRESENCE, not schema_version — the
        # pre-existing per-file v3 migration (`v17_paper_ingestion_fields`)
        # also stamps schema_version 3, so a version gate would silently skip
        # tiering for every article that ran the plain `migrate` first.
        if "subject_keywords" in fm or "related_pinned" in fm:
            stats["skipped"] += 1
            continue

        # Subject/article split via the df rule + seed lexicon
        subject = [k for k in old_kws if k in lexicon]
        new_kws = [k for k in old_kws if k not in lexicon]
        if subject and not new_kws:
            # All-subject corner: keep top-3-by-idf (rarest) as article tier
            idf = {k: math.log((n + 1) / (df.get(k, 0) + 1)) + 1.0 for k in subject}
            top = sorted(subject, key=lambda k: (-idf[k], k))[:3]
            new_kws, subject = top, [k for k in subject if k not in set(top)]
            stats["all_subject_corner"].append(fm.get("slug", Path(fp).stem))

        # related_pinned backfill: existing see-also edges the v2 algorithm won't recompute
        slug = fm.get("slug", Path(fp).stem)
        v2_auto = v2_links.get(slug, set())
        pinned = []
        for r in fm.get("related", []) or []:
            r_slug = r.get("slug", r) if isinstance(r, dict) else r
            if not isinstance(r_slug, str):
                continue
            r_type = r.get("type", "see-also") if isinstance(r, dict) else "see-also"
            if r_type == "see-also" and r_slug not in v2_auto and r_slug not in pinned:
                pinned.append(r_slug)

        # Verify invariants in memory before any write
        _assert_no_keyword_loss(old_kws, new_kws, subject, slug)

        new_fm = {}
        inserted_tiers = False
        for k, v in fm.items():
            if k == "keywords":
                new_fm["keywords"] = new_kws          # article tier after the split
                new_fm["subject_keywords"] = subject  # inserted right after keywords
                new_fm["related_pinned"] = pinned
                inserted_tiers = True
            elif k in ("subject_keywords", "related_pinned"):
                continue  # replaced above — never clobber with the originals
            else:
                new_fm[k] = v
        if not inserted_tiers:
            # Keyword-less article: still record the (empty) tiers + backfill
            new_fm["subject_keywords"] = subject
            new_fm["related_pinned"] = pinned
        new_fm["schema_version"] = 3
        version = int(new_fm.get("version", 1) or 1) + 1
        new_fm["version"] = version
        history = list(new_fm.get("history", []) or [])
        history.append({
            "v": version,
            "at": datetime.now(timezone.utc).isoformat(),
            "by": "agent:kruzzzy",
            "note": "tiered-keywords migration",
        })
        new_fm["history"] = history

        stats["migrated"] += 1
        stats["subject_keyword_instances"] += len(subject)
        stats["article_keyword_instances"] += len(new_kws)
        stats["related_pinned_backfilled"] += len(pinned)
        atype = fm.get("type", "unknown")
        stats["by_type"][atype] = stats["by_type"].get(atype, 0) + 1
        stats["details"].append({
            "filepath": fp,
            "slug": slug,
            "status": "migrated" if not dry_run else "would_migrate",
            "subject_keywords": subject,
            "keywords_after": new_kws,
            "related_pinned": pinned,
        })
        plans.append((fp, body, new_fm, old_kws))

    # ── Pass 2: write (skip entirely on dry-run) ─────────────────────────────
    if not dry_run:
        for fp, body, new_fm, old_kws in plans:
            try:
                _write_frontmatter(fp, new_fm, body)
            except Exception as e:
                logger.error(f"Tier migration write failed for {fp}: {e}")
                stats["errors"] += 1
                continue
            # Post-verify the file on disk (no-data-loss invariant, §2.5)
            fm_after, _ = _load_fm(fp)
            if fm_after is not None:
                _assert_no_keyword_loss(
                    old_kws=old_kws,
                    new_kws=list(fm_after.get("keywords", []) or []),
                    subject=list(fm_after.get("subject_keywords", []) or []),
                    slug=fm_after.get("slug", Path(fp).stem),
                )

    logger.info(
        f"Tier migration {'dry-run ' if dry_run else ''}complete: {stats['scanned']} scanned, "
        f"{stats['migrated']} migrated, {stats['skipped']} skipped, "
        f"{stats['subject_keyword_instances']} subject / {stats['article_keyword_instances']} "
        f"article keyword-instances, {stats['related_pinned_backfilled']} pinned edges backfilled"
    )
    return stats


def run_migrations(
    knowledge_dir: Optional[str] = None,
    target_version: Optional[int] = None,
    dry_run: bool = False,
    tiers: bool = False,
) -> Dict:
    kd = knowledge_dir or get("paths", "knowledge_dir", default="knowledge")
    target = target_version or CURRENT_SCHEMA_VERSION
    kb_path = Path(kd)

    # Per-file migrations run FIRST, then the corpus-wide tier pass. If the
    # tier pass ran first it would stamp schema_version (3) on every file and
    # the per-file loop would skip those files — silently dropping the
    # v1/v2/v3 field migrations (typed relations, lifecycle, paper fields).
    # Deliberate ordering deviation from plan §2.5's literal order (safer).
    results = {"scanned": 0, "migrated": 0, "skipped": 0, "errors": 0, "details": []}

    pending = [(v, name, fn) for v, name, fn in _migrations if v > 0 and v <= target]
    if pending:
        for md in sorted(kb_path.rglob("*.md")):
            results["scanned"] += 1
            fm, body = _parse_article(str(md))
            if fm is None:
                results["errors"] += 1
                results["details"].append({
                    "filepath": str(md), "status": "error", "reason": "Could not parse article",
                })
                continue

            start_version = fm.get("schema_version", 0)
            if start_version >= target:
                results["skipped"] += 1
                continue

            migrated_versions = []
            for version, name, fn in pending:
                if version <= start_version:
                    continue
                try:
                    fm, body = fn(fm, body)
                    fm["schema_version"] = version
                    migrated_versions.append(f"{version}:{name}")
                except Exception as e:
                    logger.error(f"Migration {version}:{name} failed for {md}: {e}")
                    results["errors"] += 1
                    results["details"].append({
                        "filepath": str(md), "status": "error",
                        "migration": f"{version}:{name}", "reason": str(e),
                    })
                    break

            if migrated_versions:
                if not dry_run:
                    _write_article(str(md), fm, body)
                results["migrated"] += 1
                results["details"].append({
                    "filepath": str(md), "status": "migrated" if not dry_run else "would_migrate",
                    "from_version": start_version,
                    "to_version": fm.get("schema_version", start_version),
                    "migrations_applied": migrated_versions,
                })
            else:
                results["skipped"] += 1

    tier_stats = None
    if tiers:
        tier_stats = migrate_keyword_tiers(kd, dry_run=dry_run)
        results["tiers"] = tier_stats

    logger.info(
        f"Migration {'dry-run ' if dry_run else ''}complete: "
        f"{results['scanned']} scanned, {results['migrated']} migrated, "
        f"{results['skipped']} skipped, {results['errors']} errors"
    )
    return results


def list_pending(knowledge_dir: Optional[str] = None) -> List[dict]:
    kd = knowledge_dir or get("paths", "knowledge_dir", default="knowledge")
    target = CURRENT_SCHEMA_VERSION
    pending_articles = []

    for md in sorted(Path(kd).rglob("*.md")):
        fm, _ = _parse_article(str(md))
        if fm is None:
            continue
        current = fm.get("schema_version", 0)
        if current < target:
            pending_articles.append({
                "filepath": str(md), "slug": fm.get("slug", md.stem),
                "current_version": current, "target_version": target,
            })

    return pending_articles
