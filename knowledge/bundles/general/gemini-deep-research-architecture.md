---
id: 9aa6dbee-1975-4141-bebd-5bdd3867959d
title: 'Research: Google Gemini Deep Research Agent Architecture'
slug: gemini-deep-research-architecture
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- gemini
- deep-research
- google
- workspace
- zero-etl
- collaborative-planning
- ai
- knowledge
summary: 'Architectural analysis of Google Gemini Deep Research: Interactions API,
  Collaborative Planning, zero-ETL Workspace integration, 60-min async execution,
  and 5-tool ecosystem.'
related:
- ai-deep-research-systems
- deep-research-enterprise-implications
- deep-research-tool-mission
- openai-deep-research-architecture
- perplexity-sonar-deep-research
- stanford-storm-framework
provenance:
- inbox/AI Deep Research Systems Analysis.md
retrieval_count: 0
gap: false
topic: Google Gemini Deep Research
tags:
- type/research-note
---

## Topic: 

## Key Notes
- Operates exclusively through Interactions API (POST /v1beta/interactions), not standard generate_content. Two model variants: deep-research-preview (fast, streaming) and deep-research-max (comprehensive, long-form).
- Collaborative Planning: when collaborative_planning=true, agent halts before search, outputs structured research plan. Client refines plan over multiple turns. Execution begins only when collaborative_planning=false.
- Zero-ETL Workspace integration: reads Gmail (as message objects with metadata/threads), Drive (as file entities with comments/revisions), Docs, Sheets, Chat — no ingestion pipelines or vector databases needed.
- Permission inheritance: agent accesses everything the authenticated user can see. Risk: stale permissions expose legacy data. Requires explicit IAM hygiene.
- Five-tool ecosystem: google_search (web), url_context (HTML parsing), code_execution (sandbox), file_search (user corpora), mcp_server (remote enterprise APIs).
- Visualization: setting visualization='auto' returns base64-encoded charts/graphs in response payloads. Setting thinking_summaries='auto' streams intermediate progress.
- Enterprise integration: requires async architecture with background=true, store=true. Rate limits 2-5 RPM. Recommended: SHA-256 query caching, semaphore-capped concurrency (2-3 parallel), downstream JSON extraction.

## Sources
- Google AI Developers docs
- MindStudio Gemini Deep Research API guide

## Related
[[ai-deep-research-systems]] [[deep-research-enterprise-implications]] [[deep-research-tool-mission]] [[openai-deep-research-architecture]] [[perplexity-sonar-deep-research]] [[stanford-storm-framework]]
