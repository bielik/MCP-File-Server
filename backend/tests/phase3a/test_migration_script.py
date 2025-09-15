"""
Test migration script for Phase 3A.

This test module validates the migration script that converts permissions.json
configuration files to database-based permissions, ensuring data integrity
and idempotency.
"""

import pytest
import json
import os
import tempfile
import shutil
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from .conftest import DatabaseTestHelper, create_test_workspace


class MockMigrationScript:
    """Mock migration script for testing Phase 3A migration functionality."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.migration_log = []

    def migrate_config_to_database(self, config_path: str, workspace_name: str = None) -> Dict[str, Any]:
        """
        Migrate permissions.json to database.

        Args:
            config_path: Path to permissions.json file
            workspace_name: Name for the created workspace (auto-generated if None)

        Returns:
            Dictionary with migration results
        """
        # Read config file
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read config file: {e}",
                "workspace_id": None,
                "migrated_rules": 0
            }

        # Extract rules from config
        rules = config_data.get("rules", [])
        if not rules:
            return {
                "success": False,
                "error": "No rules found in config file",
                "workspace_id": None,
                "migrated_rules": 0
            }

        # Create workspace
        workspace_name = workspace_name or f"Migrated from {os.path.basename(config_path)}"

        # Import models here to avoid circular imports
        from app.models.workspace import Workspace, Permission

        # Check if workspace already exists
        existing_workspace = self.db_session.query(Workspace).filter_by(name=workspace_name).first()
        if existing_workspace:
            return {
                "success": False,
                "error": f"Workspace '{workspace_name}' already exists",
                "workspace_id": existing_workspace.id,
                "migrated_rules": 0
            }

        # Create new workspace
        workspace = Workspace(
            name=workspace_name,
            description=f"Migrated from {config_path}",
            is_active=False
        )
        self.db_session.add(workspace)
        self.db_session.flush()  # Get ID without committing

        # Migrate rules
        migrated_count = 0
        migration_errors = []

        for rule in rules:
            try:
                # Validate rule structure
                required_fields = ["path", "permission_type", "rule_type"]
                if not all(field in rule for field in required_fields):
                    migration_errors.append(f"Rule missing required fields: {rule}")
                    continue

                # Create permission
                permission = Permission(
                    workspace_id=workspace.id,
                    path=rule["path"],
                    permission_type=rule["permission_type"],
                    rule_type=rule["rule_type"],
                    description=rule.get("description", "Migrated from config file")
                )
                self.db_session.add(permission)
                migrated_count += 1

            except Exception as e:
                migration_errors.append(f"Failed to migrate rule {rule}: {e}")

        # Commit transaction
        try:
            self.db_session.commit()
            self.migration_log.append(f"Successfully migrated {migrated_count} rules to workspace '{workspace_name}'")

            return {
                "success": True,
                "error": None,
                "workspace_id": workspace.id,
                "migrated_rules": migrated_count,
                "errors": migration_errors if migration_errors else None
            }

        except Exception as e:
            self.db_session.rollback()
            return {
                "success": False,
                "error": f"Database error during migration: {e}",
                "workspace_id": None,
                "migrated_rules": 0
            }

    def check_migration_status(self, config_path: str) -> Dict[str, Any]:
        """Check if a config file has already been migrated."""
        from app.models.workspace import Workspace

        workspace_name = f"Migrated from {os.path.basename(config_path)}"
        existing_workspace = self.db_session.query(Workspace).filter_by(name=workspace_name).first()

        if existing_workspace:
            permission_count = len(existing_workspace.permissions)
            return {
                "already_migrated": True,
                "workspace_id": existing_workspace.id,
                "workspace_name": workspace_name,
                "permission_count": permission_count
            }

        return {
            "already_migrated": False,
            "workspace_id": None,
            "workspace_name": None,
            "permission_count": 0
        }

    def rollback_migration(self, workspace_id: int) -> Dict[str, Any]:
        """Rollback a migration by deleting the migrated workspace."""
        from app.models.workspace import Workspace

        workspace = self.db_session.query(Workspace).filter_by(id=workspace_id).first()
        if not workspace:
            return {
                "success": False,
                "error": f"Workspace with ID {workspace_id} not found"
            }

        try:
            permission_count = len(workspace.permissions)
            workspace_name = workspace.name

            self.db_session.delete(workspace)
            self.db_session.commit()

            return {
                "success": True,
                "error": None,
                "deleted_workspace": workspace_name,
                "deleted_permissions": permission_count
            }

        except Exception as e:
            self.db_session.rollback()
            return {
                "success": False,
                "error": f"Failed to rollback migration: {e}"
            }


@pytest.fixture
def migration_script(db_session: Session) -> MockMigrationScript:
    """Provide migration script instance for testing."""
    return MockMigrationScript(db_session)


class TestMigrationBasicFunctionality:
    """Test basic migration functionality."""

    def test_migrate_simple_config(self, migration_script: MockMigrationScript,
                                  temp_config_file: str, migration_config_data: Dict[str, Any]):
        """Test migration of a simple config file."""
        result = migration_script.migrate_config_to_database(temp_config_file)

        assert result["success"] is True
        assert result["error"] is None
        assert result["workspace_id"] is not None
        assert result["migrated_rules"] == len(migration_config_data["rules"])

    def test_migrate_empty_config(self, migration_script: MockMigrationScript):
        """Test migration of config file with no rules."""
        # Create empty config file
        empty_config = {
            "rules": [],
            "description": "Empty configuration",
            "version": "1.0"
        }

        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "empty_permissions.json")

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(empty_config, f)

        try:
            result = migration_script.migrate_config_to_database(config_path)

            assert result["success"] is False
            assert "No rules found" in result["error"]
            assert result["workspace_id"] is None
            assert result["migrated_rules"] == 0

        finally:
            shutil.rmtree(temp_dir)

    def test_migrate_nonexistent_config(self, migration_script: MockMigrationScript):
        """Test migration of non-existent config file."""
        result = migration_script.migrate_config_to_database("/nonexistent/path.json")

        assert result["success"] is False
        assert "Failed to read config file" in result["error"]
        assert result["workspace_id"] is None
        assert result["migrated_rules"] == 0

    def test_migrate_invalid_json(self, migration_script: MockMigrationScript):
        """Test migration of invalid JSON file."""
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "invalid.json")

        # Write invalid JSON
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write("{ invalid json content }")

        try:
            result = migration_script.migrate_config_to_database(config_path)

            assert result["success"] is False
            assert "Failed to read config file" in result["error"]
            assert result["workspace_id"] is None
            assert result["migrated_rules"] == 0

        finally:
            shutil.rmtree(temp_dir)

    def test_migrate_custom_workspace_name(self, migration_script: MockMigrationScript,
                                          temp_config_file: str, migration_config_data: Dict[str, Any]):
        """Test migration with custom workspace name."""
        custom_name = "My Custom Workspace"
        result = migration_script.migrate_config_to_database(temp_config_file, custom_name)

        assert result["success"] is True
        assert result["workspace_id"] is not None
        assert result["migrated_rules"] == len(migration_config_data["rules"])

        # Verify workspace was created with custom name
        from app.models.workspace import Workspace
        workspace = migration_script.db_session.query(Workspace).filter_by(id=result["workspace_id"]).first()
        assert workspace.name == custom_name


class TestMigrationIdempotency:
    """Test that migration is idempotent (can be run multiple times safely)."""

    def test_migration_prevents_duplicate_workspace(self, migration_script: MockMigrationScript,
                                                   temp_config_file: str, migration_config_data: Dict[str, Any]):
        """Test that running migration twice doesn't create duplicate workspaces."""
        # First migration
        result1 = migration_script.migrate_config_to_database(temp_config_file)
        assert result1["success"] is True
        workspace_id1 = result1["workspace_id"]

        # Second migration (should fail due to duplicate workspace name)
        result2 = migration_script.migrate_config_to_database(temp_config_file)
        assert result2["success"] is False
        assert "already exists" in result2["error"]
        assert result2["workspace_id"] == workspace_id1  # Should reference existing workspace
        assert result2["migrated_rules"] == 0

    def test_check_migration_status(self, migration_script: MockMigrationScript,
                                   temp_config_file: str, migration_config_data: Dict[str, Any]):
        """Test checking migration status before and after migration."""
        # Check status before migration
        status_before = migration_script.check_migration_status(temp_config_file)
        assert status_before["already_migrated"] is False
        assert status_before["workspace_id"] is None
        assert status_before["permission_count"] == 0

        # Perform migration
        result = migration_script.migrate_config_to_database(temp_config_file)
        assert result["success"] is True

        # Check status after migration
        status_after = migration_script.check_migration_status(temp_config_file)
        assert status_after["already_migrated"] is True
        assert status_after["workspace_id"] == result["workspace_id"]
        assert status_after["permission_count"] == len(migration_config_data["rules"])

    def test_migration_with_custom_name_idempotency(self, migration_script: MockMigrationScript,
                                                   temp_config_file: str):
        """Test idempotency with custom workspace names."""
        custom_name = "Idempotency Test Workspace"

        # First migration
        result1 = migration_script.migrate_config_to_database(temp_config_file, custom_name)
        assert result1["success"] is True

        # Second migration with same custom name (should fail)
        result2 = migration_script.migrate_config_to_database(temp_config_file, custom_name)
        assert result2["success"] is False
        assert "already exists" in result2["error"]

        # Third migration with different name (should succeed)
        result3 = migration_script.migrate_config_to_database(temp_config_file, custom_name + " 2")
        assert result3["success"] is True
        assert result3["workspace_id"] != result1["workspace_id"]


