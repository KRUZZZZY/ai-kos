---
id: 2036ac89-a11b-4a14-ad6e-87a2d9185fd2
title: AI-KOS v1.5 Development Plan
slug: ai-kos-plan
type: plan
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: moderate
sensitivity_label: internal
keywords:
- ai-kos
- plan
- knowledge
- database
- roadmap
- features
summary: Development plan for AI-KOS v1.5 — self-building knowledge database with
  auto-linking.
related:
- ai-kos
- ai-kos-architecture-modernization-plan
- ai-kos-mission
- article-types-guide
- creation-protocol
- docling-graph-research
- durable-execution-research
- harden-aws-ssm-jump-host
- hybrid-search-research
- ingest-file
- langgraph-orchestration-research
- memsearch-claude-memory-research
- networkx-implementation-notes
- obsidian-graph-idea
- oss-consolidation-strategy
- process-articles-backup-skills
- random-graph-simulation-suite
- run-random-graph-suite
- session-end-protocol
- session-writeback
provenance:
- specification-v1.5.md
retrieval_count: 0
tags:
- type/plan
---


## Goal
Build a self-building knowledge database that auto-links articles and detects duplicates.

## Phases
- Phase 1: Core schemas — 7 article types with Pydantic validation
- Phase 2: Auto-linker — >=3 shared keywords → wikilinks
- Phase 3: Smart ingestion — parse any file, detect type, suggest template
- Phase 4: MCP server — expose all tools to Hermes
- Phase 5: Qdrant hybrid search integration

## Milestones
- All 7 templates working
- Auto-linker producing correct wikilinks
- Hermes can ingest and search autonomously

## Risks
- Qdrant dependency for vector search
- Keyword extraction quality depends on AI summarization

## Related
[[ai-kos]] [[ai-kos-architecture-modernization-plan]] [[ai-kos-mission]] [[article-types-guide]] [[creation-protocol]] [[docling-graph-research]] [[durable-execution-research]] [[harden-aws-ssm-jump-host]] [[hybrid-search-research]] [[ingest-file]] [[langgraph-orchestration-research]] [[memsearch-claude-memory-research]] [[networkx-implementation-notes]] [[obsidian-graph-idea]] [[oss-consolidation-strategy]] [[process-articles-backup-skills]] [[random-graph-simulation-suite]] [[run-random-graph-suite]] [[session-end-protocol]] [[session-writeback]]
