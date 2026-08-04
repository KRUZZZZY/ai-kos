---
id: e759b7ab-22c8-4280-ab21-b47a143c65f8
title: 'Comparing Random Graph Models: ER vs WS vs BA'
slug: random-graph-model-comparison
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- random-graph
- comparison
- erdos-renyi
- watts-strogatz
- barabasi-albert
- mathematics
summary: Side-by-side comparison of ER, WS, and BA random graph models across degree
  distribution, clustering, path length, and real-world applicability.
related:
- barabasi-albert-model
- erdos-renyi-model
- graph-theory-basics
- network-metrics
- random-graph-dissertation-mission
- random-graph-dissertation-notes
- random-graph-models
- watts-strogatz-model
provenance:
- projects/Disertation/Writing/dissertation.txt
retrieval_count: 0
gap: false
tags:
- type/base
---

The three canonical random graph models capture different aspects of real-world networks. Erdős–Rényi: Poisson degree distribution with exponential tail — no hubs. Clustering C≈p≪1 for sparse graphs — fails to match real clustering. Path length L≈log n/log(np) — short, matching real networks. Best for: modelling baseline random connectivity, studying phase transitions. Watts–Strogatz: degree distribution is regular-like (all vertices have similar degree) — no hubs. Clustering is high for small β — matches real social networks. Path length drops sharply with just a few random shortcuts. Best for: social networks, neural networks, power grids — any network needing both clustering and short paths. Barabási–Albert: power-law degree distribution P(k)∝k^(-3) — has hubs, matches many real networks. Clustering is moderate but not as high as WS. Path length is very short due to hubs acting as shortcuts. Best for: the Web, citation networks, protein interactions — growing networks where popularity breeds more popularity. Key insight: no single model captures all properties. Real networks often combine features: power-law degrees (BA) with high clustering (WS).