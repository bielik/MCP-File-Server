# 003-FEATURE: Add Dynamic File Browsing to Permission Editor

## Status: Open
**Created:** 2025-01-18
**Priority:** High
**Component:** Frontend - TwoPanelPermissionEditor

## Problem Statement
The current file browser in the Permissions tab only displays root-level folders and doesn't allow actual browsing into subdirectories. When users click the expand arrow on folders, nothing happens - the children are not loaded or displayed.

### Current Behavior
- File browser shows only top-level directories (materials/, projects/, private stuff/)
- Clicking expand/collapse arrows doesn't load folder contents
- The `loadFileTree` function loads with `maxDepth: 3` but doesn't handle dynamic expansion
- `handleNodeExpand` incorrectly reloads the entire tree instead of fetching specific folder contents

### Expected Behavior
- Clicking expand arrow should load and display folder contents
- Folders should lazy-load their children on first expansion
- Previously loaded folders should be cached to avoid redundant API calls
- Deep navigation into folder structure should be possible

## Root Cause Analysis

### Frontend Issues (TwoPanelPermissionEditor.tsx)
1. **Line 312-323:** `loadFileTree()` always fetches from root with fixed depth
2. **Line 416-427:** `handleNodeExpand()` calls `loadFileTree()` which reloads everything
3. **Line 325-371:** `buildFileTree()` doesn't handle incremental updates
4. **No caching mechanism** for already-loaded nodes

### Backend Status
- `/api/browse` endpoint works correctly and supports path parameter
- Can fetch any directory's contents with proper pagination
- Already supports `maxDepth` parameter for recursive fetching

## Implementation Plan

### Phase 1: Frontend - Dynamic Node Loading
**File:** `frontend/src/components/TwoPanelPermissionEditor.tsx`

1. **Add node caching state:**
```typescript
const [nodeCache, setNodeCache] = useState<Map<string, FileTreeNode[]>>(new Map())
const [loadingPaths, setLoadingPaths] = useState<Set<string>>(new Set())
```

2. **Create `loadFolderContents` function:**
```typescript
const loadFolderContents = async (folderPath: string) => {
  // Check cache first
  if (nodeCache.has(folderPath)) {
    return nodeCache.get(folderPath)
  }

  // Mark as loading
  setLoadingPaths(prev => new Set(prev).add(folderPath))

  try {
    const response = await fileApi.browseFiles(folderPath, 1, 1000, 1)
    const children = response.files

    // Update cache
    setNodeCache(prev => new Map(prev).set(folderPath, children))

    // Update tree structure
    updateTreeWithChildren(folderPath, children)

    return children
  } finally {
    setLoadingPaths(prev => {
      const next = new Set(prev)
      next.delete(folderPath)
      return next
    })
  }
}
```

3. **Fix `handleNodeExpand`:**
```typescript
const handleNodeExpand = async (path: string) => {
  const newExpanded = new Set(expandedPaths)

  if (newExpanded.has(path)) {
    // Collapse
    newExpanded.delete(path)
  } else {
    // Expand and load children if needed
    newExpanded.add(path)

    // Load children for this specific path
    await loadFolderContents(path)
  }

  setExpandedPaths(newExpanded)

  // Update permissions for newly visible nodes
  await updatePermissionResults(fileTree)
}
```

4. **Update `FileTree` component to show loading state:**
```typescript
// In FileTree component, show loading indicator
{loadingPaths.has(node.path) && (
  <span className="text-gray-400 text-xs ml-2">Loading...</span>
)}
```

### Phase 2: Tree State Management
**File:** `frontend/src/components/TwoPanelPermissionEditor.tsx`

