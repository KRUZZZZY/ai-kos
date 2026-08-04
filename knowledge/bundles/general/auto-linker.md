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
The auto-linker scans all knowledge articles and extracts their keywords from YAML frontmatter. For every pair of articles, it counts shared keywords. If two articles share 3 or more keywords, the linker creates bidirectional [[wikilinks]] by updating the 'related' field in each article's frontmatter. The linker also detects merge candidates — when one article's keywords overlap with another's by more than 80%, it flags them as potential duplicates that should be reviewed and possibly merged. The linker runs automatically after every article creation or update, ensuring the knowledge graph stays connected.

## Examples
- Article A has keywords [ai-kos, database, search]. Article B has keywords [ai-kos, database, linking]. They share 'ai-kos' and 'database' — only 2 keywords, so no link is created.
- Article C has keywords [ai-kos, database, auto-link, keywords]. Article A shares [ai-kos, database] — only 2. Article B shares [ai-kos, database] — only 2. No links yet.
- Add 'auto-link' to Article A's keywords. Now A and C share [ai-kos, database, auto-link] — that's 3 keywords, so a link is created.

## Related
[[choosing-keywords]] [[keyword-system]]