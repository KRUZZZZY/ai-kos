"""AI-KOS CLI — knowledge database management."""

import sys, json, argparse

def cmd_ingest(args):
    from ai_kos.ingestion import extract
    print(json.dumps(extract(args.filepath), indent=2, default=str, ensure_ascii=False))

def cmd_create(args):
    from ai_kos.articles import create_article
    data = json.loads(sys.stdin.read()) if not args.data else json.loads(args.data)
    print(json.dumps(create_article(args.type, data), indent=2, default=str))

def cmd_search(args):
    from ai_kos.search import search, compare
    if args.compare:
        results = compare(args.compare, top_k=args.top_k)
        print(json.dumps({"compare_from": args.compare, "results": results}, indent=2, default=str))
        return
    results = search(args.query or "", top_k=args.top_k, article_type=args.type)
    print(json.dumps({"results": results, "total": len(results)}, indent=2, default=str))

def cmd_read(args):
    from ai_kos.articles import read_article
    print(json.dumps(read_article(args.slug), indent=2, default=str, ensure_ascii=False))

def cmd_link(args):
    from ai_kos.linker import link_all
    result = link_all(min_overlap=args.min_overlap, mode=args.mode)
    print(json.dumps(result, indent=2))

def cmd_list(args):
    from ai_kos.articles import list_articles
    articles = list_articles(article_type=args.type, keyword=args.keyword)
    print(json.dumps({"articles": articles, "count": len(articles)}, indent=2, default=str))

