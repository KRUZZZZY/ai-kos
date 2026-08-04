---
id: 4f5ad2a0-ea22-495f-8ace-b6a82e098ad7
title: Process Articles as Skill Backups
slug: process-articles-backup-skills
type: help
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
keywords:
- process
- skill
- backup
- ai-kos
- knowledge
- articles
- hermes
summary: Why AI-KOS process articles serve as permanent backups for Hermes skills
  that get archived by the curator.
related:
- ai-kos
- ai-kos-mission
- article-types-guide
- docling-graph-research
- durable-execution-research
- harden-aws-ssm-jump-host
- ingest-file
- memsearch-claude-memory-research
- obsidian-graph-idea
- run-random-graph-suite
- session-end-protocol
- session-writeback
provenance:
- hermes-agent-skill.md
- ai-kos-spec-v1.5.md
retrieval_count: 0
project: AI-KOS + Hermes
component: Skill preservation via process articles
tags:
- type/help
---


## Component
Hermes has a curator system that tracks skill usage. Skills created by agents that go unused for a configured period are marked stale, then archived. This is good for keeping the skill set lean, but it means rarely-used procedures can disappear. AI-KOS process articles solve this problem. When Hermes discovers or uses a procedure, it should create a process article in AI-KOS. The article stores the step-by-step instructions, outcome, and prerequisites permanently — it's just a .md file in knowledge/, immune to the curator's cleanup. Next time that procedure is needed, ai_kos_search finds the process article, and Hermes can follow it or even recreate the skill from it. Process articles also work for procedures that are too niche to justify a full Hermes skill — one-off debugging workflows, environment setup sequences, or project-specific build steps.

## Examples
- Skill 'fix-docker-network' used once, curator archives it after 30 days → process article 'fix-docker-network' remains in AI-KOS forever
- Discovered a 12-step procedure for resetting the GPU after a CUDA OOM → create process article, no need for a Hermes skill

## Related
[[ai-kos]] [[ai-kos-mission]] [[article-types-guide]] [[ingest-file]] [[obsidian-graph-idea]] [[session-writeback]]