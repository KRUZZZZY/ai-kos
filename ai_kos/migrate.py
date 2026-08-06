"""AI-KOS article schema migration system.

v1.7: adds v2 migration for typed relations, lifecycle, provenance enum,
usage signals, review cadence, Diátaxis, and edit history.

Usage:
    ai-kos migrate              # apply pending migrations
    ai-kos migrate --dry-run    # preview changes without writing
"""

import logging
import os
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


def run_migrations(
    knowledge_dir: Optional[str] = None,
    target_version: Optional[int] = None,
    dry_run: bool = False,
) -> Dict:
    kd = knowledge_dir or get("paths", "knowledge_dir", default="knowledge")
    target = target_version or CURRENT_SCHEMA_VERSION
    kb_path = Path(kd)

    pending = [(v, name, fn) for v, name, fn in _migrations if v > 0 and v <= target]
    if not pending:
        return {"scanned": 0, "migrated": 0, "skipped": 0, "errors": 0, "details": []}

    results = {"scanned": 0, "migrated": 0, "skipped": 0, "errors": 0, "details": []}

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
