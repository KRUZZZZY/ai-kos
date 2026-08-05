---
id: 5f474c8a-a17a-45e8-8396-c8b2042cb881
title: How DeclarativeBindings Pydantic Settings Tool Configuration Works
slug: declarative-bindings-how-it-works
type: help
created_at: '2026-08-05'
updated_at: '2026-08-05'
reviewed_at: '2026-08-05'
next_review_at: '2027-08-05'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- declarative-bindings
- pydantic-settings
- configuration
- tool-config
- bindings
- ai-kos
- env-vars
summary: How DeclarativeBindings replaces scattered path parameters with a single
  Pydantic Settings class loaded from config.yaml and env vars — adopting Cloudflare's
  declarative service wiring pattern for AI-KOS tools.
related:
- configuring-declarative-bindings
provenance:
- ai_kos/bindings.py
retrieval_count: 0
gap: false
project: AI-KOS Architecture Modernization
component: DeclarativeBindings
tags:
- type/help
---

## Component
DeclarativeBindings provides a single configuration point for AI-KOS tools, replacing scattered path parameters with a Pydantic Settings class. Inspired by Cloudflare's wrangler.toml bindings model (where services are wired declaratively rather than via SDK calls), Bindings resolves configuration in this order: environment variables (AI_KOS_* prefix) → config.yaml values → hardcoded defaults. The singleton pattern ensures all tools share the same configuration. Convenience helpers like kb_path(explicit=None) implement the override pattern: if an explicit path is provided, use it; otherwise, fall back to the configured binding. There are 13 bindings organized into 4 groups: paths (knowledge_dir, inbox_dir, templates_dir, archive_dir, rejected_dir, projects_dir), pipeline (pipelines_dir), search (min_keyword_overlap, merge_threshold, semantic_enabled, semantic_threshold), and task queue (taskqueue_max_workers, taskqueue_max_retries, taskqueue_retry_delay). Relative paths are resolved against the project root (where config.yaml lives). The entire system is backward compatible — if bindings aren't configured, defaults match the previous hardcoded values exactly.

## Examples
- Configuring via env: export AI_KOS_KNOWLEDGE_DIR=/data/kb; export AI_KOS_MIN_KEYWORD_OVERLAP=4
- Configuring via config.yaml: paths: {knowledge_dir: custom_kb}; linking: {min_keyword_overlap: 4}
- Using in code: bindings = get_bindings(); path = kb_path()  # returns configured knowledge_dir
- Explicit override: kb_path(explicit='/tmp/test_kb') ignores the binding and uses /tmp/test_kb
- Custom task queue: Bindings(taskqueue_max_workers=8, taskqueue_max_retries=5)

## Related
[[configuring-declarative-bindings]]
