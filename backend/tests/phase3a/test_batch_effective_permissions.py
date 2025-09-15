"""
Test batch effective permissions API for Phase 3A.

This test module validates the cornerstone API endpoint that will be used by
the UI to efficiently fetch permission statuses and matched rule explanations
for multiple paths simultaneously.
"""

import os
import pytest
from typing import Dict, Any, List
from fastapi.testclient import TestClient

from .conftest import (
    DatabaseTestHelper, validate_batch_response, validate_matched_rule,
    API_ENDPOINTS, PERFORMANCE_THRESHOLDS, PerformanceTimer
)


class TestBatchEffectivePermissionsBasic:
    """Test basic batch effective permissions functionality."""

    def test_batch_permissions_empty_request(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test batch request with empty paths list."""
        # Create and activate workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()

        response = client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))
        assert response.status_code == 200

        # Test empty batch request
        batch_request = {"paths": []}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        assert validate_batch_response(batch_data)
        assert batch_data["results"] == []

    def test_batch_permissions_single_path(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test batch request with single path."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create a permission rule
        permission_data = {
            "path": "materials",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Allow read access to materials"
        }

        permission_response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission_data
        )
        assert permission_response.status_code == 201
        created_permission = permission_response.json()

        # Activate workspace
        response = client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))
        assert response.status_code == 200

        # Test single path batch request
        batch_request = {"paths": ["/materials/docs/readme.txt"]}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        assert validate_batch_response(batch_data)

        results = batch_data["results"]
        assert len(results) == 1

        result = results[0]
        assert result["path"] == "/materials/docs/readme.txt"
        assert result["status"] == "read"  # Should have read access
        assert "matched_rule" in result
        assert validate_matched_rule(result["matched_rule"])
        assert result["matched_rule"]["id"] == f"db-rule-{created_permission['id']}"

    def test_batch_permissions_multiple_paths(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                             batch_paths_test_data: List[str]):
        """Test batch request with multiple paths."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create multiple permission rules
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
                "description": "Block access to confidential materials"
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

        # Activate workspace
        response = client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))
        assert response.status_code == 200

        # Test batch request
        batch_request = {"paths": batch_paths_test_data}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        assert validate_batch_response(batch_data)

        results = batch_data["results"]
        assert len(results) == len(batch_paths_test_data)

        # Validate each result
        result_paths = [r["path"] for r in results]
        for test_path in batch_paths_test_data:
            assert test_path in result_paths

        for result in results:
            assert "path" in result
            assert "status" in result
            assert result["status"] in ["read", "write", "denied"]

            if result["status"] != "denied":
                assert "matched_rule" in result
                assert validate_matched_rule(result["matched_rule"])
            else:
                # Denied access may have null matched_rule
                assert result.get("matched_rule") is None

    def test_batch_permissions_workspace_not_found(self, client: TestClient, batch_paths_test_data: List[str]):
        """Test batch request for non-existent workspace."""
        batch_request = {"paths": batch_paths_test_data}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=99999),
            json=batch_request
        )

        assert response.status_code == 404

    def test_batch_permissions_inactive_workspace(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                                 batch_paths_test_data: List[str]):
        """Test batch request for inactive workspace."""
        # Create workspace but don't activate it
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create permission
        permission_data = {
            "path": "materials",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Test permission"
        }

        client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission_data
        )

        # Test batch request on inactive workspace
        batch_request = {"paths": batch_paths_test_data}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        # Should either deny access or return error about inactive workspace
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            # If allowed, all paths should be denied
            batch_data = response.json()
            results = batch_data["results"]
            for result in results:
                assert result["status"] == "denied"


