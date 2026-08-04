---
id: f6712a0d-3df1-425e-bf45-f868f0ee1fd1
title: 'AI-KOS Deep Research Pipeline: Ingest-to-Article Workflow'
slug: deep-research-pipeline-workflow
type: process
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.9
keywords:
- deep-research
- pipeline
- ingest
- ingestion
- firecrawl
- auto-link
- ai-kos
- pmc
summary: 'Step-by-step procedure for running the AI-KOS deep research pipeline: search
  the web via Firecrawl, write results to inbox, ingest files, create knowledge articles,
  run auto-linker, and clean up.'
related:
- research-female-orgasm-firecrawl-findings
- test-pipeline-verification
provenance:
- session-2026-08-04-hermes
- ai_kos/deep_research.py
retrieval_count: 0
gap: false
tags:
- type/process
---

## Outcome
New knowledge articles appear in the AI-KOS knowledge base, searchable and auto-linked. Inbox is clean. Provenance traces back to the original Firecrawl search results.

## Prerequisites
- AI-KOS MCP server running (or direct Python import of ai_kos package)
- Firecrawl API key (fc-...) for web search/scrape
- pmc_to_pdf() helper from ai_kos.deep_research for clean PMC extraction
- Knowledge of the 7 article types and their required fields (see ai_kos_templates)

## Steps
1. Search: run Firecrawl search across 3-6 research dimensions (e.g., neurophysiology, hormones, types). Use direct API if web_search tool is unavailable: curl -X POST https://api.firecrawl.dev/v2/search with FIRECRAWL_API_KEY
2. Scrape key papers: for each dimension, extract the most relevant PMC paper. Run URLs through pmc_to_pdf() to get clean article text instead of NIH boilerplate. Limit to 3000-5000 chars per paper for synthesis.
3. Write inbox files: save synthesis as inbox/<topic>-synthesis.md and raw findings as inbox/<topic>-findings.md. These become provenance sources.
4. Ingest: run ai_kos_ingest on each inbox file. Confirm it returns raw_content + suggested_type + slug. Note: suggested_type is heuristic — override if wrong (e.g., findings with numbered lists get misclassified as 'process').
5. Create articles: use ai_kos_create with the ingested content. For synthesis → type=base. For findings → type=research-note with key_notes, open_questions, and sources arrays.
6. Watch limits: summary max 300 chars. Slug must match ^[a-z0-9]+(?:-[a-z0-9]+)*$ — strip all punctuation. Title max 200 chars. Keywords 3-8 lowercase.
7. Auto-link: create_article runs the linker automatically. Verify with ai_kos_search that new articles appear in results. If articles don't cross-link, check that they share >=3 keywords.
8. Clean: run ai_kos_clean to move inbox files to archive/. Verify inbox is empty.