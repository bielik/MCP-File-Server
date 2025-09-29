# Ticket 019: Force Reindex ("Fresh Start") Database Feature

**Status:** ✅ Implemented
**Priority:** Medium
**Type:** Feature
**Component:** Indexer + Frontend
**Estimated Effort:** Large (5-7 days)
**Created**: 2025-01-29
**Last Updated**: 2025-01-29
**Implemented**: 2025-01-29

## Summary

Add a **Force Reindex** capability that admins can trigger from the **Indexer** tab in the web UI. This performs a clean re-build of the content index for a selectable scope (all files or subset). Designed as a **rare, heavyweight maintenance action** to recover from drift, pipeline bugs, or large refactors—without requiring SSH access.

## Goals

* One-click (with confirmations) **fresh start** of indexing:
  * **Option A**: **Soft full reindex** — keep `indexed_files`, clear indexing flags, enqueue `reindex_file` for all in-scope files
  * **Option B**: **Hard reset** — additionally purge `document_chunks` (+ FTS) and wipe pending jobs before re-queuing
* Visible **progress & status** in the UI (counts, rate, ETA-ish)
* **Idempotent & crash-safe** execution (transactional where it matters)
* **Admin-only** with double-confirmation

## Non-Goals

* Doesn't change permission rules or source mounts
* Doesn't change the watcher logic (though worker will be paused during reset)
* No "point-in-time" restore (this is rebuild-only, not backup)

## User Stories

* *As an admin*, I can open the Indexer tab, click **Force Reindex**, choose **Soft** or **Hard**, optionally filter scope, confirm, and watch progress
* *As an admin*, I can **cancel** an in-flight Force Reindex (stops creating new jobs; already-running jobs finish)
* *As an admin*, I can view a **history** of force-reindex batches and their outcomes

## UX Design (Frontend)

### Indexer Tab Enhancements

**New Button**: **Force Reindex** (dropdown):
* **Soft Reindex (recommended)**
* **Hard Reset (purge & rebuild)**

**Modal Flow** (multi-step):

1. **Scope Selection**:
   * All files
   * Path prefix (text input, optional)
   * File types: [text-only ✅] [all files ☐]

2. **Mode Selection**: Soft / Hard (with warnings)

3. **Dry Run**: checkbox (show counts only)

4. **Confirmation**: type `REINDEX` and click **Run**

**Batch Status Panel** (sticky on page after start):
* Status badge: `PLANNING | RUNNING | PAUSED | CANCELLING | COMPLETED | FAILED`
* Counters: `planned / queued / processed / errors`
* Buttons: **Pause**, **Resume**, **Cancel**
* Log tail (last N events)

## API Design (FastAPI)

### 1. Create Batch (Plan or Execute)

**Endpoint**: `POST /admin/reindex/force`

**Request Body**:
```json
{
  "mode": "soft" | "hard",
  "scope": {
    "path_prefix": "/optional/subdir",
    "text_only": true
  },
  "dry_run": false
}
```

**Response**:
```json
{
  "batch_id": "uuid",
  "status": "PLANNING" | "RUNNING" | "COMPLETED",
  "counts": {
    "candidates": 12345,
    "jobs_created": 0
  }
}
```

### 2. Get Batch Status

**Endpoint**: `GET /admin/reindex/batches/{batch_id}`
**Returns**: batch metadata, counters, recent log lines

### 3. Control Batch

* `POST /admin/reindex/batches/{batch_id}/pause`
* `POST /admin/reindex/batches/{batch_id}/resume`
* `POST /admin/reindex/batches/{batch_id}/cancel`

**Security**:
* Admin role or API token required (403 otherwise)
* Rate limiting: Only 1 active `RUNNING` batch system-wide (409 if another exists)

## Data Model Changes

### New Table: `reindex_batches`

```sql
CREATE TABLE reindex_batches (
    id TEXT PRIMARY KEY,  -- UUID
    mode TEXT NOT NULL CHECK (mode IN ('soft', 'hard')),
    path_prefix TEXT NULL,
    text_only BOOLEAN DEFAULT true,
    status TEXT NOT NULL CHECK (status IN ('PLANNING','RUNNING','PAUSED','CANCELLING','COMPLETED','FAILED')),
    created_at DATETIME NOT NULL,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    candidates_count INTEGER DEFAULT 0,
    jobs_created INTEGER DEFAULT 0,
    files_processed INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0,
    last_error TEXT NULL
);
```

### Optional: `system_flags` Table

```sql
CREATE TABLE system_flags (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME NOT NULL
);
-- maintenance_mode BOOL (indexer worker & watcher idle when true)
```

### Index Enhancement

```sql
-- Dedupe bulk job insertion
CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_file_type_batch
ON index_jobs(file_id, job_type, batch_id);
```

## Backend Implementation Strategy

### Orchestration Flow

1. **Authorize** & validate no other `RUNNING` batch exists
2. **Set `maintenance_mode=true`** so watcher/worker loops pause
3. **Build candidate file set**:
   * Query `indexed_files` (optionally filtered by `path_prefix` and `file_type`)
   * Set `candidates_count = N`
4. **If `dry_run`**: return counts and leave `maintenance_mode=false`
5. **If soft reindex**:
   * Process in chunks of 5k files:
     * `UPDATE indexed_files SET is_indexed=0, last_indexed_at=NULL, index_version=NULL WHERE id IN (...)`
     * **Bulk insert** `reindex_file` jobs for the chunk
