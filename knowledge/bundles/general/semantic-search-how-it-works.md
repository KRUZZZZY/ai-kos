---
id: d01e6842-69c4-4a2e-8963-b311fad73303
title: How SemanticSearch with Vector Embeddings and Hybrid RRF Works
slug: semantic-search-how-it-works
type: help
created_at: '2026-08-05'
updated_at: '2026-08-05'
reviewed_at: '2026-08-05'
next_review_at: '2027-08-05'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- semantic-search
- vector-embeddings
- faiss
- rrf
- hybrid-search
- sentence-transformers
- ai-kos
summary: How SemanticSearch adds vector embeddings via sentence-transformers + FAISS,
  then fuses keyword and semantic rankings with Reciprocal Rank Fusion for hybrid
  search that catches meaning-level matches keyword search would miss.
related:
- ai-kos-architecture-modernization-mission
- ai-kos-architecture-modernization-plan
- hybrid-search-research
- qdrant-alloy-research
- setting-up-semantic-search
provenance:
- ai_kos/semantic.py
retrieval_count: 0
gap: false
project: AI-KOS Architecture Modernization
component: SemanticSearch
tags:
- type/help
---

## Component
SemanticSearch augments AI-KOS's TF-IDF keyword search with vector embeddings for semantic understanding. When enabled, articles are encoded into 384-dimensional vectors using the all-MiniLM-L6-v2 model via sentence-transformers. These vectors capture meaning — 'serverless edge computing' and 'Cloudflare Workers' will have high cosine similarity even if they share no keywords. The vectors are stored in a FAISS flat index persisted to knowledge/.vectors/. At query time, the same model encodes the query, and FAISS finds the top-N articles by cosine similarity. These semantic results are fused with TF-IDF keyword results using Reciprocal Rank Fusion: RRF(score) = sum(1/(k+rank_i)) for k=60. This means an article ranked #1 by both methods gets the highest combined score, while articles that only one method finds still contribute. The entire system is optional — if sentence-transformers or faiss-cpu are not installed, search gracefully falls back to keyword-only TF-IDF.

## Examples
- Query: 'edge serverless functions' — keyword search misses 'Cloudflare Workers' but semantic search ranks it #1 because the meanings are similar
- Setting the semantic threshold: HybridSearcher().search(query, min_semantic_threshold=0.7) filters out weak semantic matches
- Building the index: searcher = get_hybrid_searcher(); searcher.ensure_index() builds or loads the FAISS index
- Checking availability: semantic_available() returns True if both sentence-transformers and faiss-cpu are installed
- RRF fusion: reciprocal_rank_fusion({'a':1,'b':2}, {'b':1,'c':2}) → b gets highest score (ranked in both lists)

## Related
[[ai-kos-architecture-modernization-mission]] [[ai-kos-architecture-modernization-plan]] [[hybrid-search-research]] [[qdrant-alloy-research]] [[setting-up-semantic-search]]
