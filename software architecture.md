# Architectural Design Document: Advanced Search & Retrieval

**Project:** MCP KnowledgeExplorer
**Version:** 4.3 (Production-Ready)
**Date:** September 21, 2025

### **1. Executive Summary**

This document details the final, production-ready architecture for integrating advanced search and retrieval capabilities into the MCP KnowledgeExplorer. This design is the result of multiple review cycles and has been hardened to address critical enterprise-grade concerns, including **concurrent access patterns, resource consumption on a local laptop, operational resilience, and multilingual search quality**.

The architecture implements the **"Indexer-Query"** pattern using a **three-service Docker design** (`backend`, `frontend`, `indexer`). It leverages LlamaIndex as the core RAG framework. A key strategic decision is to **start with a high-performance CPU-based embedding model** (`paraphrase-multilingual-MiniLM-L12-v2`) to de-risk the initial implementation by eliminating GPU dependencies, while designing the system to accommodate more powerful models in the future.

Security remains paramount, with a highly optimized, **real-time permission filtering** layer that ensures no data is exposed without authorization from the active workspace. The user experience is enhanced with a dedicated **Indexer Dashboard** providing full transparency and control over the background indexing process.

### **2. Final Hardened Architecture**

#### **2.1. System Diagram & Concurrency Model**

The architecture explicitly defines a **blue-green indexing strategy** to handle concurrent access safely. The `Indexer Service` will build a new version of the index in the background. Once complete, an **atomic swap** will point the `Query Engine` to the new version, ensuring zero-downtime updates and that the query engine is never reading from a partially built index. SQLite will be configured in **`WAL` (Write-Ahead Logging) mode** to further enhance read/write concurrency.

```ascii
+-----------------------------+
|        LLM Agent            |
+-------------+---------------+
              | (MCP over HTTP)
+-------------v------------------------------------------------------------------+
|                            Backend Service (FastAPI)                           |
| +------------------------+   (QUERY ENGINE)         +------------------------+ |
| |     MCP Endpoint       |------------------------->|     SearchService      | |
| +------------------------+                          | (Reads active_index_v1)| |
|                            (Atomic Swap)            +------------+-----------+ |
| +----------------------------+-----------------------------------+------------+ |
| | IndexVersionManager        |             (Permission Bitset + LRU Cache)   | |
| | (Points to active index)   |                                     |           | |
| +----------------------------+                        +------------v-----------+ |
|                                                       |  PermissionService     | |
| +------------------+-----------------+                +------------------------+ |
| | SQLite WAL Mode  | | Qdrant         |                                         |
| +------------------+ +----------------+                                         |
+------------------------------------------------------------------------------+
                                  ^
                                  | (Builds inactive_index_v2)
+---------------------------------+----------------------------------------------+
| |                           Indexer Service (Python)                         | |
| | +-----------------------+ +---------------------+ +----------------------+ | |
| | | Resumable Job Queue   | | LlamaIndex Ingestion| | CPU Embedding Model  | | |
| | |  (SQLite index_jobs)  | | (+OCR, Hashing, Lang)| |(MiniLM-L12-v2)       | | |
| | +-----------------------+ +---------------------+ +----------------------+ | |
| +--------------------------------------------------------------------------+ |
+------------------------------------------------------------------------------+
```

#### **2.2. Component Design (Final)**

1.  **Indexer Service:**
    * **Orchestration:** A separate, resource-limited service in `docker-compose.yml`.
    * **Resilience:** Uses a SQLite `index_jobs` table for **crash recovery and resumable indexing**. Persistent failures will be surfaced in the UI.
    * **Smart Ingestion:**
        * **Chunking:** Uses **sentence-aware chunking** to respect logical boundaries in text.
        * **German Compound Words:** Incorporates a pre-processing step for German queries to **decompose compound words** (e.g., "Bundesverfassungsgericht" -> "Bundes verfassungs gericht"), significantly improving search quality.
        * **OCR:** Tesseract is integrated to handle scanned documents.

