---
id: 4b2f48b9-683e-40cf-a977-d94ee0e50a25
title: 'Research: Hybrid Search Architectures'
slug: hybrid-search-research
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: volatile
sensitivity_label: internal
keywords:
- hybrid-search
- qdrant
- rrf
- ai-kos
- knowledge
- retrieval
- database
summary: Research notes on hybrid dense+sparse search architectures for AI-KOS retrieval.
related:
- ai-kos
- ai-kos-mission
- ai-kos-plan
- oss-consolidation-strategy
- qdrant-alloy-research
provenance:
- research-notes.md
retrieval_count: 0
topic: Hybrid Search for Knowledge Databases
tags:
- type/research-note
---


## Topic: 

## Key Notes
- Dense vectors (768-dim) provide semantic matching but miss exact terms
- Sparse vectors (BM25/SPLADE) catch exact keyword matches but miss synonyms
- Reciprocal Rank Fusion (RRF) combines both: score = sum(1/(k+rank+1))
- Cross-encoder reranking (MiniLM) adds +5-8% accuracy on top of RRF
- Qdrant supports native dense+sparse vector storage with FastEmbed integration

## Open Questions
- Is Qdrant overkill for a personal knowledge base with <1000 articles?
- Can keyword-based search + auto-linking replace vector search entirely?

## Sources
- Qdrant hybrid search docs
- BEIR benchmark results

## Related
[[ai-kos]] [[ai-kos-mission]] [[ai-kos-plan]]