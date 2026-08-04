---
id: f63398a8-ad51-433e-bdb7-403e55ddf019
title: How to Ingest a File into AI-KOS
slug: ingest-file
type: process
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
keywords:
- ingest
- ai-kos
- knowledge
- articles
- pdf
- docx
- extract
summary: Step-by-step procedure for ingesting any file into the AI-KOS knowledge database.
related:
- ai-kos
- docling-graph-research
- durable-execution-research
- harden-aws-ssm-jump-host
- memsearch-claude-memory-research
- obsidian-graph-idea
- process-articles-backup-skills
- run-random-graph-suite
- session-writeback
provenance:
- ai-kos-skill.md
retrieval_count: 0
tags:
- type/process
---


## Outcome
File is converted into a concise, linked knowledge article with auto-generated wikilinks to related articles.

## Prerequisites
- Hermes with ai-kos MCP server registered
- File in inbox/ directory

## Steps
1. Drop the file into the inbox/ directory
2. Call ai_kos_ingest(filepath) via Hermes MCP to extract raw text
3. Read the extracted text and identify the core knowledge
4. Choose the appropriate article type (base/process/plan/help/research-note/note/mission)
5. Generate 3-8 lowercase keywords that capture the topic
6. Write a concise summary (max 300 chars)
7. Simplify the content into ~5 paragraphs following the template
8. Call ai_kos_create(type, data) to persist the article

## Related
[[ai-kos]] [[obsidian-graph-idea]] [[process-articles-backup-skills]] [[session-writeback]]