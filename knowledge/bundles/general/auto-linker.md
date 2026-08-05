---
id: 08613850-a223-4e46-a314-8ebac1651bd4
title: How the Auto-Linker Works
slug: auto-linker
type: help
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
keywords:
- auto-link
- keywords
- wikilinks
- linking
- overlap
summary: Explanation of how AI-KOS automatically creates wikilinks between articles
  sharing keywords.
related:
- choosing-keywords
- creation-protocol
- keyword-system
provenance:
- ai-kos-skill.md
retrieval_count: 0
project: AI-KOS
component: Auto-linker (linker.py)
tags:
- type/help
---


## Component
The auto-linker scans all knowledge articles and extracts their keywords from YAML frontmatter. For every pair of articles, it counts shared keywords. If two articles share 2 or more keywords, the linker creates bidirectional links by updating the 'related' field in each article's frontmatter AND appends a `## Related` section with `[[wikilinks]]` to the body text so Obsidian's graph view renders them. The linker also detects merge candidates — when one article's keywords overlap with another's by more than 80%, it flags them as potential duplicates. The linker runs automatically after every article creation, ensuring the knowledge graph stays connected.

## Examples
- Article A has keywords [ai-kos, database, search]. Article B has keywords [ai-kos, database, linking]. They share 'ai-kos' and 'database' — 2 keywords, so a link IS created (threshold is >=2).
- Article C has keywords [ai-kos, database, auto-link]. Article A shares [ai-kos, database] — 2 keywords, link created. Article B shares [ai-kos, database] — 2 keywords, link created. All three are now interconnected.
- Article D has keywords [rust, systems]. Article A has [ai-kos, database, search]. They share 0 keywords — no link.

## Related
[[choosing-keywords]] [[creation-protocol]] [[keyword-system]]
