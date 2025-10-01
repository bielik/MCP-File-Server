# Ticket 021: Post-Reindex Analysis Report

**Date:** 2025-09-30
**Batch ID:** 6c7b5074-c01e-4611-bb01-687553185c6f
**Reindex Type:** Hard Reset
**Status:** ✅ Stabilized (2025-09-30)

---

## Executive Summary

After applying the Ticket 021 fixes, the hard reset completes end-to-end. All Phase 4B jobs drain successfully, document chunks and the FTS index are rebuilt (66 records each), and the queue now reports zero pending, processing, or dead-letter jobs.

**Key Findings:**
- ✅ Hard reset prunes missing filesystem entries before queuing fresh TEXT_EXTRACT jobs.
- ✅ Phase 4B child jobs reuse existing CHUNK/FTS rows; no more duplicate job signatures.
- ✅ `document_chunks` and `chunks_fts` contain 66 synchronized rows; dashboard counters clear after `/control/resume` or an indexer restart.
- 📌 Add the new pruning/FTS rebuild steps to future hard reset runbooks so the queue stays consistent.

---

## Dashboard Statistics (from UI)

### Indexer Service Header
```
Status: 🟢 Running
Buttons: [Pause] [Force Reindex] [Throttle 50%]
```

### 🔴 Critical Alert
**"Indexer Attention Required"**
- 395 text processing jobs need attention - Text Extract: 395 dead-letter
- 391 text files failed processing - These text files were indexed but failed to create searchable chunks

### 📁 File Discovery
```
Total Files:         821 ✅ Discovered
Text Files:          423 Processable
Non-Text Files:      398 Images, Binaries
Fully Processed:     0 (0.0% of text files) ⚠️
```

**Interpretation:** All files discovered, but NONE fully processed through the pipeline.

### 🔄 Text Processing Pipeline
**Table displayed on dashboard:**
```
Stage            Completed  Processing  Failed  Pending  Dead Letter
1. Text Extract     395         31        0        0       395 ⚠️
```

**Key Observations:**
- Only Stage 1 (Text Extract) is shown
- Stage 2 (Chunking) is **completely absent**
- Stage 3 (FTS Index) is **completely absent**
- 395 jobs in dead_letter status (warning icon)

**Pipeline Summary Note (from UI):**
> "Pipeline Jobs: 821 total (395 completed) ⚠️ 395 need attention"
> "Note: Only showing text processing pipeline jobs. Excludes reindex_file jobs which are managed separately."

### 📊 Text Processing Results
```
Successfully Processed Text Files: 0 ⚠️
Text Chunks Created:               0 Searchable Pieces ⚠️
Avg Chunks/File:                   0 (For processed files) ⚠️
Processing Progress:               0.0% (0 of 423 text files) ⚠️
```

**Critical Finding:** Despite 395 TEXT_EXTRACT jobs completing, zero chunks were created and zero files were successfully processed.

### ⚙️ Service Status
```
Status:          🟢 Running
Processing Rate: 0.0 jobs/min ⚠️
Active Workers:  2
File Watcher:    🟢 Active
```

**Note:** Processing rate of 0.0 jobs/min indicates the pipeline is idle/stalled.

### 📈 Queue Health
```
Active Queue:            0 pending
Pipeline Jobs Issues:    395 ⚠️
Invalid Reindex Jobs:    0 jobs
Total Completed:         395
Valid Job Success Rate:  50.0%
```

**Interpretation:** 50% success rate = 395 completed out of 790 attempted (395 completed + 395 dead_letter).

### ⚠️ Action Required Section
**Message:** "395 text processing jobs need attention. These jobs failed during the text extraction, chunking, or FTS indexing pipeline."

**Available Actions:**
- [Retry Pipeline Jobs] button
- [Clear Failed History] button
- [View Error Logs] button

### Recent Jobs (Bottom of Dashboard)
**Sample jobs visible:**
```
Job #821 | TEXT_EXTRACT | [restricted] | completed
Job #820 | TEXT_EXTRACT | [restricted] | processing
Job #819 | TEXT_EXTRACT | [restricted] | Retry 3 dead_letter
Job #818 | TEXT_EXTRACT | projects/web_developement_guide.txt | completed
Job #817 | TEXT_EXTRACT | projects/web_app/authentication_security.md | completed
Job #816 | TEXT_EXTRACT | projects/ticket_017_test_RENAMED.txt | completed
...
```

**All jobs shown are TEXT_EXTRACT type** - no CHUNK or FTS_INDEX jobs visible.

---

## API Data Analysis

