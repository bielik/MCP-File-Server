"""
Comprehensive test matrix for permission precedence logic.
This test suite validates the formal precedence rules as specified in Phase 2:

1. Specificity: A rule on a child path is more specific than a rule on a parent path
2. Tie-Breaker: For rules of equal specificity, deny wins over allow
3. Implied Permissions: A write permission implicitly grants read
4. Default: If no rule matches, access is denied
"""

import pytest
from typing import List, Dict, Any


class MockConfigPermissionService:
    """Mock implementation of the config permission service for testing precedence logic"""

    def __init__(self, rules: List[Dict[str, Any]]):
        self.rules = rules

    def check_access(self, path: str, operation: str) -> bool:
        """
        Test implementation of permission checking logic.
        This will be replaced with the actual implementation.
        """
        # Find all matching rules (rules where the path starts with the rule path)
        matching_rules = []
        for rule in self.rules:
            rule_path = rule['path']
            if path.startswith(rule_path) or rule_path == "/" or rule_path == "":
                matching_rules.append(rule)

        if not matching_rules:
            return False  # Default deny

        # Sort by specificity (path length, descending)
        matching_rules.sort(key=lambda r: len(r['path']), reverse=True)

        # Find the most specific rules
        max_specificity = len(matching_rules[0]['path'])
        most_specific_rules = [r for r in matching_rules if len(r['path']) == max_specificity]

        # Check for deny rules first (deny wins tie-breaker)
        for rule in most_specific_rules:
            if rule['rule_type'] == 'deny' and rule['permission_type'] == operation:
                return False

        # Check for allow rules
        for rule in most_specific_rules:
            if rule['rule_type'] == 'allow':
                if rule['permission_type'] == operation:
                    return True
                # Write permission implies read
                if rule['permission_type'] == 'write' and operation == 'read':
                    return True

        return False  # Default deny


