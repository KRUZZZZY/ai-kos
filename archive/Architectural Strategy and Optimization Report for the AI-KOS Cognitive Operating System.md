# **Architectural Strategy and Optimization Report for the AI-KOS Cognitive Operating System**

## **Comparative Architectural Analysis of AI-KOS and Semi-Existing Baselines**

The development of a persistent cognitive operating system requires a careful balance between human auditability, structural scalability, and execution speed. A comparative analysis of the AI-KOS v0.1 specification and the semi-existing database-backed baseline reveals significant convergence alongside distinct design paths.1  
Both architectures trace their conceptual lineage back to the Andrej Karpathy LLM Wiki and Open Knowledge Format (OKF) patterns, independently selecting a multi-stage hybrid retrieval engine.1 This hybrid engine combines dense vector representations with sparse, lexical search, fused using the Reciprocal Rank Fusion (RRF) algorithm.1 This common choice is validated by empirical data showing that hybrid RRF retrieval consistently outperforms single-method retrieval, particularly on datasets with mixed text and tabular content.3  
Despite this shared core, the two systems diverge in their storage formats, update mechanisms, and scaling assumptions.1

                 ┌──────────────────────────────────────────┐  
                 │       Ingestion & Triage Pipeline        │  
                 │   (Docling Parsing & Schema Validation)   │  
                 └────────────────────┬─────────────────────┘  
                                      │  
                                      ▼  
                 ┌──────────────────────────────────────────┐  
                 │    Redis Task Queue (queue:consolidate)  │  
                 └────────────────────┬─────────────────────┘  
                                      │  
                                      ▼  
                 ┌──────────────────────────────────────────┐  
                 │    Consolidation Agent (OKF Format)      │  
                 └────────────────────┬─────────────────────┘  
                                      │  
                                      ▼  
                 ┌──────────────────────────────────────────┐  
                 │    Hierarchical Split (Parent-Child)     │  
                 └──────────┬────────────────────┬──────────┘  
                            │                    │  
                            ▼                    ▼  
             ┌────────────────────────┐┌────────────────────────┐  
             │   Dense/Sparse Child   ││     Parent Document    │  
             │   Vectors in Qdrant    ││   Storage (Postgres)   │  
             └────────────────────────┘└────────────────────────┘

The AI-KOS system utilizes an Open Knowledge Format (OKF) v0.1 layout consisting of portable Markdown files containing YAML frontmatter.1 This design emphasizes human auditability and seamless version control via Git.1  
Conversely, the baseline system uses a database-backed storage engine, prioritizing concurrent transaction safety and fast, programmatic indexing at the expense of manual inspectability.1  
To illustrate these trade-offs, a structural comparison of the core layers of both systems is detailed below.

| System Component | AI-KOS Specification (v0.1) | Semi-Existing Database Baseline |
| :---- | :---- | :---- |
| **Storage Architecture** | File-first, Git-native directory (knowledge/, episodes/, backlog/).1 | Relational or NoSQL database-backed storage engine.1 |
| **Retrieval Engine** | Hybrid Dense \+ Sparse indexing natively hosted in Qdrant via FastEmbed.1 | Hybrid Dense \+ Sparse (BM25) fused via Reciprocal Rank Fusion (RRF).1 |
| **Auditability & Portability** | High; standard text editor diffs, portable markdown files with YAML frontmatter.1 | Low; closed database records requiring custom visualization tools.1 |
| **Concurrency Control** | High risk of file-system write conflicts and platform-dependent file-locking issues.4 | Automated via Multi-Version Concurrency Control (MVCC) and ACID transaction logs.4 |
| **Scaling Characteristics** | Linear degradation on large corpora; context bloat managed via tight retrieval.1 | Logarithmic scale-up via indexed queries, B-trees, and database-level optimization.4 |
| **Execution Speed** | Moderate; latency introduced by multi-agent validation loops.1 | High; optimized database writes and fast programmatic consolidation.1 |

The AI-KOS system features an advanced epistemic model that outpaces the simple Time-to-Live (TTL) and access-count stale detection used in the baseline system.1 AI-KOS introduces per-article confidence scores, dynamic stability classes, temporal decay metrics, and "gap" articles to track known unknowns.1  
This systematic tracking of uncertainty prevents the silent quality loss that commonly affects production RAG systems.5 Without proactive decay and validation pipelines, standard retrieval systems can lose ![][image1] to ![][image2] points of accuracy within a year of deployment due to stale context and informational drift.5  
Additionally, the AI-KOS "snippet-first" retrieval architecture provides a highly efficient way to reference long-form documents.1 By loading only the relevant child chunk at retrieval time rather than the entire parent file, AI-KOS keeps the generative model's context window clean.1  
This contrasts with the baseline system's approach of physically splitting short notes from long documents, which introduces structural fragmentation and complicates long-term maintenance.1

## **Optimizing the Reranking Tier: Latency, Accuracy, and Compute Trade-Offs**

A key design point in the comparative feedback is whether to include a second-stage cross-encoder reranker.1 The baseline developers opted to bypass this stage, finding that Reciprocal Rank Fusion (RRF) alone accounted for the majority of their precision gains (improving retrieval relevance from ![][image3] to ![][image4]), while the cross-encoder added latency and cost for marginal return.1  
While this trade-off is often acceptable for basic search tasks, multi-agent reasoning, complex query sets, and highly structured datasets require a more nuanced approach.3

### **The Limits of Independent Encoding**

Traditional bi-encoder models evaluate queries and documents independently, projecting them into a shared vector space where similarity is measured via cosine distance.7 While computationally fast, this approach prevents the model from capturing fine-grained token-level interactions between the query and candidate documents.6  
Bi-encoders alone typically achieve only ![][image5] to ![][image6] accuracy on complex, domain-specific, or entity-dense queries, often returning semantically similar but incorrect documents.7 This is because the similarity calculation occurs in vector space without the model directly comparing the two blocks of text.7  
A cross-encoder reranker addresses this limitation by processing the query and candidate document simultaneously through joint self-attention layers.6 This unified processing allows the model to evaluate exact structural matches, negative qualifiers, and complex relationships.6  
Adding a cross-encoder stage to a hybrid RRF pipeline typically yields a ![][image7] to ![][image8] NDCG@10 point improvement across standard MTEB and BEIR benchmarks.6 In specialized financial and tabular evaluations, adding a cross-encoder (such as Cohere Rerank v4.0 Pro) yielded a ![][image9] percentage point increase in MRR@3 and ![][image10] in Recall@5 over unreranked hybrid retrieval.3

### **Operational Performance of Modern Reranking Architectures**

To assist with system integration, the comparative performance, storage requirements, and optimal candidate pool sizes (![][image11]) for the leading 2026 reranking architectures are outlined below.

| Reranking Model | Latency per Query (K=100) | Storage Overhead | Retrieval Accuracy Lift | License & Deployment Cost |
| :---- | :---- | :---- | :---- | :---- |
| **RRF Only (No Rerank)** | **![][image12]** 6 | None | Baseline (![][image13] relevance) 7 | Open-source; zero runtime cost.5 |
| **MiniLM-L-6-v2** | **![][image14]** 7 | None | Moderate (![][image15] NDCG) 6 | Open-source; highly efficient on CPU.7 |
| **BGE-Reranker-v2-m3** | **![][image16]** 6 | None | High (![][image17] NDCG) 6 | Open-source; high compute requirement.6 |
| **ColBERT (Late Interaction)** | **![][image18]** 6 | ![][image19] bi-encoder (![][image20]/token) 6 | High (![][image21] NDCG) 6 | Open-source; requires substantial RAM.6 |
| **Gemma-2-9B-Reranker** | **![][image22]** 6 | None | Maximum (![][image23] NDCG) 6 | Open-weights; requires dedicated GPU.6 |
| **Cohere Rerank v4.0 Pro** | **![][image24]** 7 | None | High (![][image25] accuracy) 7 | Proprietary API; ![][image26] per 1K tokens.7 |

### **Latency Mitigation for CPU-Bound Environments**

For local, CPU-only deployments of AI-KOS, executing deep cross-encoders over a standard candidate pool of $K=100$ introduces significant latency.6 Under these hardware constraints, a tiered retrieval strategy is recommended:

1. **Reduce Candidate Pool Size (![][image11]):** Restrict the initial hybrid RRF retrieval to a smaller candidate set ($K=20$ to $K=30$) rather than the standard $K=100$.9  
2. **Deploy a Lightweight Reranker:** Use an optimized model like ms-marco-MiniLM-L-6-v2 (model size ![][image27]), which processes smaller text blocks with low latency on standard CPU threads.7  
3. **Implement Chunk-Level Caching:** Cache both dense embedding vectors and final reranker scores at the chunk level to bypass model execution for identical queries.9

This configuration provides a strong balance between speed and precision, delivering high retrieval quality without saturating CPU threads.9

## **Multi-Tenant Scaling and Shared-State Management**

The AI-KOS v0.1 specification was designed primarily as a single-tenant system, with security labels managed as configurations rather than strict authorization barriers.1 While this model is effective for individual users, transitioning the system to support multiple collaborative agents or multiple concurrent users exposes several architectural limitations in a pure file-first design.1

### **Bottlenecks of File-Based Concurrent Access**

As agent numbers and write frequencies scale, a markdown-based storage architecture faces five primary limitations 4:

1. **Concurrent Write Failures:** Simultaneous write attempts to a single Markdown file or index can result in silent data loss or file corruption.4 Implementing file-locking mechanisms helps preserve file integrity, but introduces platform-dependent complexity, potential deadlock states, and write latency.4  
2. **Lack of ACID Guarantees:** Git commits provide version tracking, but do not offer the real-time atomicity, consistency, isolation, and durability (ACID) needed to safely coordinate shared state across multiple autonomous agents.4  
3. **Linear Performance Degradation:** As the file tree grows, query operations that require scanning directory files (such as global keyword matches or relationship updates) degrade linearly in performance (![][image28]), unlike indexed database lookups (![][image29]).4  
4. **Complex Access Control:** Enforcing row-level or document-level security across a directory of raw markdown files requires building a custom permission and authorization layer from scratch.4  
5. **Polyglot Ingest Complexity:** Managing separate storage engines for semantic vectors, relational histories, and raw markdown files increases system complexity, creating multiple potential points of failure and backup targets.4

To address these limitations without completely rewriting the core architecture, AI-KOS can incorporate a converged database engine, such as SQLite or LadybugDB, to handle transient state, transaction logs, and real-time concurrent writes.4 This allows the system to maintain ACID guarantees for active operations while periodically exporting consolidated state back to the Git-native OKF Markdown directory.1

### **Implementing Isolated Runtimes and Multi-Tenant Models**

To scale the execution environment of AI-KOS, the system can utilize a multi-tenant agent runtime model.10 Rather than provisioning dedicated virtual machines per tenant—which introduces high cost and latency—the runtime should deploy lightweight, session-isolated microVMs.10  
Each active microVM maintains its own isolated, ephemeral filesystem, preserving state across multi-step agent actions while preventing cross-session data leakage.10

┌────────────────────────────────────────────────────────┐  
│               SaaS API Gateway & Router                │  
│ (Attaches Tenant ID, Regional Config, & Feature Flags) │  
└───────────────────────────┬────────────────────────────┘  
                            │  
                            ▼  
┌────────────────────────────────────────────────────────┐  
│            Isolated MicroVM Runtime Session            │  
│  (Ephemeral Filesystem, Local Tools, and Memory Port)  │  
└───────────────────────────┬────────────────────────────┘  
                            │  
                            ▼  
