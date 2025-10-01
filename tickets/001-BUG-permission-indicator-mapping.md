# BUG-001: Permission Indicator Mapping Issue

**Priority:** Medium
**Component:** Frontend - PermissionInspector
**Status:** Closed (2025-10-01)
**Reporter:** User Investigation
**Created:** 2025-09-18

## Bug Description

The PermissionInspector component incorrectly maps API permission statuses to visual indicators in the file browser. The mapping is logically backwards, causing user confusion about which files have what permission levels.

## Steps to Reproduce

1. Navigate to the Permissions tab in the UI
2. Activate a workspace with limited permission rules (e.g., "Debug Test Workspace" with only one deny rule)
3. Observe the file browser indicators
4. Compare with actual API response from `/api/workspaces/{id}/effective-permissions:batch`

## Expected Behavior

Based on API response:
- **materials**: `status: "none"` → Should show **?** (gray) - no explicit rule
- **private stuff**: `status: "none"` → Should show **?** (gray) - no explicit rule
- **projects**: `status: "denied"` → Should show **✕** (red) - explicitly denied

## Actual Behavior

Current incorrect display:
- **materials**: Shows **✕** (red) - appears denied when it should be neutral
- **private stuff**: Shows **✕** (red) - appears denied when it should be neutral
- **projects**: Shows **?** (gray) - appears unknown when it should be red denied

## Root Cause Analysis

### File: `frontend/src/components/PermissionInspector.tsx`

**Problem 1: Missing "denied" status handling**
- Lines 353-359: `getIndicatorColor` function has no case for `"denied"` status
- Falls through to default gray color

**Problem 2: Incorrect "none" status mapping**
- Lines 362-368: `getIndicatorText` function maps:
  ```typescript
  case 'none': return '✕'  // WRONG - should be '?'
  ```
- Shows red X for "no rule" instead of neutral indicator

**Problem 3: Missing "denied" status mapping**
- No explicit case for `case 'denied': return '✕'`

## Technical Details

### API Contract (Correct)
```json
{
  "results": [
    {"path": "materials", "status": "none", "matchedRule": null},
    {"path": "projects", "status": "denied", "matchedRule": {...}}
  ]
}
```

### Current Code Issue
```typescript
// Missing in getIndicatorColor:
case 'denied': return 'bg-red-500 hover:bg-red-600'

// Wrong in getIndicatorText:
case 'none': return '✕'  // Should be '?'
// Missing:
case 'denied': return '✕'
```

## Proposed Fix

### Update `getIndicatorColor` (line ~353)
```typescript
const getIndicatorColor = (status: string) => {
  switch (status) {
    case 'write': return 'bg-green-500 hover:bg-green-600'
    case 'read': return 'bg-blue-500 hover:bg-blue-600'
    case 'denied': return 'bg-red-500 hover:bg-red-600'  // ADD THIS
    case 'none': return 'bg-gray-500 hover:bg-gray-600'
    default: return 'bg-gray-500 hover:bg-gray-600'
  }
}
```

### Update `getIndicatorText` (line ~362)
```typescript
const getIndicatorText = (status: string) => {
  switch (status) {
    case 'write': return 'RW'
    case 'read': return 'R'
    case 'denied': return '✕'  // ADD THIS
    case 'none': return '?'    // CHANGE FROM '✕' TO '?'
    default: return '?'
  }
}
```

## Test Requirements

### Automated Tests
Update `frontend/tests/components/PermissionInspector.test.tsx`:
- Test all status mappings: 'write', 'read', 'denied', 'none'
- Verify correct colors for each status
- Verify correct text indicators for each status
- Test tooltip content accuracy
- Test modal display content

### Manual Testing
1. Navigate to Permissions tab
2. Verify correct indicators show for each file type
3. Test tooltip and modal functionality
4. Confirm no regression in other permission features

## Acceptance Criteria

- [ ] `status: "denied"` shows red ✕ indicator
- [ ] `status: "none"` shows gray ? indicator
- [ ] `status: "write"` shows green RW indicator (existing, should not break)
- [ ] `status: "read"` shows blue R indicator (existing, should not break)
- [ ] All automated tests pass
- [ ] No visual regression in permission UI
- [ ] Tooltip content matches status correctly
- [ ] Modal content matches status correctly

## Impact Assessment

**User Experience:** High - Users are misled about file permissions
**Functionality:** Medium - Core permission display is incorrect
**Development:** Low - Isolated to one component

## Related Files

- `frontend/src/components/PermissionInspector.tsx` (main fix)
- `frontend/tests/components/PermissionInspector.test.tsx` (test updates)
- `frontend/src/components/TwoPanelPermissionEditor.tsx` (integration point)

---

**Next Steps:**
1. Write comprehensive automated tests
2. Implement fix in PermissionInspector.tsx
3. Run tests to verify fix
4. Manual testing in browser
5. Close ticket upon verification
