import os
import math
import logging
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException, Header, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services import permission_service
from app.config import get_feature_flags, get_config
from app.database import get_db
from app.api.system import router as system_router
from app.crud.workspace import workspace_crud, permission_crud
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceListResponse,
    PermissionCreate, PermissionUpdate, PermissionResponse, PermissionListResponse,
    BatchEffectivePermissionsRequest, BatchEffectivePermissionsResponse, EffectivePermissionResult,
    ErrorResponse, SuccessResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Custom exceptions for structured error responses
class StructuredHTTPException(Exception):
    """Custom exception that returns structured error response."""
    def __init__(self, status_code: int, error_code: str, message: str, details: dict = None):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details

def create_error_response(status_code: int, error_code: str, message: str, details: dict = None):
    """Create standardized error response."""
    raise StructuredHTTPException(status_code, error_code, message, details)

class FileItem(BaseModel):
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    modified: Optional[str] = None

class BrowseResponse(BaseModel):
    files: List[FileItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int

def normalize_and_validate_path(path: str, base_path: str = "/source") -> str:
    """
    Normalize and validate a path to prevent directory traversal attacks.
    Returns the absolute path within the base directory.
    """
    # Handle empty path (root discovery)
    if not path or path == "/":
        return os.path.abspath(base_path)

    # Remove leading slash and normalize
    clean_path = path.lstrip('/')
    clean_path = os.path.normpath(clean_path)

    # Check for traversal attempts
    if clean_path.startswith('..') or '/..' in clean_path:
        raise HTTPException(status_code=400, detail="Invalid path: directory traversal detected")

    # Join with base path and resolve
    full_path = os.path.join(base_path, clean_path)
    abs_path = os.path.abspath(full_path)
    abs_base = os.path.abspath(base_path)

    # Ensure the resolved path is within the base directory
    if not abs_path.startswith(abs_base):
        raise HTTPException(status_code=400, detail="Invalid path: outside allowed directory")

    return abs_path

@router.get("/browse", response_model=BrowseResponse)
def browse_files(
    path: str = Query("", description="Path to browse within the shared filesystem"),
    max_depth: int = Query(1, ge=1, le=3, description="Maximum depth to traverse"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of items per page")
):
    """
    Browse files and directories within the shared filesystem with security hardening.
    """
    try:
        # Normalize and validate the path
        safe_path = normalize_and_validate_path(path)

        # Check if path exists and is accessible
        if not os.path.exists(safe_path):
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")

        if not os.path.isdir(safe_path):
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

        # Get directory contents
        try:
            all_items = []
            for item_name in os.listdir(safe_path):
                item_path = os.path.join(safe_path, item_name)

                # Skip hidden files and directories
                if item_name.startswith('.'):
                    continue

                try:
                    stat_info = os.stat(item_path)
                    is_directory = os.path.isdir(item_path)

                    # Create relative path for API response
                    if path == "" or path == "/":
                        relative_path = item_name
                    else:
                        relative_path = f"{path.rstrip('/')}/{item_name}"

                    file_item = FileItem(
                        name=item_name,
                        path=relative_path,
                        is_directory=is_directory,
                        size=stat_info.st_size if not is_directory else None,
                        modified=str(stat_info.st_mtime)
                    )
                    all_items.append(file_item)

                except (PermissionError, OSError):
                    # Skip items we can't access
                    continue

        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied to access directory")

        # Sort items (directories first, then alphabetically)
        all_items.sort(key=lambda x: (not x.is_directory, x.name.lower()))

        # Calculate pagination
        total_count = len(all_items)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = all_items[start_idx:end_idx]

        return BrowseResponse(
            files=paginated_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/current-permissions")
def get_current_permissions():
    """
    Returns the current permissions in frontend-compatible format.
    """
    feature_flags = get_feature_flags()

    if not feature_flags.is_config_permissions_enabled():
        # Return legacy hardcoded permissions
        return {
            "permissions": permission_service.PERMISSIONS,
            "description": "Hardcoded permission levels (Phase 1)",
            "context_description": "Read-only access to specified directories",
            "working_description": "Read-write access to specified directories",
            "config_file_enabled": False
        }

    try:
        from app.services.config_permission_service import get_permission_service
        service = get_permission_service()

        # Convert config-file format to frontend-compatible format
        config_data = service.get_config_data()

        # Extract paths by permission type and rule type
        context_paths = []
        working_paths = []

        for rule in config_data.get("rules", []):
            path = rule["path"]
            perm_type = rule["permission_type"]
            rule_type = rule["rule_type"]

            if rule_type == "allow":
                if perm_type == "read":
                    context_paths.append(path)
                elif perm_type == "write":
                    working_paths.append(path)

        return {
            "permissions": {
                "context": context_paths,
                "working": working_paths
            },
            "description": "Config-file based permissions (Phase 2)",
            "context_description": "Read-only access to specified directories",
            "working_description": "Read-write access to specified directories",
            "config_file_enabled": True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load permission config: {str(e)}")

@router.get("/config")
def get_server_config():
    """
    Returns the initial server configuration for the UI.
    """
    config = get_config()
    feature_flags = get_feature_flags()

    return {
        "server_port": config.BACKEND_PORT,
        "permissions": {
            "context": ["/shared-fs/docs"],
            "working": ["/shared-fs/projects"],
            "output": ["/shared-fs/output"]
        },
        "file_system_stats": {
            "total_files": 1024,
            "total_size_mb": 256
        },
        "feature_flags": feature_flags.to_dict(),
        "config_file_permissions_enabled": feature_flags.is_config_permissions_enabled()
    }


class PermissionConfigRequest(BaseModel):
    """Request model for permission configuration updates."""
    config: Dict[str, Any]


@router.get("/config/permissions")
def get_permissions_config():
    """
    Returns the current permission configuration with ETag for concurrency control.
    """
    feature_flags = get_feature_flags()

    if not feature_flags.is_config_permissions_enabled():
        # Return legacy hardcoded permissions
        response_data = {
            "permissions": permission_service.PERMISSIONS,
            "description": "Hardcoded permission levels (Phase 1)",
            "context_description": "Read-only access to specified directories",
            "working_description": "Read-write access to specified directories",
            "config_file_enabled": False
        }
        return JSONResponse(
            content=response_data,
            headers={"ETag": "legacy-hardcoded"}
        )

    try:
        from app.services.config_permission_service import get_permission_service
        service = get_permission_service()

        config_data = service.get_config_data()
        etag = service.get_config_etag()
        stats = service.get_stats()

        response_data = {
            **config_data,
            "config_file_enabled": True,
            "stats": stats,
            "description": "Config-file based permissions (Phase 2)"
        }

        return JSONResponse(
            content=response_data,
            headers={"ETag": f'"{etag}"'}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load permission config: {str(e)}")


@router.put("/config/permissions")
def update_permissions_config(
    request: PermissionConfigRequest,
    if_match: Optional[str] = Header(None, alias="If-Match")
):
    """
    Updates the permission configuration with optimistic locking via ETag.
    Returns 412 Precondition Failed if ETag doesn't match.
    """
    feature_flags = get_feature_flags()

    if not feature_flags.is_config_permissions_enabled():
        raise HTTPException(
            status_code=501,
            detail="Config file permissions are not enabled. Set ENABLE_CONFIG_FILE_PERMISSIONS=true"
        )

    if not if_match:
        raise HTTPException(
            status_code=400,
            detail="If-Match header is required for concurrency control"
        )

    # Remove quotes from ETag if present
    expected_etag = if_match.strip('"')

    try:
        from app.services.config_permission_service import get_permission_service
        service = get_permission_service()

        # Update with optimistic locking
        new_etag = service.update_config(request.config, expected_etag)

        # Return updated config with new ETag
        updated_config = service.get_config_data()

        return JSONResponse(
            content={
                **updated_config,
                "message": "Permission configuration updated successfully",
                "config_file_enabled": True
            },
            headers={"ETag": f'"{new_etag}"'}
        )

    except ValueError as e:
        error_msg = str(e)
        if "Expected ETag" in error_msg:
            # ETag mismatch - conflict
            raise HTTPException(
                status_code=412,
                detail={
                    "code": "ETAG_MISMATCH",
                    "message": "Configuration has been modified by another process",
                    "details": {"error": error_msg}
                }
            )
        else:
            # Validation error
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid configuration data",
                    "details": {"error": error_msg}
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "UPDATE_FAILED",
                "message": "Failed to update permission configuration",
                "details": {"error": str(e)}
            }
        )


@router.get("/config/permissions/stats")
def get_permissions_stats():
    """
    Returns performance statistics for the permission system.
    """
    feature_flags = get_feature_flags()

    if not feature_flags.is_config_permissions_enabled():
        return {
            "config_file_enabled": False,
            "message": "Config file permissions are not enabled"
        }

    try:
        from app.services.config_permission_service import get_permission_service
        service = get_permission_service()

        return {
            "config_file_enabled": True,
            **service.get_stats()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get permission stats: {str(e)}")


# ============================================================================
# ETag utility functions for optimistic locking
def generate_etag(obj_id: int, version: int) -> str:
    """Generate ETag from object ID and version."""
    data = f"{obj_id}:{version}"
    return hashlib.md5(data.encode()).hexdigest()

def validate_etag(obj_id: int, obj_version: int, provided_etag: str) -> bool:
    """Validate that provided ETag matches current object state."""
    expected_etag = generate_etag(obj_id, obj_version)
    clean_provided = provided_etag.strip('"')
    return clean_provided == expected_etag

# PHASE 3A: Database-Driven Workspace & Permission Management APIs
# ============================================================================

def check_phase3_enabled():
    """Check if Phase 3A features are enabled."""
    feature_flags = get_feature_flags()
    if not feature_flags.is_database_permissions_enabled():
        raise HTTPException(
            status_code=501,
            detail="Database permissions are not enabled. Set ENABLE_DATABASE_PERMISSIONS=true"
        )

# Workspace Management APIs
@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
def create_workspace(
    workspace: WorkspaceCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new workspace.

    The workspace will be created in an inactive state. Use the activate endpoint
    to make it the active workspace for permission resolution.
    """
    check_phase3_enabled()

    try:
        db_workspace = workspace_crud.create_workspace(
            db=db,
            workspace=workspace,
            created_by="api_user"  # TODO: Replace with actual user context
        )
        return db_workspace
    except ValueError as e:
        create_error_response(409, "WORKSPACE_CONFLICT", str(e))


@router.get("/workspaces", response_model=WorkspaceListResponse)
def list_workspaces(
    skip: int = Query(0, ge=0, description="Number of workspaces to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of workspaces to return"),
    db: Session = Depends(get_db)
):
    """
    List all workspaces with pagination.

    Returns workspaces ordered by creation date, with the currently active
    workspace indicated in the response.
    """
    check_phase3_enabled()

    try:
        workspaces = workspace_crud.get_workspaces(db, skip=skip, limit=limit)
        total = workspace_crud.get_workspaces_count(db)
        active_workspace = workspace_crud.get_active_workspace(db)

        return WorkspaceListResponse(
            workspaces=workspaces,
            total=total,
            active_workspace_id=active_workspace.id if active_workspace else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workspaces: {str(e)}")


@router.get("/workspaces/{workspace_id}")
def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific workspace by ID with ETag support."""
    check_phase3_enabled()

    workspace = workspace_crud.get_workspace(db, workspace_id)
    if not workspace:
        create_error_response(404, "WORKSPACE_NOT_FOUND", "Workspace not found")

    # Generate ETag
    etag = generate_etag(workspace.id, workspace.version)

    return JSONResponse(
        content=WorkspaceResponse.model_validate(workspace).model_dump(mode='json'),
        headers={"ETag": f'"{etag}"'}
    )


@router.put("/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: int,
    workspace_update: WorkspaceUpdate,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    db: Session = Depends(get_db)
):
    """Update a workspace with optimistic locking via ETag."""
    check_phase3_enabled()

    # Get current workspace for ETag validation
    current_workspace = workspace_crud.get_workspace(db, workspace_id)
    if not current_workspace:
        create_error_response(404, "WORKSPACE_NOT_FOUND", "Workspace not found")

    # Validate If-Match header if provided
    if if_match:
        if not validate_etag(current_workspace.id, current_workspace.version, if_match):
            create_error_response(412, "ETAG_MISMATCH",
                "Workspace has been modified by another process. Please refresh and try again.",
                {"current_version": current_workspace.version})

    try:
        updated_workspace = workspace_crud.update_workspace(
            db=db,
            workspace_id=workspace_id,
            workspace_update=workspace_update,
            updated_by="api_user"  # TODO: Replace with actual user context
        )

        if not updated_workspace:
            create_error_response(404, "WORKSPACE_NOT_FOUND", "Workspace not found")

        # Generate new ETag for response
        etag = generate_etag(updated_workspace.id, updated_workspace.version)

        return JSONResponse(
            content=WorkspaceResponse.model_validate(updated_workspace).model_dump(mode='json'),
            headers={"ETag": f'"{etag}"'}
        )
    except ValueError as e:
        create_error_response(409, "WORKSPACE_UPDATE_CONFLICT", str(e))


@router.delete("/workspaces/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a workspace and all its permissions.

    WARNING: This operation cannot be undone. All permission rules
    associated with this workspace will also be deleted.
    """
    check_phase3_enabled()

    # Check if workspace exists and is active
    workspace = workspace_crud.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Prevent deletion of active workspace
    if workspace.is_active:
        raise HTTPException(status_code=400, detail="Cannot delete active workspace. Deactivate it first.")

    success = workspace_crud.delete_workspace(db, workspace_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Return 204 No Content


@router.post("/workspaces/{workspace_id}/activate", response_model=WorkspaceResponse)
async def activate_workspace(
    workspace_id: int,
    db: Session = Depends(get_db)
):
    """
    Activate a workspace, making it the current active workspace.

    This will deactivate all other workspaces and make the specified workspace
    the source of truth for permission resolution. Permission caches will be
    invalidated and rebuilt.
    """
    check_phase3_enabled()

    # Get the workspace before activation for WebSocket event
    old_active_workspace = workspace_crud.get_active_workspace(db)
    old_workspace_data = None
    if old_active_workspace:
        old_workspace_data = {
            "id": old_active_workspace.id,
            "name": old_active_workspace.name
        }

    activated_workspace = workspace_crud.activate_workspace(db, workspace_id)
    if not activated_workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Extract data we need for WebSocket events before session closes
    activated_workspace_data = {
        "id": activated_workspace.id,
        "name": activated_workspace.name
    }

    # Invalidate permission cache to force reload of new active workspace rules
    try:
        from app.services.database_permission_service import get_database_permission_service
        service = get_database_permission_service()
        service.invalidate_cache()
        service.reload_rules(force=True)
    except Exception as e:
        logger.warning(f"Failed to invalidate permission cache: {e}")

    # Broadcast WebSocket events for real-time UI updates
    try:
        # Import ui_manager from main.py
        import sys
        import importlib
        main_module = sys.modules.get('app.main')
        if main_module and hasattr(main_module, 'ui_manager'):
            ui_manager = main_module.ui_manager

            # Send workspace deactivation event if there was a previous active workspace
            if old_workspace_data and old_workspace_data["id"] != workspace_id:
                deactivation_event = {
                    "event": "workspace_deactivated",
                    "workspace_id": old_workspace_data["id"],
                    "workspace_name": old_workspace_data["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                await ui_manager.broadcast(json.dumps(deactivation_event))

            # Send workspace activation event
            activation_event = {
                "event": "workspace_activated",
                "workspace_id": activated_workspace_data["id"],
                "workspace_name": activated_workspace_data["name"],
                "timestamp": datetime.utcnow().isoformat()
            }
            await ui_manager.broadcast(json.dumps(activation_event))

            # Send cache invalidation event
            cache_event = {
                "event": "permission_cache_invalidated",
                "workspace_id": workspace_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            await ui_manager.broadcast(json.dumps(cache_event))

    except Exception as e:
        logger.warning(f"Failed to broadcast WebSocket events: {e}")

    return activated_workspace


# Permission Management APIs
@router.post("/workspaces/{workspace_id}/permissions", response_model=PermissionResponse, status_code=201)
async def create_permission(
    workspace_id: int,
    permission: PermissionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new permission rule within a workspace.

    The rule will be validated against the unique constraint to prevent
    duplicate rules within the same workspace.
    """
    check_phase3_enabled()

    try:
        db_permission = permission_crud.create_permission(
            db=db,
            workspace_id=workspace_id,
            permission=permission,
            created_by="api_user"  # TODO: Replace with actual user context
        )

        # Broadcast WebSocket event for permission creation
        try:
            import sys
            main_module = sys.modules.get('app.main')
            if main_module and hasattr(main_module, 'ui_manager'):
                ui_manager = main_module.ui_manager

                permission_event = {
                    "event": "permission_created",
                    "workspace_id": workspace_id,
                    "permission_id": db_permission.id,
                    "path": db_permission.path,
                    "permission_type": db_permission.permission_type,
                    "rule_type": db_permission.rule_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await ui_manager.broadcast(json.dumps(permission_event))
        except Exception as e:
            logger.warning(f"Failed to broadcast permission creation event: {e}")

        # Invalidate permission cache so new rules are loaded
        try:
            from app.services.database_permission_service import get_database_permission_service
            service = get_database_permission_service()
            service.invalidate_cache(workspace_id)
        except Exception as e:
            logger.warning(f"Failed to invalidate permission cache: {e}")

        return db_permission
    except ValueError as e:
        if "not found" in str(e):
            create_error_response(404, "WORKSPACE_NOT_FOUND", str(e))
        else:
            create_error_response(409, "PERMISSION_CONFLICT", str(e))


@router.get("/workspaces/{workspace_id}/permissions", response_model=PermissionListResponse)
def list_workspace_permissions(
    workspace_id: int,
    skip: int = Query(0, ge=0, description="Number of permissions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of permissions to return"),
    db: Session = Depends(get_db)
):
    """List all permissions for a specific workspace with pagination."""
    check_phase3_enabled()

    # Verify workspace exists
    workspace = workspace_crud.get_workspace(db, workspace_id)
    if not workspace:
        create_error_response(404, "WORKSPACE_NOT_FOUND", "Workspace not found")

    try:
        permissions = permission_crud.get_workspace_permissions(
            db, workspace_id, skip=skip, limit=limit
        )
        total = permission_crud.get_workspace_permissions_count(db, workspace_id)

        return PermissionListResponse(
            permissions=permissions,
            total=total,
            workspace_id=workspace_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list permissions: {str(e)}")


@router.get("/permissions/{permission_id}")
def get_permission(
    permission_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific permission by ID with ETag support."""
    check_phase3_enabled()

    permission = permission_crud.get_permission(db, permission_id)
    if not permission:
        create_error_response(404, "PERMISSION_NOT_FOUND", "Permission not found")

    # Generate ETag
    etag = generate_etag(permission.id, permission.version)

    return JSONResponse(
        content=PermissionResponse.model_validate(permission).model_dump(mode='json'),
        headers={"ETag": f'"{etag}"'}
    )


@router.put("/permissions/{permission_id}")
def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    db: Session = Depends(get_db)
):
    """Update an existing permission rule with optimistic locking via ETag."""
    check_phase3_enabled()

    # Get current permission for ETag validation
    current_permission = permission_crud.get_permission(db, permission_id)
    if not current_permission:
        create_error_response(404, "PERMISSION_NOT_FOUND", "Permission not found")

    # Validate If-Match header if provided
    if if_match:
        if not validate_etag(current_permission.id, current_permission.version, if_match):
            create_error_response(412, "ETAG_MISMATCH",
                "Permission has been modified by another process. Please refresh and try again.",
                {"current_version": current_permission.version})

    try:
        updated_permission = permission_crud.update_permission(
            db=db,
            permission_id=permission_id,
            permission_update=permission_update,
            updated_by="api_user"  # TODO: Replace with actual user context
        )

        if not updated_permission:
            create_error_response(404, "PERMISSION_NOT_FOUND", "Permission not found")

        # Generate new ETag for response
        etag = generate_etag(updated_permission.id, updated_permission.version)

        return JSONResponse(
            content=PermissionResponse.model_validate(updated_permission).model_dump(mode='json'),
            headers={"ETag": f'"{etag}"'}
        )
    except ValueError as e:
        create_error_response(409, "PERMISSION_UPDATE_CONFLICT", str(e))


@router.delete("/permissions/{permission_id}", status_code=204)
async def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db)
):
    """Delete a permission rule."""
    check_phase3_enabled()

    # Get permission info before deletion for broadcasting
    permission = permission_crud.get_permission(db, permission_id)
    if not permission:
        create_error_response(404, "PERMISSION_NOT_FOUND", "Permission not found")

    success = permission_crud.delete_permission(db, permission_id)
    if not success:
        create_error_response(404, "PERMISSION_NOT_FOUND", "Permission not found")

    # Broadcast WebSocket event for permission deletion
    try:
        import sys
        main_module = sys.modules.get('app.main')
        if main_module and hasattr(main_module, 'ui_manager'):
            ui_manager = main_module.ui_manager

            permission_event = {
                "event": "permission_deleted",
                "workspace_id": permission.workspace_id,
                "permission_id": permission_id,
                "path": permission.path,
                "timestamp": datetime.utcnow().isoformat()
            }
            await ui_manager.broadcast(json.dumps(permission_event))
    except Exception as e:
        logger.warning(f"Failed to broadcast permission deletion event: {e}")

    # Invalidate permission cache so deleted rules are removed
    try:
        from app.services.database_permission_service import get_database_permission_service
        service = get_database_permission_service()
        service.invalidate_cache(permission.workspace_id)
    except Exception as e:
        logger.warning(f"Failed to invalidate permission cache: {e}")

    # Return 204 No Content


# Batch Effective Permissions API (Cornerstone Feature)
@router.post("/workspaces/{workspace_id}/effective-permissions:batch", response_model=BatchEffectivePermissionsResponse, response_model_by_alias=True)
def batch_effective_permissions(
    workspace_id: int,
    request: BatchEffectivePermissionsRequest,
    db: Session = Depends(get_db)
):
    """
    Batch endpoint for checking effective permissions on multiple paths.

    This is the cornerstone API for Phase 3A, designed to efficiently provide
    permission status and matched rule information for large numbers of paths.
    The UI will use this endpoint to display permission indicators and explanations.

    Performance target: < 500ms for 1000 paths
    """
    check_phase3_enabled()

    # Verify workspace exists
    workspace = workspace_crud.get_workspace(db, workspace_id)
    if not workspace:
        create_error_response(404, "WORKSPACE_NOT_FOUND", "Workspace not found")

    # For inactive workspaces, return all none results (no permissions apply)
    if not workspace.is_active:
        none_results = [
            EffectivePermissionResult(
                path=path,
                status="none",
                matched_rule=None
            )
            for path in request.paths
        ]
        return BatchEffectivePermissionsResponse(results=none_results)

    try:
        # Use the database permission service for batch permission checking
        from app.services.database_permission_service import get_database_permission_service

        service = get_database_permission_service()
        results = service.batch_check_permissions(request.paths, workspace_id)

        return BatchEffectivePermissionsResponse(results=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check permissions: {str(e)}")


# Active Workspace Permissions (Helper API)
@router.get("/active-workspace/permissions", response_model=PermissionListResponse)
def get_active_workspace_permissions(
    db: Session = Depends(get_db)
):
    """
    Get all permissions for the currently active workspace.

    This is a convenience endpoint for getting the permission rules that are
    currently being used for access control decisions.
    """
    check_phase3_enabled()

    active_workspace = workspace_crud.get_active_workspace(db)
    if not active_workspace:
        create_error_response(404, "NO_ACTIVE_WORKSPACE", "No active workspace found")

    try:
        permissions = permission_crud.get_active_workspace_permissions(db)
        total = len(permissions)

        return PermissionListResponse(
            permissions=permissions,
            total=total,
            workspace_id=active_workspace.id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active workspace permissions: {str(e)}")


# Include additional routers
router.include_router(system_router)
