---
id: 67c58e7d-f20c-40b5-afad-417f2b639ec1
title: How to Use the ResearchPipeline for Durable Deep Research
slug: using-the-research-pipeline
type: process
created_at: '2026-08-05'
updated_at: '2026-08-05'
reviewed_at: '2026-08-05'
next_review_at: '2027-08-05'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- research-pipeline
- durable-execution
- deep-research
- process
- setup
- ai-kos
summary: 'Step-by-step procedure for running durable deep research with the ResearchPipeline:
  creating a pipeline, executing with retry, pausing for human review, resuming after
  crashes, and inspecting progress.'
related:
- ai-kos-architecture-modernization-mission
- ai-kos-architecture-modernization-plan
- article-types-guide
- configuring-declarative-bindings
- deep-research-pipeline-workflow
- deep-research-tool-mission
- durable-execution-research
- process-articles-backup-skills
- processing-inbox-with-taskqueue
- research-pipeline-how-it-works
- session-2026-08-04-ai-kos-build
- setting-up-semantic-search
- wire-ai-kos-mcp-server
provenance:
- ai_kos/pipeline.py
retrieval_count: 0
gap: false
tags:
- type/process
---

## Outcome
A research pipeline that survives crashes, retries failed steps automatically, and pauses for human review before creating articles. The pipeline state file at knowledge/pipelines/<id>.json can be inspected at any time to see progress.

## Prerequisites
- AI-KOS v1.5+ installed with pipeline module
- A search function (e.g., Hermes web_search) for the search step
- Write access to the knowledge directory for state persistence

## Steps
1. STEP 1: Define your search function. The pipeline expects search_fn(sub_question: str, query: str) -> List[Dict]. Each dict must have 'title', 'url', and 'key_claim' keys. Example: def my_search(sq, query): return web_search(query) — Hermes provides this automatically.
2. STEP 2: Create the pipeline. Call ResearchPipeline.create(question) with your research question. Example: p = ResearchPipeline.create('What are the latest advances in fusion energy?'). This creates the pipeline state in memory but does NOT save to disk yet.
3. STEP 3: Run the pipeline. Call p.run(search_fn=my_search). The pipeline executes all 7 steps in order. After each step completes, state is saved atomically to knowledge/pipelines/<id>.json. If any step fails, it retries up to 3 times with exponential backoff.
4. STEP 4: Handle review (optional). To require human approval before article creation, pass a review callback: def approve(state): return input('Approve? (y/n) ') == 'y'. Then p.run(search_fn=my_search, review_callback=approve). If the callback returns False, the pipeline pauses with status 'awaiting_review'.
5. STEP 5: Resume after crash or pause. If the pipeline is interrupted (Hermes session ends, process killed), load it from disk: p2 = ResearchPipeline.load('knowledge/pipelines/<id>.json') then p2.resume(search_fn=my_search). Already-completed steps are skipped.
6. STEP 6: Inspect progress. Call p.summary() to see which steps completed and which are pending. Call ResearchPipeline.list_pipelines() to see all active and completed pipelines. The JSON state file can also be read directly for full details including context data and error traces.

## Related
[[ai-kos-architecture-modernization-mission]] [[ai-kos-architecture-modernization-plan]] [[article-types-guide]] [[configuring-declarative-bindings]] [[deep-research-pipeline-workflow]] [[deep-research-tool-mission]] [[durable-execution-research]] [[process-articles-backup-skills]] [[processing-inbox-with-taskqueue]] [[research-pipeline-how-it-works]] [[session-2026-08-04-ai-kos-build]] [[setting-up-semantic-search]] [[wire-ai-kos-mcp-server]]
