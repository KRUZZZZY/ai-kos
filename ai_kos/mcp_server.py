"""AI-KOS MCP server — exposes full knowledge database to Hermes.

Tools:
  ai_kos_ingest  — Extract text from any file, detect type, return for AI simplification
  ai_kos_create  — Create a new knowledge article (AI-simplified version)
  ai_kos_search  — Hybrid semantic search + keyword search
  ai_kos_read    — Read an article by slug
  ai_kos_link    — Run auto-linker (≥3 shared keywords → [[wikilinks]])
  ai_kos_list    — List articles, filter by type/keyword
  ai_kos_merge_candidates — Find articles with high keyword overlap with a given slug
  ai_kos_templates — Show all 7 article templates with prompts
"""

import json
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-kos-mcp")

server = Server("ai-kos")

# ── Tool definitions ──────────────────────────────────────────────

TOOLS = [
    types.Tool(
        name="ai_kos_ingest",
        description="Extract text from any file (.md, .txt, .pdf, .docx, .py, etc). Returns raw content + detected type + suggested article template. Use this first when adding new knowledge.",
        input_schema={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Absolute path to file"},
            },
            "required": ["filepath"],
        },
    ),
    types.Tool(
        name="ai_kos_create",
        description="Create a new knowledge article. After ingesting a file, simplify the content using the appropriate template, then call this to persist it. The linker runs automatically.",
        input_schema={
            "type": "object",
            "properties": {
                "article_type": {
                    "type": "string",
                    "enum": ["base", "process", "plan", "help", "research-note", "note", "mission"],
                    "description": "Article type — use the suggested_type from ai_kos_ingest",
                },
                "data": {
                    "type": "object",
                    "description": "Full article data matching the template schema. Required: title, slug, keywords (3-8), summary, provenance, + type-specific fields",
                },
            },
            "required": ["article_type", "data"],
        },
    ),
    types.Tool(
        name="ai_kos_search",
        description="Search knowledge base. Returns articles matching the query by keyword + semantic similarity.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "article_type": {"type": "string", "description": "Optional: filter by type (base/process/plan/help/research-note/note/mission)"},
                "top_k": {"type": "integer", "description": "Max results", "default": 10},
            },
            "required": ["query"],
        },
    ),
    types.Tool(
        name="ai_kos_read",
        description="Read a full knowledge article by slug. Returns frontmatter + body.",
        input_schema={
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Article slug"},
            },
            "required": ["slug"],
        },
    ),
    types.Tool(
        name="ai_kos_link",
        description="Run the auto-linker. Scans all articles and creates [[wikilinks]] between any pair sharing >=3 keywords. Also reports merge candidates (>80% keyword overlap).",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_list",
        description="List all knowledge articles. Optionally filter by type or keyword.",
        input_schema={
            "type": "object",
            "properties": {
                "article_type": {"type": "string", "description": "Filter by type"},
                "keyword": {"type": "string", "description": "Filter by keyword"},
            },
        },
    ),
    types.Tool(
        name="ai_kos_merge_candidates",
        description="Find articles with high keyword overlap with a given slug. Use before merging or updating to check for duplicates.",
        input_schema={
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Article slug to check against"},
            },
            "required": ["slug"],
        },
    ),
    types.Tool(
        name="ai_kos_templates",
        description="Show all 7 article templates with their prompts. Use this when you need to know what fields each article type requires.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_graph",
        description="Export the knowledge graph as JSON (nodes + edges). Use for visualization or to inspect the connection structure.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_compare",
        description="Find the most similar articles to a given slug by TF-IDF content similarity + keyword overlap.",
        input_schema={
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "top_k": {"type": "integer", "default": 10},
            },
            "required": ["slug"],
        },
    ),
    types.Tool(
        name="ai_kos_stats",
        description="Get knowledge base health stats: article counts by type, confidence distribution, articles past review, orphans, gaps.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_clean",
        description="Clean the inbox: move ingested .md to archive/, projects to projects/, build artifacts to rejected/.",
        input_schema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="ai_kos_research_plan",
        description="Generate a structured research plan from a question. Returns sub-questions, search queries, and perspectives to investigate (STORM-style). Review the plan, then execute searches for each sub-question using web_search.",
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The research question to investigate"},
            },
            "required": ["question"],
        },
    ),
    types.Tool(
        name="ai_kos_research_persist",
        description="Persist research findings as AI-KOS articles. After executing the research plan, structure findings and save them. Creates a research-note + base synthesis article.",
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "sub_questions": {"type": "array", "items": {"type": "string"}},
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sub_question_idx": {"type": "integer"},
                            "url": {"type": "string"},
                            "title": {"type": "string"},
                            "key_claim": {"type": "string"},
                            "evidence": {"type": "string"},
                        },
                    },
                },
                "synthesis": {"type": "string", "description": "Final synthesized report in markdown"},
                "knowledge_gaps": {"type": "array", "items": {"type": "string"}, "description": "Things we still don't know"},
            },
            "required": ["question", "findings"],
        },
    ),
]


# ── Handlers ───────────────────────────────────────────────────────


async def handle_list_tools(_ctx, _req: types.ListToolsRequest) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


