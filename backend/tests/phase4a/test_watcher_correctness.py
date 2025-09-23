"""
Test file watcher correctness for Phase 4A.

This test suite verifies that the file watcher correctly handles:
- File stability checks before job creation
- Symlink filtering
- File rename handling
- Race condition prevention between initial scan and watcher
"""

import os
import pytest
import tempfile
import time
import shutil
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from app.models.indexing import IndexedFile, IndexJob, JobStatus, ControlSetting, Base
from app.db.bootstrap import DatabaseBootstrap
from indexer.app.watcher import FileWatcher, FileStabilityTracker, IndexerFileSystemEventHandler
from indexer.app.queue import JobQueueManager


class TestWatcherCorrectness:
    """Test suite for file watcher correctness."""

    @pytest.fixture
    def test_engine(self):
        """Create test database engine with WAL mode."""
        engine = DatabaseBootstrap.create_engine_with_config("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session_factory(self, test_engine):
        """Create session factory for test database."""
        return sessionmaker(bind=test_engine)

    @pytest.fixture
    def temp_source_dir(self):
        """Create temporary source directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def stability_tracker(self):
        """Create file stability tracker for testing."""
        return FileStabilityTracker(stability_checks=2, debounce_seconds=0.1)

    @pytest.fixture
    def queue_manager(self):
        """Create queue manager for testing."""
        return JobQueueManager("test-watcher")

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for watcher."""
        config = MagicMock()
        config.WATCHER_DEBOUNCE_SECONDS = 0.1
        config.WATCHER_STABILITY_CHECKS = 2
        return config

    def test_file_stability_before_job_creation(self, stability_tracker, temp_source_dir):
        """Test that jobs are only created after file mtime and size are stable."""
        test_file = Path(temp_source_dir) / "stability_test.txt"

        # Create file
        test_file.write_text("initial content")
        stability_tracker.add_file(str(test_file))

        # File should not be stable immediately
        stable_files = stability_tracker.check_stable_files()
        assert len(stable_files) == 0

        # Modify file (should reset stability)
        time.sleep(0.05)  # Brief delay
        test_file.write_text("modified content")
        stability_tracker.add_file(str(test_file))  # Re-add after modification

        # Still not stable
        stable_files = stability_tracker.check_stable_files()
        assert len(stable_files) == 0

        # Wait for debounce period
        time.sleep(0.15)

        # Check stability (first check)
        stable_files = stability_tracker.check_stable_files()
        assert len(stable_files) == 0  # Need multiple checks

        # Wait and check again (second check)
        time.sleep(0.15)
        stable_files = stability_tracker.check_stable_files()
        assert len(stable_files) == 1  # Should be stable now
        assert str(test_file) in stable_files

    def test_symlink_filtering(self, session_factory, temp_source_dir, queue_manager, mock_config):
        """Test that symlinks pointing outside source directory are ignored."""
        # Create external directory and file
        external_dir = tempfile.mkdtemp()
        external_file = Path(external_dir) / "external.txt"
        external_file.write_text("external content")

        try:
            # Create symlink inside source directory pointing outside
            source_path = Path(temp_source_dir)
            internal_symlink = source_path / "external_link.txt"
            internal_symlink.symlink_to(external_file)

            # Create normal file for comparison
            normal_file = source_path / "normal.txt"
            normal_file.write_text("normal content")

            # Create internal symlink (should be allowed)
            internal_target = source_path / "internal_target.txt"
            internal_target.write_text("internal content")
            internal_symlink_ok = source_path / "internal_link.txt"
            internal_symlink_ok.symlink_to(internal_target)

            # Create event handler
            stability_tracker = FileStabilityTracker()
            handler = IndexerFileSystemEventHandler(
                temp_source_dir, queue_manager, stability_tracker
            )

            # Test symlink filtering
            assert handler.should_ignore_path(str(internal_symlink)) == True  # External symlink
            assert handler.should_ignore_path(str(normal_file)) == False  # Normal file
            assert handler.should_ignore_path(str(internal_symlink_ok)) == False  # Internal symlink

        finally:
            shutil.rmtree(external_dir, ignore_errors=True)

    def test_file_rename_preserves_doc_id(self, session_factory, temp_source_dir, queue_manager, mock_config):
        """Test that file renames update path while preserving doc_id and file_hash."""
        source_path = Path(temp_source_dir)
        original_file = source_path / "original.txt"
        renamed_file = source_path / "renamed.txt"

        session = session_factory()

        try:
            # Create original file and indexed record
            original_file.write_text("test content")
            stat = original_file.stat()

            indexed_file = IndexedFile(
                path="original.txt",
                size_bytes=stat.st_size,
                mtime_epoch=int(stat.st_mtime)
            )
            session.add(indexed_file)
            session.commit()

            original_doc_id = indexed_file.doc_id
            original_file_hash = indexed_file.file_hash

            # Create event handler
            stability_tracker = FileStabilityTracker()
            handler = IndexerFileSystemEventHandler(
                temp_source_dir, queue_manager, stability_tracker
            )

            # Mock file system event
            from watchdog.events import FileMovedEvent
            move_event = FileMovedEvent(str(original_file), str(renamed_file))

            # Process the move event
            with patch('indexer.app.watcher.get_db') as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = session
                mock_get_db.return_value.__exit__.return_value = None

                handler.on_moved(move_event)

            # Verify the file record was updated
            session.refresh(indexed_file)
            assert indexed_file.path == "renamed.txt"
            assert indexed_file.doc_id == original_doc_id  # Should be preserved
            assert not indexed_file.is_indexed  # Should be marked for reindexing

        finally:
            session.close()

    def test_discovery_epoch_prevents_duplicates(self, session_factory, temp_source_dir, mock_config):
        """Test that discovery epoch prevents duplicate jobs from initial scan and watcher."""
        session = session_factory()

        try:
            # Set discovery epoch
            current_epoch = int(time.time())
            ControlSetting.set_setting(
                session, "discovery_epoch", str(current_epoch), "integer"
            )

            # Create test file
            source_path = Path(temp_source_dir)
            test_file = source_path / "epoch_test.txt"
            test_file.write_text("test content")

            # Create file watcher
            file_watcher = FileWatcher(temp_source_dir, mock_config)

            # Mock database access
            with patch('indexer.app.watcher.get_db') as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = session
                mock_get_db.return_value.__exit__.return_value = None

                # Run initial discovery
                file_watcher.initial_discovery()

                # Verify file was discovered
                indexed_files = session.query(IndexedFile).all()
                assert len(indexed_files) == 1
                assert indexed_files[0].path == "epoch_test.txt"

                # Try to process the same file again (simulating watcher event)
                # This should not create a duplicate due to job signature uniqueness
                file_obj = indexed_files[0]
                queue_manager = JobQueueManager("test")

                # Try to create job twice
                job1 = queue_manager.create_job(session, file_obj.id, "index_file")
                job2 = queue_manager.create_job(session, file_obj.id, "index_file")

                # Only one job should be created (second should return None)
                assert job1 is not None
                assert job2 is None

        finally:
            session.close()

    def test_broken_symlink_handling(self, session_factory, temp_source_dir, queue_manager, mock_config):
        """Test that broken symlinks are properly ignored."""
        source_path = Path(temp_source_dir)

        # Create symlink to non-existent file
        broken_symlink = source_path / "broken_link.txt"
        non_existent = source_path / "does_not_exist.txt"
        broken_symlink.symlink_to(non_existent)

        # Create event handler
        stability_tracker = FileStabilityTracker()
        handler = IndexerFileSystemEventHandler(
            temp_source_dir, queue_manager, stability_tracker
        )

        # Broken symlink should be ignored
        assert handler.should_ignore_path(str(broken_symlink)) == True

    def test_ignored_file_patterns(self, queue_manager, temp_source_dir, mock_config):
        """Test that files matching ignored patterns are properly filtered."""
        source_path = Path(temp_source_dir)

        # Create files with ignored patterns
        ignored_files = [
            source_path / "temp.tmp",
            source_path / "backup.temp",
            source_path / "locked.lock",
            source_path / "vim.swp",
            source_path / ".DS_Store",
            source_path / "Thumbs.db",
            source_path / "__pycache__" / "test.pyc",
            source_path / ".git" / "config",
            source_path / "node_modules" / "package.json",
        ]

        # Create directories for nested files
        (source_path / "__pycache__").mkdir(exist_ok=True)
        (source_path / ".git").mkdir(exist_ok=True)
        (source_path / "node_modules").mkdir(exist_ok=True)

        # Create all files
        for file_path in ignored_files:
            file_path.touch()

        # Create normal file for comparison
        normal_file = source_path / "normal.txt"
        normal_file.touch()

        # Create event handler
        stability_tracker = FileStabilityTracker()
        handler = IndexerFileSystemEventHandler(
            temp_source_dir, queue_manager, stability_tracker
        )

        # Test ignored patterns
        for ignored_file in ignored_files:
            assert handler.should_ignore_path(str(ignored_file)) == True, \
                f"File {ignored_file} should be ignored"

        # Normal file should not be ignored
        assert handler.should_ignore_path(str(normal_file)) == False

    def test_file_deletion_cleanup(self, session_factory, temp_source_dir, queue_manager, mock_config):
        """Test that file deletion properly removes database records."""
        source_path = Path(temp_source_dir)
        test_file = source_path / "delete_test.txt"

        session = session_factory()

        try:
            # Create file and database record
            test_file.write_text("test content")
            stat = test_file.stat()

            indexed_file = IndexedFile(
                path="delete_test.txt",
                size_bytes=stat.st_size,
                mtime_epoch=int(stat.st_mtime)
            )
            session.add(indexed_file)
            session.commit()

            # Verify file exists in database
            file_count = session.query(IndexedFile).count()
            assert file_count == 1

            # Create event handler
            stability_tracker = FileStabilityTracker()
            handler = IndexerFileSystemEventHandler(
                temp_source_dir, queue_manager, stability_tracker
            )

            # Mock file deletion event
            from watchdog.events import FileDeletedEvent
            delete_event = FileDeletedEvent(str(test_file))

            # Process deletion
            with patch('indexer.app.watcher.get_db') as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = session
                mock_get_db.return_value.__exit__.return_value = None

                handler.on_deleted(delete_event)

            # Verify file was removed from database
            file_count = session.query(IndexedFile).count()
            assert file_count == 0

        finally:
            session.close()

    def test_stability_tracker_pending_file_count(self, stability_tracker, temp_source_dir):
        """Test that stability tracker correctly reports pending file count."""
        source_path = Path(temp_source_dir)

        # Initially no pending files
        assert stability_tracker.get_pending_count() == 0

        # Add files to tracker
        file1 = source_path / "file1.txt"
        file2 = source_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        stability_tracker.add_file(str(file1))
        stability_tracker.add_file(str(file2))

        # Should have 2 pending files
        assert stability_tracker.get_pending_count() == 2

        # Wait for stability and check
        time.sleep(0.15)
        stable_files = stability_tracker.check_stable_files()

        # Files should become stable and be removed from pending
        assert stability_tracker.get_pending_count() == 0

    def test_file_modification_resets_stability(self, stability_tracker, temp_source_dir):
        """Test that file modifications reset the stability tracking."""
        source_path = Path(temp_source_dir)
        test_file = source_path / "modify_test.txt"

        # Create and add file
        test_file.write_text("original")
        stability_tracker.add_file(str(test_file))

        # Wait partial time
        time.sleep(0.05)

        # Modify file
        test_file.write_text("modified")
        stability_tracker.add_file(str(test_file))  # Re-add after modification

        # Wait for original debounce time
        time.sleep(0.15)

        # Should not be stable yet (stability was reset)
        stable_files = stability_tracker.check_stable_files()
        assert len(stable_files) == 0

        # Wait for full stability period
        time.sleep(0.15)
        stable_files = stability_tracker.check_stable_files()
        assert len(stable_files) == 0  # Still need another check

        time.sleep(0.15)
        stable_files = stability_tracker.check_stable_files()
        assert len(stable_files) == 1  # Now stable