def cmd_graph(args):
    """Export graph data as JSON for visualization, or open Obsidian vault."""
    if args.obsidian:
        import subprocess
        vault_path = args.dir or "."
        subprocess.Popen(["obsidian", "open", f"--vault={vault_path}"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Opening Obsidian vault: {vault_path}")
        return

    from ai_kos.graph_data import export_graph_data
    data = export_graph_data(args.dir or "knowledge")
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Graph data written to {args.output} ({data['stats']['total_nodes']} nodes, {data['stats']['total_edges']} edges)")
    else:
        print(json.dumps(data, indent=2, default=str))

def cmd_info(args):
    from ai_kos.config import load
    from ai_kos.articles import list_articles
    from ai_kos.schemas import TEMPLATES
    from pathlib import Path
    cfg = load()
    articles = list_articles()
    by_type = {}
    for a in articles: by_type[a["type"]] = by_type.get(a["type"], 0) + 1
    print(f"AI-KOS v1.5.0")
    print(f"  Knowledge dir: {cfg['paths']['knowledge_dir']} ({len(articles)} articles)")
    for t, c in sorted(by_type.items()): print(f"    {t}: {c}")
    print(f"  Inbox: {len(list(Path(cfg['paths']['inbox_dir']).iterdir())) if Path(cfg['paths']['inbox_dir']).exists() else 0} files pending")
    print(f"  Archive: {cfg['paths']['archive_dir']}")
    print(f"  Projects: {cfg['paths']['projects_dir']}")
    print(f"  Rejected: {cfg['paths']['rejected_dir']}")
    print(f"  Templates: {len(TEMPLATES)} types")
    print(f"  Obsidian vault: ready (open with 'ai-kos graph --obsidian')")

def cmd_clean(args):
    """Move processed files out of inbox — archive ingested, reject build artifacts, move projects."""
    import shutil
    from pathlib import Path
    from ai_kos.config import get

    inbox = Path(get("paths", "inbox_dir", default="inbox"))
    archive_dir = Path(get("paths", "archive_dir", default="archive"))
    rejected_dir = Path(get("paths", "rejected_dir", default="rejected"))
    projects_dir = Path(get("paths", "projects_dir", default="projects"))

    for d in [archive_dir, rejected_dir, projects_dir]: d.mkdir(exist_ok=True)

    stats = {"archived": 0, "rejected": 0, "projects": 0, "errors": 0}

    for item in sorted(inbox.iterdir()):
        try:
            name = item.name
            ext = item.suffix.lower()

            # Reject: build artifacts, caches, venvs, binaries
            if any(p in name.lower() for p in ['.gradle', 'build/', '.venv', '__pycache__', 'node_modules']):
                _safe_move(item, rejected_dir / name)
                stats["rejected"] += 1
            elif ext in ('.jar', '.zip', '.tar', '.bin', '.lock', '.pyc', '.sqlite3', '.db', '.log', '.html'):
                _safe_move(item, rejected_dir / name)
                stats["rejected"] += 1
            # Project: directories with source code or git repos
            elif item.is_dir() and (_has_file(item, '.git') or _has_file(item, 'setup.py') or _has_file(item, 'pyproject.toml') or _has_file(item, 'build.gradle') or _has_file(item, 'README.md')):
                _safe_move(item, projects_dir / name)
                stats["projects"] += 1
            # Archive: markdown/text — assume ingested
            elif ext in ('.md', '.txt', '.rst', '.org'):
                _safe_move(item, archive_dir / name)
                stats["archived"] += 1
            else:
                _safe_move(item, rejected_dir / name)
                stats["rejected"] += 1
        except Exception as e:
            print(f"  Error moving {name}: {e}")
            stats["errors"] += 1

    print(f"Inbox cleaned: {stats['archived']} archived, {stats['projects']} projects, {stats['rejected']} rejected, {stats['errors']} errors")

def _safe_move(src, dst):
    """Move src to dst without destroying an existing same-named destination.

    If dst already exists, the file/dir is moved to a `name-1.ext`-style
    suffixed destination instead of overwriting it. Never rmtree's a
    non-empty same-named target.
    """
    import shutil
    if not dst.exists():
        shutil.move(str(src), str(dst))
        return
    for i in range(1, 10000):
        candidate = dst.with_name(f"{dst.stem}-{i}{dst.suffix}")
        if not candidate.exists():
            shutil.move(str(src), str(candidate))
            return
    raise FileExistsError(f"no free destination name for {dst}")

def _has_file(directory, filename):
    return (Path(directory) / filename).exists()

def cmd_research(args):
    """Generate a structured research plan."""
    from ai_kos.deep_research import plan_research
    from dataclasses import asdict
    plan = plan_research(args.question)
    print(json.dumps(asdict(plan), indent=2, default=str))

def cmd_migrate(args):
    """Run schema migrations on all articles."""
    from ai_kos.migrate import run_migrations
    result = run_migrations(dry_run=args.dry_run, tiers=args.tiers)
    print(json.dumps(result, indent=2, default=str))


def cmd_task_create(args):
    """Create a future task."""
    from ai_kos.tasks import TaskManager
    from dataclasses import asdict
    tm = TaskManager()
    task = tm.create(
        title=args.title,
        description=args.description or "",
        priority=args.priority,
        due_date=args.due,
        article_slugs=args.articles.split(",") if args.articles else None,
    )
    print(json.dumps(asdict(task), indent=2, default=str))


def cmd_task_list(args):
    """List future tasks."""
    from ai_kos.tasks import TaskManager
    from dataclasses import asdict
    tm = TaskManager()
    tasks = tm.list_tasks(status=args.status, limit=args.limit)
    print(json.dumps({"tasks": [asdict(t) for t in tasks], "total": len(tasks)}, indent=2, default=str))


def cmd_task_complete(args):
    """Mark a future task as completed."""
    from ai_kos.tasks import TaskManager
    from dataclasses import asdict
    tm = TaskManager()
    try:
        task = tm.complete(args.task_id)
        print(json.dumps(asdict(task), indent=2, default=str))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_task_delete(args):
    """Delete a future task."""
    from ai_kos.tasks import TaskManager
    tm = TaskManager()
    tm.delete(args.task_id)
    print(json.dumps({"status": "deleted", "task_id": args.task_id}))


def cmd_atq(args):
    """Agent Task Queue bridge: submit/tick/status/report."""
    from ai_kos.atq import main as atq_main
    import sys as _sys

    _sys.exit(atq_main([args.atq_cmd] + (args.atq_args or [])))


def cmd_serve(args):
    """Start the AI-KOS web dashboard."""
    from ai_kos.server import main
    main()


def cmd_docaudit(args):
    """Audit module-by-module KB documentation coverage."""
    from ai_kos.docaudit import audit, render_report
    result = audit()
    print(render_report(result, json_out=args.json))


def cmd_new_project(args):
    """Scaffold a repo skeleton from a mission article + create per-criterion tasks."""
    from ai_kos.new_project import scaffold
    try:
        result = scaffold(args.mission_slug, force=args.force)
    except (ValueError, FileExistsError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2, default=str))


def cmd_repo_sync(args):
    """Stage, commit, push + verify the GitHub repos (code + knowledge [+ help-guides])."""
    from ai_kos.repo_sync import RepoSyncError, repo_sync
    try:
        result = repo_sync(code_dir=args.code_dir, message=args.message,
                           include_help_guides=args.help_guides, dry_run=args.dry_run)
    except RepoSyncError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2, default=str))


