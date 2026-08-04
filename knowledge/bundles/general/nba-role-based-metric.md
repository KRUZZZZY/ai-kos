---
id: 3a574ae0-dc8b-4e1a-a095-4f774f7b9e18
title: 'Role-Based NBA Impact Metric: Architecture and Mathematics'
slug: nba-role-based-metric
type: base
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- nba
- basketball
- analytics
- rapm
- pca
- clustering
- machine-learning
- statistics
summary: 'Architecture for a positionless NBA impact metric: PCA dimensionality reduction,
  unsupervised clustering into functional archetypes, Bayesian RAPM with SPM prior,
  and lineup interaction modeling.'
related:
- nba-advanced-metrics-comparison
provenance:
- inbox/Building Role-Based NBA Metric.md
retrieval_count: 0
gap: false
tags:
- type/base
---

Traditional 5-position NBA taxonomy (PG/SG/SF/PF/C) fails to capture modern positionless basketball. A role-based impact metric replaces positional labels with data-driven functional archetypes. The pipeline has four stages. Feature engineering: build a high-dimensional matrix of per-100-possession rate statistics covering shooting spectrum (TS%, 3PAr, unassisted FG%), playmaking (USG%, AST%, TOV%), rebounding (ORB%, DRB%), and defense (STL%, BLK%, rim FG% allowed). Dimensionality reduction: PCA extracts orthogonal skill axes, removing multicollinearity between usage rate and turnover volume. Unsupervised clustering: K-Means++ or GMM on reduced component space, computed separately for offense and defense. Produces 10-14 dual-sided archetypes (on-ball creator, off-ball shooter, roll-cut finisher, point-of-attack defender, rim-deterrent anchor). Impact modeling: Bayesian RAPM with SPM prior. Ridge regression solves the ill-posed lineup stint matrix by shrinking coefficients toward a role-stabilized box/tracking prior. Luck adjustments: opponent 3PT/FT% regressed to league average, garbage-time downweighted by leverage index. Lineup interactions: multi-way archetype interaction terms capture synergy (creator+spacer+finisher) and redundancy (dual ball-dominant creators). Wins Added = RAPM * possessions * marginal points per win. Validation: out-of-sample retrodiction RMSE. EPM achieves 2.48 (best), RPM 2.60, RAPTOR 2.63, vs PER 3.20 (worst).