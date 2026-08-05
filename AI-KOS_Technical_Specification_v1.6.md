# AI-KOS Technical Specification
# Version 1.6

> **Status:** Authoritative
> **Version:** 1.6.0
> **Target:** Linux | Python 3.11+ | 32 GB RAM recommended
> **Updated:** 2026-08-05

---

## 1. System Overview

AI-KOS is a self-building knowledge database. Files are dropped into an inbox, ingested, simplified by an AI agent, and persisted as structured knowledge articles. Articles are automatically linked via shared keyword overlap (≥2 keywords → `[[wikilink]]`). The system ships as a focused Python package with a 14-tool MCP server for Hermes/AI agent integration.

### 1.1 Design Principles

- **Local-first.** No external services required. All storage is local filesystem + SQLite.
- **Single package.** Not a microservice stack. `pip install ai-kos` is the entire system.
- **AI-mediated.** The Python code handles extraction, storage, linking. AI agents (Hermes) handle simplification, classification, synthesis.
- **Optional enhancements.** Semantic search and durable execution are opt-in modules, not core dependencies.

---

## 2. Repository Layout

```
ai-kos/
├── ai_kos/                 # Python package (14 modules)
│   ├── __init__.py         # v1.6.0
│   ├── articles.py         # CRUD + auto-link trigger
│   ├── bindings.py         # Pydantic Settings tool config
│   ├── cli.py              # Command-line interface
│   ├── config.py           # YAML config loader
│   ├── deep_research.py    # Multi-step research pipeline
│   ├── graph_data.py       # Knowledge graph JSON export
│   ├── ingestion.py        # PDF/DOCX/MD/TXT extraction
│   ├── linker.py           # Keyword overlap → [[wikilinks]]
│   ├── mcp_server.py       # MCP JSON-RPC server (14 tools)
│   ├── pipeline.py         # Durable execution engine
│   ├── schemas.py          # 7 article types (Pydantic v2)
│   ├── search.py           # TF-IDF full-text search
│   ├── semantic.py         # Vector embeddings + hybrid RRF search
│   └── taskqueue.py        # SQLite priority queue for inbox
├── tests/                  # pytest suite (140 tests)
├── templates/              # Article type YAML templates
├── config.yaml             # Runtime configuration
├── pyproject.toml          # Build + dependency config
├── README.md               # This file
└── AI-KOS_Technical_Specification_v1.5.md   # Previous spec (historical)
```

Runtime directories (gitignored, managed separately):
```
knowledge/   → KRUZZZZY/ai-kos-knowledge (71 articles, Obsidian vault)
archive/     → KRUZZZZY/ai-kos-archive (14 ingested source docs)
projects/    → Separate repos per project
inbox/       → Transient file drop zone
```

---

## 3. Article System

### 3.1 Article Types

| Type | Key Fields | Purpose |
|------|-----------|---------|
| base | content | Factoid / Wikipedia-style concept (~5 paragraphs) |
| process | steps[], outcome, prerequisites | Step-by-step procedure |
| plan | goal, phases[], milestones[], risks[] | Planning document |
| help | project, component, explanation, examples[] | Component explanation |
| research-note | topic, key_notes[], open_questions[], sources[] | Research findings |
| note | content, related_project, actionable | Temporary note |
| mission | project, purpose, architecture, dependencies[], success_criteria[] | Project definition |

### 3.2 Common Frontmatter

All articles share:
```
id, title, slug, type, created_at, updated_at, reviewed_at, next_review_at
stability (stable|moderate|volatile), confidence (0.0-1.0), sensitivity_label
keywords (3-8), summary (≤300 chars), related[], provenance[], tags[]
```

### 3.3 Storage

Articles stored as markdown files with YAML frontmatter at `knowledge/bundles/general/{slug}.md`. The `knowledge/` directory is an Obsidian vault — `[[wikilinks]]` render as graph connections.

---

## 4. Auto-Linking System

### 4.1 Algorithm

1. Scan all articles in `knowledge/bundles/general/`
2. For each pair of articles, intersect keyword sets
3. If shared keywords ≥ `min_keyword_overlap` (default 2) → create `[[wikilink]]` in both articles
4. If keyword overlap ratio > `merge_threshold` (default 0.80) → flag as merge candidate

### 4.2 Triggers

- **On create:** Linker runs automatically after `create_article()`
- **On update:** Linker runs after `update_article()`
- **Manual:** `ai_kos_link` MCP tool or `ai-kos link` CLI

