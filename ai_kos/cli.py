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
    result = link_all(min_overlap=args.min_overlap)
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
                dst = projects_dir / name
                if dst.exists(): shutil.rmtree(str(dst))
                shutil.move(str(item), str(dst))
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
    import shutil
    if dst.exists():
        if dst.is_dir(): shutil.rmtree(str(dst))
        else: dst.unlink()
    shutil.move(str(src), str(dst))

def _has_file(directory, filename):
    return (Path(directory) / filename).exists()

def cmd_research(args):
    """Generate a structured research plan."""
    from ai_kos.deep_research import plan_research
    from dataclasses import asdict
    plan = plan_research(args.question)
    print(json.dumps(asdict(plan), indent=2, default=str))

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
    pl.add_argument("--min-overlap", type=int, default=None, help="Minimum shared keywords to create a link (default: from config, 2)")
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

    args = p.parse_args()
    if not args.cmd: p.print_help(); sys.exit(1)
    args.func(args)

if __name__ == "__main__": main()
