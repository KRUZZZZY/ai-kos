---
id: 9b7e13bf-cbab-4b69-9963-c0190f5f3162
title: 'Random Graph Models: ER, WS, and BA'
slug: random-graph-models
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
- erdos-renyi
- watts-strogatz
- barabasi-albert
- network
- mathematics
summary: 'Overview of three canonical random graph models: Erdős–Rényi (Poisson degree,
  sharp phase transition), Watts–Strogatz (small-world, high clustering + short paths),
  and Barabási–Albert (scale-free, power-law degree distribution).'
related:
- barabasi-albert-model
- erdos-renyi-model
- graph-theory-basics
- network-metrics
- random-graph-dissertation-mission
- random-graph-dissertation-notes
- random-graph-model-comparison
- watts-strogatz-model
provenance:
- projects/Disertation/Writing/dissertation.txt
retrieval_count: 0
gap: false
tags:
- type/base
---

Random graph models capture different aspects of real-world networks. The Erdős–Rényi model places edges independently with probability p, producing Poisson degree distributions and a sharp phase transition at p = 1/n where a giant component emerges. The Watts–Strogatz model starts from a ring lattice and rewires edges with probability β, creating small-world networks that simultaneously maintain high clustering and short average path lengths — properties seen in social networks, the brain, and the internet. The small-world window exists for β ∈ [0.01, 0.1] where both metrics cross their thresholds. The Barabási–Albert model grows by preferential attachment — new nodes connect to existing nodes with probability proportional to degree — producing scale-free networks with power-law degree distributions P(k) ∝ k^(-τ) where τ ≈ 3. This explains the hub-dominated structure of citation networks, the web, and protein interaction networks.

## Related
[[barabasi-albert-model]] [[erdos-renyi-model]] [[graph-theory-basics]] [[network-metrics]] [[random-graph-dissertation-mission]] [[random-graph-dissertation-notes]] [[random-graph-model-comparison]] [[watts-strogatz-model]]
