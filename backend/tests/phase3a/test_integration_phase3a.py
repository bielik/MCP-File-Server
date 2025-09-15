"""
Integration tests for Phase 3A database migration.

This test module validates the complete end-to-end functionality of Phase 3A,
including full workflow from migration through workspace activation to
MCP tool execution with database-backed permissions.
"""

import pytest
import json
from typing import Dict, Any, List
from fastapi.testclient import TestClient

from .conftest import (
    DatabaseTestHelper, create_test_workspace, create_test_permission,
    API_ENDPOINTS, PERFORMANCE_THRESHOLDS, PerformanceTimer,
    validate_batch_response, validate_matched_rule
)


class TestPhase3AEndToEndWorkflow:
    """Test complete Phase 3A workflow from start to finish."""

    def test_complete_workspace_creation_activation_workflow(self, client: TestClient):
        """Test complete workflow: create workspace → add permissions → activate → test access."""
        # Step 1: Create workspace
        workspace_data = {
            "name": "E2E Test Workspace",
            "description": "End-to-end testing workspace for Phase 3A",
            "is_active": False
        }

        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        # Step 2: Add complex permission rules
        permissions_data = [
            {
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Allow read access to materials"
            },
            {
                "path": "projects",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Allow write access to projects"
            },
            {
                "path": "materials/confidential",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Block confidential materials"
            },
            {
                "path": "logs",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Read-only log access"
            }
        ]

        created_permissions = []
        for permission_data in permissions_data:
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )
            assert response.status_code == 201
            created_permissions.append(response.json())

        # Step 3: Verify permissions were created correctly
        permissions_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        )
        assert permissions_response.status_code == 200
        permissions_data_response = permissions_response.json()
        assert isinstance(permissions_data_response, dict)
        assert "permissions" in permissions_data_response
        permissions_list = permissions_data_response["permissions"]
        assert len(permissions_list) == len(permissions_data)

        # Step 4: Activate workspace
        activation_response = client.post(
            API_ENDPOINTS["workspace_activate"].format(id=workspace["id"])
        )
        assert activation_response.status_code == 200

        # Step 5: Verify workspace is active
        workspace_detail_response = client.get(
            API_ENDPOINTS["workspace_detail"].format(id=workspace["id"])
        )
        updated_workspace = workspace_detail_response.json()
        assert updated_workspace["is_active"] is True

        # Step 6: Test batch effective permissions
        test_paths = [
            "/materials/docs/readme.txt",
            "/materials/confidential/secrets.txt",
            "/projects/app/main.py",
            "/logs/server.log",
            "/forbidden/file.txt"
        ]

        batch_request = {"paths": test_paths}
        batch_response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert batch_response.status_code == 200
        batch_data = batch_response.json()
        assert validate_batch_response(batch_data)

        results = batch_data["results"]
        assert len(results) == len(test_paths)

        # Verify expected permissions
        expected_results = {
            "/materials/docs/readme.txt": "read",
            "/materials/confidential/secrets.txt": "denied",
            "/projects/app/main.py": "write",
            "/logs/server.log": "read",
            "/forbidden/file.txt": "denied"
        }

        for result in results:
            path = result["path"]
            expected_status = expected_results[path]
            assert result["status"] == expected_status

            if expected_status != "denied":
                assert result["matched_rule"] is not None
                assert validate_matched_rule(result["matched_rule"])

    def test_migration_to_database_workflow(self, client: TestClient, temp_config_file: str,
                                           migration_config_data: Dict[str, Any]):
        """Test migration from config file to database workflow."""
        # This test simulates the migration process
        # In actual implementation, this would call the migration script

        # Step 1: Simulate migration by creating workspace with migrated data
        migrated_workspace_data = {
            "name": "Migrated Configuration Workspace",
            "description": f"Migrated from {temp_config_file}",
            "is_active": False
        }

        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=migrated_workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        # Step 2: Create permissions from config data
        for rule in migration_config_data["rules"]:
            permission_data = {
                "path": rule["path"],
                "permission_type": rule["permission_type"],
                "rule_type": rule["rule_type"],
                "description": rule.get("description", "Migrated from config file")
            }

            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )
            assert response.status_code == 201

        # Step 3: Verify migration completeness
        permissions_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        )
        permissions_data = permissions_response.json()
        assert len(permissions_data["permissions"]) == len(migration_config_data["rules"])

        # Step 4: Activate migrated workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Step 5: Test that migrated permissions work correctly
        test_cases = [
            ("/materials/doc.txt", "read", True),  # Should be allowed
            ("/projects/file.py", "write", True),  # Should be allowed
            ("/materials/01_Introduction to Software Engineering/module.txt", "read", False),  # Should be denied
            ("/data/exports/report.csv", "read", True),  # Should be allowed
            ("/config/sensitive/secrets.json", "read", False),  # Should be denied
        ]

        test_paths = [case[0] for case in test_cases]
        batch_request = {"paths": test_paths}
        batch_response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert batch_response.status_code == 200
        batch_data = batch_response.json()
        results = batch_data["results"]

        for (test_path, operation, expected), result in zip(test_cases, results):
            assert result["path"] == test_path
            if expected and operation == "write":
                assert result["status"] == "write"
            elif expected and operation == "read":
                assert result["status"] in ["read", "write"]  # Write implies read
            else:
                assert result["status"] == "denied"

    def test_multi_workspace_isolation(self, client: TestClient):
        """Test that multiple workspaces are properly isolated."""
        # Create two workspaces with different permissions
        workspace1_data = {
            "name": "Development Workspace",
            "description": "For development tasks",
            "is_active": False
        }

        workspace2_data = {
            "name": "Production Workspace",
            "description": "For production monitoring",
            "is_active": False
        }

        # Create workspaces
        ws1_response = client.post(API_ENDPOINTS["workspaces"], json=workspace1_data)
        ws2_response = client.post(API_ENDPOINTS["workspaces"], json=workspace2_data)

        workspace1 = ws1_response.json()
        workspace2 = ws2_response.json()

        # Add different permissions to each workspace
        ws1_permissions = [
            {
                "path": "development",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Development access"
            },
            {
                "path": "production",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Block prod access in dev workspace"
            }
        ]

        ws2_permissions = [
            {
                "path": "production",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Production monitoring"
            },
            {
                "path": "development",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Block dev access in prod workspace"
            }
        ]

        # Add permissions to workspace1
        for perm in ws1_permissions:
            client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace1["id"]),
                json=perm
            )

        # Add permissions to workspace2
        for perm in ws2_permissions:
            client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace2["id"]),
                json=perm
            )

        # Test workspace1 permissions
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace1["id"]))

        test_paths = ["/development/code.py", "/production/logs.txt"]
        batch_request = {"paths": test_paths}
        batch_response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace1["id"]),
            json=batch_request
        )

        results1 = batch_response.json()["results"]
        dev_result1 = next(r for r in results1 if r["path"] == "/development/code.py")
        prod_result1 = next(r for r in results1 if r["path"] == "/production/logs.txt")

        assert dev_result1["status"] == "write"
        assert prod_result1["status"] == "denied"

        # Test workspace2 permissions
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace2["id"]))

        batch_response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace2["id"]),
            json=batch_request
        )

        results2 = batch_response.json()["results"]
        dev_result2 = next(r for r in results2 if r["path"] == "/development/code.py")
        prod_result2 = next(r for r in results2 if r["path"] == "/production/logs.txt")

        assert dev_result2["status"] == "denied"
        assert prod_result2["status"] == "read"


