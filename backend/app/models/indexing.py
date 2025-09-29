"""
Database models for Phase 4A indexing functionality.

This module defines the database schema for the indexing and search
functionality, including file tracking, job queue, and control settings.
"""

import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Float, Index, ForeignKey
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
    mtime_epoch = Column(BigInteger, nullable=False, index=True)  # Modification time (nanoseconds)
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
    chunks = relationship("DocumentChunk", back_populates="file", cascade="all, delete-orphan")

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
        Generate deterministic document ID from file metadata WITHOUT path dependency.

        CRITICAL FIX: Removed path from doc_id generation to prevent duplicates on rename.
        The doc_id now persists through renames as long as file content doesn't change,
        solving the issue where renames created duplicate database entries.

        Args:
            path: File path (not used in ID generation, kept for API compatibility)
            size_bytes: File size in bytes
            mtime_epoch: Modification time

        Returns:
            Hex-encoded SHA-256 hash of file metadata (size + mtime only)
        """
        # Use ONLY size + mtime for deterministic ID that survives renames
        # This prevents duplicate entries when files are renamed
        content = f"{size_bytes}:{mtime_epoch}"
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
    batch_id = Column(String(36), nullable=True, index=True)  # Optional batch ID for reindex operations

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

    def __init__(self, file_id: int, job_type: str = "index_file", batch_id: Optional[str] = None, **kwargs):
        """
        Initialize IndexJob with computed values.

        Args:
            file_id: ID of the file to be indexed
            job_type: Type of indexing job
            batch_id: Optional batch ID for reindex operations
            **kwargs: Additional model fields
        """
        super().__init__(**kwargs)
        self.file_id = file_id
        self.job_type = job_type
        self.batch_id = batch_id
        self.created_at = int(datetime.utcnow().timestamp())

        # Generate job signature to prevent duplicates
        self.job_signature = self._generate_job_signature()

    def _generate_job_signature(self) -> str:
        """
        Generate unique job signature to prevent duplicates.

        Uses file_id, job_type, and optionally batch_id to ensure proper de-duplication.
        For reindex operations with batch_id, allows the same file to be reindexed
        in different batches while preventing duplicates within a batch.

        Returns:
            Hex-encoded hash of job parameters
        """
        if self.batch_id:
            # Include batch_id for reindex operations to allow per-batch uniqueness
            content = f"{self.file_id}:{self.job_type}:{self.batch_id}"
        else:
            # Standard signature for non-batch operations
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


class DocumentChunk(Base):
    """
    Represents a text chunk from a document for Phase 4B search functionality.

    This model stores text content that has been extracted and chunked from
    indexed files. Each chunk is a segment of text that can be embedded for
    semantic search and indexed for full-text search.
    """
    __tablename__ = "document_chunks"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to IndexedFile
    file_id = Column(Integer, ForeignKey("indexed_files.id", ondelete='CASCADE'), nullable=False, index=True)

    # Chunk ordering and position
    ordinal = Column(Integer, nullable=False, index=True)  # Chunk order within file (0-based)

    # Content
    text = Column(Text, nullable=False)  # The actual text content of the chunk

    # Byte position in original file
    start_byte = Column(Integer, nullable=False)  # Starting byte position
    end_byte = Column(Integer, nullable=False)    # Ending byte position

    # Metadata and processing
    word_count = Column(Integer, nullable=True)   # Number of words in chunk
    char_count = Column(Integer, nullable=True)   # Number of characters in chunk

    # Processing timestamps
    created_at = Column(Integer, nullable=False, index=True)
    updated_at = Column(Integer, nullable=False)

    # Embedding metadata (for Phase 4B)
    has_embedding = Column(Boolean, default=False, nullable=False, index=True)
    embedding_model = Column(String(128), nullable=True)  # Model used for embedding
    embedding_version = Column(String(16), nullable=True)  # Version of embedding logic

    # Relationships
    file = relationship("IndexedFile", back_populates="chunks")

    # Indexes for performance
    __table_args__ = (
        Index('idx_file_ordinal', 'file_id', 'ordinal'),  # For retrieving chunks in order
        Index('idx_file_position', 'file_id', 'start_byte', 'end_byte'),  # For position-based queries
        Index('idx_embedding_status', 'has_embedding', 'created_at'),  # For finding unembedded chunks
        {}, # Required empty dict at end for SQLAlchemy
    )

    def __init__(self, file_id: int, ordinal: int, text: str, start_byte: int, end_byte: int, **kwargs):
        """
        Initialize DocumentChunk with computed values.

        Args:
            file_id: ID of the parent indexed file
            ordinal: Order of chunk within the file (0-based)
            text: Text content of the chunk
            start_byte: Starting byte position in original file
            end_byte: Ending byte position in original file
            **kwargs: Additional model fields
        """
        super().__init__(**kwargs)
        self.file_id = file_id
        self.ordinal = ordinal
        self.text = text
        self.start_byte = start_byte
        self.end_byte = end_byte

        # Compute text statistics
        self.word_count = len(text.split()) if text else 0
        self.char_count = len(text) if text else 0

        # Set timestamps
        now = int(datetime.utcnow().timestamp())
        self.created_at = now
        self.updated_at = now

    def update_text(self, new_text: str) -> None:
        """
        Update chunk text content and recompute statistics.

        Args:
            new_text: New text content for the chunk
        """
        self.text = new_text
        self.word_count = len(new_text.split()) if new_text else 0
        self.char_count = len(new_text) if new_text else 0
        self.updated_at = int(datetime.utcnow().timestamp())

        # Reset embedding status since content changed
        self.has_embedding = False
        self.embedding_model = None
        self.embedding_version = None

    def mark_embedded(self, model_name: str, version: str) -> None:
        """
        Mark chunk as having been embedded.

        Args:
            model_name: Name of the embedding model used
            version: Version of the embedding logic/model
        """
        self.has_embedding = True
        self.embedding_model = model_name
        self.embedding_version = version
        self.updated_at = int(datetime.utcnow().timestamp())

    def needs_embedding(self, current_model: str, current_version: str) -> bool:
        """
        Check if chunk needs embedding or re-embedding.

        Args:
            current_model: Current embedding model being used
            current_version: Current embedding logic version

        Returns:
            True if embedding is needed
        """
        return (
            not self.has_embedding or
            self.embedding_model != current_model or
            self.embedding_version != current_version
        )

    def get_preview(self, max_chars: int = 100) -> str:
        """
        Get a preview of the chunk text.

        Args:
            max_chars: Maximum number of characters to return

        Returns:
            Truncated text with ellipsis if needed
        """
        if not self.text:
            return ""

        if len(self.text) <= max_chars:
            return self.text

        return self.text[:max_chars-3] + "..."

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, file_id={self.file_id}, ordinal={self.ordinal}, chars={self.char_count})>"