# Development Plan - MCP KnowledgeExplorer

## Current Project Status
**Phase:** Planning for Phase 4
**Status:** ✅ Phase 3B Complete. The next major feature is the implementation of the **Phase 4: Advanced Search & Retrieval** architecture.
**Next Phase:** Phase 4A - Resilient Indexer & Metadata Search

---

## Phase 4 Development Plan: Advanced Search & Retrieval (Hardened)

The next development cycle will focus on implementing the "Indexer-Query" architecture to transform the application into a powerful knowledge retrieval engine. This plan incorporates extensive architectural review to ensure robustness, performance, and a high-quality user experience.

**Architectural Vision:**
* A **three-service Docker architecture** (`backend`, `frontend`, `indexer`) will be implemented for process isolation and resilience.
* A background **Indexer Service** will watch the filesystem, parse documents (including OCR for scanned files), and populate optimized search indexes.
* The **Backend Service** will act as a **Query Engine**, performing fast, permission-aware searches against the indexes using LlamaIndex as the core framework.
* The initial implementation will use a high-performance **CPU-based embedding model** (`paraphrase-multilingual-MiniLM-L12-v2`) to eliminate GPU dependencies and ensure broad compatibility.

**Configuration-Driven Flexibility:**
* **Comprehensive `.env` strategy** enables seamless switching between hardware configurations (laptop CPU-only vs. desktop RTX 4060)
* **Feature toggles** (`OCR_ENABLED`, `RERANK_ENABLED`) provide user control over resource-intensive features
* **Performance tuning** (`RETRIEVAL_MODE`, `INDEXER_BATCH_SIZE`) allows optimization for different use cases
* **Hardware selection** (`INDEX_EMBED_DEVICE`) enables GPU acceleration when available with automatic fallback to CPU

### Phase 4A - Resilient Foundation & Monitoring (Est. 2 weeks)
*Goal: Build the resilient operational foundation and the user-facing dashboard first, delivering immediate value with metadata search tools while ensuring the system is stable and transparent.*

* [ ] **Architecture:** Implement the three-service `docker-compose.yml` structure with health checks and default resource limits for the new `indexer` service.
* [ ] **Configuration:** Establish comprehensive `.env` configuration system with hardware detection and feature toggles.
* [ ] **Database:** Extend the SQLite schema with `indexed_files` and `index_jobs` tables.
* [ ] **Indexer Service:** Build the initial service with a `watchdog`-based file watcher, debounce queue, file hashing, and the crash-recovery logic using the `index_jobs` table.
* [ ] **UI:** Create the "Indexer Dashboard" in the frontend to display live status (`Idle`, `Indexing`), key metrics, and provide **Pause/Resume controls**.
* [ ] **MCP Tools:** Implement and expose the `list_all_files` and `search_files_by_metadata` tools.

### Phase 4B - Search Core & Quality (Est. 3 weeks)
*Goal: Implement the core keyword and semantic search functionality using the reliable CPU-based model and high-quality search algorithms.*

* [ ] **Database:** Implement the `text_chunks_fts` table using SQLite's FTS5 engine, configured with the `trigram` tokenizer for typo-tolerance.
* [ ] **Indexer Service:** Integrate the `paraphrase-multilingual-MiniLM-L12-v2` embedding model with `.env`-controlled device selection (`INDEX_EMBED_DEVICE=cpu/gpu`). Extend the indexer to populate the FTS table and the Qdrant vector store.
* [ ] **Indexer Service:** Implement pre-processing for German queries to handle compound word decomposition.
* [ ] **Backend Service:** Integrate Qdrant. Implement the hybrid retrieval logic (FTS + Vector + Reciprocal Rank Fusion) within the `SearchService` with configurable retrieval modes (`RETRIEVAL_MODE`).

### Phase 4C - Security Hardening & Final Polish (Est. 2 weeks)
*Goal: Integrate the security layer, expose the final tools, and conduct stress testing.*

* [ ] **Security:** Implement the `PermissionPostprocessor` with its per-workspace bitset and LRU cache for high-performance, real-time permission filtering of search results.
* [ ] **MCP Tools:** Wire the fully secured query engine to the `search_content_by_keyword` and `search_content_by_semantic` tools.
* [ ] **API:** Enrich MCP responses with explainability fields (`matched_permission_rule_id`, source citations).
* [ ] **QA:** Conduct stress testing with a large dataset and integrate the optional reranker behind a feature flag (`RERANK_ENABLED`).
* [ ] **Feature Integration:** Complete OCR integration with user control (`OCR_ENABLED`) and performance tuning options (`INDEXER_BATCH_SIZE`, `INDEXER_MAX_WORKERS`).

---

## Phase 5 and Beyond (Backlog)

### Advanced Features
* [ ] **GPU Model Integration:** Add support for `EmbeddingGemma` or other GPU-based models as a configurable option.
* [ ] **Multi-client Management:** Handle multiple simultaneous AI clients.


### UI/UX Improvements
* [ ] **Shadcn/ui Integration:** Professional component library.
* [ ] **Dark/Light Theme:** Theme switching capability.
* [ ] **Drag and Drop:** File operations via drag and drop in the UI.

### Advanced Security & Production

* [ ] **Docker Swarm/Kubernetes:** Container orchestration for scaling.
* [ ] **Backup/Recovery:** Automated database backup systems.

---

## Completed Milestones

#### ✅ Phase 3B: Advanced UI & Full Workspace Experience (COMPLETED)
* **Deliverables:** UI for workspace management, two-panel permission editor, "Inspect Permission" feature, and architecture simplification.

#### ✅ Phase 1 - 3A (COMPLETED)
* **Deliverables:** Backend Core (MCP, File Tools), Frontend Fundamentals (Browse API, File Explorer), Config-File Permissions, and Database Migration.

---

## Definition of Done

Each task is considered complete when:

### Backend Tasks
* [x] Code follows FastAPI best practices.
* [x] Comprehensive error handling implemented.
* [x] Unit and integration tests are written and passing for all new logic.
* [x] Logging is added for debugging and auditing.
* [x] Documentation (`CLAUDE.md`, specs) is updated.

### Frontend Tasks
* [x] Component follows React best practices with TypeScript.
* [x] State management is properly integrated.
* [x] Error and loading states are handled gracefully.
* [x] The user workflow is tested and documented.

---

## Development Guidelines

### Code Quality Standards
* **Python:** Follow PEP 8, use type hints, comprehensive docstrings.
* **TypeScript:** Strict mode enabled, explicit types, JSDoc comments.
* **Testing:** New logic requires comprehensive unit tests. New features require end-to-end integration tests.
* **Documentation:** Update relevant spec files and `CLAUDE.md` with every significant change.

### Git Workflow
* Feature branches for each task, aligned with the phased plan.
* Clear commit messages following conventional commits.
* Pull request reviews for all changes.