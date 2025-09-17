"""
Integration Tests for Phase 3B
Phase 3B: Advanced UI & Full Workspace Experience

Tests integration between frontend and backend, WebSocket functionality,
and complete system workflows.
"""

import pytest
import json
import asyncio
import websockets
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db
from app.models.workspace import Workspace, Permission
from .conftest import (
    test_db_session,
    clear_test_data,
    create_test_workspace,
    create_test_permission
)


class TestWebSocketIntegration:
    """Test WebSocket functionality for real-time updates."""

    @pytest.mark.asyncio
    async def test_websocket_workspace_activation_events(self, test_db_session: Session):
        """Test that workspace activation events are broadcast via WebSocket."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            # Create test workspaces
            workspace1 = create_test_workspace(test_db_session, "Workspace 1", is_active=True)
            workspace2 = create_test_workspace(test_db_session, "Workspace 2", is_active=False)

            # Mock WebSocket manager to capture messages
            with patch('app.main.ui_manager') as mock_ui_manager:
                mock_ui_manager.broadcast = AsyncMock()

                # Activate workspace 2 (should deactivate workspace 1)
                response = client.post(f"/api/workspaces/{workspace2.id}/activate")
                assert response.status_code == 200

                # Verify WebSocket broadcast was called
                mock_ui_manager.broadcast.assert_called()

                # Get the actual call arguments
                call_args = mock_ui_manager.broadcast.call_args
                broadcast_message = call_args[0][0]

                # Parse the message if it's JSON
                try:
                    message_data = json.loads(broadcast_message)
                    # Check if it's a structured workspace activation message
                    if isinstance(message_data, dict) and message_data.get("type") == "workspace_activated":
                        assert message_data["data"]["workspaceId"] == workspace2.id
                        assert message_data["data"]["workspaceName"] == "Workspace 2"
                except json.JSONDecodeError:
                    # If not JSON, it should at least mention workspace activation
                    assert "workspace" in broadcast_message.lower() or "activated" in broadcast_message.lower()

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_websocket_permission_update_events(self, test_db_session: Session):
        """Test that permission updates trigger WebSocket events."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            workspace = create_test_workspace(test_db_session, "Permission Test Workspace", is_active=True)

            # Mock WebSocket manager
            with patch('app.main.ui_manager') as mock_ui_manager:
                mock_ui_manager.broadcast = AsyncMock()

                # Add permission (should trigger event)
                permission_data = {
                    "path": "test/path",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Test permission"
                }

                response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=permission_data)
                assert response.status_code == 201

                permission_id = response.json()["id"]

                # Verify broadcast was called for permission creation
                assert mock_ui_manager.broadcast.called

                # Reset mock for deletion test
                mock_ui_manager.reset_mock()

                # Delete permission (should trigger event)
                response = client.delete(f"/api/permissions/{permission_id}")
                assert response.status_code == 204

                # Verify broadcast was called for permission deletion
                assert mock_ui_manager.broadcast.called

        finally:
            app.dependency_overrides.clear()


