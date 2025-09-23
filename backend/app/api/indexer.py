"""
Backend API endpoints for indexer service integration.

This module provides API endpoints for the frontend to monitor and control
the indexer service, get statistics, and manage indexing operations.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.indexing import IndexedFile, IndexJob, ControlSetting, JobStatus
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
        queue_stats = {}
        for status in JobStatus:
            count = session.query(IndexJob).filter(IndexJob.status == status.value).count()
            queue_stats[f"{status.value}_jobs"] = count

        # Get file statistics
        total_files = session.query(IndexedFile).count()
        indexed_files = session.query(IndexedFile).filter(IndexedFile.is_indexed == True).count()
        pending_files = total_files - indexed_files

        file_stats = {
            "total_files": total_files,
            "indexed_files": indexed_files,
            "pending_files": pending_files,
            "indexing_progress": (indexed_files / total_files * 100) if total_files > 0 else 100
        }

        # Get performance statistics from indexer service
        indexer_status = await _get_indexer_service_status()
        performance_stats = indexer_status.get("stats", {})

        # Add queue depth and processing rate
        pending_jobs = queue_stats.get("pending_jobs", 0) + queue_stats.get("failed_jobs", 0)
        queue_stats["queue_depth"] = pending_jobs

        # Calculate estimated completion time
        processing_rate = performance_stats.get("jobs_per_minute", 0)
        if processing_rate > 0 and pending_jobs > 0:
            eta_minutes = pending_jobs / processing_rate
            performance_stats["eta_minutes"] = eta_minutes

        return IndexerStatusResponse(
            is_running=indexer_status.get("service", {}).get("is_running", False),
            is_paused=is_paused,
            throttle_percentage=throttle_pct,
            queue_stats=queue_stats,
            file_stats=file_stats,
            performance_stats=performance_stats
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