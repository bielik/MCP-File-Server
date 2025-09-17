# Feature Spec: Dynamic Workspace & Permission Management (v3.0 - Final Implementation Blueprint)

**Document Version:** 3.3
**Date:** 2025-01-15
**Status:** ✅ Phase 3A Complete - Database-Driven Permission System with Full Workspace Backend

---

### 1. Why?: The Problem & Goals

The current static, hardcoded permission system is a significant bottleneck, limiting the application's flexibility and requiring developer intervention for changes. This feature introduces a dynamic, UI-driven system to solve these limitations.

**Goals:**
* **Decouple Permissions from Code:** Enable real-time permission management via the UI.
* **Introduce Multi-Context Sessions ("Workspaces"):** Allow users to tailor the AI's environment for specific, concurrent tasks.
* **Provide Granular, Auditable Control:** Implement a robust `allow`/`deny` system with clear precedence rules and audit trails.

### 2. What?: The User Experience

This feature will introduce a "Workspaces" section in the UI, enabling users to manage the AI's file access context. Key features include a workspace switcher, a two-panel permission editor for granting `read`/`write` access and creating `deny` exceptions, and clear visual indicators for the permission status of all files. A crucial new UI feature will be the "Inspect Permission" tooltip, which explains exactly *why* a file has a certain status by showing the specific rule that was applied.

### 3. How?: Technical Implementation Plan

This plan adopts an incremental, three-phase rollout strategy, guided by feature flags, to manage complexity and risk. It incorporates extensive feedback on security, performance, and API design.

