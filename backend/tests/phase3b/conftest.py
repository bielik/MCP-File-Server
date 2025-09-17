"""
Phase 3B Test Configuration and Fixtures

This module provides comprehensive test fixtures and configuration for Phase 3B
testing, including E2E workflows, performance benchmarks, and UI integration tests.

For independent testers:
- All fixtures are self-contained with proper cleanup
- Test data is generated programmatically for consistency
- Performance thresholds are clearly documented
- Mock scenarios cover edge cases and error conditions
"""

import pytest
import asyncio
import time
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

# Ensure database permissions are enabled for testing
os.environ["ENABLE_DATABASE_PERMISSIONS"] = "true"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app.models.workspace import Workspace, Permission
from app.schemas.workspace import (
    WorkspaceCreate, PermissionCreate, BatchEffectivePermissionsRequest
)


# Test Configuration Constants
TEST_DATABASE_URL = "sqlite:///./test_phase3b.db"
PERFORMANCE_THRESHOLDS = {
    "batch_api_max_latency_ms": 100,
    "workspace_switch_max_latency_ms": 200,
    "ui_update_max_latency_ms": 150,
    "concurrent_operations_max_latency_ms": 500
}

API_ENDPOINTS = {
    "workspaces": "/api/workspaces",
    "workspace_by_id": "/api/workspaces/{id}",
    "workspace_activate": "/api/workspaces/{id}/activate",
    "workspace_permissions": "/api/workspaces/{id}/permissions",
    "permission_by_id": "/api/workspaces/{workspace_id}/permissions/{permission_id}",
    "batch_permissions": "/api/workspaces/{id}/effective-permissions:batch"
}


class PerformanceTimer:
    """Context manager for measuring operation performance."""

    def __init__(self, name: str, threshold_ms: int = None):
        self.name = name
        self.threshold_ms = threshold_ms
        self.start_time = None
        self.end_time = None
        self.duration_ms = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        print(f"⏱️  {self.name}: {self.duration_ms:.2f}ms")

        if self.threshold_ms and self.duration_ms > self.threshold_ms:
            pytest.fail(f"Performance threshold exceeded for {self.name}: "
                       f"{self.duration_ms:.2f}ms > {self.threshold_ms}ms")

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.duration_ms is not None:
            return self.duration_ms
        elif self.start_time is not None:
            return (time.time() - self.start_time) * 1000
        else:
            return 0.0


class PerformanceBenchmark:
    """Helper class for performance benchmarking in tests."""

    def __init__(self, name: str = "Default Benchmark"):
        self.name = name
        self.results = {}

    def measure(self, name: str, threshold_ms: int = None):
        """Return a performance timer context manager."""
        return PerformanceTimer(name, threshold_ms)

    def get_results(self) -> Dict[str, float]:
        """Get all performance results."""
        return self.results.copy()


