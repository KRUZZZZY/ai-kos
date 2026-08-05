---
id: 3db839a1-395f-4bb8-8c69-d7cbf3434150
title: 'Mission: Internship-Finder'
slug: internship-finder-mission
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
- internship
- finder
- project
- uk
- scraping
summary: Project to find and track UK internships. Scrapes listings, sends notifications,
  maintains application status.
related:
- cs375-revision-app-mission
- ma308-coursework-mission
- owcs-elo-mission
- railway-crossing-cs313-mission
- random-graph-dissertation-mission
provenance:
- inbox/Internship-Finder/
retrieval_count: 0
gap: false
project: Internship-Finder
tags:
- type/mission
---

## Purpose
Automate the discovery and tracking of UK internship opportunities. Scrape listings from multiple sources, deduplicate, send email notifications, and maintain an application pipeline.

## Architecture
The project uses Python scripts to scrape internship listings from UK job boards and company career pages. Scraped data is deduplicated and stored. An email notification system alerts when new listings match criteria. An application tracking log records email status, application deadlines, and follow-up actions. The system is designed to run on a schedule (cron) to check for new listings daily.

## Dependencies
- Python 3.x
- requests/beautifulsoup4
- smtplib for email
- cron for scheduling

## Success Criteria
- Scrapes internship listings from 3+ UK sources daily
- Sends email notifications for new matching listings
- Maintains deduplicated database of opportunities
- Tracks application status per listing

## Related
[[cs375-revision-app-mission]] [[ma308-coursework-mission]] [[owcs-elo-mission]] [[railway-crossing-cs313-mission]] [[random-graph-dissertation-mission]]
