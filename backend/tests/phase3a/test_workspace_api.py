"""
Test workspace API endpoints for Phase 3A.

This test module validates all workspace management endpoints including
CRUD operations, activation logic, and error handling as specified
in the Phase 3A requirements.
"""

import pytest
import json
from typing import Dict, Any, List
from fastapi.testclient import TestClient

from .conftest import (
    DatabaseTestHelper, validate_workspace_response, create_test_workspace,
    API_ENDPOINTS, PERFORMANCE_THRESHOLDS, PerformanceTimer
)


class TestWorkspaceCreation:
    """Test workspace creation endpoint."""

    def test_create_workspace_success(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test successful workspace creation."""
        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )

        assert response.status_code == 201

        workspace_data = response.json()
        assert validate_workspace_response(workspace_data)
        assert workspace_data["name"] == sample_workspace_data["name"]
        assert workspace_data["description"] == sample_workspace_data["description"]
        assert workspace_data["is_active"] == sample_workspace_data["is_active"]
        assert "id" in workspace_data
        assert "created_at" in workspace_data
        assert "updated_at" in workspace_data

    def test_create_workspace_minimal_data(self, client: TestClient):
        """Test workspace creation with minimal required data."""
        minimal_data = {
            "name": "Minimal Workspace",
            "description": "Minimal test workspace"
        }

        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=minimal_data
        )

        assert response.status_code == 201

        workspace_data = response.json()
        assert workspace_data["name"] == "Minimal Workspace"
        assert workspace_data["description"] == "Minimal test workspace"
        # is_active should default to False
        assert workspace_data["is_active"] is False

    def test_create_workspace_duplicate_name(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test that duplicate workspace names are rejected."""
        # Create first workspace
        response1 = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert response1.status_code == 201

        # Attempt to create workspace with same name
        duplicate_data = sample_workspace_data.copy()
        duplicate_data["description"] = "Different description"

        response2 = client.post(
            API_ENDPOINTS["workspaces"],
            json=duplicate_data
        )

        assert response2.status_code == 409
        error_data = response2.json()
        assert "code" in error_data
        assert "message" in error_data
        assert "duplicate" in error_data["message"].lower() or "already exists" in error_data["message"].lower()

    def test_create_workspace_invalid_data(self, client: TestClient):
        """Test workspace creation with invalid data."""
        # Missing required fields
        invalid_data = {
            "description": "Missing name field"
        }

        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=invalid_data
        )

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

        # Empty name
        empty_name_data = {
            "name": "",
            "description": "Empty name test"
        }

        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=empty_name_data
        )

        assert response.status_code == 422

    def test_create_workspace_performance(self, client: TestClient, performance_timer: PerformanceTimer):
        """Test workspace creation performance."""
        workspace_data = {
            "name": "Performance Test Workspace",
            "description": "Testing creation performance"
        }

        with performance_timer:
            response = client.post(
                API_ENDPOINTS["workspaces"],
                json=workspace_data
            )

        assert response.status_code == 201
        assert performance_timer.elapsed_ms < PERFORMANCE_THRESHOLDS["database_crud_ms"]


