---
id: 89536bd8-0528-4cfe-82fe-f90f09db835f
title: How to Set Up Semantic Search with Vector Embeddings
slug: setting-up-semantic-search
type: process
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
- setup
- faiss
- sentence-transformers
- process
- ai-kos
summary: Step-by-step procedure for installing sentence-transformers and FAISS, building
  the vector index from AI-KOS articles, verifying hybrid search returns semantic
  matches, and integrating semantic similarity into auto-linking.
related:
- ai-kos-architecture-modernization-mission
- ai-kos-architecture-modernization-plan
- article-types-guide
- configuring-declarative-bindings
- process-articles-backup-skills
- processing-inbox-with-taskqueue
- semantic-search-how-it-works
- using-the-research-pipeline
- wire-ai-kos-mcp-server
provenance:
- ai_kos/semantic.py
retrieval_count: 0
gap: false
tags:
- type/process
---

## Outcome
AI-KOS search results include semantically relevant articles that keyword-only search would miss. Example: searching for 'edge serverless functions' returns articles about Cloudflare Workers even if the word 'edge' never appears in those articles.

## Prerequisites
- AI-KOS v1.5+ with semantic module
- Python 3.11+
- 2-4 GB free disk space (for model download and FAISS index)
- Internet connection (first run only, for model download)

## Steps
1. STEP 1: Install optional dependencies. Run: pip install sentence-transformers faiss-cpu. The sentence-transformers package will download all-MiniLM-L6-v2 (~90MB) on first use. FAISS provides the vector similarity index.
2. STEP 2: Verify installation. Run: from ai_kos.semantic import semantic_available; print(semantic_available()). Should return True. If it returns False, check that both packages are installed and importable.
3. STEP 3: Build the vector index. Run: from ai_kos.semantic import ensure_semantic_index; ensure_semantic_index(). This reads all existing AI-KOS articles, generates 384-dim embeddings for each, and stores them in knowledge/.vectors/index.faiss. First build may take 30-60 seconds depending on article count.
4. STEP 4: Test hybrid search. Run: from ai_kos.semantic import hybrid_search; results = hybrid_search('your query here', top_k=10). Compare with keyword-only: from ai_kos.search import search; kw_results = search('your query here'). Results with semantic_rank set come from the vector index. Those with only tfidf_rank are keyword-only hits.
5. STEP 5: Integrate with auto-linking. Add semantic_threshold to config.yaml under linking section. When semantic search is active, the auto-linker can use semantic similarity alongside keyword overlap to discover connections. Set semantic_threshold: 0.7 (default) — lower values create more links.
6. STEP 6: Rebuild after article changes. The vector index is NOT automatically updated when articles change. After creating or editing articles, rebuild with: from ai_kos.semantic import HybridSearcher; searcher = HybridSearcher(); searcher.vector_index.build(articles, searcher.embedding_model, force=True). Or delete knowledge/.vectors/ and re-run ensure_semantic_index().

## Related
[[ai-kos-architecture-modernization-mission]] [[ai-kos-architecture-modernization-plan]] [[article-types-guide]] [[configuring-declarative-bindings]] [[process-articles-backup-skills]] [[processing-inbox-with-taskqueue]] [[semantic-search-how-it-works]] [[using-the-research-pipeline]] [[wire-ai-kos-mcp-server]]
