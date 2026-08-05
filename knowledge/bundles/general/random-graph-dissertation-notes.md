---
id: 8882deb7-630a-4221-a1b9-ee7451a61b50
title: 'Research: Simulating Random Graphs — ER, WS, BA Models'
slug: random-graph-dissertation-notes
type: research-note
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
- networkx
- dissertation
- simulation
- ai-kos
summary: 'Undergraduate dissertation: simulating Erdős–Rényi, Watts–Strogatz, and
  Barabási–Albert random graph models in Python with NetworkX and SQLite. Key findings
  on phase transitions, small-world windows, and power-law degree distributions.'
related:
- barabasi-albert-model
- erdos-renyi-model
- graph-theory-basics
- network-metrics
- networkx-implementation-notes
- random-graph-dissertation-mission
- random-graph-model-comparison
- random-graph-models
- random-graph-simulation-suite
- run-random-graph-suite
- watts-strogatz-model
provenance:
- projects/Disertation/Writing/dissertation.txt
retrieval_count: 0
gap: false
topic: Random Graph Simulation and Analysis
tags:
- type/research-note
---

## Topic: 

## Key Notes
- RQ1 — ER phase transition: giant component fraction exceeds 0.5 at p ≈ 1/n, matching theoretical threshold. Poisson degree distribution confirmed with residual analysis showing mean ≈ 1 for n=1000.
- RQ2 — WS small-world window: maintains C(β)/C(0) > 0.5 AND L(β)/L(0) < 0.5 for β ∈ [0.01, 0.1]. Normalisation bug found — must use theoretical lattice clustering C₀ = 3(k-2)/[4(k-1)], not simulated value at β=0.001.
- RQ3 — BA power-law: degree distribution follows P(k) ∝ k^(-τ) with τ ≈ 3 for large n. Single runs at n=30 truncated at degree 20 with wrong slope. Required aggregating many runs at larger n for tail to stabilise.
- SQLite was unplanned but essential — systematic storage across full parameter grid made boundary-value checks for RQ2 straightforward instead of laborious. Difference between anecdotal and systematic analysis.
- Key lesson: normalisation is a modelling choice requiring theoretical justification. Bugs were symptoms of conceptual gaps, not programming errors — code couldn't reveal the gap until returning to mathematics.
- Hardware lesson: hard drive failure a week before first draft presentation. Backup everything. Budget extra time for BA power-law analysis — finite-size effects on slope are themselves a theoretical prediction.

## Open Questions
- How does the BA model's power-law exponent change with different attachment mechanisms beyond preferential attachment?
- What are the finite-size scaling properties of the WS small-world transition — is there a true phase transition or a crossover?

## Sources
- van der Hofstad, Random Graphs and Complex Networks, Vol. I (2017)
- Watts & Strogatz, Nature 393, 440-442 (1998)
- Barabási & Albert, Science 286, 509-512 (1999)
- Erdős & Rényi, Publicationes Mathematicae Debrecen 6, 290-297 (1959)
- NetworkX: Hagberg, Schult, Swart, SciPy 2008

## Related
[[barabasi-albert-model]] [[erdos-renyi-model]] [[graph-theory-basics]] [[network-metrics]] [[networkx-implementation-notes]] [[random-graph-dissertation-mission]] [[random-graph-model-comparison]] [[random-graph-models]] [[random-graph-simulation-suite]] [[run-random-graph-suite]] [[watts-strogatz-model]]