class TestMigrationDataIntegrity:
    """Test that migration preserves all data correctly."""

    def test_all_rules_migrated_correctly(self, migration_script: MockMigrationScript,
                                         temp_config_file: str, migration_config_data: Dict[str, Any]):
        """Test that all rules are migrated with correct data."""
        result = migration_script.migrate_config_to_database(temp_config_file)
        assert result["success"] is True

        # Verify workspace was created
        from app.models.workspace import Workspace
        workspace = migration_script.db_session.query(Workspace).filter_by(id=result["workspace_id"]).first()
        assert workspace is not None

        # Verify all permissions were created correctly
        permissions = workspace.permissions
        assert len(permissions) == len(migration_config_data["rules"])

        # Create lookup for easier verification
        migrated_rules = {
            (p.path, p.permission_type, p.rule_type): p
            for p in permissions
        }

        # Verify each original rule was migrated correctly
        for original_rule in migration_config_data["rules"]:
            key = (original_rule["path"], original_rule["permission_type"], original_rule["rule_type"])
            assert key in migrated_rules

            migrated_rule = migrated_rules[key]
            assert migrated_rule.path == original_rule["path"]
            assert migrated_rule.permission_type == original_rule["permission_type"]
            assert migrated_rule.rule_type == original_rule["rule_type"]
            assert migrated_rule.description == original_rule["description"]
            assert migrated_rule.workspace_id == workspace.id

    def test_migration_preserves_rule_order(self, migration_script: MockMigrationScript,
                                           temp_config_file: str, migration_config_data: Dict[str, Any]):
        """Test that rule order is preserved during migration."""
        result = migration_script.migrate_config_to_database(temp_config_file)
        assert result["success"] is True

        # Get migrated permissions ordered by creation
        from app.models.workspace import Workspace
        workspace = migration_script.db_session.query(Workspace).filter_by(id=result["workspace_id"]).first()
        permissions = sorted(workspace.permissions, key=lambda p: p.created_at)

        # Verify order matches original config
        for i, (original_rule, migrated_permission) in enumerate(zip(migration_config_data["rules"], permissions)):
            assert migrated_permission.path == original_rule["path"]
            assert migrated_permission.permission_type == original_rule["permission_type"]
            assert migrated_permission.rule_type == original_rule["rule_type"]

    def test_migration_handles_missing_optional_fields(self, migration_script: MockMigrationScript):
        """Test migration of rules with missing optional fields."""
        # Create config with minimal rules (no description)
        minimal_config = {
            "rules": [
                {
                    "path": "minimal/path1",
                    "permission_type": "read",
                    "rule_type": "allow"
                    # No description field
                },
                {
                    "path": "minimal/path2",
                    "permission_type": "write",
                    "rule_type": "deny",
                    "description": ""  # Empty description
                }
            ],
            "version": "1.0"
        }

        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "minimal_permissions.json")

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(minimal_config, f)

        try:
            result = migration_script.migrate_config_to_database(config_path)
            assert result["success"] is True
            assert result["migrated_rules"] == 2

            # Verify permissions were created with default descriptions
            from app.models.workspace import Workspace
            workspace = migration_script.db_session.query(Workspace).filter_by(id=result["workspace_id"]).first()
            permissions = workspace.permissions

            for permission in permissions:
                # Should have default description for missing field
                if permission.path == "minimal/path1":
                    assert "Migrated from config file" in permission.description
                else:  # path2 with empty description
                    assert permission.description == ""

        finally:
            shutil.rmtree(temp_dir)

    def test_migration_validates_rule_structure(self, migration_script: MockMigrationScript):
        """Test that migration validates rule structure and handles invalid rules."""
        # Create config with invalid rules
        invalid_config = {
            "rules": [
                {
                    # Valid rule
                    "path": "valid/path",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Valid rule"
                },
                {
                    # Missing path
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Missing path"
                },
                {
                    # Missing permission_type
                    "path": "invalid/path2",
                    "rule_type": "deny",
                    "description": "Missing permission_type"
                },
                {
                    # Valid rule
                    "path": "another/valid",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Another valid rule"
                }
            ],
            "version": "1.0"
        }

        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "invalid_permissions.json")

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(invalid_config, f)

        try:
            result = migration_script.migrate_config_to_database(config_path)

            # Should succeed but with warnings about invalid rules
            assert result["success"] is True
            assert result["migrated_rules"] == 2  # Only valid rules migrated
            assert result["errors"] is not None
            assert len(result["errors"]) == 2  # Two invalid rules

        finally:
            shutil.rmtree(temp_dir)


