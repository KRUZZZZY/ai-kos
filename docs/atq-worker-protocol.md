# ATQ Worker Protocol — reference documentation

Defines how a worker agent executes a task on the ATQ kanban: claim → execute →
report → release. Companion to the AI-KOS knowledge article
`research-hermes-kanban-multi-agent-queue-substrate` and the `atq-protocols`
skill. Reference implementation: `ai_kos/atq_worker.py`.

## Roles

| Role | Profile | Responsibility |
|---|---|---|
| Queue manager | `atq-manager` | Decomposes missions, dispatches ready cards, reaps stalls, enforces budgets, writes run reports. Directs workers via the `atq-director` MCP server. |
| Worker | any profile | Claims one card, executes it, reports evidence, releases the lease. May sub-delegate. |
| Tester | `atq-tester` | Verifies EVIDENCE (artifacts + test output), never claims/executes. |
| Human | — | Sees blocked/triage + run report; approves T2/T3 only. |

## Lifecycle (claim → execute → report → release)

1. **Claim**: worker (or the dispatcher on its behalf) atomically moves the card
   `ready → running` with `claim_lock` + `claim_expires`. One worker per card —
   the claim IS the lock. A card whose parents aren't `done` cannot be claimed
   (structural invariant; the runtime demotes it back to `todo`).
2. **Execute**: the worker writes ONLY inside its claim workspace
   (`workspaces/<task_id>/`), naming artifacts `<task_id>-<name>.<ext>`.
   Heartbeats (`last_heartbeat_at`) keep the lease alive; the default lease TTL
   is 15 min (override `HERMES_KANBAN_CLAIM_TTL_SECONDS`).
3. **Report**: the worker comments the outcome (what, how, evidence paths) on
   the card BEFORE completing, so the tester finds artifacts without guessing.
4. **Release**: `complete` transitions `running → done` and closes the run. A
   crash or lease expiry triggers reaping + re-dispatch (at-least-once — the
   worker must be idempotent via its side-effect log).

## Sub-delegation

A worker may split its card into subtasks. Mechanism: the worker calls the
`atq-director` MCP tool `atq_spawn_worker` (create child card + dispatch) or,
as an agent, Hermes `delegate_task`. Rules:

- Every subtask is its own card with an assignee and acceptance criteria.
- The worker tracks all child ids (comment them on the parent) and aggregates
  their completion results before releasing the parent.
- A child that blocks (T2 escalation) blocks the parent's aggregation — the
  worker reports the dependency, it does not silently skip it.
- Artifacts of child tasks live in the CHILD's workspace, never the parent's.

## No-clobber (two workers never collide)

- Exclusive claims: one card = one worker; `claim_lock` is atomic.
- Workspace isolation: each task has its own scratch/worktree workspace.
- Artifact prefix: `<task_id>-` on every output file.
- Shared resources (KB articles, shared files) are read-only unless the card
  body grants write access; cross-task writes require a dependency note +
  `block_kind=dependency`.

## Least-risk defaulting (T0–T3)

| Tier | Action | Worker behaviour |
|---|---|---|
| T0 | Read-only (list, show, read, search) | Auto-act |
| T1 | Reversible write (workspace files, comment, create/dispatch cards, run tests) | Auto-act + log in the handoff |
| T2 | Destructive/irreversible (rm -rf, prod mutation, out-of-workspace write) | NEVER execute — comment the exact question + two candidate answers + recommended default, then block the card with `block_kind` |
| T3 | Hard-stop (budget cap, sandbox escape) | Stop; runtime refuses |

Escalation format on a blocked card: task id, block_kind, exact question,
recommended default, and what happens if the human does nothing.

## Verification (what the tester checks)

- Artifact exists at the recorded path (not just a claim of success).
- Tests pass: exact command + output attached.
- Acceptance criteria from the card body are marked, one by one.
- No files were touched outside the claim workspace.

## Reference implementation

`python3 -m ai_kos.atq_worker --board <slug> --task <t_id> --cmd "<shell cmd>"`

- `--cmd`: executes the command, comments the output, completes with evidence.
- Sub-delegation example:
  `python3 -m ai_kos.atq_worker --board X --task t_abc --subdelegate "title|body|profile"` (repeatable; aggregates all children before completing).

Unit tests: `tests/test_atq_worker.py` (state machine, artifact isolation,
aggregation with mocked kanban).
