---
id: 335b49ce-2750-40fe-8a05-d66359fb7da0
title: 'Research: Implementation Details — NetworkX Graph Generation'
slug: networkx-implementation-notes
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- networkx
- implementation
- python
- sqlite
- simulation
- random-graph
- ai-kos
- knowledge
summary: 'Implementation notes: how the random graph simulation suite generates ER/WS/BA
  models using NetworkX, stores results in SQLite, and produces metric plots.'
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
- obsidian-graph-idea
- oss-consolidation-strategy
- process-articles-backup-skills
- processing-inbox-with-taskqueue
- random-graph-dissertation-mission
- random-graph-dissertation-notes
- random-graph-simulation-suite
- run-random-graph-suite
- session-end-protocol
- session-writeback
- taskqueue-how-it-works
provenance:
- projects/Disertation/Writing/dissertation.txt
retrieval_count: 0
gap: false
topic: Random Graph Simulation Implementation
tags:
- type/research-note
---

## Topic: 

## Key Notes
- ER generator: networkx.erdos_renyi_graph(n, p, seed) — uses independent Bernoulli trials per possible edge. ~3,010 graphs in bulk simulation.
- WS generator: networkx.watts_strogatz_graph(n, k, beta, seed) — ring lattice with k nearest neighbours, rewires with probability beta.
- BA generator: networkx.barabasi_albert_graph(n, m, seed) — growth with preferential attachment, m edges per new node.
- Metrics computed via compute_metrics(G): avg_degree, clustering (networkx.average_clustering), avg_path_length (networkx.average_shortest_path_length on giant component), component sizes.
- SQLite schema: runs(id, model, n, param_name, param_value, avg_degree, clustering, avg_path_length, giant_frac, density, timestamp). Database path: ~/random_graphs.db.
- Bulk simulation produces ~3,010 graphs: 999 ER sweep (p from 0.0001 to 0.01), 1000 ER Poisson-regime (n=2000, p=8/2000), 1008 WS sweep (beta from 0 to 1), 1002 BA sweep (m from 1 to 10).
- Visualisation: spring layout for ER/WS, Kamada-Kawai for BA. Matplotlib exports PNG to ./outputs/. Comparison dashboard: 6-panel figure.

## Open Questions
- Can the simulation be parallelised across CPU cores for larger sweeps (n=10,000+)?
- What GPU-accelerated graph libraries (cuGraph) could replace NetworkX for large-n simulations?

## Sources
- NetworkX documentation
- random_graphs.py source code

## Related
[[ai-kos]] [[ai-kos-mission]] [[ai-kos-plan]] [[article-types-guide]] [[creation-protocol]] [[docling-graph-research]] [[durable-execution-research]] [[harden-aws-ssm-jump-host]] [[hybrid-search-research]] [[ingest-file]] [[langgraph-orchestration-research]] [[memsearch-claude-memory-research]] [[obsidian-graph-idea]] [[oss-consolidation-strategy]] [[process-articles-backup-skills]] [[processing-inbox-with-taskqueue]] [[random-graph-dissertation-mission]] [[random-graph-dissertation-notes]] [[random-graph-simulation-suite]] [[run-random-graph-suite]] [[session-end-protocol]] [[session-writeback]] [[taskqueue-how-it-works]]
