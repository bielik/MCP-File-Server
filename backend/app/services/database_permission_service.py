"""
Database-driven permission service with caching and audit logging.

This service implements Phase 3A of the dynamic workspace system, providing
database-backed permissions with Trie-based caching for performance and
comprehensive audit logging.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from sqlalchemy.orm import Session

from app.config import get_config, get_feature_flags
from app.database import SessionLocal
from app.models.workspace import Workspace, Permission
from app.crud.workspace import workspace_crud, permission_crud
from app.utils.trie import CachedPermissionTrie, PermissionRule
from app.schemas.workspace import MatchedRuleInfo, EffectivePermissionResult
from app.services.audit_logger import get_audit_logger


logger = logging.getLogger(__name__)



class DatabasePermissionService:
    """
    Permission service that reads rules from database and provides
    high-performance caching with formal precedence logic and audit logging.
    """

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self.config = get_config()
        self.feature_flags = get_feature_flags()
        self.trie = CachedPermissionTrie(
            cache_max_size=self.config.PERMISSION_CACHE_MAX_SIZE,
            cache_ttl=self.config.PERMISSION_CACHE_TTL
        )

        # Allow dependency injection of session factory for testing
        self.session_factory = session_factory or SessionLocal

        # Active workspace tracking
        self.active_workspace_id: Optional[int] = None
        self.rules_loaded_at: Optional[datetime] = None

        # Audit logging
        self.audit_logger = get_audit_logger()

        # Load initial rules
        self._load_active_workspace_rules()

    def _get_db_session(self) -> Session:
        """Get a database session."""
        session = self.session_factory()
        # For testing scenarios, the session factory might return the same instance
        # In that case, don't close it in finally blocks
        return session

    def _load_active_workspace_rules(self):
        """Load permission rules from the currently active workspace."""
        db = self._get_db_session()
        try:
            # Force a fresh read by committing any pending transactions
            try:
                db.commit()
            except Exception:
                # For test sessions, commit might fail, that's OK
                pass

            # Find active workspace
            active_workspace = workspace_crud.get_active_workspace(db)
            if not active_workspace:
                logger.warning("No active workspace found - using empty rule set")
                self.trie.clear()
                self.active_workspace_id = None
                return

            # Check if we need to reload
            if (self.active_workspace_id == active_workspace.id and
                self.rules_loaded_at):
                # Convert workspace updated_at to timezone-aware for comparison
                workspace_updated = active_workspace.updated_at
                if workspace_updated.tzinfo is None:
                    workspace_updated = workspace_updated.replace(tzinfo=timezone.utc)

                if self.rules_loaded_at >= workspace_updated:
                    # Rules are already up to date
                    return

            logger.info(f"Loading rules from active workspace: {active_workspace.name} (ID: {active_workspace.id})")

            # Load permissions for active workspace
            permissions = permission_crud.get_active_workspace_permissions(db)

            # Clear existing rules and load new ones
            self.trie.clear()
            for permission in permissions:
                rule = PermissionRule(
                    id=f"db-rule-{permission.id}",
                    path=permission.path.replace('\\', '/'),  # Normalize path separators
                    permission_type=permission.permission_type,
                    rule_type=permission.rule_type,
                    description=permission.description,
                    created_at=permission.created_at.isoformat() if permission.created_at else None
                )
                self.trie.add_rule(rule)

            self.active_workspace_id = active_workspace.id
            self.rules_loaded_at = datetime.now(timezone.utc)

            logger.info(f"Loaded {len(permissions)} permission rules from workspace '{active_workspace.name}'")

        except Exception as e:
            logger.error(f"Failed to load workspace rules: {e}")
            raise RuntimeError(f"Failed to load permission rules: {e}")
        finally:
            # Only close if it's not the same instance (testing scenario)
            if hasattr(db, '_is_test_session') or getattr(db, 'info', {}).get('test_session'):
                pass  # Don't close test sessions
            else:
                db.close()

    def invalidate_cache(self, workspace_id: Optional[int] = None):
        """
        Invalidate permission cache.

        Args:
            workspace_id: If provided, only invalidate if it matches the active workspace
        """
        if workspace_id is None or workspace_id == self.active_workspace_id:
            self.trie.clear_cache()
            self.rules_loaded_at = None
            # Clear the current workspace ID to force full reload
            self.active_workspace_id = None
            logger.info(f"Permission cache invalidated for workspace {workspace_id}")
            # Force immediate reload of rules with fresh database connection
            self._load_active_workspace_rules()

    def reload_rules(self, force: bool = False):
        """
        Reload permission rules from database.

        Args:
            force: If True, reload even if rules appear up to date
        """
        if force:
            self.rules_loaded_at = None
        self._load_active_workspace_rules()

    def check_access(self, path: str, operation: str) -> bool:
        """
        Check if a given operation is allowed on a path.
        Returns True if allowed, False if denied.
        """
        is_allowed, matched_rule = self.check_access_with_rule(path, operation)
        return is_allowed

    def check_access_with_rule(self, path: str, operation: str) -> Tuple[bool, Optional[PermissionRule]]:
        """
        Check access and return the matching rule for explanation purposes.
        Returns (is_allowed, matched_rule) tuple.
        """
        if operation not in ['read', 'write']:
            raise ValueError("Invalid operation type for permission check.")

        # Ensure rules are loaded
        self._load_active_workspace_rules()

        # Normalize the path for checking
        normalized_path = self._normalize_user_path(path)

        # Use the trie for permission checking
        is_allowed, matched_rule = self.trie.check_permission(normalized_path, operation)

        # Log audit event
        self._log_audit_event(
            event_type="permission_check",
            path=path,
            operation=operation,
            result="allowed" if is_allowed else "denied",
            matched_rule_id=matched_rule.id if matched_rule else None,
            workspace_id=self.active_workspace_id
        )

        return is_allowed, matched_rule

    def batch_check_permissions(self, paths: List[str], workspace_id: Optional[int] = None) -> List[EffectivePermissionResult]:
        """
        Check permissions for multiple paths efficiently.

        This is the core method for the batch effective permissions API.

        Args:
            paths: List of paths to check
            workspace_id: Specific workspace to check against (defaults to active)

        Returns:
            List of permission results with matched rule information
        """
        # Ensure rules are loaded for the correct workspace
        if workspace_id and workspace_id != self.active_workspace_id:
            # Need to temporarily load rules for a different workspace
            return self._batch_check_specific_workspace(paths, workspace_id)
        else:
            # Use currently loaded active workspace rules
            self._load_active_workspace_rules()
            return self._batch_check_current_rules(paths)

    def _batch_check_specific_workspace(self, paths: List[str], workspace_id: int) -> List[EffectivePermissionResult]:
        """Check permissions against a specific workspace."""
        db = self._get_db_session()
        try:
            # Get workspace
            workspace = workspace_crud.get_workspace(db, workspace_id)
            if not workspace:
                raise ValueError(f"Workspace {workspace_id} not found")

            # Get permissions for this workspace
            permissions = permission_crud.get_workspace_permissions(db, workspace_id)

            # Create temporary trie for this workspace
            temp_trie = CachedPermissionTrie(cache_max_size=1000, cache_ttl=300)
            for permission in permissions:
                rule = PermissionRule(
                    id=f"db-rule-{permission.id}",
                    path=permission.path.replace('\\', '/'),  # Normalize path separators
                    permission_type=permission.permission_type,
                    rule_type=permission.rule_type,
                    description=permission.description,
                    created_at=permission.created_at.isoformat() if permission.created_at else None
                )
                temp_trie.add_rule(rule)

            # Check all paths against this trie
            results = []
            for path in paths:
                normalized_path = self._normalize_user_path(path)

                # Check both read and write permissions
                read_allowed, read_rule = temp_trie.check_permission(normalized_path, "read")
                write_allowed, write_rule = temp_trie.check_permission(normalized_path, "write")

                # Determine final status - prioritize deny rules first
                # Check for explicit deny rules regardless of allow rules
                if read_rule and read_rule.rule_type == "deny":
                    status = "denied"
                    matched_rule = read_rule
                elif write_rule and write_rule.rule_type == "deny":
                    status = "denied"
                    matched_rule = write_rule
                elif write_allowed:
                    status = "write"
                    matched_rule = write_rule
                elif read_allowed:
                    status = "read"
                    matched_rule = read_rule
                else:
                    # No matching rule - default deny
                    status = "none"
                    matched_rule = None

                # Convert matched rule to response format
                matched_rule_info = None
                if matched_rule:
                    matched_rule_info = MatchedRuleInfo(
                        id=matched_rule.id,
                        path=matched_rule.path,
                        permission_type=matched_rule.permission_type,
                        rule_type=matched_rule.rule_type,
                        description=matched_rule.description,
                        workspace_id=workspace_id
                    )

                results.append(EffectivePermissionResult(
                    path=path,
                    status=status,
                    matched_rule=matched_rule_info
                ))

            return results

        finally:
            db.close()

    def _batch_check_current_rules(self, paths: List[str]) -> List[EffectivePermissionResult]:
        """Check permissions against currently loaded rules."""
        results = []

        for path in paths:
            normalized_path = self._normalize_user_path(path)

            # Check both read and write permissions
            read_allowed, read_rule = self.trie.check_permission(normalized_path, "read")
            write_allowed, write_rule = self.trie.check_permission(normalized_path, "write")

            # Determine final status and rule - prioritize deny rules first
            # Check for explicit deny rules regardless of allow rules
            if read_rule and read_rule.rule_type == "deny":
                status = "denied"
                matched_rule = read_rule
            elif write_rule and write_rule.rule_type == "deny":
                status = "denied"
                matched_rule = write_rule
            elif write_allowed:
                status = "write"
                matched_rule = write_rule
            elif read_allowed:
                status = "read"
                matched_rule = read_rule
            else:
                # No matching rule - default deny
                status = "none"
                matched_rule = None

            # Convert matched rule to response format
            matched_rule_info = None
            if matched_rule:
                matched_rule_info = MatchedRuleInfo(
                    id=matched_rule.id,
                    path=matched_rule.path,
                    permission_type=matched_rule.permission_type,
                    rule_type=matched_rule.rule_type,
                    description=matched_rule.description,
                    workspace_id=self.active_workspace_id
                )

            results.append(EffectivePermissionResult(
                path=path,
                status=status,
                matched_rule=matched_rule_info
            ))

        # Log single batch audit event instead of individual events for performance
        self._log_batch_audit_event(
            event_type="batch_permission_check",
            paths_count=len(paths),
            workspace_id=self.active_workspace_id
        )

        return results

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

        # Convert backslashes to forward slashes for consistency across platforms
        return normalized.replace('\\', '/')

    def _log_audit_event(
        self,
        event_type: str,
        path: str,
        operation: str,
        result: str,
        matched_rule_id: Optional[str] = None,
        workspace_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an audit event using the audit logger."""
        # Create matched rule dict if we have a rule
        matched_rule = None
        if matched_rule_id and result == "allowed":
            # Find the rule from our trie cache
            _, rule = self.trie.check_permission(self._normalize_user_path(path), operation)
            if rule:
                matched_rule = {
                    "id": rule.id,
                    "path": rule.path,
                    "permission_type": rule.permission_type,
                    "rule_type": rule.rule_type,
                    "description": rule.description
                }

        # Log to audit logger
        self.audit_logger.log_permission_decision(
            path=path,
            operation=operation,
            result=(result == "allowed"),
            matched_rule=matched_rule,
            workspace_id=workspace_id
        )

        # Log to application logger
        logger.debug(f"AUDIT: {event_type} - {path} ({operation}) = {result}")

    def _log_batch_audit_event(
        self,
        event_type: str,
        paths_count: int,
        workspace_id: Optional[int] = None
    ):
        """Log a batch audit event for performance optimization."""
        # Log to audit logger
        self.audit_logger.log_permission_decision(
            path=f"BATCH_{paths_count}_paths",
            operation="batch_check",
            result=True,  # Batch operation succeeded
            matched_rule=None,
            workspace_id=workspace_id
        )

        # Log to application logger
        logger.debug(f"AUDIT: {event_type} - BATCH operation for {paths_count} paths")

    def get_audit_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        workspace_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent audit events with optional filtering.

        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type
            workspace_id: Filter by workspace ID

        Returns:
            List of audit event dictionaries, most recent first
        """
        return self.audit_logger.get_events(
            event_type=event_type,
            workspace_id=workspace_id,
            limit=limit
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get performance and configuration statistics."""
        trie_stats = self.trie.get_stats()

        db = self._get_db_session()
        try:
            active_workspace = workspace_crud.get_active_workspace(db)
            total_workspaces = workspace_crud.get_workspaces_count(db)

            workspace_info = None
            if active_workspace:
                permission_count = permission_crud.get_workspace_permissions_count(db, active_workspace.id)
                workspace_info = {
                    "id": active_workspace.id,
                    "name": active_workspace.name,
                    "permission_count": permission_count,
                    "updated_at": active_workspace.updated_at.isoformat()
                }

        finally:
            db.close()

        return {
            "service_type": "database_permission_service",
            "active_workspace": workspace_info,
            "total_workspaces": total_workspaces,
            "rules_loaded_at": self.rules_loaded_at.isoformat() if self.rules_loaded_at else None,
            "audit_events_count": self.audit_logger.get_event_count(),
            **trie_stats
        }