class TestPhase3APerformanceIntegration:
    """Test performance characteristics of Phase 3A integration."""

    def test_large_workspace_performance(self, client: TestClient, performance_timer: PerformanceTimer):
        """Test performance with large workspace containing many permissions."""
        # Create workspace
        workspace_data = {
            "name": "Large Performance Workspace",
            "description": "Testing performance with many permissions",
            "is_active": False
        }

        workspace_response = client.post(API_ENDPOINTS["workspaces"], json=workspace_data)
        workspace = workspace_response.json()

        # Create many permissions (simulate complex organization structure)
        departments = ["engineering", "marketing", "sales"]
        permission_count = 0

        for dept in departments:
            for team_num in range(5):
                for access_level in ["read", "write"]:
                    permission_data = {
                        "path": f"{dept}/team{team_num}",
                        "permission_type": access_level,
                        "rule_type": "allow",
                        "description": f"{access_level.title()} access for {dept} team {team_num}"
                    }

                    response = client.post(
                        API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                        json=permission_data
                    )
                    assert response.status_code == 201
                    permission_count += 1

        assert permission_count == 30  # 3 depts * 5 teams * 2 access levels

        # Activate workspace (this should rebuild cache)
        with performance_timer:
            response = client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        assert response.status_code == 200
        # Activation should be fast even with many permissions
        assert performance_timer.elapsed_ms < 200

        # Test batch permissions performance
        test_paths = [f"/{dept}/team{i}/file.txt" for dept in departments for i in range(5)]

        batch_request = {"paths": test_paths}

        with performance_timer:
            batch_response = client.post(
                API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
                json=batch_request
            )

        assert batch_response.status_code == 200
        # Batch operation should meet performance threshold
        assert performance_timer.elapsed_ms < PERFORMANCE_THRESHOLDS["batch_api_1000_paths_ms"]

        batch_data = batch_response.json()
        assert len(batch_data["results"]) == len(test_paths)

    def test_complex_precedence_performance(self, client: TestClient, performance_timer: PerformanceTimer):
        """Test performance with complex nested precedence rules."""
        workspace_data = {
            "name": "Complex Precedence Workspace",
            "description": "Testing complex rule precedence performance",
            "is_active": False
        }

        workspace_response = client.post(API_ENDPOINTS["workspaces"], json=workspace_data)
        workspace = workspace_response.json()

        # Create nested permissions with complex precedence
        base_path = "organization"

        # Create hierarchical structure: organization/dept/team/project/module
        hierarchy_levels = ["dept1", "team1", "project1", "module1"]
        rule_count = 0

        for level in range(len(hierarchy_levels)):
            path_parts = [base_path] + hierarchy_levels[:level + 1]
            path = "/".join(path_parts)

            # Create both allow and deny rules at each level
            for rule_type in ["allow", "deny"]:
                for permission_type in ["read", "write"]:
                    permission_data = {
                        "path": path,
                        "permission_type": permission_type,
                        "rule_type": rule_type,
                        "description": f"Level {level} {rule_type} {permission_type} rule"
                    }

                    client.post(
                        API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                        json=permission_data
                    )
                    rule_count += 1

        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test performance with paths that require complex precedence resolution
        deep_paths = [
            "/organization/dept1/team1/project1/module1/file.txt",
            "/organization/dept1/team1/project1/file.txt",
            "/organization/dept1/team1/file.txt",
            "/organization/dept1/file.txt",
            "/organization/file.txt"
        ]

        batch_request = {"paths": deep_paths * 20}  # 100 paths total

        with performance_timer:
            batch_response = client.post(
                API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
                json=batch_request
            )

        assert batch_response.status_code == 200
        # Should handle complex precedence efficiently
        assert performance_timer.elapsed_ms < 100  # 100ms for complex precedence resolution

        batch_data = batch_response.json()
        assert len(batch_data["results"]) == 100


