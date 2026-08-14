# Multi-Agent Orchestration Frameworks — Research Findings for the Agent Task Queue (ATQ)

> Research subagent deliverable. Goal: understand what proven multi-agent orchestration frameworks do so we can design our **own lightweight queue-based system** (Hermes agent + AI-KOS SQLite KB). We are **not** adopting a framework.
>
> Scope: MetaGPT, Microsoft AutoGen, CrewAI, LangGraph, OpenAI Agents SDK (formerly Swarm), plus the queue/primitives literature that underlies them.

---

## 1. Executive summary

All five frameworks converge on the same core shape, just materialized differently:

1. **Role specialization** — agents are defined by a *role* (name, goal/prompt, tools, output schema), not by generic "assistant" behavior. Roles exist to bound what an agent may do and what format it must emit.
2. **A coordinator** — some central authority (supervisor, manager, group-chat manager, triage agent) decides *who does what next*. Only in "swarm" variants do agents hand off directly to each other.
3. **A shared medium** — either a blackboard/message pool (MetaGPT), a conversation log (AutoGen), a shared graph state (LangGraph), or a queue. Workers read inputs from and publish outputs to this medium rather than talking 1:1.
4. **Structured hand-offs** — outputs are documents/schemas/typed objects, not free chat. This is what reduces cascading hallucination and "idle chatter" between LLMs.
5. **Termination + verification** — every framework needs explicit stop conditions (max rounds, recursion limit, DONE tokens) and a verification step (guardrails, executable feedback, verifier/evaluator agent).

For a *central queue* specifically, the canonical proven pattern is **a supervised work queue with atomic claim/lease, heartbeat, completion ACK, dependency tracking, and a separate verification stage** — this is the same primitives set as mature background-job systems (Celery, SQS/Sidekiq, FastEndpoints, Azure WebJobs) applied on top of role-based agents.

---

## 2. Framework-by-framework analysis

### 2.1 MetaGPT

**Paper:** Hong et al., "MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework" (ICLR 2024). arXiv:2308.00352. https://arxiv.org/abs/2308.00352

