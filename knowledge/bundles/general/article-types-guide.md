---
id: 63670fa9-46f1-42bc-982d-a868afba65b2
title: AI-KOS Article Types Guide
slug: article-types-guide
type: help
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
keywords:
- article-types
- base
- process
- plan
- help
- template
- ai-kos
- knowledge
summary: Complete guide to the 7 AI-KOS article types — when to use each, what fields
  are required, and how they interconnect.
related:
- ai-kos-plan
- creation-protocol
- process-articles-backup-skills
provenance:
- ai-kos-schemas.py
retrieval_count: 0
project: AI-KOS
component: Article type system (schemas.py)
tags:
- type/help
---


## Component
AI-KOS has 7 article types, each with a specific purpose and template. BASE: For factual concept articles (~5 paragraphs). Use for technology concepts, definitions, architecture overviews. Example: 'What is RRF (Reciprocal Rank Fusion)?'. PROCESS: For step-by-step procedures. These are skill backups — when Hermes skills get archived due to inactivity, process articles preserve the knowledge permanently. Use for any multi-step workflow. PLAN: For planning documents with phases, milestones, and risks. Use when scoping a project or feature. HELP: For explaining how a specific component of a project works. Always names the project and component. RESEARCH-NOTE: For ongoing research — key notes, open questions, sources. These are meant to eventually become base articles. NOTE: Temporary storage for ideas, brainstorms, things that might relate to future work. Flag actionable=True if it needs follow-up. MISSION: Defines a project — its purpose, architecture, dependencies, and success criteria. The highest-level planning article.

## Examples
- Learned how Qdrant RRF works → base article 'rrf-fusion'
- Solved a recurring Docker networking bug → process article 'fix-docker-network'
- Planning the next AI-KOS feature → plan article 'ai-kos-v1.6-plan'
- Documenting how the linker works → help article 'auto-linker' (already exists)
- Researching embedding models → research-note 'embedding-model-comparison'
- Had an idea about graph visualization → note 'obsidian-graph-idea' (already exists)
- Starting a new project → mission article defining it

## Related
[[ai-kos-plan]] [[creation-protocol]] [[process-articles-backup-skills]]