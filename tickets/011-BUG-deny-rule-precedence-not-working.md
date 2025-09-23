# 011-BUG: Deny Rule Precedence Not Working - Child Deny Rules Ignored

## Status: ✅ CLOSED - FIXED
**Created:** 2025-01-23
**Resolved:** 2025-01-23
**Priority:** High
**Component:** Backend - Permission Service / Precedence Logic
**Affects:** Phase 3B - Permission enforcement security

## Problem Statement

The permission precedence logic is not correctly handling deny rules when they conflict with parent allow rules. Specifically, child deny rules are being overridden by parent allow rules, creating a **serious security vulnerability** where explicitly denied access is being granted.

### Current vs Expected Behavior

**Current Behavior (SECURITY ISSUE):**
- Rule: `materials` → **allow read** (parent)
- Rule: `materials/01_Introduction to Software Engineering` → **deny read** (child)
- **RESULT:** Access to `materials/01_Introduction to Software Engineering` is **ALLOWED** ❌
- MCP call succeeds and lists contents when it should be denied

**Expected Behavior (SECURITY REQUIREMENT):**
- Rule: `materials` → **allow read** (parent)
- Rule: `materials/01_Introduction to Software Engineering` → **deny read** (child)
- **RESULT:** Access to `materials/01_Introduction to Software Engineering` should be **DENIED** ✅
- MCP call should return "Permission Denied" error

### Verified Test Case

```bash
# This should FAIL but currently SUCCEEDS
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_files", "arguments": {"path": "materials/01_Introduction to Software Engineering"}}, "id": 1}'

# CURRENT (WRONG): Returns file list
# EXPECTED (CORRECT): {"error": {"code": -32001, "message": "Permission Denied"}}
```

### Root Cause Analysis

The formal precedence logic specified in the documentation states:
1. **Specificity**: Child paths override parent paths
2. **Deny wins**: For equal specificity, deny overrides allow
3. **Write implies read**: Write permission grants read access
4. **Default deny**: No matching rules = access denied

**The bug is in Step 1 or 2** - either:
- Child paths are not correctly identified as more specific
- The deny rule is not overriding the allow rule for equal/higher specificity

### Security Impact Assessment

**Severity:** High - This is a security vulnerability
- 🔴 **Bypasses explicit access controls** - Administrators cannot reliably deny access
- 🔴 **Violates principle of least privilege** - Users get more access than intended
- 🔴 **Documentation mismatch** - System behaves differently than documented
- 🔴 **Compliance risk** - May violate security policies requiring explicit denies

**Attack Vector:** Users can access content that was explicitly denied by exploiting parent allow rules.

## Implementation Plan

### Step 1: Locate Precedence Logic Implementation
- **Files to examine:**
  - `backend/app/utils/trie.py` - Permission trie and precedence logic
  - `backend/app/services/database_permission_service.py` - Rule matching logic
  - `backend/app/schemas/workspace.py` - Permission resolution
- **Focus:** Find where path specificity is calculated and rule conflicts are resolved

### Step 2: Debug Path Matching Algorithm
- **Test specificity calculation:**
  - Verify `materials/01_Introduction to Software Engineering` is considered more specific than `materials`
  - Check if both rules are being found during lookup
  - Validate that the more specific rule is selected
- **Log rule matching process** to trace decision making

### Step 3: Fix Precedence Logic
- **Ensure child paths override parent paths** regardless of rule type
- **Implement proper tie-breaking** where deny wins over allow
- **Add comprehensive test cases** for all precedence scenarios

### Step 4: Validate All Precedence Rules
- **Test specificity precedence**: child > parent
- **Test deny precedence**: deny > allow (same specificity)
- **Test write implies read**: write grants both read and write
- **Test default deny**: unmatched paths are denied

### Step 5: Security Hardening
- **Add precedence validation tests** to prevent regression
- **Document security implications** of rule ordering
- **Add warnings** for conflicting rules in UI

## Test Plan

### Critical Security Test Cases

