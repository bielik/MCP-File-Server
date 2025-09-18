# 004-UX: Improve Folder Interaction Behavior

## Status: Open
**Created:** 2025-01-18
**Priority:** Medium
**Component:** Frontend - TwoPanelPermissionEditor

## Problem Statement
The current folder interaction behavior in the file browser is confusing and doesn't follow standard file explorer conventions:

### Current Issues
1. **Clicking folder name selects folder instead of expanding it**
   - Users expect clicking on folder name to open/expand the folder
   - Currently requires clicking on expand arrow to open folder

2. **Expand arrows are not always visible**
   - Arrows only appear after first interaction with the folder area
   - Users can't immediately see which items are expandable folders

3. **Non-intuitive interaction pattern**
   - Standard file explorers: click name = expand, click checkbox = select
   - Current: click name = select, click invisible arrow = expand

### Expected Behavior
Following standard file explorer conventions:
- **Click folder name** → Expand/collapse folder
- **Click checkbox** → Select/deselect folder for permissions
- **Expand arrows visible at all times** → Clear visual indication of expandable folders

## Implementation Plan

### Phase 1: Always Show Expand Arrows
**File:** `frontend/src/components/TwoPanelPermissionEditor.tsx`

1. **Modify FileTree component expand button logic:**
```typescript
// Current logic (lines 46-65)
{node.isDirectory && (
  <button
    onClick={(e) => {
      e.stopPropagation()
      onNodeExpand(node.path)
    }}
    className="w-4 h-4 flex items-center justify-center text-gray-500 hover:text-gray-700"
  >
    {hasChildren ? (
      isExpanded ? (
        // Down arrow for expanded
      ) : (
        // Right arrow for collapsed
      )
    ) : null}
  </button>
)}

// New logic - always show arrow for directories
{node.isDirectory && (
  <button
    onClick={(e) => {
      e.stopPropagation()
      onNodeExpand(node.path)
    }}
    className="w-4 h-4 flex items-center justify-center text-gray-500 hover:text-gray-700"
    aria-label={isExpanded ? `Collapse ${node.name}` : `Expand ${node.name}`}
  >
    {isExpanded ? (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    ) : (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    )}
  </button>
)}
```

### Phase 2: Change Click Behavior
**File:** `frontend/src/components/TwoPanelPermissionEditor.tsx`

1. **Modify main folder click area:**
```typescript
// Current: clicking folder name selects it
<div
  className={`flex items-center space-x-2 py-1 px-2 hover:bg-gray-100 cursor-pointer ${
    isSelected ? 'bg-blue-50 border-l-2 border-blue-500' : ''
  }`}
  style={{ paddingLeft: `${depth * 20 + 8}px` }}
  onClick={() => onNodeSelect(node.path, !isSelected)}
>

// New: clicking folder name expands it, only checkbox selects
<div
  className={`flex items-center space-x-2 py-1 px-2 hover:bg-gray-100 ${
    isSelected ? 'bg-blue-50 border-l-2 border-blue-500' : ''
  }`}
  style={{ paddingLeft: `${depth * 20 + 8}px` }}
>
```

2. **Separate clickable areas:**
```typescript
{/* Expand/Collapse Button */}
{node.isDirectory && (
  <button
    onClick={(e) => {
      e.stopPropagation()
      onNodeExpand(node.path)
    }}
    className="w-4 h-4 flex items-center justify-center text-gray-500 hover:text-gray-700"
  >
    {/* Arrow SVG always visible */}
  </button>
)}

{/* Checkbox for selection */}
<input
  type="checkbox"
  checked={isSelected}
  onChange={(e) => onNodeSelect(node.path, e.target.checked)}
  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
  onClick={(e) => e.stopPropagation()}
/>

{/* File/Folder Icon and Name - clickable for folders */}
<div
  className="flex items-center space-x-2 flex-1 cursor-pointer"
  onClick={() => node.isDirectory ? onNodeExpand(node.path) : undefined}
>
  {/* Icon */}
  <div className="text-gray-500">
    {/* Folder/file icon */}
  </div>

  {/* Name */}
  <span className="flex-1 text-sm text-gray-900 truncate">{node.name}</span>
</div>

{/* Permission indicators remain the same */}
```

### Phase 3: Visual Improvements
**File:** `frontend/src/components/TwoPanelPermissionEditor.tsx`

1. **Improve hover states:**
```typescript
// Different hover effects for different clickable areas
<div className={`
  flex items-center space-x-2 py-1 px-2
  ${isSelected ? 'bg-blue-50 border-l-2 border-blue-500' : ''}
