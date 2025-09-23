# 010-BUG: MCP list_all_files Tool Returns Empty Results

## Status: Open
**Created:** 2025-01-23
**Priority:** Medium
**Component:** Backend - MCP Tools / File Indexing System
**Affects:** Phase 4A - File discovery and indexing functionality

## Problem Statement

The MCP `list_all_files` tool consistently returns empty results `[]` despite having accessible files in the filesystem with proper permissions. This prevents AI agents from discovering and working with available files across the workspace.

### Current vs Expected Behavior

**Current Behavior:**
- MCP call: `{"method": "tools/call", "params": {"name": "list_all_files", "arguments": {"limit": 100}}}`
- Returns: `{"result": {"content": [{"type": "text", "text": "[]"}]}}`
- Empty array regardless of limit, offset, or other parameters

**Expected Behavior:**
- Should return a comprehensive list of all discoverable files within permission scope
- Should respect permission rules (only return files from allowed directories)
- Should include file metadata: path, size, modification time, type
- Should support pagination with limit/offset parameters
- Should work with sorting options (path, size, mtime, discovered)

### Root Cause Analysis

The `list_all_files` tool appears to depend on an indexing system that is either:
1. **Not running** - The indexer service may not be populating the file index
2. **Not connected** - The MCP tool may not be querying the correct index database
3. **Permission filtered** - The indexer may not be indexing files due to permission restrictions
4. **Database issue** - The indexed files table may be empty or inaccessible

### Impact Assessment

**Severity:** Medium - AI agents can still access files via direct paths but lose discovery capabilities
- ✅ **Direct file access works** - `read_file` and `list_files` with specific paths functional
- ❌ **File discovery broken** - Cannot explore available files without knowing exact paths
- ❌ **Search capabilities limited** - Advanced search and metadata queries unavailable
- ❌ **Indexer integration incomplete** - Phase 4A indexing features not accessible

## Implementation Plan

### Step 1: Investigate Indexer Service Status
- **Check:** Indexer container status and logs
- **Verify:** Database connection and table existence
- **Test:** Indexer API endpoints directly

### Step 2: Examine MCP Tool Implementation
- **File:** `backend/app/services/search_tools.py` or similar
- **Check:** `list_all_files` function implementation
- **Verify:** Database queries and permission integration

### Step 3: Test Indexing Pipeline
- **Trigger:** Manual indexing of test files
- **Monitor:** Index population process
- **Validate:** Indexed files appear in database

### Step 4: Debug Permission Integration
- **Verify:** Indexer respects permission rules
- **Test:** Files from allowed directories get indexed
- **Check:** Permission service integration in indexer

### Step 5: Fix Data Flow
- **Repair:** Any broken connections between indexer and MCP tools
- **Update:** Query logic to properly fetch indexed files
- **Ensure:** Permission filtering works correctly

## Test Plan

### Manual Testing

1. **Check Indexer Service Status**
   ```bash
   docker-compose logs indexer --tail 20
   curl http://localhost:8002/health
   curl http://localhost:8002/api/stats
   ```

2. **Test MCP Tool Directly**
   ```bash
   curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_all_files", "arguments": {"limit": 10}}, "id": 1}'
   ```

3. **Verify Database Content**
   ```bash
   # Check if indexed_files table exists and has data
   docker exec mcpfileserver-backend-1 sqlite3 /data/database.db ".tables"
   docker exec mcpfileserver-backend-1 sqlite3 /data/database.db "SELECT COUNT(*) FROM indexed_files;"
   ```

4. **Test Indexer API**
   ```bash
   curl http://localhost:8002/api/files/count
   curl http://localhost:8002/api/files/list?limit=10
   ```

### Automated Testing

Create test script to validate indexing pipeline:

