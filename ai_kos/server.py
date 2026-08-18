"""AI-KOS Dashboard — single-command Flask frontend for the knowledge base.

Usage:
    ai-kos serve          # starts on http://localhost:5173
    ai_kos/server.py      # direct run

Pages:
    /               Dashboard (stats, recent articles, pending tasks, backend distribution)
    /articles       Search + browse all articles
    /articles/<slug> Read a single article
    /tasks          Task manager with CRUD + article attachments
    /files          Inbox/archive/projects/rejected file listing
    /graph          Knowledge graph (vis-network)
    /datasets       SQL/JSON-backed dataset articles
    /datasets/<slug> Browse dataset rows
    /graphs         Graph-backed articles
    /graphs/<slug>  Graph visualization + traversal
    /blobs          Blob-backed articles with file metadata
    /api/graph-data JSON endpoint for knowledge graph
    /api/graph/<slug> JSON endpoint for individual graph data
"""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, jsonify

# Ensure ai_kos is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__,
    template_folder=str(Path(__file__).parent / 'templates'),
    static_folder=str(Path(__file__).parent / 'static'))

# Article render cache — slug → rendered HTML dict
_article_cache: dict = {}


@app.context_processor
def inject_article_count():
    """Make article count available in every template."""
    from ai_kos.articles import _get_index
    return {"article_count": len(_get_index().slugs)}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _human_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _article_list_for_template(articles):
    """Convert article list to a template-friendly format with all sortable fields."""
    result = []
    for a in articles:
        result.append({
            "slug": a.get("slug", ""),
            "title": a.get("title", ""),
            "type": a.get("type", ""),
            "summary": a.get("summary", ""),
            "keywords": a.get("keywords", []),
            "lifecycle": a.get("lifecycle", "current"),
            "doc_type": a.get("doc_type"),
            "link_count": a.get("link_count", 0),
            "retrieval_count": a.get("retrieval_count", 0),
            "updated_at": str(a.get("updated_at", "")),
            "created_at": str(a.get("created_at", "")),
            "next_review_at": str(a.get("next_review_at", "")),
        })
    return result


def _read_article_markdown(slug):
    """Read an article and return frontmatter + rendered HTML for rendering. Cached."""
    global _article_cache
    if slug in _article_cache:
        return _article_cache[slug]

    from ai_kos.articles import read_article
    article = read_article(slug)
    if not article:
        _article_cache[slug] = None
        return None
    fm = article.get("frontmatter", {})
    body = article.get("body", "")

    # Escape ALL article-controlled text FIRST so nothing in the body can
    # inject HTML/JS. Only the structural tags we generate below (and the
    # hrefs built from already-escaped slugs/URLs) are added afterwards,
    # which keeps `body_html|safe` in the template safe.
    from markupsafe import escape
    body = escape(body)

    # Convert wikilinks [[slug]] to links (slug text is already escaped)
    import re
    body = re.sub(r'\[\[([^\]]+)\]\]', r'<a href="/articles/\1">\1</a>', body)
    body = re.sub(r'(https?://\S+)', r'<a href="\1" target="_blank">\1</a>', body)
    # Simple markdown → HTML
    lines = body.strip().split('\n')
    html_parts = []
    in_list = False
    for line in lines:
        if line.startswith('## '):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('# '):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('- '):
            if not in_list:
                html_parts.append('<ul>')
                in_list = True
            html_parts.append(f'<li>{line[2:]}</li>')
        elif line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            if not in_list:
                html_parts.append('<ol>')
                in_list = True
            html_parts.append(f'<li>{line[line.index(". ")+2:]}</li>')
        else:
            if in_list:
                html_parts.append('</ul>' if '<ul>' in html_parts[-2:] else '</ol>')
                in_list = False
            if line.strip():
                html_parts.append(f'<p>{line}</p>')
    if in_list:
        html_parts.append('</ul>')
    result = {"frontmatter": fm, "body_html": '\n'.join(html_parts)}
    _article_cache[slug] = result
    return result


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    from ai_kos.articles import stats as kb_stats, list_articles
    from ai_kos.tasks import TaskManager

    st = kb_stats()
    tm = TaskManager()
    pending_tasks = tm.list_tasks(status="pending", limit=10)

    recent = list_articles()
    def _sort_key(a):
        ua = a.get("updated_at", "")
        return str(ua)
    recent.sort(key=_sort_key, reverse=True)
    recent = recent[:10]

    task_list = []
    for t in pending_tasks:
        from dataclasses import asdict
        task_list.append(asdict(t))

    # Count backends
    all_articles = list_articles()
    backend_counts = {}
    for a in all_articles:
        be = a.get("backend", "md")
        backend_counts[be] = backend_counts.get(be, 0) + 1

    return render_template("dashboard.html",
        stats=st,
        recent_articles=_article_list_for_template(recent),
        pending_tasks=task_list,
        backends=backend_counts,
        page="dashboard")


