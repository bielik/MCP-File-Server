"""
Test fixtures and utilities for Phase 3A database migration tests.

This module provides common fixtures, database setup/teardown, and utility
functions used across all Phase 3A test files.
"""

import os
import json
import pytest
import tempfile
import shutil
from typing import Dict, List, Any, Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Import the models and database setup
from app.database import Base, get_db
from app.main import app

# Set up Phase 3A environment for tests
os.environ["ENABLE_DATABASE_PERMISSIONS"] = "true"
os.environ["ENABLE_CONFIG_FILE_PERMISSIONS"] = "false"

# Patch feature flags
@pytest.fixture(scope="function", autouse=True)
def patch_feature_flags():
    """Automatically patch feature flags for all tests."""
    from app.config import get_feature_flags
    feature_flags = get_feature_flags()
    # Directly set the flags since env variables might not be read yet
    original_db = feature_flags.ENABLE_DATABASE_PERMISSIONS
    original_config = feature_flags.ENABLE_CONFIG_FILE_PERMISSIONS

    feature_flags.ENABLE_DATABASE_PERMISSIONS = True
    feature_flags.ENABLE_CONFIG_FILE_PERMISSIONS = False

    yield

    # Restore original values
    feature_flags.ENABLE_DATABASE_PERMISSIONS = original_db
    feature_flags.ENABLE_CONFIG_FILE_PERMISSIONS = original_config


class DatabaseTestHelper:
    """Test database manager for Phase 3A tests."""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.test_db_path = None

    def setup(self):
        """Set up test database."""
        # Create temporary database file
        fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Create engine and session
        database_url = f"sqlite:///{self.test_db_path}"
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False}
        )

        # Enable foreign key constraints for SQLite
        @event.listens_for(self.engine, "connect")
        def enable_sqlite_fks(dbapi_connection, connection_record):
            """Enable foreign key constraints for SQLite connections."""
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create all tables
        Base.metadata.create_all(bind=self.engine)

    def teardown(self):
        """Clean up test database."""
        if self.engine:
            self.engine.dispose()

        # Wait for file handles to be released on Windows
        import time
        time.sleep(0.1)

        if self.test_db_path and os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except PermissionError:
                # Wait and retry on Windows
                time.sleep(0.5)
                try:
                    os.unlink(self.test_db_path)
                except PermissionError:
                    print(f"Warning: Could not delete temporary file {self.test_db_path}")

    def get_session(self):
        """Get database session."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()


@pytest.fixture(scope="function")
def test_db() -> Generator[DatabaseTestHelper, None, None]:
    """Provide a fresh test database for each test function."""
    db = DatabaseTestHelper()
    db.setup()
    yield db
    db.teardown()


@pytest.fixture(scope="function")
def db_session(test_db: DatabaseTestHelper):
    """Provide a database session for testing."""
    return next(test_db.get_session())


@pytest.fixture(scope="function")
def client(test_db: DatabaseTestHelper) -> TestClient:
    """Provide a test client with database override."""
    def override_get_db():
        return next(test_db.get_session())

    app.dependency_overrides[get_db] = override_get_db

    # Reset and initialize database permission service with test session factory
    from app.services.database_permission_service import reset_database_permission_service, get_database_permission_service
    reset_database_permission_service()

    # Create a session factory that returns the same session type as the test override
    def test_session_factory():
        return next(test_db.get_session())

    # Initialize the service with the test session factory
    get_database_permission_service(session_factory=test_session_factory)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_database_permission_service()


@pytest.fixture
def sample_workspace_data() -> Dict[str, Any]:
    """Sample workspace data for testing."""
    return {
        "name": "Test Workspace",
        "description": "A workspace for testing Phase 3A functionality",
        "is_active": False
    }


@pytest.fixture
def sample_workspaces_data() -> List[Dict[str, Any]]:
    """Multiple sample workspaces for testing."""
    return [
        {
            "name": "Development Workspace",
            "description": "Workspace for development tasks",
            "is_active": True
        },
        {
            "name": "Testing Workspace",
            "description": "Workspace for testing tasks",
            "is_active": False
        },
        {
            "name": "Production Workspace",
            "description": "Workspace for production monitoring",
            "is_active": False
        }
    ]


@pytest.fixture
def sample_permission_data() -> Dict[str, Any]:
    """Sample permission data for testing."""
    return {
        "path": "projects/test",
        "permission_type": "read",
        "rule_type": "allow",
        "description": "Test read access to projects"
    }


@pytest.fixture
def sample_permissions_data() -> List[Dict[str, Any]]:
    """Multiple sample permissions for testing."""
    return [
        {
            "path": "materials",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Allow read access to materials directory"
        },
        {
            "path": "projects",
            "permission_type": "write",
            "rule_type": "allow",
            "description": "Allow write access to projects directory"
        },
        {
            "path": "materials/confidential",
            "permission_type": "read",
            "rule_type": "deny",
            "description": "Block access to confidential materials"
        },
        {
            "path": "private",
            "permission_type": "read",
            "rule_type": "deny",
            "description": "Block access to private directory"
        }
    ]


@pytest.fixture
def batch_paths_test_data() -> List[str]:
    """Test paths for batch effective permissions testing."""
    return [
        "/materials/docs/readme.txt",
        "/materials/confidential/secrets.txt",
        "/projects/app/main.py",
        "/projects/tests/test_main.py",
        "/private/personal.txt",
        "/nonexistent/path.txt"
    ]


@pytest.fixture
def large_batch_paths() -> List[str]:
    """Large set of paths for performance testing."""
    paths = []
    base_paths = [
        "materials", "projects", "private", "public",
        "docs", "code", "tests", "config"
    ]

    # Generate 1000 unique paths
    for base in base_paths:
        for i in range(125):  # 8 * 125 = 1000
            paths.append(f"/{base}/subdir{i}/file{i}.txt")

    return paths


@pytest.fixture
def migration_config_data() -> Dict[str, Any]:
    """Sample config data for migration testing."""
    return {
        "rules": [
            {
                "id": "rule-1",
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Allow read access to materials"
            },
            {
                "id": "rule-2",
                "path": "projects",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Allow write access to projects"
            },
            {
                "id": "rule-3",
                "path": "data",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Allow read access to data directory"
            },
            {
                "id": "rule-4",
                "path": "materials/01_Introduction to Software Engineering",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Block introduction software engineering materials"
            }
        ],
        "description": "Test configuration for migration",
        "version": "1.1"
    }


@pytest.fixture
def temp_config_file(migration_config_data: Dict[str, Any]) -> Generator[str, None, None]:
    """Create temporary config file for migration testing."""
    # Create temporary config directory
    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(temp_dir, "permissions.json")

    # Write config data
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(migration_config_data, f, indent=2)

    yield config_path

    # Cleanup
    shutil.rmtree(temp_dir)


class MockAuditLogger:
    """Mock audit logger for testing."""

    def __init__(self):
        self.events = []

    def log_permission_decision(self, path: str, operation: str,
                               result: bool, matched_rule: Dict[str, Any] = None):
        """Log a permission decision event."""
        event = {
            "timestamp": "2025-01-14T12:00:00Z",
            "path": path,
            "operation": operation,
            "result": result,
            "matched_rule": matched_rule
        }
        self.events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all logged events."""
        return self.events.copy()

    def clear(self):
        """Clear all events."""
        self.events.clear()


