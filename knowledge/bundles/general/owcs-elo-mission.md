---
id: fd59c84f-2b39-42b9-8249-f5859ef1ad13
title: 'Mission: OWCS Elo Rating System'
slug: owcs-elo-mission
type: mission
created_at: '2026-08-04'
updated_at: '2026-08-04'
reviewed_at: '2026-08-04'
next_review_at: '2027-08-04'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- mission
- owcs
- elo
- overwatch
- esports
- liquipedia
- project
summary: ELO rating system for Overwatch Championship Series (OWCS) esports. Scrapes
  Liquipedia for match data, computes ELO ratings, maintains a database.
related:
- cs375-revision-app-mission
- internship-finder-mission
- ma308-coursework-mission
- railway-crossing-cs313-mission
- random-graph-dissertation-mission
provenance:
- inbox/OWCS elo/
retrieval_count: 0
gap: false
project: OWCS Elo
tags:
- type/mission
---

## Purpose
Build an ELO rating system for the Overwatch Championship Series (OWCS) esports league. Scrape match results from Liquipedia, compute updated ELO ratings after each match, and maintain a historical rating database.

## Architecture
Python-based system with a SQLite database for persistent rating storage. A Liquipedia scraper fetches match results (team names, scores, dates) from cached HTML pages. The ELO calculation engine processes matches sequentially, updating team ratings using standard ELO formula with configurable K-factor. Results are stored in app/data/database.sqlite3 with tables for teams, matches, and rating history. A bot logs activity to liquipedia_bot.log for monitoring scraping health.

## Dependencies
- Python 3.x
- SQLite3
- requests for Liquipedia scraping
- BeautifulSoup4 or lxml for HTML parsing

## Success Criteria
- Scrapes OWCS match results from Liquipedia reliably
- Computes accurate ELO ratings with configurable K-factor
- Maintains historical rating database with match-level granularity
- Bot logs scraping activity and errors for monitoring

## Related
[[cs375-revision-app-mission]] [[internship-finder-mission]] [[ma308-coursework-mission]] [[railway-crossing-cs313-mission]] [[random-graph-dissertation-mission]]