class TestPhase3ADataConsistency:
    """Test data consistency and integrity in Phase 3A."""

    def test_workspace_permission_consistency(self, client: TestClient):
        """Test that workspace-permission relationships remain consistent."""
        # Create workspace
        workspace_data = {
            "name": "Consistency Test Workspace",
            "description": "Testing data consistency",
            "is_active": False
        }

        workspace_response = client.post(API_ENDPOINTS["workspaces"], json=workspace_data)
        workspace = workspace_response.json()

        # Add permissions
        permissions_data = [
            {
                "path": "test1",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Test permission 1"
            },
            {
                "path": "test2",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Test permission 2"
            }
        ]

        created_permissions = []
        for perm_data in permissions_data:
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=perm_data
            )
            created_permissions.append(response.json())

        # Verify workspace-permission relationships
        for permission in created_permissions:
            assert permission["workspace_id"] == workspace["id"]

            # Verify individual permission retrieval
            perm_response = client.get(
                API_ENDPOINTS["permission_detail"].format(id=permission["id"])
            )
            assert perm_response.status_code == 200
            perm_detail = perm_response.json()
            assert perm_detail["workspace_id"] == workspace["id"]

        # Verify workspace permissions list
        workspace_permissions_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        ).json()

        assert len(workspace_permissions_response["permissions"]) == len(permissions_data)
        for perm in workspace_permissions_response["permissions"]:
            assert perm["workspace_id"] == workspace["id"]

    def test_cascade_deletion_consistency(self, client: TestClient):
        """Test that cascade deletion maintains consistency."""
        # Create workspace with permissions
        workspace_data = {
            "name": "Cascade Test Workspace",
            "description": "Testing cascade deletion",
            "is_active": False
        }

        workspace_response = client.post(API_ENDPOINTS["workspaces"], json=workspace_data)
        workspace = workspace_response.json()

        # Add multiple permissions
        permission_ids = []
        for i in range(5):
            permission_data = {
                "path": f"test{i}",
                "permission_type": "read",
                "rule_type": "allow",
                "description": f"Test permission {i}"
            }

            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )
            permission_ids.append(response.json()["id"])

        # Verify permissions exist
        for perm_id in permission_ids:
            response = client.get(API_ENDPOINTS["permission_detail"].format(id=perm_id))
            assert response.status_code == 200

        # Delete workspace
        delete_response = client.delete(
            API_ENDPOINTS["workspace_detail"].format(id=workspace["id"])
        )
        assert delete_response.status_code == 204

        # Verify workspace is deleted
        workspace_response = client.get(
            API_ENDPOINTS["workspace_detail"].format(id=workspace["id"])
        )
        assert workspace_response.status_code == 404

        # Verify permissions are also deleted (cascade)
        for perm_id in permission_ids:
            response = client.get(API_ENDPOINTS["permission_detail"].format(id=perm_id))
            assert response.status_code == 404

    def test_concurrent_workspace_operations(self, client: TestClient):
        """Test handling of concurrent workspace operations."""
        # This test simulates concurrent operations that might occur
        # in a multi-user environment

        # Create workspace
        workspace_data = {
            "name": "Concurrent Test Workspace",
            "description": "Testing concurrent operations",
            "is_active": False
        }

        workspace_response = client.post(API_ENDPOINTS["workspaces"], json=workspace_data)
        workspace = workspace_response.json()

        # Simulate concurrent permission additions
        # (In real implementation, this would involve threading)
        permission_ids = []
        for i in range(10):
            permission_data = {
                "path": f"concurrent{i}",
                "permission_type": "read" if i % 2 == 0 else "write",
                "rule_type": "allow",
                "description": f"Concurrent permission {i}"
            }

            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )
            assert response.status_code == 201
            permission_ids.append(response.json()["id"])

        # Verify all permissions were created successfully
        workspace_permissions_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        ).json()

        assert len(workspace_permissions_response["permissions"]) == 10

        # Verify no duplicate permissions were created
        permission_paths = [p["path"] for p in workspace_permissions_response["permissions"]]
        assert len(set(permission_paths)) == len(permission_paths)  # All unique

    def test_activation_state_consistency(self, client: TestClient):
        """Test that workspace activation state is consistent."""
        # Create multiple workspaces
        workspaces = []
        for i in range(3):
            workspace_data = {
                "name": f"Activation Test Workspace {i}",
                "description": f"Testing activation consistency {i}",
                "is_active": False
            }

            response = client.post(API_ENDPOINTS["workspaces"], json=workspace_data)
            workspaces.append(response.json())

        # Verify all are initially inactive
        for workspace in workspaces:
            response = client.get(API_ENDPOINTS["workspace_detail"].format(id=workspace["id"]))
            workspace_detail = response.json()
            assert workspace_detail["is_active"] is False

        # Activate middle workspace
        activation_response = client.post(
            API_ENDPOINTS["workspace_activate"].format(id=workspaces[1]["id"])
        )
        assert activation_response.status_code == 200

        # Verify only middle workspace is active
        for i, workspace in enumerate(workspaces):
            response = client.get(API_ENDPOINTS["workspace_detail"].format(id=workspace["id"]))
            workspace_detail = response.json()

            if i == 1:
                assert workspace_detail["is_active"] is True
            else:
                assert workspace_detail["is_active"] is False

        # Activate different workspace
        activation_response = client.post(
            API_ENDPOINTS["workspace_activate"].format(id=workspaces[2]["id"])
        )
        assert activation_response.status_code == 200

        # Verify only last workspace is active
        for i, workspace in enumerate(workspaces):
            response = client.get(API_ENDPOINTS["workspace_detail"].format(id=workspace["id"]))
            workspace_detail = response.json()

            if i == 2:
                assert workspace_detail["is_active"] is True
            else:
                assert workspace_detail["is_active"] is False