@pytest.fixture
def mock_audit_logger() -> MockAuditLogger:
    """Provide mock audit logger for testing."""
    return MockAuditLogger()


class PerformanceTimer:
    """Utility for timing operations in tests."""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        import time
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        self.end_time = time.time()

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


@pytest.fixture
def performance_timer() -> PerformanceTimer:
    """Provide performance timer for testing."""
    return PerformanceTimer()


# Utility functions for test validation

def validate_workspace_response(response_data: Dict[str, Any]) -> bool:
    """Validate workspace response structure."""
    required_fields = ["id", "name", "description", "is_active", "created_at", "updated_at"]
    return all(field in response_data for field in required_fields)


def validate_permission_response(response_data: Dict[str, Any]) -> bool:
    """Validate permission response structure."""
    required_fields = [
        "id", "workspace_id", "path", "permission_type",
        "rule_type", "description", "created_at", "updated_at"
    ]
    return all(field in response_data for field in required_fields)


def validate_batch_response(response_data: Dict[str, Any]) -> bool:
    """Validate batch effective permissions response structure."""
    if "results" not in response_data:
        return False

    for result in response_data["results"]:
        required_fields = ["path", "status"]
        if not all(field in result for field in required_fields):
            return False

        # If access is granted, matched_rule should be present
        if result["status"] in ["read", "write"] and "matched_rule" not in result:
            return False

    return True


def validate_matched_rule(matched_rule: Dict[str, Any]) -> bool:
    """Validate matched rule structure in batch response."""
    if not matched_rule:
        return True  # Can be null for denied access

    required_fields = ["id", "path", "rule_type", "permission_type", "description"]
    return all(field in matched_rule for field in required_fields)


# Test data creation utilities

def create_test_workspace(db_session, workspace_data: Dict[str, Any]):
    """Create a test workspace in the database."""
    # Import here to avoid circular imports
    from app.models.workspace import Workspace

    workspace = Workspace(**workspace_data)
    db_session.add(workspace)
    db_session.commit()
    db_session.refresh(workspace)
    return workspace


def create_test_permission(db_session, workspace_id: int, permission_data: Dict[str, Any]):
    """Create a test permission in the database."""
    # Import here to avoid circular imports
    from app.models.workspace import Permission

    permission_data["workspace_id"] = workspace_id
    permission = Permission(**permission_data)
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission


# Constants for testing

PERFORMANCE_THRESHOLDS = {
    "batch_api_1000_paths_ms": 500,
    "permission_resolution_ms": 5,
    "database_crud_ms": 50,
    "audit_overhead_percent": 10
}

API_ENDPOINTS = {
    "workspaces": "/api/workspaces",
    "workspace_detail": "/api/workspaces/{id}",
    "workspace_activate": "/api/workspaces/{id}/activate",
    "workspace_permissions": "/api/workspaces/{id}/permissions",
    "permission_detail": "/api/permissions/{id}",
    "batch_effective_permissions": "/api/workspaces/{id}/effective-permissions:batch"
}