**Core Strategy: Feature Flags**
Implementation will be wrapped in feature flags to allow for gradual rollout and safe rollbacks.
```python
# config.py
FEATURE_FLAGS = {
    "ENABLE_CONFIG_FILE_PERMISSIONS": False, # Activates Phase 2
    "ENABLE_DATABASE_PERMISSIONS": False     # Activates Phase 3
}


#### ✅ **Phase 1: Frontend Fundamentals & Read-Only Visualization** (COMPLETED)

*Goal: Build foundational UI components and visualize the existing permission system without altering backend logic.*

**✅ Backend Tasks Completed:**

1.  ✅ **Create Hardened Browser API:** Implemented `GET /api/browse` with pagination (`page`, `pageSize`), security hardening, and directory traversal prevention.
2.  ✅ **Expose Current Permissions:** Implemented `GET /api/current-permissions` to return the hardcoded `PERMISSIONS` dictionary with descriptions.

**✅ Frontend Tasks Completed:**

1.  ✅ **Build Advanced File Explorer:** Created comprehensive file explorer component with tree navigation, breadcrumbs, pagination, and folder navigation.
2.  ✅ **Display Permission Indicators:** Implemented color-coded permission badges (Read-Only/Read-Write/No Access) with tooltips.
3.  ✅ **Enhanced UI Architecture:** Built tabbed interface with File Explorer and Server Status views.
4.  ✅ **Permission Legend:** Added sidebar with permission explanations and real-time activity feed.

**✅ Testing Results:**

  * ✅ **Unit Tests:** API endpoints pass security tests including directory traversal prevention.
  * ✅ **Integration Tests:** Frontend correctly renders file tree, handles pagination, and displays accurate permission indicators.
  * ✅ **User Experience Tests:** Navigation, pagination, and permission visualization work seamlessly.

-----

#### ✅ **Phase 2: Config-File Driven Permissions & Performance** (COMPLETED)

*Goal: Decouple permissions from code, implement formalized logic and caching, and provide a simple UI for editing.*

**✅ Backend Tasks Completed:**

1.  ✅ **Test Matrix Implementation:** Created comprehensive `pytest` test suite for permission precedence logic with integration tests.
2.  ✅ **Permissions Externalized:** Successfully moved hardcoded rules to `config/permissions.json` with formal schema and validation.
3.  ✅ **Formal Precedence Logic & Caching:** Implemented `ConfigPermissionService` with Trie-based caching for O(log n) permission resolution. Full precedence rules implemented (specificity, deny-wins, write-implies-read, default-deny).
4.  ✅ **Hardened Config Management API:** Implemented secure `GET /api/config/permissions` and `PUT /api/config/permissions` with ETag/If-Match concurrency control and atomic file operations (temp + fsync + rename pattern).
5.  ✅ **Bug Fixes Applied:** Fixed critical file persistence bug where rule modifications weren't saving to disk, corrected frontend API integration.

**✅ Frontend Tasks Completed:**

1.  ✅ **Permission Editor Built:** Created comprehensive Settings page with visual and JSON editors for `permissions.json` management.
2.  ✅ **Rule ID Display:** Enhanced UI to show rule IDs for better debugging and management clarity.
3.  ✅ **API Integration Fixed:** Updated PermissionIndicator component to use `/api/config/permissions` endpoint with proper precedence rule implementation.

**✅ Testing Results:**

  * ✅ **Unit Tests:** All `PermissionService` precedence logic tests pass. ETag concurrency control working correctly (412 errors on conflicts).
  * ✅ **Integration Tests:** Full system tested with real filesystem at `C:/Users/MartinBielik/MCP Test/` containing materials/, projects/, and private directories.
  * ✅ **MCP Protocol Verification:** Successfully tested via wisdom MCP server with HTTP transport:
    - List operations: ✅ Working (materials directory with 16 items)
    - Read operations: ✅ Working (file content retrieval)
    - Write operations: ✅ Working (created test files in projects/)
    - Permission enforcement: ✅ Working (deny rules correctly block materials/01_Introduction to Software Engineering)
  * ✅ **Performance Verified:** Permission resolution optimized with Trie caching, meeting performance requirements.

-----

#### ✅ **Phase 3A: Backend Migration to Database** (COMPLETED)

*Goal: Migrate the entire permission system to a database backend, preparing for the full workspace UI.*

**✅ Backend Tasks Completed:**

1.  ✅ **Implement Data Model:** Complete `Workspace` and `Permission` SQLAlchemy models with all specified constraints (Appendix D) implemented in `backend/app/models/workspace.py`.
2.  ✅ **Build Core APIs:** Full Workspace and Permission CRUD APIs implemented with comprehensive endpoints for workspace and permission management.
3.  ✅ **Implement Batch `effective-permissions` API:** Complete `POST /api/workspaces/{id}/effective-permissions:batch` endpoint implemented. Returns status and `matchedRule` for each path with optimized batch processing.
4.  ✅ **Refactor `PermissionService`:** New `DatabasePermissionService` implemented in `backend/app/services/database_permission_service.py` with database backend and preserved Trie-based caching.
5.  ✅ **Implement Audit Logging:** Comprehensive audit logging service implemented in `backend/app/services/audit_logger.py` with structured event tracking.
6.  ✅ **Create Migration Script:** Complete migration script at `backend/app/scripts/migrate_config_to_db.py` with dry-run support, idempotent execution, and comprehensive error handling.

**✅ Testing Results:**

  * ✅ **Unit Tests:** Complete test suite in `backend/tests/phase3a/` covering all API endpoints, database constraints, duplicate rule rejection, and migration script functionality.
  * ✅ **Integration Tests:** Full integration testing including the `:batch` endpoint with correct status and `matchedRule` explanations. Performance testing validates sub-100ms response times for 100+ path batch requests.
  * ✅ **Database Schema:** All constraints working correctly including unique permission rules, workspace activation logic, and cascade deletions.

#### ✅ **Phase 3B: Advanced UI & Full Workspace Experience** (COMPLETED)

*Goal: Build the final user-facing features for complete workspace and permission management.*

**✅ Frontend Tasks Completed:**

1.  ✅ **Build Workspace UI:** Complete UI components implemented for creating, deleting, and activating workspaces. Workspace activation triggers proper UI refresh and permission cache invalidation. Active workspace indicator displays current context.
2.  ✅ **Build Two-Panel Permission Editor:** Full editor implemented in `TwoPanelPermissionEditor` component. Left panel provides file tree navigation, right panel uses the `:batch` endpoint for efficient permission status fetching and displays real-time indicators.
3.  ✅ **Implement "Inspect Permission" UI:** Permission indicators support both hover tooltips and click modals. Uses `matchedRule` data from `:batch` API to display human-readable explanations of permission decisions with rule precedence details.

**✅ Testing Results:**

  * ✅ **Backend Test Suite:** Comprehensive test infrastructure in `backend/tests/phase3b/` with E2E workflow tests, integration tests, and performance benchmarks. Test isolation and session management issues resolved.
  * ✅ **Frontend Test Suite:** Complete browser MCP test infrastructure in `frontend/tests/browser-mcp/` with workspace management, permission editor, and real-time update tests (72.3 KB total test code).
  * ✅ **Integration Validation:** Full workspace lifecycle confirmed working: create workspace → add permissions → activate → verify permission indicators display correctly in File Explorer.
  * ✅ **Permission System Verification:** Confirmed working with actual filesystem at `C:/Users/MartinBielik/MCP Test/`:
    - materials/: Read-Only access ✅
    - projects/: Read-Write access ✅
    - private stuff/: No Access ✅
  * ✅ **Performance Validated:** Batch API meets <100ms response time targets, Trie-based caching operational, memory usage stable.

-----

### 4\. Migration & Deprecation Strategy

  * **Phase 2 -\> 3 Migration:** The `permissions.json` to database migration will be handled by a one-time execution of the migration script during deployment.
  * **/shared-fs Deprecation:** The `/shared-fs` mount will be maintained for backward compatibility. After Phase 3, it will be exposed as a virtual `legacy/` directory within the `/source` mount. The UI will display a prominent, non-blocking warning to users still relying on the old system, guiding them to migrate their configuration. The `legacy/` mount will be fully removed in a future major version release.

-----

### 5\. Appendix: Technical Specifications

#### A: Path Normalization & Security

All path inputs to the backend MUST undergo the following normalization and validation sequence:

1.  Resolve `realpath` to handle symbolic links.
2.  Verify the resolved path is a child of the `/source` base directory. Reject if it is not.
3.  Apply Unicode normalization (NFC).
4.  Collapse multiple slashes (e.g., `//`) into a single slash.
5.  Strip any trailing slash.
6.  Paths are treated case-sensitively internally.

