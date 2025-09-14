import os

# For now, permissions are hardcoded. This would eventually query the database.
# Permission levels: 'context' (read-only), 'working' (read-write)
PERMISSIONS = {
    "context": ["docs", "projects", "materials"],
    "working": ["projects", "output"],
}

SHARED_FS_PATH = "/shared-fs"

# Feature flag integration
try:
    from app.config import get_feature_flags
    from app.services.config_permission_service import (
        check_access as config_check_access,
        get_safe_path as config_get_safe_path,
        get_permission_service
    )
    _HAS_CONFIG_SUPPORT = True
except ImportError:
    _HAS_CONFIG_SUPPORT = False

def get_safe_path(user_path: str) -> str:
    """
    Joins the user-provided path with the base shared directory and resolves it
    to an absolute path, preventing directory traversal.

    Routes to config-based service if Phase 2 is enabled, otherwise uses legacy logic.
    """
    if _HAS_CONFIG_SUPPORT:
        feature_flags = get_feature_flags()
        if feature_flags.is_config_permissions_enabled():
            # Use new config-based service
            return config_get_safe_path(user_path)

    # Legacy logic
    # Normalize path to prevent '..' traversal before joining
    norm_user_path = os.path.normpath(user_path)
    if norm_user_path.startswith(('..', '/')):
        raise PermissionError(f"Path cannot be absolute or contain '..': {user_path}")

    # Join with the base path
    full_path = os.path.join(SHARED_FS_PATH, norm_user_path)

    # Resolve the absolute path and ensure it's within the shared directory
    abs_path = os.path.abspath(full_path)
    abs_shared_fs = os.path.abspath(SHARED_FS_PATH)

    if not abs_path.startswith(abs_shared_fs):
        raise PermissionError(f"Access denied: Path '{user_path}' is outside the allowed shared directory.")

    return abs_path

def check_access(path: str, operation: str):
    """
    Checks if a given operation ('read' or 'write') is allowed on a path.
    Raises PermissionError if access is denied.

    Routes to config-based service if Phase 2 is enabled, otherwise uses legacy logic.
    """
    if _HAS_CONFIG_SUPPORT:
        feature_flags = get_feature_flags()
        if feature_flags.is_config_permissions_enabled():
            # Use new config-based service
            is_allowed = config_check_access(path, operation)
            if not is_allowed:
                raise PermissionError(f"Operation '{operation}' is not permitted for path: {path}")
            return True

    # Legacy hardcoded logic
    if operation not in ['read', 'write']:
        raise ValueError("Invalid operation type for permission check.")

    # Get the top-level directory from the user path
    try:
        top_level_dir = path.strip('/').split('/')[0]
    except IndexError:
        top_level_dir = "" # Root of shared-fs

    is_allowed = False
    if operation == 'read':
        # Read is allowed in both 'context' and 'working' directories
        allowed_dirs = set(PERMISSIONS['context'] + PERMISSIONS['working'])
        if top_level_dir in allowed_dirs:
            is_allowed = True

    elif operation == 'write':
        # Write is only allowed in 'working' directories
        if top_level_dir in PERMISSIONS['working']:
            is_allowed = True

    if not is_allowed:
        raise PermissionError(f"Operation '{operation}' is not permitted for path: {path}")

    # This call also validates the path is safe
    get_safe_path(path)

    return True
