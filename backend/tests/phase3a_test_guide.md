# Phase 3A Test Guide: Database Migration Implementation

**Document Version:** 1.0
**Date:** 2025-01-14
**Status:** Ready for Implementation
**Estimated Testing Time:** 2-3 hours (independent tester)

---

## Overview

This document provides comprehensive testing instructions for Phase 3A of the MCP KnowledgeExplorer: **Backend Migration to Database**. Phase 3A migrates the permission system from config files to a database backend while preserving all existing functionality and performance characteristics.

## Phase 3A Goals

**Primary Objective:** Migrate the entire permission system to a database backend, preparing for the full workspace UI.

**Key Features to Test:**
1. **Database Models** - Workspace and Permission SQLAlchemy models
2. **Core APIs** - Workspace and Permission CRUD operations
3. **Batch Effective Permissions** - The cornerstone API for UI integration
4. **Refactored Permission Service** - Database-backed permission resolution
5. **Audit Logging** - Structured audit events for each permission decision
6. **Migration Script** - One-shot migration from `permissions.json` to database

---

## Prerequisites

### Environment Setup
```bash
# 1. Ensure you're in the backend directory
cd backend/

# 2. Install test dependencies
pip install -r requirements.txt

# 3. Set up test environment variables
export ENABLE_DATABASE_PERMISSIONS=true
export ENABLE_CONFIG_FILE_PERMISSIONS=false
export TEST_DATABASE_PATH=./data/test_database.db

# 4. Ensure clean database state
rm -f ./data/test_database.db
```

### Feature Flag Configuration
The Phase 3A tests require specific feature flags:
```python
# In test environment
FEATURE_FLAGS = {
    "ENABLE_CONFIG_FILE_PERMISSIONS": False,  # Disable Phase 2
    "ENABLE_DATABASE_PERMISSIONS": True       # Enable Phase 3A
}
```

---

## Test Suite Structure

### Test Organization
```
backend/tests/phase3a/
├── conftest.py                     # Test fixtures and utilities
├── test_database_models.py         # Database model validation
├── test_workspace_api.py           # Workspace CRUD operations
├── test_permission_api.py          # Permission CRUD operations
├── test_batch_effective_permissions.py # Batch API (cornerstone)
├── test_permission_service_refactor.py # Service layer testing
├── test_migration_script.py        # Config to DB migration
├── test_audit_logging.py           # Audit event validation
├── test_integration_phase3a.py     # End-to-end integration
└── test_data/
    ├── sample_workspaces.json
    ├── sample_permissions.json
    └── migration_test_config.json
```

---

## Test Execution Instructions

### Running All Phase 3A Tests
```bash
# Run the complete Phase 3A test suite
pytest backend/tests/phase3a/ -v

# Run with coverage report
pytest backend/tests/phase3a/ --cov=app --cov-report=html

# Run specific test category
pytest backend/tests/phase3a/test_database_models.py -v
```

### Individual Test Categories

#### 1. Database Models (`test_database_models.py`)
**Purpose:** Validate SQLAlchemy models and database constraints

```bash
pytest backend/tests/phase3a/test_database_models.py -v
```

**Expected Outcomes:**
- ✅ Workspace model creates with all required fields
- ✅ Unique constraint on workspace name enforced
- ✅ Permission model creates with foreign key relationship
- ✅ Unique constraint on (workspace_id, path, permission_type, rule_type) enforced
- ✅ Cascade delete from workspace to permissions works
- ✅ Timestamp fields auto-populate on creation/update

**Test Scenarios:**
1. Create workspace with valid data
2. Attempt duplicate workspace name (should fail)
3. Create permission with valid workspace reference
4. Attempt duplicate permission rule (should fail)
5. Delete workspace cascades to permissions
6. Timestamps update correctly

#### 2. Workspace API (`test_workspace_api.py`)
**Purpose:** Validate workspace management endpoints

```bash
pytest backend/tests/phase3a/test_workspace_api.py -v
```

**Expected Outcomes:**
- ✅ `POST /api/workspaces` creates workspace
- ✅ `GET /api/workspaces` lists all workspaces
- ✅ `GET /api/workspaces/{id}` retrieves specific workspace
- ✅ `PUT /api/workspaces/{id}` updates workspace
- ✅ `DELETE /api/workspaces/{id}` deletes workspace
- ✅ `POST /api/workspaces/{id}/activate` activates workspace
- ✅ Error handling for invalid requests (400, 404, 409)

**Critical Test Cases:**
1. **Workspace Creation:**
   ```json
   POST /api/workspaces
   {
     "name": "Test Workspace",
     "description": "Test workspace for validation"
   }
   ```
   Expected: `201 Created` with workspace object

2. **Duplicate Name Rejection:**
   ```json
   POST /api/workspaces
   {
     "name": "Test Workspace",  # Same name as above
     "description": "Duplicate test"
   }
   ```
   Expected: `409 Conflict`

