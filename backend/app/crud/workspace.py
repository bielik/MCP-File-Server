"""
CRUD operations for workspace management.

This module provides database operations for workspaces and permissions,
implementing the data access layer for Phase 3A functionality.
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_

from ..models.workspace import Workspace, Permission
from ..schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    PermissionCreate,
    PermissionUpdate,
)


class WorkspaceCRUD:
    """CRUD operations for workspace management."""

    def create_workspace(
        self,
        db: Session,
        workspace: WorkspaceCreate,
        created_by: Optional[str] = None
    ) -> Workspace:
        """
        Create a new workspace.

        Args:
            db: Database session
            workspace: Workspace creation data
            created_by: User who created the workspace

        Returns:
            Created workspace instance

        Raises:
            IntegrityError: If workspace name already exists
        """
        # Handle workspace activation logic - only one workspace can be active
        is_active = workspace.is_active
        if is_active:
            # Deactivate all other workspaces first
            db.query(Workspace).update({"is_active": False}, synchronize_session=False)

        db_workspace = Workspace(
            name=workspace.name,
            description=workspace.description,
            is_active=is_active,
            created_by=created_by,
            updated_by=created_by,
        )

        try:
            db.add(db_workspace)
            db.commit()
            db.refresh(db_workspace)
            return db_workspace
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Workspace with name '{workspace.name}' already exists")

    def get_workspace(self, db: Session, workspace_id: int) -> Optional[Workspace]:
        """Get a workspace by ID."""
        return db.query(Workspace).filter(Workspace.id == workspace_id).first()

    def get_workspace_by_name(self, db: Session, name: str) -> Optional[Workspace]:
        """Get a workspace by name."""
        return db.query(Workspace).filter(Workspace.name == name).first()

    def get_active_workspace(self, db: Session) -> Optional[Workspace]:
        """Get the currently active workspace."""
        return db.query(Workspace).filter(Workspace.is_active == True).first()

    def get_workspaces(self, db: Session, skip: int = 0, limit: int = 100) -> List[Workspace]:
        """Get all workspaces with pagination."""
        return db.query(Workspace).offset(skip).limit(limit).all()

    def get_workspaces_count(self, db: Session) -> int:
        """Get total count of workspaces."""
        return db.query(Workspace).count()

    def update_workspace(
        self,
        db: Session,
        workspace_id: int,
        workspace_update: WorkspaceUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[Workspace]:
        """
        Update a workspace.

        Args:
            db: Database session
            workspace_id: ID of workspace to update
            workspace_update: Update data
            updated_by: User who updated the workspace

        Returns:
            Updated workspace or None if not found

        Raises:
            ValueError: If name conflict occurs
        """
        db_workspace = self.get_workspace(db, workspace_id)
        if not db_workspace:
            return None

        # Check for name conflicts if name is being changed
        if workspace_update.name and workspace_update.name != db_workspace.name:
            existing = self.get_workspace_by_name(db, workspace_update.name)
            if existing:
                raise ValueError(f"Workspace with name '{workspace_update.name}' already exists")

        # Apply updates
        update_data = workspace_update.model_dump(exclude_unset=True)
        if update_data:
            # Handle workspace activation logic - only one workspace can be active
            if update_data.get('is_active') is True:
                # Deactivate all other workspaces first
                db.query(Workspace).filter(Workspace.id != workspace_id).update(
                    {"is_active": False}, synchronize_session=False
                )

            for field, value in update_data.items():
                setattr(db_workspace, field, value)
            db_workspace.updated_by = updated_by

            try:
                db.commit()
                db.refresh(db_workspace)
            except IntegrityError:
                db.rollback()
                raise ValueError("Failed to update workspace due to constraint violation")

        return db_workspace

    def delete_workspace(self, db: Session, workspace_id: int) -> bool:
        """
        Delete a workspace and all its permissions.

        Args:
            db: Database session
            workspace_id: ID of workspace to delete

        Returns:
            True if deleted, False if not found
        """
        db_workspace = self.get_workspace(db, workspace_id)
        if not db_workspace:
            return False

        db.delete(db_workspace)
        db.commit()
        return True

    def activate_workspace(self, db: Session, workspace_id: int) -> Optional[Workspace]:
        """
        Activate a workspace and deactivate all others.

        Args:
            db: Database session
            workspace_id: ID of workspace to activate

        Returns:
            Activated workspace or None if not found
        """
        # Check if workspace exists
        target_workspace = self.get_workspace(db, workspace_id)
        if not target_workspace:
            return None

        # Deactivate all workspaces
        db.query(Workspace).update({Workspace.is_active: False})

        # Activate target workspace
        target_workspace.is_active = True

        db.commit()
        db.refresh(target_workspace)
        return target_workspace


class PermissionCRUD:
    """CRUD operations for permission management."""

    def create_permission(
        self,
        db: Session,
        workspace_id: int,
        permission: PermissionCreate,
        created_by: Optional[str] = None
    ) -> Permission:
        """
        Create a new permission within a workspace.

        Args:
            db: Database session
            workspace_id: ID of the workspace
            permission: Permission creation data
            created_by: User who created the permission

        Returns:
            Created permission instance

        Raises:
            ValueError: If duplicate rule or workspace not found
        """
        # Verify workspace exists
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise ValueError(f"Workspace with ID {workspace_id} not found")

        db_permission = Permission(
            workspace_id=workspace_id,
            path=permission.path,
            permission_type=permission.permission_type,
            rule_type=permission.rule_type,
            description=permission.description,
            created_by=created_by,
            updated_by=created_by,
        )

        try:
            db.add(db_permission)
            db.commit()
            db.refresh(db_permission)
            return db_permission
        except IntegrityError:
            db.rollback()
            raise ValueError(
                f"Permission rule already exists for path '{permission.path}' "
                f"with type '{permission.permission_type}' and rule '{permission.rule_type}'"
            )

    def get_permission(self, db: Session, permission_id: int) -> Optional[Permission]:
        """Get a permission by ID."""
        return db.query(Permission).filter(Permission.id == permission_id).first()

    def get_workspace_permissions(
        self,
        db: Session,
        workspace_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Permission]:
        """Get all permissions for a workspace with pagination."""
        return (
            db.query(Permission)
            .filter(Permission.workspace_id == workspace_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_workspace_permissions_count(self, db: Session, workspace_id: int) -> int:
        """Get total count of permissions for a workspace."""
        return db.query(Permission).filter(Permission.workspace_id == workspace_id).count()

    def update_permission(
        self,
        db: Session,
        permission_id: int,
        permission_update: PermissionUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[Permission]:
        """
        Update a permission.

        Args:
            db: Database session
            permission_id: ID of permission to update
            permission_update: Update data
            updated_by: User who updated the permission

        Returns:
            Updated permission or None if not found

        Raises:
            ValueError: If constraint violation occurs
        """
        db_permission = self.get_permission(db, permission_id)
        if not db_permission:
            return None

        # Apply updates
        update_data = permission_update.model_dump(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                setattr(db_permission, field, value)
            db_permission.updated_by = updated_by

            try:
                db.commit()
                db.refresh(db_permission)
            except IntegrityError as e:
                db.rollback()
                error_str = str(e)
                if "unique_permission_rule" in error_str.lower() or "unique" in error_str.lower():
                    raise ValueError("A permission rule with the same path, permission type, and rule type already exists in this workspace")
                raise ValueError("Failed to update permission due to constraint violation")

        return db_permission

    def delete_permission(self, db: Session, permission_id: int) -> bool:
        """
        Delete a permission.

        Args:
            db: Database session
            permission_id: ID of permission to delete

        Returns:
            True if deleted, False if not found
        """
        db_permission = self.get_permission(db, permission_id)
        if not db_permission:
            return False

        db.delete(db_permission)
        db.commit()
        return True

    def get_active_workspace_permissions(self, db: Session) -> List[Permission]:
        """
        Get all permissions for the currently active workspace.

        Returns:
            List of permissions for active workspace, empty if no active workspace
        """
        return (
            db.query(Permission)
            .join(Workspace)
            .filter(Workspace.is_active == True)
            .all()
        )

    def find_duplicate_rule(
        self,
        db: Session,
        workspace_id: int,
        path: str,
        permission_type: str,
        rule_type: str,
        exclude_id: Optional[int] = None
    ) -> Optional[Permission]:
        """
        Find a duplicate rule within the same workspace.

        Args:
            db: Database session
            workspace_id: Workspace to search in
            path: Permission path
            permission_type: Permission type ('read' or 'write')
            rule_type: Rule type ('allow' or 'deny')
            exclude_id: Permission ID to exclude from search (for updates)

        Returns:
            Existing permission if duplicate found, None otherwise
        """
        query = db.query(Permission).filter(
            and_(
                Permission.workspace_id == workspace_id,
                Permission.path == path,
                Permission.permission_type == permission_type,
                Permission.rule_type == rule_type,
            )
        )

        if exclude_id:
            query = query.filter(Permission.id != exclude_id)

        return query.first()


# Global instances for dependency injection
workspace_crud = WorkspaceCRUD()
permission_crud = PermissionCRUD()