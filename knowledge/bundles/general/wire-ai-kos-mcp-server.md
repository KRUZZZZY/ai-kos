---
id: e41dc79f-97a7-45a3-b7a7-37fef5ac5b76
title: How to Wire AI-KOS MCP Server into Hermes
slug: wire-ai-kos-mcp-server
type: process
created_at: '2026-08-05'
updated_at: '2026-08-05'
reviewed_at: '2026-08-05'
next_review_at: '2027-08-05'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- mcp
- ai-kos
- hermes
- wiring
- setup
- process
summary: Procedure for permanently wiring the AI-KOS MCP server into Hermes so all
  14 knowledge database tools are available in every session.
related:
- ai-kos
- ai-kos-mission
- article-types-guide
- configuring-declarative-bindings
- process-articles-backup-skills
- processing-inbox-with-taskqueue
- setting-up-semantic-search
- using-the-research-pipeline
provenance:
- session-2026-08-04-mcp-wiring
retrieval_count: 0
gap: false
tags:
- type/process
---

## Outcome
All 14 AI-KOS MCP tools available as first-class tools in Hermes: ai_kos_ingest, ai_kos_create, ai_kos_search, ai_kos_read, ai_kos_link, ai_kos_list, ai_kos_merge_candidates, ai_kos_templates, ai_kos_graph, ai_kos_compare, ai_kos_stats, ai_kos_clean, ai_kos_research_plan, ai_kos_research_persist. Config persists in ~/.hermes/config.yaml under mcp_servers.ai-kos — survives updates, reinstalls, reboots.

## Prerequisites
- AI-KOS installed in editable mode
- mcp>=1.0 package installed
- mcp_server.py has sync entrypoint() wrapper around async main()
- pyproject.toml has ai-kos-mcp console script entry

## Steps
1. Verify MCP server imports: python3 -c 'import ai_kos.mcp_server; print("ok")'
2. Ensure ai_kos/mcp_server.py has a sync entrypoint() wrapper around async main()
3. Ensure pyproject.toml has ai-kos-mcp = "ai_kos.mcp_server:entrypoint" under [project.scripts]
4. Reinstall: pip3 install -e /path/to/AI_KOS_PROJECT
5. Verify entry point: which ai-kos-mcp
6. Register with Hermes: echo 'Y' | hermes mcp add ai-kos --command ai-kos-mcp
7. Confirm: hermes mcp list shows ai-kos with status enabled and 14 tools
8. Test connection: hermes mcp test ai-kos reports Connected, 14 tools discovered
9. Start a new session (/reset or restart hermes) for MCP tools to load

## Related
[[ai-kos]] [[ai-kos-mission]] [[article-types-guide]] [[configuring-declarative-bindings]] [[process-articles-backup-skills]] [[processing-inbox-with-taskqueue]] [[setting-up-semantic-search]] [[using-the-research-pipeline]]
