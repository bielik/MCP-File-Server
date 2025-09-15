"""
Pydantic schemas for the MCP KnowledgeExplorer.

This module exports all Pydantic schemas used for API request and response validation.
"""

from .mcp import *
from .setting import *
from .workspace import *

__all__ = [
    # MCP schemas
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcError",
    "InitializeParams",
    "InitializeResult",
    "ToolDefinition",
    "ToolCall",
    "ToolResult",

    # Setting schemas
    "SettingBase",
    "SettingCreate",
    "SettingUpdate",
    "SettingResponse",

    # Workspace schemas
    "WorkspaceBase",
    "WorkspaceCreate",
    "WorkspaceUpdate",
    "WorkspaceResponse",
    "WorkspaceListResponse",

    # Permission schemas
    "PermissionBase",
    "PermissionCreate",
    "PermissionUpdate",
    "PermissionResponse",
    "PermissionListResponse",

    # Batch effective permissions
    "BatchEffectivePermissionsRequest",
    "BatchEffectivePermissionsResponse",
    "EffectivePermissionResult",
    "MatchedRuleInfo",

    # Common response schemas
    "ErrorResponse",
    "SuccessResponse",
]