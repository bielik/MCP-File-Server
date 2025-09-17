"""
End-to-End Workflow Tests for Phase 3B
Phase 3B: Advanced UI & Full Workspace Experience

Tests complete user workflows including workspace lifecycle,
permission management, and batch API operations.
"""

import pytest
import time
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.workspace import Workspace, Permission
from .conftest import (
    test_db_session,
    clear_test_data,
    create_test_workspace,
    create_test_permission,
    PerformanceTimer
)


class TestE2EWorkspaceLifecycle:
    """Test complete workspace lifecycle operations."""

    def test_complete_workspace_creation_to_deletion_workflow(self, client: TestClient):
        """Test: Create → Populate → Activate → Use → Delete workflow."""
        try:
            # Step 1: Create new workspace
            workspace_data = {
                "name": "Test Development Workspace",
                "description": "Workspace for testing development features",
                "is_active": False
            }

            response = client.post("/api/workspaces", json=workspace_data)
            assert response.status_code == 201, f"Failed to create workspace: {response.text}"

            workspace = response.json()
            workspace_id = workspace["id"]
            assert workspace["name"] == workspace_data["name"]
            assert workspace["is_active"] is False

            # Step 2: Add multiple permissions to workspace
            permissions_to_add = [
                {
                    "path": "projects",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Allow write access to projects directory"
                },
                {
                    "path": "materials",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Allow read access to materials directory"
                },
                {
                    "path": "materials/private",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Deny access to private materials"
                },
                {
                    "path": "output",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Allow write access to output directory"
                }
            ]

            permission_ids = []
            for perm_data in permissions_to_add:
                response = client.post(f"/api/workspaces/{workspace_id}/permissions", json=perm_data)
                assert response.status_code == 201, f"Failed to create permission: {response.text}"
                permission_ids.append(response.json()["id"])

            # Step 3: Verify permissions were created
            response = client.get(f"/api/workspaces/{workspace_id}/permissions")
            assert response.status_code == 200
            permissions = response.json()["permissions"]
            assert len(permissions) == 4

            # Step 4: Activate workspace
            response = client.post(f"/api/workspaces/{workspace_id}/activate")
            assert response.status_code == 200, f"Failed to activate workspace: {response.text}"

            activated_workspace = response.json()
            assert activated_workspace["is_active"] is True

            # Step 5: Test batch effective permissions API
            test_paths = [
                "projects/webapp",
                "projects/webapp/src/main.py",
                "materials/course_overview.pdf",
                "materials/private/grades.xlsx",
                "output/reports",
                "private/config"
            ]

            batch_request = {"paths": test_paths}
            response = client.post(
                f"/api/workspaces/{workspace_id}/effective-permissions:batch",
                json=batch_request
            )
            assert response.status_code == 200, f"Batch API failed: {response.text}"

            batch_results = response.json()["results"]
            assert len(batch_results) == len(test_paths)

            # Verify specific permission results
            results_by_path = {r["path"]: r for r in batch_results}

            # projects/webapp should have write access
            assert results_by_path["projects/webapp"]["status"] == "write"
            assert results_by_path["projects/webapp"]["matchedRule"] is not None
            assert results_by_path["projects/webapp"]["matchedRule"]["rule_type"] == "allow"

            # materials/course_overview.pdf should have read access
            assert results_by_path["materials/course_overview.pdf"]["status"] == "read"
            assert results_by_path["materials/course_overview.pdf"]["matchedRule"]["rule_type"] == "allow"

            # materials/private/grades.xlsx should be denied (deny rule overrides)
            assert results_by_path["materials/private/grades.xlsx"]["status"] == "denied"
            assert results_by_path["materials/private/grades.xlsx"]["matchedRule"]["rule_type"] == "deny"

            # private/config should have no access (default deny)
            assert results_by_path["private/config"]["status"] == "none"
            assert results_by_path["private/config"]["matchedRule"] is None

            # Step 6: Create second workspace and switch
            workspace2_data = {
                "name": "Research Workspace",
                "description": "Workspace for research activities",
                "is_active": False
            }

            response = client.post("/api/workspaces", json=workspace2_data)
            assert response.status_code == 201
            workspace2_id = response.json()["id"]

            # Add different permissions to second workspace
            research_permission = {
                "path": "research",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Allow write access to research directory"
            }

            response = client.post(f"/api/workspaces/{workspace2_id}/permissions", json=research_permission)
            assert response.status_code == 201

            # Activate second workspace
            response = client.post(f"/api/workspaces/{workspace2_id}/activate")
            assert response.status_code == 200

            # Verify first workspace is no longer active
            response = client.get(f"/api/workspaces/{workspace_id}")
            assert response.status_code == 200
            assert response.json()["is_active"] is False

            # Step 7: Verify workspace switching affects permissions
            # Test same path with different workspace
            batch_request = {"paths": ["projects/webapp"]}
            response = client.post(
                f"/api/workspaces/{workspace2_id}/effective-permissions:batch",
                json=batch_request
            )
            assert response.status_code == 200

            result = response.json()["results"][0]
            # Should have no access in research workspace
            assert result["status"] == "denied"
            assert result["matchedRule"] is None

            # Step 8: Delete workspace (should fail while active)
            response = client.delete(f"/api/workspaces/{workspace2_id}")
            # Should not be able to delete active workspace
            assert response.status_code == 400 or response.status_code == 409

            # Deactivate and then delete
            response = client.post(f"/api/workspaces/{workspace_id}/activate")
            assert response.status_code == 200

            response = client.delete(f"/api/workspaces/{workspace2_id}")
            assert response.status_code == 204

            # Verify workspace is deleted
            response = client.get(f"/api/workspaces/{workspace2_id}")
            assert response.status_code == 404

            # Step 9: Final cleanup - need to deactivate workspace1 before deleting
            # Since we can't have zero active workspaces, we skip the deletion test for the active one
            # In a real application, you would activate a different workspace first
            pass  # workspace_id is still active, so we can't delete it without violating the business rule

        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_permission_precedence_validation(self, test_db_session: Session):
        """Test permission precedence rules are correctly applied."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            # Create workspace
            workspace = create_test_workspace(test_db_session, "Precedence Test", is_active=True)

            # Create permissions with different precedence levels
            permissions = [
                # General allow rule
                {
                    "path": "materials",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "General read access to materials"
                },
                # More specific deny rule (should override)
                {
                    "path": "materials/private",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Deny access to private materials"
                },
                # Even more specific allow rule (should override deny)
                {
                    "path": "materials/private/public_subset",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Allow access to public subset within private"
                },
                # Write rule (should imply read)
                {
                    "path": "projects",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Write access to projects"
                },
                # Deny write but allow read (deny should win for write)
                {
                    "path": "projects/readonly",
                    "permission_type": "write",
                    "rule_type": "deny",
                    "description": "Deny write to readonly project"
                }
            ]

            for perm_data in permissions:
                response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=perm_data)
                assert response.status_code == 201

            # Test precedence scenarios
            test_cases = [
                # Specificity rule: more specific path wins
                {
                    "path": "materials/document.pdf",
                    "expected_status": "read",
                    "expected_rule_type": "allow",
                    "reason": "General materials allow rule applies"
                },
                {
                    "path": "materials/private/secret.pdf",
                    "expected_status": "none",
                    "expected_rule_type": "deny",
                    "reason": "Specific deny rule overrides general allow"
                },
                {
                    "path": "materials/private/public_subset/info.pdf",
                    "expected_status": "read",
                    "expected_rule_type": "allow",
                    "reason": "Most specific allow rule overrides parent deny"
                },
                # Write implies read rule
                {
                    "path": "projects/webapp/file.py",
                    "expected_status": "write",
                    "expected_rule_type": "allow",
                    "reason": "Write permission includes read access"
                },
                # Deny wins rule: deny write overrides implicit read
                {
                    "path": "projects/readonly/config.json",
                    "expected_status": "read",
                    "expected_rule_type": "allow",
                    "reason": "Should have read from parent but not write due to deny"
                },
                # Default deny
                {
                    "path": "unmatched/path.txt",
                    "expected_status": "none",
                    "expected_rule_type": None,
                    "reason": "No matching rules - default deny"
                }
            ]

            test_paths = [case["path"] for case in test_cases]
            batch_request = {"paths": test_paths}

            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json=batch_request
            )
            assert response.status_code == 200

            results = response.json()["results"]
            results_by_path = {r["path"]: r for r in results}

            # Verify each test case
            for case in test_cases:
                result = results_by_path[case["path"]]
                assert result["status"] == case["expected_status"], \
                    f"Path {case['path']}: expected {case['expected_status']}, got {result['status']}. Reason: {case['reason']}"

                if case["expected_rule_type"]:
                    assert result["matchedRule"] is not None, \
                        f"Path {case['path']}: expected matched rule but got None"
                    assert result["matchedRule"]["rule_type"] == case["expected_rule_type"], \
                        f"Path {case['path']}: expected rule type {case['expected_rule_type']}, got {result['matchedRule']['rule_type']}"
                else:
                    assert result["matchedRule"] is None, \
                        f"Path {case['path']}: expected no matched rule but got {result['matchedRule']}"

        finally:
            app.dependency_overrides.clear()

    def test_concurrent_workspace_operations(self, test_db_session: Session):
        """Test concurrent workspace operations maintain data consistency."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            # Create multiple workspaces
            workspaces = []
            for i in range(3):
                workspace_data = {
                    "name": f"Concurrent Workspace {i+1}",
                    "description": f"Test workspace {i+1} for concurrent operations",
                    "is_active": False
                }
                response = client.post("/api/workspaces", json=workspace_data)
                assert response.status_code == 201
                workspaces.append(response.json())

            # Test rapid workspace switching
            activation_order = [0, 1, 2, 1, 0, 2]
            for workspace_idx in activation_order:
                workspace_id = workspaces[workspace_idx]["id"]
                response = client.post(f"/api/workspaces/{workspace_id}/activate")
                assert response.status_code == 200

                # Verify only one workspace is active
                response = client.get("/api/workspaces")
                assert response.status_code == 200
                all_workspaces = response.json()["workspaces"]

                active_count = sum(1 for w in all_workspaces if w["is_active"])
                assert active_count == 1, f"Expected exactly 1 active workspace, got {active_count}"

                active_workspace = next(w for w in all_workspaces if w["is_active"])
                assert active_workspace["id"] == workspace_id

            # Test concurrent permission operations
            final_active_workspace = workspaces[activation_order[-1]]
            workspace_id = final_active_workspace["id"]

            # Add multiple permissions rapidly
            permissions_data = [
                {"path": f"path{i}", "permission_type": "read", "rule_type": "allow", "description": f"Test permission {i}"}
                for i in range(10)
            ]

            created_permissions = []
            for perm_data in permissions_data:
                response = client.post(f"/api/workspaces/{workspace_id}/permissions", json=perm_data)
                assert response.status_code == 201
                created_permissions.append(response.json())

            # Verify all permissions were created
            response = client.get(f"/api/workspaces/{workspace_id}/permissions")
            assert response.status_code == 200
            stored_permissions = response.json()["permissions"]
            assert len(stored_permissions) == 10

            # Test batch permission deletion
            for perm in created_permissions[:5]:  # Delete first 5
                response = client.delete(f"/api/permissions/{perm['id']}")
                assert response.status_code == 204

            # Verify correct number remain
            response = client.get(f"/api/workspaces/{workspace_id}/permissions")
            assert response.status_code == 200
            remaining_permissions = response.json()["permissions"]
            assert len(remaining_permissions) == 5

        finally:
            app.dependency_overrides.clear()


