# Development Plan - MCP KnowledgeExplorer

## Current Project Status
**Phase:** Phase 4A Implementation (In Progress)
**Status:** ~85-90% Complete per initial implementation, Critical issues identified by review panel
**Last Review:** 2025-01-23 - Independent Review Panel Assessment
**Current Focus:** Addressing critical database, concurrency, and data integrity issues

---

## 📊 Phase 4A Implementation Status & Progress Tracking

### Implementation Summary
- **Initial Implementation:** ~85-90% complete
- **Critical Issues Found:** 8 major issues across database, integrity, and configuration
- **Action Items:** 15 concrete fixes required

### Critical Issues & Action Items (From Review Panel)

#### ✅ Priority 1: Database & Concurrency Issues (COMPLETED)
- ✅ **Fix Backend Schema Creation** - IndexedFile, IndexJob, ControlSetting models not imported in Base.metadata.create_all()
  - ✅ Add imports to `backend/app/database.py`
  - ✅ Ensure Base.metadata includes all Phase 4A tables
  - ✅ Test schema creation on fresh database

- ✅ **Fix Indexer DB Connection** - Indexer bypasses DatabaseBootstrap, missing WAL mode
  - ✅ Replace simplified DB connection in `indexer/app/main.py`
  - ✅ Import and use `backend/app/db/bootstrap.py` properly
  - ✅ Verify PRAGMAs applied (WAL, busy_timeout, foreign_keys)

#### ✅ Priority 2: Data Integrity Issues (COMPLETED)
- ✅ **Implement File Rename Handling** - Missing on_moved handler causes loss of file identity
  - ✅ Add `on_moved` handler in `indexer/app/watcher.py` (was already implemented)
  - ✅ Update IndexedFile path while preserving doc_id (enhanced doc_id generation)
  - ✅ Add rename detection logic (existing implementation verified)

- ✅ **Fix Job De-duplication** - job_signature includes created_at preventing de-duplication
  - ✅ Remove created_at from job_signature calculation
  - ✅ Use only (file_id, job_type) for uniqueness
  - ✅ Implement discovery epoch gating (was already implemented)

#### ✅ Priority 3: Configuration & Maintainability (COMPLETED)
- ✅ **Resolve Configuration Drift** - Duplicate env_config.py and conflicting sources
  - ✅ Remove `indexer/env_config.py` duplicate
  - ✅ Update `backend/app/config.py` to use Phase4AConfig
  - ✅ Create single source of truth for configuration

#### ✅ Priority 4: API Contract Issues (COMPLETED)
- ✅ **Implement Cursor-Based Pagination** - Using offset/limit instead of cursor
  - ✅ Add cursor field to search responses
  - ✅ Implement cursor parsing and continuation
  - ✅ Update MCP tool schemas for cursor parameter

#### ✅ Priority 5: Testing Infrastructure (COMPLETED)
- ✅ **Implement Critical Tests**
  - ✅ Create `test_atomic_job_claim.py`
  - ✅ Create `test_crash_recovery_and_backoff.py`
  - ✅ Create `test_watcher_correctness.py`
  - ⚠️ Fix brittle GPU detection tests (deferred - tests made conditional)

### Implementation Timeline
- **Day 1 (4-6 hours):** Critical Database Fixes
- **Day 2 (4-5 hours):** Data Integrity Issues
- **Day 3 (3-4 hours):** Configuration & API
- **Day 4 (4-6 hours):** Testing Infrastructure

### Verification Checklist
- [ ] Single database initialization creates ALL tables
- [ ] SQLite shows WAL mode active: `PRAGMA journal_mode;`
- [ ] Concurrent writes don't cause "database locked" errors
- [ ] File renames preserve doc_id and history
- [ ] Duplicate job creation prevented in race conditions
- [ ] Single configuration source used by all services
- [ ] Cursor pagination works for large result sets
- [ ] All critical tests pass
- [ ] System handles indexer crashes gracefully

---

## Phase 4 Development Plan: Advanced Search & Retrieval (Hardened)

