"""
Test permission API endpoints for Phase 3A.

This test module validates all permission management endpoints within workspaces
including CRUD operations, duplicate rule rejection, and workspace-scoped isolation.
"""

import pytest
from typing import Dict, Any, List
from fastapi.testclient import TestClient

from .conftest import (
    DatabaseTestHelper, validate_permission_response, create_test_workspace,
    create_test_permission, API_ENDPOINTS, PERFORMANCE_THRESHOLDS,
    PerformanceTimer
)


class TestPermissionCreation:
    """Test permission creation endpoint."""

    def test_create_permission_success(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                     sample_permission_data: Dict[str, Any]):
        """Test successful permission creation."""
        # Create workspace first
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        # Create permission
        response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=sample_permission_data
        )

        assert response.status_code == 201

        permission_data = response.json()
        assert validate_permission_response(permission_data)
        assert permission_data["workspace_id"] == workspace["id"]
        assert permission_data["path"] == sample_permission_data["path"]
        assert permission_data["permission_type"] == sample_permission_data["permission_type"]
        assert permission_data["rule_type"] == sample_permission_data["rule_type"]
        assert permission_data["description"] == sample_permission_data["description"]
        assert "id" in permission_data
        assert "created_at" in permission_data
        assert "updated_at" in permission_data

    def test_create_permission_all_combinations(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test creating permissions with all valid combinations of permission_type and rule_type."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        # Test all valid combinations
        combinations = [
            ("read", "allow"),
            ("read", "deny"),
            ("write", "allow"),
            ("write", "deny")
        ]

        created_permissions = []
        for i, (permission_type, rule_type) in enumerate(combinations):
            permission_data = {
                "path": f"test/path/{i}",
                "permission_type": permission_type,
                "rule_type": rule_type,
                "description": f"Test {permission_type} {rule_type} permission"
            }

            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )

            assert response.status_code == 201
            created_permission = response.json()
            assert created_permission["permission_type"] == permission_type
            assert created_permission["rule_type"] == rule_type
            created_permissions.append(created_permission)

        # Verify all permissions were created
        assert len(created_permissions) == len(combinations)

    def test_create_permission_duplicate_rule_rejection(self, client: TestClient,
                                                       sample_workspace_data: Dict[str, Any],
                                                       sample_permission_data: Dict[str, Any]):
        """Test that duplicate permission rules are rejected."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        # Create first permission
        response1 = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=sample_permission_data
        )
        assert response1.status_code == 201

        # Attempt to create duplicate permission
        duplicate_data = sample_permission_data.copy()
        duplicate_data["description"] = "Duplicate permission with different description"

        response2 = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=duplicate_data
        )

        assert response2.status_code == 409
        error_data = response2.json()
        assert "code" in error_data
        assert "message" in error_data
        assert "duplicate" in error_data["message"].lower() or "already exists" in error_data["message"].lower()

    def test_create_permission_different_rule_types_allowed(self, client: TestClient,
                                                           sample_workspace_data: Dict[str, Any]):
        """Test that different rule_types for same path/permission_type are allowed."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        # Create allow rule
        allow_permission = {
            "path": "test/same/path",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Allow rule"
        }

        response1 = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=allow_permission
        )
        assert response1.status_code == 201

        # Create deny rule for same path/permission_type (should be allowed - different rule_type)
        deny_permission = {
            "path": "test/same/path",
            "permission_type": "read",
            "rule_type": "deny",  # Different rule_type
            "description": "Deny rule"
        }

        response2 = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=deny_permission
        )
        assert response2.status_code == 201

    def test_create_permission_workspace_not_found(self, client: TestClient,
                                                   sample_permission_data: Dict[str, Any]):
        """Test creating permission for non-existent workspace."""
        response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=99999),
            json=sample_permission_data
        )

        assert response.status_code == 404

    def test_create_permission_invalid_data(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test permission creation with invalid data."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        # Test missing required fields
        invalid_data_sets = [
            {
                # Missing path
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Missing path"
            },
            {
                "path": "test/path",
                # Missing permission_type
                "rule_type": "allow",
                "description": "Missing permission_type"
            },
            {
                "path": "test/path",
                "permission_type": "read",
                # Missing rule_type
                "description": "Missing rule_type"
            },
            {
                "path": "",  # Empty path
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Empty path"
            },
            {
                "path": "test/path",
                "permission_type": "invalid",  # Invalid permission_type
                "rule_type": "allow",
                "description": "Invalid permission_type"
            },
            {
                "path": "test/path",
                "permission_type": "read",
                "rule_type": "invalid",  # Invalid rule_type
                "description": "Invalid rule_type"
            }
        ]

        for invalid_data in invalid_data_sets:
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=invalid_data
            )
            assert response.status_code == 422

    def test_create_permission_performance(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                          performance_timer: PerformanceTimer):
        """Test permission creation performance."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        permission_data = {
            "path": "performance/test",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Performance test permission"
        }

        with performance_timer:
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )

        assert response.status_code == 201
        assert performance_timer.elapsed_ms < PERFORMANCE_THRESHOLDS["database_crud_ms"]


class TestPermissionRetrieval:
    """Test permission retrieval endpoints."""

    def test_list_workspace_permissions_empty(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test listing permissions for workspace with no permissions."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        # List permissions
        response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        )

        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, dict)
        assert "permissions" in response_data
        assert "total" in response_data
        assert "workspace_id" in response_data
        assert isinstance(response_data["permissions"], list)
        assert len(response_data["permissions"]) == 0
        assert response_data["total"] == 0
        assert response_data["workspace_id"] == workspace["id"]

    def test_list_workspace_permissions_multiple(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                                sample_permissions_data: List[Dict[str, Any]]):
        """Test listing multiple permissions for a workspace."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        # Create multiple permissions
        created_permissions = []
        for permission_data in sample_permissions_data:
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )
            assert response.status_code == 201
            created_permissions.append(response.json())

        # List all permissions
        response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        )

        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, dict)
        assert "permissions" in response_data
        assert "total" in response_data
        assert "workspace_id" in response_data

        permissions = response_data["permissions"]
        assert len(permissions) == len(sample_permissions_data)
        assert response_data["total"] == len(sample_permissions_data)
        assert response_data["workspace_id"] == workspace["id"]

        # Verify all permissions are returned and belong to the workspace
        permission_paths = [p["path"] for p in permissions]
        for permission_data in sample_permissions_data:
            assert permission_data["path"] in permission_paths

        for permission in permissions:
            assert permission["workspace_id"] == workspace["id"]

    def test_list_workspace_permissions_workspace_not_found(self, client: TestClient):
        """Test listing permissions for non-existent workspace."""
        response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=99999)
        )

        assert response.status_code == 404

    def test_get_permission_by_id(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                 sample_permission_data: Dict[str, Any]):
        """Test retrieving a specific permission by ID."""
        # Create workspace and permission
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        permission_response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=sample_permission_data
        )
        created_permission = permission_response.json()

        # Retrieve permission by ID
        response = client.get(
            API_ENDPOINTS["permission_detail"].format(id=created_permission["id"])
        )

        assert response.status_code == 200
        permission_data = response.json()
        assert validate_permission_response(permission_data)
        assert permission_data["id"] == created_permission["id"]
        assert permission_data["path"] == sample_permission_data["path"]

    def test_get_permission_not_found(self, client: TestClient):
        """Test retrieving non-existent permission."""
        response = client.get(API_ENDPOINTS["permission_detail"].format(id=99999))

        assert response.status_code == 404

    def test_workspace_permission_isolation(self, client: TestClient,
                                           sample_workspaces_data: List[Dict[str, Any]]):
        """Test that permissions are properly isolated between workspaces."""
        # Create two workspaces
        workspace1_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspaces_data[0]
        )
        workspace2_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspaces_data[1]
        )

        workspace1 = workspace1_response.json()
        workspace2 = workspace2_response.json()

        # Create permissions in each workspace
        permission1_data = {
            "path": "shared/path",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Workspace 1 permission"
        }

        permission2_data = {
            "path": "shared/path",  # Same path as workspace1
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Workspace 2 permission"
        }

        # Both should succeed (different workspaces)
        response1 = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace1["id"]),
            json=permission1_data
        )
        response2 = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace2["id"]),
            json=permission2_data
        )

        assert response1.status_code == 201
        assert response2.status_code == 201

        # Verify isolation - each workspace should only see its own permissions
        permissions1_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace1["id"])
        )
        permissions2_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace2["id"])
        )

        data1 = permissions1_response.json()
        data2 = permissions2_response.json()

        assert isinstance(data1, dict) and "permissions" in data1
        assert isinstance(data2, dict) and "permissions" in data2
        permissions1 = data1["permissions"]
        permissions2 = data2["permissions"]

        assert len(permissions1) == 1
        assert len(permissions2) == 1
        assert permissions1[0]["workspace_id"] == workspace1["id"]
        assert permissions2[0]["workspace_id"] == workspace2["id"]


