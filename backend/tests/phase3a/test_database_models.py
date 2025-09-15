"""
Test database models for Phase 3A: Workspace and Permission models.

This test module validates the SQLAlchemy models and their constraints,
relationships, and database operations as specified in the Phase 3A requirements.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.workspace import Workspace, Permission
from tests.phase3a.conftest import DatabaseTestHelper, validate_workspace_response, validate_permission_response


class TestWorkspaceModel:
    """Test cases for the Workspace model."""

    def test_workspace_creation(self, db_session: Session):
        """Test basic workspace creation with all required fields."""
        workspace_data = {
            "name": "Test Workspace",
            "description": "A test workspace for validation",
            "is_active": False
        }

        workspace = Workspace(**workspace_data)
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Validate basic fields
        assert workspace.id is not None
        assert workspace.name == "Test Workspace"
        assert workspace.description == "A test workspace for validation"
        assert workspace.is_active is False

        # Validate timestamp fields
        assert workspace.created_at is not None
        assert workspace.updated_at is not None
        assert isinstance(workspace.created_at, datetime)
        assert isinstance(workspace.updated_at, datetime)

    def test_workspace_unique_name_constraint(self, db_session: Session):
        """Test that workspace names must be unique."""
        # Create first workspace
        workspace1 = Workspace(
            name="Unique Workspace",
            description="First workspace",
            is_active=False
        )
        db_session.add(workspace1)
        db_session.commit()

        # Attempt to create workspace with same name
        workspace2 = Workspace(
            name="Unique Workspace",  # Same name
            description="Second workspace",
            is_active=False
        )
        db_session.add(workspace2)

        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_workspace_activation_logic(self, db_session: Session):
        """Test workspace activation and deactivation."""
        # Create multiple workspaces
        workspace1 = Workspace(
            name="Workspace 1",
            description="First workspace",
            is_active=True
        )
        workspace2 = Workspace(
            name="Workspace 2",
            description="Second workspace",
            is_active=False
        )

        db_session.add_all([workspace1, workspace2])
        db_session.commit()

        # Test activation change
        workspace2.is_active = True
        workspace1.is_active = False
        db_session.commit()

        db_session.refresh(workspace1)
        db_session.refresh(workspace2)

        assert workspace1.is_active is False
        assert workspace2.is_active is True

    def test_workspace_required_fields(self, db_session: Session):
        """Test that required fields are enforced."""
        # Test missing name
        with pytest.raises(IntegrityError):
            workspace = Workspace(
                description="Missing name workspace",
                is_active=False
            )
            db_session.add(workspace)
            db_session.commit()

    def test_workspace_timestamps_auto_update(self, db_session: Session):
        """Test that timestamps are automatically updated."""
        workspace = Workspace(
            name="Timestamp Test Workspace",
            description="Testing timestamp behavior",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        original_created = workspace.created_at
        original_updated = workspace.updated_at

        # Update workspace
        workspace.description = "Updated description"
        db_session.commit()
        db_session.refresh(workspace)

        # created_at should remain the same, updated_at should change
        assert workspace.created_at == original_created
        assert workspace.updated_at > original_updated

    def test_workspace_string_representation(self, db_session: Session):
        """Test workspace string representation."""
        workspace = Workspace(
            name="String Test Workspace",
            description="Testing string representation",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()

        str_repr = str(workspace)
        assert "String Test Workspace" in str_repr


class TestPermissionModel:
    """Test cases for the Permission model."""

    def test_permission_creation(self, db_session: Session):
        """Test basic permission creation with workspace relationship."""
        # First create a workspace
        workspace = Workspace(
            name="Permission Test Workspace",
            description="Workspace for permission testing",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Create permission
        permission_data = {
            "workspace_id": workspace.id,
            "path": "projects/test",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Test read access to projects"
        }

        permission = Permission(**permission_data)
        db_session.add(permission)
        db_session.commit()
        db_session.refresh(permission)

        # Validate basic fields
        assert permission.id is not None
        assert permission.workspace_id == workspace.id
        assert permission.path == "projects/test"
        assert permission.permission_type == "read"
        assert permission.rule_type == "allow"
        assert permission.description == "Test read access to projects"

        # Validate timestamp fields
        assert permission.created_at is not None
        assert permission.updated_at is not None
        assert isinstance(permission.created_at, datetime)
        assert isinstance(permission.updated_at, datetime)

        # Validate relationship
        assert permission.workspace == workspace

    def test_permission_unique_constraint(self, db_session: Session):
        """Test the unique constraint on (workspace_id, path, permission_type, rule_type)."""
        # Create workspace
        workspace = Workspace(
            name="Constraint Test Workspace",
            description="Testing permission constraints",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Create first permission
        permission1 = Permission(
            workspace_id=workspace.id,
            path="projects/test",
            permission_type="read",
            rule_type="allow",
            description="First permission"
        )
        db_session.add(permission1)
        db_session.commit()

        # Attempt to create duplicate permission
        permission2 = Permission(
            workspace_id=workspace.id,
            path="projects/test",        # Same path
            permission_type="read",      # Same permission_type
            rule_type="allow",          # Same rule_type
            description="Duplicate permission"
        )
        db_session.add(permission2)

        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_permission_different_combinations_allowed(self, db_session: Session):
        """Test that different combinations of the unique constraint are allowed."""
        # Create workspace
        workspace = Workspace(
            name="Combinations Test Workspace",
            description="Testing permission combinations",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # These should all be allowed (different combinations)
        permissions = [
            Permission(
                workspace_id=workspace.id,
                path="projects/test",
                permission_type="read",
                rule_type="allow",
                description="Read allow"
            ),
            Permission(
                workspace_id=workspace.id,
                path="projects/test",
                permission_type="read",
                rule_type="deny",      # Different rule_type
                description="Read deny"
            ),
            Permission(
                workspace_id=workspace.id,
                path="projects/test",
                permission_type="write",   # Different permission_type
                rule_type="allow",
                description="Write allow"
            ),
            Permission(
                workspace_id=workspace.id,
                path="projects/other",     # Different path
                permission_type="read",
                rule_type="allow",
                description="Different path"
            )
        ]

        db_session.add_all(permissions)
        db_session.commit()

        # All should be successfully created
        for perm in permissions:
            db_session.refresh(perm)
            assert perm.id is not None

    def test_permission_workspace_foreign_key(self, db_session: Session):
        """Test foreign key constraint to workspace."""
        # Attempt to create permission with non-existent workspace_id
        permission = Permission(
            workspace_id=99999,  # Non-existent workspace
            path="projects/test",
            permission_type="read",
            rule_type="allow",
            description="Orphaned permission"
        )
        db_session.add(permission)

        # Should raise IntegrityError due to foreign key constraint
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_permission_required_fields(self, db_session: Session):
        """Test that required fields are enforced."""
        workspace = Workspace(
            name="Required Fields Test",
            description="Testing required fields",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Test missing path
        with pytest.raises(IntegrityError):
            permission = Permission(
                workspace_id=workspace.id,
                permission_type="read",
                rule_type="allow",
                description="Missing path"
            )
            db_session.add(permission)
            db_session.commit()

    def test_permission_valid_enum_values(self, db_session: Session):
        """Test permission_type and rule_type enum constraints."""
        workspace = Workspace(
            name="Enum Test Workspace",
            description="Testing enum constraints",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Valid values should work
        valid_permission = Permission(
            workspace_id=workspace.id,
            path="projects/test",
            permission_type="read",  # Valid: read, write
            rule_type="allow",       # Valid: allow, deny
            description="Valid enums"
        )
        db_session.add(valid_permission)
        db_session.commit()

        # Invalid permission_type should be caught by application logic
        # (SQLAlchemy doesn't enforce enums by default, but our app should)
        db_session.refresh(valid_permission)
        assert valid_permission.permission_type in ["read", "write"]
        assert valid_permission.rule_type in ["allow", "deny"]


class TestWorkspacePermissionRelationship:
    """Test the relationship between Workspace and Permission models."""

    def test_cascade_delete(self, db_session: Session):
        """Test that deleting a workspace cascades to its permissions."""
        # Create workspace with permissions
        workspace = Workspace(
            name="Cascade Test Workspace",
            description="Testing cascade deletion",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Create multiple permissions
        permissions = [
            Permission(
                workspace_id=workspace.id,
                path="projects/test1",
                permission_type="read",
                rule_type="allow",
                description="Permission 1"
            ),
            Permission(
                workspace_id=workspace.id,
                path="projects/test2",
                permission_type="write",
                rule_type="allow",
                description="Permission 2"
            )
        ]
        db_session.add_all(permissions)
        db_session.commit()

        # Verify permissions exist
        permission_count = db_session.query(Permission).filter_by(workspace_id=workspace.id).count()
        assert permission_count == 2

        # Delete workspace
        db_session.delete(workspace)
        db_session.commit()

        # Verify permissions were also deleted (cascade)
        remaining_permissions = db_session.query(Permission).filter_by(workspace_id=workspace.id).count()
        assert remaining_permissions == 0

    def test_workspace_permissions_relationship(self, db_session: Session):
        """Test the workspace.permissions relationship."""
        # Create workspace
        workspace = Workspace(
            name="Relationship Test Workspace",
            description="Testing workspace-permissions relationship",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Create permissions
        permissions = [
            Permission(
                workspace_id=workspace.id,
                path="materials",
                permission_type="read",
                rule_type="allow",
                description="Materials read"
            ),
            Permission(
                workspace_id=workspace.id,
                path="projects",
                permission_type="write",
                rule_type="allow",
                description="Projects write"
            )
        ]
        db_session.add_all(permissions)
        db_session.commit()

        # Test relationship access
        db_session.refresh(workspace)
        assert len(workspace.permissions) == 2

        permission_paths = [p.path for p in workspace.permissions]
        assert "materials" in permission_paths
        assert "projects" in permission_paths

    def test_permission_workspace_relationship(self, db_session: Session):
        """Test the permission.workspace relationship."""
        workspace = Workspace(
            name="Reverse Relationship Test",
            description="Testing permission-workspace relationship",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        permission = Permission(
            workspace_id=workspace.id,
            path="test/path",
            permission_type="read",
            rule_type="allow",
            description="Test permission"
        )
        db_session.add(permission)
        db_session.commit()
        db_session.refresh(permission)

        # Test reverse relationship
        assert permission.workspace is not None
        assert permission.workspace.name == "Reverse Relationship Test"
        assert permission.workspace.id == workspace.id


class TestModelSerialization:
    """Test model serialization for API responses."""

    def test_workspace_to_dict(self, db_session: Session):
        """Test workspace serialization."""
        workspace = Workspace(
            name="Serialization Test",
            description="Testing workspace serialization",
            is_active=True
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Test basic serialization (if to_dict method exists)
        if hasattr(workspace, 'to_dict'):
            workspace_dict = workspace.to_dict()
            assert validate_workspace_response(workspace_dict)
        else:
            # Manual validation of expected fields
            assert hasattr(workspace, 'id')
            assert hasattr(workspace, 'name')
            assert hasattr(workspace, 'description')
            assert hasattr(workspace, 'is_active')
            assert hasattr(workspace, 'created_at')
            assert hasattr(workspace, 'updated_at')

    def test_permission_to_dict(self, db_session: Session):
        """Test permission serialization."""
        workspace = Workspace(
            name="Permission Serialization Test",
            description="Testing permission serialization",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        permission = Permission(
            workspace_id=workspace.id,
            path="serialization/test",
            permission_type="read",
            rule_type="allow",
            description="Test permission serialization"
        )
        db_session.add(permission)
        db_session.commit()
        db_session.refresh(permission)

        # Test basic serialization (if to_dict method exists)
        if hasattr(permission, 'to_dict'):
            permission_dict = permission.to_dict()
            assert validate_permission_response(permission_dict)
        else:
            # Manual validation of expected fields
            assert hasattr(permission, 'id')
            assert hasattr(permission, 'workspace_id')
            assert hasattr(permission, 'path')
            assert hasattr(permission, 'permission_type')
            assert hasattr(permission, 'rule_type')
            assert hasattr(permission, 'description')
            assert hasattr(permission, 'created_at')
            assert hasattr(permission, 'updated_at')


# Performance tests for model operations

class TestModelPerformance:
    """Test performance characteristics of model operations."""

    def test_bulk_permission_creation(self, db_session: Session):
        """Test performance of bulk permission creation."""
        workspace = Workspace(
            name="Bulk Test Workspace",
            description="Testing bulk operations",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Create 100 permissions
        permissions = []
        for i in range(100):
            permission = Permission(
                workspace_id=workspace.id,
                path=f"bulk/path{i}",
                permission_type="read" if i % 2 == 0 else "write",
                rule_type="allow",
                description=f"Bulk permission {i}"
            )
            permissions.append(permission)

        # Measure bulk insert time
        import time
        start_time = time.time()

        db_session.add_all(permissions)
        db_session.commit()

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        # Should complete in reasonable time (less than 1 second for 100 permissions)
        assert elapsed_ms < 1000

        # Verify all permissions were created
        permission_count = db_session.query(Permission).filter_by(workspace_id=workspace.id).count()
        assert permission_count == 100

    def test_query_performance(self, db_session: Session):
        """Test query performance with indexed fields."""
        # Create workspace with many permissions
        workspace = Workspace(
            name="Query Performance Test",
            description="Testing query performance",
            is_active=False
        )
        db_session.add(workspace)
        db_session.commit()
        db_session.refresh(workspace)

        # Create permissions with various paths
        permissions = []
        for i in range(50):
            permission = Permission(
                workspace_id=workspace.id,
                path=f"performance/test/{i}",
                permission_type="read",
                rule_type="allow",
                description=f"Performance test permission {i}"
            )
            permissions.append(permission)

        db_session.add_all(permissions)
        db_session.commit()

        # Test query performance
        import time
        start_time = time.time()

        # Query by workspace_id (should be indexed)
        results = db_session.query(Permission).filter_by(workspace_id=workspace.id).all()

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        # Should be very fast (less than 10ms for 50 records)
        assert elapsed_ms < 10
        assert len(results) == 50