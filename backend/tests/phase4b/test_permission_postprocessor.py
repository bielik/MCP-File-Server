"""
Permission Postprocessor Tests for Phase 4B M2

Tests for the PermissionPostprocessor class that filters search results based on
workspace permissions. This is a critical security component that must prevent
unauthorized access to search results.

Following TDD methodology as specified in Phase 4B plan.
"""

import pytest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Add parent directories to path for imports
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, backend_root)

from app.database import Base
from app.models.indexing import IndexedFile, DocumentChunk
from app.models.workspace import Workspace, Permission, RuleType, PermissionType

# Import PermissionPostprocessor (to be implemented)
# from app.services.permission_postprocessor import PermissionPostprocessor


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    try:
        # Create engine and session
        engine = create_engine(f'sqlite:///{db_path}', echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create all tables
        Base.metadata.create_all(bind=engine)

        session = SessionLocal()
        yield session
        session.close()

        # Properly dispose of engine before cleanup
        engine.dispose()

    finally:
        os.close(db_fd)
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture
def workspace_with_permissions(test_db):
    """Create a workspace with mixed allow/deny permissions."""
    # Create workspace
    workspace = Workspace(name="Test Workspace", description="Test workspace for permissions", is_active=True)
    test_db.add(workspace)
    test_db.commit()

    # Create permissions that match the current permission system
    permissions = [
        Permission(
            workspace_id=workspace.id,
            path="materials",
            permission_type=PermissionType.READ,
            rule_type=RuleType.ALLOW,
            description="Allow read access to materials directory"
        ),
        Permission(
            workspace_id=workspace.id,
            path="projects",
            permission_type=PermissionType.WRITE,
            rule_type=RuleType.ALLOW,
            description="Allow write access to projects directory"
        ),
        Permission(
            workspace_id=workspace.id,
            path="materials/restricted",
            permission_type=PermissionType.READ,
            rule_type=RuleType.DENY,
            description="Deny access to restricted materials"
        )
    ]

    for perm in permissions:
        test_db.add(perm)
    test_db.commit()

    return workspace


@pytest.fixture
def sample_files_with_mixed_permissions(test_db, workspace_with_permissions):
    """Create sample files with mixed permission levels."""
    files = []

    # Files that should be ALLOWED
    allowed_files = [
        {"path": "materials/lecture1.pdf", "doc_id": "allowed_1"},
        {"path": "materials/notes.txt", "doc_id": "allowed_2"},
        {"path": "projects/app.py", "doc_id": "allowed_3"},
        {"path": "projects/readme.md", "doc_id": "allowed_4"},
    ]

    # Files that should be DENIED
    denied_files = [
        {"path": "materials/restricted/secret.txt", "doc_id": "denied_1"},
        {"path": "materials/restricted/confidential.pdf", "doc_id": "denied_2"},
        {"path": "private/personal.txt", "doc_id": "denied_3"},
        {"path": "admin/config.json", "doc_id": "denied_4"},
    ]

    all_files = allowed_files + denied_files

    for file_info in all_files:
        indexed_file = IndexedFile(
            doc_id=file_info["doc_id"],
            path=file_info["path"],
            file_hash=f"hash_{file_info['doc_id']}",
            size_bytes=1024,
            mtime_epoch=1234567890,
            is_indexed=True,
            is_text=True
        )
        test_db.add(indexed_file)
        files.append(indexed_file)

    test_db.commit()
    return files, allowed_files, denied_files


class MockSearchResult:
    """Mock search result for testing."""
    def __init__(self, doc_id: str, file_path: str, score: float = 1.0):
        self.doc_id = doc_id
        self.file_path = file_path
        self.score = score
        self.chunk_id = f"chunk_{doc_id}"


class TestPermissionPostprocessor:
    """Test the PermissionPostprocessor class."""

    def test_filter_allowed_files_only(self, test_db, sample_files_with_mixed_permissions):
        """Test that only allowed files pass through the filter."""
        files, allowed_files, denied_files = sample_files_with_mixed_permissions

        # Create mock search results including both allowed and denied files
        mock_results = []
        for file_info in allowed_files + denied_files:
            result = MockSearchResult(
                doc_id=file_info["doc_id"],
                file_path=file_info["path"]
            )
            mock_results.append(result)

        # TODO: Initialize PermissionPostprocessor
        # postprocessor = PermissionPostprocessor()

        # TODO: Filter results through postprocessor
        # filtered_results = postprocessor.filter_results(mock_results, workspace_id=1)

        # Expected: Only allowed files should remain
        expected_allowed_count = len(allowed_files)
        # assert len(filtered_results) == expected_allowed_count

        # Verify no denied files made it through
        # filtered_doc_ids = [r.doc_id for r in filtered_results]
        # for denied_file in denied_files:
        #     assert denied_file["doc_id"] not in filtered_doc_ids

    def test_filter_respects_deny_rules(self, test_db, sample_files_with_mixed_permissions):
        """Test that deny rules override allow rules (specificity wins)."""
        files, allowed_files, denied_files = sample_files_with_mixed_permissions

        # Create results for files under materials/ including the restricted ones
        materials_results = [
            MockSearchResult("allowed_1", "materials/lecture1.pdf"),
            MockSearchResult("allowed_2", "materials/notes.txt"),
            MockSearchResult("denied_1", "materials/restricted/secret.txt"),
            MockSearchResult("denied_2", "materials/restricted/confidential.pdf"),
        ]

        # TODO: Filter results
        # postprocessor = PermissionPostprocessor()
        # filtered_results = postprocessor.filter_results(materials_results, workspace_id=1)

        # Expected: Only non-restricted materials files should pass
        # assert len(filtered_results) == 2
        # filtered_paths = [r.file_path for r in filtered_results]
        # assert "materials/lecture1.pdf" in filtered_paths
        # assert "materials/notes.txt" in filtered_paths
        # assert "materials/restricted/secret.txt" not in filtered_paths
        # assert "materials/restricted/confidential.pdf" not in filtered_paths

    def test_filter_handles_empty_results(self, test_db, workspace_with_permissions):
        """Test that filter handles empty result lists gracefully."""
        empty_results = []

        # TODO: Filter empty results
        # postprocessor = PermissionPostprocessor()
        # filtered_results = postprocessor.filter_results(empty_results, workspace_id=1)

        # Expected: Empty list returned
        # assert filtered_results == []

    def test_filter_handles_workspace_switching(self, test_db):
        """Test that filter adapts when workspace context changes."""
        # Create two workspaces with different permissions
        workspace1 = Workspace(name="Workspace 1", description="First workspace", is_active=True)
        workspace2 = Workspace(name="Workspace 2", description="Second workspace", is_active=False)
        test_db.add(workspace1)
        test_db.add(workspace2)
        test_db.commit()

        # Workspace 1: Only allow materials/
        perm1 = Permission(
            workspace_id=workspace1.id,
            path="materials",
            permission_type=PermissionType.READ,
            rule_type=RuleType.ALLOW,
            description="Workspace 1 materials access"
        )
        test_db.add(perm1)

        # Workspace 2: Only allow projects/
        perm2 = Permission(
            workspace_id=workspace2.id,
            path="projects",
            permission_type=PermissionType.READ,
            rule_type=RuleType.ALLOW,
            description="Workspace 2 projects access"
        )
        test_db.add(perm2)
        test_db.commit()

        # Create test results from both directories
        mixed_results = [
            MockSearchResult("mat1", "materials/doc1.txt"),
            MockSearchResult("proj1", "projects/app.py"),
        ]

        # TODO: Test filtering with workspace 1
        # postprocessor = PermissionPostprocessor()
        # ws1_results = postprocessor.filter_results(mixed_results, workspace_id=workspace1.id)
        # assert len(ws1_results) == 1
        # assert ws1_results[0].file_path == "materials/doc1.txt"

        # TODO: Test filtering with workspace 2
        # ws2_results = postprocessor.filter_results(mixed_results, workspace_id=workspace2.id)
        # assert len(ws2_results) == 1
        # assert ws2_results[0].file_path == "projects/app.py"

    def test_performance_with_large_result_sets(self, test_db, workspace_with_permissions):
        """Test that permission filtering performs well with large result sets."""
        # Create a large number of mock results
        large_result_set = []
        for i in range(1000):
            # Alternate between allowed and denied paths
            if i % 2 == 0:
                path = f"materials/file_{i}.txt"  # Allowed
            else:
                path = f"private/file_{i}.txt"    # Denied

            result = MockSearchResult(f"doc_{i}", path)
            large_result_set.append(result)

        # TODO: Time the filtering operation
        # import time
        # postprocessor = PermissionPostprocessor()
        #
        # start_time = time.time()
        # filtered_results = postprocessor.filter_results(large_result_set, workspace_id=1)
        # end_time = time.time()
        #
        # processing_time = end_time - start_time
        # assert processing_time < 0.1, f"Filtering 1000 results took {processing_time}s, should be < 0.1s"
        #
        # # Verify correct filtering
        # assert len(filtered_results) == 500  # Only the allowed (even-numbered) files

    def test_allowed_paths_set_caching(self, test_db, workspace_with_permissions):
        """Test that allowed paths are pre-computed and cached for performance."""
        # TODO: Test that PermissionPostprocessor pre-computes allowed paths
        # postprocessor = PermissionPostprocessor()

        # The postprocessor should create a set of allowed paths for fast lookup
        # Expected paths based on workspace_with_permissions fixture:
        expected_allowed_paths = {
            "materials", "materials/", "materials/*",  # materials/ and subdirectories (except restricted)
            "projects", "projects/", "projects/*",     # projects/ and subdirectories
        }

        # TODO: Verify caching behavior
        # allowed_paths = postprocessor.get_allowed_paths_set(workspace_id=1)
        # assert isinstance(allowed_paths, set), "Should return a set for O(1) lookup"
        # assert len(allowed_paths) > 0, "Should have some allowed paths"


class TestPermissionPostprocessorErrorHandling:
    """Test error handling in PermissionPostprocessor."""

    def test_handle_missing_workspace(self, test_db):
        """Test handling of non-existent workspace IDs."""
        mock_results = [MockSearchResult("doc1", "materials/file.txt")]

        # TODO: Test with non-existent workspace
        # postprocessor = PermissionPostprocessor()
        # filtered_results = postprocessor.filter_results(mock_results, workspace_id=999)

        # Expected: Empty results (fail-safe: deny all access for invalid workspace)
        # assert filtered_results == []

    def test_handle_missing_file_paths(self, test_db, workspace_with_permissions):
        """Test handling of search results with missing file paths."""
        # Create results with None or empty paths
        problematic_results = [
            MockSearchResult("doc1", None),
            MockSearchResult("doc2", ""),
            MockSearchResult("doc3", "materials/valid.txt"),  # This one should pass
        ]

        # TODO: Test filtering with problematic paths
        # postprocessor = PermissionPostprocessor()
        # filtered_results = postprocessor.filter_results(problematic_results, workspace_id=1)

        # Expected: Only valid paths should remain
        # assert len(filtered_results) == 1
        # assert filtered_results[0].file_path == "materials/valid.txt"

    def test_handle_database_errors(self, test_db):
        """Test handling of database connection errors."""
        mock_results = [MockSearchResult("doc1", "materials/file.txt")]

        # TODO: Test with database session error
        # with patch.object(test_db, 'query') as mock_query:
        #     mock_query.side_effect = Exception("Database connection lost")
        #
        #     postprocessor = PermissionPostprocessor()
        #     filtered_results = postprocessor.filter_results(mock_results, workspace_id=1)
        #
        #     # Expected: Empty results (fail-safe: deny all access on database error)
        #     assert filtered_results == []


class TestPermissionPostprocessorIntegration:
    """Integration tests for PermissionPostprocessor with other services."""

    def test_integration_with_search_service(self, test_db, sample_files_with_mixed_permissions):
        """Test integration with SearchService for end-to-end filtering."""
        files, allowed_files, denied_files = sample_files_with_mixed_permissions

        # Simulate search results from SearchService
        search_results = []
        for file_info in allowed_files + denied_files:
            # Find the actual IndexedFile
            file_obj = test_db.query(IndexedFile).filter(IndexedFile.doc_id == file_info["doc_id"]).first()
            if file_obj:
                result = {
                    "doc_id": file_obj.doc_id,
                    "file_path": file_obj.path,
                    "score": 0.8,
                    "highlighted_text": f"Sample text from {file_obj.path}"
                }
                search_results.append(result)

        # TODO: Integrate with actual SearchService
        # from app.services.search_service import SearchService
        # from app.services.permission_postprocessor import PermissionPostprocessor
        #
        # search_service = SearchService()
        # postprocessor = PermissionPostprocessor()
        #
        # # Filter search results
        # filtered_results = postprocessor.filter_search_results(search_results, workspace_id=1)
        #
        # # Verify only allowed results remain
        # assert len(filtered_results) == len(allowed_files)

    def test_doc_id_to_file_path_lookup(self, test_db, sample_files_with_mixed_permissions):
        """Test that postprocessor can look up file paths from doc_ids."""
        files, allowed_files, denied_files = sample_files_with_mixed_permissions

        # Create search results with only doc_ids (common search scenario)
        doc_id_results = [
            {"doc_id": "allowed_1", "score": 0.9},
            {"doc_id": "denied_1", "score": 0.8},
            {"doc_id": "allowed_3", "score": 0.7},
        ]

        # TODO: Test doc_id to path lookup
        # postprocessor = PermissionPostprocessor()
        # enriched_results = postprocessor.enrich_with_file_paths(doc_id_results, test_db)
        #
        # # Verify paths were added
        # for result in enriched_results:
        #     assert "file_path" in result
        #     assert result["file_path"] is not None
        #
        # # Filter by permissions
        # filtered_results = postprocessor.filter_results(enriched_results, workspace_id=1)
        #
        # # Should only contain allowed files
        # filtered_doc_ids = [r["doc_id"] for r in filtered_results]
        # assert "allowed_1" in filtered_doc_ids
        # assert "allowed_3" in filtered_doc_ids
        # assert "denied_1" not in filtered_doc_ids