"""
Backend API endpoints for indexer service integration.

This module provides API endpoints for the frontend to monitor and control
the indexer service, get statistics, and manage indexing operations.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import func, case, text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.indexing import IndexedFile, IndexJob, ControlSetting, JobStatus, DocumentChunk
from app.services.permission_service import check_access

logger = logging.getLogger(__name__)

# Create router for indexer endpoints
router = APIRouter(prefix="/api/indexer", tags=["indexer"])


# Pydantic models for API responses
class IndexerStatusResponse(BaseModel):
    """Response model for indexer status."""
    is_running: bool
    is_paused: bool
    throttle_percentage: int
    queue_stats: Dict[str, Any]
    file_stats: Dict[str, Any]
    performance_stats: Dict[str, Any]
    service_error: Optional[str] = None
    job_backlog: Dict[str, Any]
    integrity_stats: Dict[str, Any]
    watcher_status: Optional[Dict[str, Any]] = None


class FileMetadata(BaseModel):
    """Response model for file metadata."""
    doc_id: str
    path: str
    size_bytes: int
    mtime_epoch: int
    is_indexed: bool
    mime_type: Optional[str]
    discovered_at: int
    last_indexed_at: Optional[int]


class JobInfo(BaseModel):
    """Response model for job information."""
    id: int
    job_type: str
    status: str
    created_at: int
    retry_count: int
    file_path: Optional[str]


class IndexerControlRequest(BaseModel):
    """Request model for indexer control operations."""
    action: str  # pause, resume, throttle
    value: Optional[int] = None  # For throttle percentage


# Helper functions
async def _get_indexer_service_status() -> Dict[str, Any]:
    """
    Get status from the indexer service via HTTP.

    Returns:
        Status information from indexer service
    """
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://indexer:8002/status", timeout=5.0)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Indexer service returned {response.status_code}"}
    except Exception as e:
        logger.warning(f"Could not reach indexer service: {e}")
        return {"error": f"Indexer service unavailable: {e}"}


def _apply_permission_filter(session: Session, files: List[IndexedFile]) -> List[IndexedFile]:
    """
    Filter files based on current workspace permissions.

    Args:
        session: Database session
        files: List of IndexedFile objects

    Returns:
        Filtered list of files accessible to current workspace
    """
    try:
        filtered_files = []
        for file_obj in files:
            try:
                # Check if file is accessible
                check_access(file_obj.path, 'read')
                filtered_files.append(file_obj)
            except Exception:
                # File not accessible, skip it
                continue

        return filtered_files

    except Exception as e:
        logger.error(f"Error applying permission filter: {e}")
        # Return empty list on error to be safe
        return []


# API endpoints
@router.get("/status", response_model=IndexerStatusResponse)
async def get_indexer_status(session: Session = Depends(get_db)) -> IndexerStatusResponse:
    """
    Get comprehensive indexer status.

    Returns:
        Current status of the indexer service including queue stats and performance metrics
    """
    try:
        # Get control settings
        is_paused = ControlSetting.get_setting(session, "indexer_paused", default=False)
        throttle_pct = ControlSetting.get_setting(session, "throttle_pct", default=0)

        # Get queue statistics
        queue_stats: Dict[str, int] = {}
        for status in JobStatus:
            count = (
                session.query(func.count(IndexJob.id))
                .filter(func.lower(IndexJob.status) == status.value)
                .scalar()
                or 0
            )
            queue_stats[f"{status.value}_jobs"] = int(count)

        # Build job backlog metadata grouped by job type
        job_backlog: Dict[str, Any] = {
            "total_pending": 0,
            "total_processing": 0,
            "total_failed": 0,
            "total_dead_letter": 0,
            "total_completed": 0,
            "by_type": {}
        }

        backlog_rows = (
            session.query(
                IndexJob.job_type.label("job_type"),
                func.sum(case((func.lower(IndexJob.status) == JobStatus.PENDING.value, 1), else_=0)).label("pending"),
                func.sum(case((func.lower(IndexJob.status) == JobStatus.PROCESSING.value, 1), else_=0)).label("processing"),
                func.sum(case((func.lower(IndexJob.status) == JobStatus.FAILED.value, 1), else_=0)).label("failed"),
                func.sum(case((func.lower(IndexJob.status) == JobStatus.DEAD_LETTER.value, 1), else_=0)).label("dead_letter"),
                func.sum(case((func.lower(IndexJob.status) == JobStatus.COMPLETED.value, 1), else_=0)).label("completed"),
            )
            .group_by(IndexJob.job_type)
            .all()
        )

        for row in backlog_rows:
            pending = int((row.pending or 0))
            processing = int((row.processing or 0))
            failed = int((row.failed or 0))
            dead_letter = int((row.dead_letter or 0))
            completed = int((row.completed or 0))

            job_backlog["by_type"][row.job_type] = {
                "pending": pending,
                "processing": processing,
                "failed": failed,
                "dead_letter": dead_letter,
                "completed": completed,
            }
            job_backlog["total_pending"] += pending
            job_backlog["total_processing"] += processing
            job_backlog["total_failed"] += failed
            job_backlog["total_dead_letter"] += dead_letter
            job_backlog["total_completed"] += completed

        job_backlog["total"] = (
            job_backlog["total_pending"]
            + job_backlog["total_processing"]
            + job_backlog["total_failed"]
            + job_backlog["total_dead_letter"]
            + job_backlog["total_completed"]
        )

        # Get file statistics - separate discovery from processing
        total_files = session.query(IndexedFile).count()
        discovered_files = total_files  # All files have been discovered

        # Text vs non-text file breakdown
        text_files = session.query(IndexedFile).filter(IndexedFile.is_text == True).count()
        non_text_files = total_files - text_files

        # Text file processing status
        text_files_indexed = session.query(IndexedFile).filter(
            IndexedFile.is_text == True,
            IndexedFile.is_indexed == True
        ).count()
        text_files_pending = text_files - text_files_indexed

        # Text files with actual chunks (fully processed)
        text_files_with_chunks = (
            session.query(func.count(func.distinct(DocumentChunk.file_id)))
            .join(IndexedFile, DocumentChunk.file_id == IndexedFile.id)
            .filter(IndexedFile.is_text == True)
            .scalar() or 0
        )

        # Text files that were indexed but failed to create chunks
        text_files_failed_processing = text_files_indexed - text_files_with_chunks

        file_stats = {
            "total_files": total_files,
            "discovered_files": discovered_files,
            "text_files": text_files,
            "non_text_files": non_text_files,
            "text_files_indexed": text_files_indexed,
            "text_files_pending": text_files_pending,
            "text_files_with_chunks": text_files_with_chunks,
            "text_files_failed_processing": text_files_failed_processing,
            "text_processing_progress": (text_files_with_chunks / text_files * 100) if text_files > 0 else 100,
            "discovery_progress": 100.0,  # All files discovered
            # Keep old fields for backward compatibility
            "indexed_files": text_files_indexed,  # This was misleading before
            "pending_files": text_files_pending,
            "indexing_progress": (text_files_indexed / total_files * 100) if total_files > 0 else 100,
        }

        # Enhanced integrity checks
        chunks_total = session.query(func.count(DocumentChunk.id)).scalar() or 0

        # Only count TEXT files without chunks as problematic
        text_files_without_chunks = (
            session.query(func.count(IndexedFile.id))
            .outerjoin(DocumentChunk, DocumentChunk.file_id == IndexedFile.id)
            .filter(IndexedFile.is_indexed == True)
            .filter(IndexedFile.is_text == True)
            .filter(DocumentChunk.id.is_(None))
            .scalar()
            or 0
        )

        # Count invalid jobs (reindex_file jobs for non-text files) using raw SQL
        invalid_result = session.execute(
            text("""
                SELECT COUNT(*)
                FROM index_jobs
                JOIN indexed_files ON index_jobs.file_id = indexed_files.id
                WHERE index_jobs.job_type = 'reindex_file'
                AND indexed_files.is_text = 0
            """)
        )
        invalid_reindex_jobs = invalid_result.scalar() or 0

        integrity_stats = {
            "chunks_total": int(chunks_total),
            "files_without_chunks": int(text_files_without_chunks),  # Only text files
            "text_files_without_chunks": int(text_files_without_chunks),
            "invalid_reindex_jobs": int(invalid_reindex_jobs),
        }

        # Get performance statistics from indexer service
        indexer_status = await _get_indexer_service_status()
        service_error = indexer_status.get("error") if isinstance(indexer_status, dict) else None
        service_info = indexer_status.get("service", {}) if isinstance(indexer_status, dict) else {}
        raw_stats = indexer_status.get("stats", {}) if isinstance(indexer_status, dict) else {}
        watcher_status = indexer_status.get("file_watcher", {}) if isinstance(indexer_status, dict) else {}
        performance_stats = {} if service_error else dict(raw_stats or {})

        # Add queue depth and processing rate
        pending_jobs = sum(
            queue_stats.get(key, 0)
            for key in ("pending_jobs", "processing_jobs", "failed_jobs", "dead_letter_jobs")
        )
        queue_stats["queue_depth"] = int(pending_jobs)

        # Calculate estimated completion time
        processing_rate = performance_stats.get("jobs_per_minute", 0)
        if processing_rate and pending_jobs:
            eta_minutes = pending_jobs / processing_rate
            performance_stats["eta_minutes"] = eta_minutes

        return IndexerStatusResponse(
            is_running=bool(service_info.get("is_running")) and service_error is None,
            is_paused=is_paused,
            throttle_percentage=throttle_pct,
            queue_stats=queue_stats,
            file_stats=file_stats,
            performance_stats=performance_stats,
            service_error=service_error,
            job_backlog=job_backlog,
            integrity_stats=integrity_stats,
            watcher_status=watcher_status if watcher_status and not service_error else None,
        )

    except Exception as e:
        logger.error(f"Failed to get indexer status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get indexer status: {e}")


@router.post("/control")
async def control_indexer(
    control_request: IndexerControlRequest,
    session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Control indexer operations (pause, resume, throttle).

    Args:
        control_request: Control action and parameters

    Returns:
        Result of the control operation
    """
    try:
        action = control_request.action.lower()

        if action == "pause":
            ControlSetting.set_setting(session, "indexer_paused", "true", "boolean")
            logger.info("Indexer paused via backend API")
            return {"status": "paused", "action": action}

        elif action == "resume":
            ControlSetting.set_setting(session, "indexer_paused", "false", "boolean")
            logger.info("Indexer resumed via backend API")
            return {"status": "resumed", "action": action}

        elif action == "throttle":
            if control_request.value is None:
                raise HTTPException(status_code=400, detail="Throttle action requires a value")

            percentage = control_request.value
            if not 0 <= percentage <= 100:
                raise HTTPException(status_code=400, detail="Throttle percentage must be between 0 and 100")

            ControlSetting.set_setting(session, "throttle_pct", str(percentage), "integer")
            logger.info(f"Indexer throttle set to {percentage}% via backend API")
            return {"status": "throttle_set", "percentage": percentage, "action": action}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to control indexer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to control indexer: {e}")