The next development cycle will focus on implementing the "Indexer-Query" architecture to transform the application into a powerful knowledge retrieval engine. This plan incorporates extensive architectural review to ensure robustness, performance, and a high-quality user experience on a local-first deployment.

**Architectural Vision (Hardened):**
* A **three-service Docker architecture** (`backend`, `frontend`, `indexer`) provides process isolation and resilience.
* The **SQLite database will be configured for high concurrency** using `WAL` mode and a `busy_timeout`.
* A background **Indexer Service** will use a **crash-resilient job queue** with **atomic job claims** to watch the filesystem, parse documents (including OCR for scanned files), and populate optimized search indexes.
* The **Backend Service** will act as a **Query Engine**, performing fast, permission-aware searches using LlamaIndex.
* The initial implementation is de-risked using a high-performance **CPU-based embedding model** (`paraphrase-multilingual-MiniLM-L12-v2`).
* **Comprehensive `.env` configuration** enables hardware-adaptive deployment (laptop CPU-only ↔ desktop RTX 4060) with feature toggles and performance tuning.

### Phase 4A - Resilient Foundation & Monitoring (Est. 2 weeks)
*Goal: Build the resilient operational foundation and the user-facing dashboard first, delivering immediate value with metadata search tools while ensuring the system is stable, transparent, and correct under concurrent load.*

#### **0. Configuration System Foundation**
*Goal: Establish the comprehensive `.env` configuration system that will support flexible deployment across different hardware configurations.*

##### **Tests to Write First:**
* **`test_env_config_validation.py`**: Verifies that invalid `.env` values are caught with clear error messages on startup.
* **`test_hardware_detection.py`**: Tests automatic GPU availability detection and fallback to CPU when GPU is unavailable.

##### **Implementation Steps:**
1. **Create Configuration Module (`/config/env_config.py`):** Centralized configuration loader with validation for all `.env` variables.
2. **Implement Hardware Detection:** Auto-detect GPU availability and validate embedding model compatibility.
3. **Create `.env.example`:** Template file with all configuration options documented with examples.
4. **Configuration Validation:** Both `backend` and `indexer` services validate configuration on startup.

**Key `.env` Variables to Support:**
```bash
# Hardware & Model Selection (RTX 4060 Support)
INDEX_EMBED_DEVICE=cpu              # cpu/gpu - critical for hardware switching
INDEX_EMBED_QUANT=fp16              # Future: 4bit/8bit/fp16 for VRAM management
INDEX_EMBED_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# Feature Toggles
OCR_ENABLED=true                    # Tesseract OCR processing
RERANK_ENABLED=false                # Optional cross-encoder reranker

# Performance Tuning
RETRIEVAL_MODE=hybrid               # hybrid/fts/vector - debugging capability
INDEXER_BATCH_SIZE=50               # Files per batch - memory vs speed
INDEXER_MAX_WORKERS=2               # Parallel processing control
```

#### **1. Database Bootstrap & Concurrency Hardening**
*Goal: Configure SQLite for safe, concurrent multi-process access and establish schema versioning.*

##### **Tests to Write First:**
* **`test_sqlite_wal_concurrency.py`**: A load test that proves the `backend` can perform reads with stable, low latency while the `indexer` is performing sustained writes, with zero "database is locked" errors.
* **`test_schema_version_guard.py`**: Confirms that both `backend` and `indexer` services refuse to start if the database schema version does not match the application's expected version.
* **`test_health_endpoints.py`**: Verifies that the new `/live` (process up) and `/ready` (dependencies connected) endpoints for each service behave correctly.

##### **Implementation Steps:**
1.  **Create DB Bootstrap Module (`/db/bootstrap.py`):** Create a shared function run by both `backend` and `indexer` on startup that applies required PRAGMAs: `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`, `foreign_keys=ON`.
2.  **Implement Schema Versioning:** Add a `schema_version` table to SQLite. On startup, each service will assert the DB version matches its code version or exit with a fatal error.
3.  **Refine Health Checks:** Implement `/live` and `/ready` health endpoints in both `backend` and `indexer` services.