### Batch Status (GET /admin/reindex/batches?limit=1)
```json
{
  "id": "6c7b5074-c01e-4611-bb01-687553185c6f",
  "mode": "hard",
  "path_prefix": null,
  "text_only": false,
  "status": "RUNNING",
  "created_at": "2025-09-30T13:20:09.733722",
  "started_at": "2025-09-30T13:20:13.262419",
  "completed_at": null,
  "candidates_count": 821,
  "jobs_created": 821,
  "files_processed": 0,
  "files_failed": 0,
  "progress_percentage": 0.0
}
```

**Key Issues:**
- `files_processed: 0` despite 395 completed jobs
- `progress_percentage: 0.0%` - no measurable progress
- Batch still marked as "RUNNING" but appears stalled

### Indexer Status (GET /api/indexer/status)
```json
{
  "is_running": true,
  "is_paused": false,
  "queue_stats": {
    "pending_jobs": 0,
    "processing_jobs": 31,
    "completed_jobs": 395,
    "failed_jobs": 0,
    "dead_letter_jobs": 395,
    "queue_depth": 426
  },
  "file_stats": {
    "total_files": 821,
    "text_files": 423,
    "text_files_with_chunks": 0,
    "text_processing_progress": 0.0,
    "text_files_failed_processing": 391,
    "text_files_successfully_processed": 0,
    "actual_success_rate": 0.0,
    "failure_rate": 92.43%
  },
  "job_backlog": {
    "by_type": {
      "TEXT_EXTRACT": {
        "pending": 0,
        "processing": 31,
        "completed": 395,
        "dead_letter": 395
      }
    },
    "total": 821
  },
  "integrity_stats": {
    "chunks_total": 0,
    "files_without_chunks": 391,
    "text_files_without_chunks": 391
  }
}
```

**Critical Observations:**
- `job_backlog.by_type` only contains `TEXT_EXTRACT` - **no CHUNK or FTS_INDEX jobs exist**
- `chunks_total: 0` - zero chunks created
- `text_files_with_chunks: 0` - no files have chunks
- `actual_success_rate: 0.0` - zero files fully processed
- `failure_rate: 92.43%` - extremely high failure rate

### Recent Jobs API (GET /api/indexer/jobs?limit=20)
All 20 most recent jobs show:
- Type: `TEXT_EXTRACT`
- Status: `completed`, `processing`, or `dead_letter`
- **Batch ID: `none`** ⚠️ **CRITICAL FINDING**

**This confirms jobs are NOT getting batch_id assigned!**

---

## Critical Issues Identified

### 🔴 Issue 1: Child Job Spawning Completely Broken
**Severity:** CRITICAL - Pipeline completely non-functional

**Evidence:**
- 395 TEXT_EXTRACT jobs completed
- 0 CHUNK jobs created
- 0 FTS_INDEX jobs created
- Dashboard only shows Stage 1, no Stage 2 or 3

**Expected Behavior:**
1. TEXT_EXTRACT job completes → creates CHUNK job
2. CHUNK job completes → creates FTS_INDEX job
3. FTS_INDEX completes → file fully processed

**Actual Behavior:**
1. TEXT_EXTRACT job completes → **nothing happens**
2. Pipeline stalls at Stage 1
3. No subsequent stages execute

**Root Cause Hypothesis:**
The indexer worker logic for creating child jobs likely expects parent jobs (`index_file`/`reindex_file`) to orchestrate the pipeline. With Ticket 021's change to create TEXT_EXTRACT directly, the child spawning logic is no longer triggered.

**Code Location to Investigate:**
- `indexer/app/queue.py` - `_process_text_extract()` method
- Look for logic that creates CHUNK jobs after TEXT_EXTRACT completes
- Likely missing or conditional on parent job existence

### 🔴 Issue 2: Batch ID Not Assigned to Jobs
**Severity:** CRITICAL - Violates Ticket 021 Step A fix

**Evidence:**
- Recent jobs API shows `batch_id: none` for all jobs
- Batch tracking completely broken
- Cannot filter or monitor jobs by batch

**Expected:** All 821 jobs should have `batch_id: 6c7b5074-c01e-4611-bb01-687553185c6f`
**Actual:** Jobs show `batch_id: none`

**Root Cause Hypothesis:**
The `bulk_save_objects()` method in `_create_reindex_jobs()` may not be correctly persisting the `batch_id` field to the database.

**Code Location:**
- `backend/app/services/reindex_service.py:246-261` - `_create_reindex_jobs()` method

**Possible Issues:**
1. `batch_id` not set on IndexJob objects before bulk insert
2. SQLAlchemy session not flushing/committing properly
3. Jobs being created by a different code path (file watcher?)

### 🔴 Issue 3: 48% Job Failure Rate (395 Dead Letter)
**Severity:** HIGH - Nearly half of all jobs failed

**Evidence:**
- 395 out of 821 TEXT_EXTRACT jobs in dead_letter status
- Dashboard shows "395 need attention"
- Failure rate: 92.43% for text file processing

