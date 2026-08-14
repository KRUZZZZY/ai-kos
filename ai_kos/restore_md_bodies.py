"""Reverse the body migration — restore .md bodies from SQLite.

Usage:
    python3 ai_kos/restore_md_bodies.py
"""

import sys
import yaml
import re
from pathlib import Path
from ai_kos.config import get
from ai_kos import db as _db

KNOWLEDGE_DIR = Path(get("paths", "knowledge_dir", default="knowledge"))


def restore():
    """Read bodies from SQLite and write them back into .md files."""
    restored = 0
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
            fm = yaml.safe_load(parts[1]) or {}
            slug = fm.get('slug', md_file.stem)

            body = _db.get_body(slug)
            if not body:
                skipped += 1
                continue

            # Preserve existing ## Related wikilinks from the stub
            wikilinks = ""
            related_match = re.search(r'\n## Related\n(.*)', content, re.DOTALL)
            if related_match:
                wikilinks = '\n## Related\n' + related_match.group(1).strip()

            # Reconstruct full .md: frontmatter + body + wikilinks
            new_content = f"---\n{parts[1].strip()}\n---\n\n{body}"
            if wikilinks:
                new_content += f"\n{wikilinks}"

            with open(md_file, 'w') as f:
                f.write(new_content)

            restored += 1
            print(f"Restored: {slug} ({len(body)} chars)")

        except Exception as e:
            errors.append(f"{md_file}: {e}")
            print(f"ERROR: {md_file}: {e}")

    return {"restored": restored, "skipped": skipped, "errors": len(errors)}


if __name__ == "__main__":
    print("Restoring .md files from SQLite bodies...")
    result = restore()
    print(f"\nDone: {result['restored']} restored, {result['skipped']} skipped, {result['errors']} errors")

    if result['errors'] == 0:
        print("All files restored. The SQLite database remains intact as an additional backend.")
