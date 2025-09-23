"""
Database models for Phase 4A indexing functionality.

This module defines the database schema for the indexing and search
functionality, including file tracking, job queue, and control settings.
"""

import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, Index, ForeignKey
from sqlalchemy.orm import relationship
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


class JobStatus(str, Enum):
    """Status values for indexing jobs."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class IndexedFile(Base):
    """
    Represents a file that has been discovered and indexed.

    This model tracks file metadata and indexing state. It serves as the
    single source of truth for file discovery and change detection.
    """
    __tablename__ = "indexed_files"

    # Primary key and unique identifier
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String(64), unique=True, nullable=False, index=True)  # UUID or hash-based ID

    # File identification and location
    path = Column(Text, nullable=False, index=True)  # Relative path from mount point
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash for change detection

    # File metadata (stored as epoch timestamps for efficiency)
    size_bytes = Column(Integer, nullable=False)
    mtime_epoch = Column(Integer, nullable=False, index=True)  # Modification time
    discovered_at = Column(Integer, nullable=False, index=True)  # When first discovered
    last_indexed_at = Column(Integer, nullable=True)  # When last successfully indexed

    # Indexing status
    is_indexed = Column(Boolean, default=False, nullable=False, index=True)
    index_version = Column(String(16), nullable=True)  # Version of indexing logic used

    # File type and processing flags
    mime_type = Column(String(128), nullable=True)
    is_text = Column(Boolean, default=False, nullable=False)
    is_binary = Column(Boolean, default=False, nullable=False)
    has_ocr = Column(Boolean, default=False, nullable=False)  # Whether OCR was performed

    # Relationships
    jobs = relationship("IndexJob", back_populates="file", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('idx_path_hash', 'path', 'file_hash'),
        Index('idx_mtime_indexed', 'mtime_epoch', 'is_indexed'),
        Index('idx_discovery_status', 'discovered_at', 'is_indexed'),
        {}, # Required empty dict at end for SQLAlchemy
    )

    def __init__(self, path: str, size_bytes: int, mtime_epoch: int, **kwargs):
        """
        Initialize IndexedFile with computed values.

        Args:
            path: File path relative to mount point
            size_bytes: File size in bytes
            mtime_epoch: Modification time as epoch timestamp
            **kwargs: Additional model fields
        """
        super().__init__(**kwargs)
        self.path = path
        self.size_bytes = size_bytes
        self.mtime_epoch = mtime_epoch
        self.discovered_at = int(datetime.utcnow().timestamp())

        # Generate doc_id as UUID-like identifier that persists through renames
        self.doc_id = self._generate_doc_id(path, size_bytes, mtime_epoch)

        # Generate file hash (will be updated when file is read)
        self.file_hash = self._compute_file_hash()

    def _generate_doc_id(self, path: str, size_bytes: int, mtime_epoch: int) -> str:
        """
        Generate deterministic document ID from file metadata rather than just path.

        This ensures that renames preserve the doc_id while still being deterministic.
        Uses path + size + mtime to create a unique identifier that persists through renames
        as long as the file content doesn't change.

        Args:
            path: File path (for initial creation)
            size_bytes: File size in bytes
            mtime_epoch: Modification time

        Returns:
            Hex-encoded SHA-256 hash of file metadata
        """
        # Use initial path + metadata for deterministic ID that survives renames
        content = f"{path}:{size_bytes}:{mtime_epoch}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]

    def _compute_file_hash(self) -> str:
        """
        Compute content hash placeholder.

        This will be updated with actual file content hash during indexing.

        Returns:
            Placeholder hash based on metadata
        """
        content = f"{self.path}:{self.size_bytes}:{self.mtime_epoch}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def update_file_hash(self, content_hash: str) -> None:
        """
        Update file hash with actual content hash.

        Args:
            content_hash: SHA-256 hash of file content
        """
        self.file_hash = content_hash

    def needs_reindexing(self, current_mtime: int, current_size: int) -> bool:
        """
        Check if file needs reindexing based on metadata changes.

        Args:
            current_mtime: Current modification time (epoch)
            current_size: Current file size in bytes

        Returns:
            True if reindexing is needed
        """
        return (
            not self.is_indexed or
            self.mtime_epoch != current_mtime or
            self.size_bytes != current_size
        )

    def mark_indexed(self, index_version: str) -> None:
        """
        Mark file as successfully indexed.

        Args:
            index_version: Version of indexing logic used
        """
        self.is_indexed = True
        self.index_version = index_version
        self.last_indexed_at = int(datetime.utcnow().timestamp())

    def __repr__(self):
        return f"<IndexedFile(doc_id='{self.doc_id}', path='{self.path}', indexed={self.is_indexed})>"


class IndexJob(Base):
    """
    Represents a job in the indexing queue.

    This model implements a resilient job queue with atomic claims,
    retry logic, and crash recovery capabilities.
    """
    __tablename__ = "index_jobs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Job identification and signature
    job_signature = Column(String(128), unique=True, nullable=False, index=True)  # Prevents duplicates
    file_id = Column(Integer, ForeignKey("indexed_files.id"), nullable=False, index=True)

    # Job status and timing
    status = Column(String(16), default=JobStatus.PENDING, nullable=False, index=True)
    created_at = Column(Integer, nullable=False, index=True)
    claimed_at = Column(Integer, nullable=True)
    started_at = Column(Integer, nullable=True)
    completed_at = Column(Integer, nullable=True)

    # Retry and failure handling
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(Integer, nullable=True, index=True)

    # Processing metadata
    worker_id = Column(String(64), nullable=True)  # Which worker is processing
    processing_started_at = Column(Integer, nullable=True)
    estimated_duration = Column(Float, nullable=True)  # Seconds

    # Job content
    job_type = Column(String(32), default="index_file", nullable=False)
    job_data = Column(Text, nullable=True)  # JSON data for job parameters

    # Relationships
    file = relationship("IndexedFile", back_populates="jobs")

    # Indexes for performance
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_status_retry', 'status', 'next_retry_at'),
        Index('idx_worker_claimed', 'worker_id', 'claimed_at'),
        Index('idx_file_status', 'file_id', 'status'),
        {}, # Required empty dict at end for SQLAlchemy
    )

    def __init__(self, file_id: int, job_type: str = "index_file", **kwargs):
        """
        Initialize IndexJob with computed values.

        Args:
            file_id: ID of the file to be indexed
            job_type: Type of indexing job
            **kwargs: Additional model fields
        """
        super().__init__(**kwargs)
        self.file_id = file_id
        self.job_type = job_type
        self.created_at = int(datetime.utcnow().timestamp())

        # Generate job signature to prevent duplicates
        self.job_signature = self._generate_job_signature()

    def _generate_job_signature(self) -> str:
        """
        Generate unique job signature to prevent duplicates.

        Uses only file_id and job_type to ensure proper de-duplication
        of identical jobs created moments apart (race conditions between
        initial scan and file watcher).

        Returns:
            Hex-encoded hash of job parameters
        """
        content = f"{self.file_id}:{self.job_type}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def claim_job(self, worker_id: str) -> bool:
        """
        Atomically claim this job for processing.

        Args:
            worker_id: Identifier of the claiming worker

        Returns:
            True if successfully claimed, False if already claimed
        """
        if self.status != JobStatus.PENDING:
            return False

        now = int(datetime.utcnow().timestamp())
        self.status = JobStatus.PROCESSING
        self.worker_id = worker_id
        self.claimed_at = now
        self.started_at = now

        return True

    def mark_completed(self) -> None:
        """Mark job as completed successfully."""
        self.status = JobStatus.COMPLETED
        self.completed_at = int(datetime.utcnow().timestamp())

    def mark_failed(self, error_message: str) -> None:
        """
        Mark job as failed and schedule retry if applicable.

        Args:
            error_message: Description of the failure
        """
        self.retry_count += 1
        self.last_error = error_message

        if self.retry_count >= self.max_retries:
            self.status = JobStatus.DEAD_LETTER
        else:
            self.status = JobStatus.FAILED
            # Schedule retry with exponential backoff
            backoff_seconds = min(300, 30 * (2 ** self.retry_count))  # Cap at 5 minutes
            self.next_retry_at = int(datetime.utcnow().timestamp()) + backoff_seconds

    def reset_for_retry(self) -> None:
        """Reset job status for retry."""
        self.status = JobStatus.PENDING
        self.worker_id = None
        self.claimed_at = None
        self.started_at = None
        self.next_retry_at = None

    def is_stale(self, timeout_seconds: int = 3600) -> bool:
        """
        Check if job is stale (processing too long).

        Args:
            timeout_seconds: Maximum processing time before considering stale

        Returns:
            True if job is stale
        """
        if self.status != JobStatus.PROCESSING or not self.started_at:
            return False

        elapsed = int(datetime.utcnow().timestamp()) - self.started_at
        return elapsed > timeout_seconds

    def __repr__(self):
        return f"<IndexJob(id={self.id}, file_id={self.file_id}, status='{self.status}')>"


class ControlSetting(Base):
    """
    Key-value store for indexer control settings.

    This model provides a simple way to store and retrieve control
    settings that need to be shared between services.
    """
    __tablename__ = "control_settings"

    # Primary key
    key = Column(String(64), primary_key=True)

    # Setting value and metadata
    value = Column(Text, nullable=False)
    value_type = Column(String(16), default="string", nullable=False)  # string, boolean, integer, float
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_updated', 'updated_at'),
        {}, # Required empty dict at end for SQLAlchemy
    )

    def __init__(self, key: str, value: str, value_type: str = "string", description: Optional[str] = None):
        """
        Initialize ControlSetting.

        Args:
            key: Setting key
            value: Setting value (as string)
            value_type: Type of the value
            description: Optional description
        """
        super().__init__()
        self.key = key
        self.value = str(value)
        self.value_type = value_type
        self.description = description

        now = int(datetime.utcnow().timestamp())
        self.created_at = now
        self.updated_at = now

    def update_value(self, value: str) -> None:
        """
        Update setting value.

        Args:
            value: New value (as string)
        """
        self.value = str(value)
        self.updated_at = int(datetime.utcnow().timestamp())

    def get_typed_value(self):
        """
        Get value converted to appropriate type.

        Returns:
            Value converted to the specified type
        """
        if self.value_type == "boolean":
            return self.value.lower() in ("true", "1", "yes", "on")
        elif self.value_type == "integer":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        else:
            return self.value

    @classmethod
    def get_setting(cls, session, key: str, default=None):
        """
        Get a setting value with optional default.

        Args:
            session: Database session
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value or default
        """
        setting = session.query(cls).filter(cls.key == key).first()
        return setting.get_typed_value() if setting else default

    @classmethod
    def set_setting(cls, session, key: str, value, value_type: str = "string", description: Optional[str] = None):
        """
        Set a setting value.

        Args:
            session: Database session
            key: Setting key
            value: Setting value
            value_type: Type of the value
            description: Optional description
        """
        setting = session.query(cls).filter(cls.key == key).first()

        if setting:
            setting.update_value(value)
            if description:
                setting.description = description
        else:
            setting = cls(key=key, value=str(value), value_type=value_type, description=description)
            session.add(setting)

        session.commit()
        return setting

    def __repr__(self):
        return f"<ControlSetting(key='{self.key}', value='{self.value}', type='{self.value_type}')>"


# Initialize default control settings
DEFAULT_CONTROL_SETTINGS = {
    "indexer_paused": {
        "value": "false",
        "type": "boolean",
        "description": "Whether the indexer is paused"
    },
    "throttle_pct": {
        "value": "0",
        "type": "integer",
        "description": "CPU throttling percentage (0-100)"
    },
    "discovery_epoch": {
        "value": "0",
        "type": "integer",
        "description": "Current file discovery epoch for preventing duplicates"
    }
}