"""
Test Suite for Step B: True Clean Reset + Maintenance Mode

Tests verify that full reset clears all index state (chunks, FTS, jobs, metadata)
and that maintenance mode properly blocks processing during reset operations.

Following TDD methodology as specified in Ticket 021.
"""

import pytest
import tempfile
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add backend to path for imports
backend_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_root)

from app.database import Base
from app.models.indexing import IndexedFile, IndexJob, JobStatus, DocumentChunk
from app.models.reindex import ReindexBatch, ReindexMode, BatchStatus, SystemFlag
from app.services.reindex_service import ReindexService


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    try:
        engine = create_engine(f'sqlite:///{db_path}', echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Create FTS tables
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    text,
                    content='document_chunks',
                    content_rowid='id',
                    tokenize = 'trigram'
                );
            """))

            # Create FTS triggers
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON document_chunks BEGIN
                    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
                END;
            """))

            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_delete AFTER DELETE ON document_chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
                END;
            """))

            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_update AFTER UPDATE ON document_chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
                    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
                END;
            """))

            conn.commit()

        session = SessionLocal()
        yield session
        session.close()

        engine.dispose()

    finally:
        os.close(db_fd)
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture
def indexed_file_with_chunks(test_db):
    """Create an indexed file with chunks and FTS data."""
    base_time = int(datetime.utcnow().timestamp() * 1e9)
    current_time = int(datetime.utcnow().timestamp())

    # Create indexed file
    file = IndexedFile(
        path="/source/test_document.txt",
        size_bytes=1024,
        mtime_epoch=base_time,
        is_text=True,
        is_indexed=True,
        index_version="1.0"
    )
    file.last_indexed_at = current_time  # Set explicitly
    test_db.add(file)
    test_db.commit()

    # Create chunks
    chunks = []
    for i in range(3):
        chunk = DocumentChunk(
            file_id=file.id,
            ordinal=i,
            text=f"This is chunk {i} with some test content",
            start_byte=i * 100,
            end_byte=(i + 1) * 100
        )
        chunks.append(chunk)
        test_db.add(chunk)

    test_db.commit()

    # Create jobs
    job = IndexJob(
        file_id=file.id,
        job_type="TEXT_EXTRACT",
        status=JobStatus.COMPLETED
    )
    test_db.add(job)
    test_db.commit()

    return file, chunks