#### 1. **Child Deny Overrides Parent Allow (PRIMARY BUG)**
```bash
# Setup: materials (allow read) + materials/01_Introduction (deny read)
# Test: Access to materials/01_Introduction should be DENIED

curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_files", "arguments": {"path": "materials/01_Introduction to Software Engineering"}}, "id": 1}'

# EXPECTED: {"error": {"code": -32001, "message": "Permission Denied"}}
# CURRENT: Returns file list (BUG)
```

#### 2. **Parent Allow Still Works for Non-Denied Children**
```bash
# Test: Access to materials/02_Introduction should be ALLOWED
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_files", "arguments": {"path": "materials/02_Introduction to Cloud Computing"}}, "id": 2}'

# EXPECTED: Returns file list
```

#### 3. **Multiple Deny Rules Work**
```bash
# Add another deny rule and test both are enforced
# Test both materials/01_Introduction and new deny rule
```

#### 4. **Deny Overrides Allow at Same Level**
```bash
# Setup: Two rules for exact same path - one allow, one deny
# Test: Deny should win
```

### Comprehensive Precedence Test Matrix

| Parent Rule | Child Rule | Expected Access | Current Result | Status |
|-------------|------------|----------------|----------------|---------|
| allow read | deny read | **DENIED** | ALLOWED | ❌ **BUG** |
| allow read | allow write | **WRITE** | WRITE | ✅ OK |
| allow write | deny read | **DENIED** | ??? | ⚠️ Test needed |
| deny read | allow read | **DENIED** | ??? | ⚠️ Test needed |
| (none) | allow read | **READ** | READ | ✅ OK |
| (none) | deny read | **DENIED** | DENIED | ✅ OK |

### Automated Testing

```python
async def test_precedence_rules():
    """Comprehensive test of permission precedence logic."""

    # Test 1: Critical security bug
    result = await mcp_call("list_files", {"path": "materials/01_Introduction to Software Engineering"})
    assert "error" in result, "Child deny rule should override parent allow"
    assert result["error"]["code"] == -32001, "Should return Permission Denied"

    # Test 2: Parent allow still works for non-denied paths
    result = await mcp_call("list_files", {"path": "materials/02_Introduction to Cloud Computing"})
    assert "result" in result, "Parent allow should work for non-denied children"

    # Test 3: Direct path matching
    result = await mcp_call("list_files", {"path": "materials"})
    assert "result" in result, "Direct allow rule should work"

    # Test 4: Verify specificity calculation
    assert is_more_specific("materials/01_Introduction", "materials")
    assert is_more_specific("a/b/c", "a/b")
    assert not is_more_specific("materials", "materials/01_Introduction")

    print("✅ All precedence tests passed")
    return True

def is_more_specific(child_path: str, parent_path: str) -> bool:
    """Test the specificity calculation logic."""
    # This function should exist in the trie or permission service
    pass
```

### Browser MCP Testing

```javascript
async function testPermissionPrecedence() {
    // Navigate to permission editor
    await browser.navigate('http://localhost:5173')
    await browser.click('File Browser tab', 'file-browser-tab')
    await browser.screenshot()

    // Verify UI shows correct permission indicators
    const snapshot = await browser.snapshot()

    // materials should show blue dot (read access)
    const hasMaterialsRead = snapshot.includes('materials') && snapshot.includes('●') && snapshot.includes('R')

    // 01_Introduction should show gray dot (denied access) or red indicator
    const hasIntroductionDenied = snapshot.includes('01_Introduction') &&
                                 (snapshot.includes('○') || snapshot.includes('denied'))

    console.log('UI Permission Indicators:')
    console.log('Materials (read):', hasMaterialsRead ? 'PASS ✅' : 'FAIL ❌')
    console.log('Introduction (denied):', hasIntroductionDenied ? 'PASS ✅' : 'FAIL ❌')

    return hasMaterialsRead && hasIntroductionDenied
}
```

## Success Criteria

- [ ] **PRIMARY:** `materials/01_Introduction to Software Engineering` access is DENIED
- [ ] **SECONDARY:** `materials/02_Introduction to Cloud Computing` access is ALLOWED
- [ ] **UI:** File browser shows correct indicators (gray/red for denied paths)
- [ ] **API:** Batch permissions endpoint returns `"status": "denied"` for denied paths
- [ ] **Documentation:** Precedence logic matches implementation
- [ ] **Performance:** No degradation in permission checking speed
- [ ] **Regression:** All existing permission tests still pass

