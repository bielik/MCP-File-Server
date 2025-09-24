"""
Phase 4B Backfill Script Tests

Tests the backfill script logic to ensure it can handle:
1. Incremental processing (resuming from partial completion)
2. Adding new job types to existing files
3. Proper cursor-based pagination
4. Missing job detection per file

Following TDD methodology as specified in Phase 4B plan.
"""

import pytest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Add parent directories to path for imports
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, backend_root)
scripts_root = os.path.join(os.path.dirname(backend_root), 'scripts')
sys.path.insert(0, scripts_root)

from app.database import Base
from app.models.indexing import IndexedFile, IndexJob

# Import the backfill manager without triggering model redefinitions
import importlib.util
import sys

# Temporarily remove the app path to prevent duplicate model imports
original_paths = sys.path.copy()
paths_to_remove = [p for p in sys.path if 'backend' in p and ('app' in p or p.endswith('backend'))]
for p in paths_to_remove:
    sys.path.remove(p)

try:
    spec = importlib.util.spec_from_file_location("phase4b_backfill", os.path.join(scripts_root, "phase4b_backfill.py"))
    phase4b_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(phase4b_module)
    Phase4BBackfillManager = phase4b_module.Phase4BBackfillManager
finally:
    # Restore original sys.path
    sys.path = original_paths


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


class TestBackfillLogic:
    """Test the core backfill logic."""

    def test_get_missing_jobs_for_file_all_missing(self, test_db):
        """Test missing job detection when no jobs exist."""
        # Insert test file
        test_db.execute(text("""
            INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
            VALUES ('test_doc_id', 'test_file.txt', 'hash123', 1024, 1234567890, 1234567890, 1, 1, 0, 0)
        """))

        file_result = test_db.execute(text("SELECT id FROM indexed_files WHERE doc_id = 'test_doc_id'")).fetchone()
        file_id = file_result[0]

        # Get the file object
        file = test_db.query(IndexedFile).filter(IndexedFile.id == file_id).first()

        # Test missing jobs detection
        manager = Phase4BBackfillManager(dry_run=True)
        missing_jobs = manager.get_missing_jobs_for_file(test_db, file)

        # All jobs should be missing
        expected_jobs = ['TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX', 'EMBED']
        assert set(missing_jobs) == set(expected_jobs), f"Expected {expected_jobs}, got {missing_jobs}"

    def test_get_missing_jobs_for_file_partial_missing(self, test_db):
        """Test missing job detection when some jobs exist."""
        # Insert test file
        test_db.execute(text("""
            INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
            VALUES ('test_doc_id_2', 'test_file_2.txt', 'hash456', 2048, 1234567891, 1234567891, 1, 1, 0, 0)
        """))

        file_result = test_db.execute(text("SELECT id FROM indexed_files WHERE doc_id = 'test_doc_id_2'")).fetchone()
        file_id = file_result[0]

        # Add some existing jobs
        test_db.execute(text("""
            INSERT INTO index_jobs (file_id, job_type, status, created_at, job_signature, retry_count, max_retries)
            VALUES
            (:file_id, 'TEXT_EXTRACT', 'pending', 1234567890, :sig1, 0, 3),
            (:file_id, 'CHUNK', 'completed', 1234567890, :sig2, 0, 3)
        """), {
            "file_id": file_id,
            "sig1": f"{file_id}_TEXT_EXTRACT",
            "sig2": f"{file_id}_CHUNK"
        })

        # Get the file object
        file = test_db.query(IndexedFile).filter(IndexedFile.id == file_id).first()

        # Test missing jobs detection
        manager = Phase4BBackfillManager(dry_run=True)
        missing_jobs = manager.get_missing_jobs_for_file(test_db, file)

        # Only FTS_INDEX and EMBED should be missing
        expected_missing = ['FTS_INDEX', 'EMBED']
        assert set(missing_jobs) == set(expected_missing), f"Expected {expected_missing}, got {missing_jobs}"

    def test_get_missing_jobs_for_file_none_missing(self, test_db):
        """Test missing job detection when all jobs exist."""
        # Insert test file
        test_db.execute(text("""
            INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
            VALUES ('test_doc_id_3', 'test_file_3.txt', 'hash789', 4096, 1234567892, 1234567892, 1, 1, 0, 0)
        """))

        file_result = test_db.execute(text("SELECT id FROM indexed_files WHERE doc_id = 'test_doc_id_3'")).fetchone()
        file_id = file_result[0]

        # Add all jobs
        test_db.execute(text("""
            INSERT INTO index_jobs (file_id, job_type, status, created_at, job_signature, retry_count, max_retries)
            VALUES
            (:file_id, 'TEXT_EXTRACT', 'completed', 1234567890, :sig1, 0, 3),
            (:file_id, 'CHUNK', 'completed', 1234567890, :sig2, 0, 3),
            (:file_id, 'FTS_INDEX', 'pending', 1234567890, :sig3, 0, 3),
            (:file_id, 'EMBED', 'failed', 1234567890, :sig4, 0, 3)
        """), {
            "file_id": file_id,
            "sig1": f"{file_id}_TEXT_EXTRACT",
            "sig2": f"{file_id}_CHUNK",
            "sig3": f"{file_id}_FTS_INDEX",
            "sig4": f"{file_id}_EMBED"
        })

        # Get the file object
        file = test_db.query(IndexedFile).filter(IndexedFile.id == file_id).first()

        # Test missing jobs detection
        manager = Phase4BBackfillManager(dry_run=True)
        missing_jobs = manager.get_missing_jobs_for_file(test_db, file)

        # No jobs should be missing
        assert missing_jobs == [], f"Expected no missing jobs, got {missing_jobs}"