class TestBatchAPIPerformance:
    """Test batch API performance and scalability."""

    def test_batch_api_performance_targets(self, test_db_session: Session):
        """Test batch API meets performance targets."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            # Create workspace with comprehensive permission set
            workspace = create_test_workspace(test_db_session, "Performance Test", is_active=True)

            # Create realistic permission structure
            permissions = [
                {"path": "projects", "permission_type": "write", "rule_type": "allow"},
                {"path": "projects/legacy", "permission_type": "read", "rule_type": "allow"},
                {"path": "projects/legacy/old", "permission_type": "read", "rule_type": "deny"},
                {"path": "materials", "permission_type": "read", "rule_type": "allow"},
                {"path": "materials/private", "permission_type": "read", "rule_type": "deny"},
                {"path": "materials/private/public", "permission_type": "read", "rule_type": "allow"},
                {"path": "output", "permission_type": "write", "rule_type": "allow"},
                {"path": "temp", "permission_type": "write", "rule_type": "allow"},
                {"path": "temp/cache", "permission_type": "read", "rule_type": "deny"},
            ]

            for perm_data in permissions:
                create_test_permission(test_db_session, workspace.id, **perm_data)

            # Performance test scenarios
            test_scenarios = [
                {"name": "Small batch - 10 paths", "path_count": 10, "target_ms": 50},
                {"name": "Medium batch - 50 paths", "path_count": 50, "target_ms": 75},
                {"name": "Large batch - 150 paths", "path_count": 150, "target_ms": 100},
            ]

            for scenario in test_scenarios:
                # Generate test paths
                test_paths = []
                base_paths = ["projects", "materials", "output", "temp", "private"]

                for i in range(scenario["path_count"]):
                    base = base_paths[i % len(base_paths)]
                    test_paths.append(f"{base}/subdir{i // len(base_paths)}/file{i}.txt")

                # Performance measurement
                with PerformanceTimer(f"batch_api_{scenario['path_count']}_paths", threshold_ms=scenario["target_ms"]):
                    batch_request = {"paths": test_paths}
                    response = client.post(
                        f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                        json=batch_request
                    )

                assert response.status_code == 200, f"Batch API failed for {scenario['name']}: {response.text}"

                results = response.json()["results"]
                assert len(results) == scenario["path_count"]

                # Verify all results have required fields
                for result in results:
                    assert "path" in result
                    assert "status" in result
                    assert result["status"] in ["none", "read", "write"]
                    # matchedRule can be None for default deny

            # Test rapid successive calls (simulating UI usage)
            rapid_test_paths = ["projects/test", "materials/doc", "output/result"]
            rapid_calls = 20

            start_time = time.time()
            for _ in range(rapid_calls):
                batch_request = {"paths": rapid_test_paths}
                response = client.post(
                    f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                    json=batch_request
                )
                assert response.status_code == 200

            total_time = (time.time() - start_time) * 1000  # Convert to ms
            avg_time_per_call = total_time / rapid_calls

            # Each call should average under 30ms for good UI responsiveness
            assert avg_time_per_call < 30, f"Average batch API call took {avg_time_per_call:.2f}ms, target is <30ms"

        finally:
            app.dependency_overrides.clear()

    def test_matched_rule_explanations(self, test_db_session: Session):
        """Test that matched rule explanations are accurate and helpful."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            workspace = create_test_workspace(test_db_session, "Explanation Test", is_active=True)

            # Create permissions with specific descriptions
            permissions = [
                {
                    "path": "docs",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Documentation access for team members"
                },
                {
                    "path": "docs/sensitive",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Sensitive documents - restricted access"
                },
                {
                    "path": "code",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Full code repository access"
                }
            ]

            for perm_data in permissions:
                response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=perm_data)
                assert response.status_code == 201

            # Test explanation quality
            test_paths = [
                "docs/readme.md",
                "docs/sensitive/secrets.txt",
                "code/main.py",
                "unmatched/file.txt"
            ]

            batch_request = {"paths": test_paths}
            response = client.post(
                f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                json=batch_request
            )
            assert response.status_code == 200

            results = response.json()["results"]
            results_by_path = {r["path"]: r for r in results}

            # Verify docs/readme.md explanation
            docs_result = results_by_path["docs/readme.md"]
            assert docs_result["matchedRule"]["description"] == "Documentation access for team members"
            assert docs_result["matchedRule"]["path"] == "docs"

            # Verify docs/sensitive/secrets.txt explanation (should match more specific deny rule)
            sensitive_result = results_by_path["docs/sensitive/secrets.txt"]
            assert sensitive_result["matchedRule"]["description"] == "Sensitive documents - restricted access"
            assert sensitive_result["matchedRule"]["rule_type"] == "deny"
            assert sensitive_result["status"] == "none"

            # Verify code/main.py explanation
            code_result = results_by_path["code/main.py"]
            assert code_result["matchedRule"]["description"] == "Full code repository access"
            assert code_result["status"] == "write"

            # Verify unmatched path has no rule
            unmatched_result = results_by_path["unmatched/file.txt"]
            assert unmatched_result["matchedRule"] is None
            assert unmatched_result["status"] == "none"

        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])