# Global instance
_database_service = None


def get_database_permission_service(session_factory: Optional[Callable[[], Session]] = None) -> DatabasePermissionService:
    """Get the global database permission service instance."""
    global _database_service
    if _database_service is None:
        _database_service = DatabasePermissionService(session_factory=session_factory)
    return _database_service


def reset_database_permission_service():
    """Reset the global database permission service instance. Used for testing."""
    global _database_service
    _database_service = None


# Phase 3A integration functions
def check_access(path: str, operation: str) -> bool:
    """
    Main permission checking function that routes to appropriate service.
    Routes to database service if Phase 3A is enabled.
    """
    feature_flags = get_feature_flags()

    if feature_flags.is_database_permissions_enabled():
        # Use new database-based service
        service = get_database_permission_service()
        return service.check_access(path, operation)
    elif feature_flags.is_config_permissions_enabled():
        # Use Phase 2 config service
        from app.services.config_permission_service import get_permission_service
        service = get_permission_service()
        return service.check_access(path, operation)
    else:
        # Use legacy hardcoded logic
        from app.services.config_permission_service import _legacy_check_access
        return _legacy_check_access(path, operation)


def get_safe_path(user_path: str) -> str:
    """
    Main safe path function that routes to appropriate service.
    Routes to database service if Phase 3A is enabled.
    """
    feature_flags = get_feature_flags()

    if feature_flags.is_database_permissions_enabled():
        service = get_database_permission_service()
        return service.get_safe_path(user_path)
    elif feature_flags.is_config_permissions_enabled():
        from app.services.config_permission_service import get_permission_service
        service = get_permission_service()
        return service.get_safe_path(user_path)
    else:
        from app.services.config_permission_service import _legacy_get_safe_path
        return _legacy_get_safe_path(user_path)