class TestCursorPagination:
    """Test cursor-based pagination logic."""

    def test_get_eligible_files_cursor_pagination(self, test_db):
        """Test that cursor-based pagination works correctly."""
        # Insert multiple test files
        for i in range(10):
            test_db.execute(text("""
                INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
                VALUES (:doc_id, :path, :file_hash, 1024, 1234567890, 1234567890, 1, 1, 0, 0)
            """), {
                "doc_id": f"cursor_test_doc_{i}",
                "path": f"cursor_test_file_{i}.txt",
                "file_hash": f"cursor_hash_{i}"
            })

        test_db.commit()

        # Test pagination with batch size 3
        manager = Phase4BBackfillManager(batch_size=3, dry_run=True)

        # First batch (starting from 0)
        batch1 = manager.get_eligible_files(test_db, last_file_id=0)
        assert len(batch1) == 3, "First batch should have 3 files"

        # Second batch (starting from last ID of first batch)
        batch2 = manager.get_eligible_files(test_db, last_file_id=batch1[-1].id)
        assert len(batch2) == 3, "Second batch should have 3 files"

        # Third batch
        batch3 = manager.get_eligible_files(test_db, last_file_id=batch2[-1].id)
        assert len(batch3) == 3, "Third batch should have 3 files"

        # Fourth batch (should have 1 file)
        batch4 = manager.get_eligible_files(test_db, last_file_id=batch3[-1].id)
        assert len(batch4) == 1, "Fourth batch should have 1 file"

        # Fifth batch (should be empty)
        batch5 = manager.get_eligible_files(test_db, last_file_id=batch4[-1].id)
        assert len(batch5) == 0, "Fifth batch should be empty"

        # Verify no overlap between batches
        all_ids = [f.id for f in batch1 + batch2 + batch3 + batch4]
        assert len(all_ids) == len(set(all_ids)), "Should have no duplicate files across batches"


