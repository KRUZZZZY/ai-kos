---
id: d5fca6aa-e2ce-477e-baf4-277a8f64c33f
title: 'Plan: AI-KOS Architecture Modernization'
slug: ai-kos-architecture-modernization-plan
type: plan
created_at: '2026-08-05'
updated_at: '2026-08-05'
reviewed_at: '2026-08-05'
next_review_at: '2027-08-05'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- ai-kos
- plan
- architecture
- durable-execution
- vector-embeddings
- task-queue
- semantic-search
- modernization
summary: 'Phased implementation plan for the 4 AI-KOS architecture modernization modules:
  ResearchPipeline (durable execution), SemanticSearch (vector embeddings), TaskQueue
  (ingestion queue), and DeclarativeBindings (tool config). Ordered by priority with
  time estimates and risk mitigations.'
related:
- ai-kos-architecture-modernization-mission
- ai-kos-plan
- article-types-guide
- durable-execution-research
- oss-consolidation-strategy
- research-pipeline-how-it-works
- semantic-search-how-it-works
- setting-up-semantic-search
- using-the-research-pipeline
provenance:
- research-synthesis
retrieval_count: 0
gap: false
tags:
- type/plan
---

## Goal
Implement four Cloudflare-inspired architectural patterns into AI-KOS: durable execution for deep research (ResearchPipeline), vector embeddings for semantic search (SemanticSearch), task queue for ingestion (TaskQueue), and declarative bindings for tool config (DeclarativeBindings). All modules must be local-first, optional, and pass >80% test coverage without breaking existing functionality.

## Phases
- PHASE 1: ResearchPipeline (durable execution) — Highest priority. Build step-based pipeline class using json+pathlib for state persistence. Each step (plan, search, ingest, create, link, clean, review) wrapped in retry with exponential backoff. Pipeline state saved to .hermes/pipelines/<id>.json after each step. On resume, skip completed steps. Add human_review step that pauses for user approval before article creation. Tests: crash mid-pipeline, verify resume from last checkpoint. Estimated: 2-3 hours.
- PHASE 2: SemanticSearch (vector embeddings) — Medium priority. Optional module gated behind sentence-transformers import. Generate 384-dim embeddings via all-MiniLM-L6-v2. Store in FAISS flat index saved to knowledge/.vectors/. Hybrid search combines TF-IDF score and cosine similarity via RRF(score) = sum(1/(k+rank_i)) for k=60. Auto-linker gains semantic_similarity_threshold config option (default 0.7). Graceful fallback to keyword-only if deps missing. Tests: 5 queries where keyword misses but semantics hits. Estimated: 2-3 hours.
- PHASE 3: TaskQueue (ingestion pipeline) — Medium priority. SQLite table tasks(id, path, priority, status, attempts, created_at, last_error). Worker dequeue loop with SELECT ... ORDER BY priority, created_at LIMIT 1. Failed tasks → status=dead_letter after max_retries. Inbox watcher re-scans directory on ai_kos_clean. Parallel processing via ThreadPoolExecutor(max_workers=3). Tests: drop 10 files, verify all processed, force 1 failure, verify retry succeeds. Estimated: 2 hours.
- PHASE 4: DeclarativeBindings (tool config) — Low priority. Pydantic BaseSettings class loaded from config.yaml or env vars. Bindings replace per-call path params — ai_kos_ingest no longer needs filepath as first arg if KB_PATH is bound. Backward compat: explicit params override bindings. Wire into existing MCP tool definitions. Tests: verify param count reduction, verify explicit param override works. Estimated: 1 hour.

## Milestones
- M1: ResearchPipeline passes integration test — survives simulated mid-pipeline crash and resumes from checkpoint
- M2: SemanticSearch returns relevant results missed by keyword-only search (5 curated test queries)
- M3: TaskQueue processes 10 inbox files with 1 forced retry recovery in under 30s
- M4: DeclarativeBindings reduces ai_kos_ingest and ai_kos_create param count by >50%
- M5: Full AI-KOS test suite passes with all 4 modules installed
- M6: 80%+ coverage on new modules

## Risks
- sentence-transformers first-run downloads ~90MB model — test offline fallback path
- FAISS index rebuild on article changes — cache invalidation strategy needed; rebuild on write, not on read
- TaskQueue concurrent access to SQLite from multiple workers — use WAL mode + retry on SQLITE_BUSY
- Durable execution state file corruption on crash mid-write — atomic write via tempfile + os.replace
- DeclarativeBindings may break existing MCP tool callers — full backward compat required, explicit params override bindings
- Scope creep: each module could expand into its own sub-project — guard with strict acceptance criteria, ship MVP

## Related
[[ai-kos-architecture-modernization-mission]] [[ai-kos-plan]] [[article-types-guide]] [[durable-execution-research]] [[oss-consolidation-strategy]] [[research-pipeline-how-it-works]] [[semantic-search-how-it-works]] [[setting-up-semantic-search]] [[using-the-research-pipeline]]