@router.get("/files", response_model=List[FileMetadata])
async def list_indexed_files(
    limit: int = 100,
    offset: int = 0,
    indexed_only: bool = False,
    session: Session = Depends(get_db)
) -> List[FileMetadata]:
    """
    List indexed files with pagination and filtering.

    Args:
        limit: Maximum number of files to return
        offset: Number of files to skip
        indexed_only: If True, return only indexed files

    Returns:
        List of file metadata objects
    """
    try:
        # Validate pagination parameters
        if limit > 1000:
            limit = 1000
        if offset < 0:
            offset = 0

        # Build query
        query = session.query(IndexedFile)

        if indexed_only:
            query = query.filter(IndexedFile.is_indexed == True)

        # Apply pagination
        files = query.order_by(IndexedFile.discovered_at.desc()).offset(offset).limit(limit).all()

        # Apply permission filtering
        filtered_files = _apply_permission_filter(session, files)

        # Convert to response models
        file_metadata = []
        for file_obj in filtered_files:
            file_metadata.append(FileMetadata(
                doc_id=file_obj.doc_id,
                path=file_obj.path,
                size_bytes=file_obj.size_bytes,
                mtime_epoch=file_obj.mtime_epoch,
                is_indexed=file_obj.is_indexed,
                mime_type=file_obj.mime_type,
                discovered_at=file_obj.discovered_at,
                last_indexed_at=file_obj.last_indexed_at
            ))

        logger.debug(f"Listed {len(file_metadata)} files (filtered from {len(files)})")
        return file_metadata

    except Exception as e:
        logger.error(f"Failed to list indexed files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {e}")


