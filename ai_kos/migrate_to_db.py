"""One-time migration: move article bodies from .md files into SQLite.

Body content is moved from inline markdown to the SQLite `bodies` table.
.md files become frontmatter-only stubs with ## Related wikilinks for Obsidian.

Usage:
    python -m ai_kos.migrate_to_db              # migrate
    python -m ai_kos.migrate_to_db --dry-run    # preview only
    python -m ai_kos.migrate_to_db --verify     # verify all bodies exist
"""

import sys
import re
import yaml
from pathlib import Path
from ai_kos.config import get
from ai_kos import db as _db

KNOWLEDGE_DIR = Path(get("paths", "knowledge_dir", default="knowledge"))


def migrate(dry_run: bool = False) -> dict:
    """Move all article bodies to SQLite, strip from .md files.

    Preserves the ## Related wikilinks section in .md stubs for Obsidian.
    Returns {migrated, skipped, errors, details}.
    """
    migrated = 0
    skipped = 0
    errors = []

    for md_file in KNOWLEDGE_DIR.rglob("*.md"):
        try:
            with open(md_file, 'r') as f:
                content = f.read()

            if not content.startswith('---'):
                skipped += 1
                continue

            parts = content.split('---', 2)
            if len(parts) < 3:
                skipped += 1
                continue

            fm = yaml.safe_load(parts[1]) or {}
            slug = fm.get('slug', md_file.stem)
            body = parts[2].strip()

            # Extract ## Related wikilinks (to preserve in stub)
            wikilinks_section = ""
            related_match = re.search(r'\n## Related\n(.*)', body, re.DOTALL)
            if related_match:
                wikilinks_section = '\n## Related\n' + related_match.group(1).strip()
                body = re.sub(r'\n## Related\n.*', '', body, flags=re.DOTALL).strip()

            if not body and not wikilinks_section:
                skipped += 1
                continue

            if dry_run:
                if body:
                    print(f"[DRY RUN] Would migrate: {slug} ({len(body)} chars → SQLite)")
                else:
                    print(f"[DRY RUN] Would strip (no body): {slug}")
                migrated += 1
                continue

            # Store body in SQLite
            if body:
                _db.set_body(slug, body)
                print(f"Migrated: {slug} ({len(body)} chars → SQLite)")
            else:
                print(f"Stripped body (was empty): {slug}")

            # Strip body from .md, keeping frontmatter + wikilinks
            new_content = f"---\n{parts[1].strip()}\n---\n{wikilinks_section}".strip()
            with open(md_file, 'w') as f:
                f.write(new_content)

            migrated += 1

        except Exception as e:
            errors.append(f"{md_file}: {e}")
            print(f"ERROR: {md_file}: {e}")

    return {"migrated": migrated, "skipped": skipped, "errors": len(errors), "details": errors}


def verify() -> dict:
    """Verify all articles have bodies in SQLite where expected."""
    total = 0
    with_body = 0
    without_body = 0
    missing = []

    for md_file in KNOWLEDGE_DIR.rglob("*.md"):
        total += 1
        try:
            with open(md_file, 'r') as f:
                content = f.read()
            if not content.startswith('---'):
                continue
            fm = yaml.safe_load(content.split('---')[1]) or {}
            slug = fm.get('slug', md_file.stem)
            body = _db.get_body(slug)
            if body and body.strip():
                with_body += 1
            else:
                without_body += 1
                missing.append(slug)
        except Exception as e:
            missing.append(f"{md_file}: {e}")

    return {
        "total_articles": total,
        "with_body": with_body,
        "without_body": without_body,
        "details": missing,
    }


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        result = migrate(dry_run=True)
        print(f"\nDRY RUN: {result['migrated']} would migrate, {result['skipped']} skipped, {result['errors']} errors")
    elif "--verify" in sys.argv:
        result = verify()
        print(f"Verification: {result['total_articles']} articles, "
              f"{result['with_body']} with body, {result['without_body']} without body")
        if result['without_body'] > 0:
            print(f"Missing ({len(result['details'])}):")
            for m in result['details'][:20]:
                print(f"  - {m}")
            if len(result['details']) > 20:
                print(f"  ... and {len(result['details']) - 20} more")
    else:
        print("AI-KOS Body Migration (inline .md → SQLite)")
        print(f"Knowledge dir: {KNOWLEDGE_DIR}")
        print(f"DB path: {_db._get_db_path()}")
        print()
        result = migrate()
        print(f"\nDone: {result['migrated']} migrated, {result['skipped']} skipped, {result['errors']} errors")
