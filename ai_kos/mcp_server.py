"""AI-KOS MCP server — exposes full knowledge database to Hermes via MCP JSON-RPC.

v1.7: access/doc_type/lifecycle filtering, typed relations, usage signals.

All blocking I/O operations are offloaded to a thread pool via asyncio.to_thread().

Tools (35):
  Core (15): ai_kos_ingest, ai_kos_create, ai_kos_search, ai_kos_read, ai_kos_link,
  ai_kos_list, ai_kos_merge_candidates, ai_kos_templates, ai_kos_graph,
  ai_kos_compare, ai_kos_stats, ai_kos_clean
  Research (5): ai_kos_research_plan, ai_kos_research_persist, ai_kos_migrate,
  ai_kos_citation, ai_kos_batch_ingest
  Paper (3): ai_kos_compare_papers, ai_kos_promote_ready, ai_kos_reading_stats
  Tasks (4): ai_kos_task_create, ai_kos_task_list, ai_kos_task_complete, ai_kos_task_delete
  SQL Backend (4): ai_kos_datasets, ai_kos_query, ai_kos_ingest_csv, ai_kos_timeseries_stats
  Blob/JSON/Graph Backends (4): ai_kos_ingest_blob, ai_kos_ingest_json, ai_kos_ingest_graph
  Format Ingest (5): ai_kos_ingest_parquet, ai_kos_ingest_orc, ai_kos_ingest_sqlite, ai_kos_ingest_sql_dump
"""

import asyncio
import json
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-kos-mcp")

server = Server("ai-kos")

# ── Tool definitions ─────────────────────────────────────────────────────────