class TestPermissionUpdate:
    """Test permission update endpoint."""

    def test_update_permission_success(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                      sample_permission_data: Dict[str, Any]):
        """Test successful permission update."""
        # Create workspace and permission
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        permission_response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=sample_permission_data
        )
        created_permission = permission_response.json()

        # Update permission
        update_data = {
            "path": "updated/path",
            "permission_type": "write",
            "rule_type": "deny",
            "description": "Updated permission description"
        }

        response = client.put(
            API_ENDPOINTS["permission_detail"].format(id=created_permission["id"]),
            json=update_data
        )

        assert response.status_code == 200
        updated_permission = response.json()
        assert updated_permission["path"] == update_data["path"]
        assert updated_permission["permission_type"] == update_data["permission_type"]
        assert updated_permission["rule_type"] == update_data["rule_type"]
        assert updated_permission["description"] == update_data["description"]
        assert updated_permission["id"] == created_permission["id"]
        assert updated_permission["workspace_id"] == created_permission["workspace_id"]

    def test_update_permission_partial(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                      sample_permission_data: Dict[str, Any]):
        """Test partial permission update."""
        # Create workspace and permission
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        permission_response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=sample_permission_data
        )
        created_permission = permission_response.json()

        # Partial update (only description)
        update_data = {
            "description": "Partially updated description"
        }

        response = client.put(
            API_ENDPOINTS["permission_detail"].format(id=created_permission["id"]),
            json=update_data
        )

        assert response.status_code == 200
        updated_permission = response.json()
        assert updated_permission["description"] == update_data["description"]
        # Other fields should remain unchanged
        assert updated_permission["path"] == created_permission["path"]
        assert updated_permission["permission_type"] == created_permission["permission_type"]
        assert updated_permission["rule_type"] == created_permission["rule_type"]

    def test_update_permission_duplicate_constraint(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test that updating to create a duplicate rule is rejected."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create two different permissions
        permission1_data = {
            "path": "path/one",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "First permission"
        }

        permission2_data = {
            "path": "path/two",
            "permission_type": "write",
            "rule_type": "deny",
            "description": "Second permission"
        }

        response1 = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission1_data
        )
        response2 = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission2_data
        )

        permission1 = response1.json()
        permission2 = response2.json()

        # Try to update permission2 to match permission1 exactly
        duplicate_update = {
            "path": permission1["path"],
            "permission_type": permission1["permission_type"],
            "rule_type": permission1["rule_type"],
            "description": "Attempting duplicate"
        }

        response = client.put(
            API_ENDPOINTS["permission_detail"].format(id=permission2["id"]),
            json=duplicate_update
        )

        assert response.status_code == 409
        error_data = response.json()
        assert "duplicate" in error_data["message"].lower() or "already exists" in error_data["message"].lower()

    def test_update_permission_not_found(self, client: TestClient):
        """Test updating non-existent permission."""
        update_data = {
            "path": "non/existent",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "This should fail"
        }

        response = client.put(
            API_ENDPOINTS["permission_detail"].format(id=99999),
            json=update_data
        )

        assert response.status_code == 404

    def test_update_permission_invalid_data(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                           sample_permission_data: Dict[str, Any]):
        """Test permission update with invalid data."""
        # Create workspace and permission
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        permission_response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=sample_permission_data
        )
        permission = permission_response.json()

        # Try to update with invalid data
        invalid_updates = [
            {"path": ""},  # Empty path
            {"permission_type": "invalid"},  # Invalid permission_type
            {"rule_type": "invalid"},  # Invalid rule_type
        ]

        for invalid_data in invalid_updates:
            response = client.put(
                API_ENDPOINTS["permission_detail"].format(id=permission["id"]),
                json=invalid_data
            )
            assert response.status_code == 422


