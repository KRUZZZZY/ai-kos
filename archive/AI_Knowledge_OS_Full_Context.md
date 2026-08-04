# AI Knowledge Operating System — Full Accumulated Context

> This document consolidates all design decisions, critiques, improvements, and resolved problems from three separate planning conversations. It is intended as the complete context base for writing a final technical specification.

---

## 1. Project Identity

This system is not a chatbot, a RAG pipeline, or an Obsidian vault. It is a **personal cognitive operating system** built around:

- Local AI models
- Persistent, structured knowledge
- Scheduled knowledge consolidation
- AI-readable schemas with human-readable articles
- Multi-agent governance with minimal human interruption
- Long-term self-improvement and meta-learning

The AI does not merely answer questions. It develops, maintains, organises, and retrieves knowledge. Knowledge is external to the model and persists independently of any conversation.

---

## 2. Hardware and Software Stack

### Hardware Target
- Ubuntu Linux
- RTX 5070 Ti
- 16 GB RAM minimum, 32 GB recommended
- NVMe SSD storage

### Model Layer
- DeepSeek, Qwen, Llama (and additional local models as required)
- Served through **Ollama** — acts as model manager, inference engine, and local API server
- Ollama is not the user interface

### Interface Options
- Open WebUI
- Custom Hermes interface
- Obsidian plugins
- Dedicated dashboard

---

## 3. Core Architecture: The Cognitive Skins Model

### Original Design (Superseded)
Hermes was conceived as a single unified reasoning personality sitting above the knowledge system.

### Revised Design (Adopted)
Hermes is no longer "the AI." The knowledge system is the persistent core. Cognitive skins are temporary behavioural overlays applied to whichever model is routed to a task.

**The hierarchy is now:**
```
Knowledge System (persistent)
    ↓
Cognitive Skin (temporary behavioural overlay)
    ↓
Model (execution layer)
```

### Defined Skins
| Skin | Purpose | Reasoning Style |
|---|---|---|
| Hermes | Default conversational persona | General reasoning, balanced |
| Research | Sceptical, citation-aware | Questions claims, demands evidence |
| Coding | Terse, precision-focused | Avoids prose, values correctness |
| Project Manager | Action-oriented | Identifies blockers, next steps |
| Critic | Adversarial reviewer | Challenges proposals |
| Consolidator | Knowledge pipeline worker | Summarises, merges, structures |

All skins share:
- The same vault
- The same retrieval pipeline
- The same memories
- The same concept graph

Only their system prompts, reasoning strategies, retrieval preferences, and output styles differ.

**Skin selection:** Manual (user picks) or automatic (routing layer detects from query type). This must be specified in the routing layer design.

---

## 4. Memory Architecture

### Five-Layer Pipeline

```
Raw Information (inbox/)
    ↓
Episodic Store (backlog/ → episodes/)
    ↓
Consolidation (nightly + weekly jobs)
    ↓
Knowledge Articles (knowledge/)
    ↓
Concepts and Summaries (concepts/, summaries/)
    ↓
Indexes (indexes/)
    ↓
Retrieval
    ↓
Cognitive Skin + Model
```

### Memory Type Taxonomy
| Type | Location | Examples |
|---|---|---|
| Episodic | backlog/, episodes/ | Debug sessions, research sessions, meetings |
| Semantic | knowledge/ | DCGs, Parsing, Feature Structures |
| Procedural | templates/ | Research template, project template |
| Executive | indexes/, summaries/ | Concept maps, domain summaries |
| Social | Skin definitions | Persona system prompts |
| Operational | Query logs | Retrieval history, failure logs |
| Structural | Concept graph | Obsidian wikilinks + metadata |

### Clarification: Backlog vs Episodes
- **Backlog** = processed but unconsolidated episodic material waiting for the nightly job
- **Episodes** = episodic records that have been processed and stored for longer-term reference
- These are distinct folders; the backlog feeds into episodes and/or knowledge depending on consolidation outcome

---

## 5. Folder Structure