TOOLS = [
    types.Tool(
        name="ai_kos_ingest",
        description="Extract text from any file (.md, .txt, .pdf, .docx, .py, etc). Returns raw content + detected type + suggested article template. Use this first when adding new knowledge.",
        input_schema={"type": "object", "properties": {"filepath": {"type": "string", "description": "Absolute path to file"}}, "required": ["filepath"]},
    ),
    types.Tool(
        name="ai_kos_create",
        description="Create a new knowledge article. After ingesting a file, simplify the content using the appropriate template, then call this to persist it. The linker runs automatically.",
        input_schema={"type": "object", "properties": {"article_type": {"type": "string", "enum": ["base", "process", "plan", "help", "research-note", "note", "mission"], "description": "Article type — use the suggested_type from ai_kos_ingest"}, "data": {"type": "object", "description": "Full article data matching the template schema. Required: title, slug, keywords (3-8), summary, provenance, + type-specific fields"}}, "required": ["article_type", "data"]},
    ),
    types.Tool(
        name="ai_kos_search",
        description="Search knowledge base. Returns articles matching the query by keyword + semantic similarity. v1.7: filters by doc_type, lifecycle, and access level.",
        input_schema={"type": "object", "properties": {
            "query": {"type": "string", "description": "Search query"},
            "article_type": {"type": "string", "description": "Optional: filter by type (base/process/plan/help/research-note/note/mission)"},
            "doc_type": {"type": "string", "enum": ["tutorial", "how-to", "reference", "explanation"], "description": "Optional: Diátaxis consumption mode"},
            "lifecycle": {"type": "string", "enum": ["current", "superseded", "historical"], "description": "Optional: filter by lifecycle state"},
            "access": {"type": "string", "enum": ["public", "internal", "confidential"], "description": "Optional: only return articles at or below this sensitivity"},
            "top_k": {"type": "integer", "description": "Max results", "default": 10},
        }, "required": ["query"]},
    ),
    types.Tool(
        name="ai_kos_read",
        description="Read a full knowledge article by slug. Returns frontmatter + body. v1.7: bumps retrieval_count and last_accessed on every read.",
        input_schema={"type": "object", "properties": {"slug": {"type": "string", "description": "Article slug"}}, "required": ["slug"]},
    ),
    types.Tool(
        name="ai_kos_link",
        description="Run the auto-linker. Scans all articles and creates typed [[wikilinks]] between any pair sharing >=N keywords. Also reports merge candidates (>80% keyword overlap) and auto-sets lifecycle=superseded on losers.",
        input_schema={"type": "object", "properties": {"min_overlap": {"type": "integer", "description": "Minimum shared keywords to create a link. Default from config (2). Higher = fewer links (thicker). Lower = more links (weaker)."}}},
    ),
    types.Tool(
        name="ai_kos_list",
        description="List all knowledge articles. v1.7: filter by article_type, keyword, access, doc_type, lifecycle.",
        input_schema={"type": "object", "properties": {
            "article_type": {"type": "string", "description": "Filter by type"},
            "keyword": {"type": "string", "description": "Filter by keyword"},
            "access": {"type": "string", "enum": ["public", "internal", "confidential"], "description": "Filter by access level"},
            "doc_type": {"type": "string", "enum": ["tutorial", "how-to", "reference", "explanation"], "description": "Filter by Diátaxis doc_type"},
            "lifecycle": {"type": "string", "enum": ["current", "superseded", "historical"], "description": "Filter by lifecycle"},
        }},
    ),
    types.Tool(
        name="ai_kos_merge_candidates",
        description="Find articles with high keyword overlap with a given slug. Use before merging or updating to check for duplicates.",
        input_schema={"type": "object", "properties": {"slug": {"type": "string", "description": "Article slug to check against"}}, "required": ["slug"]},
    ),
    types.Tool(
        name="ai_kos_templates",
        description="Show all 7 article templates with their prompts. Use this when you need to know what fields each article type requires.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_graph",
        description="Export the knowledge graph as JSON (nodes + edges). v1.7: nodes include lifecycle, doc_type; edges include relation type.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_compare",
        description="Find the most similar articles to a given slug by TF-IDF content similarity + keyword overlap.",
        input_schema={"type": "object", "properties": {"slug": {"type": "string"}, "top_k": {"type": "integer", "default": 10}}, "required": ["slug"]},
    ),
    types.Tool(
        name="ai_kos_stats",
        description="Get knowledge base health stats: article counts by type, confidence distribution, articles past review, orphans (link_count=0), gaps.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_clean",
        description="Clean the inbox: move ingested .md to archive/, projects to projects/, build artifacts to rejected/.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_research_plan",
        description="Generate a structured research plan from a question. Returns sub-questions, search queries, and perspectives to investigate (STORM-style).",
        input_schema={"type": "object", "properties": {"question": {"type": "string", "description": "The research question to investigate"}}, "required": ["question"]},
    ),
    types.Tool(
        name="ai_kos_research_persist",
        description="Persist research findings as AI-KOS articles. Creates a research-note + base synthesis article.",
        input_schema={"type": "object", "properties": {"question": {"type": "string"}, "sub_questions": {"type": "array", "items": {"type": "string"}}, "findings": {"type": "array", "items": {"type": "object", "properties": {"sub_question_idx": {"type": "integer"}, "url": {"type": "string"}, "title": {"type": "string"}, "key_claim": {"type": "string"}, "evidence": {"type": "string"}}}}, "synthesis": {"type": "string", "description": "Final synthesized report in markdown"}, "knowledge_gaps": {"type": "array", "items": {"type": "string"}, "description": "Things we still don't know"}}, "required": ["question", "findings"]},
    ),
    types.Tool(
        name="ai_kos_migrate",
        description="Run schema migrations on all articles. Use --dry-run to preview changes without writing. v1.7: migrates to typed relations, lifecycle, provenance enum, usage signals, and review cadence.",
        input_schema={"type": "object", "properties": {"dry_run": {"type": "boolean", "description": "Preview changes without writing", "default": False}}},
    ),
    types.Tool(
        name="ai_kos_citation",
        description="Extract citation metadata (DOI, title, authors, year, journal) from a PDF file using pymupdf + Crossref API.",
        input_schema={"type": "object", "properties": {"filepath": {"type": "string", "description": "Absolute path to PDF file"}}, "required": ["filepath"]},
    ),
    types.Tool(
        name="ai_kos_batch_ingest",
        description="Run the full batch paper ingestion pipeline on inbox/: deduplicate, extract text, quality check, similarity check, citation extraction. Use --skip-similarity to skip knowledge-level dedup.",
        input_schema={"type": "object", "properties": {"skip_similarity": {"type": "boolean", "description": "Skip similarity check", "default": False}}},
    ),
    types.Tool(
        name="ai_kos_compare_papers",
        description="Compare two research-note articles to find their relationship: agrees, contradicts, extends, gap, or unclassified.",
        input_schema={"type": "object", "properties": {"slug_a": {"type": "string", "description": "First article slug"}, "slug_b": {"type": "string", "description": "Second article slug"}}, "required": ["slug_a", "slug_b"]},
    ),
    types.Tool(
        name="ai_kos_promote_ready",
        description="Find topics that have enough research notes (>=5) ready for synthesis into a base article.",
        input_schema={"type": "object", "properties": {"min_notes": {"type": "integer", "description": "Minimum notes needed (default 5)", "default": 5}}},
    ),
    types.Tool(
        name="ai_kos_reading_stats",
        description="Get reading status statistics across all research-note articles: how many are unread, skimmed, annotated, synthesized.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_task_create",
        description="Create a task with urgency, tags, data, and REQUIRED article_slugs. Every task must attach at least one KB article (use 'procedure' type for implementation guides). Tasks start in 'research' status.",
        input_schema={"type": "object", "properties": {
            "title": {"type": "string", "description": "Task title"},
            "description": {"type": "string", "description": "Optional context", "default": ""},
            "urgency": {"type": "string", "enum": ["red", "yellow", "green"], "description": "Default: green", "default": "green"},
            "priority": {"type": "integer", "description": "Lower = higher priority", "default": 0},
            "due_date": {"type": "string", "description": "Optional ISO date (YYYY-MM-DD)"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional categorization tags"},
            "article_slugs": {"type": "array", "items": {"type": "string"}, "description": "REQUIRED — at least one KB article slug documenting this task"},
            "data_summary": {"type": "string", "description": "Optional data summary", "default": ""},
            "image_paths": {"type": "array", "items": {"type": "string"}, "description": "Optional image paths"},
            "project_slug": {"type": "string", "description": "Optional mission article slug this task belongs to"},
        }, "required": ["title", "article_slugs"]},
    ),
    types.Tool(
        name="ai_kos_task_list",
        description="List tasks, optionally filtered by status (research/ready/in_progress/qa/qa_passed/blocked) or urgency (red/yellow/green). Returns tasks with tags, data, and attached article slugs.",
        input_schema={"type": "object", "properties": {
            "status": {"type": "string", "enum": ["research", "ready", "in_progress", "qa", "qa_passed", "blocked"], "description": "Filter by status (default: all)"},
            "urgency": {"type": "string", "enum": ["red", "yellow", "green"], "description": "Filter by urgency"},
            "limit": {"type": "integer", "description": "Max results", "default": 100},
        }},
    ),
    types.Tool(
        name="ai_kos_task_complete",
        description="Mark a task as completed (qa_passed).",
        input_schema={"type": "object", "properties": {
            "task_id": {"type": "integer", "description": "Task ID to complete"},
        }, "required": ["task_id"]},
    ),
    types.Tool(
        name="ai_kos_task_delete",
        description="Delete a future task entirely (also cancels it if pending).",
        input_schema={"type": "object", "properties": {
            "task_id": {"type": "integer", "description": "Task ID to delete"},
        }, "required": ["task_id"]},
    ),
    types.Tool(
        name="ai_kos_datasets",
        description="List all SQL-backed dataset articles with table name, row count, and column info.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_query",
        description="Run a SQL query against a dataset article. Returns rows as list of dicts (max 500).",
        input_schema={"type": "object", "properties": {
            "slug": {"type": "string", "description": "Dataset article slug"},
            "sql": {"type": "string", "description": "SELECT query to run"},
        }, "required": ["slug", "sql"]},
    ),
    types.Tool(
        name="ai_kos_ingest_csv",
        description="Ingest a CSV file as a new SQL-backed dataset article. Creates the table, frontmatter stub, and inserts all rows in one call.",
        input_schema={"type": "object", "properties": {
            "csv_path": {"type": "string", "description": "Absolute path to CSV file"},
            "slug": {"type": "string", "description": "Article slug (e.g. bird-species)"},
            "title": {"type": "string", "description": "Article title"},
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "3-8 keywords"},
            "summary": {"type": "string", "description": "1-2 sentence description"},
            "article_type": {"type": "string", "enum": ["base", "research-note", "note"], "description": "Article type (default: base)", "default": "base"},
        }, "required": ["csv_path", "slug", "title", "keywords", "summary"]},
    ),
    types.Tool(
        name="ai_kos_timeseries_stats",
        description="Get statistical summary of a time-series dataset: min/max/avg per time bucket, gap detection.",
        input_schema={"type": "object", "properties": {
            "slug": {"type": "string", "description": "Dataset article slug"},
            "interval": {"type": "string", "description": "Bucket interval: '1h', '1d'. Default: '1h'", "default": "1h"},
            "detect_gaps": {"type": "boolean", "description": "Also detect gaps", "default": False},
            "gap_threshold_seconds": {"type": "integer", "description": "Expected interval in seconds for gap detection", "default": 60},
        }, "required": ["slug"]},
    ),
    types.Tool(
        name="ai_kos_ingest_blob",
        description="Ingest a binary file (image, PDF, audio) as a blob-backed article. Copies file to datasets/blobs/, optionally runs OCR.",
        input_schema={"type": "object", "properties": {
            "filepath": {"type": "string", "description": "Absolute path to binary file"},
            "slug": {"type": "string", "description": "Article slug"},
            "title": {"type": "string", "description": "Article title"},
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "3-8 keywords"},
            "summary": {"type": "string", "description": "1-2 sentence description"},
            "extract_text": {"type": "boolean", "description": "Try OCR/STT for text extraction", "default": True},
            "article_type": {"type": "string", "enum": ["base", "research-note", "note"], "default": "base"},
        }, "required": ["filepath", "slug", "title", "keywords", "summary"]},
    ),
    types.Tool(
        name="ai_kos_ingest_json",
        description="Ingest a JSON file or URL as a JSON-backed article. Stores in SQLite with JSON1 path query support.",
        input_schema={"type": "object", "properties": {
            "source": {"type": "string", "description": "File path or URL to JSON data"},
            "slug": {"type": "string", "description": "Article slug"},
            "title": {"type": "string", "description": "Article title"},
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "3-8 keywords"},
            "summary": {"type": "string", "description": "1-2 sentence description"},
            "article_type": {"type": "string", "enum": ["base", "research-note", "note"], "default": "base"},
        }, "required": ["source", "slug", "title", "keywords", "summary"]},
    ),
    types.Tool(
        name="ai_kos_ingest_graph",
        description="Ingest graph data from edge-list CSV or node/edge JSON. Creates node/edge tables + frontmatter.",
        input_schema={"type": "object", "properties": {
            "source": {"type": "string", "description": "CSV (source,target) or JSON ({nodes:[], edges:[]})"},
            "slug": {"type": "string", "description": "Article slug"},
            "title": {"type": "string", "description": "Article title"},
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "3-8 keywords"},
            "summary": {"type": "string", "description": "1-2 sentence description"},
            "directed": {"type": "boolean", "description": "Directed graph?", "default": True},
            "article_type": {"type": "string", "enum": ["base", "research-note", "note"], "default": "base"},
        }, "required": ["source", "slug", "title", "keywords", "summary"]},
    ),
    types.Tool(
        name="ai_kos_ingest_parquet",
        description="Ingest a Parquet file as a SQL-backed dataset article. Reads columnar data via pyarrow and creates a SQLite table.",
        input_schema={"type": "object", "properties": {
            "filepath": {"type": "string", "description": "Absolute path to .parquet file"},
            "slug": {"type": "string", "description": "Article slug"},
            "title": {"type": "string", "description": "Article title"},
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "3-8 keywords"},
            "summary": {"type": "string", "description": "1-2 sentence description"},
            "article_type": {"type": "string", "enum": ["base", "research-note", "note"], "default": "base"},
        }, "required": ["filepath", "slug", "title", "keywords", "summary"]},
    ),
    types.Tool(
        name="ai_kos_ingest_orc",
        description="Ingest an ORC file as a SQL-backed dataset article. Reads columnar data via pyarrow and creates a SQLite table.",
        input_schema={"type": "object", "properties": {
            "filepath": {"type": "string", "description": "Absolute path to .orc file"},
            "slug": {"type": "string", "description": "Article slug"},
            "title": {"type": "string", "description": "Article title"},
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "3-8 keywords"},
            "summary": {"type": "string", "description": "1-2 sentence description"},
            "article_type": {"type": "string", "enum": ["base", "research-note", "note"], "default": "base"},
        }, "required": ["filepath", "slug", "title", "keywords", "summary"]},
    ),
    types.Tool(
        name="ai_kos_ingest_sqlite",
        description="Ingest a SQLite .db file — imports all tables as dataset articles linked by shared keywords.",
        input_schema={"type": "object", "properties": {
            "filepath": {"type": "string", "description": "Absolute path to .db/.sqlite file"},
            "slug_prefix": {"type": "string", "description": "Prefix for article slugs (e.g. 'birds')"},
            "title_prefix": {"type": "string", "description": "Prefix for article titles"},
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "3-8 shared keywords"},
        }, "required": ["filepath", "slug_prefix", "title_prefix", "keywords"]},
    ),
    types.Tool(
        name="ai_kos_ingest_sql_dump",
        description="Execute a .sql dump file against SQLite and import resulting tables as dataset articles.",
        input_schema={"type": "object", "properties": {
            "filepath": {"type": "string", "description": "Absolute path to .sql file"},
            "slug_prefix": {"type": "string", "description": "Prefix for article slugs"},
            "title_prefix": {"type": "string", "description": "Prefix for article titles"},
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "3-8 shared keywords"},
        }, "required": ["filepath", "slug_prefix", "title_prefix", "keywords"]},
    ),
    types.Tool(
        name="ai_kos_bibtex_export",
        description="Export BibTeX bibliography from AI-KOS research-note articles. Scans all research-notes, extracts citation metadata (DOI, authors, year, title, journal), and generates a .bib file. Use enrich=True to query Crossref for missing metadata.",
        input_schema={"type": "object", "properties": {
            "output_path": {"type": "string", "description": "Optional output path for .bib file. Default: knowledge/bibliography.bib"},
            "enrich": {"type": "boolean", "description": "Query Crossref API for articles with DOIs but incomplete metadata. Default: false", "default": False},
        }},
    ),
    types.Tool(
        name="ai_kos_search_papers",
        description="Full-text search across stored academic paper bodies. Searches the complete extracted text of ingested PDFs — not just research-note summaries. Use action='search' to find papers by keyword, action='stats' for counts, action='list' to browse, action='backfill' to extract+store text from rejected/ PDFs.",
        input_schema={"type": "object", "properties": {
            "action": {"type": "string", "enum": ["search", "stats", "list", "backfill"], "description": "What to do: search papers, get stats, list all, or backfill from PDFs", "default": "search"},
            "query": {"type": "string", "description": "Search query (required when action=search)"},
            "top_k": {"type": "integer", "description": "Max results (default: 10)", "default": 10},
            "pdf_dir": {"type": "string", "description": "PDF directory for backfill (default: rejected/)"},
        }, "required": []},
    ),
    types.Tool(
        name="ai_kos_skill_catalog",
        description="Catalog AI-KOS articles as loadable skills (dsh skill-family pattern): rank-ordered candidates (procedure=100, process=80, help=60, base=40, research-note=20) with slug, summary, and provider. Use before loading a skill.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_skill_load",
        description="Load one KB article as a skill definition (full body + meta) by slug. Use the name from ai_kos_skill_catalog.",
        input_schema={"type": "object", "properties": {"name": {"type": "string", "description": "Article slug / skill name"}}, "required": ["name"]},
    ),
]


