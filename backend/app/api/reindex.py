"""
API endpoints for Force Reindex functionality.

This module provides REST API endpoints for managing batch reindex operations,
including creating batches, monitoring progress, and controlling execution.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.reindex_service import ReindexService
from app.models.reindex import BatchStatus

logger = logging.getLogger(__name__)

# Create router for reindex endpoints
router = APIRouter(prefix="/admin/reindex", tags=["admin", "reindex"])


# Pydantic models for API requests/responses
class ReindexScope(BaseModel):
    """Scope configuration for reindex operation."""
    path_prefix: Optional[str] = Field(None, description="Optional path prefix filter")
    text_only: bool = Field(True, description="Whether to only reindex text files")


class ReindexRequest(BaseModel):
    """Request model for creating a reindex batch."""
    mode: str = Field(..., description="Reindex mode: 'soft' or 'hard'")
    scope: ReindexScope = Field(..., description="Scope configuration")
    dry_run: bool = Field(False, description="If true, only calculate counts without executing")


class ReindexResponse(BaseModel):
    """Response model for reindex operations."""
    batch_id: str
    status: str
    counts: Dict[str, int]
    message: Optional[str] = None


class BatchStatusResponse(BaseModel):
    """Response model for batch status."""
    batch_id: str
    mode: str
    status: str
    path_prefix: Optional[str]
    text_only: bool
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    candidates_count: int
    jobs_created: int
    files_processed: int
    files_failed: int
    progress_percentage: float
    job_summary: Dict[str, int]
    processing_rate: float
    eta_seconds: Optional[int]
    recent_errors: Optional[List[str]]
    last_error: Optional[str]


class BatchControlResponse(BaseModel):
    """Response model for batch control operations."""
    batch_id: str
    status: str
    action: str
    success: bool
    message: Optional[str] = None


# Simple admin authentication via API key
def verify_admin_access(x_admin_key: Optional[str] = Header(None)) -> bool:
    """
    Verify admin access via API key.

    Args:
        x_admin_key: Admin API key from header

    Returns:
        True if authorized

    Raises:
        HTTPException: If unauthorized
    """
    admin_key = os.getenv("ADMIN_API_KEY", "admin-secret-key-change-me")

    if not x_admin_key or x_admin_key != admin_key:
        raise HTTPException(
            status_code=403,
            detail="Admin access required. Please provide valid X-Admin-Key header."
        )

    return True


@router.post("/force", response_model=ReindexResponse)
async def create_reindex_batch(
    request: ReindexRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    is_admin: bool = Depends(verify_admin_access)
) -> ReindexResponse:
    """
    Create and optionally execute a force reindex batch.

    This endpoint creates a new batch reindex operation that will process
    files according to the specified mode and scope.

    Args:
        request: Reindex configuration
        background_tasks: FastAPI background tasks
        session: Database session
        is_admin: Admin authorization check

    Returns:
        ReindexResponse with batch information

    Raises:
        HTTPException: On validation errors or if another batch is active
    """
    try:
        service = ReindexService(session)

        # Create the batch
        batch = service.create_batch(
            mode=request.mode,
            path_prefix=request.scope.path_prefix,
            text_only=request.scope.text_only,
            dry_run=request.dry_run
        )

        # Prepare response
        response = ReindexResponse(
            batch_id=batch.id,
            status=batch.status,
            counts={
                "candidates": batch.candidates_count,
                "jobs_created": batch.jobs_created
            }
        )

        if request.dry_run:
            response.message = f"Dry run complete. Would reindex {batch.candidates_count} files."
        else:
            response.message = f"Reindex batch created. Processing {batch.candidates_count} files."

        logger.info(f"Created reindex batch {batch.id} (dry_run={request.dry_run})")
        return response

    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create reindex batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create batch: {e}")


@router.get("/batches/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    session: Session = Depends(get_db),
    is_admin: bool = Depends(verify_admin_access)
) -> BatchStatusResponse:
    """
    Get detailed status of a reindex batch.

    Args:
        batch_id: Batch ID
        session: Database session
        is_admin: Admin authorization check

    Returns:
        BatchStatusResponse with detailed batch information

    Raises:
        HTTPException: If batch not found
    """
    try:
        service = ReindexService(session)
        status = service.get_batch_status(batch_id)

        if not status:
            raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")

        return BatchStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


@router.post("/batches/{batch_id}/pause", response_model=BatchControlResponse)
async def pause_batch(
    batch_id: str,
    session: Session = Depends(get_db),
    is_admin: bool = Depends(verify_admin_access)
) -> BatchControlResponse:
    """
    Pause a running reindex batch.

    Args:
        batch_id: Batch ID
        session: Database session
        is_admin: Admin authorization check

    Returns:
        BatchControlResponse with operation result

    Raises:
        HTTPException: If batch not found or cannot be paused
    """
    try:
        service = ReindexService(session)
        success = service.pause_batch(batch_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause batch {batch_id}. It may not exist or is not running."
            )

        return BatchControlResponse(
            batch_id=batch_id,
            status=BatchStatus.PAUSED,
            action="pause",
            success=True,
            message="Batch paused successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause: {e}")


@router.post("/batches/{batch_id}/resume", response_model=BatchControlResponse)
async def resume_batch(
    batch_id: str,
    session: Session = Depends(get_db),
    is_admin: bool = Depends(verify_admin_access)
) -> BatchControlResponse:
    """
    Resume a paused reindex batch.

    Args:
        batch_id: Batch ID
        session: Database session
        is_admin: Admin authorization check

    Returns:
        BatchControlResponse with operation result

    Raises:
        HTTPException: If batch not found or cannot be resumed
    """
    try:
        service = ReindexService(session)
        success = service.resume_batch(batch_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume batch {batch_id}. It may not exist or is not paused."
            )

        return BatchControlResponse(
            batch_id=batch_id,
            status=BatchStatus.RUNNING,
            action="resume",
            success=True,
            message="Batch resumed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume: {e}")


@router.post("/batches/{batch_id}/cancel", response_model=BatchControlResponse)
async def cancel_batch(
    batch_id: str,
    session: Session = Depends(get_db),
    is_admin: bool = Depends(verify_admin_access)
) -> BatchControlResponse:
    """
    Cancel a running or paused reindex batch.

    Args:
        batch_id: Batch ID
        session: Database session
        is_admin: Admin authorization check

    Returns:
        BatchControlResponse with operation result

    Raises:
        HTTPException: If batch not found or cannot be cancelled
    """
    try:
        service = ReindexService(session)
        success = service.cancel_batch(batch_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel batch {batch_id}. It may not exist or is already completed."
            )

        return BatchControlResponse(
            batch_id=batch_id,
            status=BatchStatus.COMPLETED,
            action="cancel",
            success=True,
            message="Batch cancelled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel: {e}")


@router.get("/batches", response_model=List[Dict[str, Any]])
async def list_batches(
    limit: int = 10,
    include_completed: bool = False,
    session: Session = Depends(get_db),
    is_admin: bool = Depends(verify_admin_access)
) -> List[Dict[str, Any]]:
    """
    List reindex batches.

    Args:
        limit: Maximum number of batches to return
        include_completed: Whether to include completed/failed batches
        session: Database session
        is_admin: Admin authorization check

    Returns:
        List of batch summaries
    """
    try:
        service = ReindexService(session)
        batches = service.list_batches(limit=limit, include_completed=include_completed)
        return batches

    except Exception as e:
        logger.error(f"Failed to list batches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list batches: {e}")


@router.get("/status", response_model=Dict[str, Any])
async def get_reindex_status(
    session: Session = Depends(get_db),
    is_admin: bool = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """
    Get overall reindex system status.

    Returns:
        System status including active batches and maintenance mode
    """
    try:
        from app.models.reindex import ReindexBatch, SystemFlag

        # Check for active batch
        active_batch = ReindexBatch.get_active_batch(session)

        # Check maintenance mode
        maintenance_mode = SystemFlag.is_maintenance_mode(session)

        return {
            "has_active_batch": active_batch is not None,
            "active_batch_id": active_batch.id if active_batch else None,
            "active_batch_status": active_batch.status if active_batch else None,
            "maintenance_mode": maintenance_mode
        }

    except Exception as e:
        logger.error(f"Failed to get reindex status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


@router.delete("/maintenance-mode")
async def clear_maintenance_mode(
    session: Session = Depends(get_db),
    is_admin: bool = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """
    Clear maintenance mode (emergency endpoint).

    This endpoint can be used to manually clear maintenance mode
    if a batch fails to clear it properly.

    Returns:
        Operation result
    """
    try:
        from app.models.reindex import SystemFlag

        SystemFlag.set_maintenance_mode(session, False)

        return {
            "success": True,
            "message": "Maintenance mode cleared"
        }

    except Exception as e:
        logger.error(f"Failed to clear maintenance mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear maintenance mode: {e}")