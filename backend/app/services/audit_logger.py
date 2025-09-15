"""
Audit logging service for Phase 3A permission decisions.

This module provides structured audit logging capabilities for all permission
decisions, enabling compliance tracking and debugging of permission resolution.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import json
from collections import deque
import threading


class AuditLogger:
    """
    Audit logger for permission decisions and system events.

    Maintains an in-memory log of permission decisions with configurable
    retention limits and thread-safe operations.
    """

    def __init__(self, max_events: int = 10000):
        """Initialize audit logger with maximum event retention."""
        self.max_events = max_events
        self._events = deque(maxlen=max_events)
        self._lock = threading.RLock()

    def log_permission_decision(self,
                               path: str,
                               operation: str,
                               result: bool,
                               matched_rule: Optional[Dict[str, Any]] = None,
                               workspace_id: Optional[int] = None,
                               user_id: Optional[str] = None) -> None:
        """
        Log a permission decision event.

        Args:
            path: The path that was checked
            operation: The operation attempted ('read', 'write')
            result: True if access was granted, False if denied
            matched_rule: The rule that matched (None for default deny)
            workspace_id: ID of the workspace context
            user_id: ID of the user making the request
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": path,
            "operation": operation,
            "result": result,
            "matched_rule": matched_rule,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "event_type": "permission_decision"
        }

        with self._lock:
            self._events.append(event)

    def log_workspace_activation(self, workspace_id: int, workspace_name: str) -> None:
        """Log workspace activation event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "workspace_activation",
            "workspace_id": workspace_id,
            "workspace_name": workspace_name
        }

        with self._lock:
            self._events.append(event)

    def log_permission_rule_change(self,
                                  action: str,  # 'create', 'update', 'delete'
                                  rule_data: Dict[str, Any],
                                  user_id: Optional[str] = None) -> None:
        """Log permission rule modification event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "permission_rule_change",
            "action": action,
            "rule_data": rule_data,
            "user_id": user_id
        }

        with self._lock:
            self._events.append(event)

    def get_events(self,
                  event_type: Optional[str] = None,
                  workspace_id: Optional[int] = None,
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve audit events with optional filtering.

        Args:
            event_type: Filter by event type
            workspace_id: Filter by workspace ID
            limit: Maximum number of events to return

        Returns:
            List of audit events in reverse chronological order (newest first)
        """
        with self._lock:
            events = list(self._events)

        # Filter events
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]

        if workspace_id is not None:
            events = [e for e in events if e.get("workspace_id") == workspace_id]

        # Reverse to get newest first
        events.reverse()

        # Apply limit
        if limit:
            events = events[:limit]

        return events

    def get_permission_events(self,
                            path: Optional[str] = None,
                            operation: Optional[str] = None,
                            result: Optional[bool] = None,
                            limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get permission decision events with specific filtering.

        Args:
            path: Filter by exact path match
            operation: Filter by operation type
            result: Filter by result (True/False)
            limit: Maximum number of events to return
        """
        events = self.get_events(event_type="permission_decision", limit=None)

        # Apply additional filters
        if path is not None:
            events = [e for e in events if e.get("path") == path]

        if operation is not None:
            events = [e for e in events if e.get("operation") == operation]

        if result is not None:
            events = [e for e in events if e.get("result") == result]

        # Apply limit
        if limit:
            events = events[:limit]

        return events

    def clear_events(self) -> None:
        """Clear all audit events."""
        with self._lock:
            self._events.clear()

    def get_event_count(self) -> int:
        """Get total number of events stored."""
        with self._lock:
            return len(self._events)

    def export_events(self,
                     event_type: Optional[str] = None,
                     workspace_id: Optional[int] = None) -> str:
        """
        Export events as JSON string for external processing.

        Args:
            event_type: Filter by event type
            workspace_id: Filter by workspace ID

        Returns:
            JSON string containing matching events
        """
        events = self.get_events(event_type=event_type, workspace_id=workspace_id)
        return json.dumps(events, indent=2)


# Global audit logger instance
_audit_logger = None
_logger_lock = threading.RLock()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance (singleton pattern)."""
    global _audit_logger

    with _logger_lock:
        if _audit_logger is None:
            _audit_logger = AuditLogger()
        return _audit_logger


def configure_audit_logger(max_events: int = 10000) -> AuditLogger:
    """Configure and return the global audit logger."""
    global _audit_logger

    with _logger_lock:
        _audit_logger = AuditLogger(max_events=max_events)
        return _audit_logger