"""
Test atomic job claiming functionality for Phase 4A.

This test suite verifies that the job queue's atomic claiming mechanism
works correctly under concurrent load, ensuring no jobs are processed twice.
"""

import asyncio
import pytest
import threading
import time
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.models.indexing import IndexedFile, IndexJob, JobStatus, Base
from app.db.bootstrap import DatabaseBootstrap
from indexer.app.queue import JobQueueManager


class TestAtomicJobClaim:
    """Test suite for atomic job claiming under concurrent load."""

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
    def sample_jobs(self, session_factory):
        """Create sample jobs for testing."""
        session = session_factory()
        try:
            # Create sample indexed files
            file1 = IndexedFile(
                path="test1.txt",
                size_bytes=100,
                mtime_epoch=int(datetime.utcnow().timestamp())
            )
            file2 = IndexedFile(
                path="test2.txt",
                size_bytes=200,
                mtime_epoch=int(datetime.utcnow().timestamp())
            )
            session.add_all([file1, file2])
            session.commit()

            # Create sample jobs
            job1 = IndexJob(file_id=file1.id, job_type="index_file")
            job2 = IndexJob(file_id=file2.id, job_type="index_file")
            session.add_all([job1, job2])
            session.commit()

            return [job1.id, job2.id]
        finally:
            session.close()

    def test_single_worker_claim(self, session_factory, sample_jobs):
        """Test that a single worker can claim jobs normally."""
        queue_manager = JobQueueManager("test-worker-1")
        session = session_factory()

        try:
            # Claim first job
            job = queue_manager.claim_job(session)
            assert job is not None
            assert job.status == JobStatus.PROCESSING
            assert job.worker_id == "test-worker-1"
            assert job.claimed_at is not None
            assert job.started_at is not None

            # Claim second job
            job2 = queue_manager.claim_job(session)
            assert job2 is not None
            assert job2.id != job.id  # Different job
            assert job2.status == JobStatus.PROCESSING
            assert job2.worker_id == "test-worker-1"

            # No more jobs available
            job3 = queue_manager.claim_job(session)
            assert job3 is None

        finally:
            session.close()

    def test_concurrent_workers_no_double_claim(self, session_factory, sample_jobs):
        """Test that concurrent workers don't claim the same job."""
        results = []
        errors = []

        def worker_claim_jobs(worker_id: str, num_attempts: int = 5):
            """Worker function to claim jobs."""
            queue_manager = JobQueueManager(worker_id)
            worker_results = []

            for _ in range(num_attempts):
                session = session_factory()
                try:
                    job = queue_manager.claim_job(session)
                    if job:
                        worker_results.append({
                            'worker_id': worker_id,
                            'job_id': job.id,
                            'claimed_at': job.claimed_at
                        })
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {e}")
                finally:
                    session.close()

                # Brief delay to simulate processing time
                time.sleep(0.01)

            results.extend(worker_results)

        # Start multiple workers concurrently
        workers = []
        for i in range(4):  # 4 concurrent workers
            worker_thread = threading.Thread(
                target=worker_claim_jobs,
                args=(f"worker-{i}", 3)
            )
            workers.append(worker_thread)
            worker_thread.start()

        # Wait for all workers to complete
        for worker in workers:
            worker.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent execution: {errors}"

        # Verify that each job was claimed exactly once
        job_claims = {}
        for result in results:
            job_id = result['job_id']
            if job_id in job_claims:
                pytest.fail(
                    f"Job {job_id} was claimed by multiple workers: "
                    f"{job_claims[job_id]['worker_id']} and {result['worker_id']}"
                )
            job_claims[job_id] = result

        # Verify we have claims for our sample jobs
        assert len(job_claims) == len(sample_jobs)

        # Verify job IDs match our sample jobs
        claimed_job_ids = set(job_claims.keys())
        expected_job_ids = set(sample_jobs)
        assert claimed_job_ids == expected_job_ids

    def test_retry_job_claiming(self, session_factory, sample_jobs):
        """Test that failed jobs can be retried and claimed again."""
        queue_manager = JobQueueManager("test-worker")
        session = session_factory()

        try:
            # Claim and fail a job
            job = queue_manager.claim_job(session)
            assert job is not None

            # Simulate job failure
            queue_manager.fail_job(session, job, "Test failure")

            # Job should be in failed state with retry info
            session.refresh(job)
            assert job.status == JobStatus.FAILED
            assert job.retry_count > 0
            assert job.next_retry_at is not None

            # Should be able to claim the failed job for retry
            retry_job = queue_manager.claim_job(session)
            assert retry_job is not None
            assert retry_job.id == job.id  # Same job
            assert retry_job.status == JobStatus.PROCESSING

        finally:
            session.close()

    def test_stale_job_recovery(self, session_factory, sample_jobs):
        """Test recovery of stale jobs that have been processing too long."""
        queue_manager = JobQueueManager("test-worker")
        session = session_factory()

        try:
            # Claim a job
            job = queue_manager.claim_job(session)
            assert job is not None

            # Manually set started_at to make it stale (1 hour ago)
            one_hour_ago = int(datetime.utcnow().timestamp()) - 3600
            job.started_at = one_hour_ago
            session.commit()

            # Run stale job recovery
            recovered_count = queue_manager.recover_stale_jobs(session)
            assert recovered_count == 1

            # Job should be back to pending status
            session.refresh(job)
            assert job.status == JobStatus.PENDING
            assert job.worker_id is None
            assert job.claimed_at is None
            assert job.started_at is None

            # Should be claimable again
            recovered_job = queue_manager.claim_job(session)
            assert recovered_job is not None
            assert recovered_job.id == job.id

        finally:
            session.close()

    def test_job_signature_prevents_duplicates(self, session_factory):
        """Test that job signature prevents duplicate job creation."""
        session = session_factory()

        try:
            # Create indexed file
            file_obj = IndexedFile(
                path="duplicate_test.txt",
                size_bytes=100,
                mtime_epoch=int(datetime.utcnow().timestamp())
            )
            session.add(file_obj)
            session.commit()

            # Create first job
            job1 = IndexJob(file_id=file_obj.id, job_type="index_file")
            session.add(job1)
            session.commit()

            # Attempt to create duplicate job
            job2 = IndexJob(file_id=file_obj.id, job_type="index_file")
            session.add(job2)

            # Should raise integrity error due to unique job_signature
            with pytest.raises(Exception):  # SQLAlchemy IntegrityError
                session.commit()

        finally:
            session.rollback()
            session.close()

    def test_job_de_duplication_race_condition(self, session_factory):
        """Test job de-duplication under race conditions."""
        results = []
        errors = []

        def create_job_worker(worker_id: str, file_id: int):
            """Worker function to create jobs."""
            queue_manager = JobQueueManager(worker_id)
            session = session_factory()

            try:
                job = queue_manager.create_job(session, file_id, "index_file")
                results.append({
                    'worker_id': worker_id,
                    'job_created': job is not None,
                    'job_id': job.id if job else None
                })
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
            finally:
                session.close()

        # Create indexed file
        session = session_factory()
        try:
            file_obj = IndexedFile(
                path="race_test.txt",
                size_bytes=100,
                mtime_epoch=int(datetime.utcnow().timestamp())
            )
            session.add(file_obj)
            session.commit()
            file_id = file_obj.id
        finally:
            session.close()

        # Start multiple workers trying to create the same job
        workers = []
        for i in range(5):
            worker_thread = threading.Thread(
                target=create_job_worker,
                args=(f"creator-{i}", file_id)
            )
            workers.append(worker_thread)
            worker_thread.start()

        # Wait for all workers to complete
        for worker in workers:
            worker.join()

        # Count successful job creations
        successful_creations = sum(1 for r in results if r['job_created'])

        # Only one job should have been created successfully
        assert successful_creations == 1, f"Expected 1 job, got {successful_creations}"

        # The rest should have been duplicates (None returned)
        duplicates = len(results) - successful_creations
        assert duplicates == 4, f"Expected 4 duplicates, got {duplicates}"