@router.get("/jobs", response_model=List[JobInfo])
async def list_indexing_jobs(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    session: Session = Depends(get_db)
) -> List[JobInfo]:
    """
    List indexing jobs with pagination and filtering.

    Args:
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
        status_filter: Optional status to filter by

    Returns:
        List of job information objects
    """
    try:
        # Validate parameters
        if limit > 500:
            limit = 500
        if offset < 0:
            offset = 0

        # Build query
        query = session.query(IndexJob)

        if status_filter:
            if status_filter not in [status.value for status in JobStatus]:
                raise HTTPException(status_code=400, detail=f"Invalid status filter: {status_filter}")
            query = query.filter(IndexJob.status == status_filter)

        # Apply pagination and ordering
        jobs = query.order_by(IndexJob.created_at.desc()).offset(offset).limit(limit).all()

        # Convert to response models
        job_info = []
        for job in jobs:
            file_path = job.file.path if job.file else None

            # Apply permission filtering for file paths
            if file_path:
                try:
                    check_access(file_path, 'read')
                except Exception:
                    # File not accessible, hide the path
                    file_path = "[restricted]"

            job_info.append(JobInfo(
                id=job.id,
                job_type=job.job_type,
                status=job.status,
                created_at=job.created_at,
                retry_count=job.retry_count,
                file_path=file_path
            ))

        return job_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list indexing jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {e}")


