---
id: 11526ae5-4d82-4fa9-979f-a1f6d8aadf96
title: Session Writeback Protocol
slug: session-writeback
type: process
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
keywords:
- session
- writeback
- ai-kos
- knowledge
- articles
- preserve
- skill
- protocol
summary: Protocol for preserving what Hermes learns during a session as permanent
  AI-KOS knowledge articles.
related:
- ai-kos
- creation-protocol
- docling-graph-research
- durable-execution-research
- harden-aws-ssm-jump-host
- ingest-file
- memsearch-claude-memory-research
- obsidian-graph-idea
- process-articles-backup-skills
- run-random-graph-suite
- session-end-protocol
provenance:
- ai-kos-creation-protocol.md
retrieval_count: 0
tags:
- type/process
steps:
- 'Load the session-end skill: /skill session-end'
- 'REVIEW: Scan the conversation for decisions, bugs solved, procedures, knowledge
  gained, configurations, open questions'
- 'CHECK: Search AI-KOS for existing articles on each topic. If found, update instead
  of creating duplicates.'
- 'PRIORITIZE: Process articles first (skill backups), base articles second (concepts),
  research notes third, notes last.'
- 'CREATE: For each insight — generate 3-8 keywords, write summary, follow the template,
  call ai_kos_create'
- 'LINK: Run ai_kos_link to connect new articles to the knowledge graph'
- 'VERIFY: Run ai_kos_stats to show final state and report to user'
---


## Outcome
All durable knowledge from the session is preserved as interconnected AI-KOS articles. Future sessions can retrieve this knowledge via ai_kos_search. Hermes skills are backed up as process articles.

## Prerequisites
- Completed a Hermes session with new learnings
- AI-KOS MCP server running

## Steps
1. REVIEW THE SESSION: At the end of a significant session (or when asked), review what was accomplished. Identify: decisions made, bugs solved and their root causes, new procedures discovered, architecture choices, research findings, configuration changes.
2. DETERMINE WHAT TO KEEP: Filter out: trivia, temporary state, file paths that will change, task progress on completed work. Keep: reusable knowledge, hard-won debugging insights, design rationale, tool configurations, research notes.
3. FOR EACH INSIGHT: Follow the Creation Protocol (see [[creation-protocol]]). Choose the right article type. Check for existing articles to update instead of creating duplicates.
4. PRIORITIZE BY TYPE: Process articles first (procedures you'll need again). Base articles second (concepts you now understand). Research notes third (ongoing investigations). Notes last (ideas for later).
5. LINK TO SESSION CONTEXT: In the 'provenance' field, reference the session ID or a brief descriptor so you can trace where the knowledge came from.
6. VERIFY THE GRAPH: After creating all articles, run ai_kos_link to ensure the knowledge graph is fully connected. Check for unexpected merge candidates — they may reveal that two separate sessions discovered the same thing.
7. CLEAN UP: Archive any notes that became base articles by removing them or updating their type.

## Related
[[ai-kos]] [[ingest-file]] [[obsidian-graph-idea]] [[process-articles-backup-skills]]