- **(1) Role model.** MetaGPT simulates a software company: Product Manager, Architect, Project Manager, Engineer, QA Engineer. Each agent has a profile = `{name, profile, goal, constraints}` plus role-specific *skills* (e.g. Product Manager can web-search; Engineer can execute code). Core philosophy: **`Code = SOP(Team)`** — encode Standard Operating Procedures (human workflows) into the agents.
- **(2) Task flow.** **Shared message pool (blackboard) + publish–subscribe.** All agents publish structured messages to a global pool and *subscribe* to messages matching their role profile. An agent "activates its action only after receiving all its prerequisite dependencies" — i.e. **dependency-gated activation**, which is precisely the queue-dependency primitive we need. This removes 1:1 chatter: "Any agent can directly retrieve required information from the shared pool, eliminating the need to inquire about other agents and await their responses."
- **(3) Decomposition/planning.** Assembly-line SOP. Requirement → PRD (Product Manager) → System Design / data structures / interface definitions (Architect) → task distribution (Project Manager) → code (Engineer) → tests (QA Engineer). The Project Manager is the explicit *task distributor* — the closest analogue to our deepseek-flash planner.
- **(4) Communication & conflict avoidance.** **Structured outputs instead of dialogue** (documents and diagrams, not "Hi, how are you?"). Subscription filters irrelevant context → addresses "information overload." Conflict is avoided by *single-writer-per-artifact within the assembly line*: only the Architect writes the design, only the Engineer writes code, so two agents never edit the same artifact concurrently.
- **(5) Strengths / failure modes.**
  - Strengths: SoTA Pass@1 on HumanEval (85.9%) and MBPP (87.7%); 100% task completion on its own SoftwareDev benchmark; lowest human-revision cost (0.83 vs ChatDev's 2.5). Ablation shows each added role improves executability and reduces revisions.
  - Failure modes (explicitly discussed in the paper): **cascading hallucination** when naively chaining LLMs; **information overload**; **"infinite loop of message" / "assistant repeated instruction"**; and the "telephone game" (Chinese-whispers) distortion from free-form NL hand-offs. Its answer to all three: SOPs + structured schemas + subscription. Executable-feedback loop is capped at **max 3 retries**.

### 2.2 Microsoft AutoGen

**Paper:** Wu et al., "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation" (arXiv:2308.08155). https://arxiv.org/abs/2308.08155 — Framework docs: https://microsoft.github.io/autogen/

- **(1) Role model.** `ConversableAgent` base class; key subclasses `AssistantAgent` (LLM, no execution) and `UserProxyAgent` (executes code/tools, proxy for human). Roles are *behavioral capabilities*, not fixed job titles — an agent "can differ in what actions they perform after receiving messages." v0.4 moved to an **actor model** (each agent an actor with its own runtime/mailbox), with `AgentChat` as the higher-level API.
- **(2) Task flow.** **Conversation / message passing.** Agents solve tasks by *inter-agent chat*; the `UserProxyAgent.initiate_chat()` starts it. Group chat uses a `GroupChatManager` that "broadcasts messages and decides who the next speaker will be." Agents can be wrapped as tools (`AgentTool`) for manager-style orchestration.
- **(3) Decomposition/planning.** Mostly implicit — driven by LLM function calls and speaker selection. Supports static (predefined topology), dynamic (LLM-chosen next speaker), and **Finite State Machine speaker-transition constraints** (a directed transition matrix of legal/illegal transitions). Also "nested chat" for sub-problems.
- **(4) Communication & conflict avoidance.** Speaker selection methods: `auto` (LLM), `round_robin`, `random`, FSM/state-transition. **Termination rules** (max_round, explicit "DONE"/TERMINATE tokens, satisfaction checks) prevent infinite loops. Conflict avoidance is *turn-based*: only one speaker is active at a time in a given group chat, so there is no concurrent write to shared context — but there is also no file/artifact locking.
- **(5) Strengths / failure modes.**
  - Strengths: extremely flexible conversation patterns; pre-built agents; human-in-the-loop (`human_input_mode`); strong research lineage.
  - Failure modes (widely reported): **high token cost** because the full conversation history is re-sent each turn (needs `MessageHistoryLimiter`/`MessageTokenLimiter`); **infinite loops / runaway chats** without termination; **speaker-selection flakiness**. **Note:** AutoGen is now in **maintenance mode** — Microsoft has redirected development to the successor **Microsoft Agent Framework** (see the maintenance-mode badge on the repo: https://github.com/microsoft/autogen). This is itself a lesson: framework churn is a real risk, which is why ATQ builds on its own stack.

### 2.3 CrewAI

**Docs:** https://docs.crewai.com/ — Source: https://github.com/crewAIInc/crewAI

- **(1) Role model.** `Agent` is defined by **`role`, `goal`, `backstory`** (plus tools, LLM, memory, guardrails). This is the most explicitly "role-based" of the five — the role string is a first-class prompt-injection point. `Task` is defined by `description`, `expected_output`, and an assigned `agent`.
- **(2) Task flow.** **Processes** on a `Crew`: `Process.sequential` (default; tasks run in declared order, each task's output feeds the next) and `Process.hierarchical` (a manager agent allocates tasks among crew members by role/capability). Supports **task delegation** (`allow_delegation=True`) and `planning=True` (the manager makes a plan before execution).
- **(3) Decomposition/planning.** In hierarchical mode the manager LLM (often a strong model like GPT-4) decomposes and delegates; in sequential mode the user pre-declares the decomposition. There is no first-class task *queue* — tasks are a fixed list.
- **(4) Communication & conflict avoidance.** Worker outputs are accumulated into the crew context and passed to subsequent tasks; workers communicate *through* the manager/context, not directly. Conflict avoidance is structural: **one agent is assigned per task**, so no two agents work the same task concurrently.
- **(5) Strengths / failure modes.**
  - Strengths: very fast to prototype; role/goal/backstory prompt pattern is excellent for role-specialization; type-safe `TaskOutput`/`CrewOutput`.
  - Failure modes: **sequential is rigid/linear** (bad for concurrent dependency-free work); **hierarchical depends on a strong manager model** ("designed to leverage advanced models like GPT-4"); token-inefficient for large crews; no built-in lease/heartbeat/timeout machinery — if a task hangs, the crew hangs.

### 2.4 LangGraph (LangChain)

**Docs:** https://langchain-ai.github.io/langgraph/concepts/multi_agent/ — Graph API: https://docs.langchain.com/oss/python/langgraph/graph-api

- **(1) Role model.** LangGraph does **not** impose a role model; it's a **graph/state-machine runtime**. Agents are *nodes* = functions that read `State`, compute, and return a partial `State` update. Roles are whatever prompt/tools you put in a node.
- **(2) Task flow.** **Shared state + message passing (Pregel super-steps).** A `State` (TypedDict/Pydantic) is the single shared data structure; `reducers` define how concurrent updates merge (e.g. `add_messages` appends). Nodes become active when they receive new state on incoming edges and vote to "halt" when idle; graph ends when all nodes are inactive and no messages are in transit. Workers read each other's outputs from the shared state — "they do not talk directly" in the supervisor pattern.
- **(3) Decomposition/planning.** Two canonical multi-agent patterns:
  - **Supervisor** (hierarchical): one supervisor node routes to worker nodes; workers always route *back* to the supervisor. Official package: `langgraph-supervisor`. (Benchmarking by LangChain shows supervisor uses ~50% more tokens than swarm because only the supervisor may respond, but is easier to control.)
  - **Swarm**: every agent can hand off to any other via `create_handoff_tool`; the active agent changes each turn. Official package: `langgraph-swarm`.
  - Plus **hierarchical** (supervisors-of-teams) and **network** topologies.
- **(4) Communication & conflict avoidance.** Concurrency is handled by **reducers** (deterministic merge of parallel writes). **Infinite-loop protection** is built in via `recursion_limit` (raises `GraphRecursionError`) or proactive `RemainingSteps` metadata for graceful in-graph degradation. **Durable execution / checkpointing** (checkpointers + stores) means state persists across crashes — the single most relevant LangGraph feature for an unattended long-running system.
- **(5) Strengths / failure modes.**
  - Strengths: deterministic control flow; persistence/checkpointing (crash recovery, time-travel); explicit concurrency semantics; observability (LangSmith).
  - Failure modes: **higher token cost** (esp. supervisor); more boilerplate; footguns around state schema (private channels still visible when streaming); recursion/loop bugs if you don't set limits. No built-in queue/locking/lease — you'd implement that in the `State`.

### 2.5 OpenAI Agents SDK (formerly Swarm)

**Docs:** https://openai.github.io/openai-agents-python/ — Orchestration: https://openai.github.io/openai-agents-python/multi_agent/ — Guardrails: https://openai.github.io/openai-agents-python/guardrails/

- **(1) Role model.** `Agent` = LLM + `instructions` (system prompt) + `tools` + `handoffs` + `guardrails` + `output_type` (structured output). Roles are prompt-defined; specialization is encouraged ("specialized agents that excel in one task").
- **(2) Task flow.** Two orchestration styles:
  - **Agents-as-tools** (manager): manager owns the conversation, calls specialists via `Agent.as_tool()`, merges results. Good when one agent owns the final answer and you want shared guardrails in one place.
  - **Handoffs**: a triage agent transfers control to a specialist who becomes the *active agent* for the rest of the turn. Good when routing *is* the workflow and the specialist should respond directly.
  - Plus **orchestrating via code** (deterministic chaining, `asyncio.gather` for parallel, `while` loops with an evaluator agent).
- **(3) Decomposition/planning.** Either LLM-driven (open-ended task; the agent plans via tools/handoffs) or code-driven (deterministic, predictable, cheaper). The SDK explicitly recommends mixing them.
- **(4) Communication & conflict avoidance.** **Guardrails** are the standout primitive: *input* guardrails (run on first agent), *output* guardrails (run on last agent), and *tool* guardrails (run on every tool call). Each returns `tripwire_triggered`; a tripwire raises an exception and halts execution. Modes: *parallel* (fast, but agent may have already run) vs *blocking* (runs before the agent; saves cost/side-effects). **Sessions** persist conversation state across runs; **tracing** for observability. Conflict avoidance is again *turn-based ownership* (handoffs = single active agent at a time).
- **(5) Strengths / failure modes.**
  - Strengths: minimal mental model; guardrails + tracing + sessions are production-grade; clean handoff semantics inherited from Swarm.
  - Failure modes: **lock-in** to OpenAI models; handoff loops (agent A↔B ping-pong) need explicit guardrails/limits; guardrails in *parallel* mode can miss side effects; LLM-driven orchestration is non-deterministic and hard to budget.

---

## 3. Cross-cutting synthesis: the canonical pattern for role-based task execution on a central queue

Fusing what the frameworks do with what distributed job systems already prove out, the canonical pattern is:

```
[Planner]  --decomposes mission-->  [Central Queue / Scheduler]  --dispatches-->  [Role Workers (concurrent)]
                                                                        ^                        |
                                                                        |-- claims/heartbeats -- |  (lease on each task)
                                                                        |<------- completion ---- |  (ACK + artifact)
                                                          [Verifier] validates results -> accept / re-queue / block
```

Key ideas worth stealing, mapped to ATQ:

| Concept | Framework origin | Queue-system equivalent |
|---|---|---|
| Role profile (`role/goal/backstory`, instructions, tools, output schema) | CrewAI, MetaGPT, OpenAI SDK | Worker type + prompt + JSON schema |
| Supervisor / manager routing | LangGraph supervisor, CrewAI hierarchical, AutoGen GroupChatManager, OpenAI agents-as-tools | Queue manager (local LLM) that assigns tasks to workers |
| Dependency-gated activation ("activate only after all prerequisites received") | MetaGPT message pool | Task `depends_on` edges; scheduler only releases a task when deps are `done` |
| Structured hand-offs (documents/schemas, not chat) | MetaGPT | Task `data` / artifact fields with a schema; artifacts written to KB/SQLite |
| Shared medium for reading peers' outputs | MetaGPT pool, AutoGen log, LangGraph state | The queue + KB as the shared blackboard |
| Turn-based single-writer ownership | AutoGen speaker selection, OpenAI handoffs | One worker claims one task at a time; single-writer-per-artifact |
| Reducers / deterministic merge of concurrent writes | LangGraph | Merge policies if two workers ever touch the same record |
| Termination / loop guards | AutoGen max_round/DONE, LangGraph recursion_limit | Task timeouts, max-attempts, dead-letter queue |
| Durable state / checkpointing | LangGraph checkpointers | Queue state persisted in SQLite (survives process crashes) |
| Verification | MetaGPT executable feedback, OpenAI guardrails, verifier pattern | Separate testing/verifier agent stage |
| Self-correction with retry cap | MetaGPT (3 retries), Reflexion | max_attempts + backoff |

---

## 4. Design implications for ATQ (the specific questions)

### 4.1 Canonical proven pattern for role-based multi-agent execution with a central queue

The pattern is a **supervised, dependency-aware work queue** — this is the union of (a) the *supervisor/hierarchical* topology that LangGraph, CrewAI, and AutoGen all converge on, and (b) the *lease/claim/ACK* machinery that background-job systems (SQS/Sidekiq/Celery/FastEndpoints/Azure WebJobs) have proven for crash-safe processing. Concrete shape for ATQ:

- **Planner (deepseek-flash)** writes *tasks* into the queue with explicit `depends_on` links (a DAG), each task carrying a role tag, a structured spec, and an expected output schema.
- **Queue manager (local LLM)** is the supervisor: it monitors the queue, and for each *ready* task (deps satisfied, unclaimed) it selects a worker by role and issues a dispatch. It does **not** do the work — it only routes and supervises.
- **Workers (deepseek-pro)** poll or receive dispatches, *atomically claim* a task, execute, publish a structured artifact, and *complete* it. Concurrent workers = parallel execution of independent tasks.
- **Verifier (testing agent)** inspects the artifact against the task spec and either `qa_passed` or re-queues/blocks with feedback.

This mirrors MetaGPT's assembly line *without* hard-coding a linear SOP, and LangGraph's supervisor *without* a runtime framework — the queue + SQLite is the "shared state."

### 4.2 (a) Two agents editing the same file

Frameworks largely *sidestep* this by topology rather than solving it generally: MetaGPT gives each artifact a single writer by SOP; AutoGen/CrewAI/OpenAI give one agent the turn at a time. Where real concurrent agents edit a shared repo, the proven patterns (from the agentic-Git literature) are:

1. **Single-writer-per-artifact (ownership).** Assign each file/artifact to exactly one task at a time. The queue claim *is* the lock: a task that will write `foo.py` can only be claimed by one worker, and no other task targeting `foo.py` is marked ready concurrently. This is the cheapest and most robust approach and should be ATQ's default.
2. **Resource lock table.** A `resource_locks` table (resource_id → holder_task_id, lease_expiry) that workers acquire/release; a worker refuses to start if a required resource is held. This generalizes (1) when artifacts aren't known in advance.
3. **Per-agent worktrees / branches.** Give each concurrent agent its own `git worktree` or branch, then merge serially (integration step). Proven in practice for parallel agent teams; avoids content conflicts entirely at edit time and defers them to a single, sequential merge step (https://www.termdock.com/en/blog/git-worktree-conflicts-ai-agents, https://engineering.intility.com/article/agent-teams-or-how-i-learned-to-stop-worrying-about-merge-conflicts-and-love-git-worktrees).
4. **Deterministic merge reducers.** Where two workers legitimately append to the same structure, use a LangGraph-style reducer (append/merge) rather than last-write-wins.

Recommendation for ATQ: **default to (1) single-writer ownership enforced by the claim; add (2) a lock table for shared artifacts; and adopt (3) worktrees only if we ever run many workers against one repo.** Last-write-wins on a raw shared file is the anti-pattern to avoid.

### 4.3 (b) An agent waiting forever on a stuck dependency

No framework leaves this to chance; they all add explicit bounds. The proven primitives:

1. **Lease / visibility timeout.** When a worker *claims* a task, the claim has an expiry timestamp (lease). If the worker neither completes nor renews before expiry, the task becomes claimable again. This is the crash-recovery backbone of SQS visibility timeout, Sidekiq, and FastEndpoints (`DequeueAfter`) (https://fast-endpoints.com/docs/job-queues, https://learn.microsoft.com/en-us/azure/architecture/best-practices/background-jobs).
2. **Heartbeat.** A worker renews its lease periodically (every N seconds) while working, so long-running tasks don't get falsely re-claimed, but a dead worker's tasks are freed after lease expiry.
3. **Task timeout.** A hard per-task execution cap; on expiry the worker is force-killed, the task marked failed, and it's retried or dead-lettered.
4. **Dead-letter queue + max attempts.** After N failed attempts a task is moved to an isolated DLQ rather than looping forever.
5. **Dependency timeout → blocked/abort.** If a task's dependencies don't reach `done` within a deadline (a dependency's lease expired too many times, or the upstream task failed permanently), the dependent task is marked `blocked` (not left in `waiting` forever) and surfaced to the supervisor for replanning.
6. **Framework-native loop guards as a conceptual check:** LangGraph `recursion_limit`/`RemainingSteps`, AutoGen `max_round`/DONE tokens, MetaGPT's 3-retry cap.

Recommendation for ATQ: implement **lease + heartbeat + timeout + max-attempts + DLQ + `blocked` status with a supervisor escalation path**. That combination is what makes the system "unattended for prolonged periods" — every stuck state has a timer that eventually resolves to a terminal status or a human/LLM replan.

### 4.4 (c) Results verification

The convergent answer is a **dedicated, independent verifier** — not the producing agent checking its own work:

1. **Verifier / generator–verifier loop** ("critic pattern"): a separate agent receives *only* the original requirements + the artifact (no access to the generator's reasoning/chain-of-thought), evaluates against criteria, and returns pass/fail + specific issues; on fail it loops back to the generator (or a fixer) up to a max-iteration cap. Independence is what prevents inheriting the generator's blind spots (https://www.mindstudio.ai/blog/verifier-pattern-multi-agent-systems-independent-review).
2. **Executable feedback** (MetaGPT): where artifacts are code, actually *run* tests — run the unit tests, check for errors, iterate up to 3 retries. This beats "non-executable code review." MetaGPT's QA Engineer also authors test cases.
3. **Guardrails / tripwires** (OpenAI SDK): cheap deterministic checks (input/output/tool) that halt before/after expensive work; blocking mode prevents side effects.
4. **Reflexion / LLM-as-judge**: a critic step that scores output (factual accuracy, completeness) and feeds structured feedback back (https://pub.towardsai.net/how-multi-agent-self-verification-actually-works-and-why-it-changes-everything-for-production-ai-71923df63d01). The "orchestration-level verification" result (VMAO, arXiv:2603.11445) shows an *independent model* judging whether the *collective* result satisfies the original query is an effective coordination signal.
5. **Separation of QA status.** AI-KOS already models this: tasks flow `research → ready → in_progress → qa → qa_passed/blocked` — i.e. a distinct **qa** gate before a task is truly done.

Recommendation for ATQ: keep the **testing agent as a distinct, independent role with its own model**, give it *only* the spec + artifact (never the worker's scratchpad), support both **deterministic checks** (tests, schema validation, file existence, lint) and **LLM judgment**, and cap the verify→fix loop (e.g. 2–3 cycles) before escalating to `blocked`/replan.

---

## 5. Minimal primitive set the systems converge on

Across the frameworks *and* the queue/job literature, the minimal vocabulary is:

**Task lifecycle primitives**
- `enqueue` / `create` — planner writes a task (role, spec, schema, deps, deadline).
- `ready` — dependencies satisfied (MetaGPT's "activate after prerequisites received").
- `claim` (atomic) — one worker takes ownership; compare-and-swap on `status`/`owner`/`lease_until` so two workers can never both win.
- `heartbeat` — renew `lease_until` while working.
- `complete` / `ACK` — worker marks done **and** attaches a structured artifact; only ACK deletes the task.
- `fail` — explicit failure + reason/feedback.
- `lease-expiry` — implicit failure (crash); task returns to `ready` or increments attempts.

**Lifecycle / supervision primitives**
- `timeout` (per-task hard cap) and `max_attempts` (retry cap with backoff).
- `dead-letter` — terminal failure isolation (no infinite retry).
- `blocked` — dependency can never be satisfied; escalate to supervisor/replan (not "waiting forever").
- `depends_on` (DAG) — the planner's decomposition contract.

**Verification primitives**
- `verify` / `qa` — independent agent or deterministic check.
- `accept` → `qa_passed` (terminal) vs `reject` → re-queue/`blocked` with feedback.

**Conflict-avoidance primitives**
- single-writer ownership (claim = lock); optional `resource_locks` table (resource → holder + expiry); per-agent worktree/branch + serial merge; deterministic reducers for shared append-only structures.

**Concrete status set ATQ should adopt** (superset of AI-KOS's current statuses, all persisted in SQLite):

```
pending → ready → claimed → in_progress → qa → qa_passed   (happy path)
              ↘ blocked (dep failed / rejected permanently)
              ↘ failed → retry (attempts < max) → dead-letter (attempts exhausted)
claimed --lease expiry / heartbeat miss--> ready (crash recovery)
```

This is a strict superset of what AI-KOS already models (`research/ready/in_progress/qa/qa_passed/blocked`), so the queue manager only needs to add `claim`/`heartbeat`/`lease_until`/`owner`/`attempts` columns and the atomic claim query.

---

## 6. Key sources

**Frameworks**
- MetaGPT paper (ICLR 2024): https://arxiv.org/abs/2308.00352 (HTML: https://arxiv.org/html/2308.00352v6) — message pool, publish–subscribe, SOP assembly line, executable feedback.
- MetaGPT repo / docs: https://github.com/FoundationAgents/MetaGPT , https://docs.deepwisdom.ai/
- AutoGen paper: https://arxiv.org/abs/2308.08155
- AutoGen multi-agent conversation docs: https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat/
- AutoGen repo (maintenance-mode note): https://github.com/microsoft/autogen
- Microsoft Research — AutoGen/actor-model talk: https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/
- CrewAI docs (sequential): https://docs.crewai.com/v1.15.6/en/learn/sequential-process
- CrewAI docs (hierarchical): https://docs.crewai.com/v1.15.6/en/learn/hierarchical-process
- CrewAI repo: https://github.com/crewAIInc/crewAI
- LangGraph multi-agent concepts: https://langchain-ai.github.io/langgraph/concepts/multi_agent/
- LangGraph Graph API (state/nodes/edges/reducers/recursion limit): https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph supervisor package: https://reference.langchain.com/python/langgraph-supervisor
- LangGraph swarm package: https://reference.langchain.com/python/langgraph-swarm
- LangChain multi-agent supervisor blog: https://blog.langchain.dev/langgraph-multi-agent-workflows/
- LangChain benchmarking (supervisor vs swarm): https://www.langchain.com/blog/benchmarking-multi-agent-architectures
- OpenAI Agents SDK orchestration: https://openai.github.io/openai-agents-python/multi_agent/
- OpenAI Agents SDK guardrails: https://openai.github.io/openai-agents-python/guardrails/
- OpenAI Agents SDK home: https://openai.github.io/openai-agents-python/

**Queue / primitives / conflict / verification**
- Background tasks, queues, workers guide (visibility timeout, ACK, DLQ, heartbeat): https://medium.com/@moizsardar056/background-tasks-queues-and-workers-the-complete-guide-for-backend-developers-a69699c2fb1a
- FastEndpoints job queues (lease/claim/DequeueAfter crash recovery): https://fast-endpoints.com/docs/job-queues
- Azure background-jobs best practices (conflicts, partitioning, recovery): https://learn.microsoft.com/en-us/azure/architecture/best-practices/background-jobs
- Git worktree conflicts with multiple AI agents: https://www.termdock.com/en/blog/git-worktree-conflicts-ai-agents
- Agent teams + git worktrees: https://engineering.intility.com/article/agent-teams-or-how-i-learned-to-stop-worrying-about-merge-conflicts-and-love-git-worktrees
- Verifier pattern in multi-agent systems: https://www.mindstudio.ai/blog/verifier-pattern-multi-agent-systems-independent-review
- Multi-agent self-verification (LLM-as-judge, Reflexion, generator–verifier loop): https://pub.towardsai.net/how-multi-agent-self-verification-actually-works-and-why-it-changes-everything-for-production-ai-71923df63d01
- Verified Multi-Agent Orchestration (Plan-Execute-Verify-Replan), arXiv:2603.11445: https://arxiv.org/html/2603.11445v1

---

## 7. Bottom line for ATQ

1. Don't re-invent the wheel — **the "central queue + supervisor + role workers + independent verifier" topology is exactly what LangGraph-supervisor, CrewAI-hierarchical, and AutoGen-GroupChat already converge on.** Our value-add is that we're implementing it as a thin, persistent, SQLite-backed queue rather than pulling in a heavyweight framework (which is the right call given AutoGen's maintenance-mode churn and the LLM-lock-in of the OpenAI SDK).
2. **The queue is the shared blackboard.** Task `data` + artifacts in AI-KOS/SQLite replace MetaGPT's message pool and LangGraph's `State`. Structured schemas on every hand-off (MetaGPT's key lesson) keep "idle chatter" and cascading hallucination out.
3. **The five primitives that matter for unattended operation are: atomic `claim`, `heartbeat` (lease renewal), `lease_until` (visibility timeout), `complete` (ACK + artifact), and `qa_passed`/`blocked` (verification gate).** Add `attempts`, `max_attempts`, `timeout`, and a dead-letter bucket. With these, every stuck state resolves to a terminal status or a replan — no agent ever waits forever.
4. **Conflict avoidance = single-writer ownership via the claim**, backed by a `resource_locks` table; use per-agent worktrees only if many workers share one repo.
5. **Verification = an independent testing agent** (its own model, spec + artifact only, no worker scratchpad), combining deterministic checks with LLM judgment, with a capped verify→fix loop before escalation.