### 4.3 Configuration

```yaml
linking:
  min_keyword_overlap: 2    # Minimum shared keywords to link
  merge_threshold: 0.80     # Overlap ratio for merge candidates
```

---

## 5. Search System

### 5.1 TF-IDF (Core)

- Tokenizer: lowercase, alphanumeric ≥2 chars, stop-word removal
- TF-IDF scoring with normalized term frequency
- Keyword match bonus: +30% per matching keyword
- Snippet extraction from article body
- Type filtering, incremental index updates

### 5.2 Semantic Search (Optional)

- **Dependencies:** `sentence-transformers`, `faiss-cpu`
- **Model:** all-MiniLM-L6-v2 (384-dim embeddings, ~90MB)
- **Index:** FAISS IndexFlatIP (inner product on normalized vectors → cosine similarity)
- **Fusion:** Reciprocal Rank Fusion: `score = Σ 1/(k + rank_i)` where k=60
- **Fallback:** Graceful degradation to TF-IDF-only when deps missing

### 5.3 Hybrid Search API

```python
from ai_kos.semantic import hybrid_search
results = hybrid_search("query", top_k=10, min_semantic_threshold=0.7)
# Returns: [{slug, title, score, tfidf_rank, semantic_rank, semantic_score}, ...]
```

---

## 6. Ingestion System

### 6.1 Supported Formats

| Format | Extensions | Extraction Method |
|--------|-----------|-------------------|
| Text | .md, .txt, .rst, .org | Direct read |
| Code | .py, .js, .ts, .rs, .go, ... | Direct read (classified as code) |
| PDF | .pdf | Docling → PyPDF2 → pdftotext |
| DOCX | .docx, .doc | Docling → python-docx |
| Other | .csv, .html, .xml | Best-effort text read |

### 6.2 Type Detection

Heuristic classifier examines content for indicators:
- Step patterns (`step 1`, `1.`, `## steps`) → process
- Research patterns (`methodology`, `findings`, `abstract`) → research-note
- Plan patterns (`milestone`, `phase`, `roadmap`) → plan
- Architecture patterns (`api`, `database`, `service`) → mission
- Default → base

### 6.3 TaskQueue (Optional Enhancement)

SQLite-backed priority queue with thread-pool processing:

```python
from ai_kos.taskqueue import TaskQueue
q = TaskQueue()
q.scan_inbox()                            # Discover files
q.process_all(handler=ingest_handler)     # Process with 3 workers
```

Features: priority ordering, retry with exponential backoff, dead-letter isolation, WAL-mode concurrency.

---

## 7. Deep Research Pipeline

### 7.1 Flow

```
plan → search → structure → cross-reference → synthesize → review → persist
```

### 7.2 Step Details

| Step | Action | Input | Output |
|------|--------|-------|--------|
| plan | Decompose question into 5 sub-questions + perspectives | question | ResearchPlan |
| search | Web search each sub-question via external search_fn | sub_questions, queries | raw_findings[] |
| structure | Classify raw results into typed SourceFinding objects | raw_findings | structured_findings[] |
| cross_ref | Compare against AI-KOS knowledge base | structured_findings | cross_references[] |
| synthesize | Generate markdown synthesis report | all findings | synthesis_report |
| review | Human approval gate (optional) | pipeline state | approved/rejected |
| persist | Create research-note + base articles in AI-KOS | synthesis | article slugs |

### 7.3 Durable Execution (pipeline.py)

Each step is wrapped with retry (3 attempts, exponential backoff: 2s, 4s, 8s). Pipeline state is atomically persisted to `knowledge/pipelines/{id}.json` after each step. Crashes are recoverable — `ResearchPipeline.load(path).resume()` skips completed steps.

### 7.4 Research Plan Generation

STORM-style perspective-driven decomposition:
- Technical/Implementation angle
- Comparative/Trade-off angle
- Practical/Applied angle
- Critical/Limitations angle
- Future/Evolution angle

---

## 8. Scheduler System (Via Hermes)

AI-KOS ships with presets for Hermes cronjob scheduling:
```
# Daily deep research
schedule: "0 9 * * *"
prompt: Run the AI-KOS deep research pipeline on today's most relevant topic
skills: [deep-research-pipeline-workflow]
```

Jobs are defined in `.hermes/cron/` and managed via `hermes cron`.

---

## 9. Bindings System

Declarative tool configuration via Pydantic Settings. Resolution order: environment variables (`AI_KOS_*` prefix) → `config.yaml` → hardcoded defaults.

