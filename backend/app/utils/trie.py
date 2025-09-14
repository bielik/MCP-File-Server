"""
Trie data structure for efficient path matching in permission system.

This implementation provides O(log n) path prefix matching for permission rules,
significantly improving performance over linear rule scanning, especially with
large rule sets.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import os


@dataclass
class PermissionRule:
    """Represents a single permission rule."""
    id: str
    path: str
    permission_type: str  # 'read' or 'write'
    rule_type: str  # 'allow' or 'deny'
    description: Optional[str] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        """Normalize the path after initialization."""
        self.path = self._normalize_path(self.path)

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize path for consistent matching."""
        if not path or path == "/":
            return ""
        # Remove leading/trailing slashes and normalize
        normalized = os.path.normpath(path.strip("/"))
        return normalized if normalized != "." else ""


class TrieNode:
    """Node in the permission Trie data structure."""

    def __init__(self, path_segment: str = ""):
        self.path_segment = path_segment
        self.children: Dict[str, 'TrieNode'] = {}
        self.rules: List[PermissionRule] = []  # Rules that apply to this exact path
        self.is_end_node = False

    def add_rule(self, rule: PermissionRule):
        """Add a permission rule to this node."""
        self.rules.append(rule)
        self.is_end_node = True

    def get_rules_by_operation(self, operation: str) -> List[PermissionRule]:
        """Get rules that apply to a specific operation."""
        matching_rules = []
        for rule in self.rules:
            if rule.permission_type == operation:
                matching_rules.append(rule)
            # Write permission implies read
            elif rule.permission_type == "write" and operation == "read":
                matching_rules.append(rule)
        return matching_rules


