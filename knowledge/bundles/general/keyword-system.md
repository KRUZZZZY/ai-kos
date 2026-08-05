---
id: 374c0075-96e7-4d2e-a7e1-073b1f4ad9fb
title: AI-KOS Keyword System
slug: keyword-system
type: help
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: stable
sensitivity_label: internal
keywords:
- keywords
- linking
- auto-link
- overlap
- merge
- wikilinks
summary: How AI-KOS keywords drive automatic article linking and duplicate detection.
related:
- auto-linker
- choosing-keywords
- creation-protocol
provenance:
- ai-kos-linker.py
- ai-kos-schemas.py
retrieval_count: 0
project: AI-KOS
component: Keyword system (linker.py + schemas.py)
tags:
- type/help
---


## Component
Every AI-KOS article has 3-8 lowercase keywords in its YAML frontmatter. Keywords serve two purposes: auto-linking and duplicate detection. AUTO-LINKING: The linker scans all articles. When two articles share 3 or more keywords, it creates bidirectional [[wikilinks]] between them by updating each article's 'related' field. This means the knowledge graph builds itself — you don't manually create links, the keywords do it. DUPLICATE DETECTION: When keyword overlap between two articles exceeds 80% (of the smaller set), the linker flags them as merge candidates. This prevents knowledge fragmentation. KEYWORD RULES: 3-8 keywords, all lowercase, no duplicates. Include the main topic, related concepts, the article type, and any tool or technology mentioned. Avoid generic words like 'the' or 'and'. Choose words another article on a related topic would also use — that's what drives linking.

## Examples
- ai-kos article: [ai-kos, knowledge, database, auto-link, articles, hermes]
- ai-kos-mission article: [mission, ai-kos, database, hermes, knowledge, auto-link]
- Shared keywords: ai-kos, database, knowledge, auto-link, hermes = 5 shared → linked + merge candidate (83% overlap)
- ingest-file article: [ingest, file, ai-kos, pdf, docx, extract] → shares only 'ai-kos' with ai-kos article = 1 shared → no link (good, they're different enough)

## Related
[[auto-linker]] [[choosing-keywords]] [[creation-protocol]]
