"""
Reindex service for Force Reindex functionality.

This module provides the business logic for batch reindexing operations,
including soft reindex (clear flags) and hard reset (purge and rebuild).
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import func, and_, or_, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.indexing import IndexedFile, IndexJob, JobStatus, DocumentChunk
from app.models.reindex import ReindexBatch, SystemFlag, BatchStatus, ReindexMode

logger = logging.getLogger(__name__)


class ReindexService:
    """Service for managing force reindex operations."""

    CHUNK_SIZE = 5000  # Process files in chunks to avoid memory issues
    MAX_BATCH_JOBS = 10000  # Maximum jobs to create at once

    def __init__(self, session: Session):
        """
        Initialize ReindexService.

        Args:
            session: Database session
        """
        self.session = session

    def create_batch(
        self,
        mode: str,
        path_prefix: Optional[str] = None,
        text_only: bool = True,
        dry_run: bool = False
    ) -> ReindexBatch:
        """
        Create a new reindex batch.

        Args:
            mode: Reindex mode ('soft' or 'hard')
            path_prefix: Optional path filter
            text_only: Whether to only process text files
            dry_run: If True, only calculate counts without creating jobs

        Returns:
            ReindexBatch instance

        Raises:
            ValueError: If there's already an active batch
        """
        # Check for active batch
        if ReindexBatch.has_active_batch(self.session):
            raise ValueError("Another reindex batch is already active")

        # Validate mode
        if mode not in [ReindexMode.SOFT, ReindexMode.HARD]:
            raise ValueError(f"Invalid mode: {mode}")

        # Create batch
        batch = ReindexBatch(
            mode=mode,
            path_prefix=path_prefix,
            text_only=text_only
        )
        self.session.add(batch)
        self.session.commit()

        try:
            # Get candidate files
            candidates = self._get_candidate_files(path_prefix, text_only)
            batch.candidates_count = len(candidates)

            if dry_run:
                # Just return counts for dry run
                batch.status = BatchStatus.COMPLETED
                self.session.commit()
                return batch

            # Set maintenance mode
            SystemFlag.set_maintenance_mode(self.session, True)

            # Execute reindex based on mode
            if mode == ReindexMode.SOFT:
                self._execute_soft_reindex(batch, candidates)
            else:
                self._execute_hard_reset(batch, candidates)

            # Start the batch
            batch.start()
            self.session.commit()

            # Clear maintenance mode
            SystemFlag.set_maintenance_mode(self.session, False)

            logger.info(f"Created reindex batch {batch.id} with {batch.candidates_count} files")
            return batch

        except Exception as e:
            # Rollback on error
            batch.fail(str(e))
            SystemFlag.set_maintenance_mode(self.session, False)
            self.session.commit()
            logger.error(f"Failed to create reindex batch: {e}")
            raise

    def _get_candidate_files(
        self,
        path_prefix: Optional[str] = None,
        text_only: bool = True
    ) -> List[IndexedFile]:
        """
        Get list of files to reindex based on filters.

        Args:
            path_prefix: Optional path filter
            text_only: Whether to only include text files

        Returns:
            List of IndexedFile objects
        """
        query = self.session.query(IndexedFile)

        # Apply path filter
        if path_prefix:
            query = query.filter(IndexedFile.path.like(f"{path_prefix}%"))

        # Apply text-only filter
        if text_only:
            query = query.filter(IndexedFile.is_text == True)

        return query.all()

    def _execute_soft_reindex(self, batch: ReindexBatch, files: List[IndexedFile]) -> None:
        """
        Execute soft reindex - clear indexed flags and create jobs.

        Args:
            batch: ReindexBatch instance
            files: List of files to reindex
        """
        logger.info(f"Executing soft reindex for {len(files)} files")

        # Process in chunks
        for i in range(0, len(files), self.CHUNK_SIZE):
            chunk = files[i:i + self.CHUNK_SIZE]
            file_ids = [f.id for f in chunk]

            # Clear indexed flags
            self.session.query(IndexedFile).filter(
                IndexedFile.id.in_(file_ids)
            ).update({
                IndexedFile.is_indexed: False,
                IndexedFile.last_indexed_at: None,
                IndexedFile.index_version: None
            }, synchronize_session=False)

            # Create reindex jobs
            jobs_created = self._create_reindex_jobs(batch, file_ids)
            batch.jobs_created += jobs_created

            # Commit chunk
            self.session.commit()
            logger.debug(f"Processed chunk {i // self.CHUNK_SIZE + 1}, created {jobs_created} jobs")

    def _execute_hard_reset(self, batch: ReindexBatch, files: List[IndexedFile]) -> None:
        """
        Execute hard reset - purge chunks, clear jobs, and rebuild.

        Args:
            batch: ReindexBatch instance
            files: List of files to reindex
        """
        logger.info(f"Executing hard reset for {len(files)} files")

        # Process in chunks for memory efficiency
        for i in range(0, len(files), self.CHUNK_SIZE):
            chunk = files[i:i + self.CHUNK_SIZE]
            file_ids = [f.id for f in chunk]

            # Start transaction for atomic operations
            try:
                # Delete document chunks
                chunks_deleted = self.session.query(DocumentChunk).filter(
                    DocumentChunk.file_id.in_(file_ids)
                ).delete(synchronize_session=False)

                # Delete ALL jobs for these files (not just pending/failed)
                # This ensures a true hard reset with no leftover job history
                jobs_deleted = self.session.query(IndexJob).filter(
                    IndexJob.file_id.in_(file_ids)
                ).delete(synchronize_session=False)

                # Clear indexed flags
                self.session.query(IndexedFile).filter(
                    IndexedFile.id.in_(file_ids)
                ).update({
                    IndexedFile.is_indexed: False,
                    IndexedFile.last_indexed_at: None,
                    IndexedFile.index_version: None
                }, synchronize_session=False)

                # Create fresh reindex jobs
                jobs_created = self._create_reindex_jobs(batch, file_ids)
                batch.jobs_created += jobs_created

                # Commit chunk
                self.session.commit()
                logger.debug(
                    f"Hard reset chunk {i // self.CHUNK_SIZE + 1}: "
                    f"deleted {chunks_deleted} chunks, {jobs_deleted} jobs, "
                    f"created {jobs_created} new jobs"
                )

            except Exception as e:
                self.session.rollback()
                logger.error(f"Failed to process hard reset chunk: {e}")
                raise

    def _create_reindex_jobs(self, batch: ReindexBatch, file_ids: List[int]) -> int:
        """
        Create reindex jobs for given files.

        TICKET 021 FIX: Now creates TEXT_EXTRACT jobs directly instead of parent jobs.
        This eliminates the two-tier system and ensures consistent batch tracking.

        Args:
            batch: ReindexBatch instance
            file_ids: List of file IDs

        Returns:
            Number of jobs created
        """
        # TICKET 021: Always create TEXT_EXTRACT jobs directly for batch reindex
        # This bypasses the legacy parent job system (index_file/reindex_file)
        # Parent jobs are still used by the watcher for incremental operations
        job_type = "TEXT_EXTRACT"

        jobs = []
        for file_id in file_ids:
            job = IndexJob(
                file_id=file_id,
                job_type=job_type,
                batch_id=batch.id
            )
            jobs.append(job)

            # Batch insert when we reach limit
            if len(jobs) >= self.MAX_BATCH_JOBS:
                self.session.bulk_save_objects(jobs)
                jobs = []

        # Insert remaining jobs
        if jobs:
            self.session.bulk_save_objects(jobs)

        return len(file_ids)

    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Get detailed status of a reindex batch.

        TICKET 021 STEP D: Enhanced with batch-scoped job type breakdown.

        Args:
            batch_id: Batch ID

        Returns:
            Dictionary with batch status and metrics including job type breakdown
        """
        batch = self.session.query(ReindexBatch).filter(
            ReindexBatch.id == batch_id
        ).first()

        if not batch:
            return None

        # Get job statistics by status
        job_stats = self.session.query(
            IndexJob.status,
            func.count(IndexJob.id).label('count')
        ).filter(
            IndexJob.batch_id == batch_id
        ).group_by(IndexJob.status).all()

        job_summary = {status.value: 0 for status in JobStatus}
        for stat in job_stats:
            job_summary[stat.status] = stat.count

        # TICKET 021: Get job type breakdown for batch
        job_type_stats = self.session.query(
            IndexJob.job_type,
            IndexJob.status,
            func.count(IndexJob.id).label('count')
        ).filter(
            IndexJob.batch_id == batch_id
        ).group_by(IndexJob.job_type, IndexJob.status).all()

        # Organize by job type
        job_type_breakdown = {}
        for type_stat in job_type_stats:
            job_type = type_stat.job_type
            if job_type not in job_type_breakdown:
                job_type_breakdown[job_type] = {status.value: 0 for status in JobStatus}
            job_type_breakdown[job_type][type_stat.status] = type_stat.count

        # Calculate processing rate
        if batch.started_at and batch.status == BatchStatus.RUNNING:
            elapsed_seconds = (datetime.utcnow() - batch.started_at).total_seconds()
            if elapsed_seconds > 0:
                processing_rate = (batch.files_processed + batch.files_failed) / elapsed_seconds
            else:
                processing_rate = 0
        else:
            processing_rate = 0

        # Build response
        result = batch.to_dict()
        result['job_summary'] = job_summary
        result['job_type_breakdown'] = job_type_breakdown  # TICKET 021: Added
        result['processing_rate'] = processing_rate

        # Add ETA if batch is running
        if batch.status == BatchStatus.RUNNING and processing_rate > 0:
            result['eta_seconds'] = batch.get_eta_seconds(processing_rate)

        # Add recent errors if any
        if batch.status in [BatchStatus.FAILED, BatchStatus.RUNNING]:
            recent_errors = self.session.query(
                IndexJob.last_error
            ).filter(
                and_(
                    IndexJob.batch_id == batch_id,
                    IndexJob.status == JobStatus.FAILED,
                    IndexJob.last_error.isnot(None)
                )
            ).limit(5).all()
            result['recent_errors'] = [e.last_error for e in recent_errors if e.last_error]

        # TICKET 021: Add consistency check (FTS should not exceed CHUNK)
        chunk_completed = job_type_breakdown.get('CHUNK', {}).get(JobStatus.COMPLETED, 0)
        fts_completed = job_type_breakdown.get('FTS_INDEX', {}).get(JobStatus.COMPLETED, 0)
        result['consistency_check'] = {
            'is_consistent': fts_completed <= chunk_completed,
            'chunk_completed': chunk_completed,
            'fts_completed': fts_completed,
            'warning': None if fts_completed <= chunk_completed else
                      f"FTS completed ({fts_completed}) exceeds CHUNK completed ({chunk_completed})"
        }

        return result

    def pause_batch(self, batch_id: str) -> bool:
        """
        Pause a running batch.

        Args:
            batch_id: Batch ID

        Returns:
            True if paused successfully
        """
        batch = self.session.query(ReindexBatch).filter(
            ReindexBatch.id == batch_id
        ).first()

        if not batch:
            return False

        if batch.status != BatchStatus.RUNNING:
            return False

        batch.pause()
        self.session.commit()
        logger.info(f"Paused reindex batch {batch_id}")
        return True

    def resume_batch(self, batch_id: str) -> bool:
        """
        Resume a paused batch.

        Args:
            batch_id: Batch ID

        Returns:
            True if resumed successfully
        """
        batch = self.session.query(ReindexBatch).filter(
            ReindexBatch.id == batch_id
        ).first()

        if not batch:
            return False

        if batch.status != BatchStatus.PAUSED:
            return False

        batch.resume()
        self.session.commit()
        logger.info(f"Resumed reindex batch {batch_id}")
        return True

    def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel a running or paused batch.

        Args:
            batch_id: Batch ID

        Returns:
            True if cancelled successfully
        """
        batch = self.session.query(ReindexBatch).filter(
            ReindexBatch.id == batch_id
        ).first()

        if not batch:
            return False

        if batch.status not in [BatchStatus.RUNNING, BatchStatus.PAUSED]:
            return False

        # Mark batch as cancelling
        batch.cancel()

        # Delete pending jobs for this batch
        deleted = self.session.query(IndexJob).filter(
            and_(
                IndexJob.batch_id == batch_id,
                IndexJob.status == JobStatus.PENDING
            )
        ).delete(synchronize_session=False)

        # Mark batch as completed (cancelled)
        batch.complete()
        batch.last_error = "Batch cancelled by user"

        # Clear maintenance mode if it was set
        SystemFlag.set_maintenance_mode(self.session, False)

        self.session.commit()
        logger.info(f"Cancelled reindex batch {batch_id}, deleted {deleted} pending jobs")
        return True

    def update_batch_progress(self, batch_id: str) -> None:
        """
        Update batch progress based on job completion.

        Args:
            batch_id: Batch ID
        """
        batch = self.session.query(ReindexBatch).filter(
            ReindexBatch.id == batch_id
        ).first()

        if not batch or batch.status != BatchStatus.RUNNING:
            return

        # Count completed and failed jobs
        from sqlalchemy import Integer as SqlInteger
        stats = self.session.query(
            func.sum(func.cast(IndexJob.status == JobStatus.COMPLETED, SqlInteger)).label('completed'),
            func.sum(func.cast(IndexJob.status == JobStatus.FAILED, SqlInteger)).label('failed')
        ).filter(IndexJob.batch_id == batch_id).first()

        if stats:
            batch.files_processed = stats.completed or 0
            batch.files_failed = stats.failed or 0

            # Check if all jobs are done
            total_done = batch.files_processed + batch.files_failed
            if total_done >= batch.candidates_count:
                batch.complete()
                SystemFlag.set_maintenance_mode(self.session, False)
                logger.info(f"Reindex batch {batch_id} completed: {batch.files_processed} processed, {batch.files_failed} failed")

        self.session.commit()

    def list_batches(self, limit: int = 10, include_completed: bool = False) -> List[Dict[str, Any]]:
        """
        List reindex batches.

        Args:
            limit: Maximum number of batches to return
            include_completed: Whether to include completed/failed batches

        Returns:
            List of batch summaries
        """
        query = self.session.query(ReindexBatch)

        if not include_completed:
            query = query.filter(
                ReindexBatch.status.notin_([BatchStatus.COMPLETED, BatchStatus.FAILED])
            )

        batches = query.order_by(ReindexBatch.created_at.desc()).limit(limit).all()

        return [batch.to_dict() for batch in batches]

    def has_legacy_parent_jobs(self) -> bool:
        """
        Check if there are any legacy parent jobs in the system.

        TICKET 021 STEP D: Detects presence of old-style parent jobs
        (index_file/reindex_file) that were created before the fix.

        Returns:
            True if legacy parent jobs exist
        """
        count = self.session.query(IndexJob).filter(
            IndexJob.job_type.in_(['index_file', 'reindex_file'])
        ).count()

        return count > 0

    def full_reset(self) -> None:
        """
        Perform a complete reset of all indexing state.

        TICKET 021 STEP B: Comprehensive reset that clears:
        - All document chunks
        - FTS virtual table data
        - All index jobs (pending, failed, completed)
        - Indexed file metadata (flags, timestamps)

        This operation:
        - Sets maintenance mode during execution
        - Is fully transactional (rollback on failure)
        - Clears maintenance mode on completion or error
        """
        logger.info("Starting full index reset")

        try:
            # Set maintenance mode
            SystemFlag.set_maintenance_mode(self.session, True)
            logger.info("Maintenance mode enabled for full reset")

            # Delete all document chunks (FTS triggers will handle FTS cleanup)
            chunks_deleted = self.session.query(DocumentChunk).delete()
            logger.info(f"Deleted {chunks_deleted} document chunks")

            # Delete all index jobs
            jobs_deleted = self.session.query(IndexJob).delete()
            logger.info(f"Deleted {jobs_deleted} index jobs")

            # Clear indexed file metadata (but keep the files themselves)
            files_updated = self.session.query(IndexedFile).update({
                IndexedFile.is_indexed: False,
                IndexedFile.last_indexed_at: None,
                IndexedFile.index_version: None
            })
            logger.info(f"Reset metadata for {files_updated} indexed files")

            # Commit the transaction
            self.session.commit()
            logger.info("Full reset completed successfully")

        except Exception as e:
            # Rollback on error
            self.session.rollback()
            logger.error(f"Full reset failed: {e}")
            raise

        finally:
            # Always clear maintenance mode
            SystemFlag.set_maintenance_mode(self.session, False)
            logger.info("Maintenance mode disabled")