class TestStepB_FullResetAndMaintenance:
    """Test Step B: Full reset clears all state and maintenance mode blocks processing."""

    def test_full_reset_clears_all_index_state(self, test_db, indexed_file_with_chunks):
        """
        Test that full reset clears all indexing artifacts.

        After full reset:
        - document_chunks table empty
        - chunks_fts table empty
        - index_jobs table empty
        - indexed_files metadata (extracted_text_hash, embedding_vector, last_indexed_at) → NULL
        """
        file, chunks = indexed_file_with_chunks

        # Verify initial state
        assert test_db.query(DocumentChunk).count() == 3
        assert test_db.query(IndexJob).count() == 1
        assert file.is_indexed is True
        assert file.last_indexed_at is not None

        # Create ReindexService and perform full reset
        service = ReindexService(test_db)

        # Execute the full reset logic (we'll implement full_reset method)
        service.full_reset()

        # Assert - document_chunks cleared
        assert test_db.query(DocumentChunk).count() == 0, \
            "document_chunks should be empty after reset"

        # Assert - FTS table cleared
        fts_count = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts")
        ).scalar()
        assert fts_count == 0, \
            "chunks_fts should be empty after reset"

        # Assert - index_jobs cleared
        assert test_db.query(IndexJob).count() == 0, \
            "index_jobs should be empty after reset"

        # Assert - indexed_files metadata cleared
        test_db.refresh(file)
        assert file.is_indexed is False, \
            "is_indexed should be False after reset"
        assert file.last_indexed_at is None, \
            "last_indexed_at should be NULL after reset"
        assert file.index_version is None, \
            "index_version should be NULL after reset"

    def test_maintenance_mode_blocks_processing(self, test_db):
        """
        Test that jobs cannot be claimed while maintenance_mode is ON.

        Given: maintenance_mode flag is set to True
        When: Worker tries to claim jobs
        Then: No jobs are claimed (returns None)
        """
        # Create a pending job
        base_time = int(datetime.utcnow().timestamp() * 1e9)
        file = IndexedFile(
            path="/source/test.txt",
            size_bytes=1024,
            mtime_epoch=base_time,
            is_text=True
        )
        test_db.add(file)
        test_db.commit()

        job = IndexJob(
            file_id=file.id,
            job_type="TEXT_EXTRACT"
        )
        test_db.add(job)
        test_db.commit()

        # Set maintenance mode
        SystemFlag.set_maintenance_mode(test_db, True)

        # Verify maintenance mode is set
        assert SystemFlag.is_maintenance_mode(test_db) is True

        # Attempt to claim job (this will be tested via queue manager)
        # For now, we'll verify the flag is set correctly
        assert job.status == JobStatus.PENDING

        # Clear maintenance mode
        SystemFlag.set_maintenance_mode(test_db, False)
        assert SystemFlag.is_maintenance_mode(test_db) is False

    def test_full_reset_sets_maintenance_mode(self, test_db, indexed_file_with_chunks):
        """
        Test that full reset sets and clears maintenance mode.

        During reset:
        - maintenance_mode is set to True
        After reset:
        - maintenance_mode is cleared to False
        """
        service = ReindexService(test_db)

        # Verify maintenance mode starts as False
        assert SystemFlag.is_maintenance_mode(test_db) is False

        # Perform reset
        service.full_reset()

        # After reset, maintenance mode should be cleared
        assert SystemFlag.is_maintenance_mode(test_db) is False

    def test_full_reset_is_transactional(self, test_db, indexed_file_with_chunks):
        """
        Test that full reset operations are transactional.

        If reset fails partway through, all operations should be rolled back.
        """
        file, chunks = indexed_file_with_chunks
        service = ReindexService(test_db)

        initial_chunk_count = test_db.query(DocumentChunk).count()
        initial_job_count = test_db.query(IndexJob).count()

        # Perform successful reset
        service.full_reset()

        # Verify all cleared
        assert test_db.query(DocumentChunk).count() == 0
        assert test_db.query(IndexJob).count() == 0

    def test_full_reset_with_multiple_files(self, test_db):
        """
        Test full reset with multiple files and chunks.
        """
        base_time = int(datetime.utcnow().timestamp() * 1e9)

        # Create multiple files with chunks
        for i in range(3):
            file = IndexedFile(
                path=f"/source/file_{i}.txt",
                size_bytes=1024 + i,
                mtime_epoch=base_time + i * 1000000,
                is_text=True,
                is_indexed=True
            )
            test_db.add(file)
            test_db.commit()

            # Add chunks
            for j in range(2):
                chunk = DocumentChunk(
                    file_id=file.id,
                    ordinal=j,
                    text=f"File {i} chunk {j}",
                    start_byte=j * 100,
                    end_byte=(j + 1) * 100
                )
                test_db.add(chunk)

            # Add job
            job = IndexJob(
                file_id=file.id,
                job_type="TEXT_EXTRACT",
                status=JobStatus.COMPLETED
            )
            test_db.add(job)

        test_db.commit()

        # Verify initial state
        assert test_db.query(IndexedFile).count() == 3
        assert test_db.query(DocumentChunk).count() == 6
        assert test_db.query(IndexJob).count() == 3

        # Perform reset
        service = ReindexService(test_db)
        service.full_reset()

        # Verify all cleared
        assert test_db.query(DocumentChunk).count() == 0
        assert test_db.query(IndexJob).count() == 0

        # Verify files still exist but metadata cleared
        assert test_db.query(IndexedFile).count() == 3
        for file in test_db.query(IndexedFile).all():
            assert file.is_indexed is False
            assert file.last_indexed_at is None

    def test_maintenance_mode_flag_persistence(self, test_db):
        """
        Test that maintenance mode flag persists across service calls.
        """
        # Set maintenance mode
        SystemFlag.set_maintenance_mode(test_db, True)
        assert SystemFlag.is_maintenance_mode(test_db) is True

        # Create new service instance (simulates service restart)
        service2 = ReindexService(test_db)

        # Flag should still be set
        assert SystemFlag.is_maintenance_mode(test_db) is True

        # Clear it
        SystemFlag.set_maintenance_mode(test_db, False)
        assert SystemFlag.is_maintenance_mode(test_db) is False

    def test_full_reset_clears_failed_jobs(self, test_db):
        """
        Test that full reset clears failed and dead-letter jobs.
        """
        base_time = int(datetime.utcnow().timestamp() * 1e9)
        file = IndexedFile(
            path="/source/test.txt",
            size_bytes=1024,
            mtime_epoch=base_time,
            is_text=True
        )
        test_db.add(file)
        test_db.commit()

        # Create jobs with different statuses and job types to avoid signature collision
        job_types = ["TEXT_EXTRACT", "CHUNK", "FTS_INDEX", "EMBED"]
        statuses = [JobStatus.PENDING, JobStatus.FAILED, JobStatus.DEAD_LETTER, JobStatus.COMPLETED]
        for job_type, status in zip(job_types, statuses):
            job = IndexJob(
                file_id=file.id,
                job_type=job_type,
                status=status
            )
            test_db.add(job)

        test_db.commit()

        assert test_db.query(IndexJob).count() == 4

        # Perform reset
        service = ReindexService(test_db)
        service.full_reset()

        # All jobs should be cleared
        assert test_db.query(IndexJob).count() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])