"""
Tests for Phase 4A search service functionality.

Tests metadata search capabilities and permission filtering.
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.indexing import IndexedFile
from app.services.search_service import SearchService
from app.services.permission_service import PermissionService


class TestSearchService:
    """Test search service functionality."""

    @pytest.fixture
    def test_session(self):
        """Create a test database session with sample data."""
        # Create in-memory SQLite database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # Create sample indexed files
        sample_files = [
            IndexedFile(
                path="documents/readme.txt",
                size_bytes=1024,
                mtime_epoch=int(datetime(2024, 1, 1).timestamp())
            ),
            IndexedFile(
                path="projects/app.py",
                size_bytes=2048,
                mtime_epoch=int(datetime(2024, 1, 15).timestamp())
            ),
            IndexedFile(
                path="documents/report.pdf",
                size_bytes=5120,
                mtime_epoch=int(datetime(2024, 2, 1).timestamp())
            ),
            IndexedFile(
                path="config/settings.json",
                size_bytes=512,
                mtime_epoch=int(datetime(2024, 1, 10).timestamp())
            ),
        ]

        for file_obj in sample_files:
            file_obj.is_indexed = True
            session.add(file_obj)

        session.commit()

        yield session

        session.close()

    @patch.object(PermissionService, 'check_access')
    def test_list_all_files_basic(self, mock_check_access, test_session):
        """Test basic file listing functionality."""
        # Mock permission service to allow all files
        mock_check_access.return_value = None

        search_service = SearchService()
        results = search_service.list_all_files(test_session, limit=10)

        # Should return all 4 files
        assert len(results) == 4

        # Check result structure
        for result in results:
            assert 'doc_id' in result
            assert 'path' in result
            assert 'name' in result
            assert 'size_bytes' in result
            assert 'mtime_epoch' in result
            assert 'is_indexed' in result

        # Check paths are included
        paths = [r['path'] for r in results]
        assert "documents/readme.txt" in paths
        assert "projects/app.py" in paths

    @patch.object(PermissionService, 'check_access')
    def test_list_all_files_permission_filtering(self, mock_check_access, test_session):
        """Test that permission filtering works correctly."""
        # Mock permission service to deny access to certain files
        def mock_permission_check(path, operation):
            if path.startswith("projects/"):
                raise PermissionError("Access denied")

        mock_check_access.side_effect = mock_permission_check

        search_service = SearchService()
        results = search_service.list_all_files(test_session, limit=10)

        # Should only return 3 files (excluding projects/app.py)
        assert len(results) == 3

        # Check that projects file is not included
        paths = [r['path'] for r in results]
        assert "projects/app.py" not in paths
        assert "documents/readme.txt" in paths

    @patch.object(PermissionService, 'check_access')
    def test_list_all_files_sorting(self, mock_check_access, test_session):
        """Test file listing with different sorting options."""
        mock_check_access.return_value = None

        search_service = SearchService()

        # Test sorting by size (descending)
        results = search_service.list_all_files(test_session, sort_by="size")
        sizes = [r['size_bytes'] for r in results]
        assert sizes == sorted(sizes, reverse=True)

        # Test sorting by modification time (descending)
        results = search_service.list_all_files(test_session, sort_by="mtime")
        mtimes = [r['mtime_epoch'] for r in results]
        assert mtimes == sorted(mtimes, reverse=True)

    @patch.object(PermissionService, 'check_access')
    def test_search_files_by_metadata_filename_pattern(self, mock_check_access, test_session):
        """Test metadata search with filename patterns."""
        mock_check_access.return_value = None

        search_service = SearchService()

        # Search for files with "readme" in name
        results = search_service.search_files_by_metadata(
            test_session,
            filename_pattern="readme"
        )

        assert len(results) == 1
        assert results[0]['path'] == "documents/readme.txt"

        # Search for files with "app" in name
        results = search_service.search_files_by_metadata(
            test_session,
            filename_pattern="app"
        )

        assert len(results) == 1
        assert results[0]['path'] == "projects/app.py"

    @patch.object(PermissionService, 'check_access')
    def test_search_files_by_metadata_file_types(self, mock_check_access, test_session):
        """Test metadata search with file type filtering."""
        mock_check_access.return_value = None

        search_service = SearchService()

        # Search for Python files
        results = search_service.search_files_by_metadata(
            test_session,
            file_types=[".py"]
        )

        assert len(results) == 1
        assert results[0]['path'] == "projects/app.py"

        # Search for text and JSON files
        results = search_service.search_files_by_metadata(
            test_session,
            file_types=[".txt", ".json"]
        )

        assert len(results) == 2
        paths = [r['path'] for r in results]
        assert "documents/readme.txt" in paths
        assert "config/settings.json" in paths

    @patch.object(PermissionService, 'check_access')
    def test_search_files_by_metadata_size_filter(self, mock_check_access, test_session):
        """Test metadata search with size filtering."""
        mock_check_access.return_value = None

        search_service = SearchService()

        # Search for files larger than 1KB
        results = search_service.search_files_by_metadata(
            test_session,
            size_min=1024
        )

        assert len(results) == 3  # readme.txt (1024), app.py (2048), report.pdf (5120)

        # Search for files smaller than 1KB
        results = search_service.search_files_by_metadata(
            test_session,
            size_max=1023
        )

        assert len(results) == 1
        assert results[0]['path'] == "config/settings.json"

        # Search for files between 1KB and 3KB
        results = search_service.search_files_by_metadata(
            test_session,
            size_min=1024,
            size_max=3072
        )

        assert len(results) == 2
        paths = [r['path'] for r in results]
        assert "documents/readme.txt" in paths
        assert "projects/app.py" in paths

    @patch.object(PermissionService, 'check_access')
    def test_search_files_by_metadata_time_filter(self, mock_check_access, test_session):
        """Test metadata search with modification time filtering."""
        mock_check_access.return_value = None

        search_service = SearchService()

        # Search for files modified after Jan 10, 2024
        jan_10_timestamp = int(datetime(2024, 1, 10).timestamp())
        results = search_service.search_files_by_metadata(
            test_session,
            mtime_after=jan_10_timestamp
        )

        assert len(results) == 3  # app.py (Jan 15), report.pdf (Feb 1), settings.json (Jan 10)

        # Search for files modified before Jan 15, 2024
        jan_15_timestamp = int(datetime(2024, 1, 15).timestamp())
        results = search_service.search_files_by_metadata(
            test_session,
            mtime_before=jan_15_timestamp
        )

        assert len(results) == 3  # readme.txt (Jan 1), app.py (Jan 15), settings.json (Jan 10)

    @patch.object(PermissionService, 'check_access')
    def test_get_file_info(self, mock_check_access, test_session):
        """Test getting detailed file information."""
        mock_check_access.return_value = None

        search_service = SearchService()

        # Get a file from the test data
        file_obj = test_session.query(IndexedFile).filter(
            IndexedFile.path == "documents/readme.txt"
        ).first()

        result = search_service.get_file_info(test_session, file_obj.doc_id)

        assert result is not None
        assert result['doc_id'] == file_obj.doc_id
        assert result['path'] == "documents/readme.txt"
        assert result['name'] == "readme.txt"
        assert result['size_bytes'] == 1024
        assert result['file_extension'] == ".txt"
        assert result['directory'] == "documents"

    @patch.object(PermissionService, 'check_access')
    def test_get_file_info_permission_denied(self, mock_check_access, test_session):
        """Test file info with permission denied."""
        # Mock permission service to deny access
        mock_check_access.side_effect = PermissionError("Access denied")

        search_service = SearchService()

        # Get a file from the test data
        file_obj = test_session.query(IndexedFile).first()

        result = search_service.get_file_info(test_session, file_obj.doc_id)

        # Should return None for permission denied
        assert result is None

    @patch.object(PermissionService, 'check_access')
    def test_get_file_info_not_found(self, mock_check_access, test_session):
        """Test file info with non-existent file."""
        mock_check_access.return_value = None

        search_service = SearchService()

        result = search_service.get_file_info(test_session, "nonexistent-doc-id")

        # Should return None for non-existent file
        assert result is None

    @patch.object(PermissionService, 'check_access')
    def test_get_search_statistics(self, mock_check_access, test_session):
        """Test search statistics gathering."""
        mock_check_access.return_value = None

        search_service = SearchService()

        stats = search_service.get_search_statistics(test_session)

        assert 'total_files' in stats
        assert 'accessible_files' in stats
        assert 'indexed_files' in stats
        assert 'indexing_progress' in stats
        assert 'file_types' in stats
        assert 'most_common_types' in stats

        # Check expected values
        assert stats['total_files'] == 4
        assert stats['accessible_files'] == 4  # All files accessible in this test
        assert stats['indexed_files'] == 4    # All files are indexed
        assert stats['indexing_progress'] == 100.0

        # Check file types
        assert '.txt' in stats['file_types']
        assert '.py' in stats['file_types']
        assert '.pdf' in stats['file_types']
        assert '.json' in stats['file_types']

    def test_format_file_size(self):
        """Test file size formatting utility."""
        search_service = SearchService()

        assert search_service._format_file_size(0) == "0 B"
        assert search_service._format_file_size(512) == "512.0 B"
        assert search_service._format_file_size(1024) == "1.0 KB"
        assert search_service._format_file_size(1536) == "1.5 KB"
        assert search_service._format_file_size(1048576) == "1.0 MB"
        assert search_service._format_file_size(1073741824) == "1.0 GB"


if __name__ == "__main__":
    pytest.main([__file__])