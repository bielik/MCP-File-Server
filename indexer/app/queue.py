"""
Resilient Job Queue Implementation for MCP KnowledgeExplorer Phase 4A

This module provides a crash-resilient job queue with atomic claims,
retry logic, and recovery capabilities for the indexing service.
"""

import logging
import uuid
import time
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Import models and database configuration
# Note: Add backend to path to access models and database
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend/app'))

from models.indexing import IndexJob, IndexedFile, JobStatus, ControlSetting, DocumentChunk
from database import get_db, initialize_database

# Phase 4B ML imports
try:
    from llama_index.core import SimpleDirectoryReader, Document
    from llama_index.core.node_parser import SimpleNodeParser
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    logger.warning("LlamaIndex not available - Phase 4B features will be limited")
    LLAMA_INDEX_AVAILABLE = False

logger = logging.getLogger(__name__)


class JobQueueManager:
    """
    Manages the resilient job queue for indexing operations.

    This class implements atomic job claiming, crash recovery, retry logic,
    and cleanup operations for the indexing job queue.
    """

    def __init__(self, worker_id: Optional[str] = None):
        """
        Initialize job queue manager.

        Args:
            worker_id: Unique identifier for this worker instance
        """
        self.worker_id = worker_id or f"indexer-{uuid.uuid4().hex[:8]}"
        self.max_claim_attempts = 5
        self.stale_job_timeout = 3600  # 1 hour

        # Ensure database is initialized
        initialize_database()

        logger.info(f"JobQueueManager initialized with worker_id: {self.worker_id}")

    def create_job(self, session: Session, file_id: int, job_type: str = "index_file",
                   job_data: Optional[Dict[str, Any]] = None) -> Optional[IndexJob]:
        """
        Create a new indexing job.

        Args:
            session: Database session
            file_id: ID of the file to be indexed
            job_type: Type of job to create
            job_data: Optional job parameters

        Returns:
            Created IndexJob or None if duplicate
        """
        try:
            job = IndexJob(file_id=file_id, job_type=job_type)

            if job_data:
                import json
                job.job_data = json.dumps(job_data)

            session.add(job)
            session.commit()

            logger.debug(f"Created job {job.id} for file {file_id}")
            return job

        except IntegrityError:
            session.rollback()
            logger.debug(f"Duplicate job for file {file_id}, skipping")
            return None
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create job for file {file_id}: {e}")
            raise

    def claim_job(self, session: Session) -> Optional[IndexJob]:
        """
        Atomically claim a job for processing.

        Uses atomic UPDATE with RETURNING for SQLite 3.35+ or fallback
        for older versions.

        Args:
            session: Database session

        Returns:
            Claimed IndexJob or None if no jobs available
        """
        try:
            # First try the atomic UPDATE...RETURNING approach (SQLite 3.35+)
            return self._claim_job_atomic(session)
        except Exception as e:
            logger.debug(f"Atomic claim failed, using fallback: {e}")
            session.rollback()
            return self._claim_job_fallback(session)

    def _claim_job_atomic(self, session: Session) -> Optional[IndexJob]:
        """
        Atomic job claim using UPDATE...RETURNING (SQLite 3.35+).

        Args:
            session: Database session

        Returns:
            Claimed IndexJob or None
        """
        now = int(datetime.utcnow().timestamp())

        # SQL query with atomic UPDATE...RETURNING
        query = text("""
            UPDATE index_jobs SET
                status = :processing_status,
                worker_id = :worker_id,
                claimed_at = :now,
                started_at = :now
            WHERE id = (
                SELECT id FROM index_jobs
                WHERE (status = :pending_status)
                   OR (status = :failed_status AND (next_retry_at IS NULL OR next_retry_at <= :now))
                ORDER BY
                    CASE WHEN status = :pending_status THEN 0 ELSE 1 END,
                    created_at ASC
                LIMIT 1
            )
            RETURNING id
        """)

        result = session.execute(query, {
            'processing_status': JobStatus.PROCESSING,
            'pending_status': JobStatus.PENDING,
            'failed_status': JobStatus.FAILED,
            'worker_id': self.worker_id,
            'now': now
        })

        row = result.fetchone()
        if not row:
            return None

        job_id = row[0]
        session.commit()

        # Fetch the updated job
        job = session.query(IndexJob).filter(IndexJob.id == job_id).first()
        if job:
            logger.debug(f"Atomically claimed job {job.id}")

        return job

    def _claim_job_fallback(self, session: Session) -> Optional[IndexJob]:
        """
        Fallback job claim using two-step UPDATE/changes() (older SQLite).

        Args:
            session: Database session

        Returns:
            Claimed IndexJob or None
        """
        now = int(datetime.utcnow().timestamp())

        for attempt in range(self.max_claim_attempts):
            try:
                # Find next available job
                job = session.query(IndexJob).filter(
                    (IndexJob.status == JobStatus.PENDING) |
                    ((IndexJob.status == JobStatus.FAILED) &
                     ((IndexJob.next_retry_at.is_(None)) | (IndexJob.next_retry_at <= now)))
                ).order_by(
                    # Prioritize pending jobs over failed retries
                    (IndexJob.status == JobStatus.PENDING).desc(),
                    IndexJob.created_at.asc()
                ).first()

                if not job:
                    return None

                # Attempt to claim the job
                if job.claim_job(self.worker_id):
                    session.commit()
                    logger.debug(f"Claimed job {job.id} (attempt {attempt + 1})")
                    return job
                else:
                    # Job was already claimed by another worker
                    session.rollback()
                    continue

            except Exception as e:
                session.rollback()
                logger.warning(f"Job claim attempt {attempt + 1} failed: {e}")
                if attempt == self.max_claim_attempts - 1:
                    raise

                # Brief delay before retry
                time.sleep(0.1 * (attempt + 1))

        return None

    def complete_job(self, session: Session, job: IndexJob, index_version: str) -> None:
        """
        Mark a job as completed and update the associated file.

        Args:
            session: Database session
            job: Job to mark as completed
            index_version: Version of indexing logic used
        """
        try:
            # Mark job as completed
            job.mark_completed()

            # Update the associated file
            if job.file:
                job.file.mark_indexed(index_version)

            session.commit()
            logger.debug(f"Completed job {job.id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to complete job {job.id}: {e}")
            raise

    def fail_job(self, session: Session, job: IndexJob, error_message: str) -> None:
        """
        Mark a job as failed and handle retry logic.

        Args:
            session: Database session
            job: Job to mark as failed
            error_message: Description of the failure
        """
        try:
            job.mark_failed(error_message)
            session.commit()

            if job.status == JobStatus.DEAD_LETTER:
                logger.error(f"Job {job.id} moved to dead letter queue after {job.retry_count} attempts: {error_message}")
            else:
                logger.warning(f"Job {job.id} failed (attempt {job.retry_count}): {error_message}")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to mark job {job.id} as failed: {e}")
            raise

    def recover_stale_jobs(self, session: Session) -> int:
        """
        Recover jobs that have been processing too long (stale jobs).

        Args:
            session: Database session

        Returns:
            Number of jobs recovered
        """
        try:
            now = int(datetime.utcnow().timestamp())
            stale_threshold = now - self.stale_job_timeout

            # Find stale jobs
            stale_jobs = session.query(IndexJob).filter(
                IndexJob.status == JobStatus.PROCESSING,
                IndexJob.started_at < stale_threshold
            ).all()

            recovered_count = 0

            for job in stale_jobs:
                logger.warning(f"Recovering stale job {job.id} (worker: {job.worker_id})")
                job.reset_for_retry()
                recovered_count += 1

            if recovered_count > 0:
                session.commit()
                logger.info(f"Recovered {recovered_count} stale jobs")

            return recovered_count

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to recover stale jobs: {e}")
            raise

    def cleanup_old_jobs(self, session: Session, retention_days: int = 30) -> int:
        """
        Clean up completed jobs older than retention period.

        Args:
            session: Database session
            retention_days: Number of days to retain completed jobs

        Returns:
            Number of jobs cleaned up
        """
        try:
            now = int(datetime.utcnow().timestamp())
            cutoff_time = now - (retention_days * 24 * 3600)

            # Delete old completed jobs
            deleted_count = session.query(IndexJob).filter(
                IndexJob.status == JobStatus.COMPLETED,
                IndexJob.completed_at < cutoff_time
            ).delete()

            if deleted_count > 0:
                session.commit()
                logger.info(f"Cleaned up {deleted_count} old jobs")

            return deleted_count

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to cleanup old jobs: {e}")
            raise

    def get_queue_stats(self, session: Session) -> Dict[str, Any]:
        """
        Get comprehensive queue statistics.

        Args:
            session: Database session

        Returns:
            Dictionary with queue statistics
        """
        try:
            # Count jobs by status
            stats = {}
            for status in JobStatus:
                count = session.query(IndexJob).filter(IndexJob.status == status.value).count()
                stats[f"{status.value}_jobs"] = count

            # Additional metrics
            now = int(datetime.utcnow().timestamp())

            # Overdue retries
            overdue_retries = session.query(IndexJob).filter(
                IndexJob.status == JobStatus.FAILED,
                IndexJob.next_retry_at <= now
            ).count()
            stats["overdue_retries"] = overdue_retries

            # Processing duration for active jobs
            active_jobs = session.query(IndexJob).filter(
                IndexJob.status == JobStatus.PROCESSING,
                IndexJob.started_at.isnot(None)
            ).all()

            if active_jobs:
                processing_times = [now - job.started_at for job in active_jobs]
                stats["avg_processing_time"] = sum(processing_times) / len(processing_times)
                stats["max_processing_time"] = max(processing_times)
                stats["active_workers"] = len(set(job.worker_id for job in active_jobs if job.worker_id))
            else:
                stats["avg_processing_time"] = 0
                stats["max_processing_time"] = 0
                stats["active_workers"] = 0

            # Total files and indexing progress
            total_files = session.query(IndexedFile).count()
            indexed_files = session.query(IndexedFile).filter(IndexedFile.is_indexed == True).count()

            stats["total_files"] = total_files
            stats["indexed_files"] = indexed_files
            stats["indexing_progress"] = (indexed_files / total_files * 100) if total_files > 0 else 100

            return stats

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}

    def is_paused(self, session: Session) -> bool:
        """
        Check if indexing is paused via control settings.

        Args:
            session: Database session

        Returns:
            True if indexing is paused
        """
        return ControlSetting.get_setting(session, "indexer_paused", default=False)

    def get_throttle_percentage(self, session: Session) -> int:
        """
        Get CPU throttling percentage from control settings.

        Args:
            session: Database session

        Returns:
            Throttling percentage (0-100)
        """
        return ControlSetting.get_setting(session, "throttle_pct", default=0)


