"""AI-KOS GitHub repo sync — one command to upload all three repos.

Repos (see references/github-repo-sync.md):
- ai-kos (code): the repo cwd (or ``--code-dir``)
- ai-kos-knowledge (vault): ``<code>/knowledge`` — a NESTED git repo
- ai-kos-help-guides: ``~/Documents/ai-kos-help-guides`` (help+process subset)

Flow per repo: ``git add -A`` (respects .gitignore) → commit (default message
or ``-m``) → push → verify (``git ls-remote origin HEAD`` == local HEAD).
Never force-push. ``--dry-run`` previews every command without executing.

Help-guides subset: collision check (no slug in both help AND process) →
copy help+process articles to the staging dir → regenerate README from
frontmatter → commit+push (clones the repo first if absent locally).

CLI:
    ai-kos repo-sync [--dry-run] [-m MSG] [--help-guides] [--code-dir DIR]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional

logger = None  # module is CLI-first; prints to stdout like the rest of ai-kos CLI

HELP_GUIDES_DIR_DEFAULT = Path.home() / "Documents" / "ai-kos-help-guides"
HELP_GUIDES_URL = "https://github.com/KRUZZZZY/ai-kos-help-guides.git"
BUNDLES_REL = Path("bundles") / "general"


class RepoSyncError(Exception):
    """Base error for repo sync failures."""


def _run(args: list, cwd: Optional[Path] = None, dry_run: bool = False,
         timeout: int = 300) -> dict:
    """Run a command; in dry-run mode print the command and fake success."""
    if dry_run:
        print("  dry-run:", " ".join(str(a) for a in args))
        return {"returncode": 0, "stdout": "", "stderr": ""}
    proc = subprocess.run(args, cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RepoSyncError(
            f"{' '.join(str(a) for a in args)} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:300]}")
    return {"returncode": proc.returncode, "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip()}


# ── repo helpers ───────────────────────────────────────────────────────────

def _changed_count(repo_dir: Path, dry_run: bool = False) -> int:
    # `git status --porcelain` is READ-ONLY — always run it for real so dry-run
    # previews reflect the actual pending changes (only mutations are faked).
    out = _run(["git", "status", "--porcelain"], cwd=repo_dir, dry_run=False)["stdout"]
    return len([l for l in out.splitlines() if l.strip()])


def _local_head(repo_dir: Path, dry_run: bool = False) -> str:
    if dry_run:
        return "dry-run"
    return _run(["git", "rev-parse", "HEAD"], cwd=repo_dir)["stdout"][:7]


def _verify_push(repo_dir: Path) -> None:
    """Reference pitfall: never trust push output — compare ls-remote vs local HEAD."""
    remote = _run(["git", "remote", "get-url", "origin"], cwd=repo_dir)["stdout"]
    out = _run(["git", "ls-remote", remote, "HEAD"])["stdout"]
    remote_sha = out.split()[0][:7] if out.strip() else ""
    local_sha = _local_head(repo_dir)
    if remote_sha != local_sha:
        raise RepoSyncError(
            f"push verify failed for {repo_dir}: remote={remote_sha} local={local_sha}")
    print(f"  verified: {local_sha} on origin")


def sync_repo(repo_dir, message: str, dry_run: bool = False) -> dict:
    """Stage → commit → push → verify for one repo. Skips clean repos."""
    repo_dir = Path(repo_dir)
    if not (repo_dir / ".git").exists():
        return {"repo": str(repo_dir), "status": "skipped", "reason": "not a git repo"}
    n = _changed_count(repo_dir, dry_run=dry_run)
    if n == 0:
        print(f"{repo_dir.name}: clean — nothing to commit")
        return {"repo": str(repo_dir), "status": "clean"}
    _run(["git", "add", "-A"], cwd=repo_dir, dry_run=dry_run)
    _run(["git", "commit", "-m", message], cwd=repo_dir, dry_run=dry_run)
    _run(["git", "push"], cwd=repo_dir, dry_run=dry_run)
    if not dry_run:
        _verify_push(repo_dir)
    return {"repo": str(repo_dir), "status": "pushed", "changed": n}


# ── help-guides subset ─────────────────────────────────────────────────────

def _frontmatter_type(path: Path) -> str:
    text = path.read_text()
    if not text.startswith("---"):
        return ""
    import yaml

    fm = yaml.safe_load(text.split("---", 2)[1]) or {}
    return fm.get("type", "")


def _article_slug(path: Path) -> str:
    """Frontmatter slug (the real identity), falling back to the filename."""
    text = path.read_text()
    if not text.startswith("---"):
        return path.stem
    import yaml

    try:
        fm = yaml.safe_load(text.split("---", 2)[1]) or {}
    except Exception:  # noqa: BLE001 — unparsable frontmatter: use filename
        return path.stem
    return fm.get("slug") or path.stem


def build_help_guides_subset(knowledge_dir, staging_dir, dry_run: bool = False) -> dict:
    """Collision-check + copy help/process articles + regenerate README."""
    src = Path(knowledge_dir) / BUNDLES_REL
    help_files = [f for f in sorted(src.glob("*.md")) if _frontmatter_type(f) == "help"]
    process_files = [f for f in sorted(src.glob("*.md")) if _frontmatter_type(f) == "process"]
    help_slugs = {_article_slug(f) for f in help_files}
    proc_slugs = {_article_slug(f) for f in process_files}
    overlap = help_slugs & proc_slugs
    if overlap:
        raise RepoSyncError(
            f"help/process slug collision ({len(overlap)}): {sorted(overlap)[:5]}")

    staging = Path(staging_dir)
    if not dry_run:
        staging.mkdir(parents=True, exist_ok=True)
        for f in help_files + process_files:
            (staging / f.name).write_text(f.read_text())
        _write_readme(staging, help_files + process_files)
    print(f"  subset: {len(help_files)} help + {len(process_files)} process "
          f"= {len(help_files) + len(process_files)} articles")
    return {"help": len(help_files), "process": len(process_files)}


def _write_readme(staging: Path, files: list) -> None:
    """Regenerate README index from frontmatter (title/slug/summary)."""
    import yaml

    rows = []
    for f in sorted(files):
        fm = yaml.safe_load(f.read_text().split("---", 2)[1]) or {}
        rows.append({
            "title": fm.get("title", f.stem),
            "type": fm.get("type", ""),
            "slug": fm.get("slug", f.stem),
            "summary": (fm.get("summary") or "").replace("\n", " ")[:120],
        })
    lines = ["# AI-KOS Help & Process Guides",
             "",
             f"Subset of the AI-KOS knowledge base ({len(rows)} articles).",
             "",
             "| Title | Type | Slug | Summary |",
             "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['title']} | {r['type']} | {r['slug']} | {r['summary']} |")
    (staging / "README.md").write_text("\n".join(lines) + "\n")


def sync_help_guides(knowledge_dir, guides_dir=None, message: str = "",
                     dry_run: bool = False) -> dict:
    """Clone-if-missing, rebuild the subset, commit, push, verify."""
    guides = Path(guides_dir) if guides_dir else HELP_GUIDES_DIR_DEFAULT
    if not (guides / ".git").exists():
        print(f"{guides}: not present — cloning")
        _run(["git", "clone", HELP_GUIDES_URL, str(guides)], dry_run=dry_run)
    build_help_guides_subset(knowledge_dir, guides, dry_run=dry_run)
    return sync_repo(guides, message or f"docs: help-guides refresh {date.today().isoformat()}",
                     dry_run=dry_run)


# ── master ─────────────────────────────────────────────────────────────────

def repo_sync(code_dir=None, message: Optional[str] = None,
              include_help_guides: bool = False, dry_run: bool = False) -> dict:
    """Sync the code repo + nested knowledge vault (+ help-guides on request)."""
    code = Path(code_dir) if code_dir else Path.cwd()
    today = date.today().isoformat()
    results = [
        sync_repo(code, message or f"chore: sync {today}", dry_run=dry_run),
    ]
    knowledge = code / "knowledge"
    if (knowledge / ".git").exists():
        results.append(sync_repo(knowledge, message or f"docs: KB sync {today}",
                                 dry_run=dry_run))
    else:
        results.append({"repo": str(knowledge), "status": "skipped",
                        "reason": "no nested knowledge repo"})
    if include_help_guides:
        results.append(sync_help_guides(knowledge, message=message or "", dry_run=dry_run))
    return {"results": results}


# ── CLI ────────────────────────────────────────────────────────────────────

def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(prog="repo-sync",
                                description="Stage, commit, push, verify the AI-KOS repos")
    p.add_argument("--dry-run", action="store_true", help="preview every command")
    p.add_argument("-m", "--message", default=None, help="commit message (all repos)")
    p.add_argument("--help-guides", action="store_true",
                   help="also rebuild + push the help-guides subset repo")
    p.add_argument("--code-dir", default=None, help="code repo dir (default: cwd)")
    args = p.parse_args(argv)

    try:
        result = repo_sync(code_dir=args.code_dir, message=args.message,
                           include_help_guides=args.help_guides, dry_run=args.dry_run)
    except RepoSyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    import json

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