### Specific API Response Requirements

```json
// materials/01_Introduction should return:
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Permission Denied",
    "data": "Operation 'read' is not permitted for path: materials/01_Introduction to Software Engineering"
  }
}

// Batch API should return:
{
  "results": [
    {
      "path": "materials/01_Introduction to Software Engineering",
      "status": "denied",
      "matchedRule": {
        "id": "db-rule-11",
        "rule_type": "deny",
        "permission_type": "read"
      }
    }
  ]
}
```

## Technical Investigation Areas

### 1. Trie Implementation (`backend/app/utils/trie.py`)
- Path normalization and comparison logic
- Specificity calculation algorithm
- Rule conflict resolution
- Cache invalidation on rule changes

### 2. Permission Service (`backend/app/services/database_permission_service.py`)
- `check_access_with_rule` method
- `batch_check_permissions` method
- Rule matching and precedence logic
- Database query optimization

### 3. Database Schema
- Rule ordering in database queries
- Index performance for path lookups
- Rule conflict detection at storage time

### 4. Frontend Integration
- Permission indicator calculation
- Real-time rule update handling
- Conflict warning systems

## Risk Assessment

**Security Risk:** High
- Users can bypass explicit access denials
- Administrators cannot reliably restrict sensitive content
- Potential data exposure in educational/corporate environments

**Business Risk:** Medium
- Feature works partially but unreliably
- Documentation promises cannot be fulfilled
- User trust in security model compromised

**Technical Risk:** Low
- Isolated to permission logic
- No data corruption risk
- Fixable through algorithm correction

## Related Issues

- **Blocks:** Reliable security policy enforcement
- **Related:** UI permission indicator accuracy
- **Dependency:** Trie-based permission caching
- **Future:** Advanced permission schemes (time-based, conditional)

## References

### Current Permission Rules (Workspace ID: 2)
```json
[
  {"id": 8, "path": "projects", "permission_type": "read", "rule_type": "allow"},
  {"id": 9, "path": "private stuff", "permission_type": "write", "rule_type": "allow"},
  {"id": 10, "path": "materials", "permission_type": "read", "rule_type": "allow"},
  {"id": 11, "path": "materials/01_Introduction to Software Engineering", "permission_type": "read", "rule_type": "deny"},
  {"id": 12, "path": "Working with react", "permission_type": "read", "rule_type": "allow"}
]
```

### Documented Precedence Rules
From `config/permissions.json` specification:
```json
{
  "precedence_rules": {
    "rules": [
      "1. Specificity: Child paths override parent paths",
      "2. Deny wins: For equal specificity, deny overrides allow",
      "3. Write implies read: Write permission grants read access",
      "4. Default deny: No matching rules = access denied"
    ]
  }
}
```

### Test Commands
```bash
# Test the bug
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_files", "arguments": {"path": "materials/01_Introduction to Software Engineering"}}, "id": 1}'

# Check batch API
curl -X POST http://localhost:8000/api/workspaces/2/effective-permissions:batch \
  -H "Content-Type: application/json" \
  -d '{"paths": ["materials/01_Introduction to Software Engineering"]}'
```

---

## ✅ RESOLUTION SUMMARY

**Root Cause:** Permission service error handling was treating legitimate permission denials as service errors, causing fallback to hardcoded permissions that allowed access to denied paths.

**Fix Applied:** Modified `backend/app/services/permission_service.py` to distinguish between:
- Permission denials (expected - re-raise the PermissionError)
- Service errors (unexpected - fall back to basic permissions)

**Files Changed:**
- `backend/app/services/permission_service.py` - Fixed error handling logic

**Test Results:**
- ✅ `materials/01_Introduction to Software Engineering` now properly DENIED
- ✅ `materials` and other allowed paths still work correctly
- ✅ Write operations to denied paths also properly DENIED
- ✅ Batch API consistency maintained
- ✅ No more fallback messages in logs for legitimate denials

**Security Impact:** CLOSED - Users can no longer bypass explicit deny rules. Permission precedence now works as documented.

---

**RESOLVED:** This security vulnerability has been fixed. Deny rule precedence now works correctly and explicit access denials are properly enforced.