---
id: 8d8ade69-be44-4dbf-b26b-bbbb150634b6
title: 'Graph Theory: Nodes, Edges, Adjacency, and Degrees'
slug: graph-theory-basics
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- graph-theory
- nodes
- edges
- adjacency
- degree
- random-graph
- erdos-renyi
- mathematics
summary: 'Fundamental graph theory definitions: graphs G=(V,E), adjacency matrices,
  vertex degrees, connected components, and random graphs as probability distributions
  over graph structures.'
related:
- erdos-renyi-model
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

A graph G=(V,E) consists of a finite vertex set V with |V|=n and an edge set E of unordered pairs of distinct vertices. Vertices represent objects; edges represent relationships. A graph is simple if it has no self-loops or multi-edges, and undirected if every edge {u,v} is unordered. The adjacency matrix A is an n×n matrix where A_ij=1 if {i,j}∈E and 0 otherwise; for simple undirected graphs, A is symmetric with zeros on the diagonal. The degree d(v) of vertex v is the number of neighbours |N(v)|. The degree sequence is (d(v₁),...,d(vₙ)). Mean degree ⟨k⟩ = (1/n)∑d(v) = 2|E|/n since each edge contributes to two degrees. In the Erdős–Rényi model G(n,p), edges are present independently with probability p, and E[⟨k⟩] = (n-1)p ≈ np for large n. A connected component is a maximal set of vertices where every pair has a path between them. A graph is connected if it has exactly one component.