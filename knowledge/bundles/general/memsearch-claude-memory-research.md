---
id: 0ac4f240-fe6c-4514-a9c3-56b224d97b65
title: 'Research: Memsearch and Claude Code Memory Architecture'
slug: memsearch-claude-memory-research
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: volatile
sensitivity_label: internal
confidence: 0.8
keywords:
- memsearch
- claude-code
- memory
- ai-kos
- knowledge
- articles
- milvus
summary: Research on memsearch and Claude Code's native memory hierarchy for scaling
  AI-KOS beyond file-system context limits.
related:
- ai-kos
- docling-graph-research
- durable-execution-research
- harden-aws-ssm-jump-host
- ingest-file
- obsidian-graph-idea
- process-articles-backup-skills
- run-random-graph-suite
- session-writeback
provenance:
- inbox/Exploring AI Agents for Specifications.md
retrieval_count: 0
gap: false
topic: Memsearch for AI-KOS session/retrieval memory
tags:
- type/research-note
---

## Topic: 

## Key Notes
- Claude Code's native memory hierarchy: CLAUDE.md (static), Auto Memory (file-based), Auto Dream (async cleanup), KAIROS (always-on daemon)
- Critical bottleneck: Claude Code caps active memory index at 200 lines (~25KB) — everything beyond is invisible
- Memsearch replaces local grep with unlimited Milvus-backed vector+keyword hybrid search across all conversations
- Auto-summarizes every conversation and maintains continuous memory index across months
- Integration target: AI-KOS session-service (Port 8008) + retrieval-service (Port 8003) for indefinite episodic/semantic memory scaling
- Resolves linear performance degradation of flat-file index walks as corpus grows past 1000 documents

## Open Questions
- Memsearch vs Hermes built-in memory — which provides better cross-session context for AI-KOS?
- What's Milvus's resource footprint on the RTX 5070 Ti compared to Qdrant (already in use)?

## Sources
- Claude Code memory architecture docs
- memsearch GitHub