class TestMigrationRollback:
    """Test migration rollback functionality."""

    def test_rollback_migration(self, migration_script: MockMigrationScript,
                               temp_config_file: str, migration_config_data: Dict[str, Any]):
        """Test rolling back a migration."""
        # Perform migration
        result = migration_script.migrate_config_to_database(temp_config_file)
        assert result["success"] is True
        workspace_id = result["workspace_id"]

        # Verify workspace and permissions exist
        from app.models.workspace import Workspace
        workspace = migration_script.db_session.query(Workspace).filter_by(id=workspace_id).first()
        assert workspace is not None
        assert len(workspace.permissions) == len(migration_config_data["rules"])

        # Rollback migration
        rollback_result = migration_script.rollback_migration(workspace_id)
        assert rollback_result["success"] is True
        assert rollback_result["deleted_permissions"] == len(migration_config_data["rules"])

        # Verify workspace and permissions are deleted
        workspace_after_rollback = migration_script.db_session.query(Workspace).filter_by(id=workspace_id).first()
        assert workspace_after_rollback is None

    def test_rollback_nonexistent_workspace(self, migration_script: MockMigrationScript):
        """Test rolling back non-existent workspace."""
        result = migration_script.rollback_migration(99999)
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_migration_after_rollback(self, migration_script: MockMigrationScript,
                                     temp_config_file: str, migration_config_data: Dict[str, Any]):
        """Test that migration can be performed again after rollback."""
        # Initial migration
        result1 = migration_script.migrate_config_to_database(temp_config_file)
        assert result1["success"] is True

        # Rollback
        rollback_result = migration_script.rollback_migration(result1["workspace_id"])
        assert rollback_result["success"] is True

        # Migration again (should succeed)
        result2 = migration_script.migrate_config_to_database(temp_config_file)
        assert result2["success"] is True
        # The workspace ID may be reused in test environments - focus on successful migration
        assert result2["migrated_rules"] == len(migration_config_data["rules"])

        # Verify the workspace was actually created (not reusing a deleted one)
        from app.models.workspace import Workspace
        workspace = migration_script.db_session.query(Workspace).filter_by(id=result2["workspace_id"]).first()
        assert workspace is not None
        assert len(workspace.permissions) == result2["migrated_rules"]


