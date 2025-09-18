# BUG-002: File Explorer Showing Incorrect Permissions

**Priority:** High
**Component:** Frontend - File Explorer
**Status:** Open
**Reporter:** User Investigation
**Created:** 2025-09-18

## Bug Description

The File Explorer tab is displaying completely incorrect permission indicators that contradict the actual permission rules in the database.

## Current State

**Active Rule:** `projects deny read` (ID: 8, Created: 9/17/2025)

**Expected File Explorer Display:**
- `materials/` → Gray "None" (no rule)
- `private stuff/` → Gray "None" (no rule)
- `projects/` → Red "Denied" or ✕ (explicit deny rule)

**Actual File Explorer Display:**
- `materials/` → Blue "Read" ❌ WRONG
- `private stuff/` → Gray "None" ✅ Correct
- `projects/` → Green "Write" ❌ COMPLETELY WRONG

## Critical Issue

**`projects/` shows "Write" access when there's an explicit "deny read" rule!**

This is a **security concern** - the UI is telling users they have write access to a directory that's actually denied.

## Root Cause Investigation Needed

The File Explorer appears to be using a different:
1. **API endpoint** than the Permissions tab
2. **Permission evaluation logic**
3. **Workspace context**

## Comparison: Permissions Tab vs File Explorer Tab

| Directory | Permissions Tab | File Explorer Tab | Actual Rule |
|-----------|----------------|------------------|-------------|
| materials | ✅ ? (gray) | ❌ Read (blue) | none |
| private stuff | ✅ ? (gray) | ✅ None (gray) | none |
| projects | ✅ ✕ (red) | ❌ Write (green) | deny read |

## Next Steps

1. **Identify File Explorer API calls** - Find which endpoints it uses
2. **Check workspace context** - Verify it's using the same active workspace
3. **Compare permission evaluation** - Check if different logic is being applied
4. **Fix the discrepancy** - Ensure both tabs show the same accurate data
5. **Security review** - Ensure no actual permission bypass exists

## Security Impact

**HIGH** - UI shows write access where deny rules exist. While this may be only a display issue, it could lead to user confusion and security assumptions.

---

**This is now the priority issue to investigate and fix.**