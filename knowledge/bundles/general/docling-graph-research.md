---
id: 9a99e60b-a6af-4789-8ae3-24c197b4265d
title: 'Research: Docling-Graph for Document Ingestion'
slug: docling-graph-research
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: volatile
sensitivity_label: internal
confidence: 0.8
keywords:
- docling
- ingestion
- ai-kos
- knowledge
- articles
- parsing
- chunking
summary: Research on replacing the custom ingestion pipeline with IBM's docling-graph
  for layout-aware PDF/Office parsing and structure-aware chunking.
related:
- ai-kos
- ai-kos-mission
- ai-kos-plan
- article-types-guide
- creation-protocol
- deep-research-pipeline-workflow
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
- processing-inbox-with-taskqueue
- random-graph-simulation-suite
- run-random-graph-suite
- session-end-protocol
- session-writeback
- taskqueue-how-it-works
provenance:
- inbox/Exploring AI Agents for Specifications.md
- inbox/Leverage Open Source For Coding Efficiency.md
retrieval_count: 0
gap: false
topic: Docling-Graph as AI-KOS ingestion backend
tags:
- type/research-note
---

## Topic: 

## Key Notes
- Docling-graph converts complex PDFs, images, Office docs, HTML into structured representations preserving layout metadata, reading order, and table grids
- Implements structure-aware chunking with real provider-specific tokenizers and 20% safety margin for system prompts
- Maps document layouts to NetworkX directed graphs with stable identifiers and edge metadata
- Multi-pass extraction contracts (staged, delta) with programmatic model merging — auto-consolidates chunked extractions
- Validates against target Pydantic schemas — output is directly OKF-compatible, replacing both ingestion-service and consolidation-service
- 100% local execution — no data leaves the machine, matching AI-KOS's data sovereignty requirements
- Comparison with LlamaParse: Docling wins for local-first deployments; LlamaParse is cloud-only with commercial tiering

## Open Questions
- How does Docling handle OCR for scanned PDFs without embedded text layers?
- What's the throughput for batch processing 100+ PDFs on the RTX 5070 Ti?

## Sources
- IBM docling-graph GitHub
- Docling documentation

## Related
[[ai-kos]] [[ai-kos-mission]] [[ai-kos-plan]] [[article-types-guide]] [[creation-protocol]] [[deep-research-pipeline-workflow]] [[durable-execution-research]] [[harden-aws-ssm-jump-host]] [[hybrid-search-research]] [[ingest-file]] [[langgraph-orchestration-research]] [[memsearch-claude-memory-research]] [[networkx-implementation-notes]] [[obsidian-graph-idea]] [[oss-consolidation-strategy]] [[process-articles-backup-skills]] [[processing-inbox-with-taskqueue]] [[random-graph-simulation-suite]] [[run-random-graph-suite]] [[session-end-protocol]] [[session-writeback]] [[taskqueue-how-it-works]]
