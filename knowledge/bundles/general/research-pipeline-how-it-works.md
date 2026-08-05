---
id: 116456c2-bc1a-4074-97fe-e872fd0aef40
title: How the ResearchPipeline Durable Execution Engine Works
slug: research-pipeline-how-it-works
type: help
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
- retry
- state-persistence
- ai-kos
- deep-research
- workflow
summary: How AI-KOS's ResearchPipeline provides durable execution with step-based
  retry, atomic JSON state persistence, crash recovery, and human-in-the-loop review
  gates — adopting Cloudflare Workflows patterns locally.
related:
- ai-kos-architecture-modernization-mission
- ai-kos-architecture-modernization-plan
- deep-research-pipeline-workflow
- deep-research-tool-mission
- durable-execution-research
- session-2026-08-04-ai-kos-build
- taskqueue-how-it-works
- using-the-research-pipeline
provenance:
- ai_kos/pipeline.py
retrieval_count: 0
gap: false
project: AI-KOS Architecture Modernization
component: ResearchPipeline
tags:
- type/help
---

## Component
The ResearchPipeline is a durable execution engine that wraps AI-KOS's deep research flow (plan → search → structure → cross-reference → synthesize → review → persist) into resilient, restartable steps. Each step is executed in order; after each step, the entire pipeline state (which steps completed, what data was collected, any errors) is saved atomically to a JSON file at knowledge/pipelines/<id>.json. If a step fails, it retries with exponential backoff (2s, 4s, 8s — max 3 attempts). If the pipeline crashes mid-run (Hermes session ends, process killed, network drops), it can be resumed from disk — already-completed steps are skipped, and execution picks up from the first pending step. The review step is a human gate: it pauses the pipeline and marks its status as 'awaiting_review', allowing the user to inspect findings before articles are created. This is the same pattern Cloudflare Workflows uses for multi-step durable execution, but implemented locally with zero external dependencies (json + pathlib only).

## Examples
- Creating a pipeline: pipeline = ResearchPipeline.create('What is quantum computing?') then pipeline.run(search_fn=my_search_function)
- Resuming after crash: pipeline = ResearchPipeline.load('knowledge/pipelines/abc123.json') then pipeline.resume(search_fn=my_search_function)
- Checking status: pipeline.summary() returns {id, question, status, steps: {plan: {status: 'completed', attempts: 1}, ...}}
- Listing all pipelines: ResearchPipeline.list_pipelines() returns all saved pipeline states with their status
- Reject review to pause: def my_review(state): return False → pipeline.run(review_callback=my_review) pauses before article creation

## Related
[[ai-kos-architecture-modernization-mission]] [[ai-kos-architecture-modernization-plan]] [[deep-research-pipeline-workflow]] [[deep-research-tool-mission]] [[durable-execution-research]] [[session-2026-08-04-ai-kos-build]] [[taskqueue-how-it-works]] [[using-the-research-pipeline]]
