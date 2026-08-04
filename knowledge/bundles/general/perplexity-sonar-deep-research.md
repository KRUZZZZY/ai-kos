---
id: 06b101ae-6122-4ff6-8435-8f332602f101
title: 'Research: Perplexity Sonar Deep Research Architecture'
slug: perplexity-sonar-deep-research
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- perplexity
- sonar
- deep-research
- span-indexing
- multi-pass
- ai
- knowledge
summary: 'Perplexity Sonar Deep Research: span-level content indexing, 20-50 parallel
  search queries, 200+ sources per report, sub-2-minute execution at ~$0.40/run.'
related:
- ai-deep-research-systems
- gemini-deep-research-architecture
- openai-deep-research-architecture
provenance:
- inbox/AI Deep Research Systems Analysis.md
retrieval_count: 0
gap: false
topic: Perplexity Sonar Deep Research
tags:
- type/research-note
---

## Topic: 

## Key Notes
- Span-level indexing: content understanding module parses pages into discrete semantic sections and atomic text spans. Retrieves exact paragraphs without surrounding irrelevant material.
- Multi-pass fan-out search: decomposes query into 20-50 targeted parallel searches, retrieves from 200+ sources per report, applies cross-document reconciliation to resolve contradictions.
- Performance: delivers full reports in under 2 minutes using high-throughput inference accelerators. Estimated API cost ~$0.40 per research run.
- Contrast with Gemini/OpenAI: focuses on search index control and retrieval optimization rather than workspace integration or RL reasoning. Optimized for speed and cost over depth.

## Sources
- Perplexity API docs
- LYFE AI Perplexity guide