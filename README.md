# AI-KOS v1.6

**AI Knowledge Operating System** — a self-building knowledge database with automatic wikilink connections.

Drop files in, get linked articles out. AI-KOS ingests documents, extracts text, creates structured knowledge articles, and automatically links them via shared keywords. Ships as a Python package with an MCP server for AI agent integration.

## Install

```bash
pip install -e .                    # core
pip install -e ".[pdf,docx]"        # + document parsing
pip install -e ".[semantic]"        # + vector search
pip install -e ".[dev]"             # + testing
```

Requires Python 3.11+.

## Quick Start

```bash
# CLI
ai-kos ingest document.pdf          # extract text, detect type
ai-kos create base --title "..."    # create an article manually
ai-kos search "knowledge graph"     # full-text search
ai-kos link                         # auto-link all articles
ai-kos stats                        # health check
ai-kos graph                        # export knowledge graph

# MCP Server (for AI agent integration)
ai-kos-mcp                          # starts JSON-RPC server on stdio
```

## Architecture

AI-KOS is a focused Python package — 14 modules, zero microservices:

```
ai_kos/
├── articles.py      CRUD + auto-link on write
├── linker.py        Keyword overlap → [[wikilinks]]
├── search.py        TF-IDF full-text search
├── schemas.py       7 article types (Pydantic)
├── ingestion.py     PDF/DOCX/MD extraction
├── config.py        YAML config loader
├── cli.py           Command-line interface
├── mcp_server.py    MCP JSON-RPC server (14 tools)
├── deep_research.py Multi-step research pipeline
├── pipeline.py      Durable execution engine
├── semantic.py      Vector embeddings + hybrid RRF search
├── taskqueue.py     SQLite priority queue for inbox
├── bindings.py      Pydantic Settings tool config
├── graph_data.py    Knowledge graph export
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

## Auto-Linking

Articles sharing ≥2 keywords are automatically connected with `[[wikilinks]]`. The linker runs on every article creation. Merge candidates (>80% keyword overlap) are flagged for review.

## Deep Research Pipeline

Multi-step autonomous research with durable execution:

```
plan → search → structure → cross-reference → synthesize → review → persist
```

Each step is retried with exponential backoff. Pipeline state is persisted to JSON — survives crashes and resumes from the last checkpoint. Human review gate before article creation.

## Semantic Search

Optional vector embeddings via `sentence-transformers` + `FAISS`. Hybrid search combines TF-IDF keyword scores with cosine similarity using Reciprocal Rank Fusion. Falls back gracefully to keyword-only when dependencies aren't installed.

```bash
pip install sentence-transformers faiss-cpu
```

## Related Repositories

| Repo | Contents |
|------|----------|
| [ai-kos](https://github.com/KRUZZZZY/ai-kos) | This package |
| [ai-kos-knowledge](https://github.com/KRUZZZZY/ai-kos-knowledge) | 71 knowledge articles |
| [ai-kos-archive](https://github.com/KRUZZZZY/ai-kos-archive) | Original ingested source docs |

## Credits

Architectural patterns inspired by Cloudflare's developer platform (Workflows, Queues, AI Search, Vectorize, Bindings). Embeddings via UKP Lab's sentence-transformers (TU Darmstadt). Vector search via Facebook AI Research's FAISS.

## License

MIT
