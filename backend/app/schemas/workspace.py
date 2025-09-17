"""
Pydantic schemas for workspace and permission data models.

These schemas define the API request and response formats for workspace
and permission management endpoints in Phase 3A.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


# Base schemas for common fields
class TimestampMixin(BaseModel):
    """Mixin for timestamp fields common to all models."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


# Workspace schemas
class WorkspaceBase(BaseModel):
    """Base workspace schema with shared fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Workspace name (must be unique)")
    description: Optional[str] = Field(None, max_length=1000, description="Optional workspace description")
    is_active: bool = Field(default=False, description="Whether this workspace is currently active")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Workspace name cannot be empty")
        # Validate name format - alphanumeric, spaces, hyphens, underscores
        if not all(c.isalnum() or c in " -_" for c in v):
            raise ValueError("Workspace name can only contain letters, numbers, spaces, hyphens, and underscores")
        return v.strip()


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a new workspace."""
    pass


class WorkspaceUpdate(BaseModel):
    """Schema for updating an existing workspace."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = Field(None, description="Whether this workspace should be active")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Workspace name cannot be empty")
            if not all(c.isalnum() or c in " -_" for c in v):
                raise ValueError("Workspace name can only contain letters, numbers, spaces, hyphens, and underscores")
            return v.strip()
        return v


class WorkspaceResponse(WorkspaceBase, TimestampMixin):
    """Schema for workspace API responses."""
    id: int
    version: int

    model_config = ConfigDict(from_attributes=True)


# Permission schemas
class PermissionBase(BaseModel):
    """Base permission schema with shared fields."""
    path: str = Field(..., min_length=1, max_length=1000, description="File or directory path")
    permission_type: str = Field(..., description="Permission type: 'read' or 'write'")
    rule_type: str = Field(..., description="Rule type: 'allow' or 'deny'")
    description: Optional[str] = Field(None, max_length=1000, description="Optional rule description")

    @field_validator("permission_type")
    @classmethod
    def validate_permission_type(cls, v):
        if v not in ["read", "write"]:
            raise ValueError("permission_type must be 'read' or 'write'")
        return v

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v):
        if v not in ["allow", "deny"]:
            raise ValueError("rule_type must be 'allow' or 'deny'")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        if not v or not v.strip():
            raise ValueError("Path cannot be empty")
        # Remove leading and trailing slashes for consistency
        path = v.strip().strip('/')
        if not path:
            raise ValueError("Path cannot be empty or just slashes")
        # Normalize path separators to forward slashes for cross-platform consistency
        path = path.replace('\\', '/')
        return path


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission."""
    pass


class PermissionUpdate(BaseModel):
    """Schema for updating an existing permission."""
    path: Optional[str] = Field(None, min_length=1, max_length=1000)
    permission_type: Optional[str] = None
    rule_type: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("permission_type")
    @classmethod
    def validate_permission_type(cls, v):
        if v is not None and v not in ["read", "write"]:
            raise ValueError("permission_type must be 'read' or 'write'")
        return v

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v):
        if v is not None and v not in ["allow", "deny"]:
            raise ValueError("rule_type must be 'allow' or 'deny'")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Path cannot be empty")
            path = v.strip().strip('/')
            if not path:
                raise ValueError("Path cannot be empty or just slashes")
            return path
        return v


class PermissionResponse(PermissionBase, TimestampMixin):
    """Schema for permission API responses."""
    id: int
    workspace_id: int
    version: int

    model_config = ConfigDict(from_attributes=True)


# Batch effective permissions schemas
class BatchEffectivePermissionsRequest(BaseModel):
    """Schema for batch effective permissions request."""
    paths: List[str] = Field(..., min_length=0, max_length=1000, description="List of paths to check (max 1000)")

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, v):
        if len(v) > 1000:
            raise ValueError("Maximum 1000 paths allowed per batch request")

        # Allow empty list for empty batch requests
        if not v:
            return []

        # Validate paths (but don't normalize them - preserve original format)
        for path in v:
            if not isinstance(path, str):
                raise ValueError("All paths must be strings")
            if not path.strip():
                raise ValueError("Empty paths are not allowed")

        return v


class MatchedRuleInfo(BaseModel):
    """Information about the rule that matched a permission check."""
    id: str = Field(..., description="Rule ID")
    path: str = Field(..., description="Rule path pattern")
    permission_type: str = Field(..., description="Permission type: 'read' or 'write'")
    rule_type: str = Field(..., description="Rule type: 'allow' or 'deny'")
    description: Optional[str] = Field(None, description="Rule description")
    workspace_id: Optional[int] = Field(None, description="Workspace ID for database rules")


class EffectivePermissionResult(BaseModel):
    """Result for a single path in batch effective permissions."""
    path: str = Field(..., description="The path that was checked")
    status: str = Field(..., description="Permission status: 'read', 'write', 'denied'")
    matched_rule: Optional[MatchedRuleInfo] = Field(None, alias="matchedRule", description="Information about the matching rule (null for denied)")

    model_config = ConfigDict(populate_by_name=True, alias_generator=None, ser_json_encoder=None)


class BatchEffectivePermissionsResponse(BaseModel):
    """Schema for batch effective permissions response."""
    results: List[EffectivePermissionResult] = Field(..., description="Permission results for each path")

    model_config = ConfigDict(populate_by_name=True)


# Workspace list response
class WorkspaceListResponse(BaseModel):
    """Schema for workspace list API response."""
    workspaces: List[WorkspaceResponse]
    total: int
    active_workspace_id: Optional[int] = Field(None, description="ID of the currently active workspace")


# Permission list response
class PermissionListResponse(BaseModel):
    """Schema for permission list API response."""
    permissions: List[PermissionResponse]
    total: int
    workspace_id: int


# Error response schemas
class ErrorResponse(BaseModel):
    """Standard error response schema."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")


# Success response schemas
class SuccessResponse(BaseModel):
    """Standard success response schema."""
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(None, description="Optional response data")