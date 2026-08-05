---
id: ec351bb0-4ddb-4acc-8247-388c9298bbdc
title: How to Configure AI-KOS Tools with Declarative Bindings
slug: configuring-declarative-bindings
type: process
created_at: '2026-08-05'
updated_at: '2026-08-05'
reviewed_at: '2026-08-05'
next_review_at: '2027-08-05'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- declarative-bindings
- configuration
- config-yaml
- env-vars
- pydantic-settings
- process
- ai-kos
summary: 'Step-by-step procedure for configuring AI-KOS tools via declarative bindings:
  understanding the env > config.yaml > defaults resolution order, setting up config.yaml,
  using environment variables, verifying configuration, and overriding per-call for
  backward compatibility.'
related:
- article-types-guide
- declarative-bindings-how-it-works
- process-articles-backup-skills
- processing-inbox-with-taskqueue
- setting-up-semantic-search
- using-the-research-pipeline
- wire-ai-kos-mcp-server
provenance:
- ai_kos/bindings.py
retrieval_count: 0
gap: false
tags:
- type/process
---

## Outcome
All AI-KOS tools share a single configuration source. Changing the knowledge directory in one place (config.yaml or env var) affects all tools. Explicit per-call parameters still work as overrides.

## Prerequisites
- AI-KOS v1.5+ with bindings module
- pydantic-settings>=2.0 installed (included in core dependencies)
- A config.yaml file in the project root (optional — defaults work without one)

## Steps
1. STEP 1: Understand the resolution order. Bindings resolve in this priority: (1) environment variables with AI_KOS_ prefix, (2) config.yaml values, (3) hardcoded defaults. Higher-numbered sources override lower ones. Example: AI_KOS_KNOWLEDGE_DIR=/env/kb beats paths.knowledge_dir: custom_kb in config.yaml.
2. STEP 2: Configure via config.yaml (recommended for project-specific settings). Add a paths section and optionally linking/taskqueue sections. Example: paths: {knowledge_dir: my_kb, inbox_dir: my_inbox}; linking: {min_keyword_overlap: 4, merge_threshold: 0.85}; taskqueue: {max_workers: 5}. All fields are optional — omit to keep defaults.
3. STEP 3: Configure via environment variables (recommended for deployment-specific settings). Set AI_KOS_KNOWLEDGE_DIR, AI_KOS_INBOX_DIR, AI_KOS_MIN_KEYWORD_OVERLAP, etc. These override config.yaml values. Useful for Docker, CI/CD, or per-machine customization without editing files.
4. STEP 4: Use in code. Import get_bindings() and call it: bindings = get_bindings(). This returns a singleton — all modules share the same instance. Access values directly: bindings.knowledge_dir. Use convenience helpers for the override pattern: path = kb_path(explicit=user_provided_path) — returns user_provided_path if set, otherwise bindings.knowledge_dir.
5. STEP 5: Verify configuration. Print the bindings to see resolved values: print(get_bindings().model_dump()). Check that paths resolve correctly. If a path is relative (e.g., 'knowledge'), it resolves against the project root (where config.yaml or pyproject.toml is found).
6. STEP 6: Override per-call (backward compatibility). All existing MCP tools accept explicit path parameters that override bindings. Example: ai_kos_ingest(filepath='/tmp/doc.pdf', kb_path='/custom/kb') uses /custom/kb regardless of what config.yaml says. This ensures zero breakage for existing callers.

## Related
[[article-types-guide]] [[declarative-bindings-how-it-works]] [[process-articles-backup-skills]] [[processing-inbox-with-taskqueue]] [[setting-up-semantic-search]] [[using-the-research-pipeline]] [[wire-ai-kos-mcp-server]]
