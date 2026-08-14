# Durable Task Queues & Workflow Engines — Mechanisms for an LLM-Agent Task Queue

**Project:** Agent Task Queue (ATQ) — layered multi-agent system where LLM agents execute tasks from a shared queue unattended.
**Scope:** How industrial task queues / workflow engines guarantee durability, and the minimal set of those mechanisms ATQ must implement.
**Systems covered:** Temporal, Celery, Prefect, Argo Workflows, BullMQ, AWS SQS, AWS SWF.
**Date:** 2026-08-13.

---

## 0. TL;DR — the universal building blocks

Every durable system, regardless of stack, converges on the same five mechanisms:

1. **Persistent state store** — tasks/workflows live in a durable store (DB, Redis, etcd/CRDs), *not* in worker memory. The queue/manager is the source of truth; workers are disposable.
2. **Lease / heartbeat** — a task claimed by a worker carries an expiry timestamp. The worker must renew it (heartbeat); if it lapses, the task is declared abandoned and reclaimed. This is how a *stuck or dead* worker is detected.
3. **Atomic claim** — claiming a task is a compare-and-swap / transaction, so two workers can never hold the same task. This is the anti-duplicate-dispatch primitive.
4. **Retry policy + dead-letter** — retries with exponential backoff + jitter, a bounded max attempt count, a notion of *non-retryable* errors, and a terminal "dead-letter" bin for tasks that exhausted retries (for inspection and manual replay).
5. **Idempotency** — the system guarantees *at-least-once* execution, never exactly-once; therefore **the unit of work must be safe to execute more than once**. This is expressed as idempotency keys and side-effect de-duplication.

Everything below is a variation on these five.

---

## 1. Temporal — the reference design (event-sourced durable execution)

Temporal is the most complete expression of these ideas and the closest analogue to "an agent that runs for a long time and must survive crashes."

### 1.1 Core durability mechanism: event sourcing
- Every **Workflow** has an append-only **Event History**. The server stores this history; the workflow's program state is reconstructed by **replaying** the history. If a worker crashes, another worker replays the same events and continues.
- **Workflows must be deterministic**; anything non-deterministic or failure-prone (API calls, LLM calls, file I/O) is pushed into **Activities**, which are recorded in history as events.
- On replay, **already-completed Activities are not re-executed** — their input/output is read from history. This is the key trick that makes "resume from crash" safe.

### 1.2 Lease / heartbeat semantics (stuck-worker detection)
Temporal's server does **not** detect worker crashes directly. It relies on **timeouts** (source: [Detecting Activity failures](https://docs.temporal.io/encyclopedia/detecting-activity-failures)):

| Timeout | Meaning | Default |
|---|---|---|
| `scheduleToStart` | Max time a task may sit queued before a worker picks it up | ∞ |
| `startToClose` | Max time for a *single attempt* after a worker starts it → **the main crash detector** | = scheduleToClose default |
| `scheduleToClose` | Max time for the *whole* Activity Execution (all retries) | must set one of start/scheduleToClose |
| `heartbeatTimeout` | Max time *between heartbeats* during one attempt | none (opt-in) |

- **`startToClose` is the lease.** "The Temporal Server relies on the Start-To-Close Timeout to force Activity retries" — if a worker dies mid-activity, it stops responding, the timer fires, an `ActivityTaskTimedOut` event is written, and (per retry policy) a new attempt is scheduled.
- **Heartbeats are the renewal.** For long-running activities (ML training on GPUs, reading large files) the activity records progress via `heartbeat(details)`. Crucially, **heartbeat details are delivered to the retried attempt**, so the retry can *checkpoint/resume* rather than restart from zero. Quick API calls should *not* heartbeat.