```
vault/
├── inbox/          # Unprocessed raw material
├── backlog/        # Processed, awaiting consolidation
├── episodes/       # Episodic memory records
├── knowledge/      # Semantic knowledge articles
│   └── Parsing/
│       ├── DCGs.md
│       ├── Feature_Structures.md
│       └── Unification.md
├── concepts/       # High-level concept abstractions
├── summaries/      # Multi-level summaries
├── indexes/        # Category and domain indexes
├── templates/      # Article templates (procedural memory)
└── archive/        # Processed or obsolete material
```

---

## 6. Ingestion Architecture

### Resolved: Ingestion Is Automated

Material enters the system through defined ingestion agents, not manual copying. The inbox is populated automatically.

### Ingestion Sources and Methods
| Source | Method |
|---|---|
| Web search | SearXNG (self-hosted, no rate limits, structured output) |
| Web pages (on-demand) | Browser MCP server or browser extension |
| Local files (PDFs, notes, exports) | Folder-watch script |
| Chat sessions | Export pipeline |
| Hermes observations | Write-back queue (separate from main inbox) |

**Recommended primary approach:** SearXNG for automated web ingestion + folder-watch for local files + browser MCP for on-demand capture. These decouple ingestion from the chat interface.

Open WebUI's built-in search tools are not recommended for automated ingestion — they are tied to the chat UI and lack a clean programmatic pathway.

### Inbox Triage: Automatic Priority Scoring

Priority is assigned automatically at ingestion time by a **small fast model**, not manually. The scoring rubric:

1. **Recency** — how recent is the material?
2. **Project relevance** — does it match active project topics? (detected from recent query log activity)
3. **Source type** — own notes score higher than random web articles
4. **Length/density** — information density as a proxy for value

The priority score is written to inbox item metadata immediately. No human intervention at this stage. Misclassified items surface naturally through the pipeline or decay via TTL. The cost of a misclassification is low.

**Hermes write-back candidates** are a separate queue and are not scored by the same rubric.

---

## 7. Dual-Layer Article Structure

Every knowledge article has two layers:

### AI Layer (YAML Frontmatter)
```yaml
type: concept
template: programming_concept
importance: high
confidence: 0.82
stability: stable
dependencies: [Unification, Parsing]
related: [Feature_Structures, DCGs]
keywords: [grammar, parsing, definite clause]
priority: 2
updated: 2025-01-15
review_date: 2025-04-15
read_order: [summary, examples, limitations]
retrieval_tags: [nlp, prolog, grammar]
summary: "DCGs extend Prolog syntax for grammar rules..."
template_version: v2
provenance: [backlog/session_2025-01-10.md]
ai_notes: ""
```

### Human Layer (Markdown Body)
Contains: explanations, examples, diagrams, references, code, discussions. Optimised for people. No human should need to read or understand the metadata.

### Template Versioning (New Requirement)
Every article must carry a `template_version` field. When templates evolve, the consolidation job must:
1. Detect articles on old template versions
2. Flag them for migration
3. Apply the new schema
4. Update the `template_version` field

---

## 8. Article Templates (Procedural Memory)

Templates are the AI's procedural knowledge. Instead of re-reading article structures repeatedly, the routing layer knows each template's section layout.

### Defined Templates

**Concept Template:** Definition → Dependencies → Examples → Applications → Limitations → References → AI Notes

**Programming Concept Template:** Definition → Dependencies → Syntax → Examples → Applications → Limitations → Summary

**Project Template:** Goal → Current Status → Decisions → Problems → Next Actions → Dependencies

**Research Template:** Summary → Claims → Evidence → Weaknesses → Connections → Open Questions

### Template Evolution (Weekly Job)
1. Scan all articles
2. Detect repeated structures across articles
3. Suggest new or merged templates
4. Migrate articles to new template version
5. Compress knowledge

Example: twenty programming articles converge → `Programming_Component` template extracted.

---

## 9. Context Rot Prevention

Each article has:
- **Maximum size** — enforced by consolidation job
- **Soft cap** — 10 knowledge sections per article
- **Scope limit** — one concept, idea, or process per section

Large topics are split into multiple articles under a shared folder (e.g., `Parsing/DCGs.md`, `Parsing/Unification.md`).

---