@app.route("/articles")
def articles_list():
    from ai_kos.articles import list_articles
    article_type = request.args.get("type")
    articles = list_articles(article_type=article_type if article_type else None)
    return render_template("articles.html",
        articles=_article_list_for_template(articles),
        article_type=article_type,
        page="articles")


@app.route("/articles/<slug>")
def article_view(slug):
    article = _read_article_markdown(slug)
    if not article:
        return render_template("article.html", article=None, slug=slug, page="articles"), 404
    return render_template("article.html", article=article, slug=slug, page="articles")


@app.route("/tasks", methods=["GET", "POST"])
def tasks_page():
    from ai_kos.tasks import TaskManager
    from dataclasses import asdict
    tm = TaskManager()

    if request.method == "POST":
        action = request.form.get("action")
        task_id = int(request.form.get("task_id", 0))
        if action == "create":
            title = request.form.get("title", "").strip()
            slugs_raw = request.form.get("article_slugs", "")
            slugs = [s.strip() for s in slugs_raw.split(",") if s.strip()] if slugs_raw else []
            if not title:
                pass
            elif not slugs:
                pass
            else:
                tags_raw = request.form.get("tags", "")
                images_raw = request.form.get("image_paths", "")
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None
                images = [i.strip() for i in images_raw.split(",") if i.strip()] if images_raw else None
                tm.create(
                    title=title,
                    description=request.form.get("description", ""),
                    urgency=request.form.get("urgency", "green"),
                    priority=int(request.form.get("priority", 0)),
                    tags=tags,
                    article_slugs=slugs,
                    data_summary=request.form.get("data_summary", ""),
                    image_paths=images,
                    project_slug=request.form.get("project_slug") or None,
                )
        elif action == "advance":
            try:
                tm.advance(task_id)
            except ValueError:
                pass
        elif action == "block":
            try:
                tm.block(task_id)
            except ValueError:
                pass
        elif action == "unblock":
            try:
                tm.set_status(task_id, "research")
            except ValueError:
                pass
        elif action == "delete":
            tm.delete(task_id)
        return redirect(url_for("tasks_page"))

    status = request.args.get("status")
    urgency_filter = request.args.get("urgency")
    project_filter = request.args.get("project")
    tasks = tm.list_tasks(status=status if status else None,
                          urgency=urgency_filter if urgency_filter else None,
                          project_slug=project_filter if project_filter else None,
                          limit=100)
    projects = tm.list_projects()
    return render_template("tasks.html",
        tasks=[asdict(t) for t in tasks],
        status=status,
        urgency_filter=urgency_filter,
        project_filter=project_filter,
        projects=projects,
        page="tasks")