### 1.3 Retries + dead-letter
- Activities have a **default Retry Policy** (source: [Retry Policies](https://docs.temporal.io/encyclopedia/retry-policies)): `initialInterval=1s`, `backoffCoefficient=2.0`, `maximumInterval=100×initial`, `maximumAttempts=∞` (unlimited), `nonRetryableErrors=[]`.
- Retry is **declarative** — you state the policy; you don't write retry loops.
- **Non-retryable errors** let you stop retrying immediately on permanent failures (e.g. validation errors) rather than burning attempts.
- There is **no dedicated DLQ**; a task that exhausts attempts simply ends in a terminal failed state in the event history (which *is* durable and inspectable). Temporal docs recommend setting `maximumAttempts=1` for genuinely non-idempotent activities to get *at-most-once*.

### 1.4 Idempotency + exactly/at-least-once
- **Guarantee is at-least-once.** "Temporal recommends Activities be idempotent" because retries (unlimited by default) mean partial success + re-execution is normal (source: [Idempotency and durable execution](https://temporal.io/blog/idempotency-and-durable-execution)).
- **Idempotency key = Workflow Run ID + Activity ID**, constant across retries, unique across workflows.
- **Workflow-level dedupe**: `Workflow Id Reuse Policy = "Reject Duplicate"` prevents two submissions of the same workflow ID (e.g. double-click) from producing two executions.

---

## 2. Celery — broker-mediated at-least-once via late-ack

Celery is a *distributed task queue*, not a workflow engine; durability comes from the broker (RabbitMQ/Redis) + a few flags. It is the classic "make the broker re-deliver" model.

### 2.1 Core durability mechanism: broker + acknowledgements
- Tasks are messages in a broker. Default behavior is **early ack**: the worker acknowledges the message *on receipt*. If the worker then crashes before finishing, **the task is lost** (source: [Celery Tasks docs](https://docs.celeryq.dev/en/main/userguide/tasks.html)).
- `acks_late=True` flips this to **late ack**: the worker acknowledges *after* the task finishes. If the worker crashes mid-task, the broker **redelivers to another worker** — this is the at-least-once switch.
- `task_reject_on_worker_lost=True`: if the worker process is killed (SIGKILL / OOM-kill), the task is rejected and redelivered *even with acks_late* (normally a killed process can't ack or reject).

### 2.2 Lease / heartbeat semantics: the visibility timeout
- With Redis as broker, an un-acked message is hidden for `visibility_timeout` (default **3600 s = 1 hour**, configured via `broker_transport_options`). If the worker neither acks nor the message is redelivered within that window, the broker considers it **orphaned and re-queues it elsewhere** (source: [Celery ETA tasks demystified — Instawork](https://engineering.instawork.com/celery-eta-tasks-demystified-424b836e4e94), [SO 62606447](https://stackoverflow.com/questions/62606447/how-can-i-disable-redelivery-of-tasks-in-celery-with-redis)).
- **The visibility timeout is the lease**, but Celery has **no true heartbeat** — a long task that exceeds the visibility timeout will be redelivered *while still running* (see [GitHub issue #5935](https://github.com/celery/celery/issues/5935)). This is a well-known footgun: tasks must be idempotent *and* either short, or you must raise the timeout.

### 2.3 Retries + dead-letter
- Built-in `autoretry_for=(Exception,)`, `max_retries`, `retry_backoff` (exponential), `retry_jitter`.
- **No built-in DLQ.** After `max_retries` the task fails; routing to a dead-letter queue is a manual pattern (catch the exception and `.apply_async` to a `dead_letter` queue). The **result backend** (Redis/DB) stores task return values for visibility, but is not a DLQ.

### 2.4 Semantics
- Default (early ack) = **at-most-once with potential loss**; `acks_late` = **at-least-once** (requires idempotent tasks). Exactly-once is **not** provided.

---

## 3. Prefect — orchestration with heartbeat-driven crash detection

Prefect is a workflow orchestrator; the *engine* runs inside the user process, and a server/DB records durable state.

### 3.1 Core durability mechanism: server-persisted state + cached results
- Flow/task **run states** (Scheduled, Late, Pending, Running, Retrying, Failed, Crashed) are persisted to a server DB (Postgres/SQLite or Prefect Cloud).
- Task **results** can be **cached** and **persisted** to a results backend — so a retry of an upstream task doesn't recompute a downstream one.

### 3.2 Lease / heartbeat semantics: zombie-flow detection
- Flow runs **emit heartbeats** (default `PREFECT_FLOWS_HEARTBEAT_FREQUENCY = 180 s`).
- "**Unresponsive run detection**" automation marks a run **`Crashed`** if it misses ~3 heartbeats (≈ 9 minutes by default) — i.e. a worker that died (machine crash, container eviction) is detected by *heartbeat absence*, not by the server pinging it (source: [Detect zombie flows](https://docs.prefect.io/v3/advanced/detect-zombie-flows)).
- `Crashed` is a distinct terminal state from `Failed` — infrastructure failure vs. application error. Automations (event-driven) can then **resubmit/reschedule** the crashed run.
- This is the cleanest "lease = heartbeat" example to copy: **`within ≥ 3× heartbeat_frequency`** to avoid false positives on transient slowness.

### 3.3 Retries + dead-letter
- `retries=N`, `retry_delay_seconds` (scalar, list `[1,2,4,8]`, or `exponential_backoff(backoff_factor=…)`), `retry_jitter_factor`, and `retry_condition_fn` to **skip retry on specific errors** (e.g. 401/404) (source: [Prefect retries](https://docs.prefect.io/v3/how-to-guides/workflows/retries)).
- No dedicated DLQ; terminal `Failed`/`Crashed` states are persisted and queryable for manual replay.

### 3.4 Semantics
- Task retries + caching + result persistence ⇒ at-least-once execution with idempotency/caching on top; crash detection via heartbeats rather than timeouts.

---

## 4. Argo Workflows — Kubernetes-native, CRD-persisted DAGs

Argo runs each workflow step as a **Kubernetes Pod**; the workflow spec and status are persisted as **Custom Resources in etcd**.

### 4.1 Core durability mechanism: CRD + controller reconcile
- The workflow is a declarative object; the Argo **controller** watches and reconciles it. If the controller or a node dies, Kubernetes reschedules Pods and the controller resumes from persisted status.
- **Artifacts** (file outputs) are stored in an **artifact repository** (S3/GCS/etc.) so outputs survive pod death and pass between steps. **Memoization** caches step outputs by key to skip recomputation.

### 4.2 Lease / heartbeat semantics
- No application-level lease. Durability of a *running* step relies on Kubernetes **Pod restart policy** (`podSpec.restartPolicy`) for infra failures (node eviction, OOM) *before the container starts* (source: [Automatic Pod Restarts](https://argo-workflows.readthedocs.io/en/latest/pod-restarts/)).
- A step that *hangs* is bounded by `activeDeadlineSeconds` (per-template) — a timeout that kills the pod and fails the step. This is the closest analogue to a lease (timeout-based, not heartbeat-based).

### 4.3 Retries + dead-letter
- `retryStrategy`: `limit` (max attempts), `retryPolicy` (`Always` / `OnFailure` / `OnError` / `OnTransientError`), `backoff` (duration/factor/maxDuration), and **expression-based conditional retries** using `lastRetry.exitCode/.status/.duration/.message` (source: [Argo Retries](https://argo-workflows.readthedocs.io/en/latest/retries/)).
- **No native DLQ**; terminal failures handled via **exit handlers** / `onExit` templates (notify, escalate, or fan out).

### 4.4 Semantics
- At-least-once per step; retries re-run the container; artifacts + memoization provide idempotency/caching at the data layer.

---

## 5. BullMQ — Redis-native queue with lock + stall detection

BullMQ is the modern Node.js queue on Redis; its "stalled job" machinery is the clearest implementation of the lease/heartbeat idea.

### 5.1 Core durability mechanism: Redis persistence (Lua atomicity)
- Jobs and all queue state live in **Redis**; operations are **atomic Lua scripts** (claim, move, lock).
- (Durability caveat: Redis persistence config — AOF/RDB — determines crash-durability; BullMQ itself relies on Redis.)

### 5.2 Lease / heartbeat semantics: locks + stalled jobs
- When a job is picked up, BullMQ **places a lock** on it. The worker must **periodically renew** the lock (`stalledInterval`); if it fails to (CPU-bound or crashed), the job is marked **`stalled`** and **moved back to `waiting`** to be processed by another worker (source: [BullMQ Stalled Jobs](https://docs.bullmq.io/guide/workers/stalled-jobs)).
- After `maxStalledCount`, a repeatedly-stalled job is moved to the **`failed`** set — this is the dead-letter transition for "worker keeps dying on this task."

### 5.3 Retries + dead-letter
- `attempts` + `backoff` (`fixed` / `exponential` with `delay` and `jitter`), plus a **custom `backoffStrategy(attemptsMade, type, err, job)`** (source: [BullMQ Retrying failing jobs](https://docs.bullmq.io/guide/retrying-failing-jobs)).
- A job is "failed" when the processor **throws** or when it **stalls past `maxStalledCount`**. The **`failed` set is the dead-letter bin** — jobs stay there for inspection and manual `job.retry()` replay.

### 5.4 Semantics
- At-least-once: locks prevent simultaneous processing, but a stalled job *is* reprocessed, so the handler must be idempotent.

---

## 6. AWS SQS — the canonical "lease = visibility timeout + DLQ" model

SQS is the simplest mental model and worth keeping in mind because its primitives map 1:1 onto ATQ.

### 6.1 Lease: visibility timeout
- On `ReceiveMessage`, a message stays in the queue but becomes **invisible** to other consumers for the **visibility timeout** (default **30 s**) (source: [SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)).
- If not deleted before it expires, it becomes **visible again and is redelivered**. **`ChangeMessageVisibility`** extends the timeout mid-processing — i.e. it is the *heartbeat* for long tasks.
- The visibility timeout is *exactly* the lease; the `DeleteMessage` is the explicit "commit" (ack).

### 6.2 Dead-letter queue
- A **redrive policy** with `maxReceiveCount = N` moves a message to the **DLQ** after N receives without successful deletion (source: [SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)).
- DLQ retention should be **longer** than the source queue's retention (the enqueue timestamp is unchanged when moved). Supports **redrive** (move messages back to the source queue for replay).

### 6.3 Semantics — the exact contract
- **Standard queues = at-least-once** (a message may be delivered more than once, *even within the visibility window*); **consumers must be idempotent**.
- **FIFO queues = exactly-once** (dedup by MessageDeduplicationId within a 5-min window) at the cost of throughput (300 msg/s).

---

## 7. AWS SWF — the durable-execution ancestor (predecessor of Temporal/Cadence)

SWF is the historical blueprint for Temporal (Temporal's founders built Cadence from SWF's design).

- SWF **durably maintains execution state** server-side; your decider polls for **decision tasks** and workers poll for **activity tasks** (source: [What is SWF](https://docs.aws.amazon.com/amazonswf/latest/developerguide/welcome.html), [SWF basic concepts](https://docs.aws.amazon.com/amazonswf/latest/developerguide/swf-dg-basic.html)).
- Activity tasks carry **four timeouts**: `scheduleToStart`, `startToClose`, `scheduleToClose`, and `heartbeatTimeout`. Workers call **`RecordActivityTaskHeartbeat`** to renew; if `heartbeatTimeout` elapses, SWF marks the task timed out and (per your decider) reschedules it.
- **SWF guarantees at-least-once** — it explicitly documents that a task *may be delivered more than once* and **activities must be idempotent**. There is no exactly-once.

---

## 8. Comparison table

| System | Persistence | Lease/heartbeat | Retry | Dead-letter | Semantics |
|---|---|---|---|---|---|
| **Temporal** | Event history (DB) | Timeouts (`startToClose`) + optional heartbeat w/ checkpoint details | Declarative retry policy (exp backoff, ∞ default) | Terminal failed state in history | At-least-once (idempotent activities) |
| **Celery** | Broker (RabbitMQ/Redis) | `visibility_timeout` (no true heartbeat; footgun) | `autoretry_for` + backoff | Manual only | Early-ack: at-most-once; `acks_late`: at-least-once |
| **Prefect** | Server DB + results backend | Flow-run heartbeats → `Crashed` after ~3 missed | `retries` + backoff + jitter + condition | Terminal `Failed`/`Crashed` states | At-least-once + caching/idempotency |
| **Argo** | K8s CRD (etcd) + artifact repo | `activeDeadlineSeconds` (timeout), pod restarts | `retryStrategy` + backoff + expressions | Exit handlers only | At-least-once + memoization |
| **BullMQ** | Redis (atomic Lua) | Lock + `stalledInterval` renewal → `stalled`→`waiting` | `attempts` + fixed/exp backoff + jitter | `failed` set (after `maxStalledCount`) | At-least-once (idempotent handlers) |
| **SQS** | AWS-managed queue | Visibility timeout + `ChangeMessageVisibility` heartbeat | `maxReceiveCount` | DLQ + redrive | Standard: at-least-once; FIFO: exactly-once |
| **SWF** | Durable SWF service state | `heartbeatTimeout` + `RecordActivityTaskHeartbeat` | Decider-driven | Terminal state | At-least-once (idempotent activities) |

---

## 9. Design implications for ATQ (LLM-agent queue)

> Context: a "worker" is an LLM agent (deepseek-pro via delegation, ≤3 concurrent) that may **hang, crash, or produce wrong output**; the queue manager is a **local LLM**. This is *worse* than a function queue in three ways: (a) tasks are long (minutes–hours), (b) agents are non-deterministic, (c) "failure" includes *wrong-but-not-crashed* output.

### 9.1 The minimal durability mechanism set ATQ must implement

1. **Durable task store** (single source of truth) — SQLite (WAL + fsync) or Postgres, not in-memory. Persist per-task: `state ∈ {queued, claimed, running, succeeded, failed, dead}`, `attempts`, `lease_expires_at`, `lease_token`, `worker_id`, `last_heartbeat_at`, `progress/checkpoint`, `error_log`, `idempotency_key`.
2. **Atomic claim** (anti-duplicate-dispatch) — claim via `UPDATE tasks SET state='claimed', worker_id=?, lease_token=?, lease_expires_at=? WHERE id=? AND state='queued'` (or `state IN ('queued')` for retry-after-reclaim). Only the worker that wins the row owns it. The row is the mutex.
3. **Lease + heartbeat** — every claim has `lease_expires_at` (e.g. `now + heartbeat_timeout`). The agent process must **renew** (write `last_heartbeat_at` / extend `lease_expires_at`) on a fixed cadence. A separate **reaper/sweeper** loop (which must be resilient to manager crashes) finds `lease_expires_at < now` and does `state: claimed→queued, attempts++` with a **new lease_token**.
4. **Optimistic completion** — an agent may only complete if it presents the **current `lease_token`**; a stale agent (whose lease was reclaimed and re-assigned) must be **rejected** (`WHERE lease_token=?`). This is the second half of anti-duplicate-dispatch.
5. **Retry policy with backoff + jitter + non-retryable classification** — `max_attempts=3` (configurable), exponential backoff + jitter, and an error taxonomy (transient vs permanent vs "wrong output") so we don't retry permanent failures.
6. **Dead-letter bin** — after `max_attempts`, move to `dead` with full error log + last partial output; expose for human/manager inspection and **manual replay** (re-queue with the *same* `idempotency_key`).
7. **Idempotency keys + checkpointed progress** — every task gets a stable `idempotency_key`; every *side effect* the agent performs is recorded under that key so a retry doesn't duplicate it. Heartbeats carry a **checkpoint** so a reclaimed task **resumes** rather than restarts (Temporal's heartbeat-details pattern).

### 9.2 Answering the four failure scenarios

**Worker dies mid-task.** The lease expires (no more heartbeats) → reaper reclaims → task re-queued with `attempts++` and a fresh `lease_token`. If the heartbeat carried a checkpoint, the next agent resumes from it; otherwise it restarts. The `idempotency_key` ensures any side effects the dead agent *did* perform (a file half-written, an API call already sent) are not duplicated by the retry.

**Task fails 3 times.** On the 3rd failure the task transitions to `dead` (dead-letter). Crucially: distinguish *why* it failed — transient (rate-limit, network) vs permanent (invalid input) vs **"wrong output"** (agent succeeded mechanically but produced bad results). Only *transient* failures should consume retries; permanent and wrong-output failures should route to `dead` (or a `needs-human-review` state) immediately. `dead` tasks are never auto-retried; they are surfaced and replayed manually with the same `idempotency_key`.

**Queue manager crashes.** All state is in the durable store, so the manager is stateless w.r.t. the queue — on restart it just re-reads the store. Two things make this safe: (a) the **reaper is a separate/embedded-but-idempotent loop** that runs on a timer regardless of manager liveness, so expired leases still get reclaimed; (b) the manager must **persist any decision before acting** (write-then-act), and its actions must be idempotent (re-dispatching a task that's already `claimed` with a valid lease is a no-op because of the atomic claim). The manager must **not** hold leases itself — leases belong to workers.

**Duplicate dispatch (two agents claim the same task).** Prevented at the source by the **atomic claim** (only one `UPDATE … WHERE state='queued'` succeeds). The *residual* risk is a worker whose lease lapsed (so the task was re-claimed by someone else) and who then tries to "complete" — blocked by the **optimistic `lease_token` check**. If a genuinely double-executed side effect still slips through (e.g. retry after crash), the **idempotency key** makes the second execution a no-op.

### 9.3 What "at-least-once with idempotency" means for agent side effects

ATQ can only promise **at-least-once** (a task may run 1..N times). Therefore *every external effect the agent produces must be safe to repeat*. Concretely:

- **File edits** — write to a unique output path derived from `idempotency_key` (never "edit in place"); or make the write itself idempotent (content-hash compare before write, or append-only + dedupe-on-read). If the agent must edit a shared file, do it transactionally (write temp → atomic rename) and record "already applied" under the key.
- **API calls** — attach an **idempotency key** (e.g. `Idempotency-Key` / `requestId`) so the provider dedupes on its side; this is exactly Temporal's "use Workflow Run ID + Activity ID as the idempotency key." For providers without idempotency support, gate the call on a "did we already send this key" record stored before/after the call.
- **DB writes** — use `UPSERT`/`INSERT … ON CONFLICT DO NOTHING` keyed on the natural key + `idempotency_key`, never blind `INSERT`.
- **Side-effect log** — the strongest pattern: before performing any side effect, the agent appends `(idempotency_key, effect, status)` to a durable side-effect log; on retry it first checks the log and skips already-applied effects. This is the agent-task analogue of Temporal's event history.

The rule of thumb to carry into the ATQ design: **make the claim atomic, give every claim a lease + heartbeat, bound retries and dead-letter terminal failures, and require every agent action to be keyed and idempotent — because the queue can only ever guarantee at-least-once.**

---

## 10. Source URLs

**Temporal**
- https://temporal.io/blog/idempotency-and-durable-execution
- https://docs.temporal.io/encyclopedia/detecting-activity-failures
- https://docs.temporal.io/encyclopedia/retry-policies
- https://docs.temporal.io/activity-definition

**Celery**
- https://docs.celeryq.dev/en/main/userguide/tasks.html
- https://github.com/celery/celery/issues/5935
- https://stackoverflow.com/questions/62606447/how-can-i-disable-redelivery-of-tasks-in-celery-with-redis
- https://engineering.instawork.com/celery-eta-tasks-demystified-424b836e4e94

**Prefect**
- https://docs.prefect.io/v3/how-to-guides/workflows/retries
- https://docs.prefect.io/v3/advanced/detect-zombie-flows
- https://docs.prefect.io/v3/api-ref/events/flow-run-events

**Argo Workflows**
- https://argo-workflows.readthedocs.io/en/latest/retries/
- https://argo-workflows.readthedocs.io/en/latest/pod-restarts/

**BullMQ**
- https://docs.bullmq.io/guide/workers/stalled-jobs
- https://docs.bullmq.io/guide/retrying-failing-jobs

**AWS SQS**
- https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html
- https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html

**AWS SWF**
- https://docs.aws.amazon.com/amazonswf/latest/developerguide/welcome.html
- https://docs.aws.amazon.com/amazonswf/latest/developerguide/swf-dg-basic.html