class TestWorkspaceRetrieval:
    """Test workspace retrieval endpoints."""

    def test_list_workspaces_empty(self, client: TestClient):
        """Test listing workspaces when none exist."""
        response = client.get(API_ENDPOINTS["workspaces"])

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "workspaces" in data
        assert "total" in data
        assert "active_workspace_id" in data
        assert isinstance(data["workspaces"], list)
        assert len(data["workspaces"]) == 0
        assert data["total"] == 0
        assert data["active_workspace_id"] is None

    def test_list_workspaces_multiple(self, client: TestClient, sample_workspaces_data: List[Dict[str, Any]]):
        """Test listing multiple workspaces."""
        # Create multiple workspaces
        created_workspaces = []
        for workspace_data in sample_workspaces_data:
            response = client.post(
                API_ENDPOINTS["workspaces"],
                json=workspace_data
            )
            assert response.status_code == 201
            created_workspaces.append(response.json())

        # List all workspaces
        response = client.get(API_ENDPOINTS["workspaces"])

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "workspaces" in data
        workspaces = data["workspaces"]
        assert len(workspaces) == len(sample_workspaces_data)
        assert data["total"] == len(sample_workspaces_data)

        # Verify all workspaces are returned
        workspace_names = [w["name"] for w in workspaces]
        for workspace_data in sample_workspaces_data:
            assert workspace_data["name"] in workspace_names

    def test_get_workspace_by_id(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test retrieving a specific workspace by ID."""
        # Create workspace
        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert response.status_code == 201
        created_workspace = response.json()

        # Retrieve by ID
        workspace_id = created_workspace["id"]
        response = client.get(API_ENDPOINTS["workspace_detail"].format(id=workspace_id))

        assert response.status_code == 200
        workspace_data = response.json()
        assert validate_workspace_response(workspace_data)
        assert workspace_data["id"] == workspace_id
        assert workspace_data["name"] == sample_workspace_data["name"]

    def test_get_workspace_not_found(self, client: TestClient):
        """Test retrieving non-existent workspace."""
        response = client.get(API_ENDPOINTS["workspace_detail"].format(id=99999))

        assert response.status_code == 404
        error_data = response.json()
        assert "code" in error_data
        assert "message" in error_data

    def test_list_workspaces_performance(self, client: TestClient, sample_workspaces_data: List[Dict[str, Any]],
                                        performance_timer: PerformanceTimer):
        """Test workspace listing performance."""
        # Create workspaces
        for workspace_data in sample_workspaces_data:
            client.post(API_ENDPOINTS["workspaces"], json=workspace_data)

        # Time the listing operation
        with performance_timer:
            response = client.get(API_ENDPOINTS["workspaces"])

        assert response.status_code == 200
        assert performance_timer.elapsed_ms < PERFORMANCE_THRESHOLDS["database_crud_ms"]


class TestWorkspaceUpdate:
    """Test workspace update endpoint."""

    def test_update_workspace_success(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test successful workspace update."""
        # Create workspace
        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert response.status_code == 201
        created_workspace = response.json()

        # Update workspace
        workspace_id = created_workspace["id"]
        update_data = {
            "name": "Updated Workspace Name",
            "description": "Updated description",
            "is_active": True
        }

        response = client.put(
            API_ENDPOINTS["workspace_detail"].format(id=workspace_id),
            json=update_data
        )

        assert response.status_code == 200
        updated_workspace = response.json()
        assert updated_workspace["name"] == update_data["name"]
        assert updated_workspace["description"] == update_data["description"]
        assert updated_workspace["is_active"] == update_data["is_active"]
        assert updated_workspace["id"] == workspace_id

    def test_update_workspace_partial(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test partial workspace update."""
        # Create workspace
        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert response.status_code == 201
        created_workspace = response.json()

        # Partial update (only description)
        workspace_id = created_workspace["id"]
        update_data = {
            "description": "Partially updated description"
        }

        response = client.put(
            API_ENDPOINTS["workspace_detail"].format(id=workspace_id),
            json=update_data
        )

        assert response.status_code == 200
        updated_workspace = response.json()
        assert updated_workspace["description"] == update_data["description"]
        # Other fields should remain unchanged
        assert updated_workspace["name"] == created_workspace["name"]
        assert updated_workspace["is_active"] == created_workspace["is_active"]

    def test_update_workspace_duplicate_name(self, client: TestClient, sample_workspaces_data: List[Dict[str, Any]]):
        """Test that updating to a duplicate name is rejected."""
        # Create two workspaces
        workspace1_data = sample_workspaces_data[0]
        workspace2_data = sample_workspaces_data[1]

        response1 = client.post(API_ENDPOINTS["workspaces"], json=workspace1_data)
        response2 = client.post(API_ENDPOINTS["workspaces"], json=workspace2_data)

        assert response1.status_code == 201
        assert response2.status_code == 201

        workspace1 = response1.json()
        workspace2 = response2.json()

        # Try to update workspace2 to have same name as workspace1
        update_data = {
            "name": workspace1["name"]
        }

        response = client.put(
            API_ENDPOINTS["workspace_detail"].format(id=workspace2["id"]),
            json=update_data
        )

        assert response.status_code == 409
        error_data = response.json()
        assert "duplicate" in error_data["message"].lower() or "already exists" in error_data["message"].lower()

    def test_update_workspace_not_found(self, client: TestClient):
        """Test updating non-existent workspace."""
        update_data = {
            "name": "Non-existent Workspace",
            "description": "This should fail"
        }

        response = client.put(
            API_ENDPOINTS["workspace_detail"].format(id=99999),
            json=update_data
        )

        assert response.status_code == 404

    def test_update_workspace_invalid_data(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test workspace update with invalid data."""
        # Create workspace
        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert response.status_code == 201
        created_workspace = response.json()

        # Try to update with invalid data (empty name)
        workspace_id = created_workspace["id"]
        invalid_data = {
            "name": "",
            "description": "Invalid name test"
        }

        response = client.put(
            API_ENDPOINTS["workspace_detail"].format(id=workspace_id),
            json=invalid_data
        )

        assert response.status_code == 422


class TestWorkspaceActivation:
    """Test workspace activation functionality."""

    def test_activate_workspace_success(self, client: TestClient, sample_workspaces_data: List[Dict[str, Any]]):
        """Test successful workspace activation."""
        # Create multiple workspaces
        created_workspaces = []
        for workspace_data in sample_workspaces_data:
            response = client.post(
                API_ENDPOINTS["workspaces"],
                json=workspace_data
            )
            assert response.status_code == 201
            created_workspaces.append(response.json())

        # Activate the second workspace
        workspace_to_activate = created_workspaces[1]
        response = client.post(
            API_ENDPOINTS["workspace_activate"].format(id=workspace_to_activate["id"])
        )

        assert response.status_code == 200
        activation_result = response.json()
        # The activation endpoint returns the activated workspace object
        assert activation_result["id"] == workspace_to_activate["id"]
        assert activation_result["is_active"] is True

        # Verify activation status
        # Get all workspaces to verify only one is active
        response = client.get(API_ENDPOINTS["workspaces"])
        assert response.status_code == 200
        workspaces_data = response.json()
        workspaces = workspaces_data["workspaces"]

        active_workspaces = [w for w in workspaces if w["is_active"]]
        assert len(active_workspaces) == 1
        assert active_workspaces[0]["id"] == workspace_to_activate["id"]

    def test_activate_workspace_deactivates_others(self, client: TestClient, sample_workspaces_data: List[Dict[str, Any]]):
        """Test that activating a workspace deactivates all others."""
        # Create workspaces, with one initially active
        sample_workspaces_data[0]["is_active"] = True

        created_workspaces = []
        for workspace_data in sample_workspaces_data:
            response = client.post(
                API_ENDPOINTS["workspaces"],
                json=workspace_data
            )
            assert response.status_code == 201
            created_workspaces.append(response.json())

        # Verify initial state (first workspace should be active)
        response = client.get(API_ENDPOINTS["workspaces"])
        workspaces_data = response.json()
        workspaces = workspaces_data["workspaces"]
        active_workspaces = [w for w in workspaces if w["is_active"]]
        assert len(active_workspaces) == 1
        assert active_workspaces[0]["id"] == created_workspaces[0]["id"]

        # Activate a different workspace
        workspace_to_activate = created_workspaces[2]
        response = client.post(
            API_ENDPOINTS["workspace_activate"].format(id=workspace_to_activate["id"])
        )
        assert response.status_code == 200

        # Verify only the new workspace is active
        response = client.get(API_ENDPOINTS["workspaces"])
        workspaces_data = response.json()
        workspaces = workspaces_data["workspaces"]
        active_workspaces = [w for w in workspaces if w["is_active"]]
        assert len(active_workspaces) == 1
        assert active_workspaces[0]["id"] == workspace_to_activate["id"]

    def test_activate_workspace_not_found(self, client: TestClient):
        """Test activating non-existent workspace."""
        response = client.post(
            API_ENDPOINTS["workspace_activate"].format(id=99999)
        )

        assert response.status_code == 404

    def test_activate_already_active_workspace(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test activating an already active workspace."""
        # Create and activate workspace
        sample_workspace_data["is_active"] = True
        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert response.status_code == 201
        workspace = response.json()

        # Try to activate it again
        response = client.post(
            API_ENDPOINTS["workspace_activate"].format(id=workspace["id"])
        )

        # Should still succeed (idempotent operation)
        assert response.status_code == 200

        # Verify it's still active
        response = client.get(API_ENDPOINTS["workspace_detail"].format(id=workspace["id"]))
        workspace_data = response.json()
        assert workspace_data["is_active"] is True


class TestWorkspaceDeletion:
    """Test workspace deletion endpoint."""

    def test_delete_workspace_success(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test successful workspace deletion."""
        # Create workspace
        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert response.status_code == 201
        created_workspace = response.json()

        # Delete workspace
        workspace_id = created_workspace["id"]
        response = client.delete(
            API_ENDPOINTS["workspace_detail"].format(id=workspace_id)
        )

        assert response.status_code == 204

        # Verify workspace is deleted
        response = client.get(API_ENDPOINTS["workspace_detail"].format(id=workspace_id))
        assert response.status_code == 404

    def test_delete_workspace_not_found(self, client: TestClient):
        """Test deleting non-existent workspace."""
        response = client.delete(
            API_ENDPOINTS["workspace_detail"].format(id=99999)
        )

        assert response.status_code == 404

    def test_delete_active_workspace(self, client: TestClient, sample_workspaces_data: List[Dict[str, Any]]):
        """Test deleting an active workspace."""
        # Create workspaces with one active
        sample_workspaces_data[0]["is_active"] = True

        created_workspaces = []
        for workspace_data in sample_workspaces_data:
            response = client.post(
                API_ENDPOINTS["workspaces"],
                json=workspace_data
            )
            assert response.status_code == 201
            created_workspaces.append(response.json())

        # Delete the active workspace
        active_workspace = created_workspaces[0]
        response = client.delete(
            API_ENDPOINTS["workspace_detail"].format(id=active_workspace["id"])
        )

        assert response.status_code == 204

        # Verify no workspace is active after deletion
        response = client.get(API_ENDPOINTS["workspaces"])
        data = response.json()
        workspaces = data["workspaces"]
        active_workspaces = [w for w in workspaces if w["is_active"]]
        assert len(active_workspaces) == 0


class TestWorkspaceErrorHandling:
    """Test error handling for workspace endpoints."""

    def test_invalid_workspace_id_format(self, client: TestClient):
        """Test endpoints with invalid workspace ID format."""
        invalid_ids = ["abc", "12.34", "null", "undefined"]

        for invalid_id in invalid_ids:
            # Test get workspace
            response = client.get(API_ENDPOINTS["workspace_detail"].format(id=invalid_id))
            assert response.status_code in [400, 422, 404]  # Various validation errors

            # Test activate workspace
            response = client.post(API_ENDPOINTS["workspace_activate"].format(id=invalid_id))
            assert response.status_code in [400, 422, 404]

    def test_malformed_json_request(self, client: TestClient):
        """Test workspace creation with malformed JSON."""
        response = client.post(
            API_ENDPOINTS["workspaces"],
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_content_type_validation(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test that proper Content-Type is required."""
        response = client.post(
            API_ENDPOINTS["workspaces"],
            data=json.dumps(sample_workspace_data),
            headers={"Content-Type": "text/plain"}
        )

        # Should fail due to incorrect content type
        assert response.status_code in [415, 422]

    def test_request_size_limits(self, client: TestClient):
        """Test handling of oversized requests."""
        # Create very large description
        large_description = "x" * 10000  # 10KB description

        large_data = {
            "name": "Large Request Test",
            "description": large_description
        }

        response = client.post(
            API_ENDPOINTS["workspaces"],
            json=large_data
        )

        # Should either succeed or fail gracefully
        # (depending on server size limits)
        assert response.status_code in [201, 413, 422]


class TestWorkspacePagination:
    """Test workspace listing pagination (if implemented)."""

    def test_workspace_listing_large_dataset(self, client: TestClient):
        """Test workspace listing with many workspaces."""
        # Create 20 workspaces
        for i in range(20):
            workspace_data = {
                "name": f"Workspace {i:02d}",
                "description": f"Test workspace number {i}",
                "is_active": False
            }
            response = client.post(API_ENDPOINTS["workspaces"], json=workspace_data)
            assert response.status_code == 201

        # List all workspaces
        response = client.get(API_ENDPOINTS["workspaces"])
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert "workspaces" in data
        workspaces = data["workspaces"]
        assert len(workspaces) == 20

        # Verify ordering (should be consistent)
        workspace_names = [w["name"] for w in workspaces]
        assert len(set(workspace_names)) == 20  # All unique names

    def test_workspace_listing_with_pagination_params(self, client: TestClient):
        """Test workspace listing with pagination parameters (if supported)."""
        # Create some workspaces
        for i in range(5):
            workspace_data = {
                "name": f"Paginated Workspace {i}",
                "description": f"Workspace for pagination test {i}",
                "is_active": False
            }
            client.post(API_ENDPOINTS["workspaces"], json=workspace_data)

        # Test with pagination parameters (even if not implemented, should not error)
        response = client.get(API_ENDPOINTS["workspaces"] + "?page=1&limit=2")

        # Should either return paginated results or ignore parameters
        assert response.status_code == 200
        workspaces = response.json()
        assert isinstance(workspaces, (list, dict))  # Could be list or paginated object