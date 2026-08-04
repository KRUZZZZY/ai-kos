---
id: f995de57-0c8b-4d7f-ad32-fa957470f249
title: 'Research: Qdrant Alloy and FastEmbed for Hybrid Search'
slug: qdrant-alloy-research
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: volatile
sensitivity_label: internal
confidence: 0.8
keywords:
- qdrant
- fastembed
- hybrid-search
- rrf
- dense
- sparse
- ai-kos
summary: Research on replacing custom embedding/indexing microservices with Qdrant's
  native FastEmbed for in-process dense+sparse vector generation.
related:
- hybrid-search-research
provenance:
- inbox/Leverage Open Source For Coding Efficiency.md
retrieval_count: 0
gap: false
topic: Qdrant Alloy as AI-KOS retrieval backend
tags:
- type/research-note
---

## Topic: 

## Key Notes
- FastEmbed runs in-process within Qdrant, combining vectorization and insertion in one step — eliminates embedding-service (Port 8010) and sparse-index-service (Port 8011)
- Native support for dense (BAAI/bge-small-en-v1.5, 384d), sparse (BM25/SPLADE), and late-interaction (ColBERT, 128d per token) vectors
- Qdrant Query API (v1.10+) natively executes multi-stage hybrid queries via prefetch parameter — replaces custom retrieval coordination
- Reciprocal Rank Fusion (RRF) and Distribution-Based Score Fusion (DBSF) built into the database engine — no custom fusion code needed
- tune_rrf_weights grid-search framework for domain-specific weight optimization without rewriting fusion logic
- Hardware fit: RTX 5070 Ti with 16GB VRAM handles embedding generation + reranker model co-located in GPU memory

## Open Questions
- What's the latency impact of FastEmbed vs standalone embedding service for 1000+ documents?
- Can Qdrant's disk-based storage (mmap) handle the full corpus on the 300GB SSD without performance degradation?

## Sources
- Qdrant FastEmbed docs
- Qdrant Query API v1.10 release notes