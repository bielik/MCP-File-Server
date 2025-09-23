"""
Configuration and feature flags for the MCP KnowledgeExplorer.

This module manages feature flags for the dynamic workspace system
and other configuration settings. Now uses Phase4AConfig for consistency.
"""

import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add config directory to path for Phase4AConfig import
sys.path.append('/config')

# Import Phase4AConfig for single source of truth
from env_config import get_config as get_phase4a_config, Phase4AConfig


class FeatureFlags:
    """
    Feature flag management for gradual rollout of new features.

    Feature flags allow for safe deployment and rollback of new functionality.
    They should be used to wrap new code paths during development and testing.
    """

    def __init__(self):
        # Phase 2 feature flags (legacy - not used in Phase 3B+)
        self.ENABLE_CONFIG_FILE_PERMISSIONS = self._get_bool_env(
            "ENABLE_CONFIG_FILE_PERMISSIONS", False
        )

        # Phase 3 feature flags (re-enabled for proper Phase 4A functionality)
        self.ENABLE_DATABASE_PERMISSIONS = True  # Re-enabled for Phase 4A

        # Phase 4 feature flags (migration & deprecation)
        self.ENABLE_SOURCE_MOUNT = self._get_bool_env(
            "ENABLE_SOURCE_MOUNT", False
        )

        self.SHOW_DEPRECATION_WARNING = self._get_bool_env(
            "SHOW_DEPRECATION_WARNING", True
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
            "ENABLE_SOURCE_MOUNT": self.ENABLE_SOURCE_MOUNT,
            "SHOW_DEPRECATION_WARNING": self.SHOW_DEPRECATION_WARNING,
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
        # Use Docker volume mount path for database in container
        # In Docker, always use /data. Outside Docker, use ./data
        self.DATA_DIR = Path("/data") if Path("/data").exists() else self.BASE_DIR / "data"
        self.SHARED_FS_PATH = "/source"   # Primary mount point (updated for Phase 4A)
        self.SOURCE_MOUNT_PATH = "/source"   # New primary mount point

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
            "source_mount_path": self.SOURCE_MOUNT_PATH,
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


def get_config():
    """Get the global configuration instance with backward compatibility."""
    # Get Phase4A config
    phase4a_config = get_phase4a_config()

    # Create a hybrid config object that includes both old and new attributes
    class HybridConfig:
        def __init__(self, phase4a_config):
            # Copy all Phase4A attributes
            for attr in dir(phase4a_config):
                if not attr.startswith('_'):
                    setattr(self, attr, getattr(phase4a_config, attr))

            # Standardized database URL construction
            # In Docker containers, always use /data regardless of DATABASE_PATH env var
            import os
            if os.path.exists('/data'):
                # Running in Docker container
                database_path = '/data'
            else:
                # Running locally
                database_path = getattr(phase4a_config, 'DATABASE_PATH', './data')

            # Normalize the database path - ensure it points to the database file, not directory
            from pathlib import Path
            db_path = Path(database_path)

            # If it's a directory path, append database.db
            if not str(db_path).endswith('.db'):
                db_path = db_path / 'database.db'

            self.DATABASE_URL = f"sqlite:///{db_path}"

            # Log the effective database URL for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Database URL configured: {self.DATABASE_URL}")

    return HybridConfig(phase4a_config)


def is_phase2_enabled() -> bool:
    """Check if Phase 2 features (config file permissions) are enabled."""
    return feature_flags.is_config_permissions_enabled()


def is_phase3_enabled() -> bool:
    """Check if Phase 3 features (database permissions) are enabled."""
    return feature_flags.is_database_permissions_enabled()