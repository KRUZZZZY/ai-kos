# AI-KOS v1.8

**AI Knowledge Operating System** — a self-building knowledge database with automatic wikilink connections, a typed knowledge graph, and deep-research tooling.

Drop files in, get linked articles out. AI-KOS ingests documents, extracts text, creates structured knowledge articles, and automatically links them via IDF-weighted shared keywords. Ships as a Python package with an MCP server (37 tools) for AI agent integration, a Flask dashboard, and a durable research pipeline.

## Install

```bash
pip install -e .                    # core
pip install -e ".[pdf,docx]"        # + document parsing
pip install -e ".[semantic]"        # + vector search (sentence-transformers, faiss-cpu)
pip install -e ".[dev]"             # + testing
```

Requires Python 3.11+.

## Quick Start

```bash
# CLI
ai-kos ingest document.pdf           # extract text, detect type
ai-kos create base --title "..."     # create an article manually
ai-kos search "knowledge graph"      # full-text search
ai-kos link                          # auto-link all articles (IDF-weighted)
ai-kos stats                         # health check
ai-kos graph                         # export knowledge graph
ai-kos serve                         # Flask dashboard
ai-kos research "question"           # deep research pipeline
ai-kos task-create "title" --slugs a,b   # task system (v3)

# MCP Server (for AI agent integration)
ai-kos-mcp                           # starts JSON-RPC server on stdio, 37 tools
```

## Architecture

```text
ai_kos/
├── articles.py          CRUD + auto-link on write, lifecycle (current/superseded/historical)
├── linker.py            IDF-weighted keyword overlap → typed [[wikilinks]]
├── search.py            TF-IDF full-text search
├── semantic.py          Vector embeddings + hybrid RRF search (optional)
├── schemas.py           8 article types (Pydantic) — base, process, plan, help,
│                        research-note, note, mission, procedure
├── ingestion.py         PDF/DOCX/MD extraction
├── citation.py          Citation metadata extraction (pymupdf + Crossref)
├── papers.py            Academic paper ingestion pipeline
├── paper_compare.py     Paper-to-paper comparison (agrees/contradicts/extends/gap)
├── bibtex.py            BibTeX export from research-notes
├── datasets.py          SQL-backed dataset articles (CSV/Parquet/ORC/SQLite/JSON/graph)
├── blobs.py             Binary blob articles (images, PDFs, audio) + OCR
├── graphs.py            Graph dataset articles (edge lists, node/edge JSON)
├── db.py                SQLite persistence layer
├── tasks.py             Task system v3 — 6-stage status flow, urgency, project grouping
├── atq.py               ATQ — autonomous task queue (submit/tick/status/report)
├── atq_director.py      ATQ director — dispatch workers, spawn caps, leases
├── atq_worker.py        ATQ worker process
├── atq_safety.py        Safety: heartbeat, lease, no-clobber guarantees
├── atq_queue_manager.py ATQ queue manager
├── deep_research.py     Multi-step research pipeline (STORM-style planning)
├── pipeline.py          Durable execution engine — survives crashes, resumes
├── taskqueue.py         SQLite priority queue for inbox
├── docaudit.py          Documentation audit
├── migrate.py           Schema migrations (dry-run supported)
├── migrate_to_db.py     MD → SQLite migration tooling
├── bindings.py          Pydantic Settings tool config (config.yaml or AI_KOS_* env)
├── graph_data.py        Knowledge graph export (typed nodes + edges)
├── server.py            Flask dashboard (articles, graph, datasets, tasks, inbox)
├── mcp_server.py        MCP JSON-RPC server — 37 tools
├── cli.py               Command-line interface
└── vscode_bridge.py     VS Code live-editing bridge
```

## Article Types

| Type | Purpose | Example |
|------|---------|---------|
| base | Factoid / concept | "Erdős–Rényi Model" |
| process | Step-by-step procedure | "How to Ingest a File" |
| plan | Planning document | "AI-KOS Development Roadmap" |
| help | Component explanation | "How the Auto-Linker Works" |
| research-note | Research findings | "Hybrid Search Architectures" |
| note | Temporary note | "Consider Obsidian graph viz" |
| mission | Project definition | "AI-KOS Deep Research Tool" |
| procedure | Implementation guide | "ATQ Worker Protocol" |

## Auto-Linking

Articles sharing ≥2 keywords are automatically connected with `[[wikilinks]]`. The linker is IDF-weighted — rare keywords drive links, bridge keywords are filtered out. Merge candidates (>80% keyword overlap) are flagged for review, and lifecycle is auto-set (superseded losers). Typed relations: see-also, extends, contradicts, gap.

## Deep Research Pipeline

Multi-step autonomous research with durable execution:

```
plan → search → structure → cross-reference → synthesize → review → persist
```

Each step is retried with exponential backoff. Pipeline state is persisted to JSON — survives crashes and resumes from the last checkpoint. Human review gate before article creation.

## Task System (v3) + ATQ

- 6-stage status flow: research → ready → in_progress → qa → qa_passed (+ blocked)
- Tasks require attached KB article slugs; grouped by project/mission
- ATQ: autonomous agent task queue — submit a mission, tick decomposes + dispatches workers to a kanban board, with heartbeat/lease/no-clobber safety

## Storage Backends

All backends are additive — `md` (markdown) is the default; `sql`, `blob`, `json`, and `graph` backends coexist:

```bash
ai-kos ingest-csv birds.csv --slug birds           # SQL-backed dataset
ai-kos ingest-blob scan.pdf --slug scan            # blob + OCR
ai-kos ingest-json api.json --slug api             # JSON1 path queries
ai-kos ingest-graph edges.csv --slug net           # node/edge tables
```

## Configuration

Config via `config.yaml` or `AI_KOS_*` env vars. Key paths (overrideable): `kb_path()`, `inbox_path()`, `templates_path()`.

## Tests

```bash
pytest            # ~100 tests: linker, search, MCP server, ATQ, datasets, blobs, tasks
```

Note: one env-specific test (config defaults) assumes relative `knowledge_dir`; a machine with absolute paths in config.yaml will fail it — expected, not a regression.
