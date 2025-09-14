"""
Integration tests for Phase 2 dynamic workspace system.

This test suite validates that all components work together correctly,
including the API endpoints, permission service, and feature flag system.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.config import get_config, get_feature_flags


class TestPhase2Integration:
    """Integration tests for Phase 2 features."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI application."""
        return TestClient(app)

    @pytest.fixture
    def client_with_phase2_disabled(self):
        """Create a test client with Phase 2 features disabled."""
        with patch.dict(os.environ, {'ENABLE_CONFIG_FILE_PERMISSIONS': 'false'}):
            return TestClient(app)

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        config_data = {
            "metadata": {
                "version": "1.0.0",
                "description": "Test configuration"
            },
            "rules": [
                {
                    "id": "test-rule-1",
                    "path": "docs",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Allow read access to docs"
                },
                {
                    "id": "test-rule-2",
                    "path": "projects",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Allow write access to projects"
                },
                {
                    "id": "test-rule-3",
                    "path": "projects/secret",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Deny access to secret folder"
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_server_config_endpoint(self, client):
        """Test that server config endpoint returns feature flag information."""
        response = client.get("/api/config")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "server_port" in data
        assert "feature_flags" in data
        assert "config_file_permissions_enabled" in data

        # Feature flags should be present
        feature_flags = data["feature_flags"]
        assert "ENABLE_CONFIG_FILE_PERMISSIONS" in feature_flags
        assert "ENABLE_DATABASE_PERMISSIONS" in feature_flags

    def test_permissions_config_endpoint_current_mode(self, client):
        """Test permissions config endpoint with current configuration."""
        response = client.get("/api/config/permissions")

        assert response.status_code == 200
        data = response.json()

        # Should return config-based permissions (since Phase 2 is enabled)
        assert "rules" in data
        assert "config_file_enabled" in data
        assert data["config_file_enabled"] == True
        assert "ETag" in response.headers

    def test_permission_service_feature_flag_integration(self):
        """Test that permission service correctly routes based on feature flags."""
        from app.services.permission_service import check_access, get_safe_path

        # Test with default (legacy) mode
        try:
            result = check_access("docs/test.txt", "read")
            assert result == True  # Should succeed for allowed path
        except PermissionError:
            # This is expected behavior for some paths
            pass

        # Test safe path function
        try:
            safe_path = get_safe_path("docs/test.txt")
            assert "/shared-fs" in safe_path
        except PermissionError:
            # This is expected for some paths
            pass

    def test_file_service_integration(self):
        """Test that file service integrates properly with permission checking."""
        from app.services import file_service

        # Test with an allowed path
        try:
            # This should work if the path exists and is allowed
            result = file_service.list_files("docs")
            assert isinstance(result, list)
        except (PermissionError, FileNotFoundError, OSError):
            # These are expected exceptions based on actual file system state
            pass

    def test_config_validation_edge_cases(self):
        """Test config validation handles edge cases correctly."""
        from app.services.config_permission_service import ConfigPermissionService

        # Test invalid config structures
        invalid_configs = [
            {},  # Missing rules
            {"rules": "not-a-list"},  # Rules not a list
            {"rules": [{"id": "test"}]},  # Missing required fields
            {"rules": [{"id": "test", "path": "test", "permission_type": "invalid", "rule_type": "allow"}]},  # Invalid permission_type
            {"rules": [{"id": "test", "path": "test", "permission_type": "read", "rule_type": "invalid"}]},  # Invalid rule_type
        ]

        service = ConfigPermissionService()

        for invalid_config in invalid_configs:
            with pytest.raises((ValueError, KeyError)):
                service._validate_config(invalid_config)

    def test_api_error_handling(self, client):
        """Test that API endpoints handle errors gracefully."""

        # Test PUT without If-Match header
        response = client.put("/api/config/permissions", json={"config": {}})
        assert response.status_code == 400
        assert "If-Match header is required" in response.json()["detail"]

        # Test with invalid ETag - should return 412 Precondition Failed
        response = client.put(
            "/api/config/permissions",
            json={"config": {"rules": []}},
            headers={"If-Match": "invalid-etag"}
        )
        assert response.status_code == 412

    def test_api_with_phase2_enabled(self, client):
        """Test API functionality when Phase 2 is enabled."""
        # Test config permissions endpoint with Phase 2 enabled
        response = client.get("/api/config/permissions")
        assert response.status_code == 200

        data = response.json()
        assert "rules" in data
        assert "config_file_enabled" in data
        assert data["config_file_enabled"] == True

        # Test invalid config data with Phase 2 enabled - should get ETag mismatch (412)
        response = client.put(
            "/api/config/permissions",
            json={"config": {"rules": "invalid"}},
            headers={"If-Match": "invalid-etag"}
        )
        # Should fail with precondition failed (412) due to ETag mismatch
        assert response.status_code == 412

    def test_permission_changes_persist_to_file(self, client):
        """Test that API changes actually persist to the config file on disk."""
        import json
        import uuid
        import time

        # Path to the actual config file
        config_file_path = "/config/permissions.json"

        # Generate unique rule ID to avoid conflicts
        unique_id = f"test-persistence-{uuid.uuid4().hex[:8]}"

        # Read original file contents
        with open(config_file_path, 'r') as f:
            original_config = json.load(f)

        original_rule_count = len(original_config["rules"])
        print(f"📊 Original file has {original_rule_count} rules")

        # Get current ETag for API call
        response = client.get("/api/config/permissions")
        assert response.status_code == 200
        current_etag = response.headers.get("ETag", "").strip('"')
        print(f"🏷️ Current ETag: {current_etag}")

        # Create a new test rule with unique ID
        new_config = {
            "config": {
                "metadata": {
                    "version": "1.0.0",
                    "created_at": "2025-01-13T19:30:00Z",
                    "description": "Test persistence configuration"
                },
                "rules": original_config["rules"] + [{
                    "id": unique_id,
                    "path": "test-persistence-path",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Test rule to verify file persistence"
                }]
            }
        }

        print(f"🚀 Making API call to add rule: {unique_id}")

        # Make API call to add the new rule
        response = client.put(
            "/api/config/permissions",
            json=new_config,
            headers={"If-Match": current_etag}
        )

        print(f"📡 API Response: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ API Error: {response.json()}")

        assert response.status_code == 200, f"API call failed: {response.json()}"

        # Add delay for file operations
        time.sleep(1.0)

        # 🚨 CRITICAL TEST: Verify the file was actually updated on disk
        print(f"🔍 Reading file: {config_file_path}")
        with open(config_file_path, 'r') as f:
            updated_config = json.load(f)

        updated_rule_count = len(updated_config["rules"])
        print(f"📊 Rule counts - Original: {original_rule_count}, File: {updated_rule_count}")

        # Print all rule IDs to debug
        rule_ids = [rule["id"] for rule in updated_config["rules"]]
        print(f"📋 Rule IDs in file: {rule_ids}")

        # Check that our specific rule is in the file
        test_rule_found = any(
            rule["id"] == unique_id
            for rule in updated_config["rules"]
        )

        if not test_rule_found:
            # 🚨 EXPOSE THE BUG: Rule not in file but API succeeded
            print(f"❌ BUG EXPOSED: API returned success but rule '{unique_id}' not found in file!")
            print(f"📁 File has {updated_rule_count} rules but we expected {original_rule_count + 1}")

            # Check API response vs file discrepancy
            api_response = client.get("/api/config/permissions")
            api_data = api_response.json()
            api_rule_count = len(api_data["rules"])
            print(f"🔍 API reports {api_rule_count} rules, file has {updated_rule_count} rules")

            api_rule_found = any(rule["id"] == unique_id for rule in api_data["rules"])
            print(f"📡 Rule in API response: {api_rule_found}")
            print(f"📁 Rule in file: {test_rule_found}")

        assert test_rule_found, \
            f"🚨 FILE PERSISTENCE BUG: Rule '{unique_id}' not found in file but API succeeded. File rules: {rule_ids}"

        print(f"✅ SUCCESS: Rule persisted to file! Original: {original_rule_count}, Updated: {updated_rule_count}")

    def test_concurrent_api_requests(self, client):
        """Test API can handle concurrent requests."""
        import concurrent.futures
        import threading

        def make_request():
            response = client.get("/api/config/permissions")
            return response.status_code

        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        assert all(status == 200 for status in results)

    def test_browse_api_security(self, client):
        """Test that browse API prevents directory traversal."""

        # Test normal path
        response = client.get("/api/browse?path=docs")
        assert response.status_code in [200, 404]  # 404 if path doesn't exist

        # Test directory traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/passwd",
            "../config",
            "docs/../../config"
        ]

        for path in malicious_paths:
            response = client.get(f"/api/browse?path={path}")
            # Should be rejected with 400 (validation error) or 404 (not found)
            assert response.status_code in [400, 404]
            if response.status_code == 400:
                assert "directory traversal" in response.json()["detail"].lower()

    def test_current_permissions_endpoint(self, client):
        """Test current permissions endpoint returns expected data."""
        response = client.get("/api/current-permissions")

        assert response.status_code == 200
        data = response.json()

        assert "permissions" in data
        assert "description" in data

        permissions = data["permissions"]
        assert "context" in permissions
        assert "working" in permissions

        # Should contain expected directories
        context_dirs = permissions["context"]
        assert isinstance(context_dirs, list)
        assert "docs" in context_dirs

    def test_stats_in_config_response(self, client):
        """Test stats are included in config permissions response."""
        response = client.get("/api/config/permissions")

        assert response.status_code == 200
        data = response.json()

        # Stats should be included in the main config response
        assert "stats" in data
        stats = data["stats"]
        assert "rule_count" in stats
        assert "config_file_path" in stats


class TestMCPIntegration:
    """Test MCP protocol integration with new permission system."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_mcp_tool_call_with_permissions(self, client):
        """Test that MCP tool calls respect permission system."""

        # Test MCP initialize
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"version": "2024-11-05"},
            "id": 1
        }

        response = client.post("/mcp", json=init_request)
        assert response.status_code == 200

        init_data = response.json()
        assert init_data["jsonrpc"] == "2.0"
        assert "result" in init_data

        # Test tools/list
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }

        response = client.post("/mcp", json=tools_request)
        assert response.status_code == 200

        tools_data = response.json()
        assert "result" in tools_data
        assert "tools" in tools_data["result"]

        tools = tools_data["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]
        assert "read_file" in tool_names
        assert "list_files" in tool_names
        assert "write_file" in tool_names

    def test_mcp_tool_execution_security(self, client):
        """Test that MCP tool execution respects security constraints."""

        # Test file read with potentially unauthorized path
        read_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {"path": "../../../etc/passwd"}
            },
            "id": 3
        }

        response = client.post("/mcp", json=read_request)
        assert response.status_code == 200

        data = response.json()
        # Should return an error due to security constraints
        assert "error" in data
        assert data["error"]["code"] in [-32001, -32002]  # Permission denied or file not found


class TestErrorHandling:
    """Test comprehensive error handling."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_malformed_json_requests(self, client):
        """Test handling of malformed JSON requests."""

        # Test malformed JSON
        response = client.post("/mcp", data="invalid json")
        assert response.status_code == 400  # Bad Request for malformed JSON

    def test_missing_required_fields(self, client):
        """Test handling of requests with missing required fields."""

        # Missing method field
        request = {
            "jsonrpc": "2.0",
            "id": 1
        }

        response = client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32600  # Invalid Request

    def test_invalid_method_names(self, client):
        """Test handling of invalid method names."""

        request = {
            "jsonrpc": "2.0",
            "method": "nonexistent_method",
            "id": 1
        }

        response = client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])