1. **Implement `updateTreeWithChildren` function:**
```typescript
const updateTreeWithChildren = (parentPath: string, children: any[]) => {
  setFileTree(prevTree => {
    const newTree = [...prevTree]

    const findAndUpdate = (nodes: FileTreeNode[]): boolean => {
      for (const node of nodes) {
        if (node.path === parentPath) {
          node.children = children.map(child => ({
            path: child.path,
            name: child.name,
            isDirectory: child.is_directory,
            children: child.is_directory ? [] : undefined,
            expanded: expandedPaths.has(child.path),
            selected: selectedPaths.has(child.path)
          }))
          return true
        }
        if (node.children && findAndUpdate(node.children)) {
          return true
        }
      }
      return false
    }

    findAndUpdate(newTree)
    return newTree
  })
}
```

### Phase 3: Performance Optimizations

1. **Batch permission updates:**
   - Only fetch permissions for visible nodes
   - Debounce rapid expand/collapse actions

2. **Add virtual scrolling for large directories:**
   - Implement react-window for file list if > 100 items

## Test Plan

### Manual Testing Checklist

#### Test 1: Basic Folder Expansion
1. Open browser MCP: `mcp__browser__browser_navigate` to `http://localhost:5173`
2. Click on Permissions tab
3. Click expand arrow on "materials" folder
4. **Expected:** Folder contents should appear below
5. **Verify:** Loading indicator shows briefly while fetching
6. Take screenshot with `mcp__browser__browser_screenshot`

#### Test 2: Deep Navigation
1. Expand "materials" folder
2. Expand a subfolder within materials
3. Continue expanding 3-4 levels deep
4. **Expected:** Each level loads and displays correctly
5. **Verify:** Permission indicators show at each level

#### Test 3: Collapse and Re-expand
1. Expand "projects" folder
2. Collapse it
3. Re-expand it
4. **Expected:** Contents appear immediately (cached)
5. **Verify:** No loading indicator on second expansion

#### Test 4: Multiple Folder State
1. Expand "materials" and "projects" simultaneously
2. Navigate between them
3. **Expected:** Both remain expanded
4. **Verify:** State persists correctly

#### Test 5: Permission Integration
1. Expand folders with different permissions
2. **Expected:** Permission indicators update correctly
3. **Verify:** Hover shows correct permission details
4. Click permission inspector for details

### Automated Test Validation

```javascript
// Browser MCP test script
async function validateFileBrowser() {
  // Navigate to app
  await browser.navigate('http://localhost:5173')
  await browser.wait(2)

  // Click Permissions tab
  await browser.click('Permissions tab', '[data-testid="permissions-tab"]')
  await browser.wait(1)

  // Take initial screenshot
  await browser.screenshot() // Should show root folders only

  // Get initial snapshot
  const snapshot1 = await browser.snapshot()

  // Expand materials folder
  // Look for expand button near materials text
  await browser.click('Expand materials folder', 'button[aria-label="Expand materials"]')
  await browser.wait(2)

  // Take expanded screenshot
  await browser.screenshot() // Should show materials contents

  // Get expanded snapshot
  const snapshot2 = await browser.snapshot()

  // Verify children are visible
  const hasChildren = snapshot2.includes('materials/') &&
                     snapshot2.length > snapshot1.length

  console.log('Test Result:', hasChildren ? 'PASS' : 'FAIL')
  return hasChildren
}
```

## Success Criteria
- [ ] Users can navigate into any folder by clicking expand arrow
- [ ] Folder contents load dynamically without full tree refresh
- [ ] Previously loaded folders are cached (no redundant API calls)
- [ ] Loading indicators show during fetch operations
- [ ] Permission indicators work correctly at all levels
- [ ] Performance is acceptable with 1000+ files
- [ ] Expand/collapse state persists during session

## Implementation Notes
- Keep backward compatibility with existing permission functionality
- Ensure WebSocket updates still work correctly
- Consider adding folder search in future iteration
- May need to implement virtual scrolling for very large directories

## References
- Current Implementation: `frontend/src/components/TwoPanelPermissionEditor.tsx`
- API Service: `frontend/src/services/workspaceApi.ts`
- Backend Endpoint: `backend/app/api/endpoints.py` (browse endpoint)
- Related PR: Phase 3B implementation

## Estimated Effort
- Development: 4-6 hours
- Testing: 2 hours
- Total: 6-8 hours