---
id: 7bf47feb-2c5f-48c9-bd1c-802a91557acc
title: How to Run the Random Graph Simulation Suite
slug: run-random-graph-suite
type: process
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- random-graph
- simulation
- run
- networkx
- python
- ai-kos
- knowledge
- articles
summary: Step-by-step instructions for installing and running the Random Graph Simulation
  Suite from the dissertation project.
related:
- ai-kos
- ai-kos-mission
- ai-kos-plan
- article-types-guide
- creation-protocol
- docling-graph-research
- durable-execution-research
- harden-aws-ssm-jump-host
- hybrid-search-research
- ingest-file
- langgraph-orchestration-research
- memsearch-claude-memory-research
- networkx-implementation-notes
- obsidian-graph-idea
- oss-consolidation-strategy
- process-articles-backup-skills
- random-graph-dissertation-mission
- random-graph-dissertation-notes
- random-graph-simulation-suite
- session-end-protocol
- session-writeback
provenance:
- projects/Disertation/Writing/Material/README.md
retrieval_count: 0
gap: false
tags:
- type/process
---

## Outcome
Simulation suite generates 3,010 graphs across ER, WS, and BA models. Results stored in SQLite database with queryable metrics. Publication-quality PNG figures produced in ./outputs/.

## Prerequisites
- Python 3.10+
- networkx
- matplotlib
- numpy
- scipy

## Steps
1. Install dependencies: pip install networkx matplotlib numpy scipy
2. Place random_graphs.py anywhere accessible
3. Run the full demo: python random_graphs.py
4. Wait 5-10 minutes for the 9-step pipeline to complete
5. Check outputs: PNG figures in ./outputs/, database at ~/random_graphs.db
6. To customise: edit DB_PATH and OUT_DIR constants near the top of the script
7. For programmatic use: from random_graphs import make_erdos_renyi, compute_metrics, save_run
8. Query results: sqlite3 random_graphs.db 'SELECT * FROM runs WHERE model="erdos_renyi" ORDER BY avg_path_length ASC LIMIT 10'

## Related
[[ai-kos]] [[ai-kos-mission]] [[ai-kos-plan]] [[article-types-guide]] [[creation-protocol]] [[docling-graph-research]] [[durable-execution-research]] [[harden-aws-ssm-jump-host]] [[hybrid-search-research]] [[ingest-file]] [[langgraph-orchestration-research]] [[memsearch-claude-memory-research]] [[networkx-implementation-notes]] [[obsidian-graph-idea]] [[oss-consolidation-strategy]] [[process-articles-backup-skills]] [[random-graph-dissertation-mission]] [[random-graph-dissertation-notes]] [[random-graph-simulation-suite]] [[session-end-protocol]] [[session-writeback]]
