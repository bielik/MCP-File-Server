# 020-BUG: Non-Text Files Included in Text Processing Pipeline Statistics

**Type:** Bug
**Priority:** Medium
**Status:** Closed (2025-10-01)
**Created:** 2025-09-29

## Summary
The Indexer Dashboard's "Text Processing Pipeline" section displays misleading statistics by including non-text files (images, binaries) in the reindex_file job counts, making it difficult to understand the actual state of text content processing and searchability.

## Problem Description

### Current Behavior
The dashboard shows:
- **reindex_file**: 399 completed, 422 dead-letter
- This creates the impression that 422 text files failed processing
- Users assume search functionality is severely broken (422 failures vs 425 total text files)

### Actual Reality
- The 422 dead-letter reindex jobs include **both text and non-text files**
- Non-text files (images, PDFs, binaries) only need metadata reindexing, not text processing
- Only a small subset (~6) of those 422 are actually text files affecting search

### User Impact
- **Misleading alarm**: Dashboard suggests massive text processing failures
- **Operational confusion**: Users can't assess actual search functionality health
- **Incorrect prioritization**: Resources directed to non-critical issues
- **Trust erosion**: Dashboard appears to show system-wide failure

## Technical Analysis

### Current Dashboard Logic
```typescript
// Shows ALL reindex jobs regardless of file type
<row "reindex_file 399 0 0 0 422 ⚠️">
```

### File Type Breakdown (Estimated)
```
Total Files: 823
├── Text Files: 425 (documents, code)
└── Non-Text Files: 398 (images, binaries)

Dead Letter reindex_file: 422
├── Text Files: ~6 (actually affecting search)
└── Non-Text Files: ~416 (metadata-only, doesn't affect search)
```

### Root Cause
The `reindex_file` job type is used for **all file types**, but the "Text Processing Pipeline" section should only show statistics relevant to text content processing and searchability.

## Expected Behavior

### Separate Statistics by File Type
**Text Processing Pipeline** should show:
- Only text files in TEXT_EXTRACT, CHUNK, FTS_INDEX stages
- Only text files in reindex_file counts when they affect text processing

**File Metadata Pipeline** (new section):
- Show non-text file reindexing statistics separately
- Include metadata-only operations that don't affect search

### Dashboard Layout
```
📄 Text Processing Pipeline
Processing 425 text files through 3-stage pipeline
- TEXT_EXTRACT: 425 completed, 0 dead-letter
- CHUNK: 421 completed, 1 dead-letter
- FTS_INDEX: 419 completed, 1 dead-letter
- reindex_file (text): 6 completed, 6 dead-letter  ⚠️

📁 File Metadata Pipeline
Processing 398 non-text files for metadata indexing
- reindex_file (non-text): 393 completed, 416 dead-letter ⚠️
```

## Technical Requirements

### Backend Changes (`backend/app/api/indexer.py`)

1. **Enhanced Job Statistics Query**
   ```sql
   -- Add file type filtering to job queries
   SELECT
     job_type,
     status,
     COUNT(*) as count,
     indexed_files.is_text
   FROM index_jobs
   JOIN indexed_files ON index_jobs.file_id = indexed_files.id
   GROUP BY job_type, status, indexed_files.is_text
   ```

2. **Separate Response Structure**
   ```python
   {
     "text_pipeline": {
       "TEXT_EXTRACT": {"completed": 425, "dead_letter": 0},
       "CHUNK": {"completed": 421, "dead_letter": 1},
       "FTS_INDEX": {"completed": 419, "dead_letter": 1},
       "reindex_file": {"completed": 6, "dead_letter": 6}
     },
     "metadata_pipeline": {
       "reindex_file": {"completed": 393, "dead_letter": 416}
     }
   }
   ```

### Frontend Changes (`IndexerDashboard.tsx`)

1. **Split Pipeline Sections**
   - Create separate "Text Processing Pipeline" table for text files only
   - Create new "File Metadata Pipeline" table for non-text files
   - Update statistics calculations to use filtered data

2. **Enhanced Warning Logic**
   ```typescript
   // Show warnings only for relevant file types
   const textDeadLetterCount = textPipeline.reindex_file.dead_letter;
   const searchAffectingIssues = textDeadLetterCount > 0;
   ```

3. **Clearer Status Messages**
   ```typescript
   // Replace generic warnings with specific context
   "6 text files need reprocessing (affects search)"
   "416 non-text files need metadata updates (doesn't affect search)"
   ```

## Test Scenarios

### Scenario 1: Text File Modification
```
Action: Modify a .txt file
Expected: Only "Text Processing Pipeline" shows changes
Result: reindex_file (text) count increases, metadata pipeline unchanged
```

### Scenario 2: Image File Addition
```
Action: Add a .jpg file
Expected: Only "File Metadata Pipeline" shows changes
Result: reindex_file (non-text) count increases, text pipeline unchanged
```

### Scenario 3: Mixed File Operations
```
Action: Modify 1 text file, add 5 images
Expected: Both pipelines show respective changes
Result: Clear separation of text vs non-text processing status
```

## Acceptance Criteria

- [ ] Text Processing Pipeline shows only text files (documents, code)
- [ ] File Metadata Pipeline shows only non-text files (images, binaries)
- [ ] Dead letter counts accurately reflect impact on search functionality
- [ ] Warning messages distinguish between search-affecting vs metadata-only issues
- [ ] Dashboard provides clear understanding of actual text processing health
- [ ] Users can quickly assess search functionality status without confusion
- [ ] Operational teams can prioritize issues based on actual impact

## Implementation Priority

**Medium Priority** - While this doesn't break functionality, it significantly impacts:
- **Operational visibility**: Teams can't assess actual system health
- **User confidence**: Misleading statistics erode trust in the system
- **Resource allocation**: Effort spent on non-critical issues
- **Debugging efficiency**: Hard to identify real text processing problems

## Related Issues

- **Related to Ticket 017**: Helps identify which dead letter jobs actually affect search
- **Related to Ticket 018**: Improves accuracy of dashboard status displays
- **Supports Ticket 016**: Better monitoring of file watcher effectiveness

## Success Metrics

**Before Fix:**
- Users see "422 dead letter jobs" and assume search is broken
- No distinction between search-affecting vs metadata-only issues
- Operational teams investigate non-critical problems

**After Fix:**
- Users see "6 text files need reprocessing" with clear search impact
- Non-text file issues labeled as "metadata-only"
- Operational focus on actual search functionality problems
- Dashboard provides actionable, accurate status information

---

**Reporter:** Analysis based on dashboard confusion
**Environment:** Docker Compose (Windows)
**Affects:** Indexer Dashboard visibility and operational clarity