class TestAPIIntegration:
    """Test API integration scenarios that mirror frontend usage."""

    def test_complete_workspace_management_flow(self, test_db_session: Session):
        """Test complete workflow that mirrors frontend workspace manager usage."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            # 1. Initial load - Get all workspaces (empty initially)
            response = client.get("/api/workspaces")
            assert response.status_code == 200
            assert len(response.json()["workspaces"]) == 0

            # 2. Create first workspace
            workspace_data = {
                "name": "Development",
                "description": "Development environment workspace",
                "is_active": True
            }

            response = client.post("/api/workspaces", json=workspace_data)
            assert response.status_code == 201
            dev_workspace = response.json()
            assert dev_workspace["is_active"] is True

            # 3. Verify workspace appears in list
            response = client.get("/api/workspaces")
            assert response.status_code == 200
            workspaces = response.json()["workspaces"]
            assert len(workspaces) == 1
            assert workspaces[0]["name"] == "Development"

            # 4. Create second workspace (not active)
            research_data = {
                "name": "Research",
                "description": "Research activities workspace",
                "is_active": False
            }

            response = client.post("/api/workspaces", json=research_data)
            assert response.status_code == 201
            research_workspace = response.json()

            # 5. Verify only one workspace is active
            response = client.get("/api/workspaces")
            workspaces = response.json()["workspaces"]
            active_workspaces = [w for w in workspaces if w["is_active"]]
            assert len(active_workspaces) == 1
            assert active_workspaces[0]["name"] == "Development"

            # 6. Switch active workspace
            response = client.post(f"/api/workspaces/{research_workspace['id']}/activate")
            assert response.status_code == 200

            # 7. Verify switch worked
            response = client.get("/api/workspaces")
            workspaces = response.json()["workspaces"]
            active_workspaces = [w for w in workspaces if w["is_active"]]
            assert len(active_workspaces) == 1
            assert active_workspaces[0]["name"] == "Research"

            # 8. Delete non-active workspace
            response = client.delete(f"/api/workspaces/{dev_workspace['id']}")
            assert response.status_code == 204

            # 9. Verify deletion
            response = client.get("/api/workspaces")
            workspaces = response.json()["workspaces"]
            assert len(workspaces) == 1
            assert workspaces[0]["name"] == "Research"

        finally:
            app.dependency_overrides.clear()

    def test_two_panel_permission_editor_workflow(self, test_db_session: Session):
        """Test workflow that mirrors two-panel permission editor usage."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            # Setup: Create workspace
            workspace = create_test_workspace(test_db_session, "Permission Editor Test", is_active=True)

            # 1. Initial load - Get workspace permissions (empty)
            response = client.get(f"/api/workspaces/{workspace.id}/permissions")
            assert response.status_code == 200
            assert len(response.json()["permissions"]) == 0

            # 2. Simulate file tree load with batch API (no permissions yet)
            initial_paths = [
                "projects/webapp/src/main.py",
                "projects/webapp/tests/test_main.py",
                "materials/course_overview.pdf",
                "materials/private/grades.xlsx",
                "output/reports/summary.pdf"
            ]

            batch_request = {"paths": initial_paths}
            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json=batch_request
            )
            assert response.status_code == 200

            results = response.json()["results"]
            # All should have no permissions initially
            for result in results:
                assert result["status"] == "none"
                assert result["matchedRule"] is None

            # 3. Add first permission rule
            perm1_data = {
                "path": "projects",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Allow write access to projects"
            }

            response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=perm1_data)
            assert response.status_code == 201
            perm1 = response.json()

            # 4. Refresh file tree permissions after rule addition
            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json=batch_request
            )
            assert response.status_code == 200

            results = response.json()["results"]
            results_by_path = {r["path"]: r for r in results}

            # Projects paths should now have write access
            assert results_by_path["projects/webapp/src/main.py"]["status"] == "write"
            assert results_by_path["projects/webapp/tests/test_main.py"]["status"] == "write"
            # Non-projects paths should still be denied
            assert results_by_path["materials/course_overview.pdf"]["status"] == "none"

            # 5. Add second permission rule
            perm2_data = {
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Allow read access to materials"
            }

            response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=perm2_data)
            assert response.status_code == 201

            # 6. Add deny rule for private materials
            perm3_data = {
                "path": "materials/private",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Deny access to private materials"
            }

            response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=perm3_data)
            assert response.status_code == 201

            # 7. Final permission check - verify precedence
            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json=batch_request
            )
            assert response.status_code == 200

            results = response.json()["results"]
            results_by_path = {r["path"]: r for r in results}

            # Verify final permissions
            assert results_by_path["projects/webapp/src/main.py"]["status"] == "write"
            assert results_by_path["materials/course_overview.pdf"]["status"] == "read"
            assert results_by_path["materials/private/grades.xlsx"]["status"] == "denied"  # Denied by specific rule
            assert results_by_path["output/reports/summary.pdf"]["status"] == "none"  # No rule

            # 8. Verify permission list
            response = client.get(f"/api/workspaces/{workspace.id}/permissions")
            assert response.status_code == 200
            permissions = response.json()["permissions"]
            assert len(permissions) == 3

            # 9. Delete a permission (simulate UI deletion)
            response = client.delete(f"/api/permissions/{perm1['id']}")
            assert response.status_code == 204

            # 10. Verify permission was deleted
            response = client.get(f"/api/workspaces/{workspace.id}/permissions")
            assert response.status_code == 200
            permissions = response.json()["permissions"]
            assert len(permissions) == 2

            # 11. Verify file tree reflects change
            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json=batch_request
            )
            assert response.status_code == 200

            results = response.json()["results"]
            results_by_path = {r["path"]: r for r in results}

            # Projects should now be denied (rule was deleted)
            assert results_by_path["projects/webapp/src/main.py"]["status"] == "none"

        finally:
            app.dependency_overrides.clear()

    def test_permission_inspector_data_completeness(self, test_db_session: Session):
        """Test that batch API provides complete data for permission inspector."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            workspace = create_test_workspace(test_db_session, "Inspector Test", is_active=True)

            # Create permissions with detailed descriptions
            permissions = [
                {
                    "path": "documents",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "General document access for team members"
                },
                {
                    "path": "documents/confidential",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Confidential documents - manager approval required"
                },
                {
                    "path": "code",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Full code repository access for developers"
                }
            ]

            created_permissions = []
            for perm_data in permissions:
                response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=perm_data)
                assert response.status_code == 201
                created_permissions.append(response.json())

            # Test paths that should provide rich inspector data
            test_paths = [
                "documents/readme.md",                    # Should match general allow
                "documents/confidential/salary.xlsx",    # Should match specific deny
                "code/src/main.py",                      # Should match write allow
                "unmapped/file.txt"                      # Should have no rule
            ]

            batch_request = {"paths": test_paths}
            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json=batch_request
            )
            assert response.status_code == 200

            results = response.json()["results"]
            results_by_path = {r["path"]: r for r in results}

            # Test documents/readme.md - should have rich rule data
            readme_result = results_by_path["documents/readme.md"]
            assert readme_result["status"] == "read"
            assert readme_result["matchedRule"] is not None

            rule = readme_result["matchedRule"]
            assert rule["path"] == "documents"
            assert rule["permission_type"] == "read"
            assert rule["rule_type"] == "allow"
            assert rule["description"] == "General document access for team members"
            assert rule["workspace_id"] == workspace.id
            assert "db-rule-" in rule["id"]  # Should have database rule ID format

            # Test documents/confidential/salary.xlsx - should show deny rule
            salary_result = results_by_path["documents/confidential/salary.xlsx"]
            assert salary_result["status"] == "none"
            assert salary_result["matchedRule"] is not None

            deny_rule = salary_result["matchedRule"]
            assert deny_rule["path"] == "documents/confidential"
            assert deny_rule["rule_type"] == "deny"
            assert deny_rule["description"] == "Confidential documents - manager approval required"

            # Test code/src/main.py - should show write rule
            code_result = results_by_path["code/src/main.py"]
            assert code_result["status"] == "write"
            assert code_result["matchedRule"] is not None

            write_rule = code_result["matchedRule"]
            assert write_rule["permission_type"] == "write"
            assert write_rule["description"] == "Full code repository access for developers"

            # Test unmapped/file.txt - should have no rule
            unmapped_result = results_by_path["unmapped/file.txt"]
            assert unmapped_result["status"] == "none"
            assert unmapped_result["matchedRule"] is None

        finally:
            app.dependency_overrides.clear()


class TestErrorHandlingIntegration:
    """Test error handling scenarios that frontend might encounter."""

    def test_workspace_conflict_scenarios(self, test_db_session: Session):
        """Test conflict scenarios that frontend should handle gracefully."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            # Create workspace
            workspace_data = {
                "name": "Test Workspace",
                "description": "Test workspace",
                "is_active": False
            }

            response = client.post("/api/workspaces", json=workspace_data)
            assert response.status_code == 201
            workspace = response.json()

            # Test duplicate name creation
            response = client.post("/api/workspaces", json=workspace_data)
            assert response.status_code == 409  # Conflict

            error_data = response.json()
            assert "name" in error_data.get("message", "").lower()

            # Test deleting active workspace
            # First activate it
            response = client.post(f"/api/workspaces/{workspace['id']}/activate")
            assert response.status_code == 200

            # Try to delete active workspace
            response = client.delete(f"/api/workspaces/{workspace['id']}")
            assert response.status_code in [400, 409]  # Should be prevented

            # Test invalid workspace operations
            response = client.get("/api/workspaces/99999")
            assert response.status_code == 404

            response = client.post("/api/workspaces/99999/activate")
            assert response.status_code == 404

        finally:
            app.dependency_overrides.clear()

    def test_permission_validation_errors(self, test_db_session: Session):
        """Test permission validation errors that UI should handle."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            workspace = create_test_workspace(test_db_session, "Validation Test", is_active=True)

            # Test invalid permission data
            invalid_permissions = [
                # Missing required fields
                {"path": "test"},
                # Invalid permission type
                {"path": "test", "permission_type": "invalid", "rule_type": "allow"},
                # Invalid rule type
                {"path": "test", "permission_type": "read", "rule_type": "invalid"},
                # Empty path
                {"path": "", "permission_type": "read", "rule_type": "allow"},
            ]

            for invalid_perm in invalid_permissions:
                response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=invalid_perm)
                assert response.status_code in [400, 422]  # Validation error

            # Test duplicate permission rule
            valid_perm = {
                "path": "test/path",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Test permission"
            }

            # Create first permission
            response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=valid_perm)
            assert response.status_code == 201

            # Try to create duplicate
            response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=valid_perm)
            assert response.status_code == 409  # Conflict due to unique constraint

        finally:
            app.dependency_overrides.clear()

    def test_batch_api_error_handling(self, test_db_session: Session):
        """Test batch API error handling scenarios."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            workspace = create_test_workspace(test_db_session, "Batch Error Test", is_active=True)

            # Test empty paths array
            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json={"paths": []}
            )
            assert response.status_code == 200  # Should handle empty array gracefully
            assert response.json()["results"] == []

            # Test very long paths array (stress test)
            long_paths = [f"path{i}/file.txt" for i in range(1000)]
            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json={"paths": long_paths}
            )
            # Should either succeed or fail gracefully with appropriate error
            assert response.status_code in [200, 413, 422]

            if response.status_code == 200:
                results = response.json()["results"]
                assert len(results) == 1000

            # Test invalid workspace ID
            response = client.post(
                "/api/workspaces/99999/effective-permissions:batch",
                json={"paths": ["test/path"]}
            )
            assert response.status_code == 404

            # Test malformed request
            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json={"invalid_field": ["test/path"]}
            )
            assert response.status_code == 422  # Validation error

        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])