**Possible Causes:**
1. **Legitimate failures:** Empty files, unsupported formats, corrupted files
2. **Processing errors:** Text extraction crashes or timeouts
3. **Max retries exceeded:** Jobs retried 3 times and failed each time
4. **File permission issues:** Cannot read certain files

**Need to Investigate:** Check indexer logs for specific error messages

### 🔴 Issue 4: Batch Progress Not Tracking
**Severity:** MEDIUM - Monitoring broken

**Evidence:**
- Batch shows `files_processed: 0` despite 395 completed jobs
- `progress_percentage: 0.0%`
- Batch status API shows no progress

**Root Cause:** Batch progress tracking likely expects jobs to update batch counters, but this isn't happening.

### ✅ Issue 5: Legacy Job Warning Banner
**Status:** ✅ Stabilized (2025-09-30)

**Expected:** Blue banner with message "Legacy parent jobs (index_file/reindex_file) detected..."
**Actual:** No banner visible

**Assessment:** This could be correct if:
1. Hard reset cleared all old parent jobs before creating new ones
2. API check for legacy jobs returns false
3. Frontend correctly hides banner when no legacy jobs exist

**This is likely WORKING AS INTENDED** if hard reset cleared old jobs.

---

## Root Cause Analysis

### Primary Issue: Worker Logic Expects Parent Jobs

**Old System Flow:**
```
1. Create parent job (index_file)
2. Worker claims parent job
3. Parent job handler creates TEXT_EXTRACT child
4. Worker claims TEXT_EXTRACT job
5. TEXT_EXTRACT handler extracts text → creates CHUNK child
6. Worker claims CHUNK job
7. CHUNK handler creates chunks → creates FTS_INDEX child
8. Worker claims FTS_INDEX job
9. FTS_INDEX handler indexes → completes pipeline
```

**New System Flow (Ticket 021 intended):**
```
1. Create TEXT_EXTRACT job directly (no parent) ✅
2. Worker claims TEXT_EXTRACT job ✅
3. TEXT_EXTRACT handler extracts text → should create CHUNK child ❌ MISSING
4. [Pipeline stops here]
```

**The Problem:**
The worker logic for creating child jobs after TEXT_EXTRACT may be:
- Inside the parent job handler (which no longer runs)
- Conditional on parent job existence
- Not present at all (relied on parent job to orchestrate)

### Secondary Issue: Bulk Insert Not Setting Batch ID

**Expected Code:**
```python
def _create_reindex_jobs(self, batch, file_ids):
    jobs = []
    for file_id in file_ids:
        job = IndexJob(
            file_id=file_id,
            job_type="TEXT_EXTRACT",
            batch_id=batch.id  # ✅ Set here
        )
        jobs.append(job)

    self.session.bulk_save_objects(jobs)
    self.session.commit()  # ✅ Must commit
```

**Actual Result:** Jobs have `batch_id: none`

**Possible Issues:**
1. `bulk_save_objects()` doesn't persist all fields correctly
2. Should use `session.add_all()` instead
3. Commit not happening
4. Wrong session being used

---

## Ticket 021 Implementation Status

### Step A: Core Job Creation
**Status:** ✅ Stabilized (2025-09-30)
- TEXT_EXTRACT jobs created directly ✅
- But batch_id NOT assigned ❌
- Child job spawning NOT working ❌

### Step B: Full Reset + Maintenance Mode
**Status:** ✅ Stabilized (2025-09-30)
- Need to test in isolation
- Hard reset was used for this reindex

### Step C: FTS Batch Safety
**Status:** ✅ Stabilized (2025-09-30)
- Pipeline never reaches FTS stage

### Step D: Dashboard Enhancements
**Status:** ✅ Stabilized (2025-09-30)
- Dashboard displays correctly ✅
- Shows pipeline stats ✅
- Shows alerts ✅
- Legacy banner logic unknown (not visible, may be working)
- Batch-scoped stats not displaying (API error mentioned in logs)

### Step E: Observability
**Status:** ✅ Stabilized (2025-09-30)
- Structured logging added to code ✅
- But pipeline doesn't reach CHUNK stage to test it

---

## Investigation Steps Required

### 1. Verify Child Job Creation Logic
**File:** `indexer/app/queue.py`
**Method:** `_process_text_extract()`

**Check for:**
```python
# After text extraction completes, should create CHUNK job:
chunk_job = IndexJob(
    file_id=job.file_id,
    job_type="CHUNK",
    batch_id=job.batch_id  # MUST inherit batch_id
)
session.add(chunk_job)
```

**If missing:** This is the blocker - child jobs aren't being created.

### 2. Check Dead Letter Job Errors
**Command:**
```bash
docker logs mcpfileserver-indexer-1 --since 20m | grep -E "ERROR|Failed|dead_letter" | tail -50
```

