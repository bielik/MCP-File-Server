"""
Database models for Force Reindex functionality.

This module defines the database schema for batch reindexing operations
and system-wide flags for maintenance control.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index, func
from sqlalchemy.orm import Session

try:
    from app.database import Base
except ImportError:
    # Handle import from external context (like indexer)
    try:
        from ..database import Base
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from database import Base


class BatchStatus(str, Enum):
    """Status values for reindex batches."""
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReindexMode(str, Enum):
    """Reindex operation modes."""
    SOFT = "soft"  # Clear indexed flags, keep chunks
    HARD = "hard"  # Purge chunks and rebuild from scratch


class ReindexBatch(Base):
    """
    Represents a force reindex batch operation.

    This model tracks batch reindexing operations including their configuration,
    status, and progress metrics.
    """
    __tablename__ = "reindex_batches"

    # Primary key - UUID for unique identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Batch configuration
    mode = Column(String(4), nullable=False)  # soft or hard
    path_prefix = Column(Text, nullable=True)  # Optional path filter
    text_only = Column(Boolean, default=True, nullable=False)  # Filter for text files only

    # Status tracking
    status = Column(String(10), default=BatchStatus.PLANNING, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Progress counters
    candidates_count = Column(Integer, default=0, nullable=False)  # Files identified for reindexing
    jobs_created = Column(Integer, default=0, nullable=False)  # Jobs queued
    files_processed = Column(Integer, default=0, nullable=False)  # Files successfully processed
    files_failed = Column(Integer, default=0, nullable=False)  # Files that failed processing

    # Error tracking
    last_error = Column(Text, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index('idx_batch_status_created', 'status', 'created_at'),
        Index('idx_batch_active', 'status', 'started_at'),
    )

    def __init__(self, mode: str, path_prefix: Optional[str] = None,
                 text_only: bool = True, **kwargs):
        """
        Initialize ReindexBatch.

        Args:
            mode: Reindex mode (soft or hard)
            path_prefix: Optional path filter
            text_only: Whether to only process text files
            **kwargs: Additional model fields
        """
        super().__init__(**kwargs)
        self.id = str(uuid.uuid4())
        self.mode = mode
        self.path_prefix = path_prefix
        self.text_only = text_only
        self.status = BatchStatus.PLANNING
        self.created_at = datetime.utcnow()

    def start(self) -> None:
        """Mark batch as started."""
        self.status = BatchStatus.RUNNING
        self.started_at = datetime.utcnow()

    def pause(self) -> None:
        """Mark batch as paused."""
        if self.status == BatchStatus.RUNNING:
            self.status = BatchStatus.PAUSED

    def resume(self) -> None:
        """Resume a paused batch."""
        if self.status == BatchStatus.PAUSED:
            self.status = BatchStatus.RUNNING

    def cancel(self) -> None:
        """Mark batch as cancelling."""
        if self.status in [BatchStatus.RUNNING, BatchStatus.PAUSED]:
            self.status = BatchStatus.CANCELLING

    def complete(self) -> None:
        """Mark batch as completed."""
        self.status = BatchStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def fail(self, error_message: str) -> None:
        """
        Mark batch as failed.

        Args:
            error_message: Description of the failure
        """
        self.status = BatchStatus.FAILED
        self.last_error = error_message
        self.completed_at = datetime.utcnow()

    def update_progress(self, files_processed: int = 0, files_failed: int = 0) -> None:
        """
        Update batch progress counters.

        Args:
            files_processed: Number of successfully processed files to add
            files_failed: Number of failed files to add
        """
        self.files_processed += files_processed
        self.files_failed += files_failed

    def get_progress_percentage(self) -> float:
        """
        Calculate progress percentage.

        Returns:
            Percentage of files processed (0-100)
        """
        if self.candidates_count == 0:
            return 100.0 if self.status == BatchStatus.COMPLETED else 0.0

        total_processed = self.files_processed + self.files_failed
        return min(100.0, (total_processed / self.candidates_count) * 100)

    def get_eta_seconds(self, processing_rate: float) -> Optional[int]:
        """
        Calculate estimated time to completion.

        Args:
            processing_rate: Files processed per second

        Returns:
            Estimated seconds to completion, or None if cannot calculate
        """
        if processing_rate <= 0 or self.candidates_count == 0:
            return None

        remaining = self.candidates_count - (self.files_processed + self.files_failed)
        if remaining <= 0:
            return 0

        return int(remaining / processing_rate)

    def to_dict(self) -> dict:
        """
        Convert batch to dictionary representation.

        Returns:
            Dictionary with batch information
        """
        return {
            'id': self.id,
            'mode': self.mode,
            'path_prefix': self.path_prefix,
            'text_only': self.text_only,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'candidates_count': self.candidates_count,
            'jobs_created': self.jobs_created,
            'files_processed': self.files_processed,
            'files_failed': self.files_failed,
            'progress_percentage': self.get_progress_percentage(),
            'last_error': self.last_error
        }

    @classmethod
    def get_active_batch(cls, session: Session) -> Optional['ReindexBatch']:
        """
        Get the currently active batch if any.

        Args:
            session: Database session

        Returns:
            Active batch or None
        """
        return session.query(cls).filter(
            cls.status.in_([BatchStatus.RUNNING, BatchStatus.PAUSED])
        ).first()

    @classmethod
    def has_active_batch(cls, session: Session) -> bool:
        """
        Check if there's an active batch.

        Args:
            session: Database session

        Returns:
            True if there's an active batch
        """
        return cls.get_active_batch(session) is not None

    def __repr__(self):
        return f"<ReindexBatch(id='{self.id}', mode='{self.mode}', status='{self.status}')>"


class SystemFlag(Base):
    """
    Key-value store for system-wide flags.

    This model provides a simple way to store system-wide flags
    like maintenance mode that affect service behavior.
    """
    __tablename__ = "system_flags"

    # Primary key
    key = Column(String(64), primary_key=True)

    # Flag value and metadata
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Timestamps
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, key: str, value: str, description: Optional[str] = None):
        """
        Initialize SystemFlag.

        Args:
            key: Flag key
            value: Flag value (as string)
            description: Optional description
        """
        super().__init__()
        self.key = key
        self.value = value
        self.description = description
        self.updated_at = datetime.utcnow()

    def update_value(self, value: str) -> None:
        """
        Update flag value.

        Args:
            value: New value (as string)
        """
        self.value = value
        self.updated_at = datetime.utcnow()

    def get_bool_value(self) -> bool:
        """
        Get value as boolean.

        Returns:
            Boolean interpretation of value
        """
        return self.value.lower() in ("true", "1", "yes", "on")

    @classmethod
    def get_flag(cls, session: Session, key: str, default: str = "false") -> str:
        """
        Get a flag value with optional default.

        Args:
            session: Database session
            key: Flag key
            default: Default value if not found

        Returns:
            Flag value or default
        """
        flag = session.query(cls).filter(cls.key == key).first()
        return flag.value if flag else default

    @classmethod
    def get_bool_flag(cls, session: Session, key: str, default: bool = False) -> bool:
        """
        Get a flag value as boolean.

        Args:
            session: Database session
            key: Flag key
            default: Default boolean value if not found

        Returns:
            Boolean flag value
        """
        value = cls.get_flag(session, key, str(default).lower())
        return value.lower() in ("true", "1", "yes", "on")

    @classmethod
    def set_flag(cls, session: Session, key: str, value: str,
                 description: Optional[str] = None) -> 'SystemFlag':
        """
        Set a flag value.

        Args:
            session: Database session
            key: Flag key
            value: Flag value
            description: Optional description

        Returns:
            SystemFlag instance
        """
        flag = session.query(cls).filter(cls.key == key).first()

        if flag:
            flag.update_value(value)
            if description:
                flag.description = description
        else:
            flag = cls(key=key, value=value, description=description)
            session.add(flag)

        session.commit()
        return flag

    @classmethod
    def set_maintenance_mode(cls, session: Session, enabled: bool) -> None:
        """
        Set maintenance mode flag.

        Args:
            session: Database session
            enabled: Whether maintenance mode should be enabled
        """
        cls.set_flag(
            session,
            "maintenance_mode",
            str(enabled).lower(),
            "System maintenance mode - pauses indexer operations"
        )

    @classmethod
    def is_maintenance_mode(cls, session: Session) -> bool:
        """
        Check if system is in maintenance mode.

        Args:
            session: Database session

        Returns:
            True if maintenance mode is enabled
        """
        return cls.get_bool_flag(session, "maintenance_mode", False)

    def __repr__(self):
        return f"<SystemFlag(key='{self.key}', value='{self.value}')>"