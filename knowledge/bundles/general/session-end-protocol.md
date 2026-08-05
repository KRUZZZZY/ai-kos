---
id: e26f3b1b-1e0e-4470-90d3-11d687d42b1c
title: 'Session-End Protocol: Preserving Knowledge into AI-KOS'
slug: session-end-protocol
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- session-end
- writeback
- preserve
- knowledge
- ai-kos
- skill
- protocol
summary: The session-end protocol preserves what Hermes learns during a session as
  permanent AI-KOS knowledge articles. Process articles back up skills; base articles
  capture concepts; research notes track ongoing work.
related:
- ai-kos
- ai-kos-mission
- ai-kos-plan
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
- session-2026-08-04-ai-kos-build
- session-writeback
provenance:
- ~/.hermes/skills/session-end/SKILL.md
retrieval_count: 0
gap: false
tags:
- type/base
---

The session-end protocol ensures that durable knowledge from Hermes sessions is not lost. At the end of significant sessions, Hermes reviews what was accomplished and creates AI-KOS articles. The protocol follows a 5-step priority system. Process articles come first — these are permanent backups for Hermes skills that the curator might archive due to inactivity. Base articles come second — concise concept articles (~5 paragraphs) for new knowledge. Research notes track ongoing investigations. Notes capture ideas for later. Before creating any article, Hermes searches AI-KOS to avoid duplicates. If keyword overlap exceeds 80% with an existing article, the existing one is updated instead. After creation, the linker connects new articles to the knowledge graph. The session-end skill is invoked with /skill session-end and automates this entire workflow.

## Related
[[ai-kos]] [[ai-kos-mission]] [[ai-kos-plan]] [[article-types-guide]] [[creation-protocol]] [[docling-graph-research]] [[durable-execution-research]] [[harden-aws-ssm-jump-host]] [[hybrid-search-research]] [[ingest-file]] [[langgraph-orchestration-research]] [[memsearch-claude-memory-research]] [[networkx-implementation-notes]] [[obsidian-graph-idea]] [[oss-consolidation-strategy]] [[process-articles-backup-skills]] [[random-graph-simulation-suite]] [[run-random-graph-suite]] [[session-2026-08-04-ai-kos-build]] [[session-writeback]]