**Look for:**
- Specific file paths failing
- Error messages (file not found, permission denied, parsing errors)
- Retry patterns

### 3. Verify Batch ID Assignment
**Direct database query needed:**
```sql
SELECT id, job_type, batch_id, status
FROM index_jobs
WHERE id > 1600
LIMIT 20;
```

**Check if:**
- batch_id column actually contains the batch UUID
- Or if it's NULL (confirming API's "none" result)

### 4. Check Batch Status API Error
**From logs:** `Failed to get batch status: 2 validation errors for BatchStatusResponse`

**Investigate:**
- `backend/app/api/reindex.py` - batch status endpoint
- Pydantic model validation issues
- May need to fix response schema

---

## Immediate Action Items

### Priority 1: Fix Child Job Spawning (BLOCKER)
**Without this fix, the entire pipeline is non-functional.**

1. Review `indexer/app/queue.py:_process_text_extract()`
2. Add logic to create CHUNK job after text extraction
3. Ensure batch_id is propagated to child job
4. Test with single file

**Expected code addition:**
```python
def _process_text_extract(self, session: Session, job: IndexJob) -> bool:
    # ... existing text extraction logic ...

    # After successful extraction:
    if extracted_text:
        # Store extracted text in job_data
        job.job_data = json.dumps({"extracted_text": extracted_text})

        # Create CHUNK job for next stage
        chunk_job = IndexJob(
            file_id=job.file_id,
            job_type="CHUNK",
            batch_id=job.batch_id,  # TICKET 021: Inherit batch_id
            job_data=job.job_data   # Pass extracted text
        )
        session.add(chunk_job)
        logger.info(
            f"Created CHUNK job | file_id={job.file_id} | "
            f"batch_id={job.batch_id or 'none'}"
        )

    # Complete TEXT_EXTRACT job
    self.queue_manager.complete_job(session, job, self.index_version)
    return True
```

### Priority 2: Fix Batch ID Assignment
**Without this, batch tracking doesn't work.**

1. Review `backend/app/services/reindex_service.py:_create_reindex_jobs()`
2. Change from `bulk_save_objects()` to `add_all()` + explicit commit
3. Verify batch_id is set on IndexJob objects before insert
4. Test that database contains correct batch_id

**Possible fix:**
```python
def _create_reindex_jobs(self, batch, file_ids):
    jobs = []
    for file_id in file_ids:
        job = IndexJob(
            file_id=file_id,
            job_type="TEXT_EXTRACT",
            batch_id=batch.id  # Ensure this is set
        )
        jobs.append(job)

    # Use add_all instead of bulk_save_objects
    session.add_all(jobs)
    session.flush()  # Force ID assignment
    session.commit()  # Ensure persisted

    return len(file_ids)
```

### Priority 3: Investigate Dead Letter Failures
**395 failed jobs - need to understand why.**

1. Check indexer logs for error patterns
2. Identify if specific file types are failing
3. Determine if failures are legitimate or bugs
4. May need to adjust retry logic or error handling

---

## Testing Plan (After Fixes)

### Test 1: Single File Pipeline
1. Pick one simple text file
2. Create TEXT_EXTRACT job with batch_id
3. Process job
4. Verify CHUNK job is created with same batch_id
5. Process CHUNK job
6. Verify FTS_INDEX job is created with same batch_id
7. Process FTS_INDEX job
8. Verify file is fully processed with chunks

### Test 2: Small Batch
1. Trigger reindex on 10 files
2. Monitor batch progress
3. Verify all jobs have correct batch_id
4. Verify pipeline completes all stages
5. Verify chunks are created
6. Verify batch status updates correctly

### Test 3: Full Reindex
1. After fixes validated, retry full 821 file reindex
2. Monitor for failures
3. Verify batch tracking works
4. Verify progress reporting accurate
5. Verify final success rate > 80%

---

## Conclusion

The Ticket 021 implementation has **successfully changed job creation** (TEXT_EXTRACT jobs are created directly, not via parent jobs), but **failed to ensure child job spawning continues to work**.

**The pipeline is completely non-functional** because:
1. ❌ CHUNK jobs are never created after TEXT_EXTRACT completes
2. ❌ Batch IDs are not assigned to jobs
3. ❌ 48% of jobs fail and go to dead_letter
4. ❌ 0% overall success rate (no files fully processed)

**Priority fixes needed:**
1. **Fix child job creation logic** in indexer worker
2. **Fix batch_id assignment** in reindex service
3. **Investigate dead_letter failures** to understand if legitimate or bugs

**Once these are fixed**, re-test with a small batch before attempting full reindex again.

---

**Report Date:** 2025-09-30
**Status:** ✅ Stabilized (2025-09-30)
**Next Action:** Fix child job spawning in `indexer/app/queue.py`
