"""
Test crash recovery and exponential backoff functionality for Phase 4A.

This test suite verifies that the indexer service can recover from crashes
and properly handles failed jobs with exponential backoff retry logic.
"""

import pytest
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.indexing import IndexedFile, IndexJob, JobStatus, Base
from app.db.bootstrap import DatabaseBootstrap
from indexer.app.queue import JobQueueManager, JobProcessor


class TestCrashRecoveryAndBackoff:
    """Test suite for crash recovery and exponential backoff."""

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
    def queue_manager(self):
        """Create queue manager for testing."""
        return JobQueueManager("test-worker")

    @pytest.fixture
    def job_processor(self, queue_manager):
        """Create job processor for testing."""
        return JobProcessor(queue_manager)

    @pytest.fixture
    def sample_file_and_job(self, session_factory):
        """Create sample file and job for testing."""
        session = session_factory()
        try:
            # Create indexed file
            file_obj = IndexedFile(
                path="test_recovery.txt",
                size_bytes=100,
                mtime_epoch=int(datetime.utcnow().timestamp())
            )
            session.add(file_obj)
            session.commit()

            # Create job
            job = IndexJob(file_id=file_obj.id, job_type="index_file")
            session.add(job)
            session.commit()

            return file_obj.id, job.id
        finally:
            session.close()

    def test_stale_job_recovery_on_startup(self, session_factory, queue_manager, sample_file_and_job):
        """Test that stale processing jobs are recovered on startup."""
        file_id, job_id = sample_file_and_job
        session = session_factory()

        try:
            # Get the job and mark it as processing with old timestamp
            job = session.query(IndexJob).filter(IndexJob.id == job_id).first()

            # Simulate a job that was processing but worker crashed
            job.status = JobStatus.PROCESSING
            job.worker_id = "crashed-worker"
            job.claimed_at = int(datetime.utcnow().timestamp()) - 7200  # 2 hours ago
            job.started_at = int(datetime.utcnow().timestamp()) - 7200  # 2 hours ago
            session.commit()

            # Run recovery (simulating startup)
            recovered_count = queue_manager.recover_stale_jobs(session)

            # Should recover the stale job
            assert recovered_count == 1

            # Job should be reset to pending
            session.refresh(job)
            assert job.status == JobStatus.PENDING
            assert job.worker_id is None
            assert job.claimed_at is None
            assert job.started_at is None

        finally:
            session.close()

    def test_exponential_backoff_retry_schedule(self, session_factory, queue_manager, sample_file_and_job):
        """Test that failed jobs are scheduled for retry with exponential backoff."""
        file_id, job_id = sample_file_and_job
        session = session_factory()

        try:
            # Get the job
            job = session.query(IndexJob).filter(IndexJob.id == job_id).first()

            # Claim the job
            claimed_job = queue_manager.claim_job(session)
            assert claimed_job.id == job_id

            # Test multiple failures with exponential backoff
            base_time = datetime.utcnow()

            for retry_attempt in range(1, 4):  # Test 3 retry attempts
                # Fail the job
                queue_manager.fail_job(session, claimed_job, f"Test failure {retry_attempt}")

                session.refresh(claimed_job)
                assert claimed_job.status == JobStatus.FAILED
                assert claimed_job.retry_count == retry_attempt
                assert claimed_job.next_retry_at is not None

                # Verify exponential backoff timing
                expected_delay = (2 ** retry_attempt) * 60  # Base delay of 1 minute, exponential
                actual_next_retry = datetime.fromtimestamp(claimed_job.next_retry_at)
                min_expected_time = base_time + timedelta(seconds=expected_delay - 10)  # Allow 10s variance
                max_expected_time = base_time + timedelta(seconds=expected_delay + 10)

                assert min_expected_time <= actual_next_retry <= max_expected_time, \
                    f"Retry {retry_attempt}: Expected retry time between {min_expected_time} and {max_expected_time}, got {actual_next_retry}"

                # Try to claim again - should not be claimable yet (too early)
                not_ready_job = queue_manager.claim_job(session)
                assert not_ready_job is None or not_ready_job.id != job_id

                # Simulate time passing by manually adjusting next_retry_at
                claimed_job.next_retry_at = int(datetime.utcnow().timestamp()) - 1
                session.commit()

                # Now should be claimable for retry
                retry_job = queue_manager.claim_job(session)
                assert retry_job is not None
                assert retry_job.id == job_id
                assert retry_job.status == JobStatus.PROCESSING

                claimed_job = retry_job  # Update reference for next iteration

        finally:
            session.close()

    def test_dead_letter_queue_after_max_retries(self, session_factory, queue_manager, sample_file_and_job):
        """Test that jobs move to dead letter queue after max retry attempts."""
        file_id, job_id = sample_file_and_job
        session = session_factory()

        try:
            # Get the job
            job = session.query(IndexJob).filter(IndexJob.id == job_id).first()

            # Claim the job
            claimed_job = queue_manager.claim_job(session)
            assert claimed_job.id == job_id

            # Fail the job multiple times until it reaches max retries
            max_retries = 3  # Assuming max retries is 3

            for attempt in range(max_retries + 1):  # +1 to exceed max retries
                queue_manager.fail_job(session, claimed_job, f"Persistent failure {attempt}")
                session.refresh(claimed_job)

                if attempt < max_retries:
                    # Should still be in FAILED status for retry
                    assert claimed_job.status == JobStatus.FAILED
                    assert claimed_job.retry_count == attempt + 1

                    # Manually advance time and claim for retry
                    claimed_job.next_retry_at = int(datetime.utcnow().timestamp()) - 1
                    session.commit()

                    retry_job = queue_manager.claim_job(session)
                    assert retry_job is not None
                    claimed_job = retry_job
                else:
                    # Should move to dead letter queue
                    assert claimed_job.status == JobStatus.DEAD_LETTER
                    assert claimed_job.retry_count == max_retries

            # Dead letter jobs should not be claimable
            dead_job = queue_manager.claim_job(session)
            assert dead_job is None or dead_job.id != job_id

        finally:
            session.close()

    def test_multiple_failed_jobs_recovery(self, session_factory, queue_manager):
        """Test recovery of multiple failed jobs with different retry schedules."""
        session = session_factory()

        try:
            # Create multiple files and jobs
            jobs = []
            for i in range(3):
                file_obj = IndexedFile(
                    path=f"test_multi_{i}.txt",
                    size_bytes=100 + i,
                    mtime_epoch=int(datetime.utcnow().timestamp())
                )
                session.add(file_obj)
                session.commit()

                job = IndexJob(file_id=file_obj.id, job_type="index_file")
                session.add(job)
                session.commit()
                jobs.append(job)

            # Set different failure states
            now = int(datetime.utcnow().timestamp())

            # Job 0: Failed once, ready for retry
            jobs[0].status = JobStatus.FAILED
            jobs[0].retry_count = 1
            jobs[0].next_retry_at = now - 10  # 10 seconds ago (ready)

            # Job 1: Failed twice, not ready for retry yet
            jobs[1].status = JobStatus.FAILED
            jobs[1].retry_count = 2
            jobs[1].next_retry_at = now + 300  # 5 minutes in future (not ready)

            # Job 2: In processing state for too long (stale)
            jobs[2].status = JobStatus.PROCESSING
            jobs[2].worker_id = "dead-worker"
            jobs[2].started_at = now - 7200  # 2 hours ago

            session.commit()

            # Run recovery
            recovered_count = queue_manager.recover_stale_jobs(session)
            assert recovered_count == 1  # Only the stale processing job

            # Try to claim jobs
            claimable_jobs = []
            for _ in range(5):  # Try multiple times to get all claimable jobs
                job = queue_manager.claim_job(session)
                if job:
                    claimable_jobs.append(job.id)
                else:
                    break

            # Should be able to claim jobs[0] (ready for retry) and jobs[2] (recovered)
            assert len(claimable_jobs) == 2
            assert jobs[0].id in claimable_jobs
            assert jobs[2].id in claimable_jobs
            # jobs[1] should not be claimable (not ready for retry yet)

        finally:
            session.close()

    def test_concurrent_crash_recovery(self, session_factory):
        """Test that concurrent crash recovery operations don't conflict."""
        import threading

        results = []
        errors = []

        def recovery_worker(worker_id: str):
            """Worker function to run crash recovery."""
            queue_manager = JobQueueManager(worker_id)
            session = session_factory()

            try:
                recovered = queue_manager.recover_stale_jobs(session)
                results.append({
                    'worker_id': worker_id,
                    'recovered_count': recovered
                })
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
            finally:
                session.close()

        # Create some stale jobs
        session = session_factory()
        try:
            stale_jobs = []
            for i in range(3):
                file_obj = IndexedFile(
                    path=f"stale_{i}.txt",
                    size_bytes=100,
                    mtime_epoch=int(datetime.utcnow().timestamp())
                )
                session.add(file_obj)
                session.commit()

                job = IndexJob(file_id=file_obj.id, job_type="index_file")
                job.status = JobStatus.PROCESSING
                job.worker_id = f"stale-worker-{i}"
                job.started_at = int(datetime.utcnow().timestamp()) - 7200  # 2 hours ago
                session.add(job)
                stale_jobs.append(job)

            session.commit()
        finally:
            session.close()

        # Run concurrent recovery
        workers = []
        for i in range(3):
            worker_thread = threading.Thread(
                target=recovery_worker,
                args=(f"recovery-worker-{i}",)
            )
            workers.append(worker_thread)
            worker_thread.start()

        # Wait for completion
        for worker in workers:
            worker.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent recovery: {errors}"

        # Verify total recovered jobs equals expected (each job recovered once)
        total_recovered = sum(r['recovered_count'] for r in results)
        assert total_recovered == 3, f"Expected 3 total recoveries, got {total_recovered}"

    def test_job_cleanup_retention_policy(self, session_factory, queue_manager):
        """Test that old completed jobs are cleaned up according to retention policy."""
        session = session_factory()

        try:
            # Create completed jobs with different ages
            old_timestamp = int(datetime.utcnow().timestamp()) - (35 * 24 * 3600)  # 35 days ago
            recent_timestamp = int(datetime.utcnow().timestamp()) - (15 * 24 * 3600)  # 15 days ago

            jobs = []
            for i, timestamp in enumerate([old_timestamp, recent_timestamp]):
                file_obj = IndexedFile(
                    path=f"cleanup_test_{i}.txt",
                    size_bytes=100,
                    mtime_epoch=int(datetime.utcnow().timestamp())
                )
                session.add(file_obj)
                session.commit()

                job = IndexJob(file_id=file_obj.id, job_type="index_file")
                job.status = JobStatus.COMPLETED
                job.completed_at = timestamp
                session.add(job)
                jobs.append(job)

            session.commit()

            # Run cleanup with 30-day retention
            cleaned_count = queue_manager.cleanup_old_jobs(session, retention_days=30)

            # Should clean up the 35-day-old job but not the 15-day-old one
            assert cleaned_count == 1

            # Verify the old job is gone and recent job remains
            remaining_jobs = session.query(IndexJob).filter(
                IndexJob.status == JobStatus.COMPLETED
            ).all()

            assert len(remaining_jobs) == 1
            assert remaining_jobs[0].id == jobs[1].id  # Recent job should remain

        finally:
            session.close()