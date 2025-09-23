# 012-BUG: WebSocket Disconnects on Tab Switch - Unnecessary Reconnections

## Status: ✅ CLOSED - FIXED
**Created:** 2025-01-23
**Resolved:** 2025-01-23
**Priority:** Medium
**Component:** Frontend - WebSocket Connection Management
**Affects:** Phase 3B - Real-time UI updates and connection stability

## Problem Statement

The WebSocket connection unnecessarily disconnects and reconnects every time the user switches to the Workspaces tab, causing log noise and potential performance issues. The connection should remain persistent across tab switches since the WebSocketProvider is at the root level.

### Current vs Expected Behavior

**Current Behavior (INEFFICIENT):**
- User switches to Workspaces tab
- WebSocket disconnects with code 1000 "Client disconnecting"
- Backend logs show: `[UI] Client disconnected` and `INFO: connection closed`
- WebSocket immediately reconnects
- Backend logs show: `[UI] WebSocket connected successfully` and `INFO: connection open`

**Expected Behavior (OPTIMAL):**
- User switches to Workspaces tab
- WebSocket connection remains persistent
- No disconnection/reconnection cycle
- Clean logs without connection noise

### Observed Logs

```
WebSocket disconnected: 1000 Client disconnecting
[UI] Client disconnected
INFO:     connection closed
INFO:     172.20.0.1:40012 - "GET /api/workspaces HTTP/1.1" 200 OK
```

### Root Cause Analysis

The WebSocket disconnection is caused by the useWebSocket hook's useEffect dependency array causing the component to remount when switching tabs. The issue is likely in one of these areas:

1. **Unstable dependencies** in useWebSocket hook (line 154 in useWebSocket.ts)
2. **Workspace store references** changing unnecessarily (lines 44-51)
3. **Component re-rendering** causing WebSocketProvider to unmount/remount

## Implementation Plan

### Step 1: Identify the Unstable Dependency
- **Examine useWebSocket dependencies** - Check what's causing the effect to re-run
- **Debug workspace store references** - Ensure they don't change on tab switches
- **Add logging** to track when the WebSocket effect re-runs

### Step 2: Stabilize WebSocket Hook
- **Memoize callback functions** that are passed as dependencies
- **Stabilize workspace store references** using refs where appropriate
- **Minimize effect dependencies** to only essential values

### Step 3: Fix Workspace Store Integration
- **Review workspace store usage** in useWebSocket
- **Ensure store references don't trigger re-renders**
- **Use refs for stable references** where needed

### Step 4: Test Connection Persistence
- **Verify WebSocket stays connected** during tab switches
- **Check logs are clean** without disconnection noise
- **Ensure real-time updates** still work correctly

## Test Plan

### Manual Testing

#### 1. **Tab Switch Test**
```bash
# Open browser console and watch for WebSocket logs
# Switch between tabs multiple times
# Expected: No "WebSocket disconnected/connected" messages
```

#### 2. **Connection Persistence Test**
```bash
# Keep browser dev tools Network tab open
# Switch to Workspaces tab
# Expected: No new WebSocket connection entries
```

#### 3. **Real-time Updates Test**
```bash
# Have Workspaces tab open
# Create/activate workspace via API
curl -X POST http://localhost:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Workspace", "description": "Test", "is_active": true}'
# Expected: UI updates in real-time without reconnection
```

### Backend Log Verification
```bash
# Watch backend logs while switching tabs
docker-compose logs backend --follow
# Expected: No "[UI] Client disconnected" / "[UI] WebSocket connected" cycle
```

### Browser MCP Testing

```javascript
async function testWebSocketPersistence() {
    // Navigate to app
    await browser.navigate('http://localhost:5173')
    await browser.wait(2)

    // Switch to different tabs multiple times
    await browser.click('Permissions tab', '[data-testid="permissions-tab"]')
    await browser.wait(1)
    await browser.click('Workspaces tab', '[data-testid="workspaces-tab"]')
    await browser.wait(1)
    await browser.click('Status tab', '[data-testid="status-tab"]')
    await browser.wait(1)
    await browser.click('Workspaces tab', '[data-testid="workspaces-tab"]')

    // Check console logs for WebSocket disconnections
    const logs = await browser.getConsoleLogs()
    const hasDisconnections = logs.some(log =>
        log.includes('WebSocket disconnected') ||
        log.includes('Client disconnecting')
    )

    console.log('WebSocket Persistence Test:', hasDisconnections ? 'FAIL ❌' : 'PASS ✅')
    return !hasDisconnections
}
```

## Success Criteria

- [ ] **PRIMARY:** No WebSocket disconnections when switching to Workspaces tab
- [ ] **SECONDARY:** Clean backend logs without connection noise
- [ ] **PERFORMANCE:** Single persistent WebSocket connection maintained
- [ ] **FUNCTIONALITY:** Real-time updates continue to work correctly
- [ ] **STABILITY:** No connection errors or failed reconnections
- [ ] **UX:** Instant tab switching without connection delays

## Technical Investigation Areas

### 1. useWebSocket Hook Dependencies
- **File:** `frontend/src/hooks/useWebSocket.ts` line 154
- **Check:** Effect dependency array and what triggers re-runs
- **Fix:** Stabilize dependencies using refs and memoization

