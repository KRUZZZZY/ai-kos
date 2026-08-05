---
id: 928ad7e9-2b41-4000-b522-d7e0e4b22b9f
title: 'Network Metrics: Degree Distribution, Clustering, Path Length, and Giant Component'
slug: network-metrics
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- network-metrics
- degree-distribution
- clustering
- path-length
- giant-component
- random-graph
- erdos-renyi
- mathematics
summary: 'Key network metrics for comparing random graph models: degree distribution
  P(k), clustering coefficient C, average path length L, giant component fraction,
  and graph density.'
related:
- barabasi-albert-model
- erdos-renyi-model
- graph-theory-basics
- random-graph-dissertation-mission
- random-graph-dissertation-notes
- random-graph-model-comparison
- random-graph-models
- watts-strogatz-model
provenance:
- projects/Disertation/Writing/dissertation.txt
retrieval_count: 0
gap: false
tags:
- type/base
---

Five key metrics quantify random graph structure. Degree distribution P(k): fraction of vertices with degree exactly k. Heavy-tailed distributions (slow decay) indicate hubs; power-law tails indicate scale-free networks. Clustering coefficient C(v): ratio of edges among neighbours to total possible pairs — measures local triangle density. Average C = (1/n)∑C(v), with C(v)=0 for d(v)≤1. High clustering means friends-of-friends tend to be friends. Average path length L: mean shortest-path distance between all vertex pairs in the largest component. Measures how many steps separate randomly chosen vertices — 'six degrees of separation' corresponds to L≈6. Giant component fraction: size of largest connected component divided by n. Central to Erdős–Rényi phase transition — below p=1/n, all components are O(log n); above, a giant component emerges containing Θ(n) vertices. Graph density: ρ = 2|E|/[n(n-1)] — fraction of possible edges actually present. Dense graphs have ρ close to 1; sparse graphs have ρ≪1.

## Related
[[barabasi-albert-model]] [[erdos-renyi-model]] [[graph-theory-basics]] [[random-graph-dissertation-mission]] [[random-graph-dissertation-notes]] [[random-graph-model-comparison]] [[random-graph-models]] [[watts-strogatz-model]]