class TestBatchPermissionsPrecedenceLogic:
    """Test precedence logic in batch effective permissions."""

    def test_precedence_specificity_wins(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test that more specific rules override parent rules."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create parent and child rules
        permissions_data = [
            {
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Allow read access to materials (parent)"
            },
            {
                "path": "materials/confidential",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Block confidential materials (child - more specific)"
            }
        ]

        created_permissions = []
        for permission_data in permissions_data:
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )
            created_permissions.append(response.json())

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test paths at different levels
        test_cases = [
            {
                "path": "/materials/docs/readme.txt",
                "expected_status": "read",
                "expected_rule_id": f"db-rule-{created_permissions[0]['id']}"  # Parent rule
            },
            {
                "path": "/materials/confidential/secrets.txt",
                "expected_status": "denied",
                "expected_rule_id": f"db-rule-{created_permissions[1]['id']}"  # Child rule (deny)
            }
        ]

        batch_request = {"paths": [case["path"] for case in test_cases]}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]

        for i, case in enumerate(test_cases):
            result = next(r for r in results if r["path"] == case["path"])
            assert result["status"] == case["expected_status"]

            if case["expected_status"] != "denied":
                assert result["matched_rule"]["id"] == case["expected_rule_id"]

    def test_precedence_deny_wins_tie(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test that deny rules win over allow rules at same specificity."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create both allow and deny rules for same path
        permissions_data = [
            {
                "path": "materials/shared",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Allow access"
            },
            {
                "path": "materials/shared",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Deny access (should win)"
            }
        ]

        created_permissions = []
        for permission_data in permissions_data:
            response = client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )
            created_permissions.append(response.json())

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test path that matches both rules
        batch_request = {"paths": ["/materials/shared/document.txt"]}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]

        assert len(results) == 1
        result = results[0]
        assert result["status"] == "denied"  # Deny should win

    def test_precedence_write_implies_read(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test that write permission implicitly grants read access."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create write permission only
        permission_data = {
            "path": "projects",
            "permission_type": "write",
            "rule_type": "allow",
            "description": "Allow write access (implies read)"
        }

        response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission_data
        )
        created_permission = response.json()

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test path that should have both read and write access
        batch_request = {"paths": ["/projects/app/main.py"]}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]

        assert len(results) == 1
        result = results[0]
        assert result["status"] == "write"  # Should have write access (which implies read)
        assert result["matched_rule"]["id"] == f"db-rule-{created_permission['id']}"

    def test_precedence_default_deny(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test that paths with no matching rules are denied."""
        # Create workspace with limited permissions
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create permission for specific path only
        permission_data = {
            "path": "allowed",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Only allowed path"
        }

        client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission_data
        )

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test paths that should be denied (no matching rules)
        batch_request = {
            "paths": [
                "/forbidden/path/file.txt",
                "/another/blocked/path.txt",
                "/completely/different.txt"
            ]
        }

        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]

        assert len(results) == 3
        for result in results:
            assert result["status"] == "denied"
            assert result["matched_rule"] is None


class TestBatchPermissionsMatchedRules:
    """Test matched rule explanations in batch responses."""

    def test_matched_rule_structure(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test that matched rule contains all required fields."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create detailed permission
        permission_data = {
            "path": "detailed/test",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Detailed test permission with full metadata"
        }

        response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission_data
        )
        created_permission = response.json()

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test batch request
        batch_request = {"paths": ["/detailed/test/file.txt"]}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]

        assert len(results) == 1
        result = results[0]
        matched_rule = result["matched_rule"]

        # Validate matched rule structure
        assert validate_matched_rule(matched_rule)
        assert matched_rule["id"] == f"db-rule-{created_permission['id']}"
        # Accept either forward or backslashes (platform-dependent normalization)
        assert matched_rule["path"] in [permission_data["path"], permission_data["path"].replace('/', '\\')]
        assert matched_rule["rule_type"] == permission_data["rule_type"]
        assert matched_rule["permission_type"] == permission_data["permission_type"]
        assert matched_rule["description"] == permission_data["description"]

    def test_matched_rule_null_for_denied(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test that matched_rule is null for denied access."""
        # Create workspace with no permissions (everything denied by default)
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test paths with no permissions
        batch_request = {"paths": ["/denied/path/file.txt"]}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]

        assert len(results) == 1
        result = results[0]
        assert result["status"] == "denied"
        assert result["matched_rule"] is None

    def test_matched_rule_for_deny_rules(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test matched rule explanation for explicit deny rules."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create explicit deny rule
        permission_data = {
            "path": "blocked",
            "permission_type": "read",
            "rule_type": "deny",
            "description": "Explicitly blocked path"
        }

        response = client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission_data
        )
        created_permission = response.json()

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test blocked path
        batch_request = {"paths": ["/blocked/file.txt"]}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]

        assert len(results) == 1
        result = results[0]
        assert result["status"] == "denied"

        # For explicit deny rules, matched_rule should contain the deny rule details
        matched_rule = result.get("matched_rule")
        if matched_rule:  # Implementation may choose to include or exclude deny rule details
            assert matched_rule["id"] == f"db-rule-{created_permission['id']}"
            assert matched_rule["rule_type"] == "deny"


