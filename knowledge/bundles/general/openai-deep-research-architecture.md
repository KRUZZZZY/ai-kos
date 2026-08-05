---
id: b6131beb-30fa-4725-9474-6fc18dc58586
title: 'Research: OpenAI Deep Research Architecture'
slug: openai-deep-research-architecture
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- openai
- deep-research
- o3
- reinforcement-learning
- self-reflection
- ai
- knowledge
summary: 'OpenAI Deep Research: RL-trained o3-deep-research model, 3-stage consumer
  pipeline, internal self-reflection, Responses API with web_search/file_search/code_interpreter
  tools.'
related:
- ai-deep-research-systems
- deep-research-enterprise-implications
- deep-research-tool-mission
- gemini-deep-research-architecture
- perplexity-sonar-deep-research
- stanford-storm-framework
provenance:
- inbox/AI Deep Research Systems Analysis.md
retrieval_count: 0
gap: false
topic: OpenAI Deep Research
tags:
- type/research-note
---

## Topic: 

## Key Notes
- Uses specialized RL models: o3-deep-research and o4-mini-deep-research, optimized for extended self-reflection, planning, self-correction, and tool interaction over long horizons.
- Consumer pipeline (ChatGPT): 3-stage — (1) Clarification: intermediate model asks follow-up questions, (2) Prompt Expansion: combines original + clarifications into detailed prompt, (3) Execution: o3 passes to deep research agent.
- Developer API (POST /v1/responses): clarification/expansion stages omitted. Requires timeout=3600, background=true, and at least one data tool (web_search_preview, file_search, code_interpreter, remote MCP).
- Internal self-reflection: model verifies factual consistency before generating output. Achieved 26.6% accuracy on complex multi-step research tasks, outperforming non-iterative baselines.
- Tool ecosystem: web_search_preview (public web), file_search (vector stores), code_interpreter (sandbox), remote MCP connectors.

## Sources
- OpenAI API docs
- PromptLayer deep research methodology

## Related
[[ai-deep-research-systems]] [[deep-research-enterprise-implications]] [[deep-research-tool-mission]] [[gemini-deep-research-architecture]] [[perplexity-sonar-deep-research]] [[stanford-storm-framework]]
