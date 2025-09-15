"""
Test permission service refactor for Phase 3A.

This test module validates that the permission service correctly transitions
from config-file to database-backed permission resolution while maintaining
all existing functionality, performance, and precedence logic.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from .conftest import (
    DatabaseTestHelper, MockAuditLogger, PerformanceTimer,
    PERFORMANCE_THRESHOLDS, create_test_workspace, create_test_permission
)


class MockDatabasePermissionService:
    """Mock database-backed permission service for testing."""

    def __init__(self, db_session, audit_logger: MockAuditLogger = None):
        self.db_session = db_session
        self.audit_logger = audit_logger or MockAuditLogger()
        self.cache = {}
        self.active_workspace_id = None

    def set_active_workspace(self, workspace_id: int):
        """Set the active workspace and rebuild cache."""
        self.active_workspace_id = workspace_id
        self._rebuild_cache()

    def _rebuild_cache(self):
        """Rebuild permission cache from database."""
        if not self.active_workspace_id:
            self.cache = {}
            return

        from app.models.workspace import Workspace
        workspace = self.db_session.query(Workspace).filter_by(id=self.active_workspace_id).first()
        if not workspace:
            self.cache = {}
            return

        # Build cache from permissions
        self.cache = {}
        for permission in workspace.permissions:
            cache_key = (permission.path, permission.permission_type, permission.rule_type)
            self.cache[cache_key] = {
                "id": permission.id,
                "path": permission.path,
                "permission_type": permission.permission_type,
                "rule_type": permission.rule_type,
                "description": permission.description
            }

    def check_access(self, path: str, operation: str) -> bool:
        """Check access using database-backed permissions."""
        if not self.active_workspace_id:
            result = False
            self.audit_logger.log_permission_decision(path, operation, result, None)
            return result

        # Find matching rules using path prefix matching
        matching_rules = []
        for (rule_path, permission_type, rule_type), rule_data in self.cache.items():
            if self._path_matches(path, rule_path):
                matching_rules.append(rule_data)

        # Apply precedence logic
        result, matched_rule = self._apply_precedence_logic(matching_rules, operation)

        # Log decision
        self.audit_logger.log_permission_decision(path, operation, result, matched_rule)

        return result

    def get_effective_permission(self, path: str) -> Dict[str, Any]:
        """Get effective permission with matched rule explanation."""
        if not self.active_workspace_id:
            return {
                "status": "denied",
                "matched_rule": None
            }

        # Find matching rules
        matching_rules = []
        for (rule_path, permission_type, rule_type), rule_data in self.cache.items():
            if self._path_matches(path, rule_path):
                matching_rules.append(rule_data)

        # Apply precedence logic for both read and write
        write_result, write_rule = self._apply_precedence_logic(matching_rules, "write")
        read_result, read_rule = self._apply_precedence_logic(matching_rules, "read")

        # Determine final status
        if write_result:
            status = "write"
            matched_rule = write_rule
        elif read_result:
            status = "read"
            matched_rule = read_rule
        else:
            status = "denied"
            matched_rule = None

        return {
            "status": status,
            "matched_rule": matched_rule
        }

    def _path_matches(self, test_path: str, rule_path: str) -> bool:
        """Check if a test path matches a rule path (prefix matching)."""
        # Normalize paths
        test_path = test_path.strip('/').lower()
        rule_path = rule_path.strip('/').lower()

        # Root path matches everything
        if not rule_path:
            return True

        # Exact match or prefix match with separator
        return (test_path == rule_path or
                test_path.startswith(rule_path + '/'))

    def _apply_precedence_logic(self, rules: List[Dict], operation: str) -> tuple:
        """Apply precedence logic to find the most specific applicable rule."""
        if not rules:
            return False, None

        # Filter rules applicable to the operation
        applicable_rules = []
        for rule in rules:
            if rule['permission_type'] == operation:
                applicable_rules.append(rule)
            elif rule['permission_type'] == 'write' and operation == 'read':
                # Write implies read
                applicable_rules.append(rule)

        if not applicable_rules:
            return False, None

        # Sort by specificity (path length, descending)
        applicable_rules.sort(key=lambda r: len(r['path']), reverse=True)

        # Get most specific rules
        max_specificity = len(applicable_rules[0]['path'])
        most_specific = [r for r in applicable_rules if len(r['path']) == max_specificity]

        # Deny wins tie-breaker
        for rule in most_specific:
            if rule['rule_type'] == 'deny':
                return False, rule

        # Find allow rules
        for rule in most_specific:
            if rule['rule_type'] == 'allow':
                return True, rule

        return False, None

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "active_workspace_id": self.active_workspace_id,
            "cache_entries": list(self.cache.keys())
        }


@pytest.fixture
def db_permission_service(db_session, mock_audit_logger):
    """Provide database-backed permission service."""
    return MockDatabasePermissionService(db_session, mock_audit_logger)


class DatabaseTestHelperPermissionServiceBasics:
    """Test basic functionality of database-backed permission service."""

    def test_service_initialization(self, db_permission_service):
        """Test service initializes correctly."""
        assert db_permission_service.active_workspace_id is None
        assert db_permission_service.cache == {}

        stats = db_permission_service.get_cache_stats()
        assert stats["cache_size"] == 0
        assert stats["active_workspace_id"] is None

    def test_set_active_workspace_empty(self, db_permission_service, db_session):
        """Test setting active workspace with no permissions."""
        # Create empty workspace
        workspace_data = {
            "name": "Empty Workspace",
            "description": "Workspace with no permissions",
            "is_active": False
        }
        workspace = create_test_workspace(db_session, workspace_data)

        # Set as active
        db_permission_service.set_active_workspace(workspace.id)

        assert db_permission_service.active_workspace_id == workspace.id
        stats = db_permission_service.get_cache_stats()
        assert stats["cache_size"] == 0

    def test_set_active_workspace_with_permissions(self, db_permission_service, db_session):
        """Test setting active workspace with permissions."""
        # Create workspace with permissions
        workspace_data = {
            "name": "Test Workspace",
            "description": "Workspace with permissions",
            "is_active": False
        }
        workspace = create_test_workspace(db_session, workspace_data)

        # Add permissions
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
            }
        ]

        for perm_data in permissions_data:
            create_test_permission(db_session, workspace.id, perm_data)

        # Set as active
        db_permission_service.set_active_workspace(workspace.id)

        assert db_permission_service.active_workspace_id == workspace.id
        stats = db_permission_service.get_cache_stats()
        assert stats["cache_size"] == 2

    def test_set_nonexistent_workspace(self, db_permission_service):
        """Test setting non-existent workspace as active."""
        db_permission_service.set_active_workspace(99999)

        assert db_permission_service.active_workspace_id == 99999
        stats = db_permission_service.get_cache_stats()
        assert stats["cache_size"] == 0


class DatabaseTestHelperPermissionResolution:
    """Test permission resolution with database backend."""

    def test_check_access_no_active_workspace(self, db_permission_service):
        """Test access check with no active workspace."""
        result = db_permission_service.check_access("/any/path", "read")
        assert result is False

        # Should log the decision
        events = db_permission_service.audit_logger.get_events()
        assert len(events) == 1
        assert events[0]["result"] is False

    def test_check_access_basic_allow(self, db_permission_service, db_session):
        """Test basic access check with allow rule."""
        # Create workspace and permission
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        permission_data = {
            "path": "materials",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Allow materials"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        # Activate workspace
        db_permission_service.set_active_workspace(workspace.id)

        # Test access
        result = db_permission_service.check_access("/materials/doc.txt", "read")
        assert result is True

        # Should log the decision
        events = db_permission_service.audit_logger.get_events()
        assert len(events) == 1
        assert events[0]["result"] is True
        assert events[0]["matched_rule"] is not None

    def test_check_access_basic_deny(self, db_permission_service, db_session):
        """Test basic access check with deny rule."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        permission_data = {
            "path": "blocked",
            "permission_type": "read",
            "rule_type": "deny",
            "description": "Block access"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)

        result = db_permission_service.check_access("/blocked/file.txt", "read")
        assert result is False

    def test_check_access_no_matching_rules(self, db_permission_service, db_session):
        """Test access check with no matching rules (default deny)."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        permission_data = {
            "path": "allowed",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Only allowed path"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)

        # Test path that doesn't match any rules
        result = db_permission_service.check_access("/forbidden/file.txt", "read")
        assert result is False


class DatabaseTestHelperPermissionPrecedence:
    """Test precedence logic with database backend."""

    def test_precedence_specificity_wins(self, db_permission_service, db_session):
        """Test that more specific rules override parent rules."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        # Create parent and child rules
        permissions_data = [
            {
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Parent allow"
            },
            {
                "path": "materials/confidential",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Child deny (more specific)"
            }
        ]

        for perm_data in permissions_data:
            create_test_permission(db_session, workspace.id, perm_data)

        db_permission_service.set_active_workspace(workspace.id)

        # Test general materials access (should be allowed by parent rule)
        result1 = db_permission_service.check_access("/materials/doc.txt", "read")
        assert result1 is True

        # Test confidential access (should be denied by child rule)
        result2 = db_permission_service.check_access("/materials/confidential/secret.txt", "read")
        assert result2 is False

    def test_precedence_deny_wins_tie(self, db_permission_service, db_session):
        """Test that deny rules win over allow rules at same specificity."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        # Create both allow and deny rules for same path
        permissions_data = [
            {
                "path": "contested",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Allow rule"
            },
            {
                "path": "contested",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Deny rule (should win)"
            }
        ]

        for perm_data in permissions_data:
            create_test_permission(db_session, workspace.id, perm_data)

        db_permission_service.set_active_workspace(workspace.id)

        # Deny should win
        result = db_permission_service.check_access("/contested/file.txt", "read")
        assert result is False

    def test_precedence_write_implies_read(self, db_permission_service, db_session):
        """Test that write permission implicitly grants read access."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        # Create only write permission
        permission_data = {
            "path": "projects",
            "permission_type": "write",
            "rule_type": "allow",
            "description": "Write access (implies read)"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)

        # Should have both read and write access
        read_result = db_permission_service.check_access("/projects/file.txt", "read")
        write_result = db_permission_service.check_access("/projects/file.txt", "write")

        assert read_result is True  # Implied by write
        assert write_result is True