class TestBatchPermissionsPerformance:
    """Test performance characteristics of batch effective permissions."""

    def test_performance_large_batch(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                    large_batch_paths: List[str], performance_timer: PerformanceTimer):
        """Test performance with large batch (1000+ paths)."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create several broad permission rules
        permissions_data = [
            {
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Materials access"
            },
            {
                "path": "projects",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Projects access"
            },
            {
                "path": "private",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Private blocked"
            }
        ]

        for permission_data in permissions_data:
            client.post(
                API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                json=permission_data
            )

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test large batch performance
        batch_request = {"paths": large_batch_paths}

        with performance_timer:
            response = client.post(
                API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
                json=batch_request
            )

        assert response.status_code == 200
        assert performance_timer.elapsed_ms < PERFORMANCE_THRESHOLDS["batch_api_1000_paths_ms"]

        batch_data = response.json()
        results = batch_data["results"]
        assert len(results) == len(large_batch_paths)

    def test_performance_complex_rule_hierarchy(self, client: TestClient, sample_workspace_data: Dict[str, Any],
                                               performance_timer: PerformanceTimer):
        """Test performance with complex nested rule hierarchy."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create complex nested rules
        base_paths = ["docs", "code", "tests", "config"]
        rules_count = 0

        for base in base_paths:
            for i in range(5):  # 5 levels deep
                path_parts = [base]
                for j in range(i):
                    path_parts.append(f"level{j}")

                path = "/".join(path_parts)
                permission_data = {
                    "path": path,
                    "permission_type": "read" if rules_count % 2 == 0 else "write",
                    "rule_type": "allow" if rules_count % 3 != 0 else "deny",
                    "description": f"Rule {rules_count} for {path}"
                }

                client.post(
                    API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
                    json=permission_data
                )
                rules_count += 1

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Generate test paths that will match at various levels
        test_paths = []
        for base in base_paths:
            for i in range(10):
                path = f"/{base}/level0/level1/level2/file{i}.txt"
                test_paths.append(path)

        batch_request = {"paths": test_paths}

        with performance_timer:
            response = client.post(
                API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
                json=batch_request
            )

        assert response.status_code == 200
        # Should still be fast even with complex hierarchy
        assert performance_timer.elapsed_ms < 100  # 100ms for 40 paths with complex rules

        batch_data = response.json()
        results = batch_data["results"]
        assert len(results) == len(test_paths)


class TestBatchPermissionsEdgeCases:
    """Test edge cases for batch effective permissions."""

    def test_special_characters_in_paths(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test batch request with special characters in paths."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create permission for path with special characters
        permission_data = {
            "path": "special chars & symbols!",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Permission for special character path"
        }

        client.post(
            API_ENDPOINTS["workspace_permissions"].format(id=workspace["id"]),
            json=permission_data
        )

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Test paths with special characters
        special_paths = [
            "/special chars & symbols!/file.txt",
            "/path with spaces/file.txt",
            "/path-with-dashes/file.txt",
            "/path_with_underscores/file.txt",
            "/path.with.dots/file.txt",
            "/path@with@symbols/file.txt"
        ]

        batch_request = {"paths": special_paths}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]
        assert len(results) == len(special_paths)

        # First path should match the permission, others should be denied
        for i, result in enumerate(results):
            if i == 0:  # First path matches our permission
                assert result["status"] == "read"
            # Others may be denied (depending on path matching logic)

    def test_very_long_paths(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test batch request with very long paths."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Activate workspace
        client.post(API_ENDPOINTS["workspace_activate"].format(id=workspace["id"]))

        # Create very long path (1000 characters)
        long_path_segments = ["very"] * 100  # 100 segments of "very"
        long_path = "/" + "/".join(long_path_segments) + "/file.txt"

        batch_request = {"paths": [long_path]}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        # Should handle long paths gracefully
        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]
        assert len(results) == 1
        assert results[0]["path"] == long_path

    def test_duplicate_paths_in_request(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test batch request with duplicate paths."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Create permission
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

        # Test with duplicate paths
        duplicate_paths = [
            "/test/file.txt",
            "/test/file.txt",  # Duplicate
            "/other/file.txt",
            "/test/file.txt"   # Another duplicate
        ]

        batch_request = {"paths": duplicate_paths}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        assert response.status_code == 200
        batch_data = response.json()
        results = batch_data["results"]

        # Should return results for all paths (including duplicates)
        # or deduplicate them - both approaches are valid
        assert len(results) in [len(duplicate_paths), len(set(duplicate_paths))]


class TestBatchPermissionsErrorHandling:
    """Test error handling for batch effective permissions."""

    def test_invalid_request_format(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test batch request with invalid format."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Test invalid request formats
        invalid_requests = [
            {},  # Missing paths
            {"paths": "not_a_list"},  # paths should be list
            {"paths": [123, 456]},  # paths should be strings
            {"invalid": ["field"]},  # Wrong field name
        ]

        for invalid_request in invalid_requests:
            response = client.post(
                API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
                json=invalid_request
            )
            assert response.status_code == 422

    def test_request_size_limits(self, client: TestClient, sample_workspace_data: Dict[str, Any]):
        """Test batch request with too many paths."""
        # Create workspace
        workspace_response = client.post(
            API_ENDPOINTS["workspaces"],
            json=sample_workspace_data
        )
        workspace = workspace_response.json()

        # Generate extremely large batch (10000 paths)
        huge_batch_paths = [f"/path/to/file/{i}.txt" for i in range(10000)]

        batch_request = {"paths": huge_batch_paths}
        response = client.post(
            API_ENDPOINTS["batch_effective_permissions"].format(id=workspace["id"]),
            json=batch_request
        )

        # Should either succeed or fail gracefully with appropriate error
        assert response.status_code in [200, 413, 422]  # Success, payload too large, or validation error

        if response.status_code == 200:
            # If it succeeds, should return results for all paths
            batch_data = response.json()
            assert len(batch_data["results"]) == len(huge_batch_paths)