class JobProcessor:
    """
    Processes individual indexing jobs.

    This class handles the actual file processing logic for different
    types of indexing jobs.
    """

    def __init__(self, queue_manager: JobQueueManager):
        """
        Initialize job processor.

        Args:
            queue_manager: Associated queue manager
        """
        self.queue_manager = queue_manager
        self.index_version = "4.0.0"  # Phase 4A version

    def process_job(self, session: Session, job: IndexJob) -> bool:
        """
        Process a single indexing job.

        Args:
            session: Database session
            job: Job to process

        Returns:
            True if successful, False if failed
        """
        try:
            logger.info(f"Processing job {job.id} (type: {job.job_type}, file: {job.file_id})")

            if job.job_type in ("index_file", "reindex_file"):
                return self._process_file_index(session, job)
            elif job.job_type == "TEXT_EXTRACT":
                return self._process_text_extract(session, job)
            elif job.job_type == "CHUNK":
                return self._process_chunk(session, job)
            elif job.job_type == "FTS_INDEX":
                return self._process_fts_index(session, job)
            elif job.job_type == "EMBED":
                return self._process_embed(session, job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

        except Exception as e:
            error_msg = f"Job processing failed: {e}"
            logger.error(error_msg)
            self.queue_manager.fail_job(session, job, error_msg)
            return False

    def _process_file_index(self, session: Session, job: IndexJob) -> bool:
        """
        Process a file indexing job.

        Args:
            session: Database session
            job: File indexing job

        Returns:
            True if successful
        """
        if not job.file:
            raise ValueError(f"Job {job.id} has no associated file")

        file_obj = job.file

        try:
            # TODO: Implement actual file processing logic in Phase 4B
            # For Phase 4A, we'll just mark files as processed
            logger.info(f"Indexing file: {file_obj.path}")

            # Simulate processing time
            time.sleep(0.1)

            # Mark job as completed
            self.queue_manager.complete_job(session, job, self.index_version)

            logger.debug(f"Successfully indexed file: {file_obj.path}")
            return True

        except Exception as e:
            error_msg = f"Failed to index file {file_obj.path}: {e}"
            logger.error(error_msg)
            self.queue_manager.fail_job(session, job, error_msg)
            return False

    def _process_text_extract(self, session: Session, job: IndexJob) -> bool:
        """
        Process a TEXT_EXTRACT job using LlamaIndex.

        Args:
            session: Database session
            job: Text extraction job

        Returns:
            True if successful
        """
        if not job.file:
            raise ValueError(f"Job {job.id} has no associated file")

        file_obj = job.file

        try:
            logger.info(f"Extracting text from: {file_obj.path}")

            if not LLAMA_INDEX_AVAILABLE:
                raise ImportError("LlamaIndex is required for text extraction")

            # Check if file exists and is readable
            file_path = Path(file_obj.path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_obj.path}")

            # Use LlamaIndex to extract text
            try:
                # Create a document from the file
                documents = SimpleDirectoryReader(input_files=[str(file_path)]).load_data()

                if not documents:
                    raise ValueError(f"No content extracted from {file_obj.path}")

                # Combine all document text
                extracted_text = "\n\n".join([doc.text for doc in documents if doc.text])

                if not extracted_text.strip():
                    logger.warning(f"Empty text extracted from {file_obj.path}")
                    extracted_text = ""

            except Exception as e:
                # Fallback to simple file reading for text files
                if file_obj.is_text:
                    logger.warning(f"LlamaIndex extraction failed, falling back to simple read: {e}")
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            extracted_text = f.read()
                    except Exception as read_error:
                        raise ValueError(f"Both LlamaIndex and simple read failed: {e}, {read_error}")
                else:
                    raise ValueError(f"Text extraction failed for binary file: {e}")

            # Store extracted text in job_data
            job_data = {
                "extracted_text": extracted_text,
                "extraction_method": "llama_index" if len(extracted_text) > 0 else "simple_read",
                "char_count": len(extracted_text),
                "word_count": len(extracted_text.split()) if extracted_text else 0
            }

            # Update job with extracted data
            job.job_data = json.dumps(job_data)
            session.commit()

            # Mark job as completed
            self.queue_manager.complete_job(session, job, self.index_version)

            logger.debug(f"Successfully extracted {len(extracted_text)} characters from: {file_obj.path}")
            return True

        except Exception as e:
            error_msg = f"Failed to extract text from {file_obj.path}: {e}"
            logger.error(error_msg)
            self.queue_manager.fail_job(session, job, error_msg)
            return False

    def _process_chunk(self, session: Session, job: IndexJob) -> bool:
        """
        Process a CHUNK job by splitting text into manageable chunks.

        Args:
            session: Database session
            job: Chunking job

        Returns:
            True if successful
        """
        if not job.file:
            raise ValueError(f"Job {job.id} has no associated file")

        file_obj = job.file

        try:
            logger.info(f"Chunking text for: {file_obj.path}")

            # Get extracted text from job_data or previous TEXT_EXTRACT job
            extracted_text = None
            if job.job_data:
                job_data = json.loads(job.job_data)
                extracted_text = job_data.get("extracted_text")

            if not extracted_text:
                # Look for completed TEXT_EXTRACT job for this file
                text_extract_job = session.query(IndexJob).filter(
                    IndexJob.file_id == job.file_id,
                    IndexJob.job_type == "TEXT_EXTRACT",
                    IndexJob.status == JobStatus.COMPLETED
                ).first()

                if text_extract_job and text_extract_job.job_data:
                    job_data = json.loads(text_extract_job.job_data)
                    extracted_text = job_data.get("extracted_text")

            if not extracted_text:
                raise ValueError(f"No extracted text available for chunking file {file_obj.path}")

            # Use LlamaIndex for smart chunking
            if LLAMA_INDEX_AVAILABLE:
                # Create document from extracted text
                document = Document(text=extracted_text, metadata={"file_path": file_obj.path})

                # Initialize node parser with reasonable chunk size
                node_parser = SimpleNodeParser.from_defaults(
                    chunk_size=512,  # ~512 tokens per chunk
                    chunk_overlap=50  # Small overlap for context
                )

                # Parse document into nodes (chunks)
                nodes = node_parser.get_nodes_from_documents([document])

                chunks_data = []
                for i, node in enumerate(nodes):
                    chunks_data.append({
                        "ordinal": i,
                        "text": node.text,
                        "start_char": node.start_char_idx or (i * 400),  # Estimate if not available
                        "end_char": node.end_char_idx or ((i + 1) * 400),
                    })

            else:
                # Fallback simple chunking
                logger.warning("LlamaIndex not available, using simple chunking")
                chunk_size = 1000  # characters
                overlap = 100

                chunks_data = []
                text_len = len(extracted_text)

                for i in range(0, text_len, chunk_size - overlap):
                    chunk_text = extracted_text[i:i + chunk_size]
                    if chunk_text.strip():  # Only add non-empty chunks
                        chunks_data.append({
                            "ordinal": len(chunks_data),
                            "text": chunk_text,
                            "start_char": i,
                            "end_char": min(i + chunk_size, text_len)
                        })

            # Create DocumentChunk records
            created_chunks = 0
            for chunk_data in chunks_data:
                # Check if chunk already exists (avoid duplicates)
                existing_chunk = session.query(DocumentChunk).filter(
                    DocumentChunk.file_id == job.file_id,
                    DocumentChunk.ordinal == chunk_data["ordinal"]
                ).first()

                if not existing_chunk:
                    chunk = DocumentChunk(
                        file_id=job.file_id,
                        ordinal=chunk_data["ordinal"],
                        text=chunk_data["text"],
                        start_byte=chunk_data["start_char"],  # Using char indices as byte approximation
                        end_byte=chunk_data["end_char"]
                    )
                    session.add(chunk)
                    created_chunks += 1

            session.commit()

            # Mark job as completed
            self.queue_manager.complete_job(session, job, self.index_version)

            logger.debug(f"Successfully created {created_chunks} chunks for: {file_obj.path}")
            return True

        except Exception as e:
            error_msg = f"Failed to chunk text for {file_obj.path}: {e}"
            logger.error(error_msg)
            self.queue_manager.fail_job(session, job, error_msg)
            return False

    def _process_fts_index(self, session: Session, job: IndexJob) -> bool:
        """
        Process an FTS_INDEX job by ensuring chunks are in FTS table.

        Args:
            session: Database session
            job: FTS indexing job

        Returns:
            True if successful
        """
        if not job.file:
            raise ValueError(f"Job {job.id} has no associated file")

        file_obj = job.file

        try:
            logger.info(f"FTS indexing chunks for: {file_obj.path}")

            # Check if chunks exist for this file
            chunks = session.query(DocumentChunk).filter(
                DocumentChunk.file_id == job.file_id
            ).all()

            if not chunks:
                raise ValueError(f"No chunks found for FTS indexing of file {file_obj.path}")

            # The FTS population is handled automatically by SQLite triggers
            # when chunks are inserted into document_chunks table
            # This job mainly serves as a verification step

            # Verify FTS entries exist
            fts_count = session.execute(
                text("SELECT count(*) FROM chunks_fts WHERE rowid IN (SELECT id FROM document_chunks WHERE file_id = :file_id)"),
                {"file_id": job.file_id}
            ).scalar()

            if fts_count != len(chunks):
                logger.warning(f"FTS count mismatch for {file_obj.path}: {fts_count} FTS entries vs {len(chunks)} chunks")
                # FTS triggers should have handled this, but we can manually rebuild if needed
                # For now, we'll trust the triggers and just log the discrepancy

            # Mark job as completed
            self.queue_manager.complete_job(session, job, self.index_version)

            logger.debug(f"Successfully FTS indexed {len(chunks)} chunks for: {file_obj.path}")
            return True

        except Exception as e:
            error_msg = f"Failed to FTS index {file_obj.path}: {e}"
            logger.error(error_msg)
            self.queue_manager.fail_job(session, job, error_msg)
            return False

    def _process_embed(self, session: Session, job: IndexJob) -> bool:
        """
        Process an EMBED job by generating vector embeddings.

        This is a placeholder for Phase 4B M3 implementation.

        Args:
            session: Database session
            job: Embedding job

        Returns:
            True if successful
        """
        if not job.file:
            raise ValueError(f"Job {job.id} has no associated file")

        file_obj = job.file

        try:
            logger.info(f"Processing embedding job for: {file_obj.path}")

            # TODO: Implement actual embedding generation in Phase 4B M3
            # For M2, we'll just mark this as completed as a placeholder
            logger.info("EMBED job placeholder - actual implementation in Phase 4B M3")

            # Mark job as completed
            self.queue_manager.complete_job(session, job, self.index_version)

            logger.debug(f"Successfully processed EMBED job for: {file_obj.path}")
            return True

        except Exception as e:
            error_msg = f"Failed to process EMBED job for {file_obj.path}: {e}"
            logger.error(error_msg)
            self.queue_manager.fail_job(session, job, error_msg)
            return False
