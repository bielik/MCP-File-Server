"""
Phase 3B Test Helper Functions

This module provides utility functions and classes specifically designed for
Phase 3B testing scenarios. These helpers enable comprehensive testing of
workspace management, permission systems, and UI integration.

Usage for Independent Testers:
- Import helpers in test files: `from .test_helpers import *`
- Use WorkspaceTestScenario for complex test setups
- Use PermissionTestGenerator for systematic permission testing
- Use UIIntegrationMocks for frontend simulation
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.workspace import Workspace, Permission
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate, PermissionCreate, PermissionUpdate,
    BatchEffectivePermissionsRequest
)


class WorkspaceTestScenario:
    """
    Helper class for creating complex workspace test scenarios.

    This class provides methods to create realistic workspace configurations
    with multiple permissions, user contexts, and edge cases for comprehensive testing.
    """

    def __init__(self, client: TestClient, db_session: Session):
        self.client = client
        self.db = db_session
        self.created_workspaces = []
        self.created_permissions = []

    def create_multi_workspace_scenario(self) -> Dict[str, Any]:
        """
        Create a scenario with multiple workspaces and complex permissions.

        Returns:
            Dict containing workspace IDs, permission mappings, and test paths
        """
        scenarios = {
            "development": {
                "name": "Development Workspace",
                "description": "Workspace for active development",
                "is_active": True,
                "permissions": [
                    {"path": "projects", "permission_type": "write", "rule_type": "allow"},
                    {"path": "materials", "permission_type": "read", "rule_type": "allow"},
                    {"path": "private", "permission_type": "read", "rule_type": "deny"},
                ]
            },
            "research": {
                "name": "Research Workspace",
                "description": "Workspace for research and analysis",
                "is_active": False,
                "permissions": [
                    {"path": "materials", "permission_type": "read", "rule_type": "allow"},
                    {"path": "research-data", "permission_type": "write", "rule_type": "allow"},
                    {"path": "projects", "permission_type": "read", "rule_type": "deny"},
                ]
            },
            "presentation": {
                "name": "Presentation Workspace",
                "description": "Read-only workspace for presentations",
                "is_active": False,
                "permissions": [
                    {"path": "materials/presentations", "permission_type": "read", "rule_type": "allow"},
                    {"path": "output", "permission_type": "write", "rule_type": "allow"},
                ]
            }
        }

        created_scenarios = {}

        for scenario_name, config in scenarios.items():
            # Create workspace
            workspace_data = {
                "name": config["name"],
                "description": config["description"],
                "is_active": config["is_active"]
            }

            response = self.client.post("/api/workspaces", json=workspace_data)
            assert response.status_code == 201
            workspace = response.json()
            self.created_workspaces.append(workspace["id"])

            # Create permissions
            permissions = []
            for perm_config in config["permissions"]:
                perm_response = self.client.post(
                    f"/api/workspaces/{workspace['id']}/permissions",
                    json={
                        **perm_config,
                        "description": f"{perm_config['rule_type'].title()} {perm_config['permission_type']} access to {perm_config['path']}"
                    }
                )
                assert perm_response.status_code == 201
                permission = perm_response.json()
                permissions.append(permission)
                self.created_permissions.append(permission["id"])

            created_scenarios[scenario_name] = {
                "workspace": workspace,
                "permissions": permissions
            }

        return created_scenarios

    def create_permission_precedence_scenario(self, workspace_id: int) -> Dict[str, List[Dict]]:
        """
        Create a complex permission scenario to test precedence rules.

        Tests:
        - Specificity (child overrides parent)
        - Deny wins over allow at same level
        - Write implies read
        - Default deny behavior
        """
        permission_sets = {
            "parent_child_specificity": [
                {"path": "materials", "permission_type": "read", "rule_type": "allow"},
                {"path": "materials/sensitive", "permission_type": "read", "rule_type": "deny"},
                {"path": "materials/sensitive/public", "permission_type": "read", "rule_type": "allow"},
            ],
            "deny_wins_scenario": [
                {"path": "projects/shared", "permission_type": "read", "rule_type": "allow"},
                {"path": "projects/shared", "permission_type": "read", "rule_type": "deny"},  # Should win
            ],
            "write_implies_read": [
                {"path": "output", "permission_type": "write", "rule_type": "allow"},
                # No explicit read rule - should be implied
            ],
            "mixed_permissions": [
                {"path": "workspace", "permission_type": "read", "rule_type": "allow"},
                {"path": "workspace/readonly", "permission_type": "write", "rule_type": "deny"},
                {"path": "workspace/readwrite", "permission_type": "write", "rule_type": "allow"},
            ]
        }

        created_permissions = {}

        for scenario_name, permissions in permission_sets.items():
            created_perms = []
            for perm_config in permissions:
                response = self.client.post(
                    f"/api/workspaces/{workspace_id}/permissions",
                    json={
                        **perm_config,
                        "description": f"Precedence test: {scenario_name}"
                    }
                )
                assert response.status_code == 201
                created_perms.append(response.json())
                self.created_permissions.append(response.json()["id"])

            created_permissions[scenario_name] = created_perms

        return created_permissions

    def cleanup(self):
        """Clean up all created test data."""
        # Delete permissions first (foreign key constraints)
        for perm_id in self.created_permissions:
            try:
                # Find workspace_id for permission (you might need to adjust this)
                for ws_id in self.created_workspaces:
                    response = self.client.delete(f"/api/workspaces/{ws_id}/permissions/{perm_id}")
                    if response.status_code == 200:
                        break
            except Exception:
                continue  # Permission might already be deleted

        # Delete workspaces
        for workspace_id in self.created_workspaces:
            try:
                self.client.delete(f"/api/workspaces/{workspace_id}")
            except Exception:
                continue  # Workspace might already be deleted

        self.created_workspaces = []
        self.created_permissions = []


class PermissionTestGenerator:
    """
    Generates systematic test cases for permission validation.

    This class creates comprehensive test matrices for permission scenarios,
    ensuring all edge cases and combinations are covered.
    """

    @staticmethod
    def generate_path_test_matrix() -> List[Dict[str, Any]]:
        """
        Generate a comprehensive matrix of path test cases.

        Returns:
            List of test cases with expected results
        """
        base_paths = [
            "materials",
            "projects",
            "private",
            "output",
            "temp"
        ]

        nested_paths = [
            "materials/course1",
            "materials/course1/lesson1",
            "projects/app/src",
            "projects/app/tests",
            "private/user/config",
            "output/reports",
        ]

        edge_case_paths = [
            "",  # Root path
            "/",  # Root with slash
            ".",  # Current directory
            "..",  # Parent directory (should be blocked)
            "materials/../private",  # Traversal attempt
            "path with spaces",  # Spaces in path
            "path/with/unicode/文件",  # Unicode characters
            "very/deeply/nested/path/that/goes/many/levels/deep/file.txt",  # Deep nesting
        ]

        permission_types = ["read", "write"]
        rule_types = ["allow", "deny"]

        test_matrix = []

        # Generate base path tests
        for path in base_paths:
            for perm_type in permission_types:
                for rule_type in rule_types:
                    test_matrix.append({
                        "path": path,
                        "permission_type": perm_type,
                        "rule_type": rule_type,
                        "category": "base_paths",
                        "expected_valid": True
                    })

        # Generate nested path tests
        for path in nested_paths:
            for perm_type in permission_types:
                for rule_type in rule_types:
                    test_matrix.append({
                        "path": path,
                        "permission_type": perm_type,
                        "rule_type": rule_type,
                        "category": "nested_paths",
                        "expected_valid": True
                    })

        # Generate edge case tests
        for path in edge_case_paths:
            test_matrix.append({
                "path": path,
                "permission_type": "read",
                "rule_type": "allow",
                "category": "edge_cases",
                "expected_valid": path not in ["..", "materials/../private"]  # These should fail validation
            })

        return test_matrix

    @staticmethod
    def generate_batch_api_test_cases() -> List[Dict[str, Any]]:
        """
        Generate test cases specifically for batch permission API testing.

        Returns:
            List of batch test scenarios
        """
        return [
            {
                "name": "small_batch",
                "description": "Small batch of 10 paths",
                "paths": [f"test/path/{i}" for i in range(10)],
                "expected_response_time_ms": 50
            },
            {
                "name": "medium_batch",
                "description": "Medium batch of 50 paths",
                "paths": [f"materials/course_{i}/lesson_{j}" for i in range(10) for j in range(5)],
                "expected_response_time_ms": 75
            },
            {
                "name": "large_batch",
                "description": "Large batch of 150 paths",
                "paths": [f"projects/app_{i}/src/module_{j}/file_{k}.py"
                         for i in range(5) for j in range(10) for k in range(3)],
                "expected_response_time_ms": 100
            },
            {
                "name": "mixed_paths",
                "description": "Mixed paths from different directories",
                "paths": [
                    "materials/README.md",
                    "projects/app/main.py",
                    "private/config.json",
                    "output/report.pdf",
                    "temp/cache.dat"
                ] * 30,  # Repeat to create 150 paths
                "expected_response_time_ms": 100
            },
            {
                "name": "duplicate_paths",
                "description": "Batch with duplicate paths for caching test",
                "paths": ["materials/common/file.txt"] * 100,
                "expected_response_time_ms": 25  # Should be very fast due to caching
            }
        ]


class UIIntegrationMocks:
    """
    Mock objects and utilities for testing UI integration scenarios.

    This class provides realistic mock responses and behaviors for testing
    frontend-backend communication patterns.
    """

    def __init__(self):
        self.mock_websocket = Mock()
        self.mock_responses = {}
        self.call_history = []

    def setup_websocket_mocks(self):
        """Set up WebSocket mocks for real-time update testing."""
        self.mock_websocket.connect = AsyncMock()
        self.mock_websocket.disconnect = AsyncMock()
        self.mock_websocket.send_personal_message = AsyncMock()
        self.mock_websocket.broadcast = AsyncMock()

        # Track calls for verification
        async def track_broadcast(message):
            self.call_history.append(("broadcast", message, time.time()))

        async def track_personal_message(message, websocket):
            self.call_history.append(("personal_message", message, websocket, time.time()))

        self.mock_websocket.broadcast.side_effect = track_broadcast
        self.mock_websocket.send_personal_message.side_effect = track_personal_message

        return self.mock_websocket

    def create_ui_state_mock(self, initial_state: Dict[str, Any] = None) -> Mock:
        """Create a mock UI state object for testing state management."""
        default_state = {
            "activeWorkspace": None,
            "workspaces": [],
            "permissions": [],
            "selectedPaths": [],
            "permissionStatuses": {},
            "isLoading": False,
            "error": None
        }

        if initial_state:
            default_state.update(initial_state)

        mock_state = Mock()
        for key, value in default_state.items():
            setattr(mock_state, key, value)

        return mock_state

    def simulate_workspace_switch(self, from_workspace_id: int, to_workspace_id: int) -> List[Dict[str, Any]]:
        """Simulate the sequence of events that occur during workspace switching."""
        events = [
            {
                "type": "workspace_deactivation_start",
                "workspace_id": from_workspace_id,
                "timestamp": time.time()
            },
            {
                "type": "permission_cache_clear",
                "timestamp": time.time() + 0.01
            },
            {
                "type": "workspace_activation_start",
                "workspace_id": to_workspace_id,
                "timestamp": time.time() + 0.02
            },
            {
                "type": "permission_cache_rebuild",
                "workspace_id": to_workspace_id,
                "timestamp": time.time() + 0.05
            },
            {
                "type": "ui_refresh_triggered",
                "workspace_id": to_workspace_id,
                "timestamp": time.time() + 0.1
            },
            {
                "type": "workspace_switch_complete",
                "workspace_id": to_workspace_id,
                "timestamp": time.time() + 0.15
            }
        ]

        return events

    def get_call_history(self, call_type: str = None) -> List[Tuple]:
        """Get history of mock calls, optionally filtered by type."""
        if call_type:
            return [call for call in self.call_history if call[0] == call_type]
        return self.call_history

    def reset_mocks(self):
        """Reset all mocks and call history."""
        self.call_history = []
        self.mock_responses = {}
        if hasattr(self.mock_websocket, 'reset_mock'):
            self.mock_websocket.reset_mock()


class PerformanceBenchmark:
    """
    Utility class for performance testing and benchmarking.

    Provides methods to measure and validate performance characteristics
    of various system operations.
    """

    def __init__(self, thresholds: Dict[str, int]):
        self.thresholds = thresholds
        self.results = {}

    async def benchmark_batch_api(self, client: TestClient, workspace_id: int, paths: List[str]) -> Dict[str, float]:
        """Benchmark the batch permission API performance."""
        start_time = time.time()

        response = client.post(
            f"/api/workspaces/{workspace_id}/effective-permissions:batch",
            json={"paths": paths}
        )

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        assert response.status_code == 200, f"Batch API failed: {response.text}"

        result = {
            "duration_ms": duration_ms,
            "paths_count": len(paths),
            "paths_per_second": len(paths) / (duration_ms / 1000),
            "response_size_bytes": len(response.content),
            "within_threshold": duration_ms <= self.thresholds.get("batch_api_max_latency_ms", 100)
        }

        self.results[f"batch_api_{len(paths)}_paths"] = result
        return result

    def benchmark_workspace_switch(self, client: TestClient, from_workspace_id: int, to_workspace_id: int) -> Dict[str, float]:
        """Benchmark workspace switching performance."""
        start_time = time.time()

        # Deactivate current workspace
        if from_workspace_id:
            response1 = client.put(f"/api/workspaces/{from_workspace_id}/deactivate")
            assert response1.status_code == 200

        # Activate new workspace
        response2 = client.put(f"/api/workspaces/{to_workspace_id}/activate")
        assert response2.status_code == 200

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        result = {
            "duration_ms": duration_ms,
            "within_threshold": duration_ms <= self.thresholds.get("workspace_switch_max_latency_ms", 200)
        }

        self.results[f"workspace_switch_{from_workspace_id}_to_{to_workspace_id}"] = result
        return result

    def record_metric(self, metric_name: str, value: float, unit: str = "ms") -> None:
        """
        Record a performance metric.

        Args:
            metric_name: Name of the metric
            value: Measured value
            unit: Unit of measurement (default: ms)
        """
        threshold = self.thresholds.get(f"{metric_name}_max_latency_{unit}", float('inf'))

        self.results[metric_name] = {
            "value": value,
            "unit": unit,
            "threshold": threshold,
            "within_threshold": value <= threshold,
            "timestamp": time.time()
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        passed_tests = sum(1 for result in self.results.values() if result.get("within_threshold", False))
        total_tests = len(self.results)

        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "thresholds": self.thresholds,
            "detailed_results": self.results
        }


# Utility Functions
def create_realistic_file_tree() -> List[str]:
    """Create a realistic file tree structure for testing."""
    return [
        # Materials structure
        "materials/README.md",
        "materials/course-overview.pdf",
        "materials/01_introduction/slides.pptx",
        "materials/01_introduction/exercises.pdf",
        "materials/02_basics/theory.md",
        "materials/02_basics/examples.py",
        "materials/03_advanced/concepts.md",
        "materials/03_advanced/demo.ipynb",
        "materials/sensitive/admin-notes.txt",
        "materials/sensitive/grades.xlsx",

        # Projects structure
        "projects/README.md",
        "projects/webapp/src/main.py",
        "projects/webapp/src/models.py",
        "projects/webapp/src/views.py",
        "projects/webapp/tests/test_main.py",
        "projects/webapp/tests/test_models.py",
        "projects/mobile-app/src/App.tsx",
        "projects/mobile-app/src/components/Header.tsx",
        "projects/mobile-app/tests/App.test.tsx",
        "projects/data-analysis/notebooks/exploration.ipynb",
        "projects/data-analysis/scripts/preprocess.py",
        "projects/data-analysis/results/summary.csv",

        # Private structure
        "private/config/api-keys.json",
        "private/config/database.env",
        "private/personal/notes.md",
        "private/personal/todo.txt",

        # Output structure
        "output/reports/weekly-summary.pdf",
        "output/reports/performance-metrics.json",
        "output/logs/application.log",
        "output/logs/error.log",

        # Temporary structure
        "temp/cache/session-data.json",
        "temp/uploads/document.pdf",
        "temp/processed/data.csv"
    ]


def generate_permission_explanation(path: str, permission_type: str, rule_type: str, matched_rule: Dict[str, Any]) -> str:
    """Generate human-readable permission explanation for UI testing."""
    action = "granted" if rule_type == "allow" else "denied"
    rule_path = matched_rule.get("path", "unknown")
    rule_description = matched_rule.get("description", "No description")

    return f"""
