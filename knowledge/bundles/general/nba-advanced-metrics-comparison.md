---
id: ab628f7f-f51a-4a07-9d99-ef323c576795
title: 'Research: NBA Advanced Metrics Comparison'
slug: nba-advanced-metrics-comparison
type: research-note
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- nba
- metrics
- epm
- rpm
- raptor
- bpm
- analytics
- statistics
summary: 'Comparison of NBA advanced impact metrics by retrodiction RMSE: EPM (2.48),
  RPM (2.60), RAPTOR (2.63), BPM (2.71), raw RAPM (2.80), PER (3.20).'
related:
- nba-role-based-metric
provenance:
- inbox/Building Role-Based NBA Metric.md
retrieval_count: 0
gap: false
topic: NBA Advanced Impact Metrics
tags:
- type/research-note
---

## Topic: 

## Key Notes
- EPM (Estimated Plus-Minus): Tracking + Box + RAPM with Bayesian Ridge prior. Best retrodiction RMSE at 2.48. 94.2% metric-driven, only 5.8% roster continuity.
- RPM (Real Plus-Minus): Box + Play-by-Play + RAPM. RMSE 2.60. 89.3% metric-driven.
- RAPTOR: Tracking + Box + On/Off. Weighted component regression. RMSE 2.63.
- BPM 2.0 (Box Plus-Minus): Pure box score, position-adjusted regression. RMSE 2.71 — surprisingly good for no tracking data.
- Raw RAPM: Pure on/off lineups, unprioritized ridge regression. RMSE 2.80 — noisy without prior.
- PER (Player Efficiency Rating): Pure box score, unadjusted additive linear weights. RMSE 3.20 — worst performer, only 74.9% metric-driven.
- Key insight: Bayesian priors from role-based tracking/box profiles consistently outperform unadjusted metrics. The proposed archetype-based metric targets EPM-level accuracy.

## Sources
- DunksAndThrees.com metric comparison
- Basketball Index LEBRON documentation

## Related
[[nba-role-based-metric]]
