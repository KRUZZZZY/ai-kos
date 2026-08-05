---
id: 7b2ff7a1-16f4-4e9c-b714-e9575c2518ab
title: How to Process Inbox Files with the TaskQueue
slug: processing-inbox-with-taskqueue
type: process
created_at: '2026-08-05'
updated_at: '2026-08-05'
reviewed_at: '2026-08-05'
next_review_at: '2027-08-05'
stability: moderate
sensitivity_label: internal
confidence: 0.8
keywords:
- taskqueue
- inbox
- ingestion
- sqlite
- queue
- process
- ai-kos
summary: 'Step-by-step procedure for processing AI-KOS inbox files with the TaskQueue:
  scanning the inbox, defining an ingestion handler, processing with parallel workers,
  handling retries and dead-letter tasks, and cleaning up.'
related:
- article-types-guide
- configuring-declarative-bindings
- deep-research-pipeline-workflow
- docling-graph-research
- networkx-implementation-notes
- process-articles-backup-skills
- random-graph-simulation-suite
- setting-up-semantic-search
- taskqueue-how-it-works
- using-the-research-pipeline
- wire-ai-kos-mcp-server
provenance:
- ai_kos/taskqueue.py
retrieval_count: 0
gap: false
tags:
- type/process
---

## Outcome
Files dropped in the inbox/ directory are automatically discovered, enqueued, and processed by worker threads. Failed files retry automatically; permanently failed files are quarantined in the dead-letter queue for manual inspection. The inbox stays clean.

## Prerequisites
- AI-KOS v1.5+ with taskqueue module
- Write access to the knowledge directory (for taskqueue.db)
- An inbox directory with files to process
- An ingestion handler function that takes a Task and returns a result string

## Steps
1. STEP 1: Create a queue instance. q = TaskQueue(). The database is created at knowledge/taskqueue.db. If you want a different location, pass db_path='/custom/path/tasks.db'. The tasks table is created automatically on first use.
2. STEP 2: Scan the inbox. count = q.scan_inbox(). This discovers all files in the configured inbox directory and enqueues any that are not already pending or processing. Returns the number of new files found. Run this periodically or call it before processing.
3. STEP 3: Define your handler. The handler receives a Task object with filepath, priority, and other metadata. It should extract text, classify, and create an article. Minimum example: def handler(task): from ai_kos.ingestion import extract; result = extract(task.filepath); return result.get('slug', 'processed'). Return a string to record as the task result; raise an exception to trigger retry.
4. STEP 4: Process the queue. counts = q.process_all(handler=handler, max_workers=3). This dequeues all pending tasks and processes them in parallel using ThreadPoolExecutor. Returns dict with 'completed', 'failed', 'dead_letter' counts. Tasks that raise exceptions are retried up to 3 times with exponential backoff before moving to dead_letter.
5. STEP 5: Handle dead-letter tasks. Check stats with q.stats(). If dead_letter count > 0, inspect with q.list_tasks(status='dead_letter') to see what failed and why. Fix the underlying issue, then retry with q.retry_dead_letters() which resets their attempts to 0 and moves them back to pending.
6. STEP 6: Clean up. After successful processing, clear completed tasks with q.clear_completed() to free database space. This removes completed task records while keeping the database file small. Re-scan the inbox to catch any new files that arrived during processing.

## Related
[[article-types-guide]] [[configuring-declarative-bindings]] [[deep-research-pipeline-workflow]] [[docling-graph-research]] [[networkx-implementation-notes]] [[process-articles-backup-skills]] [[random-graph-simulation-suite]] [[setting-up-semantic-search]] [[taskqueue-how-it-works]] [[using-the-research-pipeline]] [[wire-ai-kos-mcp-server]]