class TestIncrementalProcessing:
    """Test incremental processing scenarios."""

    def test_resume_from_partial_completion(self, test_db):
        """Test that backfill can resume from partial completion."""
        # Insert test files
        for i in range(5):
            test_db.execute(text("""
                INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
                VALUES (:doc_id, :path, :file_hash, 1024, 1234567890, 1234567890, 1, 1, 0, 0)
            """), {
                "doc_id": f"resume_test_doc_{i}",
                "path": f"resume_test_file_{i}.txt",
                "file_hash": f"resume_hash_{i}"
            })

        test_db.commit()

        # Get file IDs
        files = test_db.execute(text("SELECT id FROM indexed_files ORDER BY id")).fetchall()
        file_ids = [f[0] for f in files]

        # Simulate partial completion - add some jobs for first 3 files
        for i, file_id in enumerate(file_ids[:3]):
            # Different job completeness for each file
            if i == 0:
                # First file: only TEXT_EXTRACT
                test_db.execute(text("""
                    INSERT INTO index_jobs (file_id, job_type, status, created_at, job_signature, retry_count, max_retries)
                    VALUES (:file_id, 'TEXT_EXTRACT', 'completed', 1234567890, :sig1, 0, 3)
                """), {
                    "file_id": file_id,
                    "sig1": f"{file_id}_TEXT_EXTRACT"
                })
            elif i == 1:
                # Second file: TEXT_EXTRACT and CHUNK
                test_db.execute(text("""
                    INSERT INTO index_jobs (file_id, job_type, status, created_at, job_signature, retry_count, max_retries)
                    VALUES
                    (:file_id, 'TEXT_EXTRACT', 'completed', 1234567890, :sig1, 0, 3),
                    (:file_id, 'CHUNK', 'completed', 1234567890, :sig2, 0, 3)
                """), {
                    "file_id": file_id,
                    "sig1": f"{file_id}_TEXT_EXTRACT",
                    "sig2": f"{file_id}_CHUNK"
                })
            elif i == 2:
                # Third file: all jobs
                test_db.execute(text("""
                    INSERT INTO index_jobs (file_id, job_type, status, created_at, job_signature, retry_count, max_retries)
                    VALUES
                    (:file_id, 'TEXT_EXTRACT', 'completed', 1234567890, :sig1, 0, 3),
                    (:file_id, 'CHUNK', 'completed', 1234567890, :sig2, 0, 3),
                    (:file_id, 'FTS_INDEX', 'completed', 1234567890, :sig3, 0, 3),
                    (:file_id, 'EMBED', 'completed', 1234567890, :sig4, 0, 3)
                """), {
                    "file_id": file_id,
                    "sig1": f"{file_id}_TEXT_EXTRACT",
                    "sig2": f"{file_id}_CHUNK",
                    "sig3": f"{file_id}_FTS_INDEX",
                    "sig4": f"{file_id}_EMBED"
                })

        test_db.commit()

        # Test backfill with dry run
        manager = Phase4BBackfillManager(batch_size=10, dry_run=True)

        # Process all files
        files = manager.get_eligible_files(test_db, last_file_id=0)
        assert len(files) == 5, "Should get all 5 files"

        # Check missing jobs for each file
        file_objects = test_db.query(IndexedFile).order_by(IndexedFile.id).all()

        # File 0: should need CHUNK, FTS_INDEX, EMBED
        missing_0 = manager.get_missing_jobs_for_file(test_db, file_objects[0])
        assert set(missing_0) == {'CHUNK', 'FTS_INDEX', 'EMBED'}

        # File 1: should need FTS_INDEX, EMBED
        missing_1 = manager.get_missing_jobs_for_file(test_db, file_objects[1])
        assert set(missing_1) == {'FTS_INDEX', 'EMBED'}

        # File 2: should need nothing
        missing_2 = manager.get_missing_jobs_for_file(test_db, file_objects[2])
        assert missing_2 == []

        # Files 3 and 4: should need all jobs
        missing_3 = manager.get_missing_jobs_for_file(test_db, file_objects[3])
        missing_4 = manager.get_missing_jobs_for_file(test_db, file_objects[4])
        all_jobs = {'TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX', 'EMBED'}
        assert set(missing_3) == all_jobs
        assert set(missing_4) == all_jobs

    def test_add_new_job_type_to_existing_files(self, test_db):
        """Test adding a new job type to files that already have other jobs."""
        # Insert test file
        test_db.execute(text("""
            INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
            VALUES ('new_job_test_doc', 'new_job_test.txt', 'new_job_hash', 1024, 1234567890, 1234567890, 1, 1, 0, 0)
        """))

        file_result = test_db.execute(text("SELECT id FROM indexed_files WHERE doc_id = 'new_job_test_doc'")).fetchone()
        file_id = file_result[0]

        # Add only first 3 job types (simulating old system)
        test_db.execute(text("""
            INSERT INTO index_jobs (file_id, job_type, status, created_at, job_signature, retry_count, max_retries)
            VALUES
            (:file_id, 'TEXT_EXTRACT', 'completed', 1234567890, :sig1, 0, 3),
            (:file_id, 'CHUNK', 'completed', 1234567890, :sig2, 0, 3),
            (:file_id, 'FTS_INDEX', 'completed', 1234567890, :sig3, 0, 3)
        """), {
            "file_id": file_id,
            "sig1": f"{file_id}_TEXT_EXTRACT",
            "sig2": f"{file_id}_CHUNK",
            "sig3": f"{file_id}_FTS_INDEX"
        })

        test_db.commit()

        # Now simulate adding a new job type (EMBED)
        manager = Phase4BBackfillManager(dry_run=True)
        file_obj = test_db.query(IndexedFile).filter(IndexedFile.id == file_id).first()

        missing_jobs = manager.get_missing_jobs_for_file(test_db, file_obj)

        # Only EMBED should be missing
        assert missing_jobs == ['EMBED'], f"Expected only EMBED to be missing, got {missing_jobs}"


