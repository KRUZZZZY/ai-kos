---
id: 9268a8f0-b525-46f5-97f4-ccf026d40ff2
title: How the TaskQueue SQLite-Backed Priority Queue Works
slug: taskqueue-how-it-works
type: help
created_at: '2026-08-05'
updated_at: '2026-08-05'
reviewed_at: '2026-08-05'
next_review_at: '2027-08-05'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- taskqueue
- sqlite
- priority-queue
- inbox
- ingestion
- retry
- dead-letter
- ai-kos
summary: How TaskQueue provides SQLite-backed priority queuing with thread-pool processing,
  exponential backoff retry, dead-letter isolation, and inbox directory scanning for
  reliable AI-KOS file ingestion.
related:
- deep-research-pipeline-workflow
- docling-graph-research
- networkx-implementation-notes
- processing-inbox-with-taskqueue
- random-graph-simulation-suite
- research-pipeline-how-it-works
provenance:
- ai_kos/taskqueue.py
retrieval_count: 0
gap: false
project: AI-KOS Architecture Modernization
component: TaskQueue
tags:
- type/help
---

## Component
The TaskQueue is a SQLite-backed priority queue that provides reliable, retryable ingestion for AI-KOS inbox files. It uses a single SQLite database (knowledge/taskqueue.db) with WAL mode for concurrent access and a 5-second busy timeout to handle contention. Tasks are enqueued with a filepath and optional priority (lower number = higher priority). A worker pool (default 3 threads via ThreadPoolExecutor) dequeues tasks one at a time, processes them through a user-supplied handler function, and marks them complete. If a handler raises an exception, the task is reset to 'pending' for retry (with exponential backoff delay) up to max_retries attempts. After exhausting retries, the task moves to 'dead_letter' status with the last error recorded. The scan_inbox() method discovers new files in the inbox directory and enqueues them, skipping any that are already pending or processing. Completed tasks can be cleared, and dead-letter tasks can be retried in bulk. This adopts Cloudflare Queues' producer/consumer pattern but runs entirely locally with no external dependencies beyond Python's sqlite3.

## Examples
- Basic usage: q = TaskQueue(); q.enqueue('/path/to/file.pdf'); q.process_all(handler=my_ingest_function)
- Scanning inbox: count = q.scan_inbox() discovers and enqueues all new files in the inbox directory
- Retrying failures: stats = q.stats(); if stats.get('dead_letter', 0) > 0: q.retry_dead_letters()
- Priority ordering: q.enqueue('/tmp/critical.md', priority=0) is processed before q.enqueue('/tmp/low.md', priority=10)
- Inspecting queue: q.list_tasks(status='pending', limit=10) shows next tasks to be processed

## Related
[[deep-research-pipeline-workflow]] [[docling-graph-research]] [[networkx-implementation-notes]] [[processing-inbox-with-taskqueue]] [[random-graph-simulation-suite]] [[research-pipeline-how-it-works]]
