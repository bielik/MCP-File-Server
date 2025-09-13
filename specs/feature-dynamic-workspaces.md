# **Implementation Plan: Dynamic Workspace & Permission Management**

**Document Version:** 1.0
**Date:** 2025-09-13
**Author:** Architect (G)

### 1. Executive Summary & Goals

This document outlines the plan to replace the current static, hardcoded file permission system with a dynamic, database-driven model centered around the concept of **Workspaces**.

**Primary Goals:**
* **Enhance Flexibility:** Allow users to define multiple, distinct contexts ("Workspaces") for an AI client, each with its own granular set of file permissions.
* **Improve User Experience:** Enable users to configure all permissions through the web UI, removing the need to edit backend code or configuration files.
* **Strengthen Security:** Implement a robust "default-deny" security model where access is only granted through explicit rules, including the ability to define exceptions.
* **Future-Proof the Architecture:** Create a scalable permission system that can be easily extended to support future tools like keyword or semantic search.

### 2. Architectural Design

The new architecture decouples the physical file system from the virtual view presented to the AI client using three core concepts:

1.  **Root Paths**: Top-level host directories (e.g., `C:\Users\...\Documents`) mounted into a common `/source` directory inside the container. These are the raw materials for Workspaces but are never directly exposed.
2.  **Workspaces**: A named session (e.g., "Project X Research," "Tax Preparation") that represents a specific configuration of permissions. Only one Workspace can be active at a time, defining the AI's current context.
3.  **Permissions**: Database records that link a Workspace to specific file paths. Each rule defines a `path`, a `permission_type` (`read`, `write`), and a `rule_type` (`allow`, `deny`).



The core security principle is that the **most specific permission rule always wins**. This allows a `deny` rule on a specific file to override an `allow` rule on its parent folder.

### 3. Key User Workflows

**Workflow A (AI Client): Initial File System Discovery**
1.  **Initiator:** AI Client.
2.  **Action:** The client, having no prior knowledge of the file structure, calls the `list_files` tool with an empty `path` parameter (`"path": ""`).
3.  **Server Process:**
    * The backend identifies the empty path request as a special case for root discovery.
    * It queries the database for all `allow` rules in the currently active Workspace.
    * It extracts the unique, top-level directories from these rules (e.g., `documents`, `archive`).
4.  **Outcome:** The client receives a list containing only the top-level virtual directories it has access to, providing a starting point for navigation.

**Workflow B (AI Client): Secure Directory Listing**
1.  **Initiator:** AI Client.
2.  **Context:** The active Workspace grants `read` access to `documents/project-alpha` but has an explicit `deny` rule on `documents/project-alpha/budget.xlsx`.
3.  **Action:** The client calls `list_files` with `"path": "documents/project-alpha"`.
4.  **Server Process:**
    * The backend verifies the client can read the requested directory.
    * It performs a raw listing of the corresponding physical directory (`/source/documents/project-alpha`).
    * It iterates through each item in the raw list, checking its permissions individually.
    * The `budget.xlsx` file is skipped because its specific `deny` rule overrides the parent folder's `allow` rule.
5.  **Outcome:** The client receives a filtered list of contents, completely unaware that `budget.xlsx` exists.

**Workflow C (UI User): Workspace Configuration**
1.  **Initiator:** UI User.
2.  **Action:** The user wants to grant the AI `write` access to the `documents/project-beta` directory.
3.  **UI Process:**
    * The user selects the "Project Beta" Workspace from a dropdown, making it active.
    * The UI displays a two-panel view:
        * **Left Panel (Source Browser):** Shows the complete, un-permissioned contents of the `/source` mount, fetched via the new `/api/browse` endpoint.
        * **Right Panel (Workspace Permissions):** Shows the files and folders that currently have rules in this Workspace.
    * The user navigates to `documents/` in the left panel, selects the `project-beta` folder, and adds it to the right panel, selecting `'write'` permission from a dialog.
    * The UI sends a `POST` request to `/api/workspaces/{id}/permissions` to save the new `allow write` rule.
4.  **Outcome:** The permission is saved to the database. The next time the AI client accesses its tools, it will have write access to the `documents/project-beta` directory.

### 4. Phased Implementation Plan

---

#### **Phase 1: Backend Foundation & Data Model**
*Goal: Establish the database schema and API endpoints required to manage workspaces and permissions.*

**Step 1.1: Database Schema Creation**
* **Tasks:**
    1.  Create `Workspace` and `Permission` SQLAlchemy models in a new `backend/app/models/workspace.py` file.
    2.  Update `backend/app/main.py`'s `on_startup` event to create these new tables.
* **Unit Tests:**
    * Verify that `Workspace` and `Permission` model instances can be created correctly.
    * Test the foreign key relationship between the models.

**Step 1.2: Configuration & Mounting Update**
* **Tasks:**
    1.  Update project documentation (`README.md`) to specify the new `ROOT_PATH_X` format for the `.env` file.
    2.  Update `docker-compose.yml` to mount the specified host paths into the `/source` directory in the backend container.
* **Tests:**
    * Manual verification: `docker-compose exec backend ls /source` should show the mounted directories.

