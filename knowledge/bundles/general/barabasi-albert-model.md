---
id: 9672bc9e-78c2-418a-bffd-aacc424a5ebc
title: Barabási–Albert Scale-Free Model
slug: barabasi-albert-model
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- barabasi-albert
- scale-free
- power-law
- preferential-attachment
- random-graph
- mathematics
summary: 'Barabási–Albert model: growth by preferential attachment. New nodes connect
  to existing nodes with probability proportional to degree, producing scale-free
  networks with P(k)∝k^(-3).'
related:
- random-graph-model-comparison
- random-graph-models
provenance:
- projects/Disertation/Writing/dissertation.txt
- projects/Disertation/Reading/RemcoVol1.pdf
retrieval_count: 0
gap: false
tags:
- type/base
---

The Barabási–Albert model generates scale-free networks through two mechanisms: growth and preferential attachment. Start with a small seed graph of m₀ nodes. At each step, add one new node with m edges connecting to existing nodes. Connection probability is proportional to degree: P(connect to v) = d(v)/∑d(u). Rich-get-richer dynamics. This produces power-law degree distributions P(k)∝k^(-τ) with τ≈3, confirmed by mean-field theory. Mean degree ⟨k⟩=2m. The network has hubs — nodes with very high degree that dominate connectivity. The model explains the scale-free structure of the World-Wide Web (pages link to popular pages), citation networks (papers cite well-cited papers), and protein interaction networks. Finite-size effects: at small n, the power-law tail is truncated. Aggregating over many runs at larger n stabilises the tail. Single runs at n=30 show tail truncated at degree 20 with OLS slope far from -3. The BA model, published by Barabási & Albert in Science (1999), revolutionised network science by showing how simple growth rules produce complex structure.