---
id: 9b38f29b-dcb5-4954-a907-f9420d8f09aa
title: AI-KOS Knowledge Database
slug: ai-kos
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
keywords:
- ai-kos
- knowledge
- database
- auto-link
- articles
- hermes
summary: AI-KOS is a self-building knowledge database that auto-links articles sharing
  3+ keywords.
related:
- ai-kos-mission
- ai-kos-plan
- docling-graph-research
- durable-execution-research
- harden-aws-ssm-jump-host
- hybrid-search-research
- ingest-file
- memsearch-claude-memory-research
- obsidian-graph-idea
- process-articles-backup-skills
- run-random-graph-suite
- session-writeback
provenance:
- specification-v1.5.md
retrieval_count: 0
tags:
- type/base
---


AI-KOS is a self-building knowledge database integrated with Hermes. It accepts any file format (PDF, DOCX, MD, TXT), extracts the text, and creates simplified .md articles. Each article has 3-8 keywords. When two articles share 3 or more keywords, the system automatically creates [[wikilinks]] between them. New articles are compared against existing ones — if keyword overlap exceeds 80%, they are flagged as merge candidates. Articles are capped at about 5 paragraphs to prevent context bloat when loaded into LLM prompts.

## Related
[[ai-kos-mission]] [[ai-kos-plan]] [[hybrid-search-research]] [[ingest-file]] [[obsidian-graph-idea]] [[process-articles-backup-skills]] [[session-writeback]]