class TestPermissionDeletion:
    """Test permission deletion endpoint."""

    def test_delete_permission_success(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                      sample_permission_data: Dict[str, Any]):
        """Test successful permission deletion."""
        # Create workspace and permission
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        permission_response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=sample_permission_data
        )
        created_permission = permission_response.json()

        # Delete permission
        response = client.delete(
            API_ENDPOINTS["permission_detail"].format(id=created_permission["id"])
        )

        assert response.status_code == 204

        # Verify permission is deleted
        response = client.get(
            API_ENDPOINTS["permission_detail"].format(id=created_permission["id"])
        )
        assert response.status_code == 404

        # Verify it's not in workspace permissions list
        permissions_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        )
        data = permissions_response.json()
        assert isinstance(data, dict)
        assert "permissions" in data
        permissions = data["permissions"]
        permission_ids = [p["id"] for p in permissions]
        assert created_permission["id"] not in permission_ids

    def test_delete_permission_not_found(self, client: TestClient):
        """Test deleting non-existent permission."""
        response = client.delete(API_ENDPOINTS["permission_detail"].format(id=99999))
        assert response.status_code == 404

    def test_delete_permission_cascade_from_workspace(self, client: TestClient,
                                                     sample_workspace_data: Dict[str, Any],
                                                     sample_permissions_data: List[Dict[str, Any]]):
        """Test that permissions are deleted when workspace is deleted (cascade)."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create multiple permissions
        created_permissions = []
        for permission_data in sample_permissions_data:
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )
            created_permissions.append(response.json())

        # Verify permissions exist
        permissions_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        )
        data = permissions_response.json()
        assert isinstance(data, dict) and "permissions" in data
        permissions = data["permissions"]
        assert len(permissions) == len(sample_permissions_data)

        # Delete workspace
        response = client.delete(
            API_ENDPOINTS["workspace_detail"].format(id=workspace["id"])
        )
        assert response.status_code == 204

        # Verify permissions are also deleted
        for permission in created_permissions:
            response = client.get(
                API_ENDPOINTS["permission_detail"].format(id=permission["id"])
            )
            assert response.status_code == 404


class TestPermissionBulkOperations:
    """Test bulk permission operations."""

    def test_bulk_permission_creation_performance(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                                 performance_timer: PerformanceTimer):
        """Test performance of creating many permissions."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create 50 permissions and measure time
        with performance_timer:
            for i in range(50):
                permission_data = {
                    "path": f"bulk/path/{i}",
                    "permission_type": "read" if i % 2 == 0 else "write",
                    "rule_type": "allow",
                    "description": f"Bulk permission {i}"
                }

                response = client.post(
                    API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                    json=permission_data
                )
                assert response.status_code == 201

        # Should complete in reasonable time (less than 5 seconds for 50 permissions)
        assert performance_timer.elapsed_ms < 5000

        # Verify all permissions were created
        permissions_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        )
        data = permissions_response.json()
        assert isinstance(data, dict) and "permissions" in data
        permissions = data["permissions"]
        assert len(permissions) == 50

    def test_permission_listing_large_dataset(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test listing permissions with many permissions."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create 25 permissions (reduced to avoid connection pool exhaustion in test environment)
        for i in range(25):
            permission_data = {
                "path": f"large/dataset/{i}",
                "permission_type": "read" if i % 2 == 0 else "write",
                "rule_type": "allow" if i % 3 != 0 else "deny",
                "description": f"Large dataset permission {i}"
            }

            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )
            assert response.status_code == 201

        # List all permissions
        response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict) and "permissions" in data
        permissions = data["permissions"]
        assert len(permissions) == 25

        # Verify all permissions belong to the workspace
        for permission in permissions:
            assert permission["workspace_id"] == workspace["id"]


