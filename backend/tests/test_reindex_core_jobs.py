"""
Test Suite for Step A: Canonicalize Reindex Entry Point (Core Jobs Only)

Tests verify that Force Reindex creates only TEXT_EXTRACT jobs directly,
with proper batch_id propagation, and no parent jobs (index_file/reindex_file).

Following TDD methodology as specified in Ticket 021.
"""

import pytest
import tempfile
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add backend to path for imports
backend_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_root)

from app.database import Base
from app.models.indexing import IndexedFile, IndexJob, JobStatus
from app.models.reindex import ReindexBatch, ReindexMode, BatchStatus
from app.services.reindex_service import ReindexService


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
def sample_files(test_db):
    """Create sample indexed files for testing."""
    files = []
    base_time = int(datetime.utcnow().timestamp() * 1e9)

    for i in range(5):
        file = IndexedFile(
            path=f"/source/test_file_{i}.txt",
            size_bytes=1024 + i,  # Unique size to avoid doc_id collision
            mtime_epoch=base_time + i * 1000000,  # Unique mtime
            is_text=True
        )
        test_db.add(file)
        files.append(file)

    test_db.commit()
    return files


class TestStepA_CoreJobCreation:
    """Test Step A: Force Reindex creates only core-stage jobs."""

    def test_force_reindex_enqueues_core_jobs_only(self, test_db, sample_files):
        """
        Test that Force Reindex creates only TEXT_EXTRACT jobs with batch_id.

        Given: N indexed files
        When: POST /admin/reindex/rebuild is called (via ReindexService)
        Then: index_jobs contains only TEXT_EXTRACT jobs (no index_file/reindex_file)
              with a new batch_id
        """
        # Arrange
        service = ReindexService(test_db)
        file_count = len(sample_files)

        # Act - Create Hard Reindex batch
        batch = service.create_batch(
            mode=ReindexMode.HARD,
            path_prefix=None,
            text_only=True,
            dry_run=False
        )

        # Assert - Batch created successfully
        assert batch is not None
        assert batch.id is not None
        assert batch.mode == ReindexMode.HARD
        assert batch.candidates_count == file_count

        # Assert - Only TEXT_EXTRACT jobs created
        jobs = test_db.query(IndexJob).filter(IndexJob.batch_id == batch.id).all()
        assert len(jobs) == file_count, f"Expected {file_count} jobs, got {len(jobs)}"

        # Assert - All jobs are TEXT_EXTRACT type (NOT index_file or reindex_file)
        for job in jobs:
            assert job.job_type == "TEXT_EXTRACT", \
                f"Expected TEXT_EXTRACT, got {job.job_type}"
            assert job.batch_id == batch.id, \
                f"Job missing batch_id"

        # Assert - No parent jobs exist for this batch
        parent_jobs = test_db.query(IndexJob).filter(
            IndexJob.batch_id == batch.id,
            IndexJob.job_type.in_(["index_file", "reindex_file"])
        ).all()
        assert len(parent_jobs) == 0, \
            f"Found {len(parent_jobs)} parent jobs, expected 0"

    def test_child_jobs_carry_batch_id(self, test_db, sample_files):
        """
        Test that child jobs (CHUNK, FTS_INDEX) inherit batch_id from TEXT_EXTRACT.

        When: Workers process TEXT_EXTRACT jobs
        Then: Generated CHUNK and FTS_INDEX jobs inherit the same batch_id

        Note: This test simulates what the worker does, but doesn't actually
              run the worker (that's an integration test).
        """
        # Arrange
        service = ReindexService(test_db)
        batch = service.create_batch(
            mode=ReindexMode.HARD,
            path_prefix=None,
            text_only=True,
            dry_run=False
        )

        # Get a TEXT_EXTRACT job
        text_extract_job = test_db.query(IndexJob).filter(
            IndexJob.batch_id == batch.id,
            IndexJob.job_type == "TEXT_EXTRACT"
        ).first()

        assert text_extract_job is not None
        assert text_extract_job.batch_id == batch.id

        # Simulate worker creating child jobs (CHUNK)
        chunk_job = IndexJob(
            file_id=text_extract_job.file_id,
            job_type="CHUNK",
            batch_id=text_extract_job.batch_id  # Inherit batch_id
        )
        test_db.add(chunk_job)
        test_db.commit()

        # Simulate worker creating FTS_INDEX job
        fts_job = IndexJob(
            file_id=text_extract_job.file_id,
            job_type="FTS_INDEX",
            batch_id=text_extract_job.batch_id  # Inherit batch_id
        )
        test_db.add(fts_job)
        test_db.commit()

        # Assert - All jobs in the chain have the same batch_id
        all_jobs = test_db.query(IndexJob).filter(
            IndexJob.file_id == text_extract_job.file_id
        ).all()

        batch_ids = {job.batch_id for job in all_jobs}
        assert len(batch_ids) == 1, \
            f"Jobs have inconsistent batch_ids: {batch_ids}"
        assert batch.id in batch_ids

    def test_no_parent_jobs_in_batch(self, test_db, sample_files):
        """
        Test that no legacy parent jobs exist for reindex batches.

        Given: A Hard Reindex batch
        When: Jobs are created
        Then: Zero index_file or reindex_file jobs exist for that batch
        """
        # Arrange
        service = ReindexService(test_db)

        # Act - Create Hard Reindex
        batch = service.create_batch(
            mode=ReindexMode.HARD,
            path_prefix=None,
            text_only=True,
            dry_run=False
        )

        # Assert - Count job types
        job_types = test_db.query(
            IndexJob.job_type,
            test_db.query(IndexJob).filter(IndexJob.batch_id == batch.id).count()
        ).filter(IndexJob.batch_id == batch.id).group_by(IndexJob.job_type).all()

        job_type_counts = {jt[0]: jt[1] for jt in job_types}

        # Assert - Only TEXT_EXTRACT jobs exist
        assert "TEXT_EXTRACT" in job_type_counts, \
            "No TEXT_EXTRACT jobs found"
        assert job_type_counts.get("index_file", 0) == 0, \
            f"Found {job_type_counts.get('index_file', 0)} index_file jobs"
        assert job_type_counts.get("reindex_file", 0) == 0, \
            f"Found {job_type_counts.get('reindex_file', 0)} reindex_file jobs"

    def test_soft_reindex_also_creates_core_jobs(self, test_db, sample_files):
        """
        Test that Soft Reindex also creates TEXT_EXTRACT jobs (not parent jobs).

        Note: The ticket specifies removing soft reindex, but initially we'll
              make it work the same way as hard reindex for consistency.
        """
        # Arrange
        service = ReindexService(test_db)

        # Act - Create Soft Reindex
        batch = service.create_batch(
            mode=ReindexMode.SOFT,
            path_prefix=None,
            text_only=True,
            dry_run=False
        )

        # Assert - Same behavior as hard reindex
        jobs = test_db.query(IndexJob).filter(IndexJob.batch_id == batch.id).all()

        for job in jobs:
            assert job.job_type == "TEXT_EXTRACT", \
                f"Soft reindex should also create TEXT_EXTRACT, got {job.job_type}"
            assert job.batch_id == batch.id

    def test_batch_id_is_required_for_core_jobs(self, test_db, sample_files):
        """
        Test that batch_id is present for all core-stage jobs in a batch.

        This ensures we can properly track and filter jobs by batch.
        """
        # Arrange
        service = ReindexService(test_db)

        # Act
        batch = service.create_batch(
            mode=ReindexMode.HARD,
            path_prefix=None,
            text_only=True,
            dry_run=False
        )

        # Assert - All jobs have batch_id
        jobs_without_batch = test_db.query(IndexJob).filter(
            IndexJob.file_id.in_([f.id for f in sample_files]),
            IndexJob.batch_id.is_(None)
        ).count()

        assert jobs_without_batch == 0, \
            f"Found {jobs_without_batch} jobs without batch_id"

    def test_path_prefix_filtering_works(self, test_db):
        """
        Test that path_prefix filtering correctly limits job creation.
        """
        # Arrange - Create files with different paths
        base_time = int(datetime.utcnow().timestamp() * 1e9)
        file1 = IndexedFile(
            path="/source/projects/file1.txt",
            size_bytes=1024,
            mtime_epoch=base_time,
            is_text=True
        )
        file2 = IndexedFile(
            path="/source/documents/file2.txt",
            size_bytes=2048,  # Different size to avoid doc_id collision
            mtime_epoch=base_time + 1000000,  # Different mtime
            is_text=True
        )
        test_db.add_all([file1, file2])
        test_db.commit()

        service = ReindexService(test_db)

        # Act - Reindex only /source/projects
        batch = service.create_batch(
            mode=ReindexMode.HARD,
            path_prefix="/source/projects",
            text_only=True,
            dry_run=False
        )

        # Assert - Only 1 job created
        assert batch.candidates_count == 1
        jobs = test_db.query(IndexJob).filter(IndexJob.batch_id == batch.id).all()
        assert len(jobs) == 1
        assert jobs[0].file.path.startswith("/source/projects")

    def test_dry_run_does_not_create_jobs(self, test_db, sample_files):
        """
        Test that dry_run=True only calculates counts without creating jobs.
        """
        # Arrange
        service = ReindexService(test_db)
        initial_job_count = test_db.query(IndexJob).count()

        # Act
        batch = service.create_batch(
            mode=ReindexMode.HARD,
            path_prefix=None,
            text_only=True,
            dry_run=True
        )

        # Assert
        assert batch.candidates_count == len(sample_files)
        assert batch.status == BatchStatus.COMPLETED

        # Assert - No jobs created
        final_job_count = test_db.query(IndexJob).count()
        assert final_job_count == initial_job_count, \
            "Dry run should not create any jobs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])