Permission {action} for {permission_type} access to '{path}'.

Matched Rule:
- Path: {rule_path}
- Type: {rule_type.title()} {permission_type}
- Description: {rule_description}
- Rule ID: {matched_rule.get('id', 'unknown')}

This rule was selected based on the permission precedence system:
1. Most specific path match
2. Deny rules override allow rules at the same specificity
3. Write permission implies read permission
4. Default behavior is deny if no rules match
    """.strip()


async def wait_for_websocket_messages(mock_websocket, expected_count: int, timeout_seconds: int = 5) -> List[Any]:
    """Wait for expected number of WebSocket messages with timeout."""
    messages = []
    start_time = time.time()

    while len(messages) < expected_count and (time.time() - start_time) < timeout_seconds:
        # Check if new messages arrived
        if hasattr(mock_websocket, 'call_args_list'):
            new_messages = mock_websocket.call_args_list[len(messages):]
            messages.extend(new_messages)

        await asyncio.sleep(0.01)  # Small delay to prevent busy waiting

    return messages


# Context Managers
@asynccontextmanager
async def temporary_workspace(client: TestClient, workspace_data: Dict[str, Any] = None):
    """Async context manager for temporary workspace creation and cleanup."""
    if workspace_data is None:
        workspace_data = {
            "name": f"Temp Workspace {datetime.utcnow().isoformat()}",
            "description": "Temporary workspace for testing",
            "is_active": False
        }

    # Create workspace
    response = client.post("/api/workspaces", json=workspace_data)
    assert response.status_code == 201
    workspace = response.json()

    try:
        yield workspace
    finally:
        # Cleanup
        try:
            client.delete(f"/api/workspaces/{workspace['id']}")
        except Exception:
            pass  # Ignore cleanup errors