@app.route("/files")
@app.route("/inbox")
def files_page():
    from ai_kos.config import get
    tab = request.args.get("tab", "inbox")
    dirs = {
        "inbox": Path(get("paths", "inbox_dir", default="inbox")),
        "archive": Path(get("paths", "archive_dir", default="archive")),
        "projects": Path(get("paths", "projects_dir", default="projects")),
        "rejected": Path(get("paths", "rejected_dir", default="rejected")),
    }
    current_dir = dirs.get(tab, dirs["inbox"])
    files = []
    if current_dir.exists():
        for f in sorted(current_dir.iterdir()):
            if f.is_file():
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "size": stat.st_size,
                    "size_human": _human_size(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "ext": f.suffix.lower(),
                })
    return render_template("files.html",
        files=files, tab=tab, dirs={k: str(v) for k, v in dirs.items()},
        current_path=str(current_dir), page="files")


@app.route("/graph")
def graph_page():
    return render_template("graph.html", page="graph")


@app.route("/api/graph-data")
def graph_data():
    """Serve graph data from the in-memory article index (fast, no disk scan)."""
    from ai_kos.articles import _get_index
    idx = _get_index()
    nodes = []
    slug_to_idx = {}
    for slug, fm in idx._frontmatter.items():
        slug_to_idx[slug] = len(nodes)
        nodes.append({
            "id": slug,
            "title": fm.get("title", slug),
            "type": fm.get("type", "base"),
            "keywords": fm.get("keywords", []),
            "summary": fm.get("summary", ""),
            "lifecycle": fm.get("lifecycle", "current"),
            "doc_type": fm.get("doc_type"),
            "linkCount": fm.get("link_count", 0),
        })

    edges = []
    seen = set()
    for slug, fm in idx._frontmatter.items():
        source_kw = set(fm.get("keywords", []))
        for rel in fm.get("related", []):
            target = rel.get("slug", rel) if isinstance(rel, dict) else rel
            if slug in slug_to_idx and target in slug_to_idx:
                key = tuple(sorted([slug, target]))
                if key not in seen:
                    seen.add(key)
                    target_kw = set(idx._frontmatter.get(target, {}).get("keywords", []))
                    weight = len(source_kw & target_kw)
                    edge_type = rel.get("type", "see-also") if isinstance(rel, dict) else "see-also"
                    edges.append({
                        "source": slug, "target": target,
                        "weight": max(weight, 1), "type": edge_type,
                    })

    by_type = {}
    for n in nodes:
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1

    return jsonify({
        "nodes": nodes, "edges": edges,
        "stats": {"total_nodes": len(nodes), "total_edges": len(edges), "by_type": by_type}
    })


# ── Backend pages ───────────────────────────────────────────────────────────

@app.route("/datasets")
def datasets_page():
    """List all SQL/JSON-backed dataset articles with row counts and columns."""
    from ai_kos.articles import list_articles
    from ai_kos import datasets as ds
    all_articles = list_articles()
    sql_articles = [a for a in all_articles if a.get("backend") in ("sql", "json")]
    results = []
    for a in sql_articles:
        dref = a.get("dataset", {})
        db_path = dref.get("db", "")
        table_name = dref.get("table", "")
        st = ds.table_stats(db_path, table_name) if db_path and table_name else None
        results.append({
            "slug": a["slug"], "title": a["title"], "type": a.get("type", ""),
            "backend": a.get("backend", "sql"), "summary": a.get("summary", ""),
            "database": db_path, "table": table_name,
            "row_count": st["row_count"] if st else 0,
            "columns": st["columns"] if st else [],
        })
    return render_template("datasets.html", datasets=results, page="datasets")


