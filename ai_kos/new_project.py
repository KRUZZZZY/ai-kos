"""AI-KOS new-project — scaffold a working repo skeleton from a mission article.

Reads a mission article by slug, extracts purpose + success criteria from the
BODY markdown (reusing ai_kos.atq body-section helpers), and scaffolds a
minimal Python repo under projects/<slug>/ with one task per success criterion.

Usage (CLI):
    ai-kos new-project <mission-slug> [--force]

Or as a module:
    from ai_kos.new_project import scaffold
    result = scaffold("atq-agent-task-queue-mission")
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from ai_kos.atq import _body_criteria, _body_section, _mission_article
from ai_kos.config import get

# Marker written into .hermes.md so --force can tell our scaffolds apart from
# real pre-existing project directories before deleting anything.
SCAFFOLD_MARKER = "ai-kos-scaffold"


def _projects_dir() -> Path:
    return Path(get("paths", "projects_dir", default="projects"))


def _package_name(slug: str) -> str:
    """Normalize a slug into a valid Python package name (hyphens -> underscores)."""
    return slug.replace("-", "_")


def _is_scaffold(project_dir: Path) -> bool:
    """True if project_dir looks like one we generated (safe to overwrite)."""
    marker = project_dir / ".hermes.md"
    if not marker.exists():
        return False
    try:
        return SCAFFOLD_MARKER in marker.read_text()
    except OSError:
        return False


# ── file writers ────────────────────────────────────────────────────────────

def _write_readme(project_dir: Path, title: str, purpose: str, criteria: List[str]) -> None:
    lines = ["# " + title, "", "## Purpose", "", purpose or "(no purpose section)", "", "## Success Criteria", ""]
    if criteria:
        for i, c in enumerate(criteria, 1):
            lines.append(f"{i}. {c}")
    else:
        lines.append("(none)")
    lines += ["", "## Development", "", "```bash", "python3 -m pytest tests/ -q", "```", ""]
    (project_dir / "README.md").write_text("\n".join(lines))


def _write_pyproject(project_dir: Path, slug: str, title: str) -> None:
    content = (
        "[build-system]\n"
        'requires = ["setuptools>=61.0"]\n'
        'build-backend = "setuptools.build_meta"\n'
        "\n"
        "[project]\n"
        f'name = "{slug}"\n'
        'version = "0.1.0"\n'
        f'description = "{title}"\n'
        'requires-python = ">=3.10"\n'
        "dependencies = []\n"
        "\n"
        "[project.optional-dependencies]\n"
        'dev = ["pytest"]\n'
        "\n"
        "[tool.setuptools.packages.find]\n"
        'where = ["src"]\n'
        "\n"
        "[tool.pytest.ini_options]\n"
        'testpaths = ["tests"]\n'
    )
    (project_dir / "pyproject.toml").write_text(content)


def _write_package_init(src_dir: Path, slug: str, title: str, purpose: str) -> None:
    doc = f'"""{title} — scaffolded from mission {slug}.\n\n{purpose}\n"""\n'
    (src_dir / "__init__.py").write_text(doc)


def _write_smoke_test(tests_dir: Path, pkg: str, slug: str) -> None:
    content = (
        f'"""Smoke test for {slug} — verifies the package imports."""\n'
        "\n"
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        'sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))\n'
        "\n"
        f"import {pkg}  # noqa: E402\n"
        "\n"
        "\n"
        "def test_package_imports():\n"
        f'    assert {pkg}.__name__ == "{pkg}"\n'
    )
    (tests_dir / "test_smoke.py").write_text(content)


_GITIGNORE = (
    "# Byte-compiled / optimized / DLL files\n"
    "__pycache__/\n"
    "*.py[cod]\n"
    "*$py.class\n"
    "\n"
    "# Distribution / packaging\n"
    "build/\n"
    "dist/\n"
    "*.egg-info/\n"
    "\n"
    "# Virtual environments\n"
    ".venv/\n"
    "venv/\n"
    "\n"
    "# Test / coverage\n"
    ".pytest_cache/\n"
    ".coverage\n"
    "htmlcov/\n"
    "\n"
    "# Editor\n"
    ".vscode/\n"
    ".idea/\n"
    "*.swp\n"
)


def _write_gitignore(project_dir: Path) -> None:
    (project_dir / ".gitignore").write_text(_GITIGNORE)


def _write_hermes_md(project_dir: Path, slug: str, title: str, purpose: str) -> None:
    content = (
        f"<!-- {SCAFFOLD_MARKER} -->\n"
        "\n"
        f"# {title}\n"
        "\n"
        f"**Mission slug**: `{slug}`\n"
        "\n"
        "## Purpose\n"
        f"{purpose or '(no purpose section)'}\n"
        "\n"
        "## Build / test commands\n"
        "```bash\n"
        "python3 -m pytest tests/ -q\n"
        "```\n"
        "\n"
        "## Notes\n"
        f"- Scaffolded by `ai-kos new-project {slug}`.\n"
    )
    (project_dir / ".hermes.md").write_text(content)


# ── scaffold ────────────────────────────────────────────────────────────────

def scaffold(mission_slug: str, force: bool = False) -> dict:
    """Scaffold a repo skeleton from a mission article and create per-criterion tasks.

    Raises ValueError if the article is missing or not a mission; FileExistsError
    if the project directory already exists (unless force=True).
    """
    art = _mission_article(mission_slug)
    slug = mission_slug
    title = art.get("title") or slug
    body = art.get("_body") or ""
    purpose = _body_section(body, "Purpose")
    criteria = _body_criteria(body)

    project_dir = _projects_dir() / slug
    if project_dir.exists():
        if not force:
            raise FileExistsError(
                f"project already exists: {project_dir} (re-run with --force to overwrite)"
            )
        if not _is_scaffold(project_dir):
            raise FileExistsError(
                f"{project_dir} exists but is not an AI-KOS scaffold; "
                f"refusing to delete it. Remove it manually first."
            )
        shutil.rmtree(project_dir)

    pkg = _package_name(slug)
    src_dir = project_dir / "src" / pkg
    tests_dir = project_dir / "tests"
    src_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    _write_readme(project_dir, title, purpose, criteria)
    _write_pyproject(project_dir, slug, title)
    _write_package_init(src_dir, slug, title, purpose)
    _write_smoke_test(tests_dir, pkg, slug)
    _write_gitignore(project_dir)
    _write_hermes_md(project_dir, slug, title, purpose)

    tasks = _create_tasks(slug, title, criteria)

    files = [
        "README.md",
        "pyproject.toml",
        ".gitignore",
        ".hermes.md",
        f"src/{pkg}/__init__.py",
        "tests/test_smoke.py",
    ]

    return {
        "status": "created",
        "slug": slug,
        "title": title,
        "project_dir": str(project_dir),
        "package": pkg,
        "purpose": purpose,
        "success_criteria": criteria,
        "files": files,
        "tasks": [{"id": t.id, "title": t.title} for t in tasks],
    }


def _create_tasks(slug: str, title: str, criteria: List[str]) -> list:
    """Create one urgency-yellow task per success criterion."""
    from ai_kos.tasks import TaskManager

    tm = TaskManager()
    tasks = []
    for criterion in criteria:
        task = tm.create(
            title=f"[{slug}] {criterion}",
            description=f"Success criterion for mission {title!r}.",
            urgency="yellow",
            article_slugs=[slug],
            project_slug=slug,
        )
        tasks.append(task)
    return tasks