async def handle_call_tool(_ctx, req: types.CallToolRequestParams) -> types.CallToolResult:
    name = req.name
    arguments = req.arguments or {}
    result = {}

    try:
        if name == "ai_kos_ingest":
            from ai_kos.ingestion import extract

            result = extract(arguments["filepath"])

        elif name == "ai_kos_create":
            from ai_kos.articles import create_article

            result = create_article(arguments["article_type"], arguments["data"])

        elif name == "ai_kos_search":
            from ai_kos.search import search

            results = search(
                arguments["query"],
                top_k=arguments.get("top_k", 10),
                article_type=arguments.get("article_type"),
            )
            result = {"results": results, "total": len(results)}

        elif name == "ai_kos_read":
            from ai_kos.articles import read_article

            article = read_article(arguments["slug"])
            result = article or {"error": f"Article not found: {arguments['slug']}"}

        elif name == "ai_kos_link":
            from ai_kos.linker import link_all

            result = link_all()

        elif name == "ai_kos_list":
            from ai_kos.articles import list_articles

            result = {
                "articles": list_articles(
                    article_type=arguments.get("article_type"),
                    keyword=arguments.get("keyword"),
                )
            }

        elif name == "ai_kos_merge_candidates":
            from ai_kos.articles import find_merge_candidates

            result = {"candidates": find_merge_candidates(arguments["slug"])}

        elif name == "ai_kos_templates":
            from ai_kos.schemas import TEMPLATES

            result = {
                name.value: {
                    "description": t["description"],
                    "prompt": t["prompt"],
                    "human_fields": t["human_fields"],
                }
                for name, t in TEMPLATES.items()
            }

        elif name == "ai_kos_graph":
            from ai_kos.graph_data import export_graph_data

            result = export_graph_data()

        elif name == "ai_kos_compare":
            from ai_kos.search import compare

            result = {
                "slug": arguments["slug"],
                "similar": compare(arguments["slug"], top_k=arguments.get("top_k", 10)),
            }

        elif name == "ai_kos_stats":
            from ai_kos.articles import stats

            result = stats()

        elif name == "ai_kos_clean":
            import shutil

            from pathlib import Path as P

            from ai_kos.config import get

            inbox = P(get("paths", "inbox_dir", default="inbox"))
            ad = P(get("paths", "archive_dir", default="archive"))
            rd = P(get("paths", "rejected_dir", default="rejected"))
            pd = P(get("paths", "projects_dir", default="projects"))
            for d in [ad, rd, pd]:
                d.mkdir(exist_ok=True)
            st = {"archived": 0, "rejected": 0, "projects": 0, "errors": 0}
            for item in sorted(inbox.iterdir()):
                try:
                    n, e = item.name, item.suffix.lower()
                    if any(
                        p in n.lower()
                        for p in [".gradle", "build/", ".venv", "__pycache__"]
                    ):
                        _mv(item, rd / n)
                        st["rejected"] += 1
                    elif e in (
                        ".jar",
                        ".zip",
                        ".tar",
                        ".bin",
                        ".lock",
                        ".pyc",
                        ".sqlite3",
                        ".db",
                        ".log",
                        ".html",
                    ):
                        _mv(item, rd / n)
                        st["rejected"] += 1
                    elif item.is_dir() and (
                        (item / ".git").exists() or (item / "README.md").exists()
                    ):
                        _mv(item, pd / n)
                        st["projects"] += 1
                    elif e in (".md", ".txt", ".rst", ".org"):
                        _mv(item, ad / n)
                        st["archived"] += 1
                    else:
                        _mv(item, rd / n)
                        st["rejected"] += 1
                except Exception:
                    st["errors"] += 1
            result = st

        elif name == "ai_kos_research_plan":
            from ai_kos.deep_research import plan_research
            from dataclasses import asdict

            plan = plan_research(arguments["question"])
            result = asdict(plan)

        elif name == "ai_kos_research_persist":
            import uuid as _uuid

            from ai_kos.deep_research import ResearchResult, persist_research

            rr = ResearchResult(
                id=str(_uuid.uuid4())[:8],
                plan_id="",
                question=arguments["question"],
                sub_questions=arguments.get("sub_questions", []),
                findings=arguments["findings"],
                cross_references=[],
                synthesis=arguments.get("synthesis", ""),
                knowledge_gaps=arguments.get("knowledge_gaps", []),
            )
            result = persist_research(rr)

        else:
            result = {"error": f"Unknown tool: {name}"}

    except Exception as exc:
        result = {"error": str(exc), "tool": name}

    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=json.dumps(result, indent=2, default=str, ensure_ascii=False),
            )
        ]
    )


# ── Register handlers ─────────────────────────────────────────────

server.add_request_handler("tools/list", types.ListToolsRequest, handle_list_tools)
server.add_request_handler("tools/call", types.CallToolRequestParams, handle_call_tool)


# ── Entrypoint ─────────────────────────────────────────────────────


async def main():
    async with stdio_server() as (read, write):
        await server.run(
            read,
            write,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())


def _mv(src, dst):
    import shutil

    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(str(dst))
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))
