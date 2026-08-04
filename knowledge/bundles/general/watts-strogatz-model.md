---
id: 0ac96fd9-88f8-4e3d-b614-88bc7aa2be96
title: Watts–Strogatz Small-World Model
slug: watts-strogatz-model
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- watts-strogatz
- small-world
- clustering
- rewiring
- random-graph
- mathematics
summary: 'Watts–Strogatz model: start from ring lattice, rewire edges with probability
  β. Produces small-world networks with high clustering AND short path lengths for
  β∈[0.01,0.1].'
related:
- network-metrics
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

The Watts–Strogatz model interpolates between a regular ring lattice (β=0) and an Erdős–Rényi random graph (β=1). Construction: start with n vertices in a ring, each connected to k nearest neighbours (k/2 per side). Then rewire each edge with probability β: replace one endpoint with a uniformly random vertex, avoiding duplicates and self-loops. At β=0: regular lattice with high clustering C₀=3(k-2)/[4(k-1)] but long paths L₀≈n/(2k). At β=1: random graph with short paths but low clustering C≈k/n. The small-world window: for β∈[0.01,0.1], the network simultaneously maintains C(β)/C₀>0.5 AND L(β)/L₀<0.5. This is the 'small-world' regime — high clustering (like a lattice) with short paths (like a random graph). Published by Watts & Strogatz in Nature (1998), it explained how social networks, neural networks, and power grids can have both properties. The model revealed that very few random 'shortcut' edges suffice to drastically reduce path length while preserving local clustering.