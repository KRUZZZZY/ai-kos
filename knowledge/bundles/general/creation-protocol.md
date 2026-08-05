---
id: 41c6aac1-1327-4768-85c5-aaaa4e53e242
title: AI-KOS Article Creation Protocol
slug: creation-protocol
type: process
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
keywords:
- creation
- protocol
- article
- ai-kos
- knowledge
- keywords
- template
- linking
summary: Standard protocol for creating any AI-KOS knowledge article. Follow this
  every time you preserve knowledge.
related:
- ai-kos
- ai-kos-mission
- ai-kos-plan
- article-types-guide
- auto-linker
- choosing-keywords
- docling-graph-research
- durable-execution-research
- harden-aws-ssm-jump-host
- hybrid-search-research
- ingest-file
- keyword-system
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
- ai-kos-spec-v1.5.md
retrieval_count: 0
tags:
- type/process
---


## Outcome
A concise, well-linked knowledge article is created in the database. It is connected to all related articles via keyword-based wikilinks. Duplicates are avoided.

## Prerequisites
- Hermes with ai-kos MCP server
- Knowledge of the 7 article types (see ai_kos_templates)

## Steps
1. IDENTIFY: Is this worth keeping? Skip trivia, chat logs, and things easily re-discovered. Keep: decisions made, bugs solved, architecture choices, research findings, reusable procedures.
2. CHECK DUPLICATES: Call ai_kos_search(query) to find existing articles on this topic. Call ai_kos_merge_candidates(slug) if a similar slug exists. If a near-duplicate is found, update the existing article instead of creating a new one.
3. CHOOSE TYPE: Pick the right article type — base for concepts, process for procedures, plan for roadmaps, help for project components, research-note for ongoing research, note for temporary ideas, mission for project definitions.
4. GENERATE KEYWORDS: Create 3-8 lowercase keywords. Include: the main topic, related concepts, the article type, any tool/technology mentioned. Keywords drive auto-linking — two articles sharing >=3 keywords get connected.
5. WRITE SUMMARY: Max 300 characters. Must be a single sentence that captures the article's value. This is what appears in search results.
6. WRITE CONTENT: Follow the template for the chosen type. Cap at ~5 paragraphs. Remove fluff, introductions, and conversational filler. Use imperative style for processes. Include concrete values, not vague descriptors.
7. CREATE: Call ai_kos_create(type, data) with the complete article data. The system automatically runs the linker after creation.
8. VERIFY: Call ai_kos_read(slug) to confirm the article was created. Check the 'related' field contains expected wikilinks. If links are missing, check keyword overlap with related articles.

## Related
[[ai-kos]] [[ai-kos-mission]] [[ai-kos-plan]] [[article-types-guide]] [[auto-linker]] [[choosing-keywords]] [[docling-graph-research]] [[durable-execution-research]] [[harden-aws-ssm-jump-host]] [[hybrid-search-research]] [[ingest-file]] [[keyword-system]] [[langgraph-orchestration-research]] [[memsearch-claude-memory-research]] [[networkx-implementation-notes]] [[obsidian-graph-idea]] [[oss-consolidation-strategy]] [[process-articles-backup-skills]] [[random-graph-simulation-suite]] [[run-random-graph-suite]] [[session-end-protocol]] [[session-writeback]]
