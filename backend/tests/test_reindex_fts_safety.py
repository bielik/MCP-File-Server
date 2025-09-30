"""
Test Suite for Step C: FTS Batch Safety

Tests verify that FTS operations respect batch boundaries and that
full reset properly truncates FTS data to prevent stale content reuse.

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
from app.models.reindex import ReindexBatch, ReindexMode, BatchStatus
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
def files_with_fts_data(test_db):
    """Create files with chunks and FTS data from a previous batch."""
    base_time = int(datetime.utcnow().timestamp() * 1e9)
    current_time = int(datetime.utcnow().timestamp())

    # Create 3 files with chunks
    files = []
    for i in range(3):
        file = IndexedFile(
            path=f"/source/old_file_{i}.txt",
            size_bytes=1024 + i,
            mtime_epoch=base_time + i * 1000000,
            is_text=True,
            is_indexed=True,
            index_version="1.0"
        )
        file.last_indexed_at = current_time
        test_db.add(file)
        test_db.commit()

        # Add 2 chunks per file
        for j in range(2):
            chunk = DocumentChunk(
                file_id=file.id,
                ordinal=j,
                text=f"Old batch content file {i} chunk {j}",
                start_byte=j * 100,
                end_byte=(j + 1) * 100
            )
            test_db.add(chunk)

        test_db.commit()
        files.append(file)

    return files


class TestStepC_FTSBatchSafety:
    """Test Step C: FTS respects batch boundaries and prevents stale data reuse."""

    def test_fts_truncate_on_full_reset(self, test_db, files_with_fts_data):
        """
        Test that full reset truncates FTS table completely.

        Given: Files with existing chunks and FTS data
        When: full_reset() is called
        Then: FTS table is empty (no stale content)
        """
        # Verify initial FTS content exists
        fts_count_before = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts")
        ).scalar()
        assert fts_count_before > 0, "Should have FTS data initially"

        # Perform full reset
        service = ReindexService(test_db)
        service.full_reset()

        # Verify FTS is empty
        fts_count_after = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts")
        ).scalar()
        assert fts_count_after == 0, \
            f"FTS table should be empty after reset, but has {fts_count_after} entries"

    def test_fts_search_returns_only_new_batch_content(self, test_db, files_with_fts_data):
        """
        Test that after reset and rebuild, FTS searches return only new batch content.

        Given: Old FTS data exists
        When: Reset, then create new chunks with new content
        Then: FTS searches return only new content (not old)
        """
        # Search for old content (should find it initially)
        old_search = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'Old'")
        ).scalar()
        assert old_search > 0, "Should find old content initially"

        # Full reset
        service = ReindexService(test_db)
        service.full_reset()

        # Create new content with different text
        test_db.refresh(files_with_fts_data[0])
        new_chunk = DocumentChunk(
            file_id=files_with_fts_data[0].id,
            ordinal=0,
            text="New batch content after reset",
            start_byte=0,
            end_byte=100
        )
        test_db.add(new_chunk)
        test_db.commit()

        # Search for old content (should find nothing)
        old_search_after = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'Old'")
        ).scalar()
        assert old_search_after == 0, \
            f"Should not find old content after reset, found {old_search_after}"

        # Search for new content (should find it)
        new_search = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'New'")
        ).scalar()
        assert new_search > 0, "Should find new content after reset"

    def test_hard_reset_clears_fts_before_creating_jobs(self, test_db, files_with_fts_data):
        """
        Test that hard reset clears FTS before creating new batch jobs.

        This ensures FTS jobs created in the new batch won't accidentally
        index stale chunks.
        """
        # Perform hard reset with rebuild
        service = ReindexService(test_db)

        # First do full reset to clear everything
        service.full_reset()

        # Verify FTS is empty
        fts_count = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts")
        ).scalar()
        assert fts_count == 0, "FTS should be empty after full reset"

        # Create a new batch (which would normally trigger reindex)
        batch = service.create_batch(
            mode=ReindexMode.HARD,
            path_prefix=None,
            text_only=True,
            dry_run=False
        )

        # Verify batch created jobs
        assert batch.jobs_created > 0

        # FTS should still be empty (no chunks created yet)
        fts_count_after = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts")
        ).scalar()
        assert fts_count_after == 0, \
            "FTS should remain empty until workers process jobs"

    def test_fts_triggers_maintain_consistency(self, test_db):
        """
        Test that FTS triggers properly sync chunk insertions and deletions.
        """
        base_time = int(datetime.utcnow().timestamp() * 1e9)

        # Create a file
        file = IndexedFile(
            path="/source/test.txt",
            size_bytes=1024,
            mtime_epoch=base_time,
            is_text=True
        )
        test_db.add(file)
        test_db.commit()

        # Add a chunk (trigger should insert into FTS)
        chunk = DocumentChunk(
            file_id=file.id,
            ordinal=0,
            text="Test content for FTS",
            start_byte=0,
            end_byte=100
        )
        test_db.add(chunk)
        test_db.commit()

        # Verify FTS has the content
        fts_count = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'Test'")
        ).scalar()
        assert fts_count == 1, "FTS should have the chunk after insert"

        # Delete the chunk (trigger should remove from FTS)
        test_db.delete(chunk)
        test_db.commit()

        # Verify FTS no longer has the content
        fts_count_after = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'Test'")
        ).scalar()
        assert fts_count_after == 0, "FTS should remove the chunk after delete"

    def test_full_reset_with_large_fts_dataset(self, test_db):
        """
        Test that full reset handles larger FTS datasets efficiently.
        """
        base_time = int(datetime.utcnow().timestamp() * 1e9)
        current_time = int(datetime.utcnow().timestamp())

        # Create 10 files with 10 chunks each (100 FTS entries)
        for i in range(10):
            file = IndexedFile(
                path=f"/source/large_file_{i}.txt",
                size_bytes=1024 + i,
                mtime_epoch=base_time + i * 1000000,
                is_text=True,
                is_indexed=True
            )
            file.last_indexed_at = current_time
            test_db.add(file)
            test_db.commit()

            for j in range(10):
                chunk = DocumentChunk(
                    file_id=file.id,
                    ordinal=j,
                    text=f"Large dataset content file {i} chunk {j}",
                    start_byte=j * 100,
                    end_byte=(j + 1) * 100
                )
                test_db.add(chunk)

            test_db.commit()

        # Verify we have 100 FTS entries
        fts_count_before = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts")
        ).scalar()
        assert fts_count_before == 100, f"Expected 100 FTS entries, got {fts_count_before}"

        # Perform full reset
        service = ReindexService(test_db)
        service.full_reset()

        # Verify all FTS entries cleared
        fts_count_after = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts")
        ).scalar()
        assert fts_count_after == 0, \
            f"FTS should be empty, but has {fts_count_after} entries"

    def test_fts_update_trigger_works_correctly(self, test_db):
        """
        Test that updating chunk text properly updates FTS index.
        """
        base_time = int(datetime.utcnow().timestamp() * 1e9)

        # Create file and chunk
        file = IndexedFile(
            path="/source/test.txt",
            size_bytes=1024,
            mtime_epoch=base_time,
            is_text=True
        )
        test_db.add(file)
        test_db.commit()

        chunk = DocumentChunk(
            file_id=file.id,
            ordinal=0,
            text="Original content",
            start_byte=0,
            end_byte=100
        )
        test_db.add(chunk)
        test_db.commit()

        # Verify original content searchable
        original_search = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'Original'")
        ).scalar()
        assert original_search == 1, "Should find original content"

        # Update the chunk text
        chunk.update_text("Updated content")
        test_db.commit()

        # Verify old content not searchable
        old_search = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'Original'")
        ).scalar()
        assert old_search == 0, "Should not find old content after update"

        # Verify new content searchable
        new_search = test_db.execute(
            text("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'Updated'")
        ).scalar()
        assert new_search == 1, "Should find updated content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])