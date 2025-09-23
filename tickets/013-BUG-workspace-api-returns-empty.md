# 013-BUG: Workspace API Returns Empty List Despite Data in Database

## Status: Open
**Created:** 2025-01-23
**Priority:** High
**Component:** Backend

## Problem Statement

The `/api/workspaces` endpoint returns an empty list even though the database contains 3 workspaces. This prevents the frontend from loading any workspaces and causes cascading errors throughout the application.

### Current Behavior
- API response: `{"workspaces":[],"total":0,"active_workspace_id":null}`
- Database contains 3 workspaces (verified via direct SQL query)
- CRUD operations work correctly when tested directly
- API returns HTTP 200 OK but with empty data

### Expected Behavior
- API should return all workspaces from the database
- Response should include workspace details and active workspace ID

### Root Cause Analysis

Investigation revealed:
1. The workspace CRUD `get_workspaces()` method correctly retrieves data from database
2. The API endpoint logic constructs the response object correctly when tested in isolation
3. The issue appears to be in the database session handling between the API layer and CRUD layer
4. The `get_db()` dependency injection may be creating a different session context

## Evidence

### Database Query Results
```sql
SELECT COUNT(*) FROM workspaces
-- Result: 3

SELECT id, name, is_active FROM workspaces
-- Results:
-- ID=1, Name='Test Workspace', Active=0
-- ID=2, Name='Debug Test Workspace', Active=1
-- ID=3, Name='Legacy Config', Active=0
```

### Direct CRUD Test
```python
workspaces = workspace_crud.get_workspaces(session, skip=0, limit=100)
# Returns: [<Workspace(id=1...)>, <Workspace(id=2...)>, <Workspace(id=3...)>]
```

### API Response
```bash
curl http://localhost:8000/api/workspaces
# Returns: {"workspaces":[],"total":0,"active_workspace_id":null}
```

## Implementation Plan

### Step 1: Investigate Database Session Configuration
- Check `backend/app/database.py` SessionLocal configuration
- Verify transaction isolation level and autocommit settings
- Check if Phase4A config changes affected database initialization

### Step 2: Debug API Endpoint
- Add logging to `list_workspaces()` in `backend/app/api/endpoints.py`
- Log session state before and after CRUD calls
- Check if `check_phase3_enabled()` is affecting execution flow

### Step 3: Fix Database Session Handling
- Ensure consistent session factory usage
- Verify proper session lifecycle management
- Check for any transaction rollback issues

### Step 4: Verify Fix
- Test API returns correct workspace list
- Ensure frontend loads workspaces properly
- Verify no side effects on other endpoints

## Test Plan

### Manual Testing
1. Start Docker containers: `docker-compose up`
2. Create test workspace via API if none exist
3. Call `/api/workspaces` and verify response contains workspaces
4. Check frontend loads workspace list correctly
5. Verify workspace activation works

### Automated Testing
```python
def test_workspace_api():
    # Direct database check
    with get_db() as session:
        db_workspaces = workspace_crud.get_workspaces(session)
        assert len(db_workspaces) > 0, "Database should contain workspaces"

    # API check
    response = requests.get("http://localhost:8000/api/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert len(data["workspaces"]) > 0, "API should return workspaces"
    assert data["total"] > 0, "Total count should be greater than 0"
```

## Success Criteria
- [ ] `/api/workspaces` returns all workspaces from database
- [ ] Frontend successfully loads and displays workspace list
- [ ] No 404 errors for workspace-related endpoints
- [ ] Workspace switching works correctly
- [ ] All workspace CRUD operations function properly

## Related Issues
- Causes frontend 404 errors (see ticket 006-BUG)
- May be related to Phase4A configuration changes

## References
- `backend/app/api/endpoints.py:445-470` - list_workspaces endpoint
- `backend/app/crud/workspace.py:81-83` - get_workspaces CRUD method
- `backend/app/database.py:97-110` - get_db dependency
- `backend/app/config.py` - Phase4A configuration integration