#### **2. Resilient Job Queue & Indexer**
*Goal: Implement a crash-resilient job queue with atomic claims and an intelligent file watcher.*

##### **Tests to Write First:**
* **`test_atomic_job_claim.py`**: Simulates two concurrent `indexer` workers attempting to claim jobs; asserts that each job is processed exactly once.
* **`test_crash_recovery_and_backoff.py`**: Verifies that stale `processing` jobs are re-queued on restart and that `failed` jobs are retried with exponential backoff, eventually moving to a `dead_letter` state after max retries.
* **`test_watcher_correctness.py`**:
    * Asserts jobs are only created after a file's `mtime` and `size` are stable.
    * Asserts symlinks pointing outside `/source` are ignored.
    * Asserts that file renames update the `path` in `indexed_files` while preserving the `doc_id` and `file_hash`.
    * Asserts that an initial crawl and the watcher do not create duplicate jobs due to race conditions (using a "discovery epoch").

##### **Implementation Steps:**
1.  **Refine Database Schema:** Implement the hardened `indexed_files` and `index_jobs` schemas, including `doc_id`, timestamps as UTC epoch integers, and the `job_signature` `UNIQUE` constraint.
2.  **Implement Atomic Job Claim:** In `indexer/app/queue.py`, implement the job claim logic using an `UPDATE ... RETURNING` statement, with a feature check and a 2-step `UPDATE`/`changes()` fallback for older SQLite versions.
3.  **Implement Crash Recovery:** Add logic to the indexer's startup sequence to handle stale and failed jobs.
4.  **Implement Robust Watcher:** Enhance the watcher to gate job creation on `mtime`/`size` stability. Use a single, shared function for all path canonicalization. Implement the "discovery epoch" guard.
5.  **Implement Job Retention Policy:** Add a simple scheduled task within the indexer to delete completed jobs older than 30 days.

#### **3. UI Dashboard & Indexer Control**
*Goal: Provide a transparent and controllable user experience for the indexing process.*

##### **Tests to Write First:**
* **`IndexerDashboard.test.tsx`**: Verifies the UI correctly displays all required metrics from the API.
* **`test_pause_resume_races.py`**: Asserts that after rapid toggling of the pause/resume control, the indexer respects the final state within ≤3 seconds.

##### **Implementation Steps:**
1.  **Implement SQLite Control Table:** Create a `control(key, value)` table to be the single source of truth for `indexer_paused` and `throttle_pct`.
2.  **Implement Indexer Control API:** The `backend` API endpoints will transactionally `UPDATE` the `control` table. The `status` endpoint will compute metrics from `index_jobs`.
3.  **Implement Indexer Control Polling:** The `indexer` main loop will poll the `control` table to respect the pause/resume state.
4.  **Implement Frontend Dashboard:** Build the React component to display all required metrics and wire the control buttons to the API.

#### **4. MCP Tools & Security**
*Goal: Deliver the first set of functional, secure, and production-ready search tools.*

##### **Tests to Write First:**
* **`test_permission_filter_metadata.py`**: Asserts that no path ever leaks from `list_all_files` or `search_files_by_metadata` if it is not permitted by the active workspace, including tricky cases like symlinks.
* **`test_metadata_pagination.py`**: Verifies that `limit` and `cursor` parameters return stable, non-overlapping pages of results.

##### **Implementation Steps:**
1.  **Implement Search Logic (`backend/app/services/search_service.py`):** Build the database queries for the metadata tools. Ensure all results are passed through the `PermissionService` for filtering before being returned.
2.  **Update MCP Tool Contracts:** Add pagination parameters (`limit`, `cursor`) and ensure the response payload includes `doc_id`.

---

### Phase 4B - Search Core & Quality (Est. 3 weeks)
*Goal: Implement the core keyword and semantic search functionality using the reliable CPU-based model and high-quality search algorithms.*

### Phase 4C - Security Hardening & Final Polish (Est. 2 weeks)
*Goal: Integrate the security layer, expose the final tools, and conduct stress testing.*

---
*(Detailed plans for 4B and 4C remain unchanged but will be executed on top of this hardened 4A foundation.)*