### 2. Workspace Store Integration
- **File:** `frontend/src/hooks/useWebSocket.ts` lines 44-51
- **Check:** How workspace store references change
- **Fix:** Use refs for store functions to prevent effect re-runs

### 3. WebSocket Context Provider
- **File:** `frontend/src/contexts/WebSocketContext.tsx`
- **Check:** Whether provider itself is re-rendering
- **Fix:** Ensure stable context value

### 4. Component Mount/Unmount Cycle
- **Check:** Whether tab switches cause component tree changes
- **Debug:** Add mount/unmount logging
- **Fix:** Identify and stabilize the mounting behavior

## Impact Assessment

**User Experience:** Medium - Causes brief delays and log noise but doesn't break functionality
- ✅ **Connection reliability** - Reconnection works automatically
- ❌ **Performance efficiency** - Unnecessary reconnection overhead
- ❌ **Log cleanliness** - Creates noise in development and production logs
- ❌ **Connection stability** - Brief moments where real-time updates could be missed

**Development Experience:** Medium - Log noise makes debugging harder
- ❌ **Clean logs** - Connection messages clutter the output
- ❌ **Debug clarity** - Harder to spot actual connection issues
- ✅ **Functionality** - Real-time features work correctly after reconnection

**System Resources:** Low - Minimal impact but unnecessary
- ❌ **Connection efficiency** - Extra connection overhead
- ❌ **Network requests** - Unnecessary WebSocket handshakes
- ✅ **Memory usage** - No significant memory impact

## Related Issues

- **Affects:** Real-time workspace updates and permission changes
- **Impacts:** Development debugging experience
- **Future:** Could affect performance with many concurrent users
- **Dependencies:** WebSocket context architecture and workspace store integration

## References

### Current Implementation
- `frontend/src/hooks/useWebSocket.ts` - Main WebSocket hook with dependencies
- `frontend/src/contexts/WebSocketContext.tsx` - WebSocket provider context
- `frontend/src/store/workspaceStore.ts` - Workspace state management
- `frontend/src/App.tsx` - Tab switching logic

### Expected Behavior
WebSocket should maintain a single persistent connection similar to:
```javascript
// Connection established once on app load
WebSocket connected to ws://localhost:8000/ws/ui

// Tab switches should NOT trigger:
WebSocket disconnected: 1000 Client disconnecting
WebSocket connected to ws://localhost:8000/ws/ui
```

### Test Commands
```bash
# Monitor backend logs for connection messages
docker-compose logs backend --follow | grep -E "(connected|disconnected|WebSocket)"

# Monitor frontend console for WebSocket messages
# Open browser dev tools and watch console while switching tabs
```

## ✅ RESOLUTION SUMMARY

**Root Cause:** Two issues were causing WebSocket disconnections:
1. **Unstable callbacks** in WebSocketProvider were recreated on every render, triggering reconnections
2. **Duplicate WebSocket connection** in TwoPanelPermissionEditor component was disconnecting when switching tabs

**Fix Applied:**
1. Memoized all callback functions using `useCallback` with empty dependency arrays
2. Removed the duplicate WebSocket connection from TwoPanelPermissionEditor and used the shared WebSocketContext instead

**Files Changed:**
- `frontend/src/contexts/WebSocketContext.tsx` - Wrapped callback functions in `useCallback`
- `frontend/src/components/TwoPanelPermissionEditor.tsx` - Removed duplicate useWebSocket and used shared context

**Technical Details:**
```typescript
// Issue 1 - WebSocketContext callbacks (FIXED):
// Before: onMessage: (data) => { /* inline function */ }
// After: const handleMessage = useCallback((data: any) => { /* stable function */ }, [])

// Issue 2 - Duplicate WebSocket in TwoPanelPermissionEditor (FIXED):
// Before: const { } = useWebSocket({ url: 'ws://localhost:8000/ws/ui', ... })
// After: const { isConnected } = useWebSocketContext() // Use shared context
```

**Testing Instructions:**
1. Open http://localhost:5173 and Developer Tools Console
2. Switch between tabs multiple times (Workspaces → Permissions → Indexer → Status)
3. Expected: No "WebSocket disconnected/connected" messages during navigation
4. Check Network tab: Only one persistent WebSocket connection should exist

**Impact:**
- ✅ **Performance:** Eliminated unnecessary connection overhead from duplicate connections
- ✅ **Logs:** Cleaner backend logs without connection noise
- ✅ **Stability:** Single persistent WebSocket connection across entire application
- ✅ **User Experience:** Instant tab switching without connection delays
- ✅ **Architecture:** Proper separation of concerns with shared WebSocket context

**Verification:**
After implementing both fixes:
- No WebSocket disconnection messages in browser console during tab switches
- Only one WebSocket connection visible in Network tab
- Clean backend logs without "[UI] Client disconnected" noise
- Real-time features continue to work correctly
- Performance improved with elimination of reconnection overhead

---

**RESOLVED:** WebSocket connection now maintains a single, persistent connection across all tab switches. Both root causes have been addressed:
1. Callback stability prevents unnecessary hook re-execution
2. Elimination of duplicate connections prevents mount/unmount disconnections

The application now has a robust, efficient WebSocket architecture that properly shares a single connection across all components.