# Ticket 022: File Modification Reindexing Blocked by Polling/Stability Conflict

**Type:** BUG
**Priority:** MEDIUM
**Component:** Indexer Service - File Watcher
**Created:** 2025-10-01
**Status:** Closed (2025-10-01)

---

## Summary

File modifications are detected by the file watcher and added to stability tracking, but reindex jobs are never created because the polling mechanism continuously re-detects the same files, resetting their stability counters before they can complete the required 3 stability checks.

---

## Problem Description

### Current Behavior
1. File modification occurs (e.g., content appended to existing file)
2. Watcher detects modification: `[POLLING] Modified file detected: /source/test_file_addition.txt`
3. File added to stability tracker (requires 3 consecutive checks × 2s debounce = ~6 seconds)
4. Stability check begins: `File stable check 1/3`, `File stable check 2/3`
5. **Before check 3/3:** Polling cycle runs again (~30 seconds) and re-detects the same file
6. Stability counter resets to 0/3
7. Cycle repeats indefinitely - file never becomes "stable"
8. `process_stable_files()` never called → no reindex job created
9. File remains indexed with old content

### Expected Behavior
Modified files should:
1. Be detected once
2. Complete stability checks (3/3)
3. Trigger reindex job creation
4. Get reindexed with updated content within ~10-15 seconds

---

## Test Results

### ✅ Test 1: File Addition - PASSED
- **Test:** Created `test_file_addition.txt` (357 bytes)
- **Result:** File detected, stability completed, 4 jobs created and processed
- **Metrics:**
  - Total files: 15 → 16 ✅
  - Completed jobs: 56 → 60 ✅
  - Time: ~8-10 seconds
  - Indexing: 100% complete

### ⚠️ Test 2: File Modification - FAILED
- **Test:** Modified `test_file_addition.txt` (appended content twice)
- **Detection:** `[POLLING] Modified file detected` ✅
- **Stability:** Started but never completed (stuck at 2/3 checks max)
- **Reindex jobs:** 0 created ❌
- **Metrics:** No change in job counts or processing stats
- **Duration:** Tested over 5+ minutes with multiple modifications

### ✅ Test 3: File Deletion - PASSED
- **Test:** Deleted `test_file_addition.txt`
- **Result:** File removed from database, no orphaned records
- **Metrics:**
  - Total files: 16 → 15 ✅
  - Detection time: ~30 seconds (next poll cycle)

---

## Root Cause Analysis

### Architecture Conflict
The indexer uses **two detection mechanisms** that conflict:

1. **Event-based detection (Watchdog):**
   - Triggers on file system events (create, modify, delete)
   - Adds files to stability tracker
   - Fast response (~2 seconds)

2. **Polling-based detection:**
   - Scans entire filesystem every 30 seconds
   - Compares current state to database records
   - Detects modifications via mtime/size changes
   - **Does not check if file is already in stability tracking**

### The Conflict
```
T=0s:   User modifies file
T=1s:   Watchdog detects → adds to stability (check 1/3 pending)
T=3s:   Stability check 1/3 passes
T=5s:   Stability check 2/3 passes
T=7s:   Should reach check 3/3 and process...
T=30s:  ⚠️ POLLING runs → re-detects same file as "modified"
T=30s:  ⚠️ File re-added to stability tracker → counter RESET to 0/3
T=32s:  Stability check 1/3 (again)
T=34s:  Stability check 2/3 (again)
T=60s:  ⚠️ POLLING runs again → RESET to 0/3 (again)
...infinite loop
```

### Code Evidence

**indexer/app/watcher.py:261-266** - Event handler correctly adds to stability:
```python
def on_modified(self, event):
    """Handle file modification events."""
    if not event.is_directory and not self.should_ignore_path(event.src_path):
        logger.info(f"File modified: {event.src_path}")
        self.stability_tracker.add_file(event.src_path)
```

**indexer/app/watcher.py:~450-590** - Polling detection has no guard:
```python
def process_stable_files(self):
    # ... polling logic ...
    if current_mtime != existing_file.mtime_epoch:
        logger.info(f"[POLLING] Modified file detected: {relative_path}")
        self.stability_tracker.add_file(file_path)  # ⚠️ No check if already tracked
```

**indexer/app/watcher.py:98-104** - Stability reset on re-add:
```python
if current_size != info['size'] or current_mtime != info['mtime']:
    # File changed, reset stability tracking
    info['size'] = current_size
    info['mtime'] = current_mtime
    info['checks_passed'] = 0  # ⚠️ Counter reset
```

---

## Proposed Solutions

### Option 1: Guard Polling Against Re-detection (Recommended)
**Change:** Modify `process_stable_files()` to skip files already in stability tracking

**Implementation:**
```python
# In FileWatcher.process_stable_files() polling section
if current_mtime != existing_file.mtime_epoch:
    # Check if file is already being tracked for stability
    if file_path not in self.stability_tracker.pending_files:
        logger.info(f"[POLLING] Modified file detected: {relative_path}")
        self.stability_tracker.add_file(file_path)
    else:
        logger.debug(f"[POLLING] File {relative_path} already in stability tracking, skipping")
```

**Pros:**
- Minimal code change
- Preserves both detection mechanisms
- Fixes the conflict directly
- No performance impact

**Cons:**
- Requires tight coupling between polling and stability tracker

---

### Option 2: Increase Polling Interval
**Change:** Increase polling from 30s to 60s or 90s

