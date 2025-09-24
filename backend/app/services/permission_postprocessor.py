"""
Permission Postprocessor for Phase 4B M2

This module provides the PermissionPostprocessor class that filters search results
based on workspace permissions. This is a critical security component that ensures
users can only see search results from files they have access to.

The postprocessor integrates with the existing workspace permission system and
uses doc_id to file path lookups to determine access rights.
"""

import logging
from typing import List, Dict, Any, Set, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.indexing import IndexedFile
from app.models.workspace import Workspace
from app.services.permission_service import check_access, PermissionService

logger = logging.getLogger(__name__)


class PermissionPostprocessor:
    """
    Filters search results based on workspace permissions.

    This class ensures that search results are filtered according to the
    active workspace's permission rules, preventing unauthorized access
    to file content through search.
    """

    def __init__(self):
        """Initialize the permission postprocessor."""
        self._cached_allowed_paths = {}  # Cache for performance
        self._cache_workspace_id = None

    def filter_results(
        self,
        search_results: List[Dict[str, Any]],
        workspace_id: int,
        session: Session
    ) -> List[Dict[str, Any]]:
        """
        Filter search results based on workspace permissions.

        Args:
            search_results: List of search result dictionaries
            workspace_id: ID of the active workspace
            session: Database session

        Returns:
            Filtered list of search results (only allowed files)
        """
        try:
            if not search_results:
                return []

            # Get allowed paths set for performance
            allowed_paths = self._get_allowed_paths_set(workspace_id, session)

            # Filter results
            filtered_results = []

            for result in search_results:
                try:
                    # Extract file path from result
                    file_path = self._extract_file_path(result, session)

                    if file_path and self._is_path_allowed(file_path, allowed_paths):
                        filtered_results.append(result)

                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")
                    # Skip problematic results rather than failing entirely
                    continue

            logger.debug(f"Filtered {len(search_results)} results to {len(filtered_results)} allowed results")
            return filtered_results

        except Exception as e:
            logger.error(f"Error filtering search results: {e}")
            # Fail-safe: return empty results if filtering fails
            return []

    def enrich_with_file_paths(
        self,
        results_with_doc_ids: List[Dict[str, Any]],
        session: Session
    ) -> List[Dict[str, Any]]:
        """
        Enrich search results that only have doc_ids with file paths.

        Args:
            results_with_doc_ids: Search results containing doc_id fields
            session: Database session

        Returns:
            Results enriched with file_path fields
        """
        try:
            enriched_results = []

            for result in results_with_doc_ids:
                try:
                    doc_id = result.get("doc_id")
                    if not doc_id:
                        continue

                    # Look up file path from doc_id
                    indexed_file = session.query(IndexedFile).filter(
                        IndexedFile.doc_id == doc_id
                    ).first()

                    if indexed_file:
                        # Add file_path to result
                        enriched_result = result.copy()
                        enriched_result["file_path"] = indexed_file.path
                        enriched_results.append(enriched_result)

                except Exception as e:
                    logger.warning(f"Error enriching result with doc_id {result.get('doc_id')}: {e}")
                    continue

            return enriched_results

        except Exception as e:
            logger.error(f"Error enriching results with file paths: {e}")
            return []

    def filter_search_results(
        self,
        search_results: List[Dict[str, Any]],
        workspace_id: int,
        session: Session
    ) -> List[Dict[str, Any]]:
        """
        High-level method to filter search results with path enrichment if needed.

        Args:
            search_results: Search results (may contain doc_id or file_path)
            workspace_id: Active workspace ID
            session: Database session

        Returns:
            Filtered search results
        """
        try:
            # Check if results need path enrichment
            needs_enrichment = any(
                "doc_id" in result and "file_path" not in result
                for result in search_results
            )

            if needs_enrichment:
                # Enrich with file paths first
                enriched_results = self.enrich_with_file_paths(search_results, session)
                # Then filter
                return self.filter_results(enriched_results, workspace_id, session)
            else:
                # Direct filtering
                return self.filter_results(search_results, workspace_id, session)

        except Exception as e:
            logger.error(f"Error in filter_search_results: {e}")
            return []

    def get_allowed_paths_set(self, workspace_id: int, session: Session) -> Set[str]:
        """
        Public method to get allowed paths set for testing and debugging.

        Args:
            workspace_id: Workspace ID
            session: Database session

        Returns:
            Set of allowed path patterns
        """
        return self._get_allowed_paths_set(workspace_id, session)

    def _get_allowed_paths_set(self, workspace_id: int, session: Session) -> Set[str]:
        """
        Get or compute the set of allowed paths for a workspace.

        Args:
            workspace_id: Workspace ID
            session: Database session

        Returns:
            Set of allowed path patterns for O(1) lookup
        """
        try:
            # Use cache if workspace hasn't changed
            if (self._cache_workspace_id == workspace_id and
                workspace_id in self._cached_allowed_paths):
                return self._cached_allowed_paths[workspace_id]

            # Get workspace
            workspace = session.query(Workspace).filter(
                Workspace.id == workspace_id
            ).first()

            if not workspace:
                logger.warning(f"Workspace {workspace_id} not found")
                return set()

            # Build allowed paths set using permission service logic
            allowed_paths = set()

            # Get all permissions for this workspace
            permissions = workspace.permissions

            for permission in permissions:
                if permission.rule_type.value == "allow":
                    # Add exact path and path patterns
                    path = permission.path.strip("/")  # Normalize path

                    # Add exact path
                    allowed_paths.add(path)

                    # Add with trailing slash for directory matching
                    allowed_paths.add(f"{path}/")

                    # Add wildcard pattern for subdirectories
                    allowed_paths.add(f"{path}/*")

            # Handle deny rules by removing patterns (specificity wins)
            deny_patterns = set()
            for permission in permissions:
                if permission.rule_type.value == "deny":
                    path = permission.path.strip("/")
                    deny_patterns.add(path)
                    deny_patterns.add(f"{path}/")
                    deny_patterns.add(f"{path}/*")

            # Remove denied patterns from allowed set
            allowed_paths = allowed_paths - deny_patterns

            # Cache the result
            self._cached_allowed_paths[workspace_id] = allowed_paths
            self._cache_workspace_id = workspace_id

            logger.debug(f"Built allowed paths set for workspace {workspace_id}: {len(allowed_paths)} patterns")
            return allowed_paths

        except Exception as e:
            logger.error(f"Error building allowed paths set for workspace {workspace_id}: {e}")
            return set()

    def _extract_file_path(self, search_result: Dict[str, Any], session: Session) -> Optional[str]:
        """
        Extract file path from a search result.

        Args:
            search_result: Search result dictionary
            session: Database session

        Returns:
            File path string or None
        """
        try:
            # Check if file_path is already present
            if "file_path" in search_result and search_result["file_path"]:
                return search_result["file_path"]

            # Try to get path from doc_id
            if "doc_id" in search_result:
                doc_id = search_result["doc_id"]
                indexed_file = session.query(IndexedFile).filter(
                    IndexedFile.doc_id == doc_id
                ).first()

                if indexed_file:
                    return indexed_file.path

            # Check for other path fields
            for field in ["path", "filename", "file"]:
                if field in search_result and search_result[field]:
                    return search_result[field]

            return None

        except Exception as e:
            logger.warning(f"Error extracting file path from search result: {e}")
            return None

    def _is_path_allowed(self, file_path: str, allowed_paths: Set[str]) -> bool:
        """
        Check if a file path is allowed based on the allowed paths set.

        Args:
            file_path: Path to check
            allowed_paths: Set of allowed path patterns

        Returns:
            True if path is allowed, False otherwise
        """
        try:
            if not file_path:
                return False

            # Normalize path (remove leading slash, handle Windows paths)
            normalized_path = file_path.replace("\\", "/").strip("/")

            # Check exact matches
            if normalized_path in allowed_paths:
                return True

            # Check if any allowed pattern matches this path
            for allowed_pattern in allowed_paths:
                if self._path_matches_pattern(normalized_path, allowed_pattern):
                    return True

            return False

        except Exception as e:
            logger.warning(f"Error checking if path {file_path} is allowed: {e}")
            return False

    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """
        Check if a path matches an allowed pattern.

        Args:
            path: File path to check
            pattern: Allowed pattern (may contain wildcards)

        Returns:
            True if path matches pattern
        """
        try:
            # Handle wildcard patterns
            if pattern.endswith("/*"):
                # Pattern like "materials/*" should match "materials/file.txt"
                prefix = pattern[:-2]  # Remove "/*"
                return path.startswith(f"{prefix}/")

            elif pattern.endswith("/"):
                # Pattern like "materials/" should match paths under materials/
                return path.startswith(pattern) or path == pattern[:-1]

            else:
                # Exact match
                return path == pattern

        except Exception as e:
            logger.warning(f"Error matching path {path} against pattern {pattern}: {e}")
            return False

    def clear_cache(self):
        """Clear the allowed paths cache."""
        self._cached_allowed_paths.clear()
        self._cache_workspace_id = None
        logger.debug("Permission postprocessor cache cleared")


# Compatibility wrapper for integration with existing permission service
class PermissionServiceWrapper:
    """
    Static wrapper around PermissionService for test compatibility.

    This provides the same interface as the existing permission service
    while allowing for easier testing and mocking.
    """

    @staticmethod
    def check_access(path: str, operation: str = "read") -> None:
        """
        Check access using the existing permission service.

        Args:
            path: Path to check
            operation: Operation type (read/write)

        Raises:
            PermissionError: If access is denied
        """
        return check_access(path, operation)

    @staticmethod
    def is_allowed(path: str, operation: str = "read") -> bool:
        """
        Check if a path is allowed without raising exceptions.

        Args:
            path: Path to check
            operation: Operation type

        Returns:
            True if allowed, False otherwise
        """
        try:
            check_access(path, operation)
            return True
        except PermissionError:
            return False