3. **Workspace Activation:**
   ```json
   POST /api/workspaces/1/activate
   ```
   Expected: `200 OK`, workspace marked as active, others deactivated

#### 3. Permission API (`test_permission_api.py`)
**Purpose:** Validate permission management within workspaces

```bash
pytest backend/tests/phase3a/test_permission_api.py -v
```

**Expected Outcomes:**
- ✅ `POST /api/workspaces/{id}/permissions` creates permission
- ✅ `GET /api/workspaces/{id}/permissions` lists permissions
- ✅ `PUT /api/permissions/{id}` updates permission
- ✅ `DELETE /api/permissions/{id}` deletes permission
- ✅ Duplicate rule rejection enforced
- ✅ Workspace-scoped permission isolation

**Critical Test Cases:**
1. **Permission Creation:**
   ```json
   POST /api/workspaces/1/permissions
   {
     "path": "projects/test",
     "permission_type": "read",
     "rule_type": "allow",
     "description": "Test read access"
   }
   ```
   Expected: `201 Created` with permission object

2. **Duplicate Rule Rejection:**
   ```json
   POST /api/workspaces/1/permissions
   {
     "path": "projects/test",
     "permission_type": "read",
     "rule_type": "allow",  # Same as above
     "description": "Duplicate rule"
   }
   ```
   Expected: `409 Conflict`

#### 4. Batch Effective Permissions (`test_batch_effective_permissions.py`)
**Purpose:** Validate the cornerstone API for UI integration

```bash
pytest backend/tests/phase3a/test_batch_effective_permissions.py -v
```

**Expected Outcomes:**
- ✅ `POST /api/workspaces/{id}/effective-permissions:batch` returns correct statuses
- ✅ `matchedRule` explanations are accurate and complete
- ✅ Performance acceptable for large path lists (>1000 paths)
- ✅ Precedence logic correctly applied
- ✅ Edge cases handled (non-existent paths, special characters)

**Critical Test Cases:**
1. **Basic Batch Request:**
   ```json
   POST /api/workspaces/1/effective-permissions:batch
   {
     "paths": ["/materials/docs", "/projects/code", "/private/data"]
   }
   ```
   Expected Response:
   ```json
   {
     "results": [
       {
         "path": "/materials/docs",
         "status": "read",
         "matchedRule": {
           "id": "rule-123",
           "path": "materials",
           "rule_type": "allow",
           "permission_type": "read",
           "description": "Allow read access to materials"
         }
       },
       {
         "path": "/projects/code",
         "status": "write",
         "matchedRule": {
           "id": "rule-124",
           "path": "projects",
           "rule_type": "allow",
           "permission_type": "write",
           "description": "Allow write access to projects"
         }
       },
       {
         "path": "/private/data",
         "status": "denied",
         "matchedRule": null
       }
     ]
   }
   ```

2. **Performance Test:**
   ```json
   POST /api/workspaces/1/effective-permissions:batch
   {
     "paths": [/* 1000 different paths */]
   }
   ```
   Expected: Response time < 500ms

#### 5. Permission Service Refactor (`test_permission_service_refactor.py`)
**Purpose:** Validate database-backed permission resolution

```bash
pytest backend/tests/phase3a/test_permission_service_refactor.py -v
```

**Expected Outcomes:**
- ✅ Permission resolution works with database source
- ✅ Trie caching performance maintained
- ✅ Precedence logic unchanged from Phase 2
- ✅ Audit events emitted for each decision
- ✅ Cache invalidation on workspace activation

#### 6. Migration Script (`test_migration_script.py`)
**Purpose:** Validate config.json to database migration

```bash
pytest backend/tests/phase3a/test_migration_script.py -v
```

**Expected Outcomes:**
- ✅ Migration script runs successfully
- ✅ All config rules migrated to database
- ✅ Idempotency: running twice has no side effects
- ✅ Data integrity preserved (no rule loss)
- ✅ Rollback capabilities functional

**Critical Test Cases:**
1. **Basic Migration:**
   - Start: `config/permissions.json` with 5 rules
   - Run: Migration script
   - Result: Database workspace with 5 permission rules

2. **Idempotency Test:**
   - Run migration script twice
   - Result: Only one workspace, no duplicate rules

#### 7. Audit Logging (`test_audit_logging.py`)
**Purpose:** Validate structured audit events

```bash
pytest backend/tests/phase3a/test_audit_logging.py -v
```

**Expected Outcomes:**
- ✅ Audit events contain required fields
- ✅ Events logged for all permission decisions
- ✅ Performance impact minimal (<10% overhead)
- ✅ Audit log querying works correctly

#### 8. Integration Tests (`test_integration_phase3a.py`)
**Purpose:** End-to-end workflow validation

```bash
pytest backend/tests/phase3a/test_integration_phase3a.py -v
```

