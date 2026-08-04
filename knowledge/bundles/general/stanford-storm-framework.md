---
id: 2507f976-5c06-4453-bea6-f65ed1b71081
title: 'Research: Stanford STORM Multi-Perspective Research Framework'
slug: stanford-storm-framework
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- storm
- stanford
- multi-perspective
- persona
- research
- synthesis
- ai
- knowledge
summary: 'Stanford STORM: multi-agent framework generating 5 expert personas per topic,
  each producing 5-10 sub-questions, with grounded Q&A, outline synthesis, and full
  article drafting. +25% structural organization.'
related: []
provenance:
- inbox/AI Deep Research Systems Analysis.md
retrieval_count: 0
gap: false
topic: Stanford STORM Research Framework
tags:
- type/research-note
---

## Topic: 

## Key Notes
- 5-stage pipeline: (1) Perspective Discovery — generates 5 expert personas (Practitioner, Academic, Skeptic, Economist, Historian), (2) Multi-Perspective Questioning — each persona creates 5-10 sub-questions, (3) Grounded Expert Conversations — web/DB searches answer each question set, (4) Outline Synthesis — aggregates Q&A, resolves contradictions, structures multi-level outline, (5) Full Article Drafting — generates complete report section by section.
- Evaluation results: +25% structural organization, +10% topic coverage breadth vs standard outline-driven baselines.
- Uses LangGraph/Python engine. Tools: Tavily (web search), ArXiv (academic), vector DBs. 3-5 minute pipeline.
- Key insight: single-prompt approaches miss depth because they rely on a unified perspective. Multi-perspective questioning surfaces angles a single query misses.

## Sources
- arXiv:2402.14207v2
- MindStudio STORM workflow guide