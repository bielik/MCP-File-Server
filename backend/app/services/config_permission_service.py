"""
Config-file driven permission service with caching and formal precedence logic.

This service implements Phase 2 of the dynamic workspace system, providing
config-file based permissions with Trie-based caching for performance.
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.config import get_config, get_feature_flags
from app.utils.trie import CachedPermissionTrie, PermissionRule


class ConfigFileHandler(FileSystemEventHandler):
    """File system event handler for config file changes."""

    def __init__(self, permission_service: 'ConfigPermissionService'):
        self.permission_service = permission_service

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith('permissions.json'):
            self.permission_service._reload_config()


class ConfigPermissionService:
    """
    Permission service that reads rules from config file and provides
    high-performance caching with formal precedence logic.
    """

    def __init__(self):
        self.config = get_config()
        self.feature_flags = get_feature_flags()
        self.trie = CachedPermissionTrie(
            cache_max_size=self.config.PERMISSION_CACHE_MAX_SIZE,
            cache_ttl=self.config.PERMISSION_CACHE_TTL
        )

        # File watching
        self.observer = None
        self.config_file_hash = ""
        self.last_loaded_config = None

        # Load initial configuration
        self._load_config()
        self._setup_file_watcher()

    def _load_config(self):
        """Load permission rules from config file, creating default if missing."""
        config_path = self.config.get_permissions_config_path()

        if not config_path.exists():
            print(f"Permission config file not found at {config_path}")
            print("Creating default configuration from schema...")
            self._create_default_config()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # Calculate file hash for change detection
            with open(config_path, 'rb') as f:
                content = f.read()
                self.config_file_hash = hashlib.md5(content).hexdigest()

            self._parse_and_load_rules(config_data)
            self.last_loaded_config = config_data

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in permission config: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load permission config: {e}")

    def _create_default_config(self):
        """Create default permission configuration file."""
        config_path = self.config.get_permissions_config_path()

        # Ensure config directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Default configuration schema with minimal permissions for safety
        default_config = {
            "$schema": {
                "title": "Permission Configuration Schema",
                "description": "Schema for MCP KnowledgeExplorer permission rules",
                "version": "1.0.0"
            },
            "metadata": {
                "version": "1.0.0",
                "created_at": "auto-generated",
                "description": "Default permission configuration - PLEASE CUSTOMIZE FOR YOUR NEEDS"
            },
            "rules": [
                {
                    "id": "default-projects-read",
                    "path": "projects",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Default read access to projects directory",
                    "created_at": "auto-generated"
                },
                {
                    "id": "default-projects-write",
                    "path": "projects",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Default write access to projects directory",
                    "created_at": "auto-generated"
                }
            ],
            "precedence_rules": {
                "description": "Formal precedence rules for permission resolution",
                "rules": [
                    "1. Specificity: A rule on a child path is more specific than a rule on a parent path",
                    "2. Tie-Breaker: For rules of equal specificity, deny wins over allow",
                    "3. Implied Permissions: A write permission implicitly grants read",
                    "4. Default: If no rule matches, access is denied"
                ]
            },
            "validation": {
                "required_fields": ["id", "path", "permission_type", "rule_type"],
                "valid_permission_types": ["read", "write"],
                "valid_rule_types": ["allow", "deny"],
                "path_format": "Relative paths within /shared-fs mount point"
            }
        }

        # Write default config with atomic operation
        temp_path = config_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            # Atomic move
            temp_path.replace(config_path)
            print(f"✅ Created default permission config at {config_path}")
            print("⚠️  IMPORTANT: Review and customize the generated permissions for your security needs!")

        except Exception as e:
            # Clean up on error
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to create default config: {e}")

    def _parse_and_load_rules(self, config_data: Dict[str, Any]):
        """Parse config data and load rules into the trie."""
        # Clear existing rules
        self.trie.clear()

        # Validate config structure
        if 'rules' not in config_data:
            raise ValueError("Config file must contain 'rules' array")

        rules = config_data['rules']
        if not isinstance(rules, list):
            raise ValueError("'rules' must be an array")

        # Load each rule
        for rule_data in rules:
            try:
                rule = self._parse_rule(rule_data)
                self.trie.add_rule(rule)
            except Exception as e:
                # Log error but continue with other rules
                print(f"Warning: Failed to parse rule {rule_data.get('id', 'unknown')}: {e}")

    def _parse_rule(self, rule_data: Dict[str, Any]) -> PermissionRule:
        """Parse a single rule from config data."""
        required_fields = ['id', 'path', 'permission_type', 'rule_type']
        for field in required_fields:
            if field not in rule_data:
                raise ValueError(f"Rule missing required field: {field}")

        # Validate permission_type
        if rule_data['permission_type'] not in ['read', 'write']:
            raise ValueError(f"Invalid permission_type: {rule_data['permission_type']}")

        # Validate rule_type
        if rule_data['rule_type'] not in ['allow', 'deny']:
            raise ValueError(f"Invalid rule_type: {rule_data['rule_type']}")

        return PermissionRule(
            id=rule_data['id'],
            path=rule_data['path'],
            permission_type=rule_data['permission_type'],
            rule_type=rule_data['rule_type'],
            description=rule_data.get('description'),
            created_at=rule_data.get('created_at')
        )

    def _setup_file_watcher(self):
        """Setup file system watcher for config changes."""
        if not self.config.CONFIG_FILE_WATCH_ENABLED:
            return

        config_dir = self.config.CONFIG_DIR
        if not config_dir.exists():
            return

        try:
            self.observer = Observer()
            event_handler = ConfigFileHandler(self)
            self.observer.schedule(event_handler, str(config_dir), recursive=False)
            self.observer.start()
        except Exception as e:
            print(f"Warning: Failed to setup config file watcher: {e}")

    def _reload_config(self):
        """Reload configuration if file has changed."""
        config_path = self.config.get_permissions_config_path()

        if not config_path.exists():
            return

        try:
            # Check if file has actually changed
            with open(config_path, 'rb') as f:
                content = f.read()
                new_hash = hashlib.md5(content).hexdigest()

            if new_hash != self.config_file_hash:
                print("Config file changed, reloading permissions...")
                self._load_config()
                print("Permission config reloaded successfully")

        except Exception as e:
            print(f"Error reloading config: {e}")

    def check_access(self, path: str, operation: str) -> bool:
        """
        Check if a given operation is allowed on a path.
        Returns True if allowed, False if denied.
        """
        if operation not in ['read', 'write']:
            raise ValueError("Invalid operation type for permission check.")

        # Normalize the path for checking
        normalized_path = self._normalize_user_path(path)

        # Use the trie for permission checking
        is_allowed, matched_rule = self.trie.check_permission(normalized_path, operation)

        return is_allowed

    def check_access_with_rule(self, path: str, operation: str) -> Tuple[bool, Optional[PermissionRule]]:
        """
        Check access and return the matching rule for explanation purposes.
        Returns (is_allowed, matched_rule) tuple.
        """
        if operation not in ['read', 'write']:
            raise ValueError("Invalid operation type for permission check.")

        normalized_path = self._normalize_user_path(path)
        return self.trie.check_permission(normalized_path, operation)

    def get_safe_path(self, user_path: str) -> str:
        """
        Joins the user-provided path with the base shared directory and resolves it
        to an absolute path, preventing directory traversal.
        """
        # Normalize path to prevent '..' traversal before joining
        norm_user_path = os.path.normpath(user_path)
        if norm_user_path.startswith(('..', '/')):
            raise PermissionError(f"Path cannot be absolute or contain '..': {user_path}")

        # Join with the base path
        full_path = os.path.join(self.config.SHARED_FS_PATH, norm_user_path)

        # Resolve the absolute path and ensure it's within the shared directory
        abs_path = os.path.abspath(full_path)
        abs_shared_fs = os.path.abspath(self.config.SHARED_FS_PATH)

        if not abs_path.startswith(abs_shared_fs):
            raise PermissionError(f"Access denied: Path '{user_path}' is outside the allowed shared directory.")

        return abs_path

    def _normalize_user_path(self, user_path: str) -> str:
        """Normalize user path for rule matching."""
        # Remove leading slashes and normalize
        clean_path = user_path.lstrip('/')
        normalized = os.path.normpath(clean_path)

        # Handle root/empty paths
        if normalized in ('.', '', '/'):
            return ''

        return normalized

    def get_config_data(self) -> Dict[str, Any]:
        """Get the current configuration data."""
        return self.last_loaded_config or {}

    def get_config_etag(self) -> str:
        """Get ETag for the current configuration."""
        return self.config_file_hash

    def update_config(self, new_config: Dict[str, Any], expected_etag: str) -> str:
        """
        Update the configuration with optimistic locking.
        Returns new ETag on success, raises exception on conflict.
        """
        import logging
        logger = logging.getLogger(__name__)

        config_path = self.config.get_permissions_config_path()
        logger.info(f"update_config called: config_path={config_path}, expected_etag={expected_etag}")

        # Check current ETag
        current_etag = self.get_config_etag()
        logger.info(f"Current ETag: {current_etag}")
        if current_etag != expected_etag:
            raise ValueError(f"Config file has been modified by another process. Expected ETag: {expected_etag}, Current: {current_etag}")

        # Validate the new configuration
        self._validate_config(new_config)
        logger.info(f"Config validation passed. New config has {len(new_config.get('rules', []))} rules")

        # Atomic write: write to temp file first
        temp_path = config_path.with_suffix('.tmp')
        logger.info(f"Using temp file: {temp_path}")

        try:
            # Write to temporary file
            logger.info("Writing to temporary file...")
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)

            # Sync to disk
            logger.info("Syncing to disk...")
            with open(temp_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())

            # Atomic move
            logger.info(f"Performing atomic move from {temp_path} to {config_path}")
            if os.name == 'nt':  # Windows
                if config_path.exists():
                    logger.info("Removing existing config file on Windows")
                    config_path.unlink()
            temp_path.replace(config_path)
            logger.info("Atomic move completed")

            # Reload the configuration
            logger.info("Reloading configuration...")
            self._load_config()

            new_etag = self.get_config_etag()
            logger.info(f"Configuration updated successfully. New ETag: {new_etag}")
            return new_etag

        except Exception as e:
            logger.error(f"Error during config update: {e}")
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _validate_config(self, config_data: Dict[str, Any]):
        """Validate configuration data before saving."""
        if not isinstance(config_data, dict):
            raise ValueError("Config must be a JSON object")

        if 'rules' not in config_data:
            raise ValueError("Config must contain 'rules' array")

        rules = config_data['rules']
        if not isinstance(rules, list):
            raise ValueError("'rules' must be an array")

        # Validate each rule
        seen_ids = set()
        for rule_data in rules:
            if not isinstance(rule_data, dict):
                raise ValueError("Each rule must be an object")

            # Check for duplicate IDs
            rule_id = rule_data.get('id')
            if rule_id in seen_ids:
                raise ValueError(f"Duplicate rule ID: {rule_id}")
            seen_ids.add(rule_id)

            # Validate rule structure
            self._parse_rule(rule_data)  # This will raise if invalid

    def get_stats(self) -> Dict[str, Any]:
        """Get performance and configuration statistics."""
        trie_stats = self.trie.get_stats()

        return {
            "config_file_path": str(self.config.get_permissions_config_path()),
            "config_file_hash": self.config_file_hash,
            "file_watcher_enabled": self.config.CONFIG_FILE_WATCH_ENABLED,
            "last_reload_time": None,  # TODO: Track reload times
            **trie_stats
        }

    def shutdown(self):
        """Cleanup resources on shutdown."""
        if self.observer:
            self.observer.stop()
            self.observer.join()


# Legacy support: maintain the same interface as the original permission service
PERMISSIONS = {
    "context": ["docs", "projects", "materials"],
    "working": ["projects", "output"],
}

SHARED_FS_PATH = "/shared-fs"

# Global instance
_config_service = None


def get_permission_service() -> ConfigPermissionService:
    """Get the global permission service instance."""
    global _config_service
    if _config_service is None:
        _config_service = ConfigPermissionService()
    return _config_service


def check_access(path: str, operation: str) -> bool:
    """
    Legacy function that checks permissions.
    Routes to config service if Phase 2 is enabled, otherwise uses hardcoded logic.
    """
    feature_flags = get_feature_flags()

    if feature_flags.is_config_permissions_enabled():
        # Use new config-based service
        service = get_permission_service()
        return service.check_access(path, operation)
    else:
        # Use legacy hardcoded logic
        return _legacy_check_access(path, operation)


def get_safe_path(user_path: str) -> str:
    """
    Legacy function that gets safe path.
    Routes to config service if Phase 2 is enabled, otherwise uses original logic.
    """
    feature_flags = get_feature_flags()

    if feature_flags.is_config_permissions_enabled():
        service = get_permission_service()
        return service.get_safe_path(user_path)
    else:
        return _legacy_get_safe_path(user_path)


def _legacy_check_access(path: str, operation: str) -> bool:
    """Original hardcoded permission checking logic."""
    if operation not in ['read', 'write']:
        raise ValueError("Invalid operation type for permission check.")

    # Get the top-level directory from the user path
    try:
        top_level_dir = path.strip('/').split('/')[0]
    except IndexError:
        top_level_dir = ""  # Root of shared-fs

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
    _legacy_get_safe_path(path)

    return True


def _legacy_get_safe_path(user_path: str) -> str:
    """Original safe path logic."""
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