┌────────────────────────────────────────────────────────┐  
│              Hub-and-Spoke Storage Model               │  
├────────────────────────────────────────────────────────┤  
│ ──► Global Master Stack (Shared Schemas & Templates)   │  
│ ──► Tenant Child Stack (Local Markdown & Configs)       │  
└────────────────────────────────────────────────────────┘

Tenant context is propagated through the service registry (Ports 8001–8012) via custom HTTP headers.1 When a request is processed, the gateway appends headers containing the tenant identifier, regional preferences, and security permissions to the payload.10  
The local services inspect these headers to restrict search queries, load only the appropriate environment variables, and block unauthorized access.10  
To prevent structural drift across tenants, a hub-and-spoke content topology (such as Contentstack's Master/Child stack strategy) can be integrated into the OKF layout 11:

* **The Master Stack:** Maintained by the central system to house core schemas, global system prompts, standard procedures, and shared templates.11  
* **The Child Stacks:** Provisioned per tenant or agent to store localized markdown entries, episodic logs, and local configurations.11

A background process, such as a Localization Agent, automatically syncs changes from the Master Stack to the Child Stacks while preserving local customizations.11

## **Gating the Write Path: Proposer-Critic Gating versus Direct Writes**

A key design difference between the AI-KOS write path and the baseline system is how knowledge updates are validated.1 AI-KOS gates all writes by routing raw inputs from inbox/ through linting, triage to backlog/, and a multi-agent Proposer ![][image30] Critic ![][image30] Comparator ![][image30] Commit cycle managed by the governance-service (Port 8004\) before writing to the long-term knowledge/ store.1  
The baseline system, by contrast, writes updates directly to the knowledge base, relying on formatting conventions and a nightly cleanup process to maintain quality.1

### **Quantitative Comparison of Write-Path Paradigms**

To evaluate the operational impact of these two designs, their performance characteristics are detailed below.

| Operational Metric | Gated Governance (AI-KOS) | Direct Write & Nightly Cleanup (Baseline) |
| :---- | :---- | :---- |
| **Write Latency** | High (![][image31] per transaction due to sequential LLM calls).1 | Low (![][image32] direct file or database update).1 |
| **API Token Cost** | High; multiple LLM calls required for every write operation.1 | Extremely low; token usage is restricted to scheduled cleanup tasks.1 |
| **Write Reliability** | High; prevents formatting errors and duplicate records.1 | Moderate; temporary drift or formatting errors can occur during active sessions.1 |
| **System Throughput** | Low; gated by single-threaded queues and API rate limits.1 | High; write operations are non-blocking.1 |
| **Unattended Autonomy** | Safest; prevents hallucinated or corrupt data from entering the index.1 | Risky; runaway agent loops can write low-quality data.1 |

### **Implementing a Hybrid Validation Pattern**

To balance the safety of the gated model with the speed of direct writes, AI-KOS can adopt a hybrid approach inspired by the Andrej Karpathy LLM Wiki ("akm") pattern.2 This model separates write tasks into structural scaffolding and semantic synthesis 2:

* **Structural Scaffolding (Programmatic Validation):** Tasks like verifying YAML frontmatter schemas, checking relative Markdown links, and confirming file structures are handled by the ci-service (Port 8012\) using fast, programmatic Pydantic validation.1 This validation runs in milliseconds and requires no LLM calls, protecting the system's structural integrity.1  
* **Semantic Synthesis (Gated LLM Governance):** Complex tasks like merging new information into existing articles, resolving conflicting data points, and updating conceptual hierarchies are routed to the multi-agent proposer-critic pipeline.1

This division of labor reserves the computationally expensive LLM governance gate for high-impact knowledge modifications, while routine operations (such as appending episodic logs or updating access counters) bypass the critic loop and write directly to the store.1

## **Advanced Segment-First Retrieval: Parent-Child Chunking and Ingestion**

The AI-KOS "snippet-first" retrieval strategy stores full articles as the master unit of record while retrieving and loading only the matching child chunk.1 This approach aligns with modern parent-child retrieval architectures, which separate search precision from generation context.13

### **Designing the Parent-Child Indexing Architecture**

A parent-child retrieval pipeline addresses the fundamental chunk-sizing dilemma: small chunks are optimal for search precision but lack context, while large chunks provide sufficient context but generate diffuse embeddings that reduce search recall.14

                 ┌────────────────────────────────────────┐  
                 │       Source Markdown Document         │  
                 └───────────────────┬────────────────────┘  
                                     │  
                                     ▼  
                 ┌────────────────────────────────────────┐  
                 │ Parent Chunk (Section-Aware: 1500 Tok) │  
                 └─────────┬───────────────────┬──────────┘  
                           │                   │  
                           ▼                   ▼  
                     ┌───────────┐       ┌───────────┐  
                     │Child 1    │       │Child 2    │  
                     │(300 Tok)  │       │(300 Tok)  │  
                     └─────┬─────┘       └─────┬─────┘  
                           │                   │  
                           ▼                   ▼  
                     ┌───────────┐       ┌───────────┐  
                     │Embedding  │       │Embedding  │  
                     │(768-dim)  │       │(768-dim)  │  
                     └─────┬─────┘       └─────┬─────┘  
                           │                   │  
                           └─────────┬─────────┘  
                                     │  
                                     ▼  
                     ┌───────────────────────────────┐  
                     │ Qdrant Vector DB (Dense Only) │  
                     └───────────────────────────────┘

The process for indexing and retrieving hierarchical segments is structured as follows 14:

1. **Section-Aware Partitioning:** The ingestion pipeline splits source documents into large, section-aware parent chunks of ![][image33] to ![][image34] tokens.14 For Markdown files, these boundaries are aligned with explicit \# headers.14  
2. **Child Segmentation:** Each parent chunk is subdivided into smaller child chunks of ![][image35] to ![][image36] tokens using sliding windows with semantic merging.14  
3. **Vector Indexing:** Only the child chunks are embedded (e.g., using a 768-dimensional model like Qwen3-Embedding-8b) and stored in Qdrant.14 This increases storage requirements by only ![][image37] to ![][image38] compared to single-level chunking.14  
4. **Reconstruction Mapping:** The document ancestry is encoded directly in the vector ID using a structured naming convention:

![][image39]  
This schema allows the system to instantly map retrieved child chunks back to their parent documents in PostgreSQL or local files, bypassing the need for a separate relational lookup.15

### **Mitigating Context Bloat in Cyclic Loops**

When executing cyclic reasoning loops (such as within a LangGraph orchestration), appending full parent documents on every retry or reasoning step can quickly lead to context bloat.19 This saturation of the context window reduces the model's instruction-following accuracy and increases token costs.12  
To prevent this, the retrieval pipeline should implement three core mechanisms 19:

1. **LLM-as-a-Judge Evaluation Nodes:** These nodes inspect retrieved child chunks and determine if they contain the specific information needed to answer the query before pulling the full parent context.19  
2. **Intermediate Map-Reduce Summarization:** A lightweight summarizer node condenses retrieved contexts before passing them to the next cycle, keeping the active token count manageable.19  
3. **Programmatic Circuit Breakers:** These components monitor active token usage and trigger early termination or consolidation loops if context limits are exceeded.20

### **Ingestion Optimizations for Specialized Data Structures**

Standard token-count chunking often degrades retrieval quality on structured content, such as code, tables, and nested hierarchies.16 To address this, the ingestion pipeline should implement specialized processing rules.16

                 ┌────────────────────────────────────────┐  
                 │       Specialized Ingest Pipeline      │  
                 └─────────┬───────────┬───────────┬──────┘  
                           │           │           │  
                           ▼           ▼           ▼  
                     ┌───────────┐┌───────────┐┌───────────┐  
                     │Code Files ││Markdown   ││ Tabular   │  
                     │ (AST)     ││Prose      ││ Data      │  
                     └─────┬─────┘└─────┬─────┘└─────┬─────┘  
                           │           │           │  
                           ▼           ▼           ▼  
                     ┌───────────┐┌───────────┐┌───────────┐  
                     │Tree-Sitter││Header     ││Summarized │  
                     │ Parsing   ││Breadcrumbs││Tables     │  
                     └───────────┘└───────────┘└───────────┘

#### **Code AST Chunking**

Traditional chunking can split functions or class definitions in half, rendering them useless for generation tasks.16 By parsing source files with tree-sitter, the ingestion pipeline builds a structured Abstract Syntax Tree (AST).23  
This tree allows the system to extract complete semantic entities (functions, methods, classes) along with their signatures, parent scopes, and docstrings, preventing unclosed brackets or incomplete definitions.24

#### **Summarized Table Strategy**

Markdown tables are highly vulnerable to token-boundary cuts.21 If a table is split in half, both chunks lose context and become unreadable.21  
The ingestion pipeline should implement a "Summarized Table" pattern: it generates a concise, natural-language summary of the table's contents for vector indexing, but returns the full, intact Markdown table to the LLM during generation.16

#### **Contextual Prepending and Breadcrumbs**

To prevent individual text segments from losing their structural context within the database, the ingestion pipeline should automatically prepend a lightweight breadcrumb header to every child chunk.22 This breadcrumb path maps the document title down to the specific header hierarchy:  
![][image40]  
Prepending this structural context ensures that nested details retain their positional meaning, reducing downstream retrieval failures by up to ![][image41].13

#### **Late Chunking**

For continuous prose, the ingestion pipeline can implement Late Chunking.25 This technique processes the entire unsplit document through a long-context embedding model (such as Jina-embeddings-v2 or Voyage-3-large) to generate token-level contextual embeddings.25  
The document is then partitioned into structural segments, but the vectors are derived from the full-context pass.25 This preserves long-range semantic dependencies and resolves cross-chunk references before storage.25

## **Hardware-Specific Optimization Guidelines: Ubuntu \+ RTX 5070 Ti \+ SSD/NAS Architecture**

Your transition to a native Ubuntu Linux host powered by an Intel Core Ultra 7 255HX CPU, 32 GB RAM, a dedicated NVIDIA GeForce RTX 5070 Ti (16 GB VRAM), and a tiered storage configuration (300 GB Local SSD \+ 3 TB Network Attached Storage) substantially changes your system constraints.  
Native Linux environments running bare-metal LLM engines bypass the performance penalties of Windows/Mac hypervisors, resulting in a direct increase of **\+72% to \+118% in local generation speeds** for identical neural weights.  
Based on these specific hardware capabilities, here is the optimal architectural configuration for your local AI-KOS instance:

### **1\. Storage Segment Segregation: Hot (Local SSD) vs. Cold (Network NAS)**

A critical performance bottleneck in local agent setups is storage I/O latency. Running transactional databases or Git-native workspaces over network mount protocols (like NFS or SMB/Samba) introduces massive random-access delays, leading to high-latency bottlenecks.

* **The Hot Tier (Local 300 GB SSD):** This SSD must host the active vector search directory (Qdrant storage), transaction databases (PostgreSQL or SQLite files), active session tracking stores, and your active ai-kos/ working Git repository. This guarantees sub-millisecond local read/write performance during parallel agent execution.  
* **The Cold Tier (3 TB Network NAS):** Use the 3 TB NAS to host unparsed historical source documents (PDF archives, raw data files), weekly system snapshots, and bare Git clone mirrors. When an ingestion sequence is triggered, the ingestion engine reads from the NAS, processes the documents locally, and writes the structured outputs (OKF Markdown) and embeddings directly to the local SSD.

### **2\. High-Precision Local Reranking (Leveraging 16 GB VRAM)**

In a CPU-only environment, executing cross-encoders at query-time is heavily constrained by processing speed. With 16 GB of dedicated VRAM, you have ample memory capacity to keep both a fast local LLM (such as Llama-3-8B-Instruct at 4-bit quantization, which occupies \~4.8 GB) and a state-of-the-art local reranker co-located in memory.

* **Optimal Reranker Strategy:** Implement the **BGE-Reranker-v2-m3** (or the lightweight ms-marco-MiniLM-L-6-v2 as a fallback) running natively on your RTX 5070 Ti.  
* **Configuration:** Set your initial retrieval candidate pool (![][image11]) to ![][image35] **candidates**.6 With CUDA acceleration on your GPU, the cross-encoder will process and rerank these ![][image35] candidate pairs down to the top $8$ chunks in **under 40 ms** (compared to \~200 ms on a CPU). This setup yields a **\+33% to \+40% accuracy improvement** on complex, entity-heavy queries for negligible latency cost.

### **3\. Git-Native Performance Optimizations for SSD**

To ensure your Git-native files (knowledge/, episodes/) remain instantly searchable and do not suffer from index write delays on your SSD, configure Git locally with the following system optimizations:

Bash  
\# Inform Git that the repository contains a high volume of files  
git config \--global feature.manyFiles true

\# Enable Git's built-in background filesystem monitor daemon (FSMonitor)   
\# to bypass scanning the entire file tree for changes on every 'git status'  
git config \--global core.fsmonitor true

\# Upgrade the Git index representation to compress paths by 30% to 50%  
git config \--global index.version 4

Applying these settings cuts file tracking and staging overhead on Linux in half, keeping your agent's directory queries fast and efficient.

## **Actionable Recommendations and Engineering Roadmap**

To evolve the AI-KOS v0.1 specification into a high-performance, multi-tenant capable, and latency-optimized cognitive operating system, the following three-phased engineering roadmap is recommended.

### **Phase 1: Search Optimization and Ingestion Upgrades (Short-Term Deployment)**

* **Implement an Adaptive Reranking Config Flag:** Do not discard the reranker stage.1 Instead, implement a dynamic configuration flag. For local, CPU-bound environments, use a lightweight model like MiniLM-L-6-v2 with a restricted candidate set ($K=20$ to $K=30$) reranked to the top $5$ to $8$ chunks.7 For high-capability GPU or enterprise cloud deployments (such as your native Ubuntu RTX 5070 Ti environment), transition to BGE-Reranker-v2-m3 or Cohere Rerank v4.0 Pro with a candidate pool of $K=100$ to maximize precision on complex tasks.  
* **Deploy Structure-Aware Ingestion Pipelines:** Integrate AST-based code chunking via tree-sitter and implement the "Summarized Table" pattern.16 Enforce contextual breadcrumb headers on all text chunks to minimize retrieval errors across long, complex documents.13

### **Phase 2: Write-Path Optimization and Caching (Medium-Term Deployment)**

* **Transition to Tiered Governance:** Replace the mandatory multi-agent critic loop for minor writes.1 Implement a programmatic validation layer (using fast Pydantic schemas within the ci-service on Port 8012\) to handle structural linting and formatting verification in milliseconds.1 Reserve the intensive Proposer-Critic-Comparator pipeline exclusively for core schema modifications and high-priority knowledge synthesis.1  
* **Develop Hybrid DB-Backed Caching:** While retaining the portable OKF Markdown format as the master system of record 1, deploy a local database (such as SQLite or an embedded key-value store on your high-speed SSD) to serve as a fast transactional caching layer for active session contexts, temporal decay calculations, and concurrent write locks. This prevents file-system lock bottlenecks during active agent execution.4

### **Phase 3: Multi-Tenant Architecture (Long-Term Evolution)**

* **Implement Session-Isolated MicroVM Runtimes:** Transition the execution layer to spin up lightweight microVMs on a per-tenant or per-session basis.10 This ensures strict filesystem and memory isolation, protecting sensitive data across collaborative agents.10  
* **Enforce Metadata-Driven Tenant Routing:** Update the service registry (Ports 8001–8012) to accept and propagate custom tenant headers in HTTP REST payloads.1 Use these headers to enforce tenant-scoped directory paths, regional compliance parameters, and model entitlement checks at the gateway layer.10

#### **Works cited**

1. c2d6c45adf3ab2f90844cf817add32c66637d9e2c97003f19c216d1c90c4006b.md  
2. Building Agent Knowledge Bases That Actually Scale \- DEV Community, accessed on June 25, 2026, [https://dev.to/itlackey/building-agent-knowledge-bases-that-actually-scale-23pb](https://dev.to/itlackey/building-agent-knowledge-bases-that-actually-scale-23pb)  
3. From BM25 to Corrective RAG: Benchmarking Retrieval Strategies for Text-and-Table Documents \- arXiv, accessed on June 25, 2026, [https://arxiv.org/html/2604.01733v1](https://arxiv.org/html/2604.01733v1)  
4. The Scaling Wall: Moving Beyond MD Files in Multi-Agent Systems \- Volodymyr Pavlyshyn, accessed on June 25, 2026, [https://volodymyrpavlyshyn.medium.com/the-scaling-wall-moving-beyond-md-files-in-multi-agent-systems-da413f9d33e3](https://volodymyrpavlyshyn.medium.com/the-scaling-wall-moving-beyond-md-files-in-multi-agent-systems-da413f9d33e3)  
5. RAG Anti-Patterns: 7 Failure Modes Engineering Guide 2026 \- Digital Applied, accessed on June 25, 2026, [https://www.digitalapplied.com/blog/rag-anti-patterns-7-failure-modes-2026-engineering-guide](https://www.digitalapplied.com/blog/rag-anti-patterns-7-failure-modes-2026-engineering-guide)  
6. Reranking & Cross-Encoders for RAG: BGE, Cohere, Jina (2026) | Local AI Master, accessed on June 25, 2026, [https://localaimaster.com/blog/reranking-cross-encoders-guide](https://localaimaster.com/blog/reranking-cross-encoders-guide)  
7. RAG Reranking Techniques For Better Search \- CustomGPT.ai, accessed on June 25, 2026, [https://customgpt.ai/rag-reranking-techniques/](https://customgpt.ai/rag-reranking-techniques/)  
8. Multi-Document RAG: RetrievalQA Breaks on 100+ Docs (2026) | AI Learning Hub, accessed on June 25, 2026, [https://ailearnings.in/blog/multi-document-rag/](https://ailearnings.in/blog/multi-document-rag/)  
9. Best practices for running a CPU-only RAG chatbot in production? \- Reddit, accessed on June 25, 2026, [https://www.reddit.com/r/Rag/comments/1qafa53/best\_practices\_for\_running\_a\_cpuonly\_rag\_chatbot/](https://www.reddit.com/r/Rag/comments/1qafa53/best_practices_for_running_a_cpuonly_rag_chatbot/)  
10. Building multi-tenant agents with Amazon Bedrock AgentCore | Artificial Intelligence \- AWS, accessed on June 25, 2026, [https://aws.amazon.com/blogs/machine-learning/building-multi-tenant-agents-with-amazon-bedrock-agentcore/](https://aws.amazon.com/blogs/machine-learning/building-multi-tenant-agents-with-amazon-bedrock-agentcore/)  
11. Content modeling for multi-tenant architectures: Scaling complex digital stacks, accessed on June 25, 2026, [https://www.contentstack.com/blog/tech-talk/content-modeling-for-multi-tenant-architectures](https://www.contentstack.com/blog/tech-talk/content-modeling-for-multi-tenant-architectures)  
12. Choosing the Right Multi-Agent Architecture \- LangChain, accessed on June 25, 2026, [https://www.langchain.com/blog/choosing-the-right-multi-agent-architecture](https://www.langchain.com/blog/choosing-the-right-multi-agent-architecture)  
13. Chunking Strategies for RAG: Methods, Trade-offs & Best Practices \- Atlan, accessed on June 25, 2026, [https://atlan.com/know/chunking-strategies-rag/](https://atlan.com/know/chunking-strategies-rag/)  
14. Parent-Child Chunking for RAG: Small Chunks for Search, Large Chunks for Context | CallSphere Blog, accessed on June 25, 2026, [https://callsphere.ai/blog/parent-child-chunking-rag-small-chunks-search-large-chunks-context](https://callsphere.ai/blog/parent-child-chunking-rag-small-chunks-search-large-chunks-context)  
15. Parent-Child Document Architecture in RAG: Why Flat Chunking Isn't Enough \- Towards AI, accessed on June 25, 2026, [https://pub.towardsai.net/parent-child-document-architecture-in-rag-why-flat-chunking-isnt-enough-0ab7ed3077ff](https://pub.towardsai.net/parent-child-document-architecture-in-rag-why-flat-chunking-isnt-enough-0ab7ed3077ff)  
16. ai-system-design-guide/06-retrieval-systems/02-chunking-strategies.md at main \- GitHub, accessed on June 25, 2026, [https://github.com/ombharatiya/ai-system-design-guide/blob/main/06-retrieval-systems/02-chunking-strategies.md](https://github.com/ombharatiya/ai-system-design-guide/blob/main/06-retrieval-systems/02-chunking-strategies.md)  
17. agentic-rag-for-dummies/project/README.md at main \- GitHub, accessed on June 25, 2026, [https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/README.md](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/README.md)  
18. Building a Modern RAG Agent in 2026: Qwen3 Embeddings and Vector Database in Qdrant., accessed on June 25, 2026, [https://pub.towardsai.net/building-a-modern-rag-pipeline-in-2026-qwen3-embeddings-and-vector-database-in-qdrant-ebeca2bbe338](https://pub.towardsai.net/building-a-modern-rag-pipeline-in-2026-qwen3-embeddings-and-vector-database-in-qdrant-ebeca2bbe338)  
19. Agentic RAG Architecture: Implementing Parent-Child Retrieval (Qdrant \+ Postgres) and tackling Context Bloat in LangGraph \- Reddit, accessed on June 25, 2026, [https://www.reddit.com/r/Rag/comments/1rbog3b/agentic\_rag\_architecture\_implementing\_parentchild/](https://www.reddit.com/r/Rag/comments/1rbog3b/agentic_rag_architecture_implementing_parentchild/)  
20. LangGraph-based production-style RAG (Parent-Child retrieval, idempotent ingestion) — feedback on recursive loops? : r/LangChain \- Reddit, accessed on June 25, 2026, [https://www.reddit.com/r/LangChain/comments/1rbd4x5/langgraphbased\_productionstyle\_rag\_parentchild/](https://www.reddit.com/r/LangChain/comments/1rbd4x5/langgraphbased_productionstyle_rag_parentchild/)  
21. Tokenizer-Aware Markdown Chunking That Doesn't Shred Tables \- DEV Community, accessed on June 25, 2026, [https://dev.to/gabrielanhaia/tokenizer-aware-markdown-chunking-that-doesnt-shred-tables-3kd7](https://dev.to/gabrielanhaia/tokenizer-aware-markdown-chunking-that-doesnt-shred-tables-3kd7)  
22. Chunking Strategies : r/Rag \- Reddit, accessed on June 25, 2026, [https://www.reddit.com/r/Rag/comments/1ppw6oi/chunking\_strategies/](https://www.reddit.com/r/Rag/comments/1ppw6oi/chunking_strategies/)  
23. Chunking \- Chroma Docs, accessed on June 25, 2026, [https://docs.trychroma.com/guides/build/chunking](https://docs.trychroma.com/guides/build/chunking)  
24. AST-Aware Code Chunking, Explained \- Supermemory, accessed on June 25, 2026, [https://supermemory.ai/blog/building-code-chunk-ast-aware-code-chunking/](https://supermemory.ai/blog/building-code-chunk-ast-aware-code-chunking/)  
25. The RAG Chunking Strategies that can actually survive Production \- SAP Community, accessed on June 25, 2026, [https://community.sap.com/t5/artificial-intelligence-blogs-posts/the-rag-chunking-strategies-that-can-actually-survive-production/ba-p/14412471](https://community.sap.com/t5/artificial-intelligence-blogs-posts/the-rag-chunking-strategies-that-can-actually-survive-production/ba-p/14412471)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAAAv0lEQVR4Xu2TUQ0CMRBEVwMW0IAFLGDhLGABB0hAAg5wgAMMnADYR7nLttzsz30Qkr5kkst2Ot1eW7PO37J1HdtiYO86u66W+97GkxXj03Wrh2cG12jFv3FdXPfP9xeYWHVnOpSJBBIceVhpKEWFEsYYDUTwEpyiQtmqCqWeokLV5KneLlbxk9D2pFeFcsJLk9UOKlTowXQodzVFhUJ7J/kV+IdQm2F1BpcU4XHwAAimczrkqq2G7uhseoGdTuAFhMtEXIyvY3cAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAAA7UlEQVR4Xu2TYQ0CMQxGpwELaMACFrCABSzgAAlIwAEOcICBEwB92z7S624Bwi+SvaS5u6791nW9lAZ/x9rsaHatz+18+QX+k9nF7BDWZmxSEdulkkTCw2zvg+r3lErMyuxsdqvvDfdUqos+hDkBkIhg3GgpN0MyRsWCQHxKQIzv2BZOiHCDeuSPEUU5ak8U/0eorxLpJcsfN2ugDQRSnfhJlAq9mFByvOm3ooh5QW5ewepxTO6dIMNlxXFhuOVjhnuizGqDhpoAbxp0EWeSVrBRLCbDQs88XCAbIUzlVLjU/6+hOiqjNf5nGQyMJ8Z/T/i+CBQMAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABpElEQVR4Xu2VUVHFMBBFowELaMACFrCABSzgAAlIwAEOcIABBEDO9J3O7ZK2rzN88NEzs/OmTbK5dzfNa+3kZJe7Hrf1ZWFv/E+56fHe46XHW4/H5fAMwj/bNH8XJj21KSGJR47Y6PUSzK2Jn9skTNhcgfeXYM5Xj4eYt4oOWIQgNmVxghjGSc5GjH+0pTiemSMYRADBe0Lzu5BYUYLr7zaJAIQwJ6vIO+YgWHjOPBoR9qpmVmExCXNTHOJMnFOd8o6QarAKs4JXQTLbRkszkfCeKtbDXIVRvRSf54281dgqlJTEfkk45BexiNmCcdeKraLaiNTIoRYCLnSdJUYcVdxKhHvmVAOs8SsURGZ+hFOEunYmhSUk4V2es8SvcjVxQK5sodeNx2NongNf2wEKHp0JEl4rqrbQ9vtcP7IFR4R536Wo+kEkrM+W+nUnde8Zz0oyaiXVHZWeiowgB2c1OSTM6mQV6uG3JQSJDJ8rtYVCdVMYZvOC/oVXhNdFPUM6HUVeqFJbKAglt2P1Ah7ifySuqtMjYKi2MGHcSm/NOzk5+Tf8AHoGi334Ia3TAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABnUlEQVR4Xu2V0U3EMBBEXQMtUMO1QAu0QAu0QAdXAiXQAR3QAQ1cAeCnaKLJaO3kJD74yJNWd4rt3dmdc661k5NdLj0e82Gwt/6nPPT47HHt8dHjZbu8gvDvtuyfwobXtiQj6dN2uYSi7HXe2iJMUFwCyUmw59bj2faVqEs//NUWoSM4Q3IXAZyjsEA4AgieExrALmzMzvH/p41HTWLWUxjPXBjfffrkQ/wo7wb9JhKK8FtI1H0lDOtmwjTBQ7CZInyqEw7TWSLboRL23rY2+ToCD1kosI3fC4XoGGtJWE2LxHpeCZNV5ECkbuVdFjoujkBAJpGFohIGnNNFEoh0CxFOrqr5Fe+SkEDv0C0UI2EJgtxCRBKI4nwOYIVFnwTT4xmFEQokznfbEWFpIWL8tiNaNTbMXgsUVWF99+Cc3mVYV5EN6TY7ZXPZgUMSRj5ib2JMg5vuHBYGjNqtBIRyQ9M+ZyYsLRRM1oXh2LB5/aFSRH8bJB3Zo5vrkY2lhQKh2K+1fAGXsIGNCMpO74FG00KHdRpnELN9Jycn/4ZflAaGqUtuqKQAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABo0lEQVR4Xu2VUVEEMRBEowELaMACFrCABSzgAAlIwAEOcICBEwB5FXrp65q97FXxwUde1dTCbmamJzPJtbZYTLnrdpsvg9n3P+Wm23u3l25v3R7PP28g/LON9VNY9NRGQAJnRXx7aL/BCM47nuK5DWGC5BJ4/2OsObURa4oqwAlBJMTZIeFXGEm96o82YggKRADGe0zFTyGwRAmJoEJ/R2Kee23Cx+Pwt8cgFzEOtRBnAnrrqJDKHAR5koosMIVpBw9BMLWNlu4lPyLstZ23yecN30MtBLaU3dJJokKeiPWhBq3hKcs1ahW7jUi1+6oWAlVokH2LEcAueiCEeJt0QCpxOoUCkR4fX2Kl74YLcwjCO5+zKohO5iWI5WsQiRGPYstdZODVSkeCZ0mropxsIWJYr/+rQ7ZxRFi1gzAThr+3VDeAk7k3cM7LNIUoYCWMHakgBrPqXCVMu+MzlMNfHXUGHL/qXsoWCvkIRol52wUhuhwlKoedoDqZWqPrIMkWCoTip295AZfoN5JkWanwNfkjLygoW+jwnd2kyEvrFovFv+EbYCCKN4Q42JcAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABsklEQVR4Xu3VYVHDQBCG4dOABTRgAQtYwAIWcIAEJOAABzjAAAIgz2S+stk2TTvDD37kndlpc7e3++3t5TLGzs4md5Pd9sHG1vyfcjPZ+2Qvk71N9ricPkD455j9z8LhaczBBL1fTh8wnqT8O89jFhYkj0BrGZ+vyR6K30lSZV38MY4TmxfQvDWvY/arVXuWOCiCAGacZQM24ShARf+/x29Sv0T11tiRKsSa+ux/3X1xejGr5Ex0JHEWQJDn3mJriQtdaBeWHbwIzpL6TSUWqyxo25ow44FfbVM9b9Ze1MKgbdokgYq1VsDsFrqAkPEITqvEIDKtv6qFlSqOqawGuVQYrMuLFIisLSRcm2vxR9QqWQTWCq8R1iGotpBIRpT1q7tosh5Yu5eEhCLPPciWsN5CYmocopNjQb8WKpLm8BJ+SsDaTgY7VdckTiU5FvQKKoLYcqhsTVh9eyvW9GvoYmEQuLYShHpDq5B+R/GRxEHv9BYGvlWYjqX4I/JBzVljgvaE/LwY5nPPrQXtLQyE5rOGfgGfhANHgnqlIVeBA7v2qhvvLayYV5SNOOe3s7Pzb/gBr9uOQRs/Kx8AAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAZCAYAAAAv3j5gAAAA10lEQVR4Xu2UURHCMAyGqwELaMACFrAwC7OAg0lAAg5wgAMMIIDl25a7LmyX9OgDD/3u/hvLQv9myZpSo1GRi6gTHZd7rtwTr8pV9DF6ik55ksfDBjbA6JXmXNSLDquMAFEj9BN/Z3RfRD79KR6EEiPtC0PAQDB5X/DwvCF2Z2NIRxn4bZvPBt8mNqFlW5FsY8jrCTlUxaZCeK+OatgMG82pbsRCLLhnZF/pLp4RC9HHfEGqxGTIYi6eETBImOn3xClxW2UEiBgBFXVpPn6KzjiFPzcadRkBQQE9U5RbdacAAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAAA70lEQVR4Xu2VbQ0CMQyGpwELaMACFrBwFrCAAyQgAQc4QAgCjj3sSnbNPsMIP+iTvMml7dY3u97OOcMwutl7HXRw4exCXuCZ2FeYvE5ed695eU5BTitXW+SmAwkwJSo1Isd+6OLWp9ZFiymBJjVTQ/gLU+TYk/njFW5WFY2MNhXP0dUFc1ljOxcWaLFIx9A2LFtRM0WPGKk/qvgbXMuXEeuRiKFU45opjdT3vI0XPQtKprgkycWn9XNT7JMz1X2rjzJFTM8OXx/jkZrPIi2maIgZLb0WE4h6MaSHvwm98adgAlP8tLNXQY1JBwzDGMQTnNtaQkc5TK0AAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADUAAAAZCAYAAACRiGY9AAABXUlEQVR4Xu2WYW0DMQxGg6EUhqEUSmEURmEUymAQCmEMxmAMSqAAtjxlVqNvji+X3qb7kSdZrRxf4s/xuU1pMplM/plTtmd1Zp6yvaeyRowa6xHEvKWyxzktxz/MSyoHfWb7+vmukBRrLXu9h/6C/RFjBeOcW7ZjHbSGD3U4cKhZSxRJW5VrwxedwY2wJ4LUd618q4gOVOw2PFG0jlb2kEpifLawPbmZGvJSsd1sJUoFgbVUBIKJoyg1uxCl0KoXda6Am8OiW27yF6JIhIRGJxjvJ+dQmBDaw8ZrbUwa9WFeQr2ibFKOQJ4UZFEQ2BRSYwP1YV7ivaKuqZy3FhssXYIitm4/Kr0U44EgbrcW1OqYRbYWRVJRDEl6k5I81M9t70IUa1EM7c56LYApSdvpK0DcED2iLFE171mLbf0tsr9AdgNWKM+8/bsYfrAB7wYtOPT7shUPT5rJZDLZJd/P03/vcFIbEAAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEsAAAAZCAYAAAB5CNMWAAACB0lEQVR4Xu2XgU3EMAxFOwMrMAMrsAIrsAIrsAEjMAIbsAEbsAADQJ7uvuQzdu2eQOpBnmSpl6RO/OM4vWWZTCaTyaTB7bA733jkatjDsJdhT8PuT7tbrPm/CAj6cdjbsM/jswehXpfDWAJmDGOf7aCEjv9dQIAVBCPLgkEUMgrRbBvjqwzr+N8FHbEEGZMFgx/6OIZC47tzrPnfBd1AYC0YsgJfN6btp8QiW+mz9UzPdj7gt/quj8YzbTbrz6IbCGTBZJBlW8Zn/glW9ex9ORx3fGMfy2ldpI82bZIuGrV7cTfxW2KxiwRGkN0drfxLLOsPIf07ulxsSQDWgmDlepSe3nDg2zDS11MFY2G3twgFlf/sSCMgIgiJhT+LLhAv4jdIQybyxiS+DYsWXAUjWMxWoaDyn4lFG306YplY8o8WZxFNnlEFA+yeF4q2DpX/SiydhkqszrdfSDR5RhUM9cMvhN22bQSUFdnKfyYWp4OjKDKxdOF0N+8b0eQZa8EgQHSkCcKO100VCbbmH+jDn81aCaBPCpBYtjbZC+dsOmJpcm/2XR2FyOwO60ayF0jHP9BGwNQc3iFj8eUzRf4Yxxh+8x7+ttbRE/yC9owVULd7hD2G+qCNbvfN+F3ZM1G2RWQ1619AVqie6bswO0706Q88NSuqjX8ast9fHJkIfhx/dyaTyeXwBUu22d+gRUDUAAAAAElFTkSuQmCC>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAaCAYAAABVX2cEAAAAv0lEQVR4Xu2SXQ2CMQxFqwELaMACFrCABSzgAAlIwAEOcICBTwDspNykWQrpCA887CR92Nrd9c9s8ldsmz0SO4SYU+e7Bl/KxTxw1zsa62Z38w9WnS+FYMR6yJxMECxBYJY+mZytmI3Ym4sdX2ceUzb3w/A7YpS0aXYzL/sr1C+aT0aISXwI9WsxXwFQ2QgPoYcSEohzX54ixH5FGEYcSol3+xXLL8Hksv0S3OP/uCKUpJ5Ei4+UcbSh5Z1MfsUTTVs/n1pNw+gAAAAASUVORK5CYII=>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADcAAAAWCAYAAABkKwTVAAAAbklEQVR4XmNgGAWjYBSMglEwCkgGyugCwwG4AfFKKBZCkxuyAOSpEwwQTw2bWMsA4p0Mw9BT14G4i2EYJb9h6SkQAOWrZ0A8k2GYeQwZDNvYQwbInhw2hQk6GJbVADoYEZ4EeWxYtVBGwSigMwAAOsgTez3h160AAAAASUVORK5CYII=>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAAWCAYAAACcy/8iAAACZklEQVR4Xu3XYXHbQBAFYGEIhWIIhVAohVIohTAohEAogzIogxIIgNZf7eesVidZzvRHM6M3cyPpfLf73ru9kzxNBw4c+E/x6dQee2fDQ+/4qPh2at8v15f2W0Dsz1Hn1+ltMtcq/PZ5enOKo/puObuGL9OZoOZ+BByeT+3H5dpX6enUXku/WITh5TdN7F/TWdMVSOsUVBITBKqQ9HdrzOkk9gAxuULKs1gVOOGAC4RTNZgIvAILkriuGsFMuPJ0E7FBxJlY+0x0RW5tVW4B4UV5TWcOCAfy9BL1XAW6r88RWoFr1fF3AHG1hCWOs4HAs4nvhHwjweInJy44dfKdazegC6ZjVsrA2ZQv99dE/SvBSCAtXoi74pFn1bMlODyMq1uPuJR8DqrZlvOQ5AYL6Cp5P4wyJmWk9TF7gYi8yMopVi3nLqz3VyNy8KmOugUWpQw6cgDVhITV0w+QqolGh8heiCtecjOgxrlHMOButQP3tZRzmM0EV6Ts6j4eCTOGkyDgrRYBWRV5VFNWOznuFVxhW9RSJv5qaA6HuvEhRkTMGqpZ5txq9b0aIGY1unmea9XV/i3BfasxchZnj+DRikMVvBdWtAuBiIHk78LWVj7Ar85JnNl4ovpHRheYRCPByuUeLBy/AClmQA7TNcGjjx3Vs7ZwM8Hp7F8w9dAyppe3vWHeiPwWxO7EQPwqsL9jgbn9YyTopQzZsouKQIK7EkZsn0xgTuqMqSfjXuSETr7saTEr8h5lRAyvh1FFL+WKcF4g39BEjIJCHdP/XNwLhoqlbcXKK2WxSgW9Eipi8NaYAwc+Iv4AMHPkvecrXv0AAAAASUVORK5CYII=>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFEAAAAWCAYAAAC40nDiAAACb0lEQVR4Xu2XfVHEQAzFqwELaMACFrCABSzgAAlIwAEOcHAGEAD9zfTd5F6T7cdx/YPZN5O5Ns1ukpc02xuGjo6Ojo6OG+BhlJfpF9yN8jTpHI+jvI3yMeTPtwJfr66cQAzPo9xP9/xyj96B/n2S7PnNATE/Jt/DPBgCRY89yRPw13S9BZABcaxnP/xlwMbjwp+KLSgO9kW4RncoIIVkPieh01R9AaKwgciI01B3UgWRiF/8tUhkf8VF53vB1AAxXq7R8ewwKJkWIC8LjHUkuhdLJC4ViI7L1qM7tBvXkKhgMxKzJNaitX4NiRQwW4+ulRN5IBpZcd6q2/l1XQT6c3xspjmCY649+CpZ6Z3ctaj2BcTAAYYoLp/TFVnoq30BazSP8cMIY298yI8OKfxjG0cGz1hzzpsLKiojWOc+vg5VskeQqC7gQMGW7hD2kgh0cMWvDEjzPfEvsuP9xQGH0g8SOZBhlWwkUa9fS5zsal9ATP4aqYMET1jYQmL0QXzoso4XibqnY2NBZ5ADLVSyWVIicY14sVokZvDOVzKOLSRGiEQvtpMIeRc+CCJWFziJuvfNt5LgqNZDNjHxOkc4idV6dFmHRlxDIqChzh2LQUWijDQrfHMCzTphLSoSlExFot4Ihnu2Hh3PWriGxFmBUPi/gNMwJwdd3EgDtjkXFlCRyN74j+NDH9GRnOzDWgX30eHYS6J8zg4WkiE4DNVdPv9YRMdiQ6DY7P2gJYhMYvD4wwf+EIqY+aOI+jcVr1twv8o76rgX0R6j/uHNuh1iWORViIBYAuSzwLv3Fljrj+7ABtulDvwLxM+ujo6O/4Ff/4kQjP8A7dYAAAAASUVORK5CYII=>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAWCAYAAABdTLWOAAABUElEQVR4Xu3WgU3DMBCF4czACszACqzACl2BFdiAERiBDdiADbpABwB/0EPuNYldVwIJ5Zee0rju+Z19l3SaNjY2/oSHol3R7fHe1b3xEe6Lnoteix6Lbk6/HuOp6CPpveiuntSJ5JhjlJjcn8yY4S0PzMCkQObSNdkfpvPfvqT7M3pN0rXYOaeQTTZj/6ZJ5ph0KgwHSmeVXpPqiMwXdLRpNEzUdTRPcwMuMRnHpGEsoglGqI2q0Z+EBY6OqmVX8hjF4wY+5zqSnAXAbJTEkiIh11hTjDD7RRxVloXyGLWOIBaw2NIG1Io5ubs9KSLZRSy2hl0URJI1tclePGocdaYZo2VSAGaWTOYyWEOMOZNNWiaZUEO1Gbsb3XkJGiQfNxz5Ki2TUE+MRhPsp463xAISY9RVLHGaHpoTjsh+N31nPfLOrok/KEx2xTJ549/wCWzwak4oZ5nHAAAAAElFTkSuQmCC>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFoAAAAWCAYAAABAMosVAAACtklEQVR4Xu2X0XHbMBBEUYNbSA1pIS2kBbfgFtxBSkgJ7iAdpAM3kAJsPZM7s1rdkVRk+QtvBkPyKBz2FiAhjjGZTCaTyeSCb6f2lMEV4j9P7WG9/r7GODrcJ/5yar/G5f2jMNbjWDQBR66JJ8R/r626D/R/PrU/61F1fBk/xjIwxryNRUgFce57o48L5vzvWArmnNz/xmLEtaApxyN3ThxjEcdImsZ36IMOLSKOXGeuu4IZWpl7RlMERwyuzMOc14jxO4q6dgUpF+PR0Jg50I5mrXrgnBj3BP3TfK67Wu/OntEuvkLGODKjmpgtMJq2BWaROyEmY2V85tIT45P0ZdxitArK/jI6C93jiNFMbGe0dDDB1fgyuquJJ5x7NGrjacp9A6qYIEeO+0FllCDO5sZRzd9xnaGKd3k7tG/Q6MtrKze6Li9xTUBnqOKpV1CrJpJzbbTo4VVIPr1Clcv1EW8XZycciLuo3FDuZbT/yyEPBYgu72cYDdKODoEeYrnvaP/ya22+F3TCodqhXcQRozX7W01G6nF1yEGBotP72UZXTxKr3EGHa5HW0uxOeIcXJFEpwI32917XqgkV5HDTOGflJJXRadY1RuckVf3SaP2llI4zOqMRyb2cHS9I19lfYlPYFqxmRPojC2m0rhPX0Y3frXTnFqNF9v2gMgokqjLaV1S+p0Bic0VtoT6d0Xql8PR0RuvJ0js1jVFN+XpybjE6fTijM5qBsujHcWkgsdwkKPjVro+gL0zPo7+P/mqqPk709PnfrerjhPz5EZPcYjQ1ny1MJauag4kkYgCK7T6t9UlMwfz2fz916UMectAQXhmjyeXo544mjsWiRZMTmVCre6Ha06PKP8XoU2nehVXCLFFI9Qdd6I86Zm8Vswd9GYsxtybrqC5Nfq7Qe6C6t/RMJpNJxztf8D1P9lnuogAAAABJRU5ErkJggg==>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADsAAAAWCAYAAAB+F+RbAAABcUlEQVR4Xu2WAW0DMQxFD8MoFEMpjMIolEIpjMEgDMIYjEEZlEABtHlafPJc27ncSeuk5knWpU7i+DuX9KZpMBgMnoTXYm/WqTgU+6yWjVvKrtjROiv4WeOl/t6rvtUg4L3Yqdi1tj0QyBgSxGjj64WCssbX9LPe9+/uGfz0a0uJAmkQKxaJJUH6ECnQxkdfD4xn19ipllgKypPCkF9KFMhDBHli2UGvsvjW7K7QEttVyCiQRyb2PMVie9awZPMfJjZKatFZSojiAv6P+hRLaQ5Q/EexOpf51uawk6w1Drj1YfqiEbaIZS7zWmaJ4kL4V8Ntpbdb7OL4bMWEllgKZxGxFM8W1DNLJrabnkCZWOJ4r+vWZKP5fEzQF31wuHiBIjKxXBSRWPrWEoklh4eJ9T4gpPre+V9KJJZ1OJqag/l9hxfIIlW0ZueyGHcAT93uRYrqmYbY5EB+vD2sl2IT3op8uJPIlh1dStd6ayo/GPwxNyTOn3z1Dp41AAAAAElFTkSuQmCC>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD8AAAAWCAYAAAB3/EQhAAABwUlEQVR4Xu2WYXHDMAxGjWEUhqEURmEURmEUxmAQBmEMxmAMSqAANr/MX05T41hxe+mP+t3p4iiOLMmSk5QGg8HgzjhkeS1XeMjyXHRb2WLrJctHEebchKcsP05Oqc+hqC0C/s7yWIQxut3BYRz8KvKe/hzqIWJLCbJ6xuh4tissiKPXIGKLHSZQD7rddz/icJSIrWOqB7/2LrYRtRDVwrnBPWcLcPU6C/q3IhMYVM+xOOP54UYitmpB6oyowTu0FHOwSUsRDGsgjHV4fpa5trV4xjtK4gQDdkMTyRj3PSUYsdUbPBA0c+zXg2C9TdZVkuy9vkIzPPCHkhZhMgGpVNYEWrbAOyq2BG9LGv/QqR2EDV73VAhtcZYEixbhSjAqlTWpYW2BnPBsCd6i4L0PPniC1hqzDRyhPyze4SgRW+y6DwDQLVWE5ZLgQT9d9P4Ek2oO+1JqEbHFwj4AQDc7VeGS4BcTi9L3wDEtl2aLiK2lHxodWv688PQGrzW9b1Mp4DRZZ7I+UUvfyRZRW/QfFcLVjtfAeSuyb3XcK0FWSIz+POXbP8g+Sp/BHiK22A0+WQTd2vFroA1g988qYDC4A34B/3/J2PRMfrUAAAAASUVORK5CYII=>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEUAAAAWCAYAAACWl1FwAAAB5klEQVR4Xu2XgU3DMBBFPQMrMAMrsAIrsAIrsAEjMAIbsAEbdIEOAHlNTjo+9xOn0EpIfpLV9Bz7/n07jdvaYDAYDK7O7dSeNJi4n9rL1N7a+n293EztWYMJ9ND/vnxyf8Xj1F6X9iB9Z0GhJKTQzzYLqCDxsc33Iw4BH8v1HqJQxjMfOSvu2twf5vPJd+KZ0MG8NK6J/QqKJCHJnCkUjiCMyRza+kpXhCnkJZczhT4tju9ZH3MwnjkDronR9yc4UzCjSsS9GHMuzpQoTA3nezYBk6rxxNRQxmztat2FJ5wpkbwypRLVixsfi+BMCR0sSDW+qoOCiTljqFGfhBPVZODER1zN6sXNq8VrPMxyeolX8zpjrCHgkjjx/80UUGNWDQGXxInPpiB0q2mRbt5LmgJhzKYh4JKEeN122ZSelt8SsGWKnjkqU3gFK1umAEeQriOFM8WtnCuqFzeePLn4QHW48a6OIHaIPkolbjJWzJlSrVQvrihErpkSRXC6rsYTo69CH5lNY5wpcGjfRYbwnGAvzhTQgxroabU6qMUC6qMKakjww5jYqlXLxLEbY0isAvegeaLl4hBIDp594u43gCLjtJ2vFTRX8YD6dGd2gSAmjr8F14BiqjdXJv7Ioq3aIYPB4PJ8Af+T2tMNlr6zAAAAAElFTkSuQmCC>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAWCAYAAACCAs+RAAAByElEQVR4Xu2WbVHFMBBFqwELaMACFrCABSzgAAlIwAEOcIABBEBP29PZ7tskw8z7BT0zO0M+urk3m+QxTScnJ/+Omzme5nib43mO++PwDv0v0zqP+SO+i3gP4+TL4/RV/TnQcNB5N63JH7Y2ApmIocjjHF/T+jHGX+f42P4e4eIVbAx50JHREHMirIkRxtC1gCA6NAIufLu1+RAT+0cbn9Ol4YqWEfL1NkMj1RpoYwxdCxqJR8WF3SUWpJ2PHJXEzIjKyMgE9IzARd5YVp1GgZqtjGSBFXlBTPBtzwT0jLi58c7tePYoVzTXEmx/NpiJRhRQictURtDofUXrxWZwoTwq+UW6lhEEUF1E0K4ueEQjrIMZgxzoJF8TkrMQk+VaRszJw0KbO9Kjqoigc5jDp83KKDiX8bdGIq5RiZSeETDHguWK0LaksZ0FtyqVqYz4pNPfOmIjI+raJ2aRvlL+EHkUKiPd0m5URmB0xEZG+G7J665QoggXKe8Uffn1YE73wm20jIBiKrEayb/s4H8g+yawK4hkMsl8fuMvPfgIMIcxEsQHoUIDMTyu4NGMQf54Ulrhxh7uLQ3EKTJfavENZzda5/rk5K/wA/ep2G5z05aRAAAAAElFTkSuQmCC>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAWCAYAAABdTLWOAAABWElEQVR4Xu2UAW0DMQxFg6EUhqEUSmEUSqEUyqAQCqEMxmAMSmAA1rwmX/JZWZxUkyZNeZJ1vTTn/HzHSWmxWPwZbzkuOa45zvX9VQ6p5LrlOOXYbf9+jWMqCfepJEToV453O2kQ5UIogcj7ZkaDDz/QgCSIknsk/67js5DHO8emu4yKRBROgkSy4Az6zovk+HQZEUlSewYpGYuFDjjIowogWHya301GRFoQyyIk9o6MQMMglFDz/IqTgrmEd2IWK3TTgJwndZQNHPFjRO+KUbl56h03emHnak02LLFPsFVO2GAnfoyISsB3aqafDLChOb67uYLCBkRQD92L/k6UC9FmLOSh1B7Ed4lEImJTksq9jnnxPahmS2RIJJJdIoayCM6rrpKZDmdDvtxgczeJRAJuIkhNwMEndLnPgJMI5UkujkCoIZxQwb1jKonDMxRgcw1tlMmLf8MDa+NttVjSa9IAAAAASUVORK5CYII=>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGMAAAAWCAYAAADU1CLnAAAC8UlEQVR4Xu2YjY3UMBCFUwMtUAMt0AIt0AItXAeUQAl0QAd0QAMUwOXT5Ytm39k577JZgeQnWXb8M3nzZux4d1kmJiYmJiYm/lt8WMuXrQbv1vJp60t8XMvXtXxf2uOA9Ywxh7navQX1fU9reX85vOPzWr5tBe4tsBYbP7Yani2M2DoNOPwnyu/lNRFI0s98HIHsz60taNPHGG3msoa114I1BAEbcMEutjK48kBsiu+vYA1rTSDqW22dCgUjYyhkYmYgwrZE/bW8ZJmgTV+FQexlYgu8n6SAW/ZV+yZS5dtai18pKs/0i1Fbp4IXVVItIGiLFOuqOLTTlk5mII/gGoJYge3KA0F5TtCn+ApakwbwXMUfsXU6RoIh0VYwdECn05bCphhHYBf5zanIYBD8noDyMJHy/QbjGlsJj2IL8BtctUKb7BPY2BOVCZ6NvJR2Eq+iV1RxeqLb33PoGrBT6pHXs0u/fFN0Yb98R2wlEF4NqL3YIC48SSbsU/vdowi/sRfBICvcrkzguW7NfyEYOImdnfj23LL7qGAIdagXAgKQehCQyoXni6MY8fODLVGN3ysYCMn4UaliC29DOTYi4KOCUTMeaL9eXNRCLj6zo7pIooqeN6JWMPKcr8FAVOf2Sl433akZCIDdFAG0gkEWVqSPI7Z6wLcMpPYrMhjg4uIAgby1JNFeduWOUfQKCWjrGrw6U5cXe+7kfL+oPHrvT59GbPXwN8EA+8nEYC8YZlOedSK3J+0kJYHMzBG4myrY0pL3XE7Q5w4loEfBcLeP2Orh1mBQX/BqOcyxkFuWvrpQJ2vW0s4feDjC2mvB9mWdjlqqg60fZSZO/Q7mDzyAf/WSMmqrhVuDgV74uOtFA0New2hDNL8PfkSZA8l0RviXAnOY2/rb4S1IulXSaROAurYrPO7YVdimbvk4YquixbPVp67pB/3wyMTfxauZkYA85LhmHgnMmEFLh8+AP6rgdpTFIz6O2roHHqHNxMTExD3wDK3HeaviEXmpAAAAAElFTkSuQmCC>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADsAAAAWCAYAAAB+F+RbAAABj0lEQVR4Xu2Wi01DMQxFMwMrMAMrsAIrsAIrdANGYAQ2YAM26AIMADl9teRe2fkUaJHIkSyqxHF8ncS8UhaLxeKfcF/tQQeP3FR7qvZa7bna4+n0WdyWLWYG+bAXe7b8hiHpXbX3ap/H3wpC38rmSwL44PvinQax9QggBnEj2Asf/LGu2CyQh6BmmVhEsTGi/Rj+sydsid+VttiPcrpflyxQBElkYonDnK+u+c/soWTrLfZVxHJ6xOI0jN8Ui0jm9mXbZ4goUEZLbASnPOMfkYkFGhPzmDWpJlmgiBmxVJ6q09SmrprQEgteMG/4ANfLupY3ktExjJavzIilOXmhrGVdz5SWWJ6O5W894wBHzIAa1dAxLNp4VCzXV0+U4mlBI1MysfhqN/6Rfz3GiFirtk+CsXPJxHJzuMJTRIEyemL5stKPCJ6Pjs2QieWmXk0soqInsS+x/yiZWAqr17hLFEghWet43vxafuu8WfQWW1hRI/NwsgjmLzl2b9CI2L8MjY+egFj/QRPyneaxWFyIL9+4nmIB0u/GAAAAAElFTkSuQmCC>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFoAAAAWCAYAAABAMosVAAACyUlEQVR4Xu2XYXHcMBBGjSEUiqEUQqEUQqEUyqAQCiEMwqAMQqAA2nvnezPrrytf3Lu5/tGb0VheS6vdT7IlL8tkMplMJpO/+HQqX9NYeD6V76fyuozbPS3rM9rQ9vP28SGIBx8/TuXb5b7jZVnbUL7EM6EvPt4uV+J8KIjHwAjze1kD6SCZX8vaniBJ6uelLtSx8Yw6belD36PQh5iYKMfDVwppHAhJcfwKPujr4uDK/S2L4DCIwcAMOhKaRDvB3pd1koQ6tooTdHQF4Yd+rmLiJL7qX1td6dSx8UzIKcXnvsv1IYyERqwMHmhbE6ee/RUjJ+ka+KKfq04/iC+IhS3BprAKXxcEcJ+T9DBGQptQJ7SJmlD2V6BM9Bq8AVUEJ7uuTCcjqXHYL8dX6MxJmGCeUYiDePhs4a/G1dkEHznumU4oqIJWtBtQl5D2zu9HIQlEzT1h5Be78Y4E1Z7xCpuwE+mGjKjsG+5V1BFZX3X/wE5sOe6ZUeD/U2j6UUg6gx75vYfQYOwIKkw0ttx3WAQ1Fu5HJ7Nh4PcS2tnfK7TpwI6f+nwU772FzpMONlZ5xQVR7+tJZ8MocAXNk0MndAZQha7fvVHZO3IROL5sQ52Vk3RCp1hHhM5J6vql0B4pjWPDSOjRqlBo6fobbAa2h+fmFMfx9JXjS41jNP4op8otQkv2PdMJBSTcDUjbuqLyOwUGm6LtoQgp4vvFpi/enmwD2Hyz/KamMI6Rb2nlFqFThw0joYEkq3MTeCk26rlJuHsfwQTr983jI7703/2cuCjqcav7OWFR5E9McovQxLn5PuusKxW/OQxAMqNA/SWmDW3/9VeXvk4uBZ+U9OXkcq31ChNDX04P5MuV+73VjGhVC+7rm2bp9NNGn06jqxAYSTBTmXDFgzpi7yVzDVYl4+ErV1WFdsRE2+7HQZz8PV/3or51k8lkcpQ/r4BGy8U+5gAAAAAASUVORK5CYII=>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAAWCAYAAACcy/8iAAACWklEQVR4Xu2WbVHkQBiEowELaMDCWcACFs4CDk7CScABDs4BBhBw7AP37Hb6JiGh+AFV6aqpJDPvV7/TM7vTdODAgS+K69O46cnCVU98V/w6jYd/z9+1JiD7pyfvposjHRvhx3RJ8LPW9oJYFMjgvXE7vdVkLTz5Zl7g9zxddo9YEKM21hj4PE1vdb9C9iYmIAZdBI4EZx4fg39EKvpalEUm7k/jbw3sUrqQeIxvasePmDwZ1D2rk90iWIJAkBYYQxbnBDYE3QOIkS8bSqHMpbKIS3wIMfDr5romJJqA3zkXAUiUTgBiWVR/C/yyMVtAt7vBEGUui3WH1oBS1gjTyLOUAQYjws7rTOAlwl38e1Ceja5jC2GPmYCckveozlTBYicCSszuLBFzvhuxBgrsWCqNAgVkkSODPKxRV8OLD8nnLT2TcgJJtiwhmo34TMKqJc+rDc4cEnaH3Bx2tYF/zvOeUvYyO38QKKVAA5izY1sIK8G1gR1E2WV2RHhxZuOxG11SKeER8EspQ75v91fSTBKQ5DbBrkhsVICEtwx3leT4OpaOVmOLoownaNDoKMwA0Qzc32Jp5/eCuNlgVUDzE+8RRjVn6U6XuDN7jAiUZwopP8W3O96J8MuLZguIgV92HdkR3xosdIlwKw3g2woZEjaIMlBeLQMakN3zZqXYPVAtnmHvjLxkRj8p/lanXaKlDPSZEYaYZAjG+4gEwZAZdp75pT/ra1CuXmRNVpCPHGm3lK+lnKAR/61RBE4QHclFsIYNtt3NPcg4eZQaW/O1lBPEYH3N5sCB74gX63PmXETAYuEAAAAASUVORK5CYII=>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFMAAAAWCAYAAAC8J6DfAAACqUlEQVR4Xu2X603DQBCEUwMtUAMt0AIt0AIt0AElUAId0AEd0AAFgL/IE01Gu75g8SMS90krO5fzPub2/DgcJpPJZDL5HbeLPSx2v9jNOsb5bnDytNjbYi+L3Z3/vQnJPC/2vh6VUPK42OtqJF/hc8in8yWI+V2YQJT8jxwFtX6sY5jOv2xOXp/GNeR9hIQZoADOSQBnpwkbIDpzKRw48jsXA9/EQHhM8Rx+UwjxiY0f5o0EBYnadZQaxSHW5+Hcv7TwBRG5UEK5HpFTRxNGhVBEJQrjQt2BiIJzL5545OBzGGNO+q8Yicm4dyQQL8eARqhE68SEU/Pg1IsHCbDVnRIkE+K3i4cYVRIulK7J7tkqwNkjJvOzbpHNBcNcJEg6lZiZgKPOyTkSRoWRWJWEx2VlOc/FGxawskdMbefq3py3KRjm0omm8RTZSdFyXD47P6PktN2qa5M9YvIQVA4Y4vJA8luNM8r3qsVky1cPs4o9YgKCaue45Q6BUb5XKybFXCok7BVTEEdPfPwQOzt0K98jEo32rsYrEYREy3fGSky2UNIlp9etS4WEPWJ2/pW/XvdEl+8ZlWhdxzrdnOxYFZpUcSmQbeeFVlsuGYmJMJlntcDAw6iq6yIxcZpFSSjvOtrei+yCSkw9Ien6KgnGfEfgnzzyydoV7SAW/jrh8ZudyPzcyqLytSXmybfuT14ERdIhDnNw5knlCzrk102+oIOepCpGXx5aWFm10BW6npxzMagv31+B+FyT81mY1AM6ManFPz9Pn3v8QWdV9yz+zxuziiBZxOJYJagF4+jnQt1cWXZ+BzGJj6Bcg7EQjGU+QA7MYb4+ZTlm7ZlPGvXm/fXoAIcIWgXfQovQ3bOARSAoInbb6y/ANzGIlQ3heK56QO2pfTKZ/A9+ANTGQHSjgpqeAAAAAElFTkSuQmCC>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADsAAAAZCAYAAACPQVaOAAAB9UlEQVR4Xu2Wf1EEMQyFqwELaMACFrBwFrCAAyQgAQc4wAEGEAD9ZnlM9l2yXfbuH2b6zXRub9ukeUl/bGuTyWTyTzj19trbc2+31ifu29LPuEfry/iyxhxbfLb1eOZ7snfesHlpdcwrbnp7b4sBzh96+/h5jhAojnmPDeOx43kE4wjszTsC+GdexiHQkWjiiyASO2K7s74zqBJOIlQPBwJBOPPKMCYLzEEkyWGeqgL0S1DmU31eBCAu+tBSgogs4zKWY/8vsItJqWActpUQEnCJWPl2HSuqQR6YquITYeerIkP+SUyWHPY/S/CoWMWX2f3CBJlY9gXvWc5QidL7LICI/FcBe38WdGbLitiyOSPLNiJjEq4lluAYTyUECdfJvhW4+rTc1fCtbTJEVdRJxj5GfAzqWmL1zGGnUzxeG3vEZnORLE9iCYK5HgiEE00J0KQS5dfMEbGnttjwCzHAo2JBd/Tw+nHcsf8XVcWdKBYIjOQiWKLhErGKxe/hFSwBBsb7j2zHfaxK+0TYEfQIF6vT098fFasrdFhZZUSDdEJ7hhAfg9AEsTIZ+MM2bgHNodNe7BHrcelrjr7hntXnIc705ZQJIECWH+O0x0fOlW21WEnmUYIlxBtVrPpi05bYBUuY5YyBH0IR+hijj4DJZDKZTP7AN40M6qLqZ87uAAAAAElFTkSuQmCC>

[image28]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAaCAYAAAAaAmTUAAAB7klEQVR4Xu2WDU0EQQyFRwMW0IAFLGABC1jAARKQgAMc4AADJwD2Y/clvUfnh8wehGS/pAnszHba13b2Sjk4+JdcL3blDyfYzR+O7ha73azHzWKvZafDN/A15ZPAcfCy2MNm/P9e1oAzOOytrAJkfJh5cE9hDTuFNeLB94/BKY6ySjyXdS0LmLVHf2jcl/V9gkUghwRn/J+hYGvqcwiBsC97ngUR4T3alr1U2UFA9y2Iidi8oikoxSG97L0FgHdH2kB7aFn8kFgEP1SvBgK01r9QeT3IDPV0hCB7IlA1ZhBUHZKKsN6qLlWTjyoEgnPmpQVJZ8lkKjsoGucElb01e9Ulzqw9z8DJSEBZv2tesgsjgqpxFtXWEpC12rwIBHEhvyG1e8PFYV5BkhhJxlWPrc3fvXkBndUkax1Hh3trjCQT5yUicUiiNy+wWzKaKx/0kWR8XoRalLb1ymUMJYMqbKp9X3jOetbTuhRayeC/5lvXdObbkaBN9EHKWoEgWWsdxnqmPKB+62OnS6U3L0Ayfp2nkBDlZjOBYSTHs94txz5PNs6YLF4cEc7ozQsQW81HCpVAAZSqtYaj31yXRO08GtMUIxWcAcGGWmwPSORSh1EVxPqVqgjmpnYRzIDfkQtidxjQkWEehWr8SSIHBwmfTACeksUI+GoAAAAASUVORK5CYII=>

[image29]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFEAAAAaCAYAAADPELCZAAAC0ElEQVR4Xu2YDVHEQAyFqwELaMACFrCABSzgAAlIwAEOcIABBEA/uMeEN0l39+iVn+k3s8O13W2St0n2jmna2dnZKTmfx5nf/ENc+I3vgiBX87g8jBY48Dh9FZHPqzt2Qojz3m8eAy9CjId53BwG189TLQhiPU0fwgPveD0M1m5JtM3AL4d7cQ6xitt53IXrYVj8MuWZxw7xTEJFeIZxB2e3FlHIX0TKNp8q88oRJEymQRMZzQwC4uGQp7vuZ+Li5E+JyAZeT7nPwKbzPEPVNwSLMJZlU4Q5CB1hbVYy8FMisqGUKFmmbPSM43m28bCUGCky5OJkqIdEELASvxIR5xCfdZRVBn7xjHk69ZnPdQsyTPNoUVmCVBsvKOkeW+/wcoy0milBZCJyXQmRiUiAOKiTH7sEFDOFlsKmSmSea03V4yKUr+Yoq1gveJaVeAS/W3M+0UlVCSEUQHRGDlZN2EXUyenzfR4+xWvZZl1PiXmWUboxRjKs6ocCAT0BSpRd3jMcXuoZW4kiXBwF46galD18zsT3ksxQP4xovd651A8FtoZFXCI26Gh8VMTKlkSUSKyJ2dRbxkCGZb2MCpL/nqkZq4voQYpREbURjt6v4BGNufr+yedW+YnYDyOsxwYC9vS6IRFVYplh4D7PM8M6bHpFrMpZJ6iynHm8E9v8bbWaCBmXEaupZ0Pc90V0EnofAQJQRlTwPCsfcEdkK84nOAKPvRZfGGSDTuhqoyI6ySt8s5bAb6+8RQiOQFhIgAyC4F7r1Gaei6wyj0MiYItAWUdQfHZnVXo+ql9Umb3Mb8SrMtWp3tEEZwiIIDJnM5jb80XdIaAsu/S1ye3rQFjKtLVQT96UnozthU2shDp2w0ap/qFyUhCwuwk3IOO8b4LaQOydp0CtbeQwWw12zwM/Fv1O1sHEoIdm5b8m2MWWt5JNIUt6Tr7fyshZsLOz8794A53EA+hjHcURAAAAAElFTkSuQmCC>

[image30]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAAAV0lEQVR4XmNgGAWjYPiCmegC1AArgVgZXZBSYArEO9EFqQFAQZCBLogMQLaeIAM/A+LPDFQMY1AQgAymWtgKAfF1KE01UMlAIDzJASBXUh1QLRxHwXADALG4FJ5+XBoHAAAAAElFTkSuQmCC>

[image31]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAAAWCAYAAAA2CDmeAAADFklEQVR4Xu2XgXHUMBBFXQMtUENaoAVaoIW0QAeUQAl0QAd0kAYoAPyCn/O9I9l3zk1myOnPaE6ytV+7+6WVb5oGBgYGBgYG/jd8XFoTD3N7XH7Bh7l9Xp6dAfbY/pjb17l92r5e8WVu35fGevcA8vFnafSbIGFOsv2eziUJUX9OL7YI01ocEX5NLzuFPs/uAcTbyskKBEEAEkn7Nu0cpwOQVBZLMRVZTjdArqGTvdP03nAoCELcAgqS5U5BLInOqeDZvZySNxMEmHjgzn+KZ/R7ghz5ATeBeDfVssr9xd3Ee34ZVyQHcyr2OOizrg3UO7gF5sLnnJYgayxMtoaTEPp18hngPBc75TCd7SXek9QDycHOZOivYA3EVizvqUwoz5hD8MyxVAs5SDDv+WWs/96RxkB8zME3uCj3CfmY54cS/SoIfq22LIyRNZ0AGL+mfECOwwaXOCsIya1cycP7ykuSjIMEZOkEvMdHQNyM62ZkzPMUVlGSi5jTf/OIAAmESUGYt+HiQb3E03kE84jvtRawz6SAs4JgA5e7F+h3DVJg41okB9ES2JtoeOGQWzDmeW4GOCuXOROcGsa1rMqXvjKufBtIzi9OQ3LUevCIGlBv8SNBFNd59Aka6C+JqhvFwH3fg7u+xmIC0zaFFlUQxz2+FETxnkFyCC6RglyDTEA+y4AMvKIG3QMBwfk0/bNhw7i769qJI343Ti+BWXpuLQhYSyIve4LU47YHF6pO+JnrpVVrrcg5LdQEWHtZy6+5lr2nqLXxADHC1StZlkN5wCWCuOvTDrQE2XAxqJ9s7L5WWdmDl2K9xNzJrtH6E2jQ9S5LwJN1HCQvYtQvOtZQpNY9g88mgz4xV/8Z11xcIgjArs5TeP0yH5tLHSMmQEofovyquBQETeLkIhiSVE8au8Y7IPt7wGl848TpZxXIUsYcW8ahf9jKkQIyVwF4z29yZBWwtZ4purl1PbitGGlP/FW4Z2cxqkf2WuCEXJaDFqz9CLF3MoQ8fmTswTLWAyLUqpBgLTh6vl+L9FnuxK3WGRgYGHgr/AUevkylUxLlRQAAAABJRU5ErkJggg==>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFEAAAAWCAYAAAC40nDiAAACPElEQVR4Xu2YgU3DMBBFPQMrMAMrsAIrdAVWYANGYAQ2YAM26AIMAHltf3X9ukvclgYh+UlW4nPsO/9zHLetDQaDwWBwY+6n8uzGwONUXqfy3uaf6+VuKi9uDBAP7R+HK89nbKbydihP1rYKCEOACPPd9gFnEOhX2z/PZAj483B/DhKG/oyHz4yHtm9XsrhSxx5RHIxL4R7bqiAKARJcJSJCMQGEjGzb/ErKkIj4xVclIm0uBvUYH2PQnzEF99ho+xMqEREvC4xnEfJSKhElhCeIehQNUbP+2DwBq1GJqGAzEbNJ9FL1V9IqERUHCcz6V/MQ9Kdo/yQp+KSu7Ymr2yLYPb4dlfNqsrK7uL1U47pYblfwVbzYs3EFfbQfMxYfS0RhP6Vwr48U3wqejVsGbfTx+HZUQVWT/a8igsaKpwxE8zFZhdGn6v6BO+IDiGqyUUScLBUXpRp3TRHjq4o/bH5Mij5VZ8Vugu1IFZQm63tDFLGnxFcClkT0yWQiMhnnHBEjEtGT5yIiXumjErFaGZUIvVT9NZkYOHgcVf9qHpFrRAQWlCd5R+Vce4UPzrPZSuilEsH3IeGvIJt71h8bbXNcI2Km0ZFKRNi204E00XRf6KQSEfxgDSQsnv+yg7US7luHc6mI8nnyYVHHrET0M4zBdBy49EDrflRi8CQJHxwxsHOl7vsySdSvqXg/h/tlTkqoCnUJ7THig/al1Z6iA6h+Jq4BCWMyvjoi+uOE2JZW4G+gRK6lwWAwuD0/0YYMkH91EZoAAAAASUVORK5CYII=>

[image33]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAZCAYAAACsGgdbAAABZUlEQVR4Xu2WW3ECQRBFR0MsRAMWYgELWMACDpAQCTjAQRxgAAEwp3bv1t2mO/lgv1JzqqYy6enH7YbMpLXBYLAJn30do9H46uvc16XVfh9tOsMH3936eOHQ1/e89uHsBQqf2pT00dd1fbxA0nub/BFC8p95L9hj44w9vsQQ6yiWobAUU0IiOqfjSiQFs2K3NjUo2GNz1JyaoR51ECfYY+PsTyqRFMqS4Oui2Md4iVKDTIzfI9h+naaoRCpxJlIFNY0YL5GaOI1UImNsSuXoYhzZERLFCNmVt6qBPavxQpVgiJzZTKRfN253kdyNTiaSKyfytkimIzFOnHAWHyccY0QWm1I58iJUIn0q7GO8ROpVYdKVyPgppFQi4dbW3zc+evwPZmPvFzdQmFiRXdwagl/wK9RpthxeJAQglKTVU6YnDx98iYnvt5rhp+83gQmRTM9oBWdqJv6xCf0zQ75ygoPB4L/yBDKjo77UzZHwAAAAAElFTkSuQmCC>

[image34]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAZCAYAAACsGgdbAAABkElEQVR4Xu2VbU0FMRBFqwELaMACFrDwLGABB0hAAg5wgINnAAHQw+7d3F6mhAR+vJCepNnutJ25nX61tlgsfsV1Lw+9vOzf27H5APtjL8+93EebuGpbG33oezM2H5x6edrLXbR9ASeIoyMicP7eNicO/29t64MQnL/udUEdG23U6cuY9KWxJIeiMVPObcte2hCKAyBgFSzHUsfmaHKaDMLdN1DHNlvBz0aKLwvBsEkAgSonrICLoo7NkShNkIzxn2CbZlN7zJctRcpxJVIBlY2ZSPnSKiXV2G/RvpQoF+PITr8UI2SXgJkY7FWMEpY9U39RIv10OhclkmVOgSAxvm/d7iLZ404lkkQkPxKpi1VwELQndZD0LzLDVZYywzlGVGMHmP0pbLwasnHRz0R6VqhnIInUq0KsmchchQOEcNni3IteF3Fu435j6XHsk5Mv3xYEZqyoLm4lwS/4Ae2FqjicegQgFKfVAQM9efShL2Py/dZk+Hr9TyBDOGMrZGCHNk0mD5sga9pS0wwuFov/ygfBGq8lkr4ZsQAAAABJRU5ErkJggg==>

[image35]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAZCAYAAADJ9/UkAAABFElEQVR4Xu2UUQ0CMQyGqwELaMACFrBwFrCAAyQgAQc4wAEGEAD9Mkq6Xnsh4YEH9iVNmq7t342jIoPBj1mr7WPQsVU7qp2lzltJOyOH3E1/3EPDg7Tkh9qlP34zqd2l5SNwUru+fAOfGGf45FJDbQoJTMqElTiNsiY3aYMb+MQ8NrQfMqUSpwFnDOoh14vhx3pqqI2Dz6jEecZKnDjwvWT1Ju5fKCUrBi/isTgClYjFs74dVdIQj19sJs5/2/O1OLcxEU98kay+epEZWTHspBZnqRj4sd7E6bFIJQ436afnJyB/cjH8uFD4GahNscky87ABacwA3MLWaMTWLjnkUrO43z+FG3E7W8cVnNmQ8SMdDP6MJ8CTdyyC4JWrAAAAAElFTkSuQmCC>

[image36]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAZCAYAAADJ9/UkAAABVUlEQVR4Xu2UURHCMBBEowELaMACFrBQC1jAARKQgAMc4AADCIA82u1srmn5Aj7Im8mQXO6yl+uRlBqNH7HKY5/HOY9DHttyewT7MfV++Nfws/DdlNslbF7y2A1rAh+pT8Lp8rinPgEETnlch7lgjo095vgSQ2wVHBGTOLBmrIc1B9UOuaUySebYHCXtSY5I3MsocZWMA1jHz0HFXIw5NocYYmPiI/5duC3OfqgSrIljB8XNicfPOIHS0CiUyRNyEUd2BOZEZI9JFdCZKmPs5I+LC27MzSm1+Jo4UHoCVAGJxI6tiVNBZ1GcTGO2rD1A66WGg5rIXEXGjXiwulu34A2IPoAQj4pgPifu78gLPR6U2aHpCPCOx+bZE4tPZzbm8UHhAsRWISM2ceJw/dVipmpEfNjTMxrRs4sPvvFvO4FM5cxvbCyBndvRiEsHsvfurEbjT3gCXxCE3YVmWiwAAAAASUVORK5CYII=>

[image37]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAZCAYAAADAHFVeAAABOklEQVR4Xu2UURHCMBBEowELaMACFrCABSzgAAlIwAEOcIABBEAezcJxXJv0Cz7yZm7aZnLZy+aalDo/YpFj7QcDln5gLtsc5xz78kQ44piGOSGrHLvyBBbZlDHB2C29d4XwNcehjBHkUMSlzAlh4t0FC5MseGdcIM7CKpSdUABCKjoEMRYnmaBa7zmLWTFgrkWikyDmEz1UPSVGcbU1nrSIsRhissifqSytghhe00U64MgOnYkaQd3YZJ9AjM7SObEI34h71BAS4tu6wjfCdtcfkDjWEDVrbPfxpEiKn7VbiU0l+B2c0tDJIuwDqqP1LTUxbx/4+bx/XW36iS0Ssz+2BSFvfZNY1LZ4P3btePsEOVaMBvMFva4e/Gay2j+6aCP7hHKBXM5wFCwLt24IqzVQMIVGbnU6f8ID0sFcm9Db9R0AAAAASUVORK5CYII=>

[image38]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABb0lEQVR4Xu2WUVUDMRBFR0MtoKEWagELWMBCHSABCTjAAQ4wUAGQe7avzA6TzLb0g4/cc+ZsSTKTl7xkF7PJpGTf4iE2Bqr+u7Jr8d7ipcVbi6d19wWEf9oyfhOs4jk2nqH90X6KUZw2nuJoizDB5BJ4OAdjTrbUGqLBFPiydWEP7fT7IMev+sOWWoKdQwBBO8FiyCtBmFZeCWNinj2byPfC+E19wSKosdlCUQnzk2Rg3UiYdvBq/irs1dY2+VrkbrIwoxLGinkq/MEHWcXRQKTsvtlCUQnzNjE5tysThyC/u4j0FpJLrZjbZSQsK6KbOQJBfgwiCeox16ZdHAnL0GujR7RQN19/I5rdK+kJowB9sUgljJ3ylmJfHJ/N94ueMBXMhLEjGSyGy+K5u7DsqnPAGZ+9l6KFQjmCTyDnLYVJZUkMD0V1M9kJbqReB5FooUAoeeqLL+Cb0UceQb1/Wzjg0UIP/fq0jcZNJpN/wzcViXlu+3GzfAAAAABJRU5ErkJggg==>

[image39]: <data:image/png;base64,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>

[image40]: <data:image/png;base64,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>

[image41]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABkklEQVR4Xu2V0U0DMRBEXUNaoIa0kBZogRZoIR1QAiWkAzqgAxqgAPDjmGgy8ubuJD748JNWSu7s9Yx37WttMlnl2OMhHwZr7/+UQ4+3Hi89Lj2ebl9fQfhHW8avwqDntiQkcTrSQqdBsBCc2yJMsHjOY8xnj0cbVyIHTEIQApnsfN0JFof3tuQQGEQAwXNC5ldhpyRK4JoFcQgI16IeLIwBlYQ5noffygGMI8+mEjKZhF46HOKs+i8w4AunwRSmHdwEyVQ2dsYTCUSnS4S6CHhtt2XyfiPvphICi7FbOkkqD2LV0CNU2kSlQjQidSp3lRBwoQb2Lc7eSTBSXQXM0SkUiPT82u3SvAtzSMKzUV9pTiU6IZeXEJEEojA4zEPvqJSOFh/1BEnzKqnIEiLGTVWH6oe9whCV4yuY7yXVDeCUuZicO1CVstrhEeSgV51dwrQ73ohV82tsmeyXLKHgULgwjNIaJboi/DYfnZh7JXayhAKh5Na7vICH6BuJq3Tq8D4/8A6GsoSO7kDdnZPJ5N/zDbLsgvSetvTdAAAAAElFTkSuQmCC>