class DatabaseTestHelper:
    """Helper class for database operations in tests."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_test_workspace(self,
                            name: str = "Test Workspace",
                            description: str = "Test workspace for Phase 3B",
                            is_active: bool = False) -> Workspace:
        """Create a test workspace with optional parameters."""
        workspace = Workspace(
            name=name,
            description=description,
            is_active=is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by="test_user",
            updated_by="test_user",
            version=1
        )
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def create_test_permission(self,
                             workspace_id: int,
                             path: str = "test/path",
                             permission_type: str = "read",
                             rule_type: str = "allow",
                             description: str = "Test permission") -> Permission:
        """Create a test permission with optional parameters."""
        permission = Permission(
            workspace_id=workspace_id,
            path=path,
            permission_type=permission_type,
            rule_type=rule_type,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by="test_user",
            updated_by="test_user"
        )
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def create_complex_permission_scenario(self, workspace_id: int) -> List[Permission]:
        """Create a complex permission scenario for testing precedence rules."""
        permissions = [
            # Allow read access to materials
            self.create_test_permission(
                workspace_id, "materials", "read", "allow",
                "Allow read access to materials directory"
            ),
            # Allow write access to projects
            self.create_test_permission(
                workspace_id, "projects", "write", "allow",
                "Allow write access to projects directory"
            ),
            # Deny access to sensitive subdirectory
            self.create_test_permission(
                workspace_id, "materials/sensitive", "read", "deny",
                "Deny access to sensitive materials"
            ),
            # Allow access to specific file in denied directory (should be overridden)
            self.create_test_permission(
                workspace_id, "materials/sensitive/public.txt", "read", "allow",
                "Allow access to specific file (test precedence)"
            )
        ]
        return permissions

    def cleanup_workspace(self, workspace_id: int):
        """Clean up workspace and all associated permissions."""
        # Delete permissions first due to foreign key constraints
        self.db.query(Permission).filter(Permission.workspace_id == workspace_id).delete()
        self.db.query(Workspace).filter(Workspace.id == workspace_id).delete()
        self.db.commit()


# Database Fixtures
@pytest.fixture(scope="function")
def test_db_engine():
    """Create test database engine with in-memory SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",  # Use in-memory database for tests
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )
    # Make sure we create all tables with current schema
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def override_db_dependency(test_db_session):
    """Override the database dependency for testing."""
    def get_test_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = get_test_db

    # Reset database permission service to use test database
    from app.services.database_permission_service import reset_database_permission_service, get_database_permission_service
    reset_database_permission_service()

    # Mark the test session to avoid closing it
    test_db_session._is_test_session = True

    # Create test session factory that returns the SAME session instance
    def test_session_factory():
        # Always return the same test session instance
        return test_db_session

    # Initialize permission service with test session factory
    test_permission_service = get_database_permission_service(session_factory=test_session_factory)

    # Override the permission service getter to return our test instance
    import app.services.database_permission_service as db_perm_module
    original_getter = db_perm_module.get_database_permission_service
    db_perm_module.get_database_permission_service = lambda session_factory=None: test_permission_service

    # Also override the global instance to ensure consistency
    db_perm_module._database_service = test_permission_service

    yield
    app.dependency_overrides.clear()
    reset_database_permission_service()
    # Restore original permission service getter
    db_perm_module.get_database_permission_service = original_getter
    db_perm_module._database_service = None


@pytest.fixture(scope="function")
def client(override_db_dependency):
    """Create test client with database override."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db_helper(test_db_session):
    """Provide database helper instance."""
    return DatabaseTestHelper(test_db_session)


# Sample Data Fixtures
@pytest.fixture
def sample_workspace_data() -> Dict[str, Any]:
    """Sample workspace data for creation tests."""
    return {
        "name": "Sample Workspace",
        "description": "A sample workspace for testing Phase 3B functionality",
        "is_active": False
    }


@pytest.fixture
def sample_permission_data() -> Dict[str, Any]:
    """Sample permission data for creation tests."""
    return {
        "path": "test/sample/path",
        "permission_type": "read",
        "rule_type": "allow",
        "description": "Sample permission for testing"
    }


@pytest.fixture
def large_batch_paths() -> List[str]:
    """Generate large list of paths for batch API performance testing."""
    paths = []
    # Generate various path patterns
    for i in range(100):
        paths.extend([
            f"materials/course_{i:03d}/README.md",
            f"projects/project_{i:03d}/src/main.py",
            f"projects/project_{i:03d}/tests/test_main.py",
            f"private/user_{i:03d}/config.json"
        ])
    return paths[:150]  # Return exactly 150 paths


@pytest.fixture
def complex_workspace_scenario(client, db_helper):
    """Create a complex workspace scenario for E2E testing."""
    # First, deactivate any existing active workspaces to avoid conflicts
    db_helper.db.query(Workspace).update({"is_active": False}, synchronize_session=False)
    db_helper.db.commit()

    # Create workspace
    workspace = db_helper.create_test_workspace(
        name="Complex Test Workspace",
        description="Workspace with complex permission hierarchy",
        is_active=True
    )

    # Create complex permission scenario
    permissions = db_helper.create_complex_permission_scenario(workspace.id)

    # Invalidate permission service cache to pick up new workspace
    from app.services.database_permission_service import get_database_permission_service
    permission_service = get_database_permission_service()
    permission_service.invalidate_cache(workspace.id)

    yield {
        "workspace": workspace,
        "permissions": permissions
    }

    # Cleanup
    db_helper.cleanup_workspace(workspace.id)

    # Reset permission service cache after cleanup
    permission_service.invalidate_cache()


# Mock Fixtures for Frontend Testing
@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for testing real-time updates."""
    manager = Mock()
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.send_personal_message = AsyncMock()
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def mock_mcp_client_response():
    """Mock MCP client responses for integration testing."""
    def create_response(method: str, success: bool = True, data: Any = None):
        if success:
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "result": data or {"status": "success"}
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": data
                }
            }
    return create_response