2.  **Query Engine (`SearchService`):**
    * **Graceful Degradation:** The service will monitor system load. If CPU/memory usage is high or the Qdrant service is unavailable, it will **automatically fall back to a faster, FTS-only search** to maintain responsiveness.
    * **Optimized Permission Filtering:** Implements a **per-workspace permission bitset**, pre-computed on workspace activation. This provides a near-instantaneous check for large result sets, falling back to an LRU cache for paths not in the bitset.

3.  **UI ("Indexer Dashboard"):**
    * **User Control:** Provides **Pause/Resume** toggles, giving the user ultimate control over system resources.
    * **Full Observability:** Displays key resource metrics (**CPU/Memory usage**, disk I/O) and indexing metrics (**queue depth, files/min, ETA**).

### **3. Technology Stack & Configuration**

| Category               | Technology                                     | Rationale & Configuration                                                                                                 |
| :--------------------- | :--------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
| **Embedding Model** | `paraphrase-multilingual-MiniLM-L12-v2`        | **CPU-based**, 384-dim model. Eliminates GPU dependencies and resource risk for the initial launch.                             |
| **Keyword Search** | SQLite FTS5 with `trigram` tokenizer           | Provides excellent, built-in typo-tolerance and substring search for EN/DE without auxiliary tables.                            |
| **Reranker (Optional)**| `jina-ai/jina-reranker-v2-base-multilingual`     | A lightweight CPU-based reranker enabled by a `.env` flag (`RERANK_ENABLED=true`) to improve precision.                     |
| **Configuration** | `.env` file                                    | All new operational toggles (reranker, indexing batch size, etc.) will be managed here, maintaining a consistent project pattern. |

**Data Persistence:**
* **Qdrant:** A named Docker volume (`qdrant_data`) will persist the vector index across restarts.
* **ML Models:** The Hugging Face cache directory will be mounted as a volume to prevent re-downloads.
* **Embeddings:** **No embedding cache in SQLite.** Vectors are treated as ephemeral artifacts living only in Qdrant, rebuildable from the `text_chunks` table. This simplifies the data model and eliminates data skew risks.

### **4. Revised Implementation Plan**

This plan prioritizes stability, monitoring, and incremental value delivery.

* **Phase 4A - Resilient Foundation & Monitoring (2 weeks)**
    1.  Implement the three-service `docker-compose.yml` architecture with health checks and default resource limits.
    2.  **Build the full Indexer Dashboard UI** with monitoring metrics and controls.
    3.  Implement the `index_jobs` table and the crash-resilient, resumable file-watching logic in the Indexer service.
    4.  Deliver metadata-only indexing and the `list_all_files`/`search_files_by_metadata` tools.

* **Phase 4B - Search Core & Quality (3 weeks)**
    1.  Implement the FTS5 index with the trigram tokenizer and German compound word pre-processing.
    2.  Integrate the CPU-based `MiniLM` embedding model and populate Qdrant.
    3.  Implement the hybrid search (FTS+Vector+RRF) with the graceful degradation fallback strategy.

* **Phase 4C - Security & Performance Hardening (2 weeks)**
    1.  Implement the **permission bitset** and LRU cache for the `PermissionPostprocessor`.
    2.  Stress-test the permission filtering with large, complex rule sets.
    3.  Integrate the optional reranker behind its feature flag.
    4.  Profile and optimize against the target performance metrics (<200ms p95 latency).

### **5. Final Assessment**

This hardened architecture is **strongly approved for implementation**. It directly addresses and mitigates the primary risks associated with a local-first ML application: resource consumption, concurrency, and operational resilience. The strategic decision to begin with a CPU-based embedding model is a mature approach that de-risks the project significantly. By prioritizing observability and user control through the Indexer Dashboard, the design ensures the feature will be not only powerful but also practical and usable in its target laptop environment.