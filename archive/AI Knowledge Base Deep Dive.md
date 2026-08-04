# **Architecture and Navigation Design for the Autonomous AI Knowledge Operating System**

The evolution of modern knowledge management has reached an architectural inflection point. Traditional repositories—siloed across disparate databases and flat text structures—fail to support the active, long-term cognitive requirements of agentic workflows.1 When large language models are treated as stateless conversational engines, they encounter catastrophic context loss, high token costs, and a tendency to generate inaccurate answers due to missing or stale reference materials.2  
The AI Knowledge Operating System addresses these challenges by acting as an autonomous, persistent, and self-sustaining cognitive environment.1 Rather than simply retrieving documents, this system actively maintains, organizes, and reviews a structured database that is fully decoupled from individual sessions.3  
Implementing this cognitive infrastructure on local hardware requires a robust system design.3 The following analysis outlines the technical framework for the files, metadata, navigation systems, and dual-engine retrieval models needed to support autonomous, zero-interruption knowledge governance.3

## **Architectural Choices for Document Storage: LLM Wiki versus RAG**

A foundational decision in the design of a persistent cognitive repository is balancing the simplicity of file-based routing with the scalability of vectorized databases.6 For the past several years, Retrieval-Augmented Generation has served as the default architecture for enterprise retrieval, relying on vector search to pull isolated text blocks into an LLM's active context.6  
However, standard vector retrieval often struggles with highly structured documents, precise alphanumeric codes, and complex logical relationships.8 This has led to the emergence of the LLM Wiki pattern, which stores information in structured, human-readable markdown files and dynamically loads entire documents into the active context.6  
Evaluating these approaches requires a structured decision-making framework based on document volume, stability, and retrieval precision requirements.

### **Technical Framework for Document Architecture Selection**

| Evaluation Criterion | LLM Wiki Pattern | Retrieval-Augmented Generation (RAG) |
| :---- | :---- | :---- |
| **Document Volume Threshold** | Optimized for fewer than 100 documents; remains viable up to 1,000 highly structured files.6 | Designed for scale; optimized for corpora exceeding 1,000 to 10,000+ unstructured files.6 |
| **Content Stability** | Highly effective for stable documentation, core procedures, standards, and static tables.6 | Suited for rapidly changing, unstructured logs and dynamic document streams.6 |
| **Knowledge Structure** | Built for highly structured, hierarchical documentation, procedures, policies, and FAQs.6 | Built for long-form prose, research reports, raw transcripts, and unformatted text.6 |
| **Retrieval Precision** | Deterministic; guarantees exact, complete document context without semantic fragmentation.6 | Probabilistic; matches semantic similarity but risks separating relevant paragraphs from their context.6 |
| **Engineering Overhead** | Low complexity; can be implemented using standard file directories and basic system prompts.6 | High complexity; requires dedicated infrastructure for embedding pipelines and vector indexing.6 |
| **Auditability & Control** | High; files are human-readable and directly compatible with Git version control systems.6 | Low; updates are stored as mathematical vector coordinates, making manual audits difficult.6 |

The Open Knowledge Format (OKF) v0.1—published by Google Cloud on June 12, 2026—formalizes the LLM Wiki approach.16 The OKF specification establishes a vendor-neutral, portable, and human-readable standard for representing organizational knowledge as a structured directory of markdown files containing YAML frontmatter.16  
The system implements this pattern by organizing files within a central directory (historically structured as a bundles folder), using standard relative or bundle-absolute markdown links to create an interconnected concept graph.11 These links serve as untyped directed edges that allow autonomous agents to systematically traverse the repository.2

## **Syntactic Architecture and Granular Chunking Specifications**

To prevent retrieval errors, the content within the markdown files must be structured to ensure it is highly parseable by machines while remaining readable for human editors.3 Traditional document parsing often strips formatting, flattening headers and tables into unstructured text blocks.21  
This destruction of syntactic structure degrades downstream retrieval, particularly when processing technical data, formulas, or non-English documentation.21