# Performance Testing Utilities
@pytest.fixture
def performance_thresholds():
    """Return performance thresholds for validation."""
    return PERFORMANCE_THRESHOLDS


@pytest.fixture
def api_endpoints():
    """Return API endpoint templates."""
    return API_ENDPOINTS


# Validation Helper Functions
def validate_workspace_response(workspace_data: Dict[str, Any]) -> bool:
    """Validate workspace API response structure."""
    required_fields = ["id", "name", "description", "is_active", "created_at", "updated_at", "version"]
    return all(field in workspace_data for field in required_fields)


def validate_permission_response(permission_data: Dict[str, Any]) -> bool:
    """Validate permission API response structure."""
    required_fields = ["id", "workspace_id", "path", "permission_type", "rule_type", "created_at", "updated_at"]
    return all(field in permission_data for field in required_fields)


def validate_batch_permission_response(batch_response: Dict[str, Any]) -> bool:
    """Validate batch permission API response structure."""
    if "results" not in batch_response:
        return False

    for result in batch_response["results"]:
        required_fields = ["path", "status"]
        if not all(field in result for field in required_fields):
            return False

        # If permission is granted/denied, should have matchedRule
        if result["status"] in ["read", "write", "denied"] and "matchedRule" not in result:
            return False

    return True


def create_test_workspace_via_api(client: TestClient, workspace_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Helper function to create a test workspace via API."""
    if workspace_data is None:
        workspace_data = {
            "name": f"Test Workspace {datetime.utcnow().isoformat()}",
            "description": "Created by test helper function",
            "is_active": False
        }

    # Ensure unique names by adding timestamp for concurrent tests
    if "name" in workspace_data and not workspace_data["name"].endswith("]"):
        import time
        workspace_data["name"] = f"{workspace_data['name']} [{int(time.time() * 1000)}]"

    response = client.post("/api/workspaces", json=workspace_data)
    assert response.status_code == 201, f"Failed to create workspace: {response.text}"
    return response.json()


def create_test_workspace(db_session: Session, name: str, description: str = "Test workspace", is_active: bool = False) -> Workspace:
    """Helper function to create a test workspace directly in database."""
    # If creating an active workspace, deactivate others first to avoid conflicts
    if is_active:
        db_session.query(Workspace).update({"is_active": False}, synchronize_session=False)
        db_session.commit()

    # Ensure unique names for concurrent tests
    import time
    if not name.endswith("]"):
        name = f"{name} [{int(time.time() * 1000)}]"

    workspace = Workspace(
        name=name,
        description=description,
        is_active=is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by="test_user",
        updated_by="test_user",
        version=1
    )
    db_session.add(workspace)
    db_session.commit()
    db_session.refresh(workspace)
    return workspace


def create_test_permission_via_api(client: TestClient, workspace_id: int, permission_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Helper function to create a test permission via API."""
    if permission_data is None:
        permission_data = {
            "path": f"test/path/{datetime.utcnow().isoformat()}",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Created by test helper function"
        }

    response = client.post(f"/api/workspaces/{workspace_id}/permissions", json=permission_data)
    assert response.status_code == 201, f"Failed to create permission: {response.text}"
    return response.json()


def create_test_permission(db_session: Session, workspace_id: int, path: str, permission_type: str = "read", rule_type: str = "allow", description: str = "Test permission") -> Permission:
    """Helper function to create a test permission directly in database."""
    permission = Permission(
        workspace_id=workspace_id,
        path=path,
        permission_type=permission_type,
        rule_type=rule_type,
        description=description,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission


def clear_test_data(db_session: Session):
    """Clear all test data from database for clean test environment."""
    # Delete in order due to foreign key constraints
    db_session.query(Permission).delete()
    db_session.query(Workspace).delete()
    db_session.commit()


# Async Test Utilities
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def async_timer(name: str, threshold_ms: int = None):
    """Async context manager for performance timing."""
    return PerformanceTimer(name, threshold_ms)