### 9.1 Available Bindings

| Group | Binding | Default | Description |
|-------|---------|---------|-------------|
| paths | knowledge_dir | knowledge | Article storage root |
| paths | inbox_dir | inbox | File drop zone |
| paths | templates_dir | templates | Article templates |
| paths | archive_dir | archive | Ingested source archive |
| paths | rejected_dir | rejected | Rejected files |
| paths | projects_dir | projects | Project files |
| pipeline | pipelines_dir | pipelines | Pipeline state storage |
| search | min_keyword_overlap | 2 | Auto-link threshold |
| search | merge_threshold | 0.80 | Merge candidate threshold |
| search | semantic_enabled | true | Enable semantic search |
| search | semantic_threshold | 0.7 | Min cosine similarity |
| taskqueue | taskqueue_max_workers | 3 | Worker thread count |
| taskqueue | taskqueue_max_retries | 3 | Max retry attempts |
| taskqueue | taskqueue_retry_delay | 2.0 | Base retry delay (seconds) |

---

## 10. MCP Server

### 10.1 Tool Inventory (14 tools)

| Tool | Function | Category |
|------|----------|----------|
| ai_kos_ingest | Extract text from file | Ingestion |
| ai_kos_create | Create knowledge article | CRUD |
| ai_kos_read | Read article by slug | CRUD |
| ai_kos_list | List all articles | CRUD |
| ai_kos_search | Full-text search | Search |
| ai_kos_compare | Find similar articles | Search |
| ai_kos_link | Run auto-linker | Linking |
| ai_kos_merge_candidates | Check for merge candidates | Linking |
| ai_kos_stats | Health statistics | Admin |
| ai_kos_templates | Show article templates | Admin |
| ai_kos_graph | Export knowledge graph | Admin |
| ai_kos_clean | Clean inbox → archive/projects/rejected | Inbox |
| ai_kos_research_plan | Generate research plan | Research |
| ai_kos_research_persist | Persist research findings | Research |

### 10.2 Protocol

JSON-RPC 2.0 over stdio. Initialize with `protocolVersion: "2025-06-18"`. Compatible with Hermes MCP client and any MCP-compliant agent.

---

## 11. Dependencies

### 11.1 Core (required)

```
pydantic>=2.0          # Article schemas
pydantic-settings>=2.0 # Bindings configuration
pyyaml>=6.0            # Config + frontmatter parsing
mcp>=1.0               # MCP server protocol
```

### 11.2 Optional

```
docling>=2.0           # PDF/DOCX extraction (high quality)
PyPDF2>=3.0            # PDF extraction (fallback)
python-docx>=1.0       # DOCX extraction (fallback)
sentence-transformers  # Vector embeddings (semantic search)
faiss-cpu              # Vector similarity index (semantic search)
```

---

## 12. Testing

140 tests across 8 test files. Run with:

```bash
pip install -e ".[dev]"
pytest                          # Full suite (140 passed, 9 skipped)
pytest --cov=ai_kos             # With coverage report
```

Key coverage: pipeline 95%, taskqueue 96%, bindings 98%, semantic 36% (logic paths 100%, FAISS paths require optional deps).

---

## 13. Configuration Reference

Full `config.yaml`:

```yaml
paths:
  knowledge_dir: knowledge
  inbox_dir: inbox
  templates_dir: templates
  archive_dir: archive
  rejected_dir: rejected
  projects_dir: projects

search:
  default_top_k: 50
  fusion: rrf

linking:
  min_keyword_overlap: 2
  merge_threshold: 0.80

article:
  max_paragraphs: 5
  min_keywords: 3
  max_keywords: 8
  summary_max_chars: 300

decay:
  lambda_stable: 0.01
  lambda_moderate: 0.05
  lambda_volatile: 0.15
  critical: 0.3
```

---

## 14. Article Index Cache

### 14.1 Design

`_ArticleIndex` is an in-memory cache of slug→filepath + slug→frontmatter mappings. It replaces per-call filesystem scans with O(1) dictionary lookups. Built once on first access, incrementally updated on writes.

### 14.2 Lifecycle

- **Build:** First call to any function that reads articles triggers a single `rglob("*.md")` scan of `knowledge/`. YAML frontmatter is parsed and cached.
- **Update:** `create_article()`, `update_article()`, and `delete_article()` call `index.upsert()` or `index.remove()` — no full rebuild needed.
- **Invalidate:** `_refresh_index()` forces a full rebuild on next access (for external file changes).

