import os
import math
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services import permission_service
from app.config import get_feature_flags, get_config

router = APIRouter()

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

def normalize_and_validate_path(path: str, base_path: str = "/shared-fs") -> str:
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
