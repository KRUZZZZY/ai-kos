# **Technical Optimization Report for AI-KOS: Streamlining Architecture and Reducing Workload via Open-Source Consolidation**

The architectural design of AI-KOS Version 1.2.0 reflects a transition toward a local-first cognitive operating system.1 By targeting consumer-grade hardware—specifically the NVIDIA RTX 5070 Ti with 16 GB of VRAM—and hosting models like Qwen3, DeepSeek, and Mistral via Ollama, the system prioritizes offline data sovereignty and low-latency execution.1 The system architecture manages data flow across distinct cognitive layers, beginning with raw capture in the information layer (inbox/), moving through episodic and session tracking in the memory layer (episodes/, backlog/), and culminating in structured semantic storage in the knowledge layer (knowledge/ utilizing the Open Knowledge Format v0.1).1  
However, the proposed deployment of twelve independent microservices introduces severe operational challenges for consumer hardware.1 Running twelve distinct runtimes, web frameworks, and inter-service communication layers over REST and Redis queues (redis://localhost:6379) creates substantial CPU context-switching overhead, memory fragmentation, and network serialization bottlenecks.1 To mitigate this resource strain and dramatically reduce the custom development workload, the core services can be consolidated. Leveraging existing, mature open-source software (OSS) frameworks allows the engineering team to replace extensive custom code with standardized, highly optimized, and hardware-aware components.

## **Consolidating the Retrieval and Embedding Pipeline**

The AI-KOS specification allocates retrieval operations across three independent microservices: retrieval-service (Port 8003), embedding-service (Port 8010), and sparse-index-service (Port 8011).1 In a local-first environment, this design forces large vector payloads to undergo multiple serialization and deserialization cycles over local loopback interfaces, severely degrading query performance.1

### **Native In-Database Vector and Index Generation**

The custom embedding-service and sparse-index-service can be entirely eliminated by deploying Qdrant Alloy or leveraging Qdrant's native FastEmbed integration.2 FastEmbed runs in-process within the Qdrant client or database node, combining document vectorization and insertion into a single execution step.3 This native capability supports the concurrent generation of both dense and sparse representations without external dependencies.4  
For dense semantic indexing, FastEmbed natively supports highly efficient models such as BAAI/bge-small-en-v1.5 or nomic-embed-text.1 Simultaneously, the sparse indexing layer can be offloaded to FastEmbed's implementations of BM25 or SPLADE (prithivida/Splade\_PP\_en\_v1), which execute token-level lexical analysis directly within the same database engine.2  
Furthermore, late-interaction architectures like ColBERT can be incorporated via FastEmbed's LateInteractionTextEmbedding (e.g., answerdotai/answerai-colbert-small-v1) to perform token-level relevance calculations.2 In this configuration, instead of storing a single static vector, the database stores fine-grained 128-dimension token vectors for up to 4,000 keywords per document, drastically improving retrieval precision while avoiding custom serialization logic.5

| Vector Type | Target Representation | Typical Dimensionality | Operational Role in AI-KOS |
| :---- | :---- | :---- | :---- |
| **Dense (Semantic)** | BAAI/bge-small-en-v1.5 | 384 dimensions 2 | Captures conceptual similarity and broader semantic context.2 |
| **Sparse (Lexical)** | Qdrant/bm25 or SPLADE | Unbounded / Vocabulary Map 4 | Guarantees exact keyword matching and term precision.2 |
| **Late Interaction** | answerai-colbert-small-v1 | ![][image1] dimensions per token 2 | Performs fine-grained token-level reranking of candidates.2 |

### **Executing Multi-Stage Hybrid Queries**

Custom retrieval coordination can be replaced by Qdrant’s native Query API (available in v1.10.0 and later), which introduces sub-request execution through the prefetch parameter.6 The database engine independently coordinates multi-stage queries, prefetching candidate documents from both dense and sparse vector spaces, and subsequently applying a mathematical fusion algorithm over the combined candidate set.6  
To reconcile the fundamentally different scoring mechanics of dense vectors (bounded cosine similarities) and sparse vectors (unbounded BM25 scores), the system can natively configure Reciprocal Rank Fusion (RRF) or Distribution-Based Score Fusion (DBSF).4 The mathematical execution of RRF inside the database engine is structured as follows 6:  
![][image2]  
Where:

* ![][image3] represents the unified set of candidate documents retrieved across all prefetch steps.6  
* ![][image4] represents the set of retrieval models, specifically the dense semantic vector search and the sparse lexical search.6  
* ![][image5] represents the zero-based ordinal rank of document ![][image6] within the results returned by retrieval model ![][image7].6  
* ![][image8] is a smoothing constant (defaulting to ![][image9]) designed to minimize the disproportionate influence of high rank positions.6  
* ![][image10] represents the weight assigned to retrieval model ![][image7], defaulting to ![][image11].6

When the system operates without an evaluation dataset, weights should remain at their default values to ensure balanced scoring.6 However, the development team can utilize the tune\_rrf\_weights grid-search framework within a validation split to dynamically tune weights based on local dataset characteristics, ensuring that the consensus between dense and sparse results is mathematically preserved.4 This advanced capability renders custom ranking and fusion code in the retrieval-service redundant.1

## **Replacing Custom Ingestion Frameworks**

The ingestion-service (Port 8001\) is designed to handle capture, triage, priority scoring, and document parsing.1 The current specification lists the open-source Docling library as the primary parsing utility.1 While Docling provides layout-aware document conversion, building custom orchestration, document partitioning, and metadata mapping layers represents a significant development hurdle.7

### **Docling vs. LlamaParse in Local-First Contexts**

When evaluating the document processing layer, comparing open-source Docling against commercial cloud-based options like LlamaParse highlights key structural tradeoffs.9

| Architectural Dimension | Docling (Open Source) | LlamaParse (Proprietary Cloud) |
| :---- | :---- | :---- |
| **Deployment Model** | 100% Local / Self-hosted on commodity hardware.10 | Managed cloud infrastructure.9 |
| **Licensing** | Permissive open-source license.10 | Commercial tiering based on volume.9 |
| **Hardware Targets** | Runs locally; leverages local CPU/GPU.10 | Offloaded to managed cloud clusters.9 |
| **Layout Analysis** | Built-in layout analysis and table extraction.7 | Cloud-based agentic OCR and layout parsing.9 |
| **Data Sovereignty** | Absolute; no external data transmission.7 | Requires uploading files to external APIs.9 |

Given that AI-KOS v1.2 strictly prioritizes a local-first model architecture targeting local GPU hardware (RTX 5070 Ti) and demotes cloud APIs to emergency fallbacks, Docling is the most appropriate option.1 Docling’s native layout analysis, OCR engine fallbacks, table recognition, and hierarchical Markdown output run entirely within local computing environments, matching the data sovereignty requirements of the system.7

### **Implementing LlamaIndex and Docling Integration**

To avoid writing custom document partitioning and node assembly code, the engineering team can utilize standard integration libraries.10 The llama-index-readers-docling and llama-index-node-parser-docling packages allow the system to ingest raw data directly into the LlamaIndex framework.10  
Using the DoclingReader with a JSON export type, paired with the DoclingNodeParser, allows the system to map unstructured files directly to structured "Nodes".10 This pipeline preserves headers, section boundaries, and nested table hierarchies while appending document-level metadata—such as page numbers, bounding boxes, and document paths—directly to each node.8  
For standard text files, the MarkdownNodeParser can partition Markdown files exported by Docling, maintaining the semantic integrity of document sections and headers.8 Additionally, this structured ingestion pipeline can generate standard JSONL datasets to support downstream fine-tuning frameworks like Unsloth or Llama Factory.8  
By deploying a Celery-based job queue utilizing task chains and chords, the system can parallelize file parsing and node generation without requiring custom scheduling code.8

## **Standardizing Agent State and Governance**

The planned session-service (Port 8008\) and governance-service (Port 8004\) are tasked with maintaining conversational context, tracking session states, and orchestrating the Dual-Agent Quality Control (QC) pipeline.1 The governance model relies on a Proposer ![][image12] Critic ![][image12] Comparator ![][image12] Commit execution flow.1 Coding this state-machine, transaction boundary layer, and serialization mechanism from scratch requires substantial effort and is highly error-prone.12

### **LangGraph State Persistence Infrastructure**

These state-management requirements can be implemented using the **LangGraph persistence framework**.12 LangGraph models multi-agent workflows as directed graphs where nodes are standard functions and state transitions are explicitly typed and tracked.13 Rather than constructing a custom database interaction layer, the system can utilize LangGraph's dual persistence architecture to manage execution states 14:

| Component | Scope | Persistence Target | Cognitive Use-Case in AI-KOS |
| :---- | :---- | :---- | :---- |
| **Checkpointer** | Single thread.14 | MemorySaver, SqliteSaver, or PostgresSaver.13 | Manages conversation continuity, fault tolerance, and execution recovery.12 |
| **Store** | Across threads.14 | Application-defined key-value storage.14 | Tracks user preferences, long-term facts, and shared consolidated knowledge.14 |

Using checkpointers allows the state-machine to automatically serialize the entire execution graph after every node execution.12 If a local process terminates unexpectedly, the system queries the checkpointer, hydrates the exact state of the execution graph, and resumes processing without loss of context.12

### **Preventing State Corruption and Orchestrating Human Approval**

To manage state updates across parallel branches (such as when multiple Critic agents evaluate a proposal concurrently), LangGraph uses Annotated Reducers.13 Applying Annotated\[list, add\] to shared state keys prevents race conditions by appending partial updates rather than overwriting existing values.13  
For the governance-service QC comparison loop, LangGraph's native human-in-the-loop features provide a structured way to pause execution.1 By configuring interrupt\_before on the comparison or commit nodes, the runtime automatically serializes the active state and pauses the thread.13  
The system can then wait for a human user or automated process to inspect the comparison, update the state via graph.update\_state(), and resume execution with graph.invoke(None, config).13 This native state tracking replaces the need for custom session recovery, database transaction coordination, or manual polling loops inside the session-service and governance-service.1

## **Model Routing, Resource Management, and Failover**

The router-service (Port 8005\) is designed to handle model routing and provide fallback capabilities when the local RTX 5070 Ti is over-allocated, routing requests to emergency cloud APIs (Anthropic/OpenAI).1 Developing custom rate-limiting, failure-detection, and payload-translation code represents a significant engineering challenge.15

### **Leveraging Olla for Local Backend Management**

For managing local inference, **Olla** offers a high-performance, lightweight solution.15 Written in Go, Olla operates with a minimal memory footprint (\~50MB RAM), making it highly suitable for resource-constrained environments.15 Olla is designed to coordinate local backends, including Ollama, LM Studio, and vLLM.15  
Olla introduces Prefix-Hash Routing to support multi-turn conversations.15 By hashing the message prefix of a conversation, Olla consistently routes subsequent turns to the same local backend GPU instance.15 This maintains a warm Key-Value (KV) cache, avoiding the computational cost of re-processing long contexts on subsequent turns.15  
Additionally, Olla supports declarative priorities and circuit-breaker failover.15 If a local model fails to load or experiences a significant latency spike (e.g., during initial model loading), Olla's circuit breaker trips and reroutes traffic before user requests fail.15

### **Integrating LiteLLM for Cloud Translation and Budgets**

While Olla optimizes local execution, **LiteLLM** can be deployed behind it to manage external cloud fallbacks.15 LiteLLM provides a unified Python SDK and Proxy Server that translates standard OpenAI-compatible API payloads to over 100 cloud providers.15  
LiteLLM includes native fallback arrays, allowing developers to define prioritized routing chains.16 In production, LiteLLM can use Redis to track server cooldowns, request latency, and TPM/RPM limits, ensuring that requests failover gracefully if API quotas are exhausted.16

                   
                            │  
                            ▼  
                    \[ Olla Gateway \] ───( Warm KV Cache / Prefix Hash )  
                            │  
             ┌──────────────┴──────────────┐  
             ▼                             ▼  
     \[ Local Ollama \]             \[ LiteLLM Proxy \]  
   (Qwen3/DeepSeek/Mistral)        (Cloud Fallback Array)  
             │                             │  
            ┌─────────┴─────────┐  
                                 ▼                   ▼  
                            \[ Anthropic \]       \[ OpenAI \]

Combining these two gateways allows the system to route local inference through Olla to preserve the KV cache, while utilizing LiteLLM as an upstream target to manage cloud-based fallbacks.15 This dual-proxy model provides robust routing and budget controls without requiring custom translation or failover code in the router-service.1

## **Integrating the Knowledge Graph and Obsidian Vault**

The graph-service (Port 8009\) is designed to synchronize consolidated knowledge articles with a local Obsidian vault and traverse the resulting semantic graph.1 Writing custom filesystem watchers, Markdown frontmatter parsers, and graph-traversal algorithms is complex and prone to synchronization issues.

### **Exposing Vault Capabilities via Obsidian Local REST API**

Instead of custom syncing code, the graph-service can utilize the **Obsidian Local REST API** community plugin.1 This plugin runs locally, exposing a secure, HTTPS-encrypted, and authenticated REST interface directly into the active Obsidian vault.19  
The Local REST API supports full CRUD operations on all files and directories, and enables surgical content patching.19 Using targeted HTTP requests, agents can modify specific headings, block references, or YAML frontmatter keys without rewriting the entire file.19  
Additionally, the plugin provides search capabilities, allowing agents to run structured JsonLogic or Dataview queries over note metadata, tags, and content.19 This interface simplifies note querying and relational analysis.19

### **Transitioning to Model Context Protocol (MCP)**

To integrate these capabilities into the agent workflows, the system can wrap the REST API in an MCP server (such as mcp-obsidian or obsidian-local-rest-api-mcp).19 This protocol translates the vault’s REST endpoints into structured, schema-validated tools that can be executed directly by LLMs.20

                
                            │  
                            ▼ (Tool Invocation Signature)  
               
                            │  
                            ▼ (Local HTTPS REST Calls)  
               
                            │  
                            ▼ (Surgical Patch / Query)  
                 \[ Local Obsidian Vault \]

Deploying an MCP server allows agents to list directory contents, perform text searches, retrieve files, and append content through standardized tool-invocation signatures.20 This standard interface replaces custom synchronization, parsing, and graph-traversal code within the graph-service.1

## **Complete Service Migration and Workload Reduction Matrix**

The table below outlines the recommended transition from the custom-coded microservice registry specified in AI-KOS v1.2 to existing open-source frameworks, detailing the estimated workload reduction and architectural benefits.1

| Original Service Registry | Planned Port | Primary Responsibilities | Recommended Open-Source Framework / Replacement | Workload & Architectural Impact |
| :---- | :---- | :---- | :---- | :---- |
| **ingestion-service** | 8001 | File capture, validation, scoring, and layout parsing.1 | LlamaIndex \+ DoclingReader.10 | **High Workload Reduction:** Eliminates custom layout analysis, parsing pipelines, and node generation code.10 |
| **consolidation-service** | 8002 | Merging backlog items into consolidated OKF articles.1 | LangGraph State Graph.12 | **Medium Workload Reduction:** Replaces custom process orchestration with a structured, persistent state machine.12 |
| **retrieval-service** | 8003 | Coordinating dense/sparse hybrid search and fusion.1 | Qdrant Native Query API (v1.10+).6 | **High Workload Reduction:** Replaces custom vector retrieval and RRF scoring algorithms with in-database execution.6 |
| **governance-service** | 8004 | Proposer ![][image12] Critic ![][image12] Comparator pipeline.1 | LangGraph Human-in-the-Loop (interrupt\_before).13 | **High Workload Reduction:** Replaces custom state tracking, pause/resume mechanisms, and approval queues.13 |
| **router-service** | 8005 | Task routing to local models and cloud fallbacks.1 | Olla (local) \+ LiteLLM (cloud) Proxy.15 | **High Workload Reduction:** Replaces custom model translation, KV-cache routing, and failure-detection code.15 |
| **scheduler-service** | 8006 | Executing scheduled routines and decay cycles.1 | Celery task schedules using Redis.8 | **Low Workload Reduction:** Replaces custom cron schedulers with standard task execution libraries.8 |
| **health-service** | 8007 | System dashboard and performance monitoring.1 | LiteLLM Admin Portal \+ Prometheus.15 | **Medium Workload Reduction:** Replaces custom performance dashboard code with standard observability tools.15 |
| **session-service** | 8008 | Conversational context and state management.1 | LangGraph Checkpointers and Stores.14 | **High Workload Reduction:** Replaces custom context databases, serialization logic, and session-state recovery.12 |
| **graph-service** | 8009 | Syncing notes and traversing the knowledge graph.1 | Obsidian Local REST API \+ MCP Server.19 | **High Workload Reduction:** Replaces custom filesystem syncing and Markdown parsing with standardized API tools.19 |
| **embedding-service** | 8010 | Generating dense vector representations.1 | FastEmbed running inside Qdrant.3 | **Service Eliminated:** Vector generation runs in-process with the database, reducing network and memory overhead.3 |
| **sparse-index-service** | 8011 | Encoding text into sparse vectors.1 | FastEmbed running inside Qdrant.2 | **Service Eliminated:** Sparse vector generation runs in-process with the database, reducing network and memory overhead.2 |
| **ci-service** | 8012 | Schema verification and repository access control.1 | Pydantic validation inside LlamaIndex.1 | **Low Workload Reduction:** Integrates validation loops directly into the standard data-entry pipelines.1 |

## **Strategic Recommendations and Integration Plan**

The architectural analysis indicates that consolidation of the microservices registry is the most viable path to ensure optimal execution of the AI-KOS operating system on consumer-grade hardware.1 This transition can be guided by several strategic milestones:

* **Consolidate the Vector and Embedding Engines:** The planned embedding-service and sparse-index-service should be decommissioned.1 By configuring Qdrant to run with FastEmbed, the database engine can natively generate and store dense, sparse, and late-interaction (ColBERT) vectors in a single step, reducing VRAM usage and loopback network latency.2  
* **Implement Unified Routing and Failover:** The custom routing logic in the router-service should be replaced with Olla and LiteLLM.1 Olla should manage the local Ollama instances on the RTX 5070 Ti, using prefix-hash routing to optimize KV-cache warming.1 Olla's circuit breaker can then route overflow requests directly to LiteLLM, which acts as the gateway to cloud-based backup models.15  
* **Standardize Ingestion via LlamaIndex and Docling:** The ingestion-service should utilize the native LlamaIndex integration for Docling.1 This replaces custom file parsing and node assembly with standardized reader and parser classes, generating structured nodes complete with rich layout and hierarchy metadata.10  
* **Rebuild Sessions and Governance on LangGraph:** The state-management logic in the session-service and the multi-agent comparison loops in the governance-service should be migrated to LangGraph.1 This transition allows the system to rely on native database checkpointers and stores to manage state serialization, thread isolation, and human-in-the-loop validation.13  
* **Deploy Obsidian Local REST API and MCP:** The custom filesystem syncing in the graph-service should be replaced with the Obsidian Local REST API and its associated MCP server.1 This configures the local vault as a set of structured, schema-validated tools, allowing agents to perform surgical file updates and semantic queries via standardized interface calls.19

Adopting these existing, highly optimized frameworks significantly reduces the custom coding footprint, allowing development to focus on refining the system's core cognitive workflows and agent coordination strategies.1

#### **Works cited**

1. AI-KOS-Technical-Specification-v1\_2.md  
2. Qdrant Alloy \- GitHub, accessed on June 25, 2026, [https://github.com/qdrant/qdrant-alloy](https://github.com/qdrant/qdrant-alloy)  
3. Build a Hybrid Search API \- Qdrant, accessed on June 25, 2026, [https://qdrant.tech/documentation/tutorials-develop/hybrid-search-fastembed/](https://qdrant.tech/documentation/tutorials-develop/hybrid-search-fastembed/)  
4. Demo: Implementing a Hybrid Search System \- Qdrant, accessed on June 25, 2026, [https://qdrant.tech/course/essentials/day-3/hybrid-search-demo/](https://qdrant.tech/course/essentials/day-3/hybrid-search-demo/)  
5. Qdrant Hybrid Search Tutorial \- YouTube, accessed on June 25, 2026, [https://www.youtube.com/watch?v=QuDGpV9Nhzc](https://www.youtube.com/watch?v=QuDGpV9Nhzc)  
6. Hybrid Queries \- Qdrant, accessed on June 25, 2026, [https://qdrant.tech/documentation/search/hybrid-queries/](https://qdrant.tech/documentation/search/hybrid-queries/)  
7. Understanding Docling for Structured Document Processing \- LlamaIndex, accessed on June 25, 2026, [https://www.llamaindex.ai/glossary/what-is-docling](https://www.llamaindex.ai/glossary/what-is-docling)  
8. Dataset Generation using Docling and LlamaIndex \- Intel Community, accessed on June 25, 2026, [https://community.intel.com/t5/Blogs/Tech-Innovation/Artificial-Intelligence-AI/Dataset-Generation-using-Docling-and-LlamaIndex/post/1746014](https://community.intel.com/t5/Blogs/Tech-Innovation/Artificial-Intelligence-AI/Dataset-Generation-using-Docling-and-LlamaIndex/post/1746014)  
9. LlamaParse vs. Docling: Which platform delivers better document parsing? \- LlamaIndex, accessed on June 25, 2026, [https://www.llamaindex.ai/compare/llamaparse-vs-docling](https://www.llamaindex.ai/compare/llamaparse-vs-docling)  
10. Docling Reader | Developer Documentation \- LlamaParse, accessed on June 25, 2026, [https://developers.llamaindex.ai/python/examples/data\_connectors/doclingreaderdemo/](https://developers.llamaindex.ai/python/examples/data_connectors/doclingreaderdemo/)  
11. Unleashing the Power of Your Data: Semi-Structured Data RAG with Docling and LlamaIndex | by Fahaam Shawl | Medium, accessed on June 25, 2026, [https://medium.com/@shawlfahaam/unleashing-the-power-of-your-data-semi-structured-data-rag-with-docling-and-llamaindex-ce15d550f2f1](https://medium.com/@shawlfahaam/unleashing-the-power-of-your-data-semi-structured-data-rag-with-docling-and-llamaindex-ce15d550f2f1)  
12. Deploying LangGraph: From Local Prototype to Production-Ready Microservice, accessed on June 25, 2026, [https://programmingcentral.hashnode.dev/deploying-langgraph-from-local-prototype-to-production-ready-microservice](https://programmingcentral.hashnode.dev/deploying-langgraph-from-local-prototype-to-production-ready-microservice)  
13. LangGraph in Production: Building Stateful AI Agents \- Kalvium Labs, accessed on June 25, 2026, [https://www.kalviumlabs.ai/blog/langgraph-in-production-stateful-multi-step-agents/](https://www.kalviumlabs.ai/blog/langgraph-in-production-stateful-multi-step-agents/)  
14. Persistence \- Docs by LangChain, accessed on June 25, 2026, [https://docs.langchain.com/oss/python/langgraph/persistence](https://docs.langchain.com/oss/python/langgraph/persistence)  
15. Olla vs LiteLLM \- Choosing an LLM Proxy \- TensorFoundry, accessed on June 25, 2026, [https://tensorfoundry.io/blog/olla-vs-litellm](https://tensorfoundry.io/blog/olla-vs-litellm)  
16. Multi-provider LLM fallback in Python — rolling your own ProviderPool vs existing solutions, accessed on June 25, 2026, [https://www.reddit.com/r/Python/comments/1t0liz0/multiprovider\_llm\_fallback\_in\_python\_rolling\_your/](https://www.reddit.com/r/Python/comments/1t0liz0/multiprovider_llm_fallback_in_python_rolling_your/)  
17. LiteLLM \- Getting Started | liteLLM, accessed on June 25, 2026, [https://docs.litellm.ai/](https://docs.litellm.ai/)  
18. Load Balancing \- Router \- LiteLLM, accessed on June 25, 2026, [https://docs.litellm.ai/docs/routing](https://docs.litellm.ai/docs/routing)  
19. GitHub \- coddingtonbear/obsidian-local-rest-api: A secure REST API and Model Context Protocol (MCP) server for your vault., accessed on June 25, 2026, [https://github.com/coddingtonbear/obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api)  
20. MarkusPfundstein/mcp-obsidian: MCP server that interacts with Obsidian via the Obsidian rest API community plugin \- GitHub, accessed on June 25, 2026, [https://github.com/MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian)  
21. evelynkyl/obsidian\_python\_api: A simple Python wrapper of Obsidian Local REST API: https://coddingtonbear.github.io/obsidian-local-rest-api/ · GitHub \- GitHub, accessed on June 25, 2026, [https://github.com/evelynkyl/obsidian\_python\_api](https://github.com/evelynkyl/obsidian_python_api)  
22. Obsidian Local REST API MCP Server, accessed on June 25, 2026, [https://mcpservers.org/servers/j-shelfwood/obsidian-local-rest-api-mcp](https://mcpservers.org/servers/j-shelfwood/obsidian-local-rest-api-mcp)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAWCAYAAAAxSueLAAABJklEQVR4Xu2UaxHCQAyETwMW0IAFLGABC1jAARKQgAMc4AADFQD3td1Omst1uM7wrzuTgctrm720KW3Y0Ih9tot3Gpyz3UcjbzcP98BH7JHtlu1ogxyuY/CT7WmDBhCQRz6kXbZXmhPyn3ri5GHkTAPg4HBIdTKK32mY3PrI5yEE+jCNBTXkFaiRMRExprfAZxtR68lAExlTSx4LTwYRZ34l7ykNUhaokUWIZEcy7hI/siMrcXIL+OIlICmNfSNLKOmjrf2ZTNvoiWiq7cNEulpGCCIiQC3LJDAlvqYFESDgLiyRlkYrHkkW9lwi01P6ZpJIC+PjwE47oUamu8CIy3QWOPvG1KJGD74g2hxvgl7qyGxzyay7w3gASf0X6HsLSSTrhnX4AguwbkNFw2jeAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAZCAYAAAA8CX6UAAAAqElEQVR4Xu2TWw3DMAxFjWEUiqEURmEUSqGQBqEMymAMRmAA1py5liIr9vIxaT85kr98c/1qRQZ/Yy7xTuJVYjt1XdxFH/oHU4ld1NDnmjxFxS0uojkMU6hKN4wQgQkatCGLqGj1iQozuvpETbSfmi6jbD+GXZF9NenZz01U8/CJmm9j2XeWFfqQjcUYdEGEI0E2FpekCLnQhHbpwhbow36L9EKDwS84AE5BOLDLwSB0AAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAaCAYAAACzdqxAAAAA1klEQVR4Xu2UbQ0CQQxEqwELaMACFrCABSzgAAk4wQEOMIAAuJdmQvc7x8/LvqTJQdvZdrjFbLIZDkt8QrzTdMHR0vpXmi65L/E0L26xM6+j5pHlmiB6NW9iqhrkL+Y1PA9hEiY4WVsYyxAbHZ6AIA3yrzYNFmiAnl0JN3NRGmvCrK8JV/sr8kb9YNDbqEDrCQ6JB8kC+MtfET1EABtquSHyN36meW8/C0RuUxfW1qqgdfmeV0ys8pfG/Eq2BLRJ118E+U+gUHEOOQ7TFrrCMfJhJpPN8AXhAEuEcuOEIwAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAaCAYAAAD1wA/qAAAB9UlEQVR4Xu3XDW3cQBCG4cNQCsUQCqVQCqVQCmFQCIFQBmVQBiUQAI0fKV+0HY3tdS7pndp7pZVz6/H8fLuzdk6nGzf+Ce7qxA4fl/GhTl6ah2V8qZMrKEDRivjxfL0Kvi7jW51suF/G7+cR+0/L+PlicUGo+3iaV1XiCvk8zFlNRV4USRizZFXGwm2zI2K8CxIY1d1DT3Rb6ddposdUysg2gKvg+f1a+KDuFmKzE9/fY3+MWNXvdbJCBQ0ZJx7w+9zltE06dYPko3Ti1f4IfLFdxUOcUJ+TVC0Bv89ZFSoSqSOrpbkD+9ofQbGbq8tAM8UwLy2BOmWOoIiuEIlSv67WWn8gp9ku1OD8LVkrJKLZCSPm1k646ULsv91mOshaITlix0+WJKrIjqlC0h9VoWCLOQQ4y1vaVSKSomL3HcWuK8R8TSrFyYXvsXeQ+5vU/hixnznJCZRGHNVLMZWcRJXEi6+88HIqKb42vBidKH/AqAsIChmcpPkTOFC4+4RgF5UreS941jXFrfkS371NVN8FGxkVpLTggZLdasI99h35yg38d37youzuHaJ+gSoiyXEuWcE6xSi9dqTOwsfutprBUo9J2lZZQYVIlE3d18H92ryz8Lm14oeoCdZtWO9XUuyeXceRf8j+Cjmqj+CZqyrixn/HE3ulidGO/pv1AAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAZCAYAAADnstS2AAAAo0lEQVR4Xu2SUQ2AMAwFqwELaMACFrCABSzgAAlIwAEOcIABBMCOUTKa7odPwkuaQNu9Xhki31QRorZJKxr2KxZTy4rmwSY9qXtjC556ic1wu8KtC1GGmCXDW4VYJboxlmeXF5dNYqOqlQwv4yyby6sbw5mK3Ghy5xgK6S2pASjscuPBm7Ixli9AjhoLPq4bBxpwgJ+DLAzGlPTd8n4Y+/7rnQ5Q/ye8X08LfAAAAABJRU5ErkJggg==>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAaCAYAAAC6nQw6AAAAwElEQVR4Xu2SURECMQxEowELaDgLWMACFrBwDpCABBzgAAcYQADktbdMLi18M0PfzE4hbbJNemaDwQ+ycR1c2xDbuY4pNlk9x9rlajXpafUg/1kV27surtPy++GaS2aADTmTdLN6Q0GMxHgLjNAKXZWVJFoSKs5NIpg1hcTZqnPkW3G66HK31oWbkBTR3OIjvJFLHmCvOG0hwGj1gmohBj8VV4wHySZlI8+HueTioEGjvFeq93puDi5gEj+RwX/zAm1IMvC4HKj8AAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAbCAYAAACqenW9AAAAqElEQVR4Xu2SYQ2EMAxGqwELaMACFrBwFrCAAyTgBAc4wMAJuNujNOnKQvab8JJmsLVfvw5EnkF7xi1Lit8ZUzgr8hFN7uNBCVOvYk+xxs0SDBX9dinGFI3bO4h+Z9HCTbQgw/sl0VRjtwP8okIRicBK4sVGdbIN9xUtwMZFzfDDUXh7hfFjkEgXQCi7DVp7JZ7tnTWzhKqvHkSV8Y5yhk3vqfpVX6r4A9AILffqQy+fAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAaCAYAAACO5M0mAAAAkUlEQVR4XmNgGKZAGYi7gPgElHZDlYYAUwaIgnAGiIKdQPwfiDOQFYHAMwaIKehiIMUgm+AAJADCIJNhAKQRJIZiwEwGiHVCSGJYFWIDMHdi9RQMgJwAUrQSXQIZgKy/zkBAEQgQrRDkNoKKQAqQFYHCEMMzoCBCj4lKdDEQ5zMDJBqRMUgMxURYzGDDo4AwAAB59ingjmNn9gAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAaCAYAAACkVDyJAAABCklEQVR4Xu3TW1EEQQyF4daAhdWwFrCAhbWAhXWABCTgYB3gAAMIgP6qJjWnmp0Hpt9g/qrU9D3JSaa1g4ODf83TYiOnGJ/b/TO/5rXbc7f3bi+xfun21Vann8t8ise2Ovno9hZ7AuGkENS0Q1mQinnMvBgDQAYwhSw5fFjmZDSXVWFvDGA3srnFvOon81xLBabw+DXmxmO9ZFcK6Faq6AEqGPsK0F31z2B/oDbZobJNibO5rHmU6ew6kz1QTjdxsJzKRLQe47jWsr7MXv2XssmGcicV20Qm48++JU0qIMBsKD2xdW8XAqNAUaqAIw4Fk2Waglz5GDlLGQ4F40wpMM34UJYB4/7BH+EbU75BYoehw1EAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAZCAYAAAAv3j5gAAAAzElEQVR4Xu2UYRHCMAxGowELaMACFrCAhVnACRJwMAcTggDWd9tuaddk9OD2K+8u10ua5muztSJB4HBO1pXBHVjzSNbP4ymfXrnKlPBK9pFpwbdckr1l3RwjPvENCJHAZKsQuc8ihr9bo0WIlpFPNzT4xJk3aRG6iy9Ep0xahKyCS7zcQEYIkX8z4n8T4iS1gtZJMzwhfld9EXkBPCHzhQBPiBvPvBarXc5hjm9YWlAzDQUQ0xeRXRPn+aIOI757ml/gh6Bl7ncJguMYAUmPTq+ma4LNAAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAWCAYAAADNX8xBAAAAYUlEQVR4XmNgGAWjYODATHQBcsFKIFZGFyQHmALxTnRBcgHIexnogiAb3MjA1xkgBgoxQAHImSfIwM+A+DMDhYEP8gXIMIoCHeQVkLfgXiIXVDJgCWhyAMg1VAEUhcsQAwCiqxnjs1TMzwAAAABJRU5ErkJggg==>