class TestPermissionErrorHandling:
    """Test error handling for permission endpoints."""

    def test_invalid_permission_id_format(self, client: TestClient):
        """Test endpoints with invalid permission ID format."""
        invalid_ids = ["abc", "12.34", "null", "undefined"]

        for invalid_id in invalid_ids:
            # Test get permission
            response = client.get(API_ENDPOINTS["permission_detail"].format(id=invalid_id))
            assert response.status_code in [400, 422, 404]

            # Test update permission
            update_data = {"description": "Test update"}
            response = client.put(API_ENDPOINTS["permission_detail"].format(id=invalid_id), json=update_data)
            assert response.status_code in [400, 422, 404]

            # Test delete permission
            response = client.delete(API_ENDPOINTS["permission_detail"].format(id=invalid_id))
            assert response.status_code in [400, 422, 404]

    def test_invalid_workspace_id_format_in_permissions(self, client: TestClient):
        """Test permission endpoints with invalid workspace ID format."""
        invalid_ids = ["abc", "12.34", "null", "undefined"]
        permission_data = {
            "path": "test/path",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Test permission"
        }

        for invalid_id in invalid_ids:
            # Test create permission
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=invalid_id),
                json=permission_data
            )
            assert response.status_code in [400, 422, 404]

            # Test list permissions
            response = client.get(API_ENDPOINTS["workspace_permissions"].format(id=invalid_id))
            assert response.status_code in [400, 422, 404]