class TestPermissionPrecedence:
    """Test suite for permission precedence logic"""

    def test_specificity_child_over_parent(self):
        """Rule on child path should be more specific than parent path"""
        rules = [
            {'path': '/projects', 'permission_type': 'read', 'rule_type': 'allow'},
            {'path': '/projects/secret', 'permission_type': 'read', 'rule_type': 'deny'},
        ]
        service = MockConfigPermissionService(rules)

        # Parent path should be allowed
        assert service.check_access('/projects/public/file.txt', 'read') == True

        # Child path should be denied (more specific)
        assert service.check_access('/projects/secret/file.txt', 'read') == False

    def test_deny_wins_over_allow_same_specificity(self):
        """For rules of equal specificity, deny should win over allow"""
        rules = [
            {'path': '/projects', 'permission_type': 'read', 'rule_type': 'allow'},
            {'path': '/projects', 'permission_type': 'read', 'rule_type': 'deny'},
        ]
        service = MockConfigPermissionService(rules)

        # Deny should win the tie-breaker
        assert service.check_access('/projects/file.txt', 'read') == False

    def test_write_implies_read_permission(self):
        """Write permission should implicitly grant read permission"""
        rules = [
            {'path': '/output', 'permission_type': 'write', 'rule_type': 'allow'},
        ]
        service = MockConfigPermissionService(rules)

        # Write permission should allow both read and write
        assert service.check_access('/output/file.txt', 'write') == True
        assert service.check_access('/output/file.txt', 'read') == True

    def test_default_deny_no_matching_rules(self):
        """If no rule matches, access should be denied"""
        rules = [
            {'path': '/projects', 'permission_type': 'read', 'rule_type': 'allow'},
        ]
        service = MockConfigPermissionService(rules)

        # No matching rules should result in denial
        assert service.check_access('/forbidden/file.txt', 'read') == False
        assert service.check_access('/forbidden/file.txt', 'write') == False

    def test_exact_path_match(self):
        """Exact path matches should work correctly"""
        rules = [
            {'path': '/projects/specific-file.txt', 'permission_type': 'read', 'rule_type': 'allow'},
        ]
        service = MockConfigPermissionService(rules)

        # Exact match should be allowed
        assert service.check_access('/projects/specific-file.txt', 'read') == True

        # Non-exact match should be denied
        assert service.check_access('/projects/other-file.txt', 'read') == False

    def test_root_path_permission(self):
        """Root path permissions should affect all paths"""
        rules = [
            {'path': '/', 'permission_type': 'read', 'rule_type': 'allow'},
            {'path': '/restricted', 'permission_type': 'read', 'rule_type': 'deny'},
        ]
        service = MockConfigPermissionService(rules)

        # Root allows everything by default
        assert service.check_access('/any/path/file.txt', 'read') == True

        # But specific deny overrides due to higher specificity
        assert service.check_access('/restricted/file.txt', 'read') == False

    def test_nested_path_specificity(self):
        """Deeper nested paths should have higher specificity"""
        rules = [
            {'path': '/a', 'permission_type': 'read', 'rule_type': 'allow'},
            {'path': '/a/b', 'permission_type': 'read', 'rule_type': 'deny'},
            {'path': '/a/b/c', 'permission_type': 'read', 'rule_type': 'allow'},
        ]
        service = MockConfigPermissionService(rules)

        assert service.check_access('/a/file.txt', 'read') == True
        assert service.check_access('/a/b/file.txt', 'read') == False
        assert service.check_access('/a/b/c/file.txt', 'read') == True

    def test_different_operation_types(self):
        """Different operation types should be handled independently"""
        rules = [
            {'path': '/projects', 'permission_type': 'read', 'rule_type': 'allow'},
            {'path': '/projects', 'permission_type': 'write', 'rule_type': 'deny'},
        ]
        service = MockConfigPermissionService(rules)

        # Read should be allowed, write should be denied
        assert service.check_access('/projects/file.txt', 'read') == True
        assert service.check_access('/projects/file.txt', 'write') == False

    def test_multiple_allow_rules(self):
        """Multiple allow rules should all grant permission"""
        rules = [
            {'path': '/docs', 'permission_type': 'read', 'rule_type': 'allow'},
            {'path': '/projects', 'permission_type': 'read', 'rule_type': 'allow'},
        ]
        service = MockConfigPermissionService(rules)

        assert service.check_access('/docs/file.txt', 'read') == True
        assert service.check_access('/projects/file.txt', 'read') == True

    def test_complex_hierarchy_with_mixed_rules(self):
        """Complex test with multiple levels and mixed allow/deny rules"""
        rules = [
            {'path': '/', 'permission_type': 'read', 'rule_type': 'deny'},  # Default deny all
            {'path': '/public', 'permission_type': 'read', 'rule_type': 'allow'},  # Allow public
            {'path': '/public/sensitive', 'permission_type': 'read', 'rule_type': 'deny'},  # Deny sensitive
            {'path': '/public/sensitive/allowed', 'permission_type': 'read', 'rule_type': 'allow'},  # Allow specific
            {'path': '/projects', 'permission_type': 'write', 'rule_type': 'allow'},  # Write to projects
        ]
        service = MockConfigPermissionService(rules)

        # Root denial
        assert service.check_access('/random/file.txt', 'read') == False

        # Public access
        assert service.check_access('/public/file.txt', 'read') == True

        # Sensitive denied
        assert service.check_access('/public/sensitive/file.txt', 'read') == False

        # Specific allowed path
        assert service.check_access('/public/sensitive/allowed/file.txt', 'read') == True

        # Write permissions with read implication
        assert service.check_access('/projects/file.txt', 'write') == True
        assert service.check_access('/projects/file.txt', 'read') == True  # Implied by write

    def test_empty_path_handling(self):
        """Test handling of empty and root paths"""
        rules = [
            {'path': '', 'permission_type': 'read', 'rule_type': 'allow'},  # Empty path
        ]
        service = MockConfigPermissionService(rules)

        # Empty path should match all paths
        assert service.check_access('/any/file.txt', 'read') == True
        assert service.check_access('file.txt', 'read') == True


class TestPermissionEdgeCases:
    """Test edge cases and error conditions"""

    def test_invalid_operation_type(self):
        """Test handling of invalid operation types"""
        rules = []
        service = MockConfigPermissionService(rules)

        # This should be handled by the actual implementation
        # For now, we'll assume False for unknown operations
        assert service.check_access('/file.txt', 'invalid_op') == False

    def test_path_normalization(self):
        """Test that path normalization works correctly"""
        rules = [
            {'path': '/projects', 'permission_type': 'read', 'rule_type': 'allow'},
        ]
        service = MockConfigPermissionService(rules)

        # These should all be treated as equivalent paths
        assert service.check_access('/projects/file.txt', 'read') == True
        # The actual implementation will handle path normalization
        # assert service.check_access('/projects//file.txt', 'read') == True
        # assert service.check_access('/projects/./file.txt', 'read') == True

    def test_performance_with_many_rules(self):
        """Test performance with a large number of rules"""
        # Generate many rules
        rules = []
        for i in range(1000):
            rules.append({
                'path': f'/test{i}',
                'permission_type': 'read',
                'rule_type': 'allow'
            })

        service = MockConfigPermissionService(rules)

        # This should complete in reasonable time
        import time
        start_time = time.time()

        for i in range(100):  # Test 100 permission checks
            service.check_access(f'/test{i}/file.txt', 'read')

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in less than 1 second for 100 checks with 1000 rules
        assert duration < 1.0, f"Performance test failed: {duration}s for 100 checks"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])