6. **If hard reset**:
   * Inside transaction(s):
     * `DELETE FROM document_chunks WHERE file_id IN (...)` (or whole table if scope==all)
     * **FTS**: `DELETE FROM chunks_fts` or drop/recreate virtual table if full reset
     * `DELETE FROM index_jobs WHERE status IN ('PENDING','FAILED','RUNNING')` (scoped)
     * `UPDATE indexed_files ...` as in soft mode
     * **Bulk insert** `reindex_file` jobs for the chunk
7. **Set `maintenance_mode=false`**, kick worker, mark batch `RUNNING`
8. **Track progress** by monitoring job updates and aggregating into `reindex_batches` counters

### Worker/Watcher Cooperation

* Watcher & worker check `maintenance_mode` in their loops and sleep when true
* Job processing remains unchanged
* **Transactional requirement**: parent job should only complete after children are created

### Idempotency & Crash Safety

* Batch has stable `batch_id` for retry scenarios
* **Deduplication**: `reindex_file` jobs use `(file_id, job_type, batch_id)` unique constraint
* **Crash recovery**: On restart, batch resumes using `jobs_created` and cursor tracking

## SQL Implementation Sketches

### Soft Reindex Chunk Update
```sql
UPDATE indexed_files
SET is_indexed = 0, last_indexed_at = NULL, index_version = NULL
WHERE id IN (:chunk_ids);
```

### Bulk Job Insert (SQLAlchemy)
```python
rows = [
  {"file_id": fid, "job_type": "reindex_file", "batch_id": batch_id, "status": "PENDING"}
  for fid in chunk_ids
]
session.execute(IndexJob.__table__.insert().prefix_with("OR IGNORE"), rows)
```

### Hard Reset (Full Scope)
```sql
DELETE FROM document_chunks;          -- or scoped delete by file_id
DELETE FROM chunks_fts;               -- or DROP/CREATE VIRTUAL TABLE
DELETE FROM index_jobs WHERE status IN ('PENDING','FAILED','RUNNING');
UPDATE indexed_files SET is_indexed=0, last_indexed_at=NULL, index_version=NULL;
```

## Security & Guardrails

* **Admin-only API** with CSRF token if using cookies
* Modal requires typing **`REINDEX`** to confirm
* **Single active batch** globally enforced
* Hard reset warning: "This will temporarily remove search results until rebuild completes"

## Observability & Monitoring

* **Structured logs**: `force_reindex batch=<id> mode=<soft|hard> scope=<all|prefix> planned=<N> queued=<N>`
* **Metrics**: `indexer.force_reindex.planned`, `...queued`, `...processed`, `...errors`, duration
* **UI log tail**: Recent events from circular buffer in DB or application log fetch

## Risk Mitigation

* **Large DB lock times**: Process in chunks; avoid long exclusive locks
* **Race with watcher**: `maintenance_mode` prevents concurrent writes
* **Queue floods**: Enforce backpressure (max outstanding jobs) or rate-limit creation

## Implementation Phases

### Phase 1: Backend Foundation ✅
- [x] Add `reindex_batches` table and model (`backend/app/models/reindex.py`)
- [x] Add `system_flags` table for `maintenance_mode`
- [x] Implement API endpoints (`/admin/reindex/force`, status, control)
- [x] Add `maintenance_mode` checks to watcher/worker loops

### Phase 2: Core Logic ✅
- [x] Implement soft reindex chunked processing
- [x] Implement hard reset with transactional safety
- [x] Add batch progress tracking and status updates
- [x] Implement idempotent job creation with deduplication

### Phase 3: Frontend Integration ✅
- [x] Add Force Reindex dropdown button to Indexer tab
- [x] Implement multi-step confirmation modal
- [x] Add batch status panel with real-time updates
- [x] Add pause/resume/cancel controls

### Phase 4: CLI & Testing ✅
- [x] CLI script for programmatic access (`scripts/trigger_reindex.py`)
- [x] End-to-end testing with dry run capability
- [x] System status and batch management commands
- [x] Windows compatibility fixes (Unicode characters)

## Testing Strategy

### Unit Tests
* API authentication & validation (bad mode, prefix)
* Chunked updates don't exceed batch size
* Idempotent inserts via unique index
* `maintenance_mode` respected by watcher/worker loops

### Integration Tests
* Soft reindex (prefix & all): creates correct job count, rebuilds search results
* Hard reset: chunks/FTS cleared then rebuilt, no orphan rows, FTS matches chunks
* Cancel/pause/resume state transitions

### Failure Injection Tests
* Crash after half the bulk inserts → restart resumes without duplicates
* Kill app during hard reset → DB remains consistent (smaller transactions)

## Acceptance Criteria (Definition of Done)

- [x] Admin can trigger **Soft** and **Hard** force reindex from Indexer tab with confirmation modal
- [x] API enforces **single active batch**, **admin-only access**, and **scope options**
- [x] Progress panel shows live counts and final "Completed" status with totals
- [x] After completion, **entire in-scope corpus is searchable** and matches filesystem
- [x] Logs & metrics present; dry-run shows candidate counts without side effects
- [x] CLI tool for programmatic access

## Dependencies & Prerequisites

### Required
* **Transactional parent/child job creation** fix (prevents "indexed but not searchable" gaps)
* Admin authentication system in place
* Existing indexer pipeline operational

### Optional Future Enhancements
* **History view** of past batches
* **CSV export** of processing failures
* **Email notifications** for batch completion/failure

## Estimated Timeline

* **Phase 1**: 1-2 days (Backend foundation)
* **Phase 2**: 2-3 days (Core logic implementation)
* **Phase 3**: 1-2 days (Frontend integration)
* **Phase 4**: 1-2 days (Testing & polish)

**Total**: 5-7 days for complete implementation

## Related Issues

* Ticket 017: Incomplete reindex pipeline (prerequisite fix)
* Ticket 018: Misleading dashboard file status (related UX improvements)

---
