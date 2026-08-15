"""AI-KOS skill backup — generate KB `process` articles from Hermes skills.

The KB's ``process`` article type is documented as the skill-backup class
("Step-by-step procedure. Backup for rarely-used Hermes skills"). This module
turns ``~/.hermes/skills/**/SKILL.md`` files into distilled process articles:

- slug = ``skill-<sanitized-name>`` (namespaced, never collides with real articles)
- steps = imperative list items from the body (fallback: section headings)
- outcome + prerequisites from the body/frontmatter
- provenance ``[{source: import, origin_ref: <abs SKILL.md path>}]`` — the full
  skill stays on disk; the article is the recoverable backup.

Idempotent + additive: existing slugs are skipped, nothing is overwritten,
``--dry-run`` previews without writing. Default scope: agent-created skills
(``created_by == "agent"`` in ``usage.json``) — bundled/hub skills are skipped.

Usage:
    python3 -m ai_kos.skill_backup --dry-run
    python3 -m ai_kos.skill_backup --all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

from ai_kos.config import get

SKILLS_DIR_DEFAULT = Path.home() / ".hermes" / "skills"
USAGE_FILE = ".usage.json"  # hidden file: ~/.hermes/skills/.usage.json
SLUG_PREFIX = "skill-"
MAX_STEPS = 30
STEP_MAX_CHARS = 300


# ── parsing ────────────────────────────────────────────────────────────────

def _parse_skill(path: Path) -> dict:
    """Parse a SKILL.md into {name, title, description, tags, env, cmds, body}."""
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    import yaml

    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    name = (fm.get("name") or path.parent.name or "").strip()
    return {
        "name": name,
        "title": (fm.get("title") or name or path.parent.name).strip(),
        "description": (fm.get("description") or "").strip(),
        "tags": [str(t) for t in (fm.get("tags") or [])],
        "env": [str(e) for e in (fm.get("required_environment_variables") or [])],
        "cmds": [str(c) for c in (fm.get("required_commands") or [])],
        "body": body,
    }


def _sanitize_slug(name: str) -> str:
    """Skill name → slug fragment (^[a-z0-9]+(?:-[a-z0-9]+)*$)."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "skill-backup"


def _extract_keywords(skill: dict) -> list:
    kws = []
    for t in skill["tags"]:
        t = t.lower().strip()
        if re.fullmatch(r"[a-z0-9][a-z0-9-]*", t) and t not in kws:
            kws.append(t)
    if len(kws) < 3:
        for w in re.split(r"[^a-z0-9]+", skill["name"].lower()):
            if w and w not in ("skill", "the", "a") and w not in kws:
                kws.append(w)
    if len(kws) < 3:
        # Fall back to significant description words (>=4 chars, no stopwords).
        stop = {"with", "from", "that", "this", "your", "when", "what", "which",
                "have", "into", "them", "they", "then", "than", "their", "about"}
        for w in re.split(r"[^a-z0-9]+", skill["description"].lower()):
            if w and len(w) >= 4 and w not in stop and w not in kws:
                kws.append(w)
    return kws[:8]


def _extract_steps(body: str) -> list:
    """Imperative list items as steps; fall back to section headings."""
    items = []
    for line in body.splitlines():
        line = line.strip()
        m = re.match(r"^(?:\d+[.)]|[-*])\s+(.+)$", line)
        if not m or line.startswith("```"):
            continue
        text = m.group(1).strip()
        if text and not text.startswith("#"):
            items.append(text[:STEP_MAX_CHARS])
    if len(items) < 3:
        items = [h.strip("# ").strip()[:STEP_MAX_CHARS]
                 for h in re.findall(r"^#{2,3}\s+(.+)$", body, re.M)]
    return items[:MAX_STEPS]


def _extract_outcome(body: str, description: str) -> str:
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    for p in reversed(paras):
        if len(p) > 40 and not p.startswith("#"):
            return p[:300]
    return (description or "Skill completed.")[:300]