**Expected Outcomes:**
- ✅ Complete workspace creation → permission setup → activation workflow
- ✅ Permission resolution through MCP tools
- ✅ Migration from Phase 2 to Phase 3 configuration
- ✅ Performance benchmarks met

---

## Expected Test Results

### Success Criteria
When all tests pass, you should see output similar to:

```
backend/tests/phase3a/test_database_models.py::test_workspace_creation ✅ PASSED
backend/tests/phase3a/test_database_models.py::test_workspace_unique_name ✅ PASSED
backend/tests/phase3a/test_database_models.py::test_permission_creation ✅ PASSED
backend/tests/phase3a/test_database_models.py::test_permission_unique_constraint ✅ PASSED
backend/tests/phase3a/test_database_models.py::test_cascade_delete ✅ PASSED

backend/tests/phase3a/test_workspace_api.py::test_create_workspace ✅ PASSED
backend/tests/phase3a/test_workspace_api.py::test_list_workspaces ✅ PASSED
backend/tests/phase3a/test_workspace_api.py::test_activate_workspace ✅ PASSED
backend/tests/phase3a/test_workspace_api.py::test_duplicate_name_rejection ✅ PASSED

backend/tests/phase3a/test_batch_effective_permissions.py::test_batch_permissions ✅ PASSED
backend/tests/phase3a/test_batch_effective_permissions.py::test_matched_rule_explanation ✅ PASSED
backend/tests/phase3a/test_batch_effective_permissions.py::test_performance_large_batch ✅ PASSED

backend/tests/phase3a/test_migration_script.py::test_config_to_db_migration ✅ PASSED
backend/tests/phase3a/test_migration_script.py::test_migration_idempotency ✅ PASSED

backend/tests/phase3a/test_integration_phase3a.py::test_end_to_end_workflow ✅ PASSED

======================== XX passed in YY.XXs ========================
```

### Performance Benchmarks
- **Batch Effective Permissions:** < 500ms for 1000 paths
- **Permission Resolution:** < 5ms per decision (with caching)
- **Audit Logging Overhead:** < 10% performance impact
- **Database Operations:** CRUD operations < 50ms each

---

## Common Issues and Troubleshooting

### Database Connection Issues
```
Error: (sqlite3.OperationalError) unable to open database file
```
**Solution:** Ensure `./data/` directory exists and has write permissions

### Feature Flag Issues
```
AssertionError: Expected database permissions to be enabled
```
**Solution:** Verify `ENABLE_DATABASE_PERMISSIONS=true` in test environment

### Migration Script Issues
```
Error: permissions.json not found
```
**Solution:** Ensure test config file exists in `backend/tests/phase3a/test_data/`

---

## Independent Tester Validation Checklist

### Pre-Testing Setup ☐
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Test database directory created (`mkdir -p ./data`)
- [ ] Feature flags configured for Phase 3A
- [ ] No conflicting Phase 2 processes running

### Core Functionality Testing ☐
- [ ] All database model tests pass
- [ ] All workspace API tests pass
- [ ] All permission API tests pass
- [ ] Batch effective permissions API works correctly
- [ ] Permission service refactor maintains functionality
- [ ] Migration script completes successfully
- [ ] Audit logging captures all events

### Performance Testing ☐
- [ ] Batch API handles 1000+ paths in < 500ms
- [ ] Permission resolution maintains < 5ms response time
- [ ] Database operations complete in < 50ms
- [ ] Audit logging adds < 10% overhead

### Integration Testing ☐
- [ ] End-to-end workspace workflow functions
- [ ] MCP tools work with database permissions
- [ ] Migration preserves all existing rules
- [ ] Cache invalidation works on workspace changes

### Documentation Validation ☐
- [ ] All test commands execute successfully
- [ ] Expected outcomes match actual results
- [ ] Error cases produce expected failures
- [ ] Performance benchmarks are met

---

## Post-Testing Cleanup

```bash
# Clean up test databases
rm -f ./data/test_database.db

# Reset feature flags to Phase 2
export ENABLE_DATABASE_PERMISSIONS=false
export ENABLE_CONFIG_FILE_PERMISSIONS=true

# Optional: Generate test coverage report
pytest backend/tests/phase3a/ --cov=app --cov-report=html
# View at: htmlcov/index.html
```

---

## Test Success Metrics

**Phase 3A is ready for production when:**
- [ ] **100% Test Pass Rate** - All tests pass without failures
- [ ] **Performance Benchmarks Met** - All timing requirements satisfied
- [ ] **Migration Validation** - Config to database migration preserves all data
- [ ] **API Contract Compliance** - All endpoints match specification in Appendix E
- [ ] **Audit Completeness** - All permission decisions generate audit events
- [ ] **Integration Stability** - End-to-end workflows execute without errors

---

**Document Prepared For:** Independent Testing Validation
**Next Phase:** Phase 3B - Advanced UI & Full Workspace Experience
**Contact:** Development Team for clarifications or issues
