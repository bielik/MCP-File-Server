# Ticket 021 Implementation Status

## Overview
Implementation of fix for dual pipeline conflict issue where old and new indexing systems were running simultaneously, causing inconsistent dashboard metrics and stale FTS data.

## ✅ COMPLETED STEPS

### Step A: Canonicalize Reindex Entry Point (Core Jobs Only) - **COMPLETE**

**Problem Solved:**
- Force Reindex was creating parent jobs (`index_file`/`reindex_file`) that spawned child jobs inconsistently
- Batch tracking was ambiguous
- Dashboard showed paradoxical states (FTS > CHUNK)

**Implementation:**
1. **Modified `ReindexService._create_reindex_jobs()`** (`backend/app/services/reindex_service.py:226-263`)
   - Changed from creating `index_file`/`reindex_file` jobs to creating `TEXT_EXTRACT` jobs directly
   - All jobs now receive `batch_id` for proper tracking
   - Bypasses legacy parent job system for batch operations
   - Parent jobs still used by file watcher for incremental operations

2. **Tests Created:** `backend/tests/test_reindex_core_jobs.py`
   - ✅ 7 tests all passing
   - Validates core job creation, batch_id propagation, no parent jobs

**Files Changed:**
- `backend/app/services/reindex_service.py` (modified)
- `backend/tests/test_reindex_core_jobs.py` (created)

---

### Step B: True Clean Reset + Maintenance Mode - **COMPLETE**

**Problem Solved:**
- No atomic way to reset all indexing state
- Workers could interfere during reset operations
- FTS data could become stale and reused

**Implementation:**
1. **Added `ReindexService.full_reset()` method** (`backend/app/services/reindex_service.py:476-527`)
   - Deletes all document chunks (FTS triggers handle FTS cleanup automatically)
   - Deletes all index jobs (pending, failed, completed, dead_letter)
   - Resets indexed file metadata (is_indexed, last_indexed_at, index_version → NULL)
   - Sets maintenance mode during execution
   - Fully transactional with rollback on failure
   - Always clears maintenance mode in finally block

2. **Added API endpoint:** `POST /admin/reindex/full-reset-now` (`backend/app/api/reindex.py:426-475`)
   - Admin-only access with API key authentication
   - Returns statistics (chunks deleted, jobs deleted, files reset)
   - Calls `ReindexService.full_reset()`

3. **Added maintenance mode check** (`indexer/app/queue.py:102-133`)
   - Modified `JobQueueManager.claim_job()` to check maintenance mode before claiming
   - Returns None if maintenance_mode is active, preventing processing during reset

4. **Tests Created:** `backend/tests/test_reindex_reset_maintenance.py`
   - ✅ 7 tests all passing
   - Validates full reset, maintenance mode blocking, transactional safety

**Files Changed:**
- `backend/app/services/reindex_service.py` (added `full_reset()` method)
- `backend/app/api/reindex.py` (added endpoint)
- `indexer/app/queue.py` (added maintenance mode check)
- `backend/tests/test_reindex_reset_maintenance.py` (created)

---

## 🔄 REMAINING STEPS (NOT YET IMPLEMENTED)

### Step C: FTS Batch Safety

**What needs to be done:**
1. Modify `ReindexService._execute_hard_reset()` to truncate FTS table:
   ```python
   session.execute(text("DELETE FROM chunks_fts"))
   ```

2. Update `JobProcessor._process_fts_index()` in indexer to filter chunks by batch_id

3. **Tests to create:** `backend/tests/test_reindex_fts_safety.py`
   - Test FTS truncate and rebuild
   - Test batch filtering prevents cross-batch contamination

**Files to modify:**
- `backend/app/services/reindex_service.py`
- `indexer/app/queue.py` (_process_fts_index method)

---

### Step D: Monitoring & Dashboard (Batch-Aware)

**What needs to be done:**
1. **Backend API enhancements:**
   - Enhance `/admin/reindex/batches/{batch_id}` to return batch-scoped job statistics
   - Add endpoint for job type breakdowns by batch
   - Add consistency validation (FTS_completed <= CHUNK_completed)

2. **Frontend Dashboard updates:** `frontend/src/components/IndexerDashboard.tsx`
   - Add batch selector dropdown
   - Filter pipeline metrics by selected batch_id
   - Add consistency validator with visual flag
   - Display legacy job banner if parent jobs detected
   - Rename "Force Reindex" button to "Rebuild Index (Hard)"

3. **Tests to create:** `backend/tests/test_reindex_dashboard_batch.py`
   - Test batch-scoped statistics API
   - Test consistency rules

