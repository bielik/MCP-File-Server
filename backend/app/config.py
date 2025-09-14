"""
Configuration and feature flags for the MCP KnowledgeExplorer.

This module manages feature flags for the dynamic workspace system
and other configuration settings.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path


class FeatureFlags:
    """
    Feature flag management for gradual rollout of new features.

    Feature flags allow for safe deployment and rollback of new functionality.
    They should be used to wrap new code paths during development and testing.
    """

    def __init__(self):
        # Phase 2 feature flags
        self.ENABLE_CONFIG_FILE_PERMISSIONS = self._get_bool_env(
            "ENABLE_CONFIG_FILE_PERMISSIONS", False
        )

        # Phase 3 feature flags (for future use)
        self.ENABLE_DATABASE_PERMISSIONS = self._get_bool_env(
            "ENABLE_DATABASE_PERMISSIONS", False
        )

        # Development and debugging flags
        self.DEBUG_PERMISSION_CACHE = self._get_bool_env(
            "DEBUG_PERMISSION_CACHE", False
        )

        self.ENABLE_PERFORMANCE_METRICS = self._get_bool_env(
            "ENABLE_PERFORMANCE_METRICS", False
        )

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with default fallback."""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    def is_config_permissions_enabled(self) -> bool:
        """Check if config file permissions are enabled."""
        return self.ENABLE_CONFIG_FILE_PERMISSIONS

    def is_database_permissions_enabled(self) -> bool:
        """Check if database permissions are enabled."""
        return self.ENABLE_DATABASE_PERMISSIONS

    def to_dict(self) -> Dict[str, bool]:
        """Convert feature flags to dictionary for API responses."""
        return {
            "ENABLE_CONFIG_FILE_PERMISSIONS": self.ENABLE_CONFIG_FILE_PERMISSIONS,
            "ENABLE_DATABASE_PERMISSIONS": self.ENABLE_DATABASE_PERMISSIONS,
            "DEBUG_PERMISSION_CACHE": self.DEBUG_PERMISSION_CACHE,
            "ENABLE_PERFORMANCE_METRICS": self.ENABLE_PERFORMANCE_METRICS,
        }


class Config:
    """
    Application configuration settings.

    This class centralizes all configuration management including
    paths, database settings, and other application parameters.
    """

    def __init__(self):
        # Base paths
        self.BASE_DIR = Path(__file__).parent.parent.parent
        self.CONFIG_DIR = self.BASE_DIR / "config"
        self.DATA_DIR = self.BASE_DIR / "data"
        self.SHARED_FS_PATH = "/shared-fs"

        # Permission configuration
        self.PERMISSIONS_CONFIG_FILE = self.CONFIG_DIR / "permissions.json"

        # Database configuration
        self.DATABASE_PATH = self.DATA_DIR / "database.db"
        self.DATABASE_URL = f"sqlite:///{self.DATABASE_PATH}"

        # Server configuration
        self.BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
        self.FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 5173))

        # Performance settings
        self.PERMISSION_CACHE_TTL = int(os.getenv("PERMISSION_CACHE_TTL", 300))  # 5 minutes
        self.PERMISSION_CACHE_MAX_SIZE = int(os.getenv("PERMISSION_CACHE_MAX_SIZE", 10000))

        # File watcher settings
        self.CONFIG_FILE_WATCH_ENABLED = self._get_bool_env("CONFIG_FILE_WATCH_ENABLED", True)

        # Security settings
        self.ETAG_SECRET = os.getenv("ETAG_SECRET", "default-secret-change-in-production")

        # Create directories if they don't exist
        self._ensure_directories_exist()

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with default fallback."""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    def _ensure_directories_exist(self):
        """Create necessary directories if they don't exist."""
        self.CONFIG_DIR.mkdir(exist_ok=True)
        self.DATA_DIR.mkdir(exist_ok=True)

    def get_permissions_config_path(self) -> Path:
        """Get the path to the permissions configuration file."""
        return self.PERMISSIONS_CONFIG_FILE

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for API responses."""
        return {
            "base_dir": str(self.BASE_DIR),
            "config_dir": str(self.CONFIG_DIR),
            "data_dir": str(self.DATA_DIR),
            "shared_fs_path": self.SHARED_FS_PATH,
            "permissions_config_file": str(self.PERMISSIONS_CONFIG_FILE),
            "backend_port": self.BACKEND_PORT,
            "frontend_port": self.FRONTEND_PORT,
            "permission_cache_ttl": self.PERMISSION_CACHE_TTL,
            "permission_cache_max_size": self.PERMISSION_CACHE_MAX_SIZE,
            "config_file_watch_enabled": self.CONFIG_FILE_WATCH_ENABLED,
        }


# Global instances
feature_flags = FeatureFlags()
config = Config()


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance."""
    return feature_flags


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def is_phase2_enabled() -> bool:
    """Check if Phase 2 features (config file permissions) are enabled."""
    return feature_flags.is_config_permissions_enabled()


def is_phase3_enabled() -> bool:
    """Check if Phase 3 features (database permissions) are enabled."""
    return feature_flags.is_database_permissions_enabled()