class TestJobCreation:
    """Test job creation logic."""

    def test_create_phase4b_jobs_dry_run(self, test_db):
        """Test job creation in dry run mode."""
        # Insert test file
        test_db.execute(text("""
            INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
            VALUES ('dry_run_test_doc', 'dry_run_test.txt', 'dry_run_hash', 1024, 1234567890, 1234567890, 1, 1, 0, 0)
        """))

        file_result = test_db.execute(text("SELECT id FROM indexed_files WHERE doc_id = 'dry_run_test_doc'")).fetchone()
        file_id = file_result[0]

        # Get file object
        file_obj = test_db.query(IndexedFile).filter(IndexedFile.id == file_id).first()

        # Test dry run job creation
        manager = Phase4BBackfillManager(dry_run=True)
        jobs_created = manager.create_phase4b_jobs(test_db, file_obj)

        # Should report creating 4 jobs
        assert jobs_created == 4, f"Expected 4 jobs to be created, got {jobs_created}"

        # But no actual jobs should be in database
        actual_jobs = test_db.execute(text("SELECT COUNT(*) FROM index_jobs WHERE file_id = :file_id"), {"file_id": file_id}).fetchone()
        assert actual_jobs[0] == 0, "No jobs should be created in dry run mode"

    def test_create_phase4b_jobs_real_run(self, test_db):
        """Test job creation in real mode."""
        # Insert test file
        test_db.execute(text("""
            INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
            VALUES ('real_run_test_doc', 'real_run_test.txt', 'real_run_hash', 1024, 1234567890, 1234567890, 1, 1, 0, 0)
        """))

        file_result = test_db.execute(text("SELECT id FROM indexed_files WHERE doc_id = 'real_run_test_doc'")).fetchone()
        file_id = file_result[0]

        # Get file object
        file_obj = test_db.query(IndexedFile).filter(IndexedFile.id == file_id).first()

        # Test real job creation
        manager = Phase4BBackfillManager(dry_run=False)
        jobs_created = manager.create_phase4b_jobs(test_db, file_obj)

        # Should create 4 jobs
        assert jobs_created == 4, f"Expected 4 jobs to be created, got {jobs_created}"

        # Jobs should actually be in database
        actual_jobs = test_db.execute(text("SELECT COUNT(*) FROM index_jobs WHERE file_id = :file_id"), {"file_id": file_id}).fetchone()
        assert actual_jobs[0] == 4, "4 jobs should be created in database"

        # Verify job types
        job_types = test_db.execute(text("SELECT job_type FROM index_jobs WHERE file_id = :file_id ORDER BY job_type"), {"file_id": file_id}).fetchall()
        expected_types = ['CHUNK', 'EMBED', 'FTS_INDEX', 'TEXT_EXTRACT']  # Alphabetical order
        actual_types = [job[0] for job in job_types]
        assert actual_types == expected_types, f"Expected {expected_types}, got {actual_types}"