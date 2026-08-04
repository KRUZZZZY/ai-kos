---
id: 776fce7f-d852-4b68-a7f1-3f841bbe0d6e
title: 'Mission: AI-KOS Self-Building Knowledge Database'
slug: ai-kos-mission
type: mission
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
keywords:
- mission
- ai-kos
- database
- hermes
- knowledge
- auto-link
- complete
summary: Project mission for AI-KOS — a self-building knowledge database with auto-linking
  and smart ingestion.
related:
- ai-kos
- ai-kos-plan
- hybrid-search-research
- process-articles-backup-skills
provenance:
- specification-v1.5.md
retrieval_count: 0
project: AI-KOS
tags:
- type/mission
---


## Purpose
Build a knowledge database where any file can be dropped in, automatically simplified into concise articles, and interconnected via keyword-based auto-linking. Designed as a Hermes MCP tool for long-term knowledge retention.

## Architecture
The system has four layers: (1) Ingestion — parses any file format and extracts raw text. (2) Simplification — Hermes reads the text and creates a concise ~5-paragraph article following one of 7 templates. (3) Storage — articles are stored as .md files with YAML frontmatter in the knowledge/ directory. (4) Linking — the auto-linker scans all articles and creates [[wikilinks]] between any pair sharing >=3 keywords. Merge candidates (>80% keyword overlap) are flagged for review. Everything is exposed as MCP tools so Hermes can ingest, create, search, and link autonomously.

## Dependencies
- Hermes agent
- Python 3.11+
- pydantic
- pyyaml

## Success Criteria
- Drop a PDF in inbox/ → Hermes creates a linked .md article
- Auto-linker connects articles with >=3 shared keywords
- Search finds articles by keyword or type
- Merge candidates are correctly identified at >80% overlap

## Related
[[ai-kos]] [[ai-kos-plan]] [[hybrid-search-research]] [[process-articles-backup-skills]]