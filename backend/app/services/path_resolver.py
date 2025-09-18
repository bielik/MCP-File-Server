"""
Path resolver service for handling /source mount point.

This service provides path resolution for the /source mount point.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class MountPointInfo:
    """Information about a mount point."""

    def __init__(self, path: str, is_primary: bool = False, is_legacy: bool = False):
        self.path = path
        self.is_primary = is_primary
        self.is_legacy = is_legacy
        self.is_available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if this mount point is available."""
        try:
            return Path(self.path).exists() and Path(self.path).is_dir()
        except (OSError, PermissionError):
            return False

    def __repr__(self):
        return f"MountPoint({self.path}, primary={self.is_primary}, legacy={self.is_legacy}, available={self.is_available})"


class PathResolver:
    """
    Service for resolving paths using the /source mount point.

    Provides path resolution with caching for the /source mount point.
    """

    def __init__(self):
        self.mount = MountPointInfo("/source", is_primary=True)
        self._mount_info_cache = {}

    def _load_feature_flags(self):
        """Load feature flags for mount point behavior."""
        try:
            from app.config import get_feature_flags
            self._feature_flags = get_feature_flags()
            self._source_mount_enabled = os.getenv("ENABLE_SOURCE_MOUNT", "false").lower() == "true"
        except ImportError:
            logger.warning("Feature flags not available, using defaults")
            self._feature_flags = None
            self._source_mount_enabled = False

    def _discover_mount_points(self):
        """Discover and validate available mount points."""
        self.available_mounts: List[MountPointInfo] = []

        # Check legacy mount
        if self.legacy_mount.is_available:
            self.available_mounts.append(self.legacy_mount)
            logger.info(f"Legacy mount point available: {self.legacy_mount.path}")

        # Check new mount if enabled
        if self._source_mount_enabled and self.new_mount.is_available:
            self.available_mounts.append(self.new_mount)
            logger.info(f"New mount point available: {self.new_mount.path}")

        # Determine primary mount
        if self._source_mount_enabled and self.new_mount.is_available:
            self._primary_mount = self.new_mount
        elif self.legacy_mount.is_available:
            self._primary_mount = self.legacy_mount
        else:
            logger.error("No mount points available!")
            self._primary_mount = None

    @property
    def primary_mount_path(self) -> Optional[str]:
        """Get the primary mount point path."""
        return self._primary_mount.path if self._primary_mount else None

    @property
    def is_legacy_mount_active(self) -> bool:
        """Check if legacy mount is still being used as primary."""
        return self._primary_mount == self.legacy_mount if self._primary_mount else False

    @property
    def legacy_mount_detected(self) -> bool:
        """Check if legacy mount is available (for deprecation warnings)."""
        return self.legacy_mount.is_available

    def get_safe_path(self, user_path: str, preferred_mount: Optional[str] = None) -> str:
        """
        Convert user path to safe absolute path within mount boundaries.

        Args:
            user_path: User-provided relative path
            preferred_mount: Preferred mount point (defaults to primary)

        Returns:
            Safe absolute path within mount point

        Raises:
            ValueError: If path is unsafe or no mount points available
            FileNotFoundError: If preferred mount not available
        """
        if not self.available_mounts:
            raise ValueError("No mount points available")

        # Normalize user path to prevent traversal
        norm_user_path = os.path.normpath(user_path)
        if norm_user_path.startswith(('..', '/')):
            raise ValueError(f"Path traversal detected: {user_path}")

        # Determine which mount to use
        target_mount = self._primary_mount
        if preferred_mount:
            target_mount = self._find_mount_by_path(preferred_mount)
            if not target_mount or not target_mount.is_available:
                raise FileNotFoundError(f"Preferred mount not available: {preferred_mount}")

        if not target_mount:
            raise ValueError("No suitable mount point found")

        # Construct safe path
        safe_path = os.path.join(target_mount.path, norm_user_path)
        return safe_path

    def _find_mount_by_path(self, mount_path: str) -> Optional[MountPointInfo]:
        """Find mount info by path."""
        for mount in self.available_mounts:
            if mount.path == mount_path:
                return mount
        return None

    def translate_path(self, path: str, from_mount: str, to_mount: str) -> Optional[str]:
        """
        Translate a path from one mount point to another.

        Args:
            path: Full path within from_mount
            from_mount: Source mount point path
            to_mount: Target mount point path

        Returns:
            Translated path or None if translation not possible
        """
        # Validate mounts exist
        source_mount = self._find_mount_by_path(from_mount)
        target_mount = self._find_mount_by_path(to_mount)

        if not source_mount or not target_mount:
            return None

        if not source_mount.is_available or not target_mount.is_available:
            return None

        # Extract relative path from source mount
        try:
            relative_path = os.path.relpath(path, from_mount)
            if relative_path.startswith('..'):
                return None  # Path is outside source mount
        except ValueError:
            return None  # Paths on different drives (Windows)

        # Construct path in target mount
        translated_path = os.path.join(to_mount, relative_path)
        return translated_path

    def get_mount_status(self) -> Dict[str, Any]:
        """
        Get comprehensive mount point status for API responses.

        Returns:
            Dictionary with mount point information
        """
        return {
            "available_mounts": [
                {
                    "path": mount.path,
                    "is_primary": mount == self._primary_mount,
                    "is_legacy": mount.is_legacy,
                    "is_available": mount.is_available
                }
                for mount in self.available_mounts
            ],
            "primary_mount": self._primary_mount.path if self._primary_mount else None,
            "legacy_mount_detected": self.legacy_mount_detected,
            "legacy_mount_active": self.is_legacy_mount_active,
            "source_mount_enabled": self._source_mount_enabled,
            "dual_mount_active": len(self.available_mounts) > 1
        }

    def get_deprecation_info(self) -> Dict[str, Any]:
        """
        Get deprecation information for UI warnings.

        Returns:
            Dictionary with deprecation status
        """
        return {
            "legacy_mount_detected": self.legacy_mount_detected,
            "current_mount": self._primary_mount.path if self._primary_mount else None,
            "recommended_mount": "/source",
            "migration_required": self.is_legacy_mount_active,
            "dual_mount_available": len(self.available_mounts) > 1
        }

    @lru_cache(maxsize=128)
    def resolve_path_with_fallback(self, user_path: str) -> str:
        """
        Resolve path with automatic fallback between mounts.

        This method tries the primary mount first, then falls back to other
        available mounts if the file/directory doesn't exist.

        Args:
            user_path: User-provided relative path

        Returns:
            First existing absolute path found

        Raises:
            FileNotFoundError: If path doesn't exist in any mount
        """
        attempted_paths = []

        # Try each available mount
        for mount in self.available_mounts:
            try:
                safe_path = self.get_safe_path(user_path, mount.path)
                if os.path.exists(safe_path):
                    return safe_path
                attempted_paths.append(safe_path)
            except (ValueError, FileNotFoundError):
                continue

        # No path found in any mount
        raise FileNotFoundError(
            f"Path '{user_path}' not found in any mount point. "
            f"Tried: {attempted_paths}"
        )


# Global instance
_path_resolver: Optional[PathResolver] = None


def get_path_resolver() -> PathResolver:
    """Get the global path resolver instance."""
    global _path_resolver
    if _path_resolver is None:
        _path_resolver = PathResolver()
    return _path_resolver


def clear_path_resolver_cache():
    """Clear the path resolver cache (for testing)."""
    global _path_resolver
    if _path_resolver:
        _path_resolver.resolve_path_with_fallback.cache_clear()


# Convenience functions for backward compatibility
def get_safe_path(user_path: str) -> str:
    """Get safe path using the global path resolver."""
    return get_path_resolver().get_safe_path(user_path)


def translate_legacy_path(legacy_path: str) -> Optional[str]:
    """Translate a legacy /shared-fs path to /source if available."""
    resolver = get_path_resolver()
    return resolver.translate_path(legacy_path, "/shared-fs", "/source")