**Configuration change in `.env`:**
```bash
WATCHER_POLL_INTERVAL=60  # or 90
```

**Pros:**
- Zero code changes
- Simple configuration tweak
- Allows stability checks to complete (3 checks × 2s = 6s < 60s)

**Cons:**
- Slower detection of modifications (up to 60-90s delay)
- Doesn't fix the architectural issue
- Still fails if user makes rapid successive modifications

---

### Option 3: Disable Polling Modification Detection
**Change:** Make polling only detect new/deleted files, rely on watchdog for modifications

**Implementation:**
```python
# In process_stable_files() polling section
if current_mtime != existing_file.mtime_epoch:
    # Modification detected by polling, but ignore - watchdog will handle it
    logger.debug(f"[POLLING] File {relative_path} modified (watchdog will handle)")
    continue
```

**Pros:**
- Clean separation of concerns
- Polling handles discovery, watchdog handles changes
- No conflict possible

**Cons:**
- Loses polling as backup for watchdog failures
- Watchdog may miss some modification events in edge cases

---

### Option 4: Smart Re-add with Mtime Comparison
**Change:** Only reset stability if file actually changed since being tracked

**Implementation:**
```python
def add_file(self, file_path: str) -> None:
    stat = os.stat(file_path)

    # If file already tracked, check if actually changed
    if file_path in self.pending_files:
        existing = self.pending_files[file_path]
        if stat.st_mtime == existing['mtime'] and stat.st_size == existing['size']:
            logger.debug(f"File {file_path} unchanged since tracking started, keeping progress")
            return  # Don't reset

    # New file or actually changed - (re)start tracking
    self.pending_files[file_path] = {
        'last_check': time.time(),
        'checks_passed': 0,
        'size': stat.st_size,
        'mtime': stat.st_mtime,
        'first_seen': time.time()
    }
```

**Pros:**
- Most robust solution
- Handles rapid successive modifications correctly
- Prevents unnecessary stability resets
- Works with both detection mechanisms

**Cons:**
- More complex logic in stability tracker
- Requires careful testing of edge cases

---

## Impact Assessment

### Current Impact
- **Severity:** Medium
- **Affected users:** All users with active file watching
- **Workaround:** Manual reindex via Force Reindex feature (ticket 019)
- **Data loss:** None (no data corruption, old content remains accessible)
- **Performance:** No performance degradation

### User Experience Impact
- Modified files not automatically reindexed
- Search results show stale content
- Users must manually trigger reindexing to see updates
- Confusion about "why my changes aren't showing up"

---

## Testing Plan

### Test Scenarios
1. **Single modification:** Modify file once, verify reindex within 10s
2. **Rapid modifications:** Modify file 3 times in 5 seconds, verify single reindex
3. **Polling during stability:** Start modification, force polling at T=4s, verify stability completes
4. **Long-running stability:** File takes 30+ seconds to stabilize (large file), verify no reset
5. **Concurrent modifications:** Modify multiple files simultaneously
6. **Deleted during stability:** Delete file while in stability tracking, verify cleanup

### Verification Steps
1. Modify test file
2. Check logs for `[POLLING] Modified file detected`
3. Verify stability progresses: 1/3 → 2/3 → 3/3
4. Verify `process_stable_files()` called
5. Verify reindex job created: `Created reindexing job for: <path>`
6. Verify job completes: jobs_processed count increases
7. Verify updated content in search results

---

## Recommended Approach

**Implement Option 4 (Smart Re-add)** with fallback to **Option 1 (Polling Guard)**:

1. **Phase 1:** Add polling guard (Option 1) - Quick fix, low risk
2. **Phase 2:** Enhance stability tracker (Option 4) - Robust long-term solution
3. **Testing:** Comprehensive test suite for all modification scenarios
4. **Monitoring:** Add metrics for stability check completion rates

**Timeline:**
- Phase 1: 1-2 hours (immediate fix)
- Phase 2: 4-6 hours (robust solution + testing)
- Total: 1 day

---

## Related Issues
- Ticket 021: Dual pipeline conflict (resolved)
- Ticket 016: File watcher monitoring feature
- Ticket 019: Force reindex feature (working workaround)

---

## Additional Notes

### Performance Considerations
- Stability tracking overhead: ~50 files × 3 checks × 2s = minimal
- Polling overhead: ~15 files × 30s cycle = negligible
- Event handler overhead: microseconds per event

### Configuration Current Values
```bash
WATCHER_DEBOUNCE_SECONDS=2.0
WATCHER_STABILITY_CHECKS=3
INDEXER_POLL_INTERVAL=5  # Main loop, not polling interval
# Polling runs every ~30 seconds based on code inspection
```

### Logs for Reference
```
2025-10-01 14:29:54 - [POLLING] New file detected: /source/test_file_addition.txt
2025-10-01 14:29:54 - Added file to stability tracking
2025-10-01 14:30:55 - [POLLING] Modified file detected: /source/test_file_addition.txt
2025-10-01 14:30:55 - Added file to stability tracking  # ⚠️ Re-added
2025-10-01 14:30:58 - File stable check 1/3
2025-10-01 14:31:03 - File stable check 2/3
2025-10-01 14:31:25 - [POLLING] Modified file detected  # ⚠️ Reset before 3/3
```

---

**Status:** Closed (2025-10-01) - fix verified
**Assignee:** TBD
**Target Version:** 4.4.1 (hotfix) or 4.5.0 (next minor)