`}>
  {/* Expand button with distinct hover */}
  <button className="w-4 h-4 flex items-center justify-center text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded">

  {/* Folder name area with expand hover for directories */}
  <div className={`
    flex items-center space-x-2 flex-1
    ${node.isDirectory ? 'cursor-pointer hover:bg-gray-50' : ''}
  `}>
```

2. **Add visual feedback:**
```typescript
// Show loading state during expansion
{loadingPaths.has(node.path) && (
  <div className="flex items-center space-x-1">
    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-500"></div>
    <span className="text-gray-400 text-xs">Loading...</span>
  </div>
)}
```

## Test Plan

### Manual Testing Checklist

#### Test 1: Arrow Visibility
1. Navigate to Permissions tab
2. **Expected:** All folders show expand arrows immediately
3. **Verify:** Materials, projects, private stuff all have visible arrows
4. Take screenshot

#### Test 2: Folder Name Click Behavior
1. Click on "materials" folder name (not arrow, not checkbox)
2. **Expected:** Folder expands to show contents
3. Click on "materials" name again
4. **Expected:** Folder collapses
5. **Verify:** Folder selection state unchanged

#### Test 3: Checkbox Selection Behavior
1. Click checkbox next to "projects" folder
2. **Expected:** Folder gets selected (blue highlight)
3. **Verify:** Folder does not expand
4. Click checkbox again
5. **Expected:** Folder gets deselected

#### Test 4: Arrow Click Behavior
1. Click expand arrow next to "private stuff" folder
2. **Expected:** Folder expands
3. Click collapse arrow
4. **Expected:** Folder collapses
5. **Verify:** Same behavior as clicking folder name

#### Test 5: Mixed Interaction
1. Select materials folder using checkbox
2. Expand materials folder using name click
3. **Expected:** Folder is both selected AND expanded
4. **Verify:** Blue selection highlight + expanded contents visible

### Automated Test Validation

```javascript
// Browser MCP test script
async function validateFolderInteraction() {
  await browser.navigate('http://localhost:5173')
  await browser.wait(2)

  // Click Permissions tab
  await browser.click('Permissions tab', '[data-testid="permissions-tab"]')
  await browser.wait(1)

  // Test 1: Verify arrows are visible
  const snapshot1 = await browser.snapshot()
  const hasArrows = snapshot1.includes('aria-label="Expand') ||
                   snapshot1.includes('aria-label="Collapse')

  // Test 2: Click folder name to expand
  await browser.click('Materials folder name', '[data-path="materials"] .folder-name')
  await browser.wait(1)

  const snapshot2 = await browser.snapshot()
  const isExpanded = snapshot2.includes('materials/') &&
                    snapshot2.length > snapshot1.length

  // Test 3: Click checkbox to select
  await browser.click('Projects checkbox', '[data-path="projects"] input[type="checkbox"]')
  await browser.wait(0.5)

  const snapshot3 = await browser.snapshot()
  const isSelected = snapshot3.includes('bg-blue-50') || snapshot3.includes('border-blue-500')

  console.log('Test Results:')
  console.log('Arrows visible:', hasArrows ? 'PASS' : 'FAIL')
  console.log('Name click expands:', isExpanded ? 'PASS' : 'FAIL')
  console.log('Checkbox selects:', isSelected ? 'PASS' : 'FAIL')

  return hasArrows && isExpanded && isSelected
}
```

## Success Criteria
- [ ] Expand arrows are visible on all folders at all times
- [ ] Clicking folder name expands/collapses the folder
- [ ] Clicking checkbox selects/deselects the folder without expanding
- [ ] Clicking expand arrow expands/collapses the folder (same as name click)
- [ ] Visual feedback is clear for different interaction areas
- [ ] Hover states provide appropriate visual cues
- [ ] Loading indicators work correctly during expansion
- [ ] Behavior is consistent across all folder levels
- [ ] Accessibility attributes are properly set (aria-labels)

## Implementation Notes
- Maintain backward compatibility with existing permission functionality
- Ensure WebSocket updates continue working correctly
- Consider adding keyboard navigation in future iteration (arrow keys, enter, space)
- May need to adjust CSS spacing to accommodate always-visible arrows
- Test with long folder names to ensure layout doesn't break

## References
- Current Implementation: `frontend/src/components/TwoPanelPermissionEditor.tsx:29-117`
- Related Ticket: `003-FEATURE-file-browser-navigation.md`
- Standard File Explorer UX patterns (Windows Explorer, macOS Finder, VSCode Explorer)

## Estimated Effort
- Development: 2-3 hours
- Testing: 1 hour
- Total: 3-4 hours