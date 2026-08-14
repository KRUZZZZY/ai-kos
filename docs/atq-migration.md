# ATQ → Task System v3: additive migration path

How the Agent Task Queue (ATQ) layer sits on top of the existing AI-KOS task
system v3 without modifying or removing anything. Companion to
`docs/atq-worker-protocol.md`.

## Layering (nothing existing was touched)

```
AI-KOS task system v3            (ai_kos/tasks.py + task tools — UNCHANGED)
   ▲ uses task APIs / stores
ATQ layer                         (ai_kos/atq.py, atq_worker.py,
   ▲                                atq_queue_manager.py, atq_director.py)
Hermes kanban substrate           (hermes kanban — SQLite board, claims,
   ▲                                leases, heartbeats, dispatcher)
atq-director MCP server           (ai_kos/atq_director.py — agent-facing
                                    7 tools to direct workers)
```

The ATQ layer is composed entirely of NEW modules; it consumes the task
system's public APIs where a link is needed and otherwise talks to the kanban
DB via the `hermes kanban` CLI. No v3 module was edited to enable ATQ.

## What the ATQ layer provides

| Module | Role |
|---|---|
| `ai_kos/atq.py` | Mission bridge: `ai-kos atq submit/tick/status/report`, planner decompose, spawn caps, pause flag, run reports |
| `ai_kos/atq_queue_manager.py` | Reference queue manager: lease-based dispatch, stale/crash reaping, dead-lettering, atomic claims, per-assignee caps, run report |
| `ai_kos/atq_worker.py` | Reference worker: claim → execute → report → release, sub-delegation + aggregation, task-id artifact prefixes, idempotent side-effect log |
| `ai_kos/atq_director.py` | MCP server (7 tools) giving agents real hands: status/show/workers/spawn_worker/dispatch/comment/tick |
| `docs/atq-worker-protocol.md` | Protocol: lifecycle, no-clobber, least-risk T0–T3, escalation format |

## Enable / disable (zero effect on task system v3)

- **Enable**: (1) run `ai-kos atq submit <mission-slug>` / `ai-kos atq tick
  --board <slug>`, or drive `hermes kanban` directly; (2) optional: add the
  `atq-director` toolset to a profile (`~/.hermes/profiles/<p>/config.yaml`)
  so that agent can direct workers; (3) optional: schedule the cron wrapper
  `~/.hermes/scripts/atq_tick.sh` for unattended ticks.
- **Disable**: stop ticking / remove the cron entry / drop the `atq-director`
  toolset. State files (`~/.hermes/atq/`, kanban DBs) can be left in place or
  deleted; nothing in the task system v3 depends on them.
- v3 behaviour is bit-for-bit identical with ATQ absent: the v3 suite passes
  unchanged (see verification).

## New dependencies

- `hermes kanban` CLI (ships with Hermes Agent) — the only hard dependency.
- Optional: `mcp` Python package for the atq-director MCP server (already used
  by the AI-KOS MCP server).
- Optional: a local LLM for planner decompose (`auxiliary.kanban_decomposer`).

## Verification (2026-08-14)

- Task system v3, unchanged: `pytest tests/test_tasks.py tests/test_taskqueue.py`
  → **44 passed**.
- ATQ layer: `pytest tests/test_atq.py tests/test_atq_worker.py
  tests/test_atq_queue_manager.py` → **38 passed** (queue, leases, delegation,
  safety escalation hooks, aggregation).
- ATQ can be disabled without affecting v3: no shared code paths; ATQ modules
  are import-isolated from v3.