## 10. Multi-Level Summarisation

```
Section Summary     → summarises one section
Article Summary     → summarises the whole article
Category Summary    → summarises related articles
Domain Summary      → summarises an entire subject area
```

This allows a skin to descend through layers of detail efficiently, loading only what is needed. Hermes rarely needs entire articles — it starts at summaries.

---

## 11. Retrieval Strategy

Retrieval is hierarchical and now multi-modal. The full retrieval hierarchy:

```
Summary retrieval (cheapest)
    ↓
Metadata retrieval (structured query)
    ↓
Vector retrieval (semantic similarity)
    ↓
Graph traversal (lateral / related concept discovery)
    ↓
Source retrieval (raw backlog / episode material)
```

### Lateral Retrieval (Resolved Gap)
The original design was top-down only (category → article → section). The concept graph enables lateral retrieval: when a query doesn't match a known domain, graph traversal surfaces related articles via wikilinks. This addresses unknown unknowns — knowledge that exists but the skin doesn't know to search for.

---

## 12. Concept Graph

### Implementation Decision (Resolved)
The concept graph is implemented via **Obsidian wikilinks**, not a separate graph database. Every `[[wikilink]]` in an article becomes an edge in the graph. Obsidian renders this natively.

### Dual Representation (Must Be Kept in Sync)
- **Metadata field** (`related:`, `depends_on:`) — AI-readable for fast programmatic access
- **Wikilinks in body** (`[[DCGs]]`, `[[Parsing]]`) — picked up by Obsidian's graph

The consolidation job must keep both representations synchronised. If one is updated, the other must be updated in the same pass.

### Graph Capabilities Enabled
- Orphan detection — articles with no incoming links
- Hub detection — high-connectivity concept nodes
- Lateral retrieval — traversal from a known concept to unknown related concepts
- Uncertainty propagation — if article A depends on article B, and B's confidence drops, A is flagged for review
- Queried programmatically via Obsidian local REST API or direct markdown parsing

---

## 13. Confidence and Staleness Model

### Confidence (Resolved: Pragmatic Float Model)
- Confidence stored as float 0.0–1.0
- **+0.05** per additional supporting source
- **−0.15** per direct contradiction
- **×0.95** per missed review window (staleness decay multiplier)
- Decay rate varies by stability class:
  - `volatile` — fast decay (e.g., library APIs, current software versions)
  - `stable` — slow decay (e.g., theoretical concepts, mathematical definitions)
- Threshold for staleness flag: to be defined empirically once running

### Confidence Inheritance on Creation
When a new article is created from backlog material, its initial confidence is derived from the provenance sources, not set arbitrarily. The inheritance rule must be explicitly defined.

### Decay Reset on Access
When an article is read or retrieved, its staleness decay is reset or slowed. Access is implicit validation. This is not in the original spec and must be added.

### Uncertainty Propagation
If article A `depends_on` article B, and B's confidence falls below threshold, A is automatically flagged for review. The concept graph provides the dependency structure to implement this.

---

## 14. Consolidation Jobs

### Nightly Consolidation (Incremental)
1. Read backlog
2. Detect topics
3. Cluster related information
4. Merge duplicates (see conflict resolution policy below)
5. Update knowledge articles
6. Generate/update summaries
7. Update metadata (including confidence, review dates)
8. Update vector database
9. Generate/update indexes
10. Archive processed material
11. Sync wikilinks with metadata
12. Write to job log (idempotency checkpoint)

### Weekly Consolidation (Structural)
1. Review templates — detect repeated structures, suggest new schemas
2. Merge related concepts
3. Update concept graph relationships
4. Identify obsolete knowledge
5. Run confidence decay pass
6. Detect orphaned articles
7. Run meta-learning pass (see Section 19)
8. Generate knowledge health dashboard update

### Idempotency and Failure Recovery (Resolved Gap)
Partial outputs are written **incrementally** during consolidation. A job crash does not corrupt completed steps. On restart, the job reads the job log and resumes from the last successful checkpoint. The routing layer logs which fallback model was used so chronic failures are detectable.

---

## 15. Conflict Resolution Policy (Resolved Gap)