class PermissionTrie:
    """
    Trie data structure for efficient permission rule lookup.

    This implementation provides fast path prefix matching and supports
    the formal precedence rules:
    1. Specificity (path length)
    2. Deny wins over allow
    3. Write implies read
    4. Default deny
    """

    def __init__(self):
        self.root = TrieNode()
        self.rule_count = 0

    def add_rule(self, rule: PermissionRule):
        """Add a permission rule to the trie."""
        path_parts = self._split_path(rule.path)
        current = self.root

        # Traverse/create nodes for each path segment
        for part in path_parts:
            if part not in current.children:
                current.children[part] = TrieNode(part)
            current = current.children[part]

        # Add the rule to the final node
        current.add_rule(rule)
        self.rule_count += 1

    def find_matching_rules(self, path: str, operation: str) -> List[Tuple[PermissionRule, int]]:
        """
        Find all rules that match the given path and operation.
        Returns list of (rule, specificity) tuples.
        Specificity is measured by path depth.
        """
        path_parts = self._split_path(path)
        matching_rules = []
        current = self.root
        current_depth = 0

        # Check root rules (apply to all paths)
        root_rules = current.get_rules_by_operation(operation)
        for rule in root_rules:
            matching_rules.append((rule, 0))  # Root has specificity 0

        # Traverse the trie following the path
        for part in path_parts:
            current_depth += 1

            if part not in current.children:
                break  # No more specific rules

            current = current.children[part]

            # Check for rules at this level
            level_rules = current.get_rules_by_operation(operation)
            for rule in level_rules:
                matching_rules.append((rule, current_depth))

        return matching_rules

    def check_permission(self, path: str, operation: str) -> Tuple[bool, Optional[PermissionRule]]:
        """
        Check if an operation is permitted on a path.
        Returns (is_allowed, matching_rule) tuple.
        """
        if operation not in ['read', 'write']:
            return False, None

        matching_rules = self.find_matching_rules(path, operation)

        if not matching_rules:
            return False, None  # Default deny

        # Sort by specificity (descending), then by rule_type (deny first)
        matching_rules.sort(
            key=lambda x: (x[1], x[0].rule_type == 'allow'),
            reverse=True
        )

        # Find the most specific rules
        max_specificity = matching_rules[0][1]
        most_specific_rules = [
            (rule, spec) for rule, spec in matching_rules
            if spec == max_specificity
        ]

        # Apply precedence rules
        # 1. Check for deny rules first (deny wins tie-breaker)
        for rule, _ in most_specific_rules:
            if rule.rule_type == 'deny':
                return False, rule

        # 2. Check for allow rules
        for rule, _ in most_specific_rules:
            if rule.rule_type == 'allow':
                return True, rule

        return False, None  # Default deny

    def clear(self):
        """Clear all rules from the trie."""
        self.root = TrieNode()
        self.rule_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the trie."""
        return {
            "rule_count": self.rule_count,
            "max_depth": self._calculate_max_depth(),
            "node_count": self._count_nodes(),
        }

    def _split_path(self, path: str) -> List[str]:
        """Split path into components, handling normalization."""
        if not path or path == "/":
            return []

        # Normalize and split
        normalized = os.path.normpath(path.strip("/"))
        if normalized == "." or normalized == "":
            return []

        return normalized.split(os.path.sep)

    def _calculate_max_depth(self, node: Optional[TrieNode] = None, current_depth: int = 0) -> int:
        """Calculate the maximum depth of the trie."""
        if node is None:
            node = self.root

        if not node.children:
            return current_depth

        max_child_depth = 0
        for child in node.children.values():
            child_depth = self._calculate_max_depth(child, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    def _count_nodes(self, node: Optional[TrieNode] = None) -> int:
        """Count the total number of nodes in the trie."""
        if node is None:
            node = self.root

        count = 1  # Current node
        for child in node.children.values():
            count += self._count_nodes(child)

        return count

    def debug_print(self, node: Optional[TrieNode] = None, prefix: str = "", depth: int = 0):
        """Print the trie structure for debugging."""
        if node is None:
            node = self.root
            print("Trie Structure:")
            print(f"Root ({len(node.rules)} rules)")

        for segment, child in node.children.items():
            print(f"{prefix}├── {segment} ({len(child.rules)} rules)")
            self.debug_print(child, prefix + "│   ", depth + 1)


class CachedPermissionTrie:
    """
    Wrapper around PermissionTrie that adds caching for frequently accessed paths.

    This provides additional performance improvement by caching permission
    decisions for recently accessed paths.
    """

    def __init__(self, cache_max_size: int = 10000, cache_ttl: int = 300):
        self.trie = PermissionTrie()
        self.cache: Dict[str, Tuple[bool, Optional[PermissionRule]]] = {}
        self.cache_access_count: Dict[str, int] = {}
        self.cache_max_size = cache_max_size
        self.cache_ttl = cache_ttl
        self.cache_hits = 0
        self.cache_misses = 0

    def add_rule(self, rule: PermissionRule):
        """Add a permission rule and invalidate cache."""
        self.trie.add_rule(rule)
        self._invalidate_cache()

    def check_permission(self, path: str, operation: str) -> Tuple[bool, Optional[PermissionRule]]:
        """Check permission with caching."""
        cache_key = f"{path}:{operation}"

        # Check cache first
        if cache_key in self.cache:
            self.cache_hits += 1
            self.cache_access_count[cache_key] = self.cache_access_count.get(cache_key, 0) + 1
            return self.cache[cache_key]

        # Cache miss - compute result
        self.cache_misses += 1
        result = self.trie.check_permission(path, operation)

        # Store in cache
        self._add_to_cache(cache_key, result)

        return result

    def clear(self):
        """Clear trie and cache."""
        self.trie.clear()
        self._invalidate_cache()

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        trie_stats = self.trie.get_stats()
        cache_stats = {
            "cache_size": len(self.cache),
            "cache_max_size": self.cache_max_size,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0 else 0
            ),
        }
        return {**trie_stats, **cache_stats}

    def _add_to_cache(self, key: str, value: Tuple[bool, Optional[PermissionRule]]):
        """Add item to cache, evicting if necessary."""
        if len(self.cache) >= self.cache_max_size:
            self._evict_cache_items()

        self.cache[key] = value
        self.cache_access_count[key] = 1

    def _evict_cache_items(self):
        """Evict least recently used cache items."""
        # Sort by access count and remove least used items
        sorted_items = sorted(
            self.cache_access_count.items(),
            key=lambda x: x[1]
        )

        # Remove bottom 25% of items
        items_to_remove = len(sorted_items) // 4
        for key, _ in sorted_items[:items_to_remove]:
            self.cache.pop(key, None)
            self.cache_access_count.pop(key, None)

    def _invalidate_cache(self):
        """Clear the cache when rules change."""
        self.cache.clear()
        self.cache_access_count.clear()