```python
async def test_indexing_pipeline():
    """Test complete indexing and discovery pipeline."""

    # Test 1: Verify indexer is running
    indexer_response = requests.get('http://localhost:8002/health')
    assert indexer_response.status_code == 200

    # Test 2: Check file count in index
    stats = requests.get('http://localhost:8002/api/stats').json()
    indexed_count = stats.get('total_files', 0)
    print(f"Indexed files: {indexed_count}")

    # Test 3: Test MCP list_all_files
    mcp_response = requests.post('http://localhost:8000/mcp', json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "list_all_files", "arguments": {"limit": 50}},
        "id": 1
    })

    result = mcp_response.json()
    files = eval(result['result']['content'][0]['text'])  # Parse the text array

    assert len(files) > 0, "list_all_files should return files"
    assert len(files) <= 50, "Should respect limit parameter"

    # Test 4: Verify permission filtering
    for file_info in files:
        path = file_info['path']
        # Should only include files from allowed directories
        assert any(path.startswith(allowed) for allowed in ['projects', 'materials', 'private stuff', 'Working with react'])

    print(f"✅ Found {len(files)} discoverable files")
    return True
```

### Browser MCP Testing

```javascript
async function testFileDiscovery() {
    // Test indexer web interface if available
    await browser.navigate('http://localhost:8002')
    await browser.screenshot()

    // Check indexer status
    const snapshot = await browser.snapshot()
    const hasIndexedFiles = snapshot.includes('indexed') || snapshot.includes('files')

    console.log('Indexer Interface Test:', hasIndexedFiles ? 'AVAILABLE' : 'NOT FOUND')

    return hasIndexedFiles
}
```

## Success Criteria

- [ ] `list_all_files` returns non-empty array of file objects
- [ ] Results include files from permitted directories only:
  - `projects/` files should be included (read permission)
  - `materials/` files should be included (read permission)
  - `private stuff/` files should be included (write permission)
  - `Working with react/` files should be included (read permission)
  - `SSS11/` files should NOT be included (no permission)
- [ ] File objects contain required metadata:
  ```json
  {
    "path": "projects/API_Documentation.md",
    "size": 10500,
    "mtime": 1695377760,
    "type": "file",
    "discovered": "2025-01-23T10:44:31Z"
  }
  ```
- [ ] Pagination parameters work correctly:
  - `limit` parameter controls result count
  - `offset` parameter enables pagination
  - `sort_by` parameter affects result ordering
- [ ] Performance is acceptable (< 2 seconds for 1000 files)
- [ ] Permission integration works (only accessible files returned)
- [ ] Real-time updates (new files appear after indexing)

## Technical Investigation Areas

### 1. Indexer Service Health
- Container status and resource usage
- Database connectivity and table schema
- File system access and permission integration
- Indexing job status and error logs

### 2. MCP Tool Implementation
- `list_all_files` function location and implementation
- Database query logic and optimization
- Permission filtering in query or post-processing
- Error handling and fallback behavior

### 3. Database Schema
- `indexed_files` table structure and contents
- Foreign key relationships to permissions/workspaces
- Indexing job tracking and status fields
- Performance indexes on query fields

### 4. Permission Integration
- How indexer determines which files to index
- Permission checking during indexing vs querying
- Workspace context in file discovery
- Real-time permission updates to indexed files

## Related Issues

- **Dependency:** Indexer service functionality (Phase 4A)
- **Related:** Search capabilities and metadata queries
- **Blocks:** Advanced file discovery for AI agents
- **Future:** Full-text search and semantic search features

## References

### Affected Files
- `backend/app/services/search_tools.py` - MCP tool implementation
- `indexer/` - Indexer service (separate container)
- `backend/app/models/indexing.py` - IndexedFile model
- `backend/app/main.py` - MCP tool registration

### Expected API Behavior
```bash
# Should return file list with metadata
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_all_files", "arguments": {"limit": 5}}, "id": 1}'

# Expected response:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "[{'path': 'projects/API_Documentation.md', 'size': 10500, 'type': 'file'}, ...]"
    }]
  }
}
```

### Indexer Integration Points
- Database shared between backend and indexer
- Permission service used by both components
- File system mounted to both containers
- WebSocket updates for real-time indexing

---

**Investigation Priority:** Start with indexer service health check, then examine MCP tool implementation. The issue is likely in the indexer → database → MCP tool data flow rather than permission logic, since direct file access works correctly.