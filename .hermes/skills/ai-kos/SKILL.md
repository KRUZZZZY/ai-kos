---
name: ai-kos
title: "AI-KOS — self-building knowledge database with auto-linking, full-text search, and Obsidian graph"
description: |
  AI-KOS is a knowledge database where any file is converted into linked .md articles.
  Articles sharing >=3 keywords auto-link. Includes TF-IDF full-text search, similarity 
  comparison, Obsidian vault for graph visualization, and D3.js standalone visualizer.
  Exposed as 12 MCP tools for Hermes integration.
version: 1.5.0
---

# AI-KOS Knowledge Database

## Quick Start

```bash
pip install -e /path/to/AI_KOS_PROJECT
hermes mcp add ai-kos --command "python -m ai_kos.mcp_server"
```

## MCP Tools (12 total)

| Tool | What it does |
|---|---|
| `ai_kos_ingest` | Extract text from any file (.md/.txt/.pdf/.docx/.py), detect article type |
| `ai_kos_create` | Create a new knowledge article (validates, writes .md, auto-links) |
| `ai_kos_search` | Full-text TF-IDF search with snippets + keyword bonus |
| `ai_kos_compare` | Find most similar articles to a slug by content + keyword overlap |
| `ai_kos_read` | Read full article (frontmatter + body) by slug |
| `ai_kos_list` | List all articles, filter by type or keyword |
| `ai_kos_link` | Run auto-linker (>=3 shared keywords -> [[wikilinks]]) |
| `ai_kos_merge_candidates` | Find near-duplicates (>50% keyword overlap) |
| `ai_kos_templates` | Show all 7 article templates with prompts |
| `ai_kos_graph` | Export knowledge graph as JSON (nodes + edges) |
| `ai_kos_stats` | Health stats: counts by type, confidence distribution, orphans, past-review |
| `ai_kos_clean` | Clean inbox: archive ingested, move projects, reject binaries |

## CLI Commands

```bash
ai-kos ingest path/to/file.pdf     # extract text, detect type
ai-kos create base --data '{...}'   # create article from JSON
ai-kos search "query" -k 10         # full-text search
ai-kos search --compare my-slug     # find similar articles
ai-kos read my-slug                 # read full article
ai-kos link                         # run auto-linker
ai-kos list -t process              # filter by type
ai-kos graph --obsidian             # open Obsidian vault
ai-kos graph -o data.json           # export graph JSON
ai-kos clean                        # organize inbox
ai-kos info                         # system overview
```

## Article Types (7)

| Type | Purpose | When to use |
|---|---|---|
| `base` | Factoid / concept (~5 paragraphs) | Definitions, technology concepts, architecture overviews |
| `process` | Step-by-step procedure | Skill backups, debugging workflows, setup sequences |
| `plan` | Planning document | Project roadmaps, feature scoping, migration plans |
| `help` | Explains a project component | Developer docs, onboarding, troubleshooting guides |
| `research-note` | Key notes for larger research | Literature reviews, preliminary findings, open questions |
| `note` | Temporary idea/brainstorm | Quick captures, future work ideas, observations |
| `mission` | Project building block | Project charters, architecture decisions, success criteria |

## Standard Workflow

### 1. Ingest new knowledge
```
Drop file in inbox/ -> ai_kos_ingest(filepath) -> reads text, suggests type
Read the content and simplify it -> ai_kos_create(type, {title, slug, keywords, ...})
System auto-links to related articles, reports merge candidates
ai_kos_clean -> moves source to archive/, projects to projects/, rejects binaries
```

### 2. Search before creating
```
ai_kos_search("topic") -> check what already exists
ai_kos_compare(similar-slug) -> find near-duplicates
If overlap > 80%: update existing article instead of creating new one
```

### 3. Session writeback
```
At end of significant session: review what was learned
For each insight: follow creation protocol (see [[creation-protocol]])
Prioritize: process articles first (skill backups), base articles second
Run ai_kos_link to connect new articles
Run ai_kos_stats to check knowledge base health
```

### 4. Visualize
```
ai-kos graph --obsidian -> colored graph view with backlinks
Or: ai-kos graph -o graph-data.json && open graph.html in browser
```

## Directory Layout

```
AI_KOS_PROJECT/
├── inbox/          # Drop files here for ingestion
├── archive/        # Successfully ingested source documents
├── projects/       # Project directories (source code repos)
├── rejected/       # Build artifacts, caches, non-knowledge files
├── knowledge/      # OKF .md articles (the knowledge base)
├── templates/      # 7 YAML article templates
├── ai_kos/         # Python package (CLI + MCP server)
├── .obsidian/      # Obsidian vault config (graph, backlinks, tags)
└── graph.html      # D3.js force-directed graph visualizer
```

## Cron Jobs (via Hermes)

```bash
# Nightly re-index
hermes cron create "0 2 * * *" -p "cd /path && ai-kos link" --name "ai-kos-nightly-link"

# Weekly health check
hermes cron create "0 9 * * 0" -p "cd /path && ai-kos info" --name "ai-kos-weekly-health"
```