When two backlog entries contradict each other, the following policy applies:

1. Both entries are flagged as conflicting in metadata
2. The Critic skin evaluates each against known provenance and confidence
3. If one clearly supersedes (newer, higher-confidence source), the newer wins and the older is archived with a conflict note
4. If both have comparable weight, a conflict stub is created in the article with both positions noted and confidence reduced
5. Unresolvable conflicts are escalated to human review (see governance section)

---

## 16. Vector Database

### Implementation Options Compared
| Option | Pros | Cons |
|---|---|---|
| Chroma | Simplest, Python-native, zero infrastructure | Limited metadata filtering |
| Qdrant | Payload filtering + vector search, Docker | More setup |
| pgvector | Unifies vector + structured metadata in one DB | Complex setup |
| Weaviate | Object model matches dual-layer articles | Heavy local resource use |
| SQLite + sqlite-vec | Zero infrastructure, single file | Limited scale |

**Current recommendation:** Start with **SQLite + sqlite-vec** for simplicity; migrate to **Qdrant** when metadata filtering needs grow.

### Embedding Model (Critical Decision)
The embedding model matters more than the database choice.
- Use a **local embedding model via Ollama** (e.g., `nomic-embed-text`) to avoid API drift
- **Pin the embedding model and version explicitly**
- If the embedding model is ever changed, all embeddings must be regenerated

What the vector database stores: chunked article sections and/or summaries, with metadata payload for filtered retrieval (template type, confidence score, stability class).

---

## 17. Model Routing Layer

### Routing Table
| Task | Skin | Model Tier |
|---|---|---|
| Web search / retrieval | Research | Small (fast) |
| Inbox scoring | — | Small (fast) |
| Summarisation | Consolidator | Medium |
| Article generation | Consolidator | Medium |
| Coding tasks | Coding | Strong |
| Debate / critique | Critic | Strong |
| Conflict resolution | Critic | Strong |
| Synthesis / reasoning | Hermes | Best available |
| Dual-agent review | Proposer + Critic | Medium |

### Failure Handling (Resolved)
- Each task type has a **primary model** and 1–2 **fallbacks**, ranked by capability
- On primary failure or timeout: drop to next fallback
- If all fallbacks fail: write to **retry queue** with error flag; retry at next consolidation window
- Partial consolidation outputs are checkpointed so failure mid-job doesn't lose completed steps
- Routing layer **logs which fallback was used** — chronic failures become visible

---

## 18. Governance: Dual-Agent Review

### Revised Model (Human Approval Minimised)

**Old model:** AI proposes → Human approves (every change)

**New model:**
```
Proposer AI (evaluates change)
    ↓
Critic AI (independently evaluates same change)
    ↓
Agreement Check
    ↓
Auto-commit (if agreement within threshold)
    OR
Human review queue (if disagreement / high-stakes)
```

Two instances of the same model, different system prompts (Proposer skin vs Critic skin), evaluate independently. A third pass compares outputs.

### What Gets Auto-Committed
- Duplicate merges
- Confidence updates
- Article updates from non-contradicting new evidence
- Wikilink sync
- Summary regeneration

### What Still Requires Human Approval
- Permanent deletion
- Template migrations
- Major structural reorganisation
- Unresolvable contradictions flagged by dual-agent disagreement

This reduces the human approval queue to genuine ambiguities and destructive/irreversible operations only.

---

## 19. Knowledge Health Dashboard

Built from existing metadata. Makes maintenance active rather than invisible.

### Metrics
- Articles by last review date
- Confidence score distribution across the vault
- Concept graph connectivity (orphans, hubs, isolated clusters)
- High-priority stale articles
- Skin usage frequency
- Model fallback frequency (indicates model reliability issues)
- Ingestion source quality (which sources produce high-confidence articles)
- Disagreement rate between Proposer and Critic agents
- Confidence decay statistics
- Template convergence rate (how often articles cluster into new templates)
- Query log: which articles are retrieved, which queries fail to find answers

---

## 20. Meta-Learning (Weekly)

The system evaluates its own operation weekly:

