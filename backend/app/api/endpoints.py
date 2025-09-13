import os
import math
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.services import permission_service

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
    Returns the current hardcoded permissions for the UI to display.
    """
    return {
        "permissions": permission_service.PERMISSIONS,
        "description": "Current hardcoded permission levels",
        "context_description": "Read-only access to specified directories",
        "working_description": "Read-write access to specified directories"
    }

@router.get("/config")
def get_config():
    """
    Returns the initial server configuration for the UI.
    """
    # This will be populated with actual config data from the DB or files.
    return {
        "server_port": 8000,
        "permissions": {
            "context": ["/shared-fs/docs"],
            "working": ["/shared-fs/projects"],
            "output": ["/shared-fs/output"]
        },
        "file_system_stats": {
            "total_files": 1024,
            "total_size_mb": 256
        }
    }
