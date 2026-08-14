# ATQ Protocols — Working Draft (v0.1, pending research validation)

Status: DRAFT — to be refined with findings from research subagents (frameworks, durable queues, autonomy) and persisted as AI-KOS process articles during the documentation phase.

## P0. Least-Risk Action Protocol (choose the least risky option, almost always)

Classify EVERY action before executing, on a 4-tier scale:

- TIER 0 — READ-ONLY / NO SIDE EFFECTS: search, read, list, status, diff, plan.
  Always allowed. Never needs approval. Default when unsure.
- TIER 1 — REVERSIBLE LOCAL WRITE: create a new file, edit a file (git-tracked,
  diffable), run tests, write to a scratch/worktree, create a task, post a comment.
  Allowed with a stated intent in the task handoff ("I will X because Y").
  Prefer additive edits; never delete; never overwrite without keeping the old
  content reachable (git).
- TIER 2 — DESTRUCTIVE / IRREVERSIBLE: rm -rf, git reset --hard, force-push,
  overwriting a config/secrets file, dropping a DB table, modifying ~/.hermes
  config, destructive AI-KOS migrations, anything touching another agent's
  claim/workspace. NOT ALLOWED silently: the worker must (a) stop, (b) mark the
  task blocked with escalation reason, (c) leave the queue paused flag set.
  The queue manager (or human) reviews and either approves (with explicit
  unblock) or replans.
- TIER 3 — EXTERNAL / COST-INDUCING: paid API calls at scale, network writes,
  publishing, sending messages. Rate-limited and budget-checked (see P3).

Tie-break rule: when two options look equivalent, pick the one with the shorter
rollback path (fewest irreversible effects). When in doubt between acting and
asking, act if TIER 0/1; ask if TIER 2/3.

## P1. Minimal-Question Protocol (ask less, default-and-escalate)

- Default action: CONTINUE. A worker that can make progress on TIER 0/1 actions
  makes progress. Do not stop to ask permission for the default path.
- Escalate ONLY when: (a) the action is TIER 2/3, (b) two mutually-exclusive
  interpretations of the task produce materially different deliverables and
  the wrong one wastes >30 min, (c) prerequisites are missing in a way that
  can't be worked around, (d) the queue manager has paused the queue.
- Escalation format: one comment on the task, status -> blocked, block_kind
  set, exact question + the two candidate answers + the worker's recommended
  default. The queue manager's decision rule: if the recommendation is TIER
  0/1-compatible, approve the default without human input; only TIER 2/3 or
  genuine ambiguity reaches the human.
- Question budget: queue manager tracks questions per mission; >3 human
  escalations in 24h on one mission -> queue pauses with a summary alert.

## P2. Autonomy / Keepalive Protocol (run for prolonged periods)

- The queue manager runs as a cron-driven loop (every N minutes) OR a
  long-lived daemon session; every tick it: checks board health, reaps nothing
  itself (kanban dispatcher owns reaping), creates follow-up tasks from
  completed outcomes, promotes triage via decompose, escalates blocked/triage-
  loop tasks per thresholds.
- Heartbeat: any worker holds a claim; kanban's lease (default 15 min) +
  heartbeat columns detect stalls; workers that cannot finish must extend
  heartbeat or release the claim EXPLICITLY (never let the lease silently
  expire while still working — it causes duplicate dispatch).
- Loop detection: if the same task is re-blocked for the same block_kind more
  than N times (kanban block_recurrences -> triage), the queue manager must
  NOT re-dispatch it; it goes to triage for replanning or human.
- Budget guards: per-mission caps on (a) total worker API spend, (b) max
  concurrent workers (3), (c) max attempts per task (3), (d) max runtime per
  task (max_runtime_seconds). When a cap hits: pause queue, alert, no new
  dispatches.
- Drift guard: the queue manager re-reads the mission article every tick and
  compares completed work against success criteria; work that doesn't map to
  a success criterion is marked as scope creep and parked (not discarded).
- Shutdown/restart: all state is in SQLite (kanban DB + AI-KOS KB) — a crash
  anywhere is recovered by the next tick (idempotent loop, no in-memory
  scheduler state). Never hold critical state in the agent's context; write
  it to the board.

## P3. No-Clobber Protocol (agents don't get in each other's way)

- Every task claims exclusive ownership (kanban claim_lock). A worker touches
  ONLY files inside its claim's workspace_path/worktree (kanban workspace
  isolation). Cross-task files: read-only, unless explicitly granted in the
  task body.
- Artifact naming: outputs go under the task's workspace with a
  `<task-id>-<artifact>.ext` convention; completion records artifact paths in
  the task result metadata so the tester can find them without guessing.
- Two agents never edit the same file: if a task requires editing a file
  another task claims, the worker does NOT edit it — it notes the dependency
  and blocks with block_kind=dependency (kanban routes dependency blocks to
  todo, not blocked).
- The shared blackboard (swarm root comments) is append-only JSON under
  [swarm:blackboard]; later keys replace earlier ones by design (kanban
  latest_blackboard semantics) — agents write FACTS, not opinions, to the
  blackboard.
- AI-KOS KB writes: article creation is additive; before creating, search
  (ai_kos_search) to avoid duplicates; never delete or supersede another
  agent's article without a comment on the task.

## P4. Testing / Verification Protocol (tester agent)

- Every task declares acceptance criteria at creation (planner's job; kanban
  body + verifier gate). The tester (verifier role) checks EVIDENCE, not
  claims: artifact exists, tests pass (exact command + output), criteria
  checklist marked.
- Verifier decision: complete with metadata {"gate": "pass"} OR block with
  exact missing work (never vague "needs improvement"). Re-blocked-for-
  verification tasks increment attempts; after 3 failed verifications the
  task returns to the queue manager for replanning, not another blind retry.
- Verifier must be a DIFFERENT agent/profile than the worker (kanban swarm
  enforces this via separate assignees).

## P5. Human Oversight Protocol (when humans DO get involved)

- Humans see a single aggregated view: blocked/triage tasks, queue health,
  budget usage, open questions — via `hermes kanban list` + a run report the
  queue manager writes per mission.
- All escalations carry: task id, block_kind, the exact question, the
  recommended default, and what happens if the human does nothing (the
  default path). Default = least-risk.
- Nothing auto-destructive ever runs while the queue is paused; pausing is
  the human's (or budget guard's) kill switch. Resume = unblock.

## Open questions (for research validation)

- Q1: Are 3 tiers enough, or should TIER 2 split destructive-local vs
  destructive-global? (research: action-risk classification in agentic coding)
- Q2: What does the literature say about the right human-escalation
  threshold per unit time? (research: human-in-the-loop gating)
- Q3: Should the queue manager use a local model (devstral) or flash for the
  judgment loop? Latency vs cost tradeoff; VRAM contention with workers.