**Files to modify:**
- `backend/app/api/reindex.py` (enhance endpoints)
- `frontend/src/components/IndexerDashboard.tsx` (major UI changes)

---

### Step E: Observability & Guardrails

**What needs to be done:**
1. **Enhanced logging in indexer:** `indexer/app/queue.py`
   - Add structured logging to `_process_chunk()` with batch_id, file_id, chunks_created
   - Add batch_id to all log messages in job processing pipeline

2. **Startup validator:** `indexer/app/main.py`
   - Add check for unknown job types on startup
   - Fail fast if invalid job types detected post-migration

3. **Batch-scoped retry methods:** `backend/app/services/reindex_service.py`
   - Add methods to retry failed jobs by batch and stage

4. **Tests to create:** `backend/tests/test_reindex_observability.py`
   - Test structured logging output
   - Test startup validator
   - Test batch-scoped retry operations

**Files to modify:**
- `indexer/app/queue.py` (enhanced logging)
- `indexer/app/main.py` (startup validator)
- `backend/app/services/reindex_service.py` (retry methods)

---

## 🎯 CRITICAL NEXT STEPS

Given that Steps A and B fix the **core architectural problem** (dual pipeline conflict), the system now has:

✅ Single-tier core job creation (no parent jobs in batches)
✅ Atomic full reset capability
✅ Maintenance mode protection
✅ Batch-aware job tracking

**Recommended Priority:**

1. **Step C (FTS Batch Safety)** - HIGH PRIORITY
   - Prevents stale FTS data reuse
   - Simple implementation (truncate on reset)
   - Critical for data consistency

2. **Step D (Dashboard Batch Awareness)** - MEDIUM PRIORITY
   - Fixes UI paradoxes
   - Improves user experience
   - Not blocking for backend functionality

3. **Step E (Observability)** - LOW PRIORITY
   - Nice-to-have improvements
   - Can be added incrementally
   - Not blocking for core functionality

---

## TEST COVERAGE SUMMARY

**Implemented:**
- ✅ Step A: 7 tests (100% passing)
- ✅ Step B: 7 tests (100% passing)
- **Total: 14 tests, 0 failures**

**Still needed:**
- ⏳ Step C: FTS batch safety tests
- ⏳ Step D: Dashboard batch awareness tests
- ⏳ Step E: Observability and guardrail tests

---

## FILES CREATED

1. `backend/tests/test_reindex_core_jobs.py` - Step A tests
2. `backend/tests/test_reindex_reset_maintenance.py` - Step B tests
3. `tickets/021-IMPLEMENTATION-STATUS.md` - This file

---

## FILES MODIFIED

1. `backend/app/services/reindex_service.py`
   - Changed `_create_reindex_jobs()` to create TEXT_EXTRACT directly
   - Added `full_reset()` method

2. `backend/app/api/reindex.py`
   - Added `POST /admin/reindex/full-reset-now` endpoint

3. `indexer/app/queue.py`
   - Added maintenance mode check in `claim_job()`

---

## DEPLOYMENT NOTES

**Safe to deploy now:**
- ✅ Steps A and B are backward compatible
- ✅ Existing parent jobs (from watcher) continue to work
- ✅ Only batch reindex behavior changed
- ✅ Full reset is additive (new endpoint)
- ✅ Maintenance mode check is safety-only (doesn't break normal operation)

**Validation after deploy:**
1. Trigger a Force Reindex
2. SQL query: `SELECT job_type, batch_id, COUNT(*) FROM index_jobs WHERE batch_id IS NOT NULL GROUP BY job_type, batch_id`
3. Should see only TEXT_EXTRACT/CHUNK/FTS_INDEX jobs (no index_file/reindex_file)
4. Dashboard should show jobs progressing without paradoxes

**Rollback plan:**
- Revert `reindex_service.py` change to restore parent job creation
- Remove maintenance mode check from `queue.py`
- No database migration needed (changes are code-only)

---

## CONCLUSION

✅ **Core problem solved:** Dual pipeline conflict eliminated
✅ **Primary objectives achieved:** Single-tier pipeline, atomic reset, safety mechanisms
🔄 **Remaining work:** UI polish, FTS safety, observability enhancements

**The system is now in a stable state where:**
- Batch reindex operations use the correct single-tier pipeline
- Full reset capability available for recovery scenarios
- Maintenance mode prevents worker interference
- All changes are fully tested and backward compatible

*Steps C, D, and E can be implemented incrementally without blocking production deployment of the core fixes.*