\+-------------------------------------------------------------+  
|                     KNOWLEDGE FILE (.md)                    |  
\+-------------------------------------------------------------+  
|                                                             |  
|                              |  
|  \---                                                        |  
|  type: concept                                              |  
|  confidence: 0.82                                           |  
|  dependencies: \[Unification, Parsing\]                       |  
| ...                                                        |  
|  \---                                                        |  
|                                                             |  
\+-------------------------------------------------------------+  
|                                                             |  
|                              |  
|  \# Definite Clause Grammars                                 |  
|  Definite Clause Grammars (DCGs) extend Prolog syntax...     |  
|                                                             |  
|  \#\# Implementation                                          |  
|  \`\`\`prolog |

| sentence \--\> noun\_phrase, verb\_phrase. |  
| \`\`\`                                                        |  
|                                                             |  
\+-------------------------------------------------------------+

### **The Dual-Layer Article Layout**

The system enforces a strict separation of concerns using a dual-layer file structure 3:

* **The AI Layer (YAML Frontmatter):** A machine-readable block at the absolute top of the file, enclosed by triple-dash (---) delimiters.3 This section contains the structured parameters used by indexing, routing, and access control engines.3  
* **The Human Layer (Markdown Body):** The rest of the file, containing the core content, formatted headings, tables, code blocks, and diagrams.3

### **Writing Rules for Semantic Chunks**

To keep retrieval precise, files must be broken down into single-topic chunks, containing only one coherent process, idea, or concept.3 Content within these chunks is authored using a direct, imperative style designed for literal programmatic execution 20:

* **Elimination of Fluff:** Historical details, introductory filler, and conversational phrasing are systematically removed.20  
* **Imperative Directives:** Step-by-step procedures must use explicit commands (e.g., "Call custom action Submit to commit changes" rather than "You should then click submit").20  
* **Absolute Factual Values:** Vague descriptors are replaced with concrete data (e.g., "Tier A hosting costs $30 per month" instead of "Our plans are affordable").20  
* **Explicit Outcome Statements:** Every procedural chunk must end with an explicit declaration of its target state (e.g., "Outcome: User account is successfully provisioned and a confirmation payload is returned to the client").20 This outcome statement serves as a validation check for the executing agent, ensuring it does not terminate a process prematurely.20

### **Hierarchical Processing and Semantic Splitting**

When processing long-form, unstructured files, the ingestion engine uses a combination of hierarchical parsing and semantic similarity splitting.12 This approach ensures that logical context is preserved even when documents are divided into smaller segments.12  
Semantic chunking splits text dynamically by analyzing embedding similarity between consecutive sentences, rather than relying on fixed character limits.27 The cosine similarity between consecutive sentences is calculated as:  
![][image1]  
where ![][image2] and ![][image3] are the vector representations of sentences ![][image4] and ![][image5].27 Breakpoints are placed where similarity drops below a specific percentile threshold (such as the 95th percentile), ensuring that sentences with close semantic relationships remain grouped in the same chunk.27  
These semantic chunks are organized into a parent-child hierarchy.12 Large parent nodes (e.g., 2048 tokens) are split into smaller child nodes (e.g., 512 tokens), with child vectors indexed in the database alongside pointers to their parent.12 This bidirectional relationship allows the system to expand its context window dynamically during retrieval, pulling the broader parent context if a highly specific child node is matched.12  
For files containing mixed layouts, tables, and images, the ingestion engine integrates the local Docling parser, which maps document structures directly into a structured "Markdown Plus" format.29

### **Markdown Plus Layout Annotations**

| Structural Annotation | Format and Layout Rules | Functional Parsing Role |
| :---- | :---- | :---- |
| **Page Marker** | \[Page (number)\]: \# 30 | Identifies physical page boundaries from the source document to enable accurate citation and audit trails.22 |
| **Vertical Position Marker** | : \# 30 | Tracks the vertical position of parsed elements, dividing pages into proportional bands to preserve reading order.30 |
| **Split Marker** | : \# 30 | Injects pre-calculated segmentation points directly into the file, allowing editors to manually adjust chunk boundaries before final indexing.30 |

## **Exhaustive Metadata Schema and Data Governance Protocol**

To ensure structured indexing and robust access controls, every active document in the repository must conform to an exhaustive YAML schema.3 The system parses this frontmatter block using custom validators built on the Pydantic framework, translating formatting errors into actionable reports before files are committed to the index.32

### **Standard Schema Fields, Typings, and Constraints**

| Metadata Field | Data Type | Validation Rules / Constraints | Functional Retrieval Role |
| :---- | :---- | :---- | :---- |
| type | String (Enum) | concept, project, research, programming\_concept, agent 3 | Mandatory field; defines the primary document class and routes queries to specialized cognitive skins.3 |
| template | String | Must match a valid template file in the active repository.3 | Enforces schema rules and structural layout constraints during CI/CD checks.3 |
| importance | String (Enum) | high, medium, low 3 | Weight modifier used during hybrid retrieval and context scaling.3 |
| confidence | Float | Float value between 0.0 and 1.0.3 | Operational threshold filter; drops uncertain context from high-stakes pipelines.3 |
| stability | String (Enum) | stable, volatile 3 | Directs temporal decay calculations and scheduled review cycles.3 |
| dependencies | List of Strings | Array of valid document paths or concept identifiers.3 | Establishes prerequisite relationships to guide sequential agent traversal.3 |
| related | List of Strings | Array of valid document paths or concept identifiers.3 | Defines lateral relationships; must remain synchronized with body links.3 |
| keywords | List of Strings | List of lowercase alphanumeric search tags.3 | Used by sparse engines to enable exact term matching.3 |
| priority | Integer | Positive integer scale (e.g., 1 to 5).3 | Sorting mechanism for sequential prompt injection when under strict token limits.3 |
| updated | Date | ISO 8601 Date format (YYYY-MM-DD).3 | Tracks temporal freshness and triggers staleness audits.3 |
| review\_date | Date | ISO 8601 Date format (YYYY-MM-DD).3 | Scheduled review flag for automated, cron-based validation checks.3 |
| read\_order | List of Strings | Ordered list of section titles in the markdown body.3 | Establishes reading sequences for sequential context loading.3 |
| retrieval\_tags | List of Strings | Domain-specific categorization keys.3 | Used for hardware-accelerated metadata filtering in vector databases.3 |
| summary | String | Plain-text string; maximum 250 characters.3 | Injected into global index maps to enable lightweight routing decisions.3 |
| template\_version | String | Semantic version identifier (e.g., v1.2.0).3 | Identifies outdated metadata configurations requiring automated migrations.3 |
| provenance | List of Strings | Array of original source file paths or ingest session logs.3 | Establishes audit trails and source lineage to track hallucinations.3 |
| ai\_notes | String | Free-form text workspace.3 | Dedicated field for agent notes and interaction history.3 |

### **Access Control and Security Integration**

Managing data security requires applying access permissions before files are indexed, rather than filtering results after retrieval.24 Security metadata must be derived directly from the source systems to prevent unauthorized data exposure.21  
The ingestion engine enforces three validation steps before indexing files:

1. **Role-Based Access Mapping:** Every document is assigned a sensitivity label—Public, Internal, Confidential, or Restricted.24 These labels are mapped to explicit user roles.24 Documents with missing labels are automatically blocked from ingestion.24  
2. **Glossary Alignment:** Documents are linked to defined business terms and standard taxonomies to maintain consistent vocabulary across different data sources.24  
3. **Lineage Preservation:** Technical files must include references to their upstream source systems, preserving audit trails and validating the authority of the document.22

## **Mathematical Models of Confidence, Memory, and Temporal Decay**

To prevent the accumulation of outdated or contradictory information, the system dynamically manages document lifecycle properties.3 Instead of treating all files as statically valid, the system uses mathematical models to adjust confidence scores and apply temporal decay.3

### **Active Confidence Modification**

When new documents are ingested, the system recalculates the confidence score (![][image6]) of existing concepts based on confirmation and contradiction metrics 3:  
![][image7]  
where ![][image8] is the current confidence score, ![][image9] is the validation modifier for supporting sources, ![][image10] is the number of newly identified verifying sources, ![][image11] is the contradiction penalty, and ![][image12] is the count of conflicting statements detected across active documents.3

### **Exponential Temporal Decay**

For volatile files (such as active software APIs, fast-evolving projects, or ephemeral schedules), the system applies exponential temporal decay when a document passes its scheduled review\_date without verification 3:  
![][image13]  
where ![][image14] represents the number of weeks elapsed past the scheduled review\_date, and ![][image15] is the decay factor based on the document's stability class 3:  
![][image16]  
If a document's confidence score falls below a critical threshold (![][image17]), the system initiates an uncertainty propagation check across the concept graph.3 Any concept listing that degraded document in its dependencies array is automatically flagged for review.3  
This ensures that outdated or uncertain premises do not silently corrupt dependent conclusions.3 Conversely, when a document is accessed, queried, or reinforced, the system resets its decay calculation.3

### **Structural Staleness and Decay Modes**

Staleness affects different retrieval architectures in distinct ways, requiring specific tracking and mitigation metrics.4

| Storage Architecture | Primary Staleness Mode | Core Failure Mechanism | Core Tracking Metric |
| :---- | :---- | :---- | :---- |
| **Retrieval-Augmented Generation (RAG)** | Document Staleness & Embedding Lag.4 | Delay between updating source documents and re-indexing vectors.4 | **Embedding Lag:** Time difference between source modifications and database indexing.4 |
| **Agent Memory Systems** | Personalization Drift.4 | Storing static user profiles and context that has since changed.4 | **Recency of Activity:** Time elapsed since a memory was last accessed or reinforced.4 |
| **Knowledge Graphs** | Entity Decay.4 | Structural facts and relationships that have become obsolete.4 | **Provenance Verification:** Frequency of validating facts against active source systems.4 |

## **AI Navigation, Graph Traversal, and Tool Integrations**

Autonomous agents need structured navigation paths to browse the repository systematically, avoiding the token waste and search bloat associated with unstructured similarity searches.2

### **Global Navigation Directory Structure**

The system's root directory uses standardized landing files to guide agents entering the workspace 14:

* **START\_HERE.md:** The entry point for humans and machines, providing a high-level project overview, team details, active sprints, and pointers to core structures.14  
* **KNOWLEDGE\_BASE.md:** The repository's central index.14 It lists files by tier, provides one-line summaries, groups documents into topic-specific Concept Clusters, and uses Mermaid diagrams to visualize relationships.14  
* **AGENTS.md:** Standardized instructions outlining the system layout and behavioral expectations for incoming agents.14

### **The Agentic Traversal Sequence**

When executing a user query, the agent follows a defined traversal sequence to locate context 14:

\+-----------------------------------------------------------+  
| STEP 1: INITIALIZATION                                    |  
| Read START\_HERE.md, KNOWLEDGE\_BASE.md, and Tier 1 files.  |  
\+-----------------------------+-----------------------------+  
                              |  
\+-----------------------------v-----------------------------+  
| STEP 2: CONCEPT ROUTING                                   |  
| Search KNOWLEDGE\_BASE.md to find relevant topic clusters. |  
\+-----------------------------+-----------------------------+  
                              |  
\+-----------------------------v-----------------------------+  
| STEP 3: DYNAMIC LOADING                                   |  
| Fetch mapped files; limit to 3-4 files to prevent bloat.  |  
\+-----------------------------+-----------------------------+  
                              |  
\+-----------------------------v-----------------------------+  
| STEP 4: GENERATION & CITATION                             |  
| Synthesize answers citing specific files and line numbers.|  
\+-----------------------------------------------------------+

During execution, agents use specialized local tools to navigate the file system and graph relationships 37:

* **geode-graph-obsidian CLI:** Parses relative markdown links and YAML frontmatter to construct structured relationship triples locally using Ollama.37  
* **obsidianmd-parser library:** Programmatically evaluates Dataview queries, tracks metadata tags, manages task lists, and identifies broken links.38  
* **Agent Skill Graph Plugin:** Interacts with the Obsidian cached metadata cache and dynamically overrides PixiJS WebGL node labels in-memory.34 This allows the agent to visualize out-of-vault references as virtual nodes without modifying files on disk.34

## **Dual-Engine Hybrid Retrieval and Late Interaction Reranking**

Relying on dense vector similarity alone introduces significant retrieval vulnerabilities in technical domains. High-dimensional embeddings excel at capturing broad concepts, but they struggle with exact matching.  
Specific product codes, variable names, error identifiers, or negations often get lost in semantic noise, causing traditional RAG pipelines to return superficially relevant but functionally useless results.8  
To resolve this issue, the system uses a dual-engine architecture in Qdrant, configuring each index point with both dense and sparse vectors.39

               \+--------------------------------------+  
               |             USER QUERY               |  
               |     "Verify error ERR\_CONN\_RESET"    |  
               \+------------------+-------------------+  
                                  |  
         \+------------------------+------------------------+  
         |                                                 |  
\+--------v---------+                             \+---------v--------+  
| DENSE ENGINE     |                             | SPARSE ENGINE    |  
| Vector Match     |                             | BM25 / SPLADE    |  
| (Semantic Space) |                             | (Exact Strings)  |  
\+--------+---------+                             \+---------+--------+  
         |                                                 |  
         \+------------------------+------------------------+  
                                  |  
                        \+---------v--------+  
                        |  HYBRID FUSION   |  
                        |   RRF or DBSF    |  
                        \+---------+--------+  
                                  |  
                        \+---------v--------+  
                        |    RERANKER      |  
                        |  Cross-Encoder   |  
                        \+---------+--------+  
                                  |  
                        \+---------v--------+  
                        |   FINAL RESULT   |  
                        \+------------------+

### **The Ingestion and Search Pipeline**

The search pipeline indexes chunks using parallel dense and sparse named vectors to balance semantic understanding with keyword precision 39:

* **The Dense Semantic Index:** Converts chunks into continuous vectors (e.g., 384 dimensions matching models like all-MiniLM-L6-v2) using cosine distance metrics.39 This handles synonyms, conceptual queries, and cross-language matching.9  
* **The Sparse Lexical Index:** Maps text to high-dimensional vocabulary spaces using BM25 or SPLADE.9 This ensures exact terminology matching, preserving the importance of rare terms and handling direct qualification and negation.9

Python  
from qdrant\_client import QdrantClient, models

client \= QdrantClient(location="https://your-cluster-url.cloud.qdrant.io:6333", api\_key="your-key")

\# Create a dual-engine collection configured with both dense and sparse vectors  
client.create\_collection(  
    collection\_name="hybrid\_knowledge\_base",  
    vectors\_config={  
        "dense": models.VectorParams(  
            distance=models.Distance.COSINE,  
            size=384,  
        ),  
    },  
    sparse\_vectors\_config={  
        "sparse": models.SparseVectorParams(  
            modifier=models.Modifier.IDF  
        )  
    }  
)

### **Rank Fusion and Candidates Reranking**

To combine results from both search paths, the system uses multi-stage prefetching and score fusion 41:

* **Reciprocal Rank Fusion (RRF):** Evaluates the relative position of documents across dense and sparse result sets, boosting documents that rank highly in both paths 9:

![][image18]  
where ![][image19], ![][image20] represents the zero-based rank of document ![][image21] in retrieval path ![][image22], ![][image23] is a smoothing constant, and ![][image24] is the weight assigned to each path.9

* **Distribution-Based Score Fusion (DBSF):** Normalizes similarity score distributions to preserve relative semantic distance, preventing a single highly anomalous score from skewing the final rankings.39

Once the hybrid results are fused, the system runs a final reranking stage.10 Rather than passing hundreds of candidates directly to the LLM, the top 30 candidates are processed using a precise late-interaction model (e.g., ColBERT via maximum similarity operators) or a Cross-Encoder.10 This final pass scores the specific interactions between query tokens and document tokens, producing highly accurate context rankings.40

## **Content CI/CD, Automated Validation, and Ingestion Governance**

To maintain repository quality at scale, all knowledge files are stored in a Git repository managed by automated continuous integration pipelines.14 This automated governance ensures that every document meets formatting and security standards before it is committed to the active index.42

### **The Continuous Integration Quality Pipeline**

When an editor or agent submits a pull request, the CI/CD pipeline runs a series of automated checks 42:

1. **Structural Linting:** Runs markdownlint to enforce consistent formatting, heading hierarchies, and file structures.42  
2. **Schema Verification:** Parses YAML frontmatter using Pydantic models to verify datatypes, mandatory fields, and link integrity.32  
3. **Quality and Tonal Audit:** Uses local engines (like Vale or custom scripts) to scan for style compliance, inclusive language, and brand terminology.42 It filters out conversational filler and motivational fluff, ensuring the content is structured as clear, direct instructions.20

### **Dual-Agent Ingestion and Reconciliation**

Rather than simply appending new documents, the ingestion engine uses a local dual-agent model (comprising independent Proposer and Critic roles) to evaluate how new data relates to the existing corpus.3

\+-----------------------------------------------------------+  
| NEW DOCUMENT ARRIVES                                      |  
\+-----------------------------+-----------------------------+  
                              |  
\+-----------------------------v-----------------------------+  
| RETRIEVAL STEP                                            |  
| Search for existing documents with high semantic similarity.|  
\+-----------------------------+-----------------------------+  
                              |  
\+-----------------------------v-----------------------------+  
| DUAL-AGENT REVIEW (Proposer & Critic)                     |  
| Evaluate relationship to current files.                   |  
\+-----------------------------+-----------------------------+  
                              |  
         \+--------------------+--------------------+  
         |                    |                    |  
\+--------v-------+   \+--------v-------+   \+--------v-------+  
| CONFIRMATION   |   | CONTRADICTION  |   | SUPERCESSION   |  
| Boost base     |   | Lower score;   |   | Move old file  |  
| confidence     |   | flag for human |   | to /archive/;  |  
| score.         |   | review.        |   | update links.  |  
\+----------------+   \+----------------+   \+----------------+

During ingestion, the system retrieves files with high semantic similarity to the incoming text and evaluates the relationship 36:

* **Confirmation:** If the incoming text reinforces existing documentation, the system boosts the confidence scores of the corresponding files.3  
* **Contradiction:** If the new document contradicts existing facts, the system lowers the confidence score of the affected files and flags them for manual review.3  
* **Supercession:** If the incoming document is an updated standard or design, the engine automatically moves the obsolete files to the /archive/ directory, adds a warning banner, updates relative links, and recalculates affected graph dependencies.3

## **Architectural Conclusions and Recommendations**

Transitioning to an autonomous AI Knowledge Operating System requires a shift from passive file storage to active, self-governing semantic environments. For repositories with stable, structured knowledge bases containing fewer than 1,000 files, the system should default to the Open Knowledge Format (OKF) v0.1 specification, using structured markdown files and file-level routing to minimize engineering overhead.  
As the corpus scales, this file-based architecture must be paired with dual-engine vector and lexical indexes.39 This hybrid search approach ensures semantic understanding while maintaining exact term matching.9  
Finally, to prevent data rot and maintain factual consistency, organizations must implement automated ingestion pipelines, Git-based CI/CD workflows, and dynamic confidence scoring models.3 Treating knowledge as a structured, version-controlled codebase ensures that autonomous agents have access to a reliable, secure, and self-sustaining cognitive database.3

#### **Works cited**

1. What Is an AI Knowledge Base? A Complete 2025 Guide to AI-Powered Knowledge Management | Kuse Blog, accessed on June 24, 2026, [https://www.kuse.ai/blog/insight/what-is-an-ai-knowledge-base-a-complete-2025-guide-to-ai-powered-knowledge-management](https://www.kuse.ai/blog/insight/what-is-an-ai-knowledge-base-a-complete-2025-guide-to-ai-powered-knowledge-management)  
2. AI Knowledge Management: The Architecture Behind Agents That Remember | DevRev, accessed on June 24, 2026, [https://devrev.ai/blog/ai-knowledge-management](https://devrev.ai/blog/ai-knowledge-management)  
3. AI\_Knowledge\_OS\_Full\_Context.md  
4. LLM Knowledge Base Freshness Scoring: Metrics and Framework \- Atlan, accessed on June 24, 2026, [https://atlan.com/know/llm-knowledge-base-freshness-scoring/](https://atlan.com/know/llm-knowledge-base-freshness-scoring/)  
5. Andrej Karpathy Killed RAG. Or Did He? The LLM Wiki Pattern \- Towards AI, accessed on June 24, 2026, [https://pub.towardsai.net/andrej-karpathy-killed-rag-or-did-he-the-llm-wiki-pattern-7824d876e790](https://pub.towardsai.net/andrej-karpathy-killed-rag-or-did-he-the-llm-wiki-pattern-7824d876e790)  
6. LLM Wiki vs RAG: A Decision Framework for AI Knowledge Bases ..., accessed on June 24, 2026, [https://www.mindstudio.ai/blog/llm-wiki-vs-rag-knowledge-base](https://www.mindstudio.ai/blog/llm-wiki-vs-rag-knowledge-base)  
7. The Complete Guide to RAG: Naive, Advanced, and Graph RAG in One Document, accessed on June 24, 2026, [https://www.mrlatte.net/en/research/2026/04/27/rag-complete-guide/](https://www.mrlatte.net/en/research/2026/04/27/rag-complete-guide/)  
8. Utilizing Metadata for Better Retrieval-Augmented Generation \- arXiv, accessed on June 24, 2026, [https://arxiv.org/html/2601.11863v1](https://arxiv.org/html/2601.11863v1)  
9. Hybrid Search in RAG: Dense \+ Sparse (BM25/SPLADE), Reciprocal Rank Fusion, and When to Use Which\! | by Vaibhav Dixit | GoPenAI, accessed on June 24, 2026, [https://blog.gopenai.com/hybrid-search-in-rag-dense-sparse-bm25-splade-reciprocal-rank-fusion-and-when-to-use-which-fafe4fd6156e](https://blog.gopenai.com/hybrid-search-in-rag-dense-sparse-bm25-splade-reciprocal-rank-fusion-and-when-to-use-which-fafe4fd6156e)  
10. Hybrid Search Implementation Guide: Combining Vector and Keyword Search for RAG, accessed on June 24, 2026, [https://zenvanriel.com/ai-engineer-blog/hybrid-search-implementation-guide/](https://zenvanriel.com/ai-engineer-blog/hybrid-search-implementation-guide/)  
11. Open Knowledge Format has just been announced as a new Knowledge Base format for AI agents made by Google : r/LLMDevs \- Reddit, accessed on June 24, 2026, [https://www.reddit.com/r/LLMDevs/comments/1u7jmvt/open\_knowledge\_format\_has\_just\_been\_announced\_as/](https://www.reddit.com/r/LLMDevs/comments/1u7jmvt/open_knowledge_format_has_just_been_announced_as/)  
12. Hierarchical Chunking \- Grokipedia, accessed on June 24, 2026, [https://grokipedia.com/page/Hierarchical\_Chunking](https://grokipedia.com/page/Hierarchical_Chunking)  
13. Building a Knowledge Base for RAG: A Step-by-Step Guide | by Arushi Aggarwal \- Medium, accessed on June 24, 2026, [https://medium.com/@arushiagg04/building-a-knowledge-base-for-rag-a-step-by-step-guide-c3afbccf3700](https://medium.com/@arushiagg04/building-a-knowledge-base-for-rag-a-step-by-step-guide-c3afbccf3700)  
14. Building an AI-Powered Markdown Knowledge Base System for Your Engineering Team, accessed on June 24, 2026, [https://medium.com/cwan-engineering/building-an-ai-powered-markdown-knowledge-base-system-for-your-engineering-team-4bccea3cdbfe](https://medium.com/cwan-engineering/building-an-ai-powered-markdown-knowledge-base-system-for-your-engineering-team-4bccea3cdbfe)  
15. Unlocking High-Precision RAG: The Role of Metadata enhancement, Parsing, and Document Structuring | by SHYAM SUNDAR M | Medium, accessed on June 24, 2026, [https://medium.com/@shyamsundarmuthu/unlocking-high-precision-rag-the-role-of-metadata-enhancement-parsing-and-document-structuring-d5d17364b894](https://medium.com/@shyamsundarmuthu/unlocking-high-precision-rag-the-role-of-metadata-enhancement-parsing-and-document-structuring-d5d17364b894)  
16. How the Open Knowledge Format can improve data sharing | Google Cloud Blog, accessed on June 24, 2026, [https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)  
17. Open Knowledge Format | Definition, Scope and Compliance (Grounding Page), accessed on June 24, 2026, [https://groundingpage.com/facts/open-knowledge-format/](https://groundingpage.com/facts/open-knowledge-format/)  
18. Google's new Open Knowledge Format is basically the CLAUDE.md / memory-folder pattern, formalized into a spec. I'd already built it for my own Claude setup. \- Reddit, accessed on June 24, 2026, [https://www.reddit.com/r/ClaudeAI/comments/1u9rbs8/googles\_new\_open\_knowledge\_format\_is\_basically/](https://www.reddit.com/r/ClaudeAI/comments/1u9rbs8/googles_new_open_knowledge_format_is_basically/)  
19. knowledge-catalog/okf/SPEC.md at main · GoogleCloudPlatform ..., accessed on June 24, 2026, [https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)  
20. The RAG Playbook: Structuring Scalable Knowledge Bases for Reliable AI Agents \- Regal.ai, accessed on June 24, 2026, [https://www.regal.ai/blog/rag-playbook-structuring-knowledge-bases](https://www.regal.ai/blog/rag-playbook-structuring-knowledge-bases)  
21. Building retrieval augmented generation (RAG) systems and… \- Implement Consulting Group, accessed on June 24, 2026, [https://implementconsultinggroup.com/article/building-high-quality-rag-systems](https://implementconsultinggroup.com/article/building-high-quality-rag-systems)  
22. Document Extraction for RAG: Preparing Structured Outputs for Vector Databases, accessed on June 24, 2026, [https://landing.ai/llms/document-extraction-for-rag-preparing-structured-outputs-for-vector-databases](https://landing.ai/llms/document-extraction-for-rag-preparing-structured-outputs-for-vector-databases)  
23. Parse Front Matter from Documents • frontmatter, accessed on June 24, 2026, [https://posit-dev.github.io/frontmatter/](https://posit-dev.github.io/frontmatter/)  
24. Preparing Data for LLM Knowledge Bases: Governance and Readiness \- Atlan, accessed on June 24, 2026, [https://atlan.com/know/knowledge-base-data-preparation-llm/](https://atlan.com/know/knowledge-base-data-preparation-llm/)  
25. How to Build a Multimodal RAG Pipeline with Metadata Filtering | MindStudio, accessed on June 24, 2026, [https://www.mindstudio.ai/blog/multimodal-rag-pipeline-metadata-filtering](https://www.mindstudio.ai/blog/multimodal-rag-pipeline-metadata-filtering)  
26. How to Build an Efficient Knowledge Base for AI Models | Towards Data Science, accessed on June 24, 2026, [https://towardsdatascience.com/how-to-build-an-efficient-knowledge-base-for-ai-models/](https://towardsdatascience.com/how-to-build-an-efficient-knowledge-base-for-ai-models/)  
27. Semantic Chunker | Developer Documentation \- LlamaParse, accessed on June 24, 2026, [https://developers.llamaindex.ai/python/examples/node\_parsers/semantic\_chunking/](https://developers.llamaindex.ai/python/examples/node_parsers/semantic_chunking/)  
28. How do I handle document segmentation in LlamaIndex? \- Milvus, accessed on June 24, 2026, [https://milvus.io/ai-quick-reference/how-do-i-handle-document-segmentation-in-llamaindex](https://milvus.io/ai-quick-reference/how-do-i-handle-document-segmentation-in-llamaindex)  
29. docling-project/docling: Get your documents ready for gen AI \- GitHub, accessed on June 24, 2026, [https://github.com/docling-project/docling](https://github.com/docling-project/docling)  
30. Docling process :: Documentation for HPC, accessed on June 24, 2026, [https://docs.hpc.gwdg.de/services/ai-services/arcana/docling-process/index.html](https://docs.hpc.gwdg.de/services/ai-services/arcana/docling-process/index.html)  
31. RAG with Haystack \- Docling, accessed on June 24, 2026, [https://docling-project.github.io/docling/\_generated/examples/rag\_haystack/](https://docling-project.github.io/docling/_generated/examples/rag_haystack/)  
32. pydantic-yaml, accessed on June 24, 2026, [https://pydantic-yaml.readthedocs.io/](https://pydantic-yaml.readthedocs.io/)  
33. hamelsmu/pydantic-yaml-parser \- GitHub, accessed on June 24, 2026, [https://github.com/hamelsmu/pydantic-yaml-parser](https://github.com/hamelsmu/pydantic-yaml-parser)  
34. Obsidian plugin to visualize agent skill structures (OpenClaw / Claude Code) in graph view \- GitHub, accessed on June 24, 2026, [https://github.com/hanamizuki/obsidian-skill-graph](https://github.com/hanamizuki/obsidian-skill-graph)  
35. Myelin Kernel: a lightweight reinforcement-based memory kernel for Python AI agents (open source) \- Reddit, accessed on June 24, 2026, [https://www.reddit.com/r/Python/comments/1rvh67l/myelin\_kernel\_a\_lightweight\_reinforcementbased/](https://www.reddit.com/r/Python/comments/1rvh67l/myelin_kernel_a_lightweight_reinforcementbased/)  
36. What I Think RAG Gets Wrong \- Mohamed EL HARCHAOUI, accessed on June 24, 2026, [https://mohamedelharchaoui.com/writing/the-indexing-gap/](https://mohamedelharchaoui.com/writing/the-indexing-gap/)  
37. I built a local Graph RAG for Obsidian (CLI, looking for feedback) \- Reddit, accessed on June 24, 2026, [https://www.reddit.com/r/Rag/comments/1srs4zb/i\_built\_a\_local\_graph\_rag\_for\_obsidian\_cli/](https://www.reddit.com/r/Rag/comments/1srs4zb/i_built_a_local_graph_rag_for_obsidian_cli/)  
38. obsidianmd-parser \- PyPI, accessed on June 24, 2026, [https://pypi.org/project/obsidianmd-parser/](https://pypi.org/project/obsidianmd-parser/)  
39. Demo: Implementing a Hybrid Search System \- Qdrant, accessed on June 24, 2026, [https://qdrant.tech/course/essentials/day-3/hybrid-search-demo/](https://qdrant.tech/course/essentials/day-3/hybrid-search-demo/)  
40. Qdrant Hybrid Search with Reranking, accessed on June 24, 2026, [https://qdrant.tech/documentation/tutorials-basics/reranking-hybrid-search/](https://qdrant.tech/documentation/tutorials-basics/reranking-hybrid-search/)  
41. Hybrid Queries \- Qdrant, accessed on June 24, 2026, [https://qdrant.tech/documentation/search/hybrid-queries/](https://qdrant.tech/documentation/search/hybrid-queries/)  
42. The "Content CI/CD" Pipeline: Automating GEO Compliance Tests via GitHub Actions, accessed on June 24, 2026, [https://blog.trysteakhouse.com/blog/content-ci-cd-pipeline-automating-geo-compliance-tests-github-actions](https://blog.trysteakhouse.com/blog/content-ci-cd-pipeline-automating-geo-compliance-tests-github-actions)  
43. Automating Documentation Review in Your CI/CD Pipeline \- DEV Community, accessed on June 24, 2026, [https://dev.to/ekline/automating-documentation-review-in-your-cicd-pipeline-goj](https://dev.to/ekline/automating-documentation-review-in-your-cicd-pipeline-goj)

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAaCAYAAAAaAmTUAAACAElEQVR4Xu2WjU3EMAxGMwMrMAMrsAIrsAIr3AaMwAhswAZswAIMAH3XfshYtpOq5XRIfZIFJI3/ndDawcG/5HaSG7+4AXSh8+LcTfLW+sHcT/Kw/BT8nfHaZt2rQOHXoJyWM4IA3ludRRz6mOSlzeef23zmafk9A92cq3SnYAyHbeYEa5+TPLp1OZhBIJzzFSAQbHl9Hvap+mrIAgYyUGoDJWN8X2WOMwQc0TsrSEaU4BQ55rNglbBnjZNd2iWDNolaU5C8EUhGlpAQyukNax6Ed4o9v2ahxdCZ9f3ocOMb1RlG80K2qQbCWjWgfO9nwaPWRQgefataps3fj7bkGRmllRAMV86qLXuOkX3pstIbfMuorTPZvOCEfTtsZpStIQNtPksAvB2c821D0FWAw7aieQE7L3xj93vBVP8RqFIW9O8STPW+CNrQOtcLppoNOgB9a6hs/YKS+0xZuBT81ahrNzNA9rM9ArFVlv6skr3E/aDr088LoByj7EfXKEnAEY8CZT48OG1nkfO0ZBW8gknhA1WkJ1GggLO+YsANyBlaTVVAdFP6diWYqu04Wz3Ou8DA+lsJcFAO6xbDoai6QNDVe0YgUQfsDhnN3qJRSAhB+9sUWGc/m6ddUUttAWcJJJoZWvkiVRHMzVaDUeZpz2gm/xx6fvh/pwF0kx4cXAPfJC+m29E/0/UAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEUAAAAaCAYAAADhVZELAAACS0lEQVR4Xu2YDVEEMQxGqwELaMACFrCABSzgAAlIwAEOcIABBMA+7r6ZEJo0e+zu3Qz7ZjpAd9smX356R2s7OzsXxPU0rvzkBXDjJ7aCg1/bWJTbadwdfwr+XpPHadz7yQoY9lkcHGJBiLd2yJQIRHufxnM7rH9qhzUPx9/XhoCdLD5G47iNpGDuo/1WXY5GIAjrvFEIwll+vzUgYNgwyuQuRBNDI1DcCsZhvJ9lCWsQrsdo7ZK8tDx4XeQgTlisCDyzThBtyiCCyPRKThCErSAjZ5/HIu+A+oXwzvHMz1koHfbEmF5GbHkzKOizzlQ/IfpkB4O5rBHyvu8VHpUkAxHZr9eztmB2D5PxlAgDBzKnpfzIQSKjveyYZdxC4GOW2T+I+gnO2I5tSwAxKqII1iIEDY913AYWxDtVKGyIgmfBv7IovX4Ctp/wjn0+EiX7hKvMsbB/JEp0hkq8mgGzRMk+nwgOtk6ORMl6B8axX5WRI1Vnq+99Qyr7yFlovv6zhq7byHGyIXrmI6v9o8waOVJ1tlcNXXRt+n4CGMkmPO9dZYiJQx4JRv/w4LztVayn1DIRR47MESU64xseKkNGoycY4LTPIKDpsYYSUlYwmGP4MkQUW07qX3ad/dsHoiKKyj3KxsXAeH+LAAbocN06GN3LNkC87PPQyOGKKOzfy9xVIMKV6zADYREvciyaFxVRsDMtnSVRqfwFRMGpyOjIYYQkA1iffeWg3DbLEkFf8XU+l6zWI2crVP8BtgpErPel79wg6FkE2dn5R3wBvfW97AvAr3sAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAZCAYAAADTyxWqAAAA6klEQVR4Xu2TYRHCMAxGo2EW0IAFLGABC7OAAyQgAQc4wAEGEMDyWMOFXrq1XH/u3X23bmu/JmkqstGTneqoOqQx7N24movqqTonPVRjeg5u3ipX1V1+FzHGHFVDSm+JUyFCNqqG9DCLwOyUf1ziJrMZC3OItqle7IwZeslsTuGbTDykipGZouZTzOEwSNeMidDDe3RQn11phwg74eri0+klM0yIztLkFlCKorm1BBM9vGPkFzJ3afPvdaHDaUxqZVfKG1EjxJxiZOxkWOGZHJ0g38gi+tcMGRAZJfBB/AVmNDNl6EKXFDdEJs5sNz9w/hlUAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAaCAYAAAAwspV7AAABNklEQVR4Xu2VbQ3CMBCGqwELaMACFrCABSzgAAlIwAEOcIABBECfbG9ya+42IEv7p09yoR1d995Hryl1OvXYZjtk249j2JlxdS7ZntnOoz2yncbfjVlXjWu2e5p+nDEiseqQqnfyU0TEEFwd0oYoD0Qdy4c1uKVBFAJKiF6TeiISiMJeaRBJgTcRYyGFCJI4rNmpK6HoSaMEEjELc+9ALIFzXnm40Bg9aKBenZFaL3oIjcSyB+0mOkwT2JzFHmoT35481mMR2m8RohGJQgwpVFSIKHUXiVxNlPpTmULmCLICWDvnxGqidLdxjdC1yb3uPytI9cIaPWeuO1JdX3vIrLNfi8JzoVPHR71C5hmbev/BapH6BSJKJPDeOiOaiaIdkF6POVFEXy2B96N1fxGlDuZEdTpN+AA65VC43O7H0AAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAaCAYAAAC+aNwHAAAAv0lEQVR4Xu2SbQ2DMBCGqwELaMACFrCAhVnAwSTMCQ4QMgHjnq3Njt61EH4SnuRNA9fedwg3e7SiXjTEM9GIOvVt4PIseoteoime/MPpEu+4PEWf8HtEJA2PsCEXomAcc4OC6MjwCP/INSiDLDeQKvWiPO0cHJj6iUp049mBJhqoCQeM6xSps3vpF6mORkGp7gLRvCMOaKBLmn+tB9wp2tMYaabXBx7XlusLteFA7z9jJe1iZA8csZXIbdjN5VgBd1suIbSymG4AAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAaCAYAAAAue6XIAAABhUlEQVR4Xu3WYVHEMBAF4GjAAhqwgAF+YAEJYAEHSEACDnCAAwwgAPLN3YOl9O7KMBBg+mZ22iab5GXzstvWVqz4XzjudtrtfPsMjrqdlO+hQOy+21O3227X26c2G3jY+gzHTbfntiEoghUI6mPDIXqIXEw7CkSVDcVVe4voPpCC6A+D46ZPNj36KZAdqlfRFNUlEXPBhoIGkZWifj1yww9JIJBjH9tGEj+OpemIXFIMkot/HC7WErKV3DCyya/7NMun9oeslJcKFxl51spXSzN/eVxf8rlLG/9DqfM1dbloc7o10bRQIEu38fedYsHXfGnnl/dkHONSJfUny8yt9QF2b7H6P2Bi0ZuL+JwMnE6iiIRxSYuAkPe7tolwfFKMmDmtvwgWMxHb92e1i6x2BOrPTr0PCCOl33hRXHJfvoR67IBEKiAS0Z4NZxOX7f0R88+4WmwOyuCzsLjjJBWRRDCRtJiNeOr3zvestNuM04OMj/S+tUrumnzaXrPFHKb+K1b8abwAsnZrEuVdnH4AAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFIAAAAaCAYAAAAkJwuaAAACMklEQVR4Xu2XgVHDMAxFPQMrMAMrsAIrdAVWYANGYAQ2YAM26AIdAPxof08Viu0kR5vj9O50SRxHkb8lxyklSZIkmcNDtddqL9Weqt1d3k5GuK/2Xu2x2ke1r3IUdGsQH5NNrM/uXo9dtbeTkSge/NkEIrFo4ziMAhRbzEiEOJRjrMSGIJ+n8x7qS8JgnNNmUQJZY8JG/J/BOUFy3CIMhvgQ07Iv/cpBeESxY+OcNu4JhERgjgjo3zWMHG0RBuUHDsSMmC3IPJ710GazEl/e/yJYD3BuS3wrSAw/UJVjC4SO+tDG82K1kJQNqYzppasc/gFTgqm9Fa8XTGgdFPQhiTjKhj80iEg5a51RCfXWnRb4tMGMWPQVtdDnGkLacVOhrMtDYlIydo3RIry18r6GkJFg3KdSm5A5UfZFbbdGgvmtyKiQ0UfUCxkx0ue8LbBBSNydaVsCPudYb9vFxPpYYSpTLVN9aFOmsrRw7Tf5i4XEIeuC3d1T5hJWv48teJZ+cywqK4sGGgnps40+NnOJPxKDNi1hmqhISO//F9rkWmEITM64z4u4r5nj+lZlvy+X746qR1s4u65Fm29NjCqBe34txC99eonzA5lAgAiEI/uR0e8U7QqWF64t+6UQKxOvqiBT/G+eBLLjAGLWn5E9t3BNwuCf56M+XVrrFIGpVJjxqX7XgDgYHHH0lgMPcfMcz0+NYaTPIhCYmRG3Kut/ASXEDJHufvuRzGRuGSVJkiRJ+QaEssqORdj91AAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD8AAAAaCAYAAAAAPoRaAAABzklEQVR4Xu3WW1HEQBRF0WjAAhqwgAUsYAELOEACEnCAAxxgAAEwa8KBQ1cIP/BBJruqK0nfft1nZ5p2dnZ2TpTLQ3ut9vRVfERfj3n4Kv7/3B/ayzQrdzHIcHVoj4d2Ngq2AO9eT7PyDDFyO83yzXE+zaHMq/H+6GFy4zYHj968v99Ns/I83SzVgk0gzJPnvEv550/xUbaUCptg9KoQZwBFDqJi0/ne5PpT3XES+d4Iewag9BgZm6Hzvcm1R/HN5nsXtqavvTHfUwP67jfeTaHPM1ellJE+DCyKvJPDWN/WYOCsZWzW0p+17Ktfi8PUJf3aeEOtYuJaSNskoR/UgxzeobKhdTJuTBVrmIf8KYZEVoxpLodYW8sfJ+USgRmD3ifnWmX8n+/K3vQm3Wc8jzqQA2a9phXud89W3nvvnWgYoaR+ci1OcT6yGO7PsYnNcqDUh6YN+pPykeE75Sm5FNaMzwmcIU3HP9NfxUGTm7BhoiEbp17EE628uWvKe28lrKFPSHfhZVhjus9aS8X713AQHk+Osjp8s36KVIdyilTGUM48395HA8T7KZ6gqLm+e99EhLX+/FZq7y7xU/938iWWcjiFsL/7ubOzs/PBG3HPkgXH92feAAAAAElFTkSuQmCC>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAaCAYAAAAg0tunAAAB+ElEQVR4Xu2YjU3DMBCFPQMrMAMrsAIrdAVWYANGYAQ2YAM26AIdAPwpeehqnWMnTVsj3SedEjnJJff8/NOmFARBEFiecrzneMvxkuPh/HKwxGOOzxzPOb5y/KRJyJE45PiYgw5eCzW+lo0ztFvTYCbaOHaBcLhPjOZARPtOkwgE57S1oC6MgDkwBebwkGls8Ey3BnzUaT6OBiJQkP02zmnj2hJcl5NaAtIpHBEOt69GSUYDp1F8CW09LhQtAVud0YSe4iV2KI/AMdUFrAnisXT/RQIyzrEtoY/dnOwK1ArXXNVLLQ/QjnE4KroWEMRj2GrFZezzoq0rsFbxNdGad2uF7y2grZnRyJrQFJE5BNcJTc4jDeNa4XsK6AnF/YzKKrjPc5vXdk/4Hm9x21NAj2Z+bQ/sfCdRD6ZtDTxPvjXR2mtRtFfIFkG8+9nzcq3cZG8SkGSMfVsU5ziSKF9SwlDQvb3REpDpxCuENjvVqPNq1ATkG2oCes7/gxcilv1ZxAtsIubEY5qE0Wb01nibZrnGLkDMV54QoiYgecu5jhHI/c2fjIiCQPQkScrFw65OCO5NtreAguhsjvbcIqfaojXKvLCQS7WSx8u/CC/ythNlz98T/RlAYd63XspV8pfzYdPSwTn0hv4+wt4h4AZw4G6WDoIgCP4/v7fGuIY4DKb1AAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGoAAAAaCAYAAABfA8lWAAACrklEQVR4Xu2XDVHEQAxGqwELaMACFrCABSzgAAlIwAEOcIABBMC9673hI9NlChw9mMmb6XRvk2azSfbnpqlpmqZpmuaIXO6e13iePor30Jc6Dx/FzZbc756XaU7ERZHB1e553D1nVdBsC6vmepoTRdIqt9Msb07I+TRvZ6wWV1VdOcjRa04IK+Xm0L6b5kSxgpKls6vZGLY6zyVWDYl6fhfvZUvbYbMxdbWwzZEsLhDAauvz6cR4PiVe2bnlwX85nzhX/Ssh370EUaQcA3+GPJ8Stj4mTILqijs29Tz8CSQrE0Ww19ivOsSlFvBJyfMp8apOkn7zfCKwxw5IJmoNv+HD0clLQ5JX9bp1ILNSM9G87bdC/aPsys0KZ7Uiwwf62HLtQw99Ash4XmgcM/8+pIzxTFTaErc0/VjyARjXrR9yzrz5nfaxW33DL7feHxU7xj/b1nDA7S/hGydEm4DWLRLnDBDOEggnQNvkYicDAgbbQPBmogQPDAggS9uZKEBX+xaNbQoRlnzwnBbmZhxyruhhx3jgF/EAbOpXFstqdCIfHK8YhKROQDIgkHpVRtuJjYK0VED4Y3X6TbVd/Us5b1dzMvJBO9Um8Jv+KsO+Y+An8SNJznczqmOSwQP1qKgazFGirNilwGkDnZRX29W/ryYqfdDOdbTF4l4aL8fgW2KTq24TPLtyUJzhyVWQ22oNZk1U6tlXE2UFA1uLQafvWaXD7xq4UVLxkfmMfNAOybPowBhYNHW8XFHZ75a4GSaBwVnWViHtPPA5hwwCEzOhtDlv+I5Ja8uzDhk6ua97RvE9/XxjIPitjD4CxzvHps1Y6OmjgRv5gB11sE2fcyMGqYcPjsdD27HQpZ0XoE0xQZXvOLTmG3RGespG8mSkt9RXWaMj6n7lm6Zpmqb587wBolX1urN+9SkAAAAASUVORK5CYII=>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAxCAYAAABnGvUlAAACxUlEQVR4Xu3c0Y3TQBQFUNdAC9RAC7RAC7RAC3RACZRAB3RABzRAAZCr3SfNPsbObmzIJjpHsuKMx/Y4X1dvxlkWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4CDvhv0vj5/fhzYAgIuNQWP0pjewqUJafJi0AQD8JYHr12n7cdo+P35+fNJjWT61793P3nCgr6ft9/IwtgSbBMfs37p7eAYA4D9I+ElA6xKQSgJTtlGO96rQ+/b9COM4Su57D1W92bMBADyR0JPK2Cz8jGEi1beauis53tt6qNsrYXK2tuseKlMJtwIbAHBWgthaaHg77PcKXEJUzu1hKtcaz9tjK9DMAuZrlN8tz5Dfqtb/9almAIBNCRM9jM30YBZ9OjRyvdm0aNpyjbVtFvJy/bXAdiu+LQ9VyHrOWwmaAMArUgv5ux4semDLOb1PrAW2S+Sea4Ht3AsQMwmme8Y2+50ilbPZOHsIzZj77wgAcNaswjZbN9a/V0DpoW0tsNVbnWtbv05k6nAWhNIeqV5Vda7Gl2vleNbS1fq6XDvt6ZOx5XiqdxXA0rfOixwbq4fVdy2wPVfu3UMcAMBZCSE9FM2m7rIGa1Tn9JcM+rX2yljG/36rMFbqfuPLDxUA629GKpBWmEz7WrWrKncVrMbgdkRgAwC4WAJPth7USoWc0axv73OEhKeEpVngqcA2Hqv9Oqf6VGBLUBsrbCX3qZBXxgDa+79UD7cAAIdKZatPnXYJPLMQ9y9VoKrpzKhqW1UKqzpYga3OyZRqhbCaNh0ramkbq3B7A1sPgwAAh8vU5FYgu2YFaRxXQlkfZw+TfS3ZeCz7W30vkTHtDXwAAM+yFjp6QLqm/me+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAV/QGsqofcHqwWMAAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAaCAYAAABozQZiAAAAiklEQVR4XmNgGAVkATcgPkECBqmHg5VAvBOITdHE/gNxOJIYSBNIDEXzdSAWQhYAgmcMEIXoAGQzHIBM7kIWAAJlBohGFIVQALIIDjIYIIrRxUCa0Q0FgZnoAugA5l8UvxELcPmXIMDnX4IAn38JAor8+5mBTP+CUhhJ/oUFEDYMShDISXYUjEAAAP/iLUaL5SySAAAAAElFTkSuQmCC>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAaCAYAAACD+r1hAAAAjUlEQVR4XmNgGAVDHggBcTgQu0HZ6HIoYqZA/BmI/0PxdTQFJ4BYGcYBMUCKZzJATM8A4mdA3AWVB4mthLLBAMQBCSIDkCEgTSAAkoebDgIg52ADOxmwmI4PgJwEcju67TgBSAPMWUQBkIZKdEF8ABZqRAOQc9AjECdADlaiACjyiA5OEAB5mCT3DyUAAHuOGAlbFP75AAAAAElFTkSuQmCC>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABLCAYAAADNo9uCAAAExUlEQVR4Xu3d4XHrRBQFYNdAC5TA0AIt0AIt0AIdUAIl0AEd0MFrgAIgZ/LOcGdHSpQXO1Hi75vR2JZ3lVV+nbm7K18uAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGf303oCAIBz+OXh+Pfh+G79AgCAc0hY+2s9CQDAOfz6cPyxngQA4DxSXbN2DQDgxD5bYPv94fhzPbnI/aaquN7395fHqeG8AgCcxmcKbP+M918ejt/G58oUcO/358v/4SwhL58jmzD+/voeAODdfabAlnupVMoS2lYziCWsNdSlbwNb/h8z/AEAvKunAlu+y9FNCWd/7Mca2ObnmkEs99MAl7DW3bKptp39XgGAO7IX2GYlKlOE8ZJHf2Qt2XrdVLxeco2XOhLYUlXLtGgkmLUK9+PX9xn3DKkAAO9uL7AlwEwJbQ1u09Y6sVqvm7bvHdgi3+XIPXY8qbx1vAlue30BAN7cXmBbteKUqcNUqBq+Em7SP+EnbXJ0OrHtujZsBrZUsnLsyfXSfu/YmrJcA1urhBlf2+f93FzQTQfrJoNbBksAgBc5GthacWuw6ZRng02CWqYYE6Ya7jr1mDYJSQ1sPX/tx2d0ejNyX60I5n0f9ZEx5O8nwM32s8KWe7XpAAA4jSOBbQarBJ2EnwacBLDutsz7GeJ63X43q3K3kpDWQLhnVtam3FvGCABwKkfWas0F+AlbCTyd+kzFLQGpFbZU3mYVLm1b3cr5BL30y3fCEQDAAUcCWwNXJGxtrR+LrfNb5+Kp6wAAfAgJUnMd1nPTlt8i1/T4CgCAb9CpxASqTiFu7Vrs+b2juyG3WFgPAPAKc0F8H5extUj+NRLoTEkCAFzJ3jqz7mrcO9aH364SBG8x1QoAcHduNXWZwHerawMA3I2sZcuatlvZq94BAHBQpi27U/QWEtiuvT4OAOCubO0OvaYjv3Tw0eWBvQmled17jEmmhvMA4P5sVXXDx1N9AQBu6rMHtjVkbU0B93dOq23Sd7bf6gsAcHNPBbZUlva++yjW3y3dCl3dVVv9n6SvwAYAvLu9wJaqU6YHE2S6k/TIb39mCvdIsMnPXWXqMaHoJdO+68OB57E1vnUs6+dIMJ2VuLTJtfI6x7bVFwDg5vYCW3/APbrp4Wiw2gs2M1DlWglKOXf0ut9iHcv6uRIcEyDzv0ib3LPABgCcwl5gW7UiloCVMNOwFXnsSI4u1m+w6flq5SoShPJg3xnYUuV67hEmGevesfWg4DUMHgldbZO+s/2RvgAAV3c0sM0w1IpbzL4NNH1Nn06rzvN9n74NbAlqXUs2r/9acx1epnk7hkzzzvF02jfj7WNO8to2sy8AwJs6GtimTJc2VM1wtQa2Vt2OBLZ1N+c1JYxlnH2N3MP8lYeMIWPJ1OiU9mtfAIA3dSSwrUEl4SqVqMp0ac6lCpWQlmv+cHkMQGnXMJQ2DWZpk34zOOXzXOcGAMDlMTA9F9jW6td8sOxTtn5B4bm+W30AAO5awto6DQgAwMms67kAADiZTFNm/dhclwYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA3LP/ALK+Ksg866a/AAAAAElFTkSuQmCC>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEoAAAAaCAYAAAAQXsqGAAAB5klEQVR4Xu2XC1FEMQxFqwELaMACFrCABSzgAAlIwAEOcLAGEAA9+7i8O6F9v0J3mOmZyczSTdIkTbMlpcFgMPh/3GS5z3IVvxjMPGd5SVOh3tPlinWb5SlNsTyE77ZA/OSC4CvS5B+nr/Y3n3c7+QV0SCTDQRHX29fnNdAhbgrAzcAHvvgsWvynuywfWa5tjQ29cD0gWJIgGeeU5TGslaBAHjM25CXbVv9nRTZxqHLvQpEAicXrQhzEuAQ22HoR6CQKoG5p8f9tHKvMWu9CcQ1qibC+hGwpDjdDV8tp8X/uJJTcKZuxxsDrSS1grccEHW6ADpy46SS6xBugxf9ZgXuLsoQNSl3maHDuEWbhEugcTYTv4+Fq9srusH91Di3pyNCHew8OJ5LmQrkOh8ma5u9h/6UBGJ33RAHH2bKaSJpvQYQ1bgwc9q9CuQJFi2s10Nkjax2qn/O4d60TnJqOF+qwfwyiIUNxSzdxKmy8R/zhVyLOFEEixOWg453B4xhb3yPejj3+f6BXKrDZ5lfqH3FKU1GFkvXxoKL4geox6f9NlAqzxX8RFCgOvxZU9pJFAjqChEmGRIkt/tioAPH5Qi4UQs+D0it8i/8qzI61a9ETDosE6Y69cbltbSa2+B8MBoPBYDD4BPbJzZBE7jcWAAAAAElFTkSuQmCC>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABDCAYAAAAh8FnvAAAFRElEQVR4Xu3dgW3rVBQG4M7ACszACqzACqzACmzACIzABmzABizAANBffUc6OrpOnNZxQ/p9kpXGdu3r9En5dc6138sLAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMDCD6/Ld3Plq1/mCgAAzvfz6/L76/LXt/fff1sX/357BQDgE1U4S2jrr/Fn+xkA4Gn98/JWqcprAtBcsm21/JRfPknOVef7u60X2ACAL6NC2Gqe2MqPL2/7pz15hgpmdd6SEJf5bb+9vFXifn15u4ZU4c4MlADAF3dGKErVKkHoj7nhgoSi3p68pxpXAlkFtgqXCWsJcglukTHlfa/EAQBPqia5T7dWo66plmRfZqtvayxHyh2XOXcFnz3OCJOljyuBrKvPq4c2d5ACwJOrie5beltuJUEmoSLLnmC3Ol6CXP1ugkje31uFx7MqZ0fIZ1yBtipxuQ6BDQCe3KXW4JxHNdVjKNK+y7KnCrUKYzlHD45ntPjq2i5d3yOqYNs/6z1BGQC4owSZTCrP69FfzKtAlnOk7ZZtCVdbLcoEtFvlGlbVoIyhH+89x36PXFvOvXWNAABXJTxVoErQuWXO1R4JUDOwJbzUPKlsy0T3o6Qat7qGnKff6bjVps1nkLFtLbdKlapao2eFRADgySSwVaCoNuGsivVAVaEj4adaZnP/3gLtdyKW3rLMtlWbM8ecYSnLat+SbfNckXA2Q+GcaH9vR7RG6xjPsAAAN8iXZ78bMGYAuyWwzXlm2a8fKwGxV5ouTchfVcouybFmGMi61Zy2rWpXxlvz5VbLe6WqeHS7GQD4IlJVS5DIMitsCShzcn6qXFnf52TV/qu2YULXDFEVABOmUv3aeijrtYralLH2cJZxZZyr4PeR8HWrXKOwBgB8yGwPzgpb315Bpweevv88VqyqaLVfwtS1MJMWa4XBVfi6VZ+3d28JkEeM+VEljK7+vpHPOX/nM8MxAHwZM7DlC7dCxwxsWT/3n1IluxbKzpSQMSuB95BrzrmOtDVP77Ns3f1a/yZq+1YVFQA4yFaFKF/Ke1uWW1/sn+HoELVlq/K00lvS1zxKYLv2OWacFdRSJVVpA4AH9ygVtq3webRbwlok0M47Wbc8SmC79EDkyDjr755wtzeQAgDcXeatpbKUCuSlJRWntGYTbG4JMzWXL4FpdQfsrfLsuRwnx81rxrbHKjjmOnLteZ0BdLU/AMDpEn7mo0D2LHtby6lU9SC0mhs2g2FfZoUx7/u8uIx/rxnAEviqopZrmlXVM+YNAgB8urRaq4q1pe6oXS2rNmZC4Axfe/TfmTdDrMLZah0AwFPpoSivqYYdcTNHAuAMcqni1UOE62HHMyT2gJZt9T6VvPyc6l1+r7wnFAIA/K/0UJTXBKM5T+w9Kvx1OXbNj6sbKOY8u60KW0Jkfs7Y+nw4gQ0AeHqpdPW5bj0MfcSc1xZpXyYg9m0z1K3uhN0aU8LbrOIBADy8tAvnvK68TyVrTtg/W6phGUMPaQmLPaTd8kDkXNNWmAMAeAipMNUdoSWBJ4Gogkw9PHfOFfsMFcR6RW8VztL+XFXouj3//RgAwF3VpPz+kNioatTWPLNan9+tR24ccRMBAABDqlDV2uzVpqqmZVt/5lrpga1aj1vhDgCAD6rKWE2s723AHtK6Cnd196XWIQDAHVVlrB6FMZ9BljZpD2PZP5W3VOcS8rK9KnEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPxP/QfuHmhPf7ubFQAAAABJRU5ErkJggg==>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAALgAAAAaCAYAAAAE55YiAAAE0UlEQVR4Xu2YWZEUQRRFWwMW0IAFLGABC1jgkz8kIAEHOMDBGEAA9An6RFxevKyu6umdPBEZM1W5veXmUr3bTSaTyWQymUyuxLt9eV9fTu6WN7u/+XpbKyb/8nFffu3Lj335XOpGzIVwexA2+Xo5FDaoi8DAv6MgliUQR7bHuFtBkLBhrbDT7sn9wOZ0cR1925efu+Xkc6zQjjYYdWtcbFt2ZO2f3A9sUBfPCeJ2opFgqP+027ZrXpJTBH6VYE42cfGcsDOzI3/YjQXDVQZDji2CazIF/hxcPCcIm0kUTLc7c7S7EC5qzAbWCJx7Oh+iFOwfBZN2nE7UE498z/gUP4T4n7bdLwC5EdAuxwJswBbqtWkL2R8bmAM7/FUi5/T/0Qecea8+Q45Hf+agTfqcMcOmOgY4xyheMMrJ2fi6++sITnUCN5BA/T3cv+GYwPGLj2bsJ9Cj7wyS83L4y1i0oa119uHd98M7k5JJ5T2xURi0z1ghFOZR/NqzVuS0o712Mjf++b92Mgd24jeFNvojxoZ++py25HiMpS/0Qaj4Qr39vbqKmyF9radvt9guLnAMlSpgPyxBQdUFMEInt5QUzDEMahe0UZ1JE5JF4NMnf1lCSKJwUoyMlbHimXmTWp/P0IlvhIJOXCzS2Um/mjeEl/HxF6lqP++Y09PPRcACYYwkfXMBpR20x7YKce5ydRYUobiSxasJuNIyoLfAo5EApggTApl+CL6mwElE51MVBM+0TVyU+eyJ4Xgey53IoI6xhBsMQmE8ryYpIuq78YhHLg761CtD17d7B2qBmGBXjsf/Xb+lnRqdYSN+pT+vhgEz6CkAj5au7pYYDII7CkYXYKg++MyYxCFLLp414mQHQkS0peQCNLm0r/PUcZfwZ04L460RuH7mLoltvGcjcNzat3sHzOlpaHEDcCGSo+onpS4s8MrTnYKvwhWYzxiHEfXoHDm7BGNvKZ3zHZ48HpmVka0mWtgNec4YdNCmCrEKXBiLtiTYWJK0boxTYDzEqSgzT8f8Nr7Ezfu7dH27dwnCxDfHxy6veEv9ku6aeDaqQNxpeJ+rnUBsTRDj1tV7rGy5h2lTJ07ERalUgZMQnjnJEmzPd53vVeA1oR7VLlz+r9ccwAbxA67DhZMwXs47EhYCMh6jXNpXkea7Cn1r3NGMYzJXd0XsriD0yZycDZyoIhg5P7qr3pIlgRPIWkdg8Zf3GWSPxrrQtwqcsevxSj/FQgzrLwnYl6L3itOJHOExR7WTU0joW9t4euiPO2zOayzxJ8U7Eri/KCW003/jn4vXU7dydoHXu2IaougNUL3zGcB7YEngoCBIJIWEIGT9ULD4mvd62lln8LM4b/eOBHqfz4QL75mHNpa62NK2hHcuRv53985rnfnRB8bvPsbpS1tjQ1tspS19vxzqs6RNLm4XRCd4RK4txrVbuGcX+LNwTOBCvSIgwKN7PkKjbT1C12I/xt9iU4W6TuBp16i/iwzwdcmO1/hrnzVjYEcnbJkCH7BW4I8Gu92SIJZIgT8KU+ADFHj9QHxkEHY96tfgqUE8uMIc21XvCa9LkwbvpM+yi3NXPkWY9Mt7MeXUU+CaYDf3fkQ+aUAMfByx6z3a0fw/w+IjX3yc1g/gyWQymUwmk2fjD+40BJF5VScQAAAAAElFTkSuQmCC>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAaCAYAAAD1wA/qAAAB9UlEQVR4Xu3XDW3cQBCG4cNQCsUQCqVQCqVQCmFQCIFQBmVQBiUQAI0fKV+0HY3tdS7pndp7pZVz6/H8fLuzdk6nGzf+Ce7qxA4fl/GhTl6ah2V8qZMrKEDRivjxfL0Kvi7jW51suF/G7+cR+0/L+PlicUGo+3iaV1XiCvk8zFlNRV4USRizZFXGwm2zI2K8CxIY1d1DT3Rb6ddposdUysg2gKvg+f1a+KDuFmKzE9/fY3+MWNXvdbJCBQ0ZJx7w+9zltE06dYPko3Ti1f4IfLFdxUOcUJ+TVC0Bv89ZFSoSqSOrpbkD+9ofQbGbq8tAM8UwLy2BOmWOoIiuEIlSv67WWn8gp9ku1OD8LVkrJKLZCSPm1k646ULsv91mOshaITlix0+WJKrIjqlC0h9VoWCLOQQ4y1vaVSKSomL3HcWuK8R8TSrFyYXvsXeQ+5vU/hixnznJCZRGHNVLMZWcRJXEi6+88HIqKb42vBidKH/AqAsIChmcpPkTOFC4+4RgF5UreS941jXFrfkS371NVN8FGxkVpLTggZLdasI99h35yg38d37youzuHaJ+gSoiyXEuWcE6xSi9dqTOwsfutprBUo9J2lZZQYVIlE3d18H92ryz8Lm14oeoCdZtWO9XUuyeXceRf8j+Cjmqj+CZqyrixn/HE3ulidGO/pv1AAAAAElFTkSuQmCC>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAZCAYAAADnstS2AAAAo0lEQVR4Xu2SUQ2AMAwFqwELaMACFrCABSzgAAlIwAEOcIABBMCOUTKa7odPwkuaQNu9Xhki31QRorZJKxr2KxZTy4rmwSY9qXtjC556ic1wu8KtC1GGmCXDW4VYJboxlmeXF5dNYqOqlQwv4yyby6sbw5mK3Ghy5xgK6S2pASjscuPBm7Ixli9AjhoLPq4bBxpwgJ+DLAzGlPTd8n4Y+/7rnQ5Q/ye8X08LfAAAAABJRU5ErkJggg==>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAaCAYAAAC6nQw6AAAAwElEQVR4Xu2SURECMQxEowELaDgLWMACFrBwDpCABBzgAAcYQADktbdMLi18M0PfzE4hbbJNemaDwQ+ycR1c2xDbuY4pNlk9x9rlajXpafUg/1kV27surtPy++GaS2aADTmTdLN6Q0GMxHgLjNAKXZWVJFoSKs5NIpg1hcTZqnPkW3G66HK31oWbkBTR3OIjvJFLHmCvOG0hwGj1gmohBj8VV4wHySZlI8+HueTioEGjvFeq93puDi5gEj+RwX/zAm1IMvC4HKj8AAAAAElFTkSuQmCC>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADsAAAAaCAYAAAAJ1SQgAAABo0lEQVR4Xu2XgVHDMAxFPUNXYAZWYAVW6ApdgQ0YgRG6ARuwAQswQPG79LdClZ0LcHHg9O50TWJb1rdlJS0lSZK/zt3Z/jUv1U5ne3JtI3mo9lztWG3v2mBX7VCmdvrdf21ugzPEMsEWIPi3ao9lyjauESYQyjM2imvi/ijxotyg3d0CiCJwRABCiO310mPKwHdzDwi145ow0DobBYESMItvnyHOpmkUrxalu7ukiT+vOGaFZ1fpl9Fx0twI8EVT8bbEduuOP6+cFwb4c7IGzC2x7K7i4LloiYrS/QZ7XlXVmCxyaGHlcbzEKDg96MO8CBTMY2P5kVjyX5VN54JfnK2dxhLrhRAfZxm+LVb5jyOly9oCLcoyHSmhRWATJMqmNsyK3Zerc4RHVa4H45aYLzYedmtOLESiJNbv+AX/fsWB0oWF6BUovRKW2NxXDu3E4+e1aaz7lthmXfCDVEh0PSKlmfdo7n2BAjbCf0CQ1mRmE7+KrApOGIjDEbC7BG1fPfYjQ/CMNmKmH3F3Mydq3Mq/H4mIYhR6a9B3RBYmSZIkScQn0SKZhi7PEZQAAAAASUVORK5CYII=>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAaCAYAAACkVDyJAAABCklEQVR4Xu3TW1EEQQyF4daAhdWwFrCAhbWAhXWABCTgYB3gAAMIgP6qJjWnmp0Hpt9g/qrU9D3JSaa1g4ODf83TYiOnGJ/b/TO/5rXbc7f3bi+xfun21Vann8t8ise2Ovno9hZ7AuGkENS0Q1mQinnMvBgDQAYwhSw5fFjmZDSXVWFvDGA3srnFvOon81xLBabw+DXmxmO9ZFcK6Faq6AEqGPsK0F31z2B/oDbZobJNibO5rHmU6ew6kz1QTjdxsJzKRLQe47jWsr7MXv2XssmGcicV20Qm48++JU0qIMBsKD2xdW8XAqNAUaqAIw4Fk2Waglz5GDlLGQ4F40wpMM34UJYB4/7BH+EbU75BYoehw1EAAAAASUVORK5CYII=>