class TestPhase3AErrorRecovery:
    """Test error recovery and resilience in Phase 3A."""

    def test_invalid_permission_recovery(self, client: TestClient):
        """Test system recovery from invalid permission operations."""
        # Create workspace
        workspace_data = {
            "name": "Error Recovery Test",
            "description": "Testing error recovery",
            "is_active": False
        }

        workspace_response = client.post(API_ENDPOINTS["workspaces"], json=workspace_data)
        workspace = workspace_response.json()

        # Add valid permission
        valid_permission = {
            "path": "valid/path",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Valid permission"
        }

        response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=valid_permission
        )
        assert response.status_code == 201
        valid_perm = response.json()

        # Attempt invalid permission operations
        invalid_operations = [
            # Invalid permission data
            {
                "path": "",  # Empty path
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Invalid empty path"
            },
            # Invalid permission type
            {
                "path": "test/path",
                "permission_type": "invalid",
                "rule_type": "allow",
                "description": "Invalid permission type"
            }
        ]

        for invalid_perm in invalid_operations:
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=invalid_perm
            )
            assert response.status_code == 422  # Should fail validation

        # Verify valid permission still exists and works
        permissions_response = client.get(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"])
        )
        permissions_data = permissions_response.json()
        assert len(permissions_data["permissions"]) == 1  # Only the valid permission
        assert permissions_data["permissions"][0]["id"] == valid_perm["id"]

        # Test that valid permission still works after error attempts
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        batch_request = {"paths": ["/valid/path/file.txt"]}
        batch_response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert batch_response.status_code == 200
        results = batch_response.json()["results"]
        assert results[0]["status"] == "read"

    def test_workspace_deletion_with_active_state(self, client: TestClient):
        """Test handling of active workspace deletion."""
        # Create and activate workspace
        workspace_data = {
            "name": "Active Deletion Test",
            "description": "Testing deletion of active workspace",
            "is_active": False
        }

        workspace_response = client.post(API_ENDPOINTS["workspaces"], json=workspace_data)
        workspace = workspace_response.json()

        # Add permission
        permission_data = {
            "path": "test",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Test permission"
        }

        client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission_data
        )

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Verify workspace is active
        active_workspace = client.get(
            API_ENDPOINTS["workspace_detail"].format(id=workspace["id"])
        ).json()
        assert active_workspace["is_active"] is True

        # Delete active workspace
        delete_response = client.delete(
            API_ENDPOINTS["workspace_detail"].format(id=workspace["id"])
        )
        assert delete_response.status_code == 204

        # Verify workspace is deleted
        response = client.get(API_ENDPOINTS["workspace_detail"].format(id=workspace["id"]))
        assert response.status_code == 404

        # Verify system handles no active workspace gracefully
        # (This would depend on implementation - might set another workspace as active
        # or handle the no-active-workspace state gracefully)