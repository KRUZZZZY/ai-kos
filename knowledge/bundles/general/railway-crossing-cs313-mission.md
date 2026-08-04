---
id: 070d05db-be6a-48ae-956a-d1f605663265
title: 'Mission: Railway Level Crossing Control System (CS-313)'
slug: railway-crossing-cs313-mission
type: mission
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
confidence: 0.8
keywords:
- mission
- cs313
- railway
- safety-critical
- spark-ada
- formal-verification
- project
summary: Safety-critical railway level crossing control system in SPARK Ada with formal
  verification. Fail-safe design for Swansea CS-313 module.
related: []
provenance:
- inbox/CS-313/
retrieval_count: 0
gap: false
project: Railway Level Crossing Control System
tags:
- type/mission
---

## Purpose
Implement a safety-critical railway level crossing barrier control system in SPARK Ada. Prove the fundamental safety property: barriers must be down whenever a train is within danger distance or sensor faults occur.

## Architecture
SPARK Ada implementation with formal verification of safety properties. Monitors multiple trains with dynamic danger distance calculation based on speed and braking profiles. Sensor health monitoring with fail-safe default (barriers down on any fault). Multiple redundant checks — no single point of failure. Conservative danger distances account for worst-case braking. Designed for the CS-313 (Safety-Critical Systems) module at Swansea University.

## Dependencies
- SPARK Ada toolchain
- GNATprove for formal verification

## Success Criteria
- Barrier control logic formally verified — barriers down when train in danger zone
- Fail-safe behavior proven — any sensor fault → barriers down
- Dynamic danger distance calculation accounts for speed and braking
- No single point of failure in the control logic