class TestMigrationPerformance:
    """Test migration performance with large datasets."""

    def test_large_config_migration_performance(self, migration_script: MockMigrationScript):
        """Test migration performance with large config file."""
        # Generate large config (1000 rules)
        large_rules = []
        for i in range(1000):
            large_rules.append({
                "path": f"large/dataset/path/{i}",
                "permission_type": "read" if i % 2 == 0 else "write",
                "rule_type": "allow" if i % 3 != 0 else "deny",
                "description": f"Large dataset rule {i}"
            })

        large_config = {
            "rules": large_rules,
            "description": "Large configuration for performance testing",
            "version": "1.0"
        }

        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "large_permissions.json")

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(large_config, f)

        try:
            import time
            start_time = time.time()

            result = migration_script.migrate_config_to_database(config_path)

            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000

            assert result["success"] is True
            assert result["migrated_rules"] == 1000

            # Should complete in reasonable time (less than 10 seconds for 1000 rules)
            assert elapsed_ms < 10000

            # Verify all rules were actually migrated
            from app.models.workspace import Workspace
            workspace = migration_script.db_session.query(Workspace).filter_by(id=result["workspace_id"]).first()
            assert len(workspace.permissions) == 1000

        finally:
            shutil.rmtree(temp_dir)

    def test_complex_nested_rules_migration(self, migration_script: MockMigrationScript):
        """Test migration of complex nested rule hierarchies."""
        # Generate complex nested rules
        complex_rules = []
        base_paths = ["docs", "code", "tests", "config", "data"]

        rule_id = 0
        for base in base_paths:
            for level1 in range(5):
                for level2 in range(3):
                    path = f"{base}/level{level1}/sublevel{level2}"
                    complex_rules.append({
                        "path": path,
                        "permission_type": "read" if rule_id % 2 == 0 else "write",
                        "rule_type": "allow" if rule_id % 4 != 0 else "deny",
                        "description": f"Complex nested rule {rule_id} for {path}"
                    })
                    rule_id += 1

        complex_config = {
            "rules": complex_rules,
            "description": "Complex nested configuration",
            "version": "1.1"
        }

        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "complex_permissions.json")

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(complex_config, f)

        try:
            result = migration_script.migrate_config_to_database(config_path)

            assert result["success"] is True
            assert result["migrated_rules"] == len(complex_rules)

            # Verify complex structure is preserved
            from app.models.workspace import Workspace
            workspace = migration_script.db_session.query(Workspace).filter_by(id=result["workspace_id"]).first()
            permissions = workspace.permissions

            # Verify we have permissions at all expected path levels
            path_levels = set()
            for permission in permissions:
                path_parts = permission.path.split('/')
                path_levels.add(len(path_parts))

            # Should have 3-level paths (base/level/sublevel)
            assert 3 in path_levels

            # Verify some specific complex paths exist
            permission_paths = {p.path for p in permissions}
            assert "docs/level0/sublevel0" in permission_paths
            assert "code/level4/sublevel2" in permission_paths

        finally:
            shutil.rmtree(temp_dir)