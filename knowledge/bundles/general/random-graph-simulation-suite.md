---
id: f579189d-9ae0-42d4-b1c4-4e87e7c54d99
title: Random Graph Simulation Suite — How It Works
slug: random-graph-simulation-suite
type: help
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
- networkx
- sqlite
- visualisation
- python
- ai-kos
- knowledge
summary: 'How the Random Graph Simulation Suite works: generates ER/WS/BA graphs,
  computes metrics, stores results in SQLite, and produces publication-quality figures.'
related:
- networkx-implementation-notes
- random-graph-dissertation-notes
- run-random-graph-suite
provenance:
- projects/Disertation/Writing/Material/README.md
retrieval_count: 0
gap: false
project: Random Graph Simulation Suite
component: Simulation pipeline (random_graphs.py + SQLite)
tags:
- type/help
---

## Component
The simulation suite is a single Python script (random_graphs.py) with three model generators: make_erdos_renyi(n, p), make_watts_strogatz(n, k, beta), and make_barabasi_albert(n, m). Each returns a networkx.Graph with a seed parameter for reproducibility. Metrics are computed via compute_metrics(G) returning average degree, clustering coefficient, average path length, and component sizes. Results are stored in an SQLite database (random_graphs.db) via save_run() which records model type, parameters, metrics, and timestamps. Database queries support sorting by any metric across the full parameter grid. Visualisation uses matplotlib with layout algorithms from networkx — spring layout for ER/WS, Kamada–Kawai for BA. The bulk_simulate() function runs parameter sweeps: ~3,010 graphs across all three models in a single run (~5-10 minutes). The demo produces 9 outputs in sequence: database init, single graphs, parameter sweep visual, bulk simulation, database queries, metric plots, small-world plot, comparison dashboard, and Poisson residual analysis.

## Examples
- from random_graphs import make_erdos_renyi, compute_metrics, save_run
- G = make_erdos_renyi(n=1000, p=0.001, seed=42)
- metrics = compute_metrics(G)  # {'avg_degree': 5.95, 'clustering': 0.056, 'avg_path_length': 2.64}
- save_run('erdos_renyi', {'n': 1000, 'p': 0.001}, metrics)
- Results viewable via: sqlite3 random_graphs.db 'SELECT * FROM runs ORDER BY clustering DESC LIMIT 10'