#### B: Permission Precedence Logic

The logic for `check_access` is as follows:

1.  **Specificity:** A rule on a child path is more specific than a rule on a parent path.
2.  **Tie-Breaker:** For rules of equal specificity, **`deny` wins over `allow`**.
3.  **Implied Permissions:** A `write` permission implicitly grants `read`.
4.  **Default:** If no rule matches, access is **denied**.

#### C: Caching Strategy

The active workspace's permission rules will be loaded into an in-memory **Trie** data structure. This provides highly efficient prefix matching for resolving permissions. The cache is invalidated and rebuilt upon workspace activation or any change to the active workspace's rules.

#### D: Database Schema

**`workspaces` table:**

  * `id`, `name` (UNIQUE), `description`, `is_active`, `created_at`, `updated_at`.

**`permissions` table:**

  * `id`: INTEGER, PRIMARY KEY
  * `workspace_id`: INTEGER, FOREIGN KEY, INDEX
  * `path`: VARCHAR, NOT NULL, INDEX
  * `permission_type`: VARCHAR, NOT NULL (`read`, `write`)
  * `rule_type`: VARCHAR, NOT NULL (`allow`, `deny`)
  * `created_at`, `updated_at`, `created_by`, `updated_by`
  * **Constraint:** `UNIQUE(workspace_id, path, permission_type, rule_type)`

#### E: API Contracts

  * **`GET /api/browse`**:
      * Query Params: `path=<string>`, `maxDepth=<int>`, `page=<int>`, `pageSize=<int>`.
      * Returns: Paginated list of file/folder objects.
  * **`PUT /api/config/permissions`**:
      * Headers: `If-Match: <etag>`.
      * Returns: `200 OK` on success, `412 Precondition Failed` on ETag mismatch.
  * **`POST /api/workspaces/{id}/effective-permissions:batch`**:
      * Body: `{ "paths": ["/path/one", "/path/two"] }`.
      * Returns: `{ "results": [{ "path": "/path/one", "status": "read", "matchedRule": {...} }] }`.
  * All endpoints will return standardized JSON errors: `{ "code": "string", "message": "string", "details": {} }`.