def main():
    p = argparse.ArgumentParser("ai-kos", description="AI Knowledge Operating System")
    sub = p.add_subparsers(dest="cmd")

    pi = sub.add_parser("ingest", help="Extract text from any file")
    pi.add_argument("filepath"); pi.set_defaults(func=cmd_ingest)

    pc = sub.add_parser("create", help="Create article from JSON (stdin or --data)")
    pc.add_argument("type", choices=["base","process","plan","help","research-note","note","mission"])
    pc.add_argument("--data"); pc.set_defaults(func=cmd_create)

    ps = sub.add_parser("search", help="Search knowledge base by full-text or compare similarity")
    ps.add_argument("query", nargs="?", help="Search query (or use --compare for similarity)")
    ps.add_argument("-t","--type", help="Filter by article type")
    ps.add_argument("-k","--top-k",type=int,default=10)
    ps.add_argument("--compare", help="Find articles similar to this slug")
    ps.set_defaults(func=cmd_search)

    pr = sub.add_parser("read", help="Read an article by slug")
    pr.add_argument("slug"); pr.set_defaults(func=cmd_read)

    pl = sub.add_parser("link", help="Run auto-linker")
    pl.add_argument("--min-overlap", type=int, default=None, help="Minimum shared keywords to create a link (count mode only; default: from config, 2)")
    pl.add_argument("--mode", choices=["similarity", "idf", "count"], default=None, help="Linking mode override (default: from config linking.mode)")
    pl.set_defaults(func=cmd_link)

    pls = sub.add_parser("list", help="List articles")
    pls.add_argument("-t","--type"); pls.add_argument("--keyword"); pls.set_defaults(func=cmd_list)

    pg = sub.add_parser("graph", help="Export graph data or open Obsidian vault")
    pg.add_argument("-d","--dir", default="knowledge", help="Knowledge directory")
    pg.add_argument("-o","--output", help="Write graph JSON to file")
    pg.add_argument("--obsidian", action="store_true", help="Open knowledge/ as Obsidian vault")
    pg.set_defaults(func=cmd_graph)

    pif = sub.add_parser("info", help="System info"); pif.set_defaults(func=cmd_info)

    pcl = sub.add_parser("clean", help="Clean inbox"); pcl.set_defaults(func=cmd_clean)

    pres = sub.add_parser("research", help="Generate a deep research plan from a question")
    pres.add_argument("question", help="The research question"); pres.set_defaults(func=cmd_research)

    pm = sub.add_parser("migrate", help="Run schema migrations on all articles")
    pm.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    pm.add_argument("--tiers", action="store_true", help="Also run the two-pass keyword-tier migration (subject_keywords split + related_pinned backfill)")
    pm.set_defaults(func=cmd_migrate)

    pt = sub.add_parser("task", help="Manage future tasks")
    task_sub = pt.add_subparsers(dest="task_cmd")

    ptc = task_sub.add_parser("create", help="Create a future task")
    ptc.add_argument("title", help="Task title")
    ptc.add_argument("-d", "--description", help="Task description")
    ptc.add_argument("-p", "--priority", type=int, default=0, help="Priority (lower=higher, 0 is default)")
    ptc.add_argument("--due", help="Due date (YYYY-MM-DD)")
    ptc.add_argument("-a", "--articles", help="Comma-separated article slugs to attach")
    ptc.set_defaults(func=cmd_task_create)

    ptl = task_sub.add_parser("list", help="List tasks")
    ptl.add_argument("-s", "--status", choices=["pending", "in_progress", "completed", "cancelled"])
    ptl.add_argument("-n", "--limit", type=int, default=50)
    ptl.set_defaults(func=cmd_task_list)

    ptcomp = task_sub.add_parser("complete", help="Mark a task as completed")
    ptcomp.add_argument("task_id", type=int, help="Task ID")
    ptcomp.set_defaults(func=cmd_task_complete)

    ptdel = task_sub.add_parser("delete", help="Delete a task")
    ptdel.add_argument("task_id", type=int, help="Task ID")
    ptdel.set_defaults(func=cmd_task_delete)

    psv = sub.add_parser("serve", help="Start the AI-KOS dashboard")
    psv.set_defaults(func=cmd_serve)

    pa = sub.add_parser("atq", help="Agent Task Queue bridge (submit/tick/status/report)")
    pa.add_argument("atq_cmd", choices=["submit", "tick", "status", "report"],
                    help="atq subcommand")
    pa.add_argument("atq_args", nargs=argparse.REMAINDER,
                    help="args passed to the atq subcommand")
    pa.set_defaults(func=cmd_atq)

    pda = sub.add_parser("doc-audit", help="Audit module-by-module KB documentation coverage")
    pda.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    pda.set_defaults(func=cmd_docaudit)

    pnp = sub.add_parser("new-project", help="Scaffold a repo skeleton from a mission article")
    pnp.add_argument("mission_slug", help="Mission article slug")
    pnp.add_argument("--force", action="store_true", help="Overwrite an existing scaffold")
    pnp.set_defaults(func=cmd_new_project)

    prs = sub.add_parser("repo-sync", help="Stage, commit, push + verify the GitHub repos (code + knowledge [+ help-guides])")
    prs.add_argument("--dry-run", action="store_true", help="Preview every command without executing")
    prs.add_argument("-m", "--message", default=None, help="Commit message (applies to all repos)")
    prs.add_argument("--help-guides", action="store_true",
                     help="Also rebuild + push the ai-kos-help-guides subset repo")
    prs.add_argument("--code-dir", default=None, help="Code repo dir (default: cwd)")
    prs.set_defaults(func=cmd_repo_sync)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)
    # Handle nested task subcommands
    if args.cmd == "task":
        if hasattr(args, "task_cmd") and args.task_cmd:
            args.func(args)
        else:
            pt.print_help()
            sys.exit(1)
    elif args.cmd == "atq":
        if not args.atq_cmd:
            pa.print_help()
            sys.exit(1)
        args.func(args)
    else:
        args.func(args)

if __name__ == "__main__": main()