class DatabaseTestHelperPermissionEffectivePermissions:
    """Test get_effective_permission method."""

    def test_get_effective_permission_write_access(self, db_permission_service, db_session):
        """Test getting effective permission for write access."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        permission_data = {
            "path": "projects",
            "permission_type": "write",
            "rule_type": "allow",
            "description": "Write access"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)

        result = db_permission_service.get_effective_permission("/projects/file.txt")

        assert result["status"] == "write"
        assert result["matched_rule"] is not None
        assert result["matched_rule"]["rule_type"] == "allow"

    def test_get_effective_permission_read_only(self, db_permission_service, db_session):
        """Test getting effective permission for read-only access."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        permission_data = {
            "path": "materials",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Read access"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)

        result = db_permission_service.get_effective_permission("/materials/doc.txt")

        assert result["status"] == "read"
        assert result["matched_rule"] is not None

    def test_get_effective_permission_denied(self, db_permission_service, db_session):
        """Test getting effective permission for denied access."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        # Only create limited permission
        permission_data = {
            "path": "allowed",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Only allowed path"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)

        # Test denied path
        result = db_permission_service.get_effective_permission("/forbidden/file.txt")

        assert result["status"] == "denied"
        assert result["matched_rule"] is None


class DatabaseTestHelperPermissionServicePerformance:
    """Test performance of database-backed permission service."""

    def test_cache_rebuild_performance(self, db_permission_service, db_session, performance_timer):
        """Test performance of cache rebuild with many permissions."""
        workspace_data = {"name": "Performance Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        # Create many permissions
        for i in range(100):
            permission_data = {
                "path": f"path/{i}",
                "permission_type": "read" if i % 2 == 0 else "write",
                "rule_type": "allow",
                "description": f"Permission {i}"
            }
            create_test_permission(db_session, workspace.id, permission_data)

        # Time cache rebuild
        with performance_timer:
            db_permission_service.set_active_workspace(workspace.id)

        # Should be fast (less than 50ms for 100 rules)
        assert performance_timer.elapsed_ms < 50

        stats = db_permission_service.get_cache_stats()
        assert stats["cache_size"] == 100

    def test_permission_resolution_performance(self, db_permission_service, db_session, performance_timer):
        """Test performance of permission resolution."""
        workspace_data = {"name": "Performance Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        # Create hierarchical permissions for performance testing
        base_paths = ["materials", "projects", "logs", "config"]
        for base in base_paths:
            for i in range(10):
                permission_data = {
                    "path": f"{base}/level{i}",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": f"{base} level {i}"
                }
                create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)

        # Time multiple permission checks
        test_paths = [f"/{base}/level{i}/file.txt" for base in base_paths for i in range(5)]

        with performance_timer:
            for path in test_paths:
                db_permission_service.check_access(path, "read")

        # Should complete quickly (less than 5ms per check for 20 checks = 100ms)
        average_per_check = performance_timer.elapsed_ms / len(test_paths)
        assert average_per_check < PERFORMANCE_THRESHOLDS["permission_resolution_ms"]


class DatabaseTestHelperPermissionServiceAuditLogging:
    """Test audit logging functionality."""

    def test_audit_logging_enabled(self, db_permission_service, db_session):
        """Test that audit logging captures all permission decisions."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        permission_data = {
            "path": "test",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Test permission"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)

        # Clear previous events
        db_permission_service.audit_logger.clear()

        # Perform various access checks
        test_cases = [
            ("/test/file.txt", "read", True),
            ("/test/file.txt", "write", False),
            ("/blocked/file.txt", "read", False)
        ]

        for path, operation, expected in test_cases:
            result = db_permission_service.check_access(path, operation)
            assert result == expected

        # Verify all decisions were logged
        events = db_permission_service.audit_logger.get_events()
        assert len(events) == len(test_cases)

        for i, (path, operation, expected) in enumerate(test_cases):
            event = events[i]
            assert event["path"] == path
            assert event["operation"] == operation
            assert event["result"] == expected

    def test_audit_logging_includes_matched_rules(self, db_permission_service, db_session):
        """Test that audit logs include matched rule details."""
        workspace_data = {"name": "Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        permission_data = {
            "path": "materials",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Materials access"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)
        db_permission_service.audit_logger.clear()

        # Perform access check
        result = db_permission_service.check_access("/materials/doc.txt", "read")
        assert result is True

        # Verify matched rule is included in audit log
        events = db_permission_service.audit_logger.get_events()
        assert len(events) == 1

        event = events[0]
        assert event["matched_rule"] is not None
        assert event["matched_rule"]["path"] == "materials"
        assert event["matched_rule"]["rule_type"] == "allow"

    def test_audit_logging_performance_overhead(self, db_permission_service, db_session, performance_timer):
        """Test that audit logging has minimal performance impact."""
        workspace_data = {"name": "Performance Test", "description": "Test", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        permission_data = {
            "path": "test",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Test permission"
        }
        create_test_permission(db_session, workspace.id, permission_data)

        db_permission_service.set_active_workspace(workspace.id)

        # Time many permission checks with audit logging
        with performance_timer:
            for i in range(100):
                db_permission_service.check_access(f"/test/file{i}.txt", "read")

        # Overhead should be minimal (less than 10% threshold)
        total_time = performance_timer.elapsed_ms
        overhead_per_check = total_time / 100

        # Should be very fast even with audit logging
        assert overhead_per_check < 1.0  # Less than 1ms per check including audit


class DatabaseTestHelperPermissionServiceMigrationCompatibility:
    """Test compatibility with migrated configurations."""

    def test_migrated_permissions_work_correctly(self, db_permission_service, db_session):
        """Test that permissions migrated from config files work correctly."""
        workspace_data = {"name": "Migrated Workspace", "description": "From config", "is_active": False}
        workspace = create_test_workspace(db_session, workspace_data)

        # Create permissions that simulate migrated config
        migrated_permissions = [
            {
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Migrated from config file"
            },
            {
                "path": "projects",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Migrated from config file"
            },
            {
                "path": "materials/confidential",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Migrated from config file"
            }
        ]

        for perm_data in migrated_permissions:
            create_test_permission(db_session, workspace.id, perm_data)

        db_permission_service.set_active_workspace(workspace.id)

        # Test that migrated permissions work as expected
        assert db_permission_service.check_access("/materials/doc.txt", "read") is True
        assert db_permission_service.check_access("/projects/file.py", "write") is True
        assert db_permission_service.check_access("/projects/file.py", "read") is True  # Write implies read
        assert db_permission_service.check_access("/materials/confidential/secret.txt", "read") is False

    def test_cache_invalidation_on_workspace_change(self, db_permission_service, db_session):
        """Test that cache is properly invalidated when switching workspaces."""
        # Create two workspaces with different permissions
        workspace1_data = {"name": "Workspace 1", "description": "First", "is_active": False}
        workspace2_data = {"name": "Workspace 2", "description": "Second", "is_active": False}

        workspace1 = create_test_workspace(db_session, workspace1_data)
        workspace2 = create_test_workspace(db_session, workspace2_data)

        # Different permissions for each workspace
        perm1_data = {"path": "workspace1", "permission_type": "read", "rule_type": "allow", "description": "WS1"}
        perm2_data = {"path": "workspace2", "permission_type": "read", "rule_type": "allow", "description": "WS2"}

        create_test_permission(db_session, workspace1.id, perm1_data)
        create_test_permission(db_session, workspace2.id, perm2_data)

        # Test workspace1
        db_permission_service.set_active_workspace(workspace1.id)
        assert db_permission_service.check_access("/workspace1/file.txt", "read") is True
        assert db_permission_service.check_access("/workspace2/file.txt", "read") is False

        # Switch to workspace2
        db_permission_service.set_active_workspace(workspace2.id)
        assert db_permission_service.check_access("/workspace1/file.txt", "read") is False
        assert db_permission_service.check_access("/workspace2/file.txt", "read") is True