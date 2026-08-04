---
id: 91fd7051-6b39-4b39-98d9-2ee03a7034c2
title: 'Mission: AI-KOS Deep Research Tool'
slug: deep-research-tool-mission
type: mission
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- mission
- deep-research
- ai
- autonomous
- synthesis
- search
- ai-kos
summary: Build an autonomous deep research tool for AI-KOS that decomposes questions,
  searches the web, cross-references with the knowledge base, and persists structured
  findings as articles.
related:
- ai-deep-research-systems
provenance:
- ai_kos/deep_research.py
retrieval_count: 0
gap: false
project: AI-KOS Deep Research
tags:
- type/mission
---

## Purpose
Add autonomous deep research capabilities to AI-KOS: decompose any research question into sub-questions, search the web, cross-reference with existing knowledge, synthesize findings, and persist as linked articles.

## Architecture
The deep research engine follows a 4-phase pipeline inspired by the best features of Gemini, OpenAI, Perplexity, and STORM. Phase 1 (PLAN): The research question is decomposed into 3-5 sub-questions with specific search queries and 5 investigation perspectives (technical, comparative, practical, critical, future). This is STORM-style perspective-driven questioning. Phase 2 (SEARCH): For each sub-question, Hermes executes web_search + web_extract to gather sources. This is Perplexity-style multi-pass fan-out search. Phase 3 (CROSS-REFERENCE): Findings are compared against the AI-KOS knowledge base. Each finding is classified as confirming, contradicting, extending, or new relative to existing knowledge. Phase 4 (PERSIST): Findings are saved as research-note articles (per sub-question) and a base synthesis article. The linker automatically connects new articles to the knowledge graph. Exposed as 2 MCP tools: ai_kos_research_plan (generate plan) and ai_kos_research_persist (save findings). The actual web search execution is done by Hermes using its built-in tools.

## Dependencies
- Hermes web_search/web_extract tools
- AI-KOS articles/linker
- Python 3.11+

## Success Criteria
- Plan generation produces 5 sub-questions + 5 perspectives for any research topic
- Cross-reference correctly identifies confirm/contradict/extend/new relationships
- Research findings persist as linked AI-KOS articles
- Full pipeline: plan → search → cross-reference → persist works end-to-end