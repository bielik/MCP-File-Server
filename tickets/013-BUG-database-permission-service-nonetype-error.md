# 013-BUG: Database Permission Service NoneType Error

## Status: ✅ CLOSED - RESOLVED
**Created:** 2025-01-23
**Resolved:** 2025-01-23
**Priority:** Critical
**Component:** Backend Database Configuration

## Problem Statement

### Original Symptom
- Backend API endpoint `/api/workspaces` returns empty results: `{"workspaces": [], "total": 0, "active_workspace_id": null}`
- Database contains 3 workspaces but API shows 0
- Frontend displays empty workspace list causing 404 cascade errors

### Root Cause Analysis
**Primary Issue: Docker Volume Mount Misconfiguration**

The problem was caused by incorrect Docker volume mounting configuration:

1. **Environment Variable Confusion**: `.env` file contained `DATABASE_PATH=/data` (container path) instead of `./data` (local path for Docker mount)
2. **Broken Volume Mount**: Docker Compose expanded `${DATABASE_PATH:-./data}:/data` to `/data:/data` instead of `./data:/data`
3. **Multiple Databases**: This caused containers to create separate database instances instead of sharing the local database file
4. **File Evidence**:
   - Local database: `./data/database.db` (172,032 bytes) - contained 3 workspaces
   - Container database: `/data/database.db` (4,096 bytes) - contained 1 workspace

## Implementation Plan

### Fix 1: Environment Variable Correction
**File:** `.env`
```bash
# Before (INCORRECT):
DATABASE_PATH=/data

# After (CORRECT):
DATABASE_PATH=./data
```

### Fix 2: Container Path Detection
**File:** `backend/app/config.py`
```python
# Added container detection logic
if os.path.exists('/data'):
    # Running in Docker container - use /data
    database_path = '/data'
else:
    # Running locally - use config value
    database_path = getattr(phase4a_config, 'DATABASE_PATH', './data')
```

### Fix 3: Standardized Database URL Construction
**Files:** `backend/app/config.py`, `indexer/app/main.py`
```python
# Consistent path normalization across all services
from pathlib import Path
db_path = Path(database_path)
if not str(db_path).endswith('.db'):
    db_path = db_path / 'database.db'
self.DATABASE_URL = f"sqlite:///{db_path}"
```

## Test Plan

### Verification Steps
1. **Container Database Access**:
   ```bash
   docker exec mcpfileserver-backend-1 sh -c "ls -la /data/database.db"
   # Should show correct file size matching local database
   ```

2. **API Response Validation**:
   ```bash
   curl -s http://localhost:8000/api/workspaces
   # Should return all 3 workspaces with active_workspace_id
   ```

3. **Database Diagnostic**:
   ```bash
   curl -s http://localhost:8000/api/system/db-info
   # Should show consistent database path and table counts
   ```

## Test Results ✅

### Manual Testing - PASSED
- ✅ Container database file now matches local database (same size and timestamp)
- ✅ API returns correct workspace count: `{"total": 3, "active_workspace_id": 2}`
- ✅ All 3 workspaces properly displayed in API response
- ✅ Database diagnostic endpoint shows consistent configuration

### API Response Verification - PASSED
```json
{
  "workspaces": [
    {"id": 1, "name": "Test Workspace", "is_active": false},
    {"id": 2, "name": "Debug Test Workspace", "is_active": true},
    {"id": 3, "name": "Legacy Config", "is_active": false}
  ],
  "total": 3,
  "active_workspace_id": 2
}
```

### Database Consistency Check - PASSED
- Local file: `./data/database.db` (172,032 bytes)
- Container file: `/data/database.db` (172,032 bytes) ✅ MATCH
- Both show 3 workspaces in workspace table

## Success Criteria ✅

- [x] **API Returns Correct Data**: `/api/workspaces` shows all 3 workspaces
- [x] **Database Consistency**: Container and local database files are identical
- [x] **Active Workspace**: `active_workspace_id` properly included in response
- [x] **No Empty State**: Frontend receives populated workspace list
- [x] **Service Health**: All containers start successfully with shared database

## Resolution Summary

**Issue Type:** Configuration Error - Docker Volume Mount
**Impact:** Critical - Complete data isolation between services
**Complexity:** Medium - Required understanding of Docker volume mounting and environment variable expansion

**Key Learning:** Environment variables in `.env` should contain **local paths** for Docker Compose volume mounts, not container paths. The application logic should handle the container vs local path translation internally.

## References

- Related Issue: 015-BUG-frontend-workspace-404-errors.md (cascading effect)
- Database diagnostic endpoint: `/api/system/db-info`
- Docker Compose volume documentation: https://docs.docker.com/compose/compose-file/compose-file-v3/#volumes

---

**🎉 Resolution Impact:** This fix resolved the primary backend data isolation issue and enabled proper workspace management across all services. The frontend 404 errors were automatically resolved once the backend returned the correct workspace data.

**✅ Verified Working:** 2025-01-23 - All services now share the same database and return consistent data.