**Step 1.3: CRUD APIs for Workspaces & Permissions**
* **Tasks:**
    1.  Create `schemas` and `crud` functions for `Workspace` and `Permission`.
    2.  Implement a new API router in `backend/app/api/endpoints/workspaces.py` with the following endpoints:
        * `GET /api/workspaces`
        * `POST /api/workspaces`
        * `PUT /api/workspaces/{id}/activate`
        * `GET /api/workspaces/{id}/permissions`
        * `POST /api/workspaces/{id}/permissions`
        * `DELETE /api/permissions/{id}`
* **Unit Tests:**
    * Write tests for each CRUD function, mocking database calls.
* **Integration Tests:**
    * Write API tests (using FastAPI's `TestClient`) that hit the actual endpoints to create a workspace, add a permission, and then delete them.

---

#### **Phase 2: Core Logic Refactoring**
*Goal: Replace all hardcoded permission logic with the new dynamic, database-driven system.*

**Step 2.1: Refactor `PermissionService`**
* **Tasks:**
    1.  Delete the hardcoded `PERMISSIONS` dictionary.
    2.  Implement a function `get_active_workspace()` that queries the database.
    3.  Rewrite `check_access(path, operation)` to:
        * Fetch all permissions for the active workspace.
        * Filter for rules applying to the given `path`.
        * Implement the "most specific rule wins" logic to determine the final outcome (`allow` or `deny`).
* **Unit Tests:**
    * This is critical. Create a comprehensive test suite for `check_access` with mock database responses. Test scenarios:
        * Simple allow.
        * Simple deny.
        * Parent `allow`, specific child `deny` (should deny child).
        * Parent `deny`, specific child `allow` (should allow child).
        * No matching rule (should deny).
        * Permission check on the root directory.

**Step 2.2: Refactor `FileService`**
* **Tasks:**
    1.  Update `read_file`, `write_file`, and `list_files` to only use the refactored `permission_service.check_access`.
    2.  In `list_files`, implement the special logic for an empty `path` to discover the root directories.
    3.  In `list_files`, ensure the post-listing filtering loop is implemented correctly.
* **Unit Tests:**
    * Mock `permission_service` to verify that `file_service` functions call it correctly before any file system access.
* **Integration Tests:**
    * Set up a test workspace and permissions in the database.
    * Call the `tools/call` MCP endpoint for `list_files` and assert that the returned list is correctly filtered based on the database rules.

---

#### **Phase 3: Frontend Implementation**
*Goal: Build the UI components necessary for users to manage workspaces and permissions.*

**Step 3.1: "Source Browser" API Endpoint**
* **Tasks:**
    1.  Create a new, UI-only endpoint: `GET /api/browse`.
    2.  This endpoint lists the raw contents of `/source` and must include robust security to prevent directory traversal attacks (e.g., `?path=../`).
* **Unit Tests:**
    * Write tests specifically for the path traversal security checks.

**Step 3.2: Workspace Management UI**
* **Tasks:**
    1.  Create a React component that fetches and displays the list of workspaces from `GET /api/workspaces`.
    2.  Implement functionality to create new workspaces and to set a workspace as active via the API.
* **Unit Tests:**
    * Use React Testing Library to test component rendering and interactions with mock API calls.

**Step 3.3: Two-Panel Permission Editor UI**
* **Tasks:**
    1.  Build the main two-panel layout. The left panel uses `/api/browse`, the right panel uses `/api/workspaces/{id}/permissions`.
    2.  Implement the client-side helper function `getPermissionStatus(path)` that merges the file list with the rules list to determine the status for each item.
    3.  Render status indicators (e.g., icons) next to each file/folder.
    4.  Implement the user interactions (e.g., drag-and-drop, context menus) for adding/removing permissions.
* **Unit Tests:**
    * Write comprehensive tests for the `getPermissionStatus` helper function with various mock rule sets to ensure it correctly identifies the winning rule.

### 5. Appendix

#### A: Database Schema

**`workspaces` table:**
* `id`: INTEGER, PRIMARY KEY
* `name`: VARCHAR, UNIQUE, NOT NULL
* `description`: VARCHAR
* `is_active`: BOOLEAN, NOT NULL, DEFAULT `False`

**`permissions` table:**
* `id`: INTEGER, PRIMARY KEY
* `workspace_id`: INTEGER, FOREIGN KEY (`workspaces.id`)
* `path`: VARCHAR, NOT NULL
* `permission_type`: VARCHAR, NOT NULL (`read`, `write`)
* `rule_type`: VARCHAR, NOT NULL (`allow`, `deny`)

#### B: API Contracts

* `GET /api/browse?path=<string>`: Returns a JSON list of files/folders at a given path within `/source`.
* `GET /api/workspaces`: Returns a list of all `Workspace` objects.
* `POST /api/workspaces`: Creates a new workspace. Body: `{ "name": "string", "description": "string" }`.
* `PUT /api/workspaces/{id}/activate`: Sets a workspace as active.
* `GET /api/workspaces/{id}/permissions`: Returns a list of all `Permission` objects for a workspace.
* `POST /api/workspaces/{id}/permissions`: Creates a new permission rule. Body: `{ "path": "string", "permission_type": "string", "rule_type": "string" }`.
* `DELETE /api/permissions/{id}`: Deletes a specific permission rule.