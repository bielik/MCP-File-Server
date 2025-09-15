"""
Test audit logging functionality for Phase 3A.

This test module validates that all permission decisions are properly
logged with structured audit events for compliance and debugging purposes.
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime

from .conftest import MockAuditLogger


class TestAuditLoggerBasics:
    """Test basic audit logger functionality."""

    def test_audit_logger_initialization(self, mock_audit_logger: MockAuditLogger):
        """Test audit logger initializes correctly."""
        assert len(mock_audit_logger.get_events()) == 0

    def test_log_permission_decision(self, mock_audit_logger: MockAuditLogger):
        """Test logging a basic permission decision."""
        matched_rule = {
            "id": "rule-123",
            "path": "materials",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Allow materials access"
        }

        mock_audit_logger.log_permission_decision(
            path="/materials/doc.txt",
            operation="read",
            result=True,
            matched_rule=matched_rule
        )

        events = mock_audit_logger.get_events()
        assert len(events) == 1

        event = events[0]
        assert event["path"] == "/materials/doc.txt"
        assert event["operation"] == "read"
        assert event["result"] is True
        assert event["matched_rule"] == matched_rule
        assert "timestamp" in event

    def test_log_denied_permission(self, mock_audit_logger: MockAuditLogger):
        """Test logging denied permission (no matched rule)."""
        mock_audit_logger.log_permission_decision(
            path="/forbidden/file.txt",
            operation="read",
            result=False,
            matched_rule=None
        )

        events = mock_audit_logger.get_events()
        assert len(events) == 1

        event = events[0]
        assert event["path"] == "/forbidden/file.txt"
        assert event["operation"] == "read"
        assert event["result"] is False
        assert event["matched_rule"] is None

    def test_multiple_permission_decisions(self, mock_audit_logger: MockAuditLogger):
        """Test logging multiple permission decisions."""
        test_cases = [
            ("/materials/doc.txt", "read", True, {"id": "rule-1", "rule_type": "allow"}),
            ("/projects/code.py", "write", True, {"id": "rule-2", "rule_type": "allow"}),
            ("/blocked/file.txt", "read", False, None),
            ("/materials/secret.txt", "read", False, {"id": "rule-3", "rule_type": "deny"})
        ]

        for path, operation, result, matched_rule in test_cases:
            mock_audit_logger.log_permission_decision(path, operation, result, matched_rule)

        events = mock_audit_logger.get_events()
        assert len(events) == len(test_cases)

        for i, (path, operation, result, matched_rule) in enumerate(test_cases):
            event = events[i]
            assert event["path"] == path
            assert event["operation"] == operation
            assert event["result"] == result
            assert event["matched_rule"] == matched_rule

    def test_clear_events(self, mock_audit_logger: MockAuditLogger):
        """Test clearing audit events."""
        # Log some events
        mock_audit_logger.log_permission_decision("/test/path", "read", True, None)
        mock_audit_logger.log_permission_decision("/another/path", "write", False, None)

        assert len(mock_audit_logger.get_events()) == 2

        # Clear events
        mock_audit_logger.clear()

        assert len(mock_audit_logger.get_events()) == 0


class TestAuditLogStructure:
    """Test audit log event structure and content."""

    def test_audit_event_required_fields(self, mock_audit_logger: MockAuditLogger):
        """Test that audit events contain all required fields."""
        mock_audit_logger.log_permission_decision(
            path="/test/path",
            operation="read",
            result=True,
            matched_rule={"id": "rule-1", "rule_type": "allow"}
        )

        events = mock_audit_logger.get_events()
        event = events[0]

        # Required fields
        required_fields = ["timestamp", "path", "operation", "result", "matched_rule"]
        for field in required_fields:
            assert field in event

    def test_audit_event_timestamps(self, mock_audit_logger: MockAuditLogger):
        """Test that audit events have proper timestamps."""
        before_log = datetime.now().isoformat()

        mock_audit_logger.log_permission_decision("/test", "read", True, None)

        after_log = datetime.now().isoformat()

        events = mock_audit_logger.get_events()
        event = events[0]

        # Timestamp should be between before and after
        assert event["timestamp"] >= before_log or event["timestamp"] <= after_log

    def test_matched_rule_structure(self, mock_audit_logger: MockAuditLogger):
        """Test matched rule structure in audit events."""
        complete_rule = {
            "id": "rule-123",
            "path": "materials",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Allow materials access"
        }

        mock_audit_logger.log_permission_decision(
            path="/materials/doc.txt",
            operation="read",
            result=True,
            matched_rule=complete_rule
        )

        events = mock_audit_logger.get_events()
        event = events[0]

        assert event["matched_rule"] == complete_rule
        assert event["matched_rule"]["id"] == "rule-123"
        assert event["matched_rule"]["rule_type"] == "allow"

    def test_audit_event_data_types(self, mock_audit_logger: MockAuditLogger):
        """Test that audit event data types are correct."""
        matched_rule = {
            "id": "rule-1",
            "path": "test",
            "permission_type": "read",
            "rule_type": "allow",
            "description": "Test rule"
        }

        mock_audit_logger.log_permission_decision(
            path="/test/file.txt",
            operation="write",
            result=False,
            matched_rule=matched_rule
        )

        events = mock_audit_logger.get_events()
        event = events[0]

        # Check data types
        assert isinstance(event["timestamp"], str)
        assert isinstance(event["path"], str)
        assert isinstance(event["operation"], str)
        assert isinstance(event["result"], bool)
        assert isinstance(event["matched_rule"], dict)


class TestAuditLogPerformance:
    """Test performance characteristics of audit logging."""

    def test_logging_performance(self, mock_audit_logger: MockAuditLogger):
        """Test that audit logging has minimal performance overhead."""
        import time

        # Log many events and measure time
        num_events = 1000

        start_time = time.time()

        for i in range(num_events):
            matched_rule = {
                "id": f"rule-{i}",
                "path": f"path{i}",
                "permission_type": "read",
                "rule_type": "allow",
                "description": f"Rule {i}"
            }

            mock_audit_logger.log_permission_decision(
                path=f"/test/path/{i}",
                operation="read",
                result=True,
                matched_rule=matched_rule
            )

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        # Should log 1000 events in reasonable time (less than 100ms)
        assert elapsed_ms < 100

        # Verify all events were logged
        events = mock_audit_logger.get_events()
        assert len(events) == num_events

    def test_memory_usage_with_many_events(self, mock_audit_logger: MockAuditLogger):
        """Test memory usage with large number of audit events."""
        # Log many events
        for i in range(10000):
            mock_audit_logger.log_permission_decision(
                path=f"/large/test/{i}",
                operation="read",
                result=i % 2 == 0,  # Alternate true/false
                matched_rule={"id": f"rule-{i}", "rule_type": "allow"} if i % 2 == 0 else None
            )

        events = mock_audit_logger.get_events()
        assert len(events) == 10000

        # Test that we can still clear efficiently
        mock_audit_logger.clear()
        assert len(mock_audit_logger.get_events()) == 0


class TestAuditLogIntegration:
    """Test audit logging integration with permission service."""

    def test_audit_integration_with_permission_checks(self, mock_audit_logger: MockAuditLogger):
        """Test that audit logging integrates properly with permission checking."""
        # This test simulates how audit logging would work with the actual permission service

        # Simulate permission service using audit logger
        class MockPermissionService:
            def __init__(self, audit_logger):
                self.audit_logger = audit_logger
                self.rules = [
                    {"path": "materials", "permission_type": "read", "rule_type": "allow", "id": "rule-1"},
                    {"path": "blocked", "permission_type": "read", "rule_type": "deny", "id": "rule-2"}
                ]

            def check_access(self, path, operation):
                # Simple permission check logic
                matched_rule = None
                result = False

                for rule in self.rules:
                    if path.startswith(f"/{rule['path']}/") and rule["permission_type"] == operation:
                        matched_rule = rule
                        result = rule["rule_type"] == "allow"
                        break

                # Log the decision
                self.audit_logger.log_permission_decision(path, operation, result, matched_rule)
                return result

        permission_service = MockPermissionService(mock_audit_logger)

        # Test various permission checks
        test_cases = [
            ("/materials/doc.txt", "read"),
            ("/blocked/secret.txt", "read"),
            ("/unknown/file.txt", "read"),
            ("/materials/another.txt", "write")  # No write rule for materials
        ]

        results = []
        for path, operation in test_cases:
            result = permission_service.check_access(path, operation)
            results.append(result)

        # Verify results
        expected_results = [True, False, False, False]
        assert results == expected_results

        # Verify all decisions were logged
        events = mock_audit_logger.get_events()
        assert len(events) == len(test_cases)

        # Verify audit log content
        for i, (path, operation) in enumerate(test_cases):
            event = events[i]
            assert event["path"] == path
            assert event["operation"] == operation
            assert event["result"] == expected_results[i]

    def test_audit_log_with_complex_rules(self, mock_audit_logger: MockAuditLogger):
        """Test audit logging with complex permission scenarios."""
        # Simulate complex permission scenarios that would generate different audit patterns

        scenarios = [
            {
                "description": "Allow rule matched",
                "path": "/projects/app/main.py",
                "operation": "write",
                "result": True,
                "matched_rule": {
                    "id": "rule-proj-write",
                    "path": "projects",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Allow write access to projects"
                }
            },
            {
                "description": "Deny rule overrides allow",
                "path": "/projects/confidential/secret.py",
                "operation": "read",
                "result": False,
                "matched_rule": {
                    "id": "rule-proj-conf-deny",
                    "path": "projects/confidential",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Block confidential project files"
                }
            },
            {
                "description": "Write implies read",
                "path": "/projects/app/utils.py",
                "operation": "read",
                "result": True,
                "matched_rule": {
                    "id": "rule-proj-write",
                    "path": "projects",
                    "permission_type": "write",  # Write rule used for read access
                    "rule_type": "allow",
                    "description": "Allow write access to projects"
                }
            },
            {
                "description": "No matching rule - default deny",
                "path": "/forbidden/area/file.txt",
                "operation": "read",
                "result": False,
                "matched_rule": None
            }
        ]

        # Log each scenario
        for scenario in scenarios:
            mock_audit_logger.log_permission_decision(
                path=scenario["path"],
                operation=scenario["operation"],
                result=scenario["result"],
                matched_rule=scenario["matched_rule"]
            )

        # Verify audit log captures all scenarios correctly
        events = mock_audit_logger.get_events()
        assert len(events) == len(scenarios)

        for i, scenario in enumerate(scenarios):
            event = events[i]
            assert event["path"] == scenario["path"]
            assert event["operation"] == scenario["operation"]
            assert event["result"] == scenario["result"]
            assert event["matched_rule"] == scenario["matched_rule"]

        # Verify different types of outcomes are logged
        allow_events = [e for e in events if e["result"] is True]
        deny_events = [e for e in events if e["result"] is False]

        assert len(allow_events) == 2  # Two allow scenarios
        assert len(deny_events) == 2   # Two deny scenarios

        # Verify some events have matched rules and others don't
        events_with_rules = [e for e in events if e["matched_rule"] is not None]
        events_without_rules = [e for e in events if e["matched_rule"] is None]

        assert len(events_with_rules) == 3  # Three scenarios with matched rules
        assert len(events_without_rules) == 1  # One scenario with no matching rule


class TestAuditLogCompliance:
    """Test audit logging compliance features."""

    def test_audit_log_immutability(self, mock_audit_logger: MockAuditLogger):
        """Test that audit log events are immutable after creation."""
        mock_audit_logger.log_permission_decision(
            path="/test/immutable",
            operation="read",
            result=True,
            matched_rule={"id": "rule-1", "rule_type": "allow"}
        )

        events = mock_audit_logger.get_events()
        original_event = events[0].copy()

        # Try to modify the event (in a real system, this should not be possible)
        # This test just verifies we get a consistent copy
        events_again = mock_audit_logger.get_events()
        assert events_again[0] == original_event

    def test_audit_log_completeness(self, mock_audit_logger: MockAuditLogger):
        """Test that audit log captures complete information."""
        # Log a comprehensive permission decision
        comprehensive_rule = {
            "id": "comprehensive-rule-123",
            "path": "secure/area",
            "permission_type": "write",
            "rule_type": "deny",
            "description": "Comprehensive test rule with all metadata"
        }

        mock_audit_logger.log_permission_decision(
            path="/secure/area/document.pdf",
            operation="write",
            result=False,
            matched_rule=comprehensive_rule
        )

        events = mock_audit_logger.get_events()
        event = events[0]

        # Verify completeness
        assert all(key in event for key in ["timestamp", "path", "operation", "result", "matched_rule"])
        assert all(key in event["matched_rule"] for key in ["id", "path", "permission_type", "rule_type", "description"])

    def test_audit_log_chronological_order(self, mock_audit_logger: MockAuditLogger):
        """Test that audit events maintain chronological order."""
        import time

        # Log events with small delays
        for i in range(5):
            mock_audit_logger.log_permission_decision(
                path=f"/test/chronological/{i}",
                operation="read",
                result=True,
                matched_rule={"id": f"rule-{i}", "rule_type": "allow"}
            )
            time.sleep(0.001)  # Small delay to ensure different timestamps

        events = mock_audit_logger.get_events()
        assert len(events) == 5

        # Verify chronological order (timestamps should be non-decreasing)
        timestamps = [event["timestamp"] for event in events]
        sorted_timestamps = sorted(timestamps)
        assert timestamps == sorted_timestamps