# ── Sync dispatch ────────────────────────────────────────────────────────────

def _dispatch_tool(name: str, arguments: dict) -> dict:
    if name == "ai_kos_ingest":
        from ai_kos.ingestion import extract
        return extract(arguments["filepath"])

    elif name == "ai_kos_create":
        from ai_kos.articles import create_article
        return create_article(arguments["article_type"], arguments["data"])

    elif name == "ai_kos_search":
        from ai_kos.search import search
        results = search(
            arguments["query"],
            top_k=arguments.get("top_k", 10),
            article_type=arguments.get("article_type"),
            doc_type=arguments.get("doc_type"),
            lifecycle=arguments.get("lifecycle"),
            access=arguments.get("access"),
        )
        return {"results": results, "total": len(results)}

    elif name == "ai_kos_read":
        from ai_kos.articles import read_article
        article = read_article(arguments["slug"])
        return article or {"error": f"Article not found: {arguments['slug']}"}

    elif name == "ai_kos_link":
        from ai_kos.linker import link_all
        return link_all(min_overlap=arguments.get("min_overlap"))

    elif name == "ai_kos_list":
        from ai_kos.articles import list_articles
        return {"articles": list_articles(
            article_type=arguments.get("article_type"),
            keyword=arguments.get("keyword"),
            access=arguments.get("access"),
            doc_type=arguments.get("doc_type"),
            lifecycle=arguments.get("lifecycle"),
        )}

    elif name == "ai_kos_merge_candidates":
        from ai_kos.articles import find_merge_candidates
        return {"candidates": find_merge_candidates(arguments["slug"])}

    elif name == "ai_kos_templates":
        from ai_kos.schemas import TEMPLATES
        return {name.value: {"description": t["description"], "prompt": t["prompt"], "human_fields": t["human_fields"]} for name, t in TEMPLATES.items()}

    elif name == "ai_kos_graph":
        from ai_kos.graph_data import export_graph_data
        return export_graph_data()

    elif name == "ai_kos_compare":
        from ai_kos.search import compare
        return {"slug": arguments["slug"], "similar": compare(arguments["slug"], top_k=arguments.get("top_k", 10))}

    elif name == "ai_kos_stats":
        from ai_kos.articles import stats
        from ai_kos.db import body_stats
        result = stats()
        result.update(body_stats())
        return result

    elif name == "ai_kos_clean":
        import shutil
        from ai_kos.config import get
        inbox = Path(get("paths", "inbox_dir", default="inbox"))
        ad, rd, pd = Path(get("paths", "archive_dir", default="archive")), Path(get("paths", "rejected_dir", default="rejected")), Path(get("paths", "projects_dir", default="projects"))
        for d in [ad, rd, pd]:
            d.mkdir(exist_ok=True)
        st = {"archived": 0, "rejected": 0, "projects": 0, "errors": 0}
        for item in sorted(inbox.iterdir()):
            try:
                n, e = item.name, item.suffix.lower()
                if any(p in n.lower() for p in [".gradle", "build/", ".venv", "__pycache__"]):
                    _mv(item, rd / n); st["rejected"] += 1
                elif e in (".jar", ".zip", ".tar", ".bin", ".lock", ".pyc", ".sqlite3", ".db", ".log", ".html"):
                    _mv(item, rd / n); st["rejected"] += 1
                elif item.is_dir() and ((item / ".git").exists() or (item / "README.md").exists()):
                    _mv(item, pd / n); st["projects"] += 1
                elif e in (".md", ".txt", ".rst", ".org"):
                    _mv(item, ad / n); st["archived"] += 1
                else:
                    _mv(item, rd / n); st["rejected"] += 1
            except Exception:
                st["errors"] += 1
        return st

    elif name == "ai_kos_research_plan":
        from ai_kos.deep_research import plan_research
        from dataclasses import asdict
        return asdict(plan_research(arguments["question"]))

    elif name == "ai_kos_research_persist":
        import uuid as _uuid
        from ai_kos.deep_research import ResearchResult, persist_research
        rr = ResearchResult(
            id=str(_uuid.uuid4())[:8], plan_id="", question=arguments["question"],
            sub_questions=arguments.get("sub_questions", []), findings=arguments["findings"],
            cross_references=[], synthesis=arguments.get("synthesis", ""),
            knowledge_gaps=arguments.get("knowledge_gaps", []),
        )
        return persist_research(rr)

    elif name == "ai_kos_migrate":
        from ai_kos.migrate import run_migrations
        return run_migrations(dry_run=arguments.get("dry_run", False))

    elif name == "ai_kos_citation":
        from ai_kos.citation import extract_citation
        cit = extract_citation(arguments["filepath"])
        return {"citation": cit.to_dict(), "author_year": cit.author_year_key()}

    elif name == "ai_kos_batch_ingest":
        from ai_kos.batch_ingest import ingest_batch
        return ingest_batch(skip_similarity=arguments.get("skip_similarity", False))

    elif name == "ai_kos_compare_papers":
        from ai_kos.paper_compare import compare_papers
        return compare_papers(arguments["slug_a"], arguments["slug_b"])

    elif name == "ai_kos_promote_ready":
        from ai_kos.paper_compare import promote_ready
        return {"topics": promote_ready(min_notes=arguments.get("min_notes", 5))}

    elif name == "ai_kos_reading_stats":
        from ai_kos.paper_compare import reading_status_stats
        return reading_status_stats()

    elif name == "ai_kos_skill_catalog":
        from ai_kos.skills import skill_catalog, catalog_version
        skills = skill_catalog()
        return {
            "skills": [{"name": s.name, "description": s.description,
                        "rank": s.rank, "provider": s.provider, "slug": s.slug}
                       for s in skills],
            "total": len(skills),
            "version": catalog_version(),
        }

    elif name == "ai_kos_skill_load":
        from ai_kos.skills import skill_load
        skill = skill_load(arguments["name"])
        if skill is None:
            return {"error": "skill not found"}
        return {"skill": {"name": skill.name, "body": skill.body, "meta": skill.meta}}

    elif name == "ai_kos_task_create":
        from ai_kos.tasks import TaskManager
        from dataclasses import asdict
        tm = TaskManager()
        task = tm.create(
            title=arguments["title"],
            description=arguments.get("description", ""),
            urgency=arguments.get("urgency", "green"),
            priority=arguments.get("priority", 0),
            due_date=arguments.get("due_date"),
            tags=arguments.get("tags"),
            article_slugs=arguments.get("article_slugs"),
            data_summary=arguments.get("data_summary", ""),
            image_paths=arguments.get("image_paths"),
            project_slug=arguments.get("project_slug"),
        )
        return asdict(task)

    elif name == "ai_kos_task_list":
        from ai_kos.tasks import TaskManager
        from dataclasses import asdict
        tm = TaskManager()
        tasks = tm.list_tasks(
            status=arguments.get("status"),
            urgency=arguments.get("urgency"),
            limit=arguments.get("limit", 100),
        )
        return {"tasks": [asdict(t) for t in tasks], "total": len(tasks)}

    elif name == "ai_kos_task_complete":
        from ai_kos.tasks import TaskManager
        from dataclasses import asdict
        tm = TaskManager()
        try:
            task = tm.complete(arguments["task_id"])
            return asdict(task)
        except ValueError as e:
            return {"error": str(e)}

    elif name == "ai_kos_task_delete":
        from ai_kos.tasks import TaskManager
        tm = TaskManager()
        tm.delete(arguments["task_id"])
        return {"status": "deleted", "task_id": arguments["task_id"]}

    elif name == "ai_kos_datasets":
        from ai_kos.articles import list_articles
        from ai_kos import datasets
        all_articles = list_articles()
        sql_articles = [a for a in all_articles if a.get("backend") == "sql"]
        results = []
        for a in sql_articles:
            ds = a.get("dataset", {})
            db_path = ds.get("db", "")
            table_name = ds.get("table", "")
            stats = datasets.table_stats(db_path, table_name) if db_path and table_name else None
            results.append({
                "slug": a["slug"], "title": a["title"], "type": a["type"],
                "database": db_path, "table": table_name,
                "row_count": stats["row_count"] if stats else 0,
                "columns": stats["columns"] if stats else [],
            })
        return {"datasets": results, "total": len(results)}

    elif name == "ai_kos_query":
        from ai_kos.articles import read_article
        from ai_kos import datasets
        article = read_article(arguments["slug"])
        if not article:
            return {"error": f"Article not found: {arguments['slug']}"}

        backend = article.get("backend", "md")

        if backend == "graph":
            from ai_kos import graphs
            ds = article.get("dataset", {})
            sql = arguments["sql"].strip().upper()
            if sql.startswith("NEIGHBORS"):
                parts = sql.split()
                node_id = parts[2] if len(parts) > 2 else ""
                direction = parts[3].lower() if len(parts) > 3 else "out"
                rows = graphs.get_neighbors(ds["db"], ds["table"], node_id, direction)
                return {"slug": arguments["slug"], "query_type": "neighbors",
                        "node": node_id, "rows": rows, "count": len(rows)}
            elif sql.startswith("SHORTEST PATH"):
                parts = sql.split()
                source = parts[2] if len(parts) > 2 else ""
                target = parts[4] if len(parts) > 4 else ""
                path = graphs.shortest_path(ds["db"], ds["table"], source, target)
                return {"slug": arguments["slug"], "query_type": "shortest_path",
                        "source": source, "target": target, "path": path}
            elif sql.startswith("EXPORT"):
                data = graphs.export_vis_network(ds["db"], ds["table"])
                return {"slug": arguments["slug"], "query_type": "vis_export",
                        "nodes": len(data["nodes"]), "edges": len(data["edges"]), "data": data}
            else:
                return {"error": f"Unknown graph query: {sql}. Use NEIGHBORS, SHORTEST PATH, or EXPORT VIS"}

        elif backend == "json":
            ds = article.get("dataset", {})
            rows = datasets.json_query(ds["db"], ds["table"], arguments["slug"], arguments["sql"])
            return {"slug": arguments["slug"], "query_type": "json_path", "rows": rows, "count": len(rows)}

        elif backend == "sql":
            ds = article.get("dataset", {})
            time_col = ds.get("time_column")
            time_from = arguments.get("time_from")
            time_to = arguments.get("time_to")
            if time_col and (time_from or time_to):
                rows = datasets.query_time_range(ds["db"], ds["table"], time_col, time_from, time_to)
            else:
                rows = datasets.query_table(ds["db"], arguments["sql"])
            return {"slug": arguments["slug"], "rows": rows, "count": len(rows)}

        else:
            return {"error": f"Article is not queryable: {arguments['slug']} (backend={backend})"}

    elif name == "ai_kos_ingest_csv":
        from ai_kos import datasets
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetColumn, DatasetRef
        import uuid as _uuid, os as _os
        from datetime import date as _date

        csv_path = arguments["csv_path"]
        slug = arguments["slug"]
        table_name = slug.replace("-", "_")
        db_path = "datasets/ai-kos.db"

        # Ingest CSV into SQLite
        result = datasets.ingest_csv(csv_path, db_path, table_name)
        if "error" in result:
            return result

        # Create the article
        today = _date.today()
        columns = [DatasetColumn(name=c["name"], type=c["type"]) for c in result["columns"]]

        article_data = {
            "id": str(_uuid.uuid4()),
            "title": arguments["title"],
            "slug": slug,
            "type": arguments.get("article_type", "base"),
            "created_at": today,
            "updated_at": today,
            "reviewed_at": today,
            "next_review_at": today.replace(year=today.year + 1),
            "keywords": arguments["keywords"],
            "summary": arguments["summary"],
            "backend": "sql",
            "dataset": DatasetRef(db=db_path, table=table_name, columns=columns),
            "provenance": [{"source": "ingest", "origin_ref": _os.path.basename(csv_path)}],
            "confidence": 0.9,
        }
        return create_article(arguments.get("article_type", "base"), article_data)

    elif name == "ai_kos_timeseries_stats":
        from ai_kos.articles import read_article
        from ai_kos import datasets
        article = read_article(arguments["slug"])
        if not article:
            return {"error": f"Article not found: {arguments['slug']}"}
        ds = article.get("dataset", {})
        time_col = ds.get("time_column")
        if not time_col:
            return {"error": "Article is not a time-series dataset (no time_column)"}

        stats = datasets.timeseries_stats(ds["db"], ds["table"], time_col,
                                          interval=arguments.get("interval", "1h"))
        result = {"slug": arguments["slug"], **stats}
        if arguments.get("detect_gaps"):
            gaps = datasets.detect_gaps(ds["db"], ds["table"], time_col,
                                        arguments.get("gap_threshold_seconds", 60))
            result["gaps"] = gaps
        return result

    elif name == "ai_kos_ingest_blob":
        from ai_kos.blobs import store_blob, extract_text
        from ai_kos.articles import create_article
        from ai_kos.schemas import BlobRef
        import uuid as _uuid, os as _os
        from datetime import date as _date

        filepath = arguments["filepath"]
        slug = arguments["slug"]
        blob_info = store_blob(filepath, slug=slug)
        if arguments.get("extract_text", True):
            blob_info["extracted_text"] = extract_text(blob_info["path"], blob_info["mime_type"])

        today = _date.today()
        article_data = {
            "id": str(_uuid.uuid4()), "title": arguments["title"], "slug": slug,
            "type": arguments.get("article_type", "base"),
            "created_at": today, "updated_at": today, "reviewed_at": today,
            "next_review_at": today.replace(year=today.year + 1),
            "keywords": arguments["keywords"], "summary": arguments["summary"],
            "backend": "blob", "blob": BlobRef(**blob_info),
            "provenance": [{"source": "ingest", "origin_ref": _os.path.basename(filepath)}],
            "confidence": 0.9,
        }
        return create_article(arguments.get("article_type", "base"), article_data)

    elif name == "ai_kos_ingest_json":
        from ai_kos.datasets import store_json_doc
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetRef, DatasetColumn
        import json, uuid as _uuid, os as _os
        from datetime import date as _date

        source = arguments["source"]
        slug = arguments["slug"]
        if source.startswith("http://") or source.startswith("https://"):
            import urllib.request
            with urllib.request.urlopen(source) as resp:
                data = json.loads(resp.read().decode())
        else:
            with open(source) as f:
                data = json.load(f)

        db_path = "datasets/ai-kos.db"
        table_name = "json_docs"
        store_json_doc(db_path, table_name, slug, data)

        today = _date.today()
        article_data = {
            "id": str(_uuid.uuid4()), "title": arguments["title"], "slug": slug,
            "type": arguments.get("article_type", "base"),
            "created_at": today, "updated_at": today, "reviewed_at": today,
            "next_review_at": today.replace(year=today.year + 1),
            "keywords": arguments["keywords"], "summary": arguments["summary"],
            "backend": "json",
            "dataset": DatasetRef(db=db_path, table=table_name, columns=[
                DatasetColumn(name="slug", type="TEXT"),
                DatasetColumn(name="doc", type="TEXT"),
            ]),
            "provenance": [{"source": "ingest", "origin_ref": source}],
            "confidence": 0.9,
        }
        return create_article(arguments.get("article_type", "base"), article_data)

    elif name == "ai_kos_ingest_graph":
        from ai_kos.graphs import create_graph, insert_nodes, insert_edges
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetRef, GraphRef, DatasetColumn
        import uuid as _uuid, os as _os, csv
        from datetime import date as _date

        source = arguments["source"]
        slug = arguments["slug"]
        db_path = "datasets/ai-kos.db"
        table = slug.replace("-", "_")
        directed = arguments.get("directed", True)

        nodes, edges, node_ids = [], [], set()
        if source.endswith(".csv"):
            with open(source, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    src = row.get("source") or row.get("from") or row.get("src")
                    tgt = row.get("target") or row.get("to") or row.get("dst")
                    if src and tgt:
                        edges.append({"source": src, "target": tgt})
                        node_ids.add(src); node_ids.add(tgt)
        elif source.endswith(".json"):
            import json
            with open(source) as f:
                data = json.load(f)
            if isinstance(data, dict):
                for n in data.get("nodes", []):
                    nid = n.get("id") or n.get("node_id")
                    if nid:
                        node_ids.add(nid)
                        nd = dict(n)
                        nd["node_id"] = nid
                        nodes.append(nd)
                edges = data.get("edges", data.get("links", []))

        nodes_to_insert = nodes or [{"node_id": nid} for nid in node_ids]
        create_graph(db_path, table, directed=directed)
        insert_nodes(db_path, table, nodes_to_insert)
        edge_count = insert_edges(db_path, table, edges)

        today = _date.today()
        graph_ref = GraphRef(directed=directed, node_count=len(node_ids), edge_count=edge_count)
        article_data = {
            "id": str(_uuid.uuid4()), "title": arguments["title"], "slug": slug,
            "type": arguments.get("article_type", "base"),
            "created_at": today, "updated_at": today, "reviewed_at": today,
            "next_review_at": today.replace(year=today.year + 1),
            "keywords": arguments["keywords"], "summary": arguments["summary"],
            "backend": "graph",
            "dataset": DatasetRef(db=db_path, table=table, columns=[
                DatasetColumn(name="node_id", type="TEXT"),
            ]),
            "graph": graph_ref,
            "provenance": [{"source": "ingest", "origin_ref": _os.path.basename(source)}],
            "confidence": 0.9,
        }
        return create_article(arguments.get("article_type", "base"), article_data)

    elif name == "ai_kos_ingest_parquet":
        from ai_kos.datasets import ingest_parquet
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetRef, DatasetColumn
        from datetime import date as _date
        import uuid, os

        db_path = "datasets/ai-kos.db"
        table = arguments["slug"].replace("-", "_")
        result = ingest_parquet(arguments["filepath"], db_path, table)
        if "error" in result:
            return result

        today = _date.today()
        cols = [DatasetColumn(name=c["name"], type=c["type"]) for c in result["columns"]]
        return create_article(arguments.get("article_type", "base"), {
            "id": str(uuid.uuid4()), "title": arguments["title"], "slug": arguments["slug"],
            "type": arguments.get("article_type", "base"),
            "created_at": today, "updated_at": today, "reviewed_at": today,
            "next_review_at": today.replace(year=today.year + 1),
            "keywords": arguments["keywords"], "summary": arguments["summary"],
            "backend": "sql",
            "dataset": DatasetRef(db=db_path, table=table, columns=cols),
            "provenance": [{"source": "ingest", "origin_ref": os.path.basename(arguments["filepath"])}],
            "confidence": 0.9,
        })

    elif name == "ai_kos_ingest_orc":
        from ai_kos.datasets import ingest_orc
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetRef, DatasetColumn
        from datetime import date as _date
        import uuid, os

        db_path = "datasets/ai-kos.db"
        table = arguments["slug"].replace("-", "_")
        result = ingest_orc(arguments["filepath"], db_path, table)
        if "error" in result:
            return result

        today = _date.today()
        cols = [DatasetColumn(name=c["name"], type=c["type"]) for c in result["columns"]]
        return create_article(arguments.get("article_type", "base"), {
            "id": str(uuid.uuid4()), "title": arguments["title"], "slug": arguments["slug"],
            "type": arguments.get("article_type", "base"),
            "created_at": today, "updated_at": today, "reviewed_at": today,
            "next_review_at": today.replace(year=today.year + 1),
            "keywords": arguments["keywords"], "summary": arguments["summary"],
            "backend": "sql",
            "dataset": DatasetRef(db=db_path, table=table, columns=cols),
            "provenance": [{"source": "ingest", "origin_ref": os.path.basename(arguments["filepath"])}],
            "confidence": 0.9,
        })

    elif name == "ai_kos_ingest_sqlite":
        from ai_kos.datasets import import_sqlite_db
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetRef, DatasetColumn
        from datetime import date as _date
        import uuid, os

        db_path = "datasets/ai-kos.db"
        prefix = arguments["slug_prefix"]
        title_pre = arguments["title_prefix"]
        kws = arguments["keywords"]

        result = import_sqlite_db(arguments["filepath"], db_path)
        articles = []
        today = _date.today()
        for table_info in result.get("tables", []):
            tname = table_info["table"]
            slug = f"{prefix}-{tname}"
            cols = [DatasetColumn(name=c, type="TEXT") for c in table_info["columns"]]
            r = create_article("base", {
                "id": str(uuid.uuid4()), "title": f"{title_pre}: {tname}", "slug": slug,
                "type": "base", "created_at": today, "updated_at": today, "reviewed_at": today,
                "next_review_at": today.replace(year=today.year + 1),
                "keywords": kws + [tname], "summary": f"Table {tname} ({table_info['row_count']} rows) from {os.path.basename(arguments['filepath'])}.",
                "backend": "sql",
                "dataset": DatasetRef(db=db_path, table=tname, columns=cols),
                "provenance": [{"source": "ingest", "origin_ref": os.path.basename(arguments['filepath'])}],
                "confidence": 0.9,
            })
            articles.append({"slug": slug, "table": tname, "row_count": table_info["row_count"],
                           "status": r.get("status", "error")})
        return {"source": arguments["filepath"], "tables_imported": len(articles), "articles": articles}

    elif name == "ai_kos_ingest_sql_dump":
        from ai_kos.datasets import ingest_sql_dump
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetRef, DatasetColumn
        from datetime import date as _date
        import uuid, os

        db_path = "datasets/ai-kos.db"
        prefix = arguments["slug_prefix"]
        title_pre = arguments["title_prefix"]
        kws = arguments["keywords"]

        result = ingest_sql_dump(arguments["filepath"], db_path)
        if "error" in result:
            return result

        articles = []
        today = _date.today()
        for table_info in result.get("tables", []):
            tname = table_info["table"]
            slug = f"{prefix}-{tname}"
            cols = [DatasetColumn(name=c, type="TEXT") for c in table_info["columns"]]
            r = create_article("base", {
                "id": str(uuid.uuid4()), "title": f"{title_pre}: {tname}", "slug": slug,
                "type": "base", "created_at": today, "updated_at": today, "reviewed_at": today,
                "next_review_at": today.replace(year=today.year + 1),
                "keywords": kws + [tname], "summary": f"Table {tname} ({table_info['row_count']} rows) from SQL dump.",
                "backend": "sql",
                "dataset": DatasetRef(db=db_path, table=tname, columns=cols),
                "provenance": [{"source": "ingest", "origin_ref": os.path.basename(arguments["filepath"])}],
                "confidence": 0.9,
            })
            articles.append({"slug": slug, "table": tname, "row_count": table_info["row_count"],
                           "status": r.get("status", "error")})
        return {"source": arguments["filepath"], "tables_imported": len(articles), "articles": articles}

    elif name == "ai_kos_bibtex_export":
        from ai_kos.bibtex import export_bibtex
        return export_bibtex(
            output_path=arguments.get("output_path"),
            enrich=arguments.get("enrich", False),
        )

    elif name == "ai_kos_search_papers":
        from ai_kos.papers import search_papers, paper_stats, list_papers, backfill_from_pdfs, search_sources, source_stats
        action = arguments.get("action", "search")
        if action == "search":
            return {"results": search_papers(arguments["query"], top_k=arguments.get("top_k", 10))}
        elif action == "stats":
            return paper_stats()
        elif action == "list":
            return {"papers": list_papers()}
        elif action == "backfill":
            return backfill_from_pdfs(pdf_dir=arguments.get("pdf_dir"))
        elif action == "sources":
            return {"results": search_sources(arguments["query"], top_k=arguments.get("top_k", 10))}
        elif action == "source_stats":
            return source_stats()
        else:
            return {"error": f"Unknown action: {action}. Use search, stats, list, backfill, sources, source_stats."}

    else:
        return {"error": f"Unknown tool: {name}"}


# ── Async handlers ───────────────────────────────────────────────────────────

async def handle_list_tools(_ctx, _req: types.ListToolsRequest) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


async def handle_call_tool(_ctx, req: types.CallToolRequestParams) -> types.CallToolResult:
    name = req.name
    arguments = req.arguments or {}

    try:
        result = await asyncio.to_thread(_dispatch_tool, name, arguments)
    except Exception as exc:
        result = {"error": str(exc), "tool": name}

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(result, indent=2, default=str, ensure_ascii=False))]
    )


server.add_request_handler("tools/list", types.ListToolsRequest, handle_list_tools)
server.add_request_handler("tools/call", types.CallToolRequestParams, handle_call_tool)


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def entrypoint():
    asyncio.run(main())


if __name__ == "__main__":
    entrypoint()


def _mv(src, dst):
    import shutil
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(str(dst))
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))