@app.route("/datasets/<slug>")
def dataset_view(slug):
    """Browse rows of a specific SQL-backed dataset."""
    from ai_kos.articles import read_article
    from ai_kos import datasets as ds
    article = read_article(slug)
    if not article:
        return render_template("dataset_view.html", dataset=None, slug=slug, page="datasets"), 404
    dref = article.get("dataset", {})
    db_path = dref.get("db", "")
    table_name = dref.get("table", "")
    backend = article.get("backend", "sql")

    page_num = int(request.args.get("page", 1))
    per_page = 50
    offset = (page_num - 1) * per_page

    rows = []
    columns = []
    total_rows = 0

    if db_path and table_name and backend == "sql":
        st = ds.table_stats(db_path, table_name)
        if st:
            total_rows = st.get("row_count", 0)
            columns = st.get("columns", [])
        col_names = [c["name"] for c in columns]
        if col_names:
            rows = ds.query_table(db_path,
                f'SELECT * FROM "{table_name}" LIMIT {per_page} OFFSET {offset}')

    total_pages = max(1, (total_rows + per_page - 1) // per_page)
    return render_template("dataset_view.html",
        dataset={"slug": slug, "title": article.get("title", slug),
                 "backend": backend, "table": table_name,
                 "row_count": total_rows, "columns": columns},
        rows=rows, page_num=page_num, total_pages=total_pages, page="datasets")


@app.route("/graphs")
def graphs_page():
    """List all graph-backed articles with node/edge counts."""
    from ai_kos.articles import list_articles
    from ai_kos.graphs import graph_stats
    all_articles = list_articles()
    graph_articles = [a for a in all_articles if a.get("backend") == "graph"]
    results = []
    for a in graph_articles:
        dref = a.get("dataset", {})
        db_path = dref.get("db", "")
        table_name = dref.get("table", "")
        gr = a.get("graph", {})
        try:
            gs = graph_stats(db_path, table_name)
            node_count = gs["node_count"]
            edge_count = gs["edge_count"]
        except Exception:
            node_count = gr.get("node_count", 0)
            edge_count = gr.get("edge_count", 0)
        results.append({
            "slug": a["slug"], "title": a["title"], "type": a.get("type", ""),
            "summary": a.get("summary", ""),
            "node_count": node_count, "edge_count": edge_count,
            "directed": gr.get("directed", True),
        })
    return render_template("graphs.html", graphs=results, page="graphs")


@app.route("/graphs/<slug>")
def graph_view(slug):
    """Visualize and explore a graph-backed article."""
    from ai_kos.articles import read_article
    article = read_article(slug)
    if not article or article.get("backend") != "graph":
        return render_template("graph_view.html", graph_meta=None, slug=slug, page="graphs"), 404
    return render_template("graph_view.html",
        graph_meta={"slug": slug, "title": article.get("title", slug),
                    "summary": article.get("summary", "")},
        page="graphs")


@app.route("/api/graph/<slug>")
def api_graph_data(slug):
    """Serve graph data as vis-network JSON for a graph-backed article."""
    from ai_kos.articles import read_article
    from ai_kos.graphs import export_vis_network
    article = read_article(slug)
    if not article or article.get("backend") != "graph":
        return jsonify({"error": "Not a graph article"}), 404
    dref = article.get("dataset", {})
    db_path = dref.get("db", "datasets/ai-kos.db")
    table_name = dref.get("table", slug.replace("-", "_"))
    try:
        data = export_vis_network(db_path, table_name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(data)


@app.route("/blobs")
def blobs_page():
    """List all blob-backed articles with file metadata."""
    from ai_kos.articles import list_articles
    all_articles = list_articles()
    blob_articles = [a for a in all_articles if a.get("backend") == "blob"]
    results = []
    for a in blob_articles:
        blob = a.get("blob", {})
        results.append({
            "slug": a["slug"], "title": a["title"], "type": a.get("type", ""),
            "summary": a.get("summary", ""),
            "mime_type": blob.get("mime_type", "unknown"),
            "size_bytes": blob.get("size_bytes", 0),
            "size_human": _human_size(blob.get("size_bytes", 0)),
            "path": blob.get("path", ""),
            "extracted_text": blob.get("extracted_text", ""),
        })
    return render_template("blobs.html", blobs=results, page="blobs")


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    import webbrowser, threading
    # Always run from project root so paths resolve correctly
    os.chdir(str(Path(__file__).parent.parent))
    host = "127.0.0.1"
    port = 5173
    print(f"\n  AI-KOS Dashboard → http://{host}:{port}\n")
    # Open browser after a short delay
    threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
