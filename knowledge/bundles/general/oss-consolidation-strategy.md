---
id: 133634ee-18c4-405c-ab6a-b6c026e5b53d
title: Open-Source Consolidation Strategy for AI-KOS
slug: oss-consolidation-strategy
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- open-source
- consolidation
- ai-kos
- knowledge
- architecture
- microservices
- langgraph
- qdrant
summary: 'Strategy for replacing custom AI-KOS microservices with mature open-source
  alternatives: Qdrant Alloy for retrieval, docling-graph for ingestion, LangGraph
  for orchestration, Temporal/Restate for durable execution.'
related:
- hybrid-search-research
- langgraph-orchestration-research
provenance:
- inbox/Exploring AI Agents for Specifications.md
- inbox/Leverage Open Source For Coding Efficiency.md
retrieval_count: 0
gap: false
tags:
- type/base
---

AI-KOS v1.5 originally specified 10-12 microservices (ingestion, consolidation, retrieval, governance, router, scheduler, health, session, graph, CI). Running this many services on consumer hardware creates CPU context-switching overhead, memory fragmentation, and network serialization bottlenecks. The open-source ecosystem now offers mature alternatives that replace or consolidate these services. Qdrant with FastEmbed replaces the separate embedding-service and sparse-index-service by generating dense and sparse vectors in-process. Docling-graph replaces the custom ingestion pipeline with layout-aware parsing, structure-aware chunking, and direct OKF-compatible output. LangGraph replaces the governance-service state machine with directed cyclic graphs and native checkpointing. Temporal or Restate replace the Redis task queue with durable execution, automatic retry, and crash recovery. This consolidation reduces the service count from 10+ to 3-4 and eliminates custom state management, queue coordination, and embedding microservices.