@router.post("/requeue-dead-letter")
async def requeue_dead_letter_jobs(session: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Requeue all jobs currently in dead_letter status back to pending.

    This endpoint is used to retry jobs that have failed after multiple attempts
    and have been moved to dead_letter status. Useful after fixing underlying
    issues that caused the jobs to fail.

    Returns:
        Result of the requeue operation including count of requeued jobs
    """
    try:
        # Count dead letter jobs before requeue
        dead_letter_count = (
            session.query(IndexJob)
            .filter(func.lower(IndexJob.status) == JobStatus.DEAD_LETTER.value)
            .count()
        )

        if dead_letter_count == 0:
            return {
                "status": "no_jobs",
                "message": "No dead letter jobs found to requeue",
                "requeued_count": 0
            }

        # Update all dead letter jobs to pending status and reset retry count
        updated_count = (
            session.query(IndexJob)
            .filter(func.lower(IndexJob.status) == JobStatus.DEAD_LETTER.value)
            .update({
                IndexJob.status: JobStatus.PENDING.value,
                IndexJob.retry_count: 0,
                IndexJob.last_error: None,
                IndexJob.claimed_at: None,
                IndexJob.worker_id: None,
                IndexJob.next_retry_at: None
            }, synchronize_session=False)
        )

        session.commit()

        logger.info(f"Requeued {updated_count} dead letter jobs to pending status")
        return {
            "status": "requeued",
            "message": f"Successfully requeued {updated_count} dead letter jobs",
            "requeued_count": updated_count
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to requeue dead letter jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to requeue jobs: {e}")


@router.post("/clear-failed")
async def clear_failed_jobs(session: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Clear all jobs in failed status from the queue.

    This endpoint removes failed jobs from the queue to clean up the job history.
    Note: This only affects jobs in 'failed' status, not 'dead_letter' status.

    Returns:
        Result of the clear operation including count of cleared jobs
    """
    try:
        # Count failed jobs before clearing
        failed_count = (
            session.query(IndexJob)
            .filter(func.lower(IndexJob.status) == JobStatus.FAILED.value)
            .count()
        )

        if failed_count == 0:
            return {
                "status": "no_jobs",
                "message": "No failed jobs found to clear",
                "cleared_count": 0
            }

        # Delete failed jobs
        deleted_count = (
            session.query(IndexJob)
            .filter(func.lower(IndexJob.status) == JobStatus.FAILED.value)
            .delete(synchronize_session=False)
        )

        session.commit()

        logger.info(f"Cleared {deleted_count} failed jobs from queue")
        return {
            "status": "cleared",
            "message": f"Successfully cleared {deleted_count} failed jobs",
            "cleared_count": deleted_count
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to clear failed jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear jobs: {e}")


@router.post("/clear-invalid-jobs")
async def clear_invalid_jobs(session: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Clear invalid reindex_file jobs for non-text files.

    This endpoint removes reindex_file jobs that were incorrectly created for non-text files.
    These jobs cannot succeed because non-text files don't go through text processing.

    Returns:
        Result of the clear operation including count of cleared jobs
    """
    try:
        # Use raw SQL to avoid ORM column issues with batch_id
        # Count invalid reindex jobs before clearing
        count_result = session.execute(
            text("""
                SELECT COUNT(*)
                FROM index_jobs
                JOIN indexed_files ON index_jobs.file_id = indexed_files.id
                WHERE index_jobs.job_type = 'reindex_file'
                AND indexed_files.is_text = 0
            """)
        )
        invalid_count = count_result.scalar()

        if invalid_count == 0:
            return {
                "status": "no_jobs",
                "message": "No invalid reindex jobs found to clear",
                "cleared_count": 0
            }

        # Delete invalid reindex jobs using raw SQL
        delete_result = session.execute(
            text("""
                DELETE FROM index_jobs
                WHERE id IN (
                    SELECT index_jobs.id
                    FROM index_jobs
                    JOIN indexed_files ON index_jobs.file_id = indexed_files.id
                    WHERE index_jobs.job_type = 'reindex_file'
                    AND indexed_files.is_text = 0
                )
            """)
        )
        deleted_count = delete_result.rowcount

        session.commit()

        logger.info(f"Cleared {deleted_count} invalid reindex jobs for non-text files")
        return {
            "status": "cleared",
            "message": f"Successfully cleared {deleted_count} invalid reindex jobs for non-text files",
            "cleared_count": deleted_count
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to clear invalid jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear invalid jobs: {e}")


@router.post("/reindex/{doc_id}")
async def reindex_file(
    doc_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Trigger reindexing of a specific file.

    Args:
        doc_id: Document ID of the file to reindex
        background_tasks: FastAPI background tasks

    Returns:
        Result of the reindexing request
    """
    try:
        # Find the file
        file_obj = session.query(IndexedFile).filter(IndexedFile.doc_id == doc_id).first()
        if not file_obj:
            raise HTTPException(status_code=404, detail=f"File not found: {doc_id}")

        # Check permissions
        try:
            check_access(file_obj.path, 'read')
        except Exception as e:
            raise HTTPException(status_code=403, detail=f"Access denied: {e}")

        # Create reindexing job
        from app.models.indexing import IndexJob
        job = IndexJob(file_id=file_obj.id, job_type="reindex_file")
        session.add(job)

        # Mark file as needing reindexing
        file_obj.is_indexed = False

        session.commit()

        logger.info(f"Reindexing requested for file: {file_obj.path}")
        return {
            "status": "reindex_queued",
            "doc_id": doc_id,
            "job_id": job.id,
            "file_path": file_obj.path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue reindexing for {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue reindexing: {e}")


@router.get("/logs")
async def get_indexer_logs(
    limit: int = 100,
    level: str = "error",
    session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get recent error logs and failed job information.

    Args:
        limit: Maximum number of log entries to return
        level: Log level filter (error, warning, info)

    Returns:
        Recent logs and failed job information
    """
    try:
        # Get recent failed jobs with error messages
        failed_jobs = (
            session.query(IndexJob)
            .filter(
                (func.lower(IndexJob.status) == JobStatus.FAILED.value) |
                (func.lower(IndexJob.status) == JobStatus.DEAD_LETTER.value)
            )
            .filter(IndexJob.last_error.is_not(None))
            .order_by(IndexJob.created_at.desc())
            .limit(limit)
            .all()
        )

        # Format job errors as log entries
        log_entries = []
        for job in failed_jobs:
            file_path = job.file.path if job.file else "Unknown file"
            log_entries.append({
                "timestamp": job.created_at,
                "level": "error",
                "component": "indexer",
                "job_id": job.id,
                "job_type": job.job_type,
                "file_path": file_path,
                "message": job.last_error or "No error message available",
                "retry_count": job.retry_count,
                "status": job.status
            })

        return {
            "logs": log_entries,
            "total_entries": len(log_entries),
            "timestamp": int(datetime.utcnow().timestamp())
        }

    except Exception as e:
        logger.error(f"Failed to get indexer logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {e}")


@router.get("/health")
async def get_indexer_health() -> Dict[str, Any]:
    """
    Get health status of the indexer service.

    Returns:
        Health information including service connectivity and basic metrics
    """
    try:
        # Check indexer service connectivity
        indexer_status = await _get_indexer_service_status()

        # Check database connectivity
        with next(get_db()) as session:
            session.execute("SELECT 1").fetchone()

        health_status = {
            "status": "healthy",
            "indexer_service": "connected" if "error" not in indexer_status else "disconnected",
            "database": "connected",
            "timestamp": indexer_status.get("timestamp", 0)
        }

        if "error" in indexer_status:
            health_status["indexer_error"] = indexer_status["error"]

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "indexer_service": "unknown",
            "database": "unknown"
        }