---
id: 6cd3b4f2-0e81-4c5d-82a9-597c8ac37ca2
title: 'Mission: CS-375 Revision App (Scrollo)'
slug: cs375-revision-app-mission
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
- cs375
- revision
- scrollo
- java
- javafx
- project
summary: Java/JavaFX revision application for Swansea CS-375 module. Scrollable flashcard-style
  revision tool with themes and module content.
related:
- internship-finder-mission
- ma308-coursework-mission
- owcs-elo-mission
- railway-crossing-cs313-mission
- random-graph-dissertation-mission
provenance:
- inbox/Year 3 Swansea/CS-375/Revision App/
retrieval_count: 0
gap: false
project: CS-375 Revision App
tags:
- type/mission
---

## Purpose
Build a desktop revision application for the CS-375 (Logic and Computability) module at Swansea University. Provides interactive flashcard-style content review with theming support.

## Architecture
Built with Java and JavaFX for cross-platform desktop deployment. Uses Gradle for build management with version 8.10.2. Module content is stored as JSON files (ma308_appended.json, cs375-logic.json) with question-answer pairs organized by topic. Themes (dark, light, grey) are defined as JSS JSON files. Distributed as a runnable JAR (scrollo-1.0.4.jar) with platform launcher scripts. The name 'Scrollo' suggests a scrollable card-flipping interface.

## Dependencies
- Java 17+
- JavaFX
- Gradle 8.10
- JSON module content files

## Success Criteria
- Scrollable revision interface with card-flip mechanics
- Multiple theme support (dark, light, grey)
- Content covering CS-375 Logic and MA-308 topics
- Cross-platform distribution via JAR + launcher scripts

## Related
[[internship-finder-mission]] [[ma308-coursework-mission]] [[owcs-elo-mission]] [[railway-crossing-cs313-mission]] [[random-graph-dissertation-mission]]