### 14.3 Consumers

- `_slug_path(slug)` — O(1) filepath lookup (was O(n) rglob per call)
- `list_articles()` — returns from cache (was O(n) YAML parse every call)
- `stats()` — computed from cached frontmatter (was O(n) filesystem scan)
- `find_merge_candidates()` — iterates cached dict, not filesystem

### 14.4 Scaling

At 71 articles the improvement is imperceptible. At 500 it eliminates noticeable latency. At 5000 it prevents catastrophic degradation — `list_articles()` goes from 5000 YAML parses to zero.

---

## 15. Schema Migration System

### 15.1 Design

Articles are markdown files, not SQL rows. Migrations are pure-Python transforms: `(frontmatter_dict, body_text) → (frontmatter_dict, body_text)`. Each migration is registered with a version number and applied in order.

### 15.2 Registration

```python
from ai_kos.migrate import register

@register(version=2, name="add_new_field")
def _add_new_field(fm, body):
    fm["new_field"] = "default_value"
    return fm, body
```

Migrations are sorted by version and applied sequentially. The `schema_version` field in each article's frontmatter tracks which migrations have been applied.

### 15.3 Execution

- **Idempotent:** Checking `fm.get("schema_version", 0) >= target_version` before applying prevents double-runs.
- **Atomic writes:** `tempfile + os.replace` ensures no partial writes if the process crashes.
- **Dry-run:** `run_migrations(dry_run=True)` previews changes without writing.
- **CLI:** `ai-kos migrate [--dry-run]`
- **MCP:** `ai_kos_migrate` tool

### 15.4 Built-in Migrations

| Version | Name | Description |
|---------|------|-------------|
| 1 | add_schema_version | Adds `schema_version: 1` to articles without it (baseline) |

### 15.5 Adding a Migration

1. Increment `CURRENT_SCHEMA_VERSION` in `migrate.py`
2. Write a transform function decorated with `@register(version=N, name="...")`
3. The function receives `(frontmatter_dict, body_str)` and returns `(frontmatter_dict, body_str)`
4. Run `ai-kos migrate --dry-run` to preview
5. Run `ai-kos migrate` to apply

---

## 16. MCP Server Async Architecture

### 16.1 Problem

The MCP server runs on an asyncio event loop. All 15 tool handlers were called synchronously inside an async function — every `yaml.safe_load()`, file read, and linker scan blocked the event loop. One slow article search would block all concurrent agent requests.

### 16.2 Solution

All blocking I/O is offloaded to a thread pool via `asyncio.to_thread()` (Python 3.9+ stdlib). The `handle_call_tool` handler extracts tool dispatch into a pure sync function `_dispatch_tool()` and calls it via:

```python
result = await asyncio.to_thread(_dispatch_tool, name, arguments)
```

This is the recommended pattern from Python docs and the Temporal SDK. No rewrite of the sync article/search code needed — just a thread-pool wrapper in the server layer.

### 16.3 Tool Inventory (15 tools)

| Tool | Thread-pool? | Reason |
|------|-------------|--------|
| ai_kos_ingest | Yes | PDF/DOCX extraction |
| ai_kos_create | Yes | YAML parse + file write + linker trigger |
| ai_kos_search | Yes | TF-IDF index scan |
| ai_kos_read | Yes | File read + YAML parse |
| ai_kos_link | Yes | O(n²) article scan |
| ai_kos_list | Yes | Article listing |
| ai_kos_merge_candidates | Yes | Keyword overlap computation |
| ai_kos_templates | No | Pure in-memory dict |
| ai_kos_graph | Yes | Graph export |
| ai_kos_compare | Yes | TF-IDF comparison |
| ai_kos_stats | Yes | Stats from index |
| ai_kos_clean | Yes | Filesystem operations |
| ai_kos_research_plan | Yes | Plan generation |
| ai_kos_research_persist | Yes | Article creation |
| ai_kos_migrate | Yes | Bulk filesystem writes |

---

## 17. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.6.1 | 2026-08-05 | Article index cache, async MCP server (asyncio.to_thread), schema migration system, schema_version field. Performance + architecture fixes. |
| 1.6.0 | 2026-08-05 | Pipeline, SemanticSearch, TaskQueue, Bindings modules. Repo split. |
| 1.5.0 | 2026-08-04 | Deep research pipeline. MCP server (14 tools). 48 articles. |
| 1.0-1.4 | 2026-07 | Initial builds, microservice architecture (deprecated). |