- What templates are being used vs. ignored?
- What retrievals consistently fail to find answers?
- What skins produce the most useful outputs?
- What concepts lack coverage (gap articles)?
- What articles are never retrieved?
- Where do Proposer/Critic disagreements cluster?

Results feed back into template evolution, retrieval tuning, and skin prompt refinement. The system learns how it should operate.

---

## 21. Knowledge Gap Articles

Beyond logging failed queries, the system maintains explicit **gap stubs** — articles that represent things the system knows it does not know. These:
- Are flagged for future research sessions
- Give any skin a way to say "I know I'm missing something here" rather than silently returning weak results
- Are created automatically when a query fails to find a relevant article

---

## 22. Session Context Layer

Within a single working session, a lightweight **session context scratchpad** holds:
- Things discussed in the current conversation not yet in the inbox
- Temporary conclusions, working hypotheses, in-progress decisions

This is **distinct from the inbox** — it is not persisted to disk automatically and does not go through the full pipeline. It influences immediate answers within the session. At session end, valuable material can be exported to the inbox as a write-back candidate.

---

## 23. Provenance Tracking

Every claim in a knowledge article traces back to at least one source in the backlog or inbox. Provenance is stored in the `provenance:` metadata field.

Provenance matters for:
- Knowing why a belief is held
- Updating beliefs when sources are found to be wrong
- Confidence inheritance when creating new articles
- Conflict resolution (provenance quality informs which claim wins)

---

## 24. Archive Policy (Resolved Gap)

The archive is not a black hole. Two distinct archive types:

| Type | Reason | Retrieval |
|---|---|---|
| Processed archive | Item was consolidated into a knowledge article | Accessible via provenance lookup |
| Obsolete archive | Knowledge is superseded or no longer relevant | Accessible but flagged; no active retrieval |

Archived items retain their metadata. The archive has no expiry by default but can be cleaned via explicit human action on the dashboard.

---

## 25. Export and Portability

The knowledge base must be portable. All knowledge articles are stored as **plain markdown with YAML frontmatter**. This is a hard requirement, not an assumption. If Obsidian, Ollama, or the local stack become unavailable, the vault remains readable and migratable.

---

## 26. Bootstrapping Plan (Resolved Gap)

The system was only described in steady state. The bootstrapping sequence:

1. **Week 0:** Set up folder structure, Ollama, embedding model, vector DB
2. **Week 0:** Define initial templates (concept, programming concept, project, research)
3. **Week 0–1:** Bulk ingestion pass over existing notes, exports, and saved materials
4. **Week 1:** First nightly consolidation run on bulk-ingested backlog
5. **Week 1–2:** Manually review first wave of generated articles; tune confidence arithmetic
6. **Week 2+:** System enters steady-state operation; nightly and weekly jobs run automatically

---

## 27. Open Questions / Decisions Not Yet Made

The following are flagged for the technical specification stage:

- **Disagreement threshold** for dual-agent review — what percentage divergence triggers human escalation?
- **Confidence inheritance rule** — exact formula when creating an article from multi-source backlog material
- **Decay reset formula** — how much does retrieval slow staleness decay (full reset vs. partial)?
- **Gap article threshold** — how many failed queries on a topic before a gap stub is created?
- **Session context export policy** — automatic or manual export to inbox at session end?
- **Skin selection heuristics** — exact logic for automatic skin detection from query type
- **Graph query interface** — Obsidian REST API vs. direct markdown parse for graph traversal

---

## 28. What Comes Next: Technical Specification

The conceptual design is complete. The next document is the **AI Knowledge Operating System v1.0 Technical Specification**, covering:

- Service architecture diagram
- Directory layouts (with file naming conventions)
- YAML schema definitions for every metadata field
- Article template examples (full)
- Confidence arithmetic formulas
- Consolidation algorithms (step-by-step pseudocode)
- Retrieval algorithms
- Agent responsibilities and message formats
- Nightly and weekly job specifications
- Model routing table (full)
- Skin system prompt structure
- Vector database schema
- Dual-agent review protocol
- Query log format
- Dashboard data sources
- API design between skins/routing layer and the vault
- Docker/deployment architecture