# ── article construction ───────────────────────────────────────────────────

def build_article_dict(skill: dict, source_path: Path) -> dict:
    """Pure: parsed skill → process-article data dict (no side effects)."""
    steps = _extract_steps(skill["body"])
    if not steps:
        steps = [f"Follow the original skill: {source_path}"]
    return {
        "title": skill["title"],
        "slug": SLUG_PREFIX + _sanitize_slug(skill["name"]),
        "type": "process",
        "keywords": _extract_keywords(skill),
        "summary": (skill["description"] or f"Process backup of the {skill['name']} skill.")[:300],
        "provenance": [{"source": "import", "origin_ref": str(source_path)}],
        "steps": steps,
        "outcome": _extract_outcome(skill["body"], skill["description"]),
        "prerequisites": skill["env"] + skill["cmds"],
    }


# ── backup operations ──────────────────────────────────────────────────────

def skill_backup(skill_path: Path, dry_run: bool = False) -> dict:
    """One SKILL.md → one process article. Idempotent: existing slug → skipped."""
    from ai_kos.articles import create_article, read_article

    path = Path(skill_path)
    if not path.exists():
        return {"error": f"SKILL.md not found: {path}"}
    skill = _parse_skill(path)
    if not skill:
        return {"error": f"could not parse {path}"}
    data = build_article_dict(skill, path)

    existing = read_article(data["slug"])
    if existing and not existing.get("error"):
        return {"skipped": data["slug"], "reason": "already exists"}
    if dry_run:
        return {"dry_run": data["slug"], "data": data}
    result = create_article("process", data)
    if isinstance(result, dict) and result.get("error"):
        return {"error": str(result["error"]), "slug": data["slug"]}
    return result


def backup_skills(skills_dir: Optional[Path] = None, only_agent_created: bool = True,
                  dry_run: bool = False, limit: Optional[int] = None) -> dict:
    """Walk a skills dir and back up SKILL.md files (idempotent, additive)."""
    skills_dir = Path(skills_dir) if skills_dir else SKILLS_DIR_DEFAULT
    usage = {}
    usage_path = skills_dir / USAGE_FILE
    if usage_path.exists():
        try:
            usage = json.loads(usage_path.read_text())
        except (json.JSONDecodeError, OSError):
            usage = {}

    results = {"created": [], "skipped": [], "dry_run": [],
               "errors": [], "total": 0, "skills_dir": str(skills_dir)}
    for path in sorted(skills_dir.rglob("SKILL.md")):
        if only_agent_created:
            meta = usage.get(path.parent.name, {})
            if meta.get("created_by") != "agent":
                continue
        if limit is not None and results["total"] >= limit:
            break
        results["total"] += 1
        try:
            out = skill_backup(path, dry_run=dry_run)
        except Exception as e:  # noqa: BLE001 — one bad skill must not abort the run
            results["errors"].append({"path": str(path), "error": str(e)})
            continue
        if out is None:
            continue
        if "skipped" in out:
            results["skipped"].append(out["skipped"])
        elif "dry_run" in out:
            results["dry_run"].append(out["dry_run"])
        elif "error" in out:
            results["errors"].append({"path": str(path), "error": out["error"]})
        else:
            results["created"].append(out.get("slug", str(path)))
    return results


# ── CLI ────────────────────────────────────────────────────────────────────

def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(prog="skill_backup",
                                description="Back up Hermes skills as KB process articles")
    p.add_argument("--dry-run", action="store_true", help="preview without writing")
    p.add_argument("--all", action="store_true",
                   help="back up every skill (default: agent-created only)")
    p.add_argument("--limit", type=int, default=None, help="max skills to process")
    p.add_argument("--skills-dir", default=None, help="override skills directory")
    args = p.parse_args(argv)

    result = backup_skills(
        skills_dir=Path(args.skills_dir) if args.skills_dir else None,
        only_agent_created=not args.all,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
