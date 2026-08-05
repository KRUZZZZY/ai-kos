"""AI-KOS article schema migration system.

Since articles are markdown files (not a database), migrations are pure-Python
transforms: (frontmatter, body) → (frontmatter, body). Each migration checks the
`schema_version` field to determine if it should run.

Migrations are registered in order and run idempotently — applying the same
migration twice is safe (it skips already-migrated articles).

Usage:
    # CLI
    ai-kos migrate              # apply pending migrations
    ai-kos migrate --dry-run    # preview changes without writing

    # API
    from ai_kos.migrate import run_migrations
    results = run_migrations(dry_run=True)
"""

import logging
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ai_kos.config import get

logger = logging.getLogger("ai-kos.migrate")

CURRENT_SCHEMA_VERSION = 1

# ── Migration Registry ───────────────────────────────────────────────────────

# Ordered list of (version, name, transform_fn)
# Transform signature: Callable[[dict, str], Tuple[dict, str]]
#   - Input: (frontmatter_dict, body_text)
#   - Output: (modified_frontmatter_dict, modified_body_text)
_migrations: List[Tuple[int, str, Callable[[dict, str], Tuple[dict, str]]]] = []


def register(version: int, name: str):
    """Decorator to register a migration function."""
    def decorator(fn: Callable[[dict, str], Tuple[dict, str]]):
        _migrations.append((version, name, fn))
        _migrations.sort(key=lambda x: x[0])  # Keep sorted by version
        return fn
    return decorator


# ── Built-in Migrations ──────────────────────────────────────────────────────

@register(version=1, name="add_schema_version")
def _add_schema_version(fm: dict, body: str) -> Tuple[dict, str]:
    """Migration v1: Add schema_version field to all articles.

    This is the baseline migration — ensures every article has a schema_version.
    Existing articles without the field get version 1. Future schema changes
    will increment the version and add new migration functions.
    """
    if "schema_version" not in fm:
        fm["schema_version"] = 1
    return fm, body


# ── Migration Engine ─────────────────────────────────────────────────────────

def _parse_article(filepath: str) -> Tuple[Optional[dict], Optional[str]]:
    """Read an article file, return (frontmatter, raw_content)."""
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
    """Write frontmatter + body back to disk."""
    import yaml
    new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    content = f"---\n{new_fm}\n---{body}"
    # Atomic write: temp file + rename
    tmp = filepath + ".migrate_tmp"
    with open(tmp, 'w') as f:
        f.write(content)
    os.replace(tmp, filepath)


def _article_needs_migration(fm: dict, target_version: int) -> bool:
    """Check if an article needs migration to reach target_version."""
    current = fm.get("schema_version", 0)
    return current < target_version


def run_migrations(
    knowledge_dir: Optional[str] = None,
    target_version: Optional[int] = None,
    dry_run: bool = False,
) -> Dict:
    """Run pending migrations on all articles.

    Args:
        knowledge_dir: Root of the knowledge base. Default from config.
        target_version: Migrate up to this version. Default: CURRENT_SCHEMA_VERSION.
        dry_run: If True, preview changes without writing.

    Returns:
        Dict with 'scanned', 'migrated', 'skipped', 'errors', 'details' keys.
    """
    kd = knowledge_dir or get("paths", "knowledge_dir", default="knowledge")
    target = target_version or CURRENT_SCHEMA_VERSION
    kb_path = Path(kd)

    # Find migrations to apply
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
                "filepath": str(md),
                "status": "error",
                "reason": "Could not parse article",
            })
            continue

        start_version = fm.get("schema_version", 0)
        if start_version >= target:
            results["skipped"] += 1
            continue

        # Apply each pending migration in order
        migrated_versions = []
        original_fm = dict(fm)
        for version, name, fn in pending:
            if version <= start_version:
                continue  # Already at or past this version
            try:
                fm, body = fn(fm, body)
                fm["schema_version"] = version
                migrated_versions.append(f"{version}:{name}")
            except Exception as e:
                logger.error(f"Migration {version}:{name} failed for {md}: {e}")
                results["errors"] += 1
                results["details"].append({
                    "filepath": str(md),
                    "status": "error",
                    "migration": f"{version}:{name}",
                    "reason": str(e),
                })
                break

        if migrated_versions:
            if not dry_run:
                _write_article(str(md), fm, body)
            results["migrated"] += 1
            results["details"].append({
                "filepath": str(md),
                "status": "migrated" if not dry_run else "would_migrate",
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
    """List articles that need migration, without applying changes."""
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
                "filepath": str(md),
                "slug": fm.get("slug", md.stem),
                "current_version": current,
                "target_version": target,
            })

    return pending_articles
