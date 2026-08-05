---
id: 2a176472-6bcf-476c-9c17-ef56c6ef26f7
title: Erdős–Rényi Random Graph Model
slug: erdos-renyi-model
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- erdos-renyi
- random-graph
- phase-transition
- poisson
- giant-component
- mathematics
summary: 'The Erdős–Rényi G(n,p) model: each of the n(n-1)/2 possible edges is present
  independently with probability p. Poisson degree distribution, sharp phase transition
  at p=1/n.'
related:
- barabasi-albert-model
- graph-theory-basics
- network-metrics
- random-graph-dissertation-mission
- random-graph-dissertation-notes
- random-graph-model-comparison
- random-graph-models
- watts-strogatz-model
provenance:
- projects/Disertation/Writing/dissertation.txt
- projects/Disertation/Reading/RemcoVol1.pdf
retrieval_count: 0
gap: false
tags:
- type/base
---

The Erdős–Rényi model G(n,p) places each of the n(n-1)/2 possible edges independently with probability p∈[0,1]. The degree distribution is binomial, approximating Poisson(λ) where λ=np for large n. Key property: sharp phase transition at p=1/n (or λ=1). Below this threshold, all components have size O(log n). Above it, a giant component emerges containing a positive fraction of all vertices. At criticality (λ=1), the largest component scales as n^(2/3). The clustering coefficient is C≈p — very low for sparse graphs, meaning ER graphs lack the high clustering of real networks. Average path length L≈log n / log(np) — short paths ('small world' property). The ER model captures short paths but fails on clustering: real networks have C≫p. This motivated the Watts–Strogatz model which adds clustering to the small-world property.

## Related
[[barabasi-albert-model]] [[graph-theory-basics]] [[network-metrics]] [[random-graph-dissertation-mission]] [[random-graph-dissertation-notes]] [[random-graph-model-comparison]] [[random-graph-models]] [[watts-strogatz-model]]
