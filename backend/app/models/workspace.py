"""
Database models for workspace management.

This module defines the SQLAlchemy models for workspaces and permissions,
implementing the Phase 3A database schema as specified in the feature spec.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, event, Index
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

try:
    from ..database import Base
except ImportError:
    # Handle import from external context (like indexer)
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from database import Base


class Workspace(Base):
    """
    Workspace model representing isolated permission contexts.

    A workspace contains a collection of permission rules and provides
    an isolated context for AI agent operations.
    """
    __tablename__ = "workspaces"

    # Primary key
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Core fields
    name: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = Column(String(1000), nullable=True)
    is_active: Mapped[bool] = Column(Boolean, default=False, nullable=False, index=True)

    # Version field for optimistic locking
    version: Mapped[int] = Column(Integer, default=1, nullable=False)

    # Timestamps - automatically managed
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Audit fields
    created_by: Mapped[Optional[str]] = Column(String(255), nullable=True)
    updated_by: Mapped[Optional[str]] = Column(String(255), nullable=True)

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        back_populates="workspace",
        cascade="all, delete-orphan"  # Cascade delete to permissions
    )

    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}', active={self.is_active})>"


class Permission(Base):
    """
    Permission model representing access rules within workspaces.

    Each permission rule defines access control for a specific path
    within a workspace context.
    """
    __tablename__ = "permissions"

    # Primary key
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Foreign key to workspace
    workspace_id: Mapped[int] = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    # Permission fields
    path: Mapped[str] = Column(String(1000), nullable=False, index=True)
    permission_type: Mapped[str] = Column(String(50), nullable=False)  # 'read', 'write'
    rule_type: Mapped[str] = Column(String(50), nullable=False)        # 'allow', 'deny'

    # Metadata
    description: Mapped[Optional[str]] = Column(String(1000), nullable=True)

    # Version field for optimistic locking
    version: Mapped[int] = Column(Integer, default=1, nullable=False)

    # Timestamps - automatically managed
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Audit fields
    created_by: Mapped[Optional[str]] = Column(String(255), nullable=True)
    updated_by: Mapped[Optional[str]] = Column(String(255), nullable=True)

    # Relationship back to workspace
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="permissions")

    # Unique constraint: no duplicate rules within a workspace
    __table_args__ = (
        UniqueConstraint(
            'workspace_id', 'path', 'permission_type', 'rule_type',
            name='unique_permission_rule'
        ),
        {}, # Required empty dict at end for SQLAlchemy
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, workspace_id={self.workspace_id}, path='{self.path}', {self.rule_type}:{self.permission_type})>"

    def to_rule_dict(self) -> dict:
        """
        Convert permission to rule dictionary format compatible with Phase 2.

        This ensures backwards compatibility with existing permission logic.
        """
        return {
            "id": f"db-rule-{self.id}",
            "path": self.path,
            "permission_type": self.permission_type,
            "rule_type": self.rule_type,
            "description": self.description or f"{self.rule_type.capitalize()} {self.permission_type} access to {self.path}",
            "workspace_id": self.workspace_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Event listeners for timestamp updates (SQLite doesn't support onupdate properly)
@event.listens_for(Workspace, 'before_update')
def update_workspace_timestamp(mapper, connection, target):
    """Update the updated_at timestamp and version for Workspace before update."""
    target.updated_at = datetime.now(timezone.utc)
    target.version = target.version + 1


@event.listens_for(Permission, 'before_update')
def update_permission_timestamp(mapper, connection, target):
    """Update the updated_at timestamp and version for Permission before update."""
    target.updated_at = datetime.now(timezone.utc)
    target.version = target.version + 1