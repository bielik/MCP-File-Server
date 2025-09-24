"""
Phase 4B Database Schema Tests

Tests the creation and functionality of Phase 4B database schema extensions,
including document_chunks table and FTS5 virtual table with triggers.

Following TDD methodology as specified in Phase 4B plan.
"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session

import sys
# Add parent directory to path for app imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import Base, _create_fts_tables
from app.models.indexing import IndexedFile, IndexJob, DocumentChunk


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    try:
        # Create engine and session
        engine = create_engine(f'sqlite:///{db_path}', echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Create FTS tables
        _create_fts_tables(engine)

        session = SessionLocal()
        yield session
        session.close()

        # Properly dispose of engine before cleanup
        engine.dispose()

    finally:
        os.close(db_fd)
        try:
            os.unlink(db_path)
        except (PermissionError, FileNotFoundError):
            # On Windows, the database file may be locked briefly
            pass


class TestDocumentChunksSchema:
    """Test document_chunks table creation and structure."""

    def test_document_chunks_table_exists(self, test_db):
        """Test that document_chunks table is created correctly on startup."""
        inspector = inspect(test_db.bind)
        tables = inspector.get_table_names()

        assert "document_chunks" in tables, "document_chunks table should exist"

        # Check table structure
        columns = inspector.get_columns("document_chunks")
        column_names = [col['name'] for col in columns]

        expected_columns = ['id', 'file_id', 'ordinal', 'text', 'start_byte', 'end_byte']
        for col in expected_columns:
            assert col in column_names, f"Column '{col}' should exist in document_chunks"

    def test_document_chunks_foreign_key(self, test_db):
        """Test that document_chunks has proper foreign key to indexed_files."""
        inspector = inspect(test_db.bind)
        foreign_keys = inspector.get_foreign_keys("document_chunks")

        # Should have one foreign key to indexed_files
        assert len(foreign_keys) == 1, "Should have one foreign key"
        fk = foreign_keys[0]
        assert fk['referred_table'] == 'indexed_files', "Should reference indexed_files table"
        assert 'file_id' in fk['constrained_columns'], "Should reference through file_id"


class TestChunksFTSSchema:
    """Test chunks_fts virtual table creation and configuration."""

    def test_chunks_fts_virtual_table_exists(self, test_db):
        """Test that chunks_fts virtual table is created correctly."""
        # Check if FTS virtual table exists
        result = test_db.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='chunks_fts'
        """)).fetchone()

        assert result is not None, "chunks_fts virtual table should exist"

    def test_chunks_fts_configuration(self, test_db):
        """Test that chunks_fts is configured with trigram tokenizer."""
        # Check FTS configuration
        result = test_db.execute(text("""
            SELECT sql FROM sqlite_master
            WHERE name='chunks_fts' AND type='table'
        """)).fetchone()

        assert result is not None, "chunks_fts table should exist"
        sql_definition = result[0].lower()
        assert 'fts5' in sql_definition, "Should be FTS5 table"
        assert 'trigram' in sql_definition, "Should use trigram tokenizer"

    def test_fts_search_functionality(self, test_db):
        """Test that FTS search works with trigram tokenizer."""
        # Insert test data into chunks_fts
        test_db.execute(text("""
            INSERT INTO chunks_fts(rowid, text)
            VALUES (1, 'This is a test document with some content')
        """))

        # Test search functionality
        result = test_db.execute(text("""
            SELECT rowid FROM chunks_fts
            WHERE chunks_fts MATCH 'test*'
        """)).fetchone()

        assert result is not None, "FTS search should work"
        assert result[0] == 1, "Should find the test document"


class TestFTSSynchronizationTriggers:
    """Test INSERT/UPDATE/DELETE triggers for FTS synchronization."""

    def test_insert_trigger_exists(self, test_db):
        """Test that INSERT trigger exists for FTS synchronization."""
        result = test_db.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='trigger' AND name='chunks_fts_insert'
        """)).fetchall()

        assert len(result) > 0, "INSERT trigger should exist for chunks FTS sync"

    def test_update_trigger_exists(self, test_db):
        """Test that UPDATE trigger exists for FTS synchronization."""
        result = test_db.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='trigger' AND name='chunks_fts_update'
        """)).fetchall()

        assert len(result) > 0, "UPDATE trigger should exist for chunks FTS sync"

    def test_delete_trigger_exists(self, test_db):
        """Test that DELETE trigger exists for FTS synchronization."""
        result = test_db.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='trigger' AND name='chunks_fts_delete'
        """)).fetchall()

        assert len(result) > 0, "DELETE trigger should exist for chunks FTS sync"

    def test_fts_synchronization_on_insert(self, test_db):
        """Test that chunks_fts stays synchronized with document_chunks on INSERT."""
        # Create test indexed file first
        test_db.execute(text("""
            INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
            VALUES ('test123', 'test.txt', 'hash123', 100, 1234567890, 1234567890, 1, 1, 0, 0)
        """))

        file_result = test_db.execute(text("SELECT id FROM indexed_files WHERE doc_id = 'test123'")).fetchone()
        file_id = file_result[0]

        # Insert into document_chunks
        test_db.execute(text("""
            INSERT INTO document_chunks (file_id, ordinal, text, start_byte, end_byte, word_count, char_count, created_at, updated_at, has_embedding)
            VALUES (:file_id, 0, 'Test chunk content for searching', 0, 100, 5, 35, 1234567890, 1234567890, 0)
        """), {"file_id": file_id})

        chunk_result = test_db.execute(text("SELECT id FROM document_chunks WHERE file_id = :file_id"), {"file_id": file_id}).fetchone()
        chunk_id = chunk_result[0]

        # Check that FTS was updated automatically
        fts_result = test_db.execute(text("""
            SELECT rowid FROM chunks_fts WHERE rowid = :chunk_id
        """), {"chunk_id": chunk_id}).fetchone()

        assert fts_result is not None, "FTS table should be updated on INSERT"

    def test_fts_synchronization_on_update(self, test_db):
        """Test that chunks_fts stays synchronized with document_chunks on UPDATE."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
            VALUES ('test456', 'test2.txt', 'hash456', 200, 1234567891, 1234567891, 1, 1, 0, 0)
        """))

        file_result = test_db.execute(text("SELECT id FROM indexed_files WHERE doc_id = 'test456'")).fetchone()
        file_id = file_result[0]

        # Insert chunk
        test_db.execute(text("""
            INSERT INTO document_chunks (file_id, ordinal, text, start_byte, end_byte, word_count, char_count, created_at, updated_at, has_embedding)
            VALUES (:file_id, 0, 'Original chunk content', 0, 200, 3, 22, 1234567891, 1234567891, 0)
        """), {"file_id": file_id})

        chunk_result = test_db.execute(text("SELECT id FROM document_chunks WHERE file_id = :file_id"), {"file_id": file_id}).fetchone()
        chunk_id = chunk_result[0]

        # Update chunk content
        test_db.execute(text("""
            UPDATE document_chunks
            SET text = 'Updated chunk content for testing'
            WHERE id = :chunk_id
        """), {"chunk_id": chunk_id})

        # Verify FTS was updated
        fts_result = test_db.execute(text("""
            SELECT rowid FROM chunks_fts
            WHERE chunks_fts MATCH 'Updated' AND rowid = :chunk_id
        """), {"chunk_id": chunk_id}).fetchone()

        assert fts_result is not None, "FTS should be updated when chunk content changes"

    def test_fts_synchronization_on_delete(self, test_db):
        """Test that chunks_fts stays synchronized with document_chunks on DELETE."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO indexed_files (doc_id, path, file_hash, size_bytes, mtime_epoch, discovered_at, is_indexed, is_text, is_binary, has_ocr)
            VALUES ('test789', 'test3.txt', 'hash789', 300, 1234567892, 1234567892, 1, 1, 0, 0)
        """))

        file_result = test_db.execute(text("SELECT id FROM indexed_files WHERE doc_id = 'test789'")).fetchone()
        file_id = file_result[0]

        # Insert chunk
        test_db.execute(text("""
            INSERT INTO document_chunks (file_id, ordinal, text, start_byte, end_byte, word_count, char_count, created_at, updated_at, has_embedding)
            VALUES (:file_id, 0, 'Chunk to be deleted', 0, 300, 4, 19, 1234567892, 1234567892, 0)
        """), {"file_id": file_id})

        chunk_result = test_db.execute(text("SELECT id FROM document_chunks WHERE file_id = :file_id"), {"file_id": file_id}).fetchone()
        chunk_id = chunk_result[0]

        # Verify chunk exists in FTS
        fts_before = test_db.execute(text("SELECT rowid FROM chunks_fts WHERE rowid = :chunk_id"), {"chunk_id": chunk_id}).fetchone()
        assert fts_before is not None, "Chunk should exist in FTS before delete"

        # Delete chunk
        test_db.execute(text("DELETE FROM document_chunks WHERE id = :chunk_id"), {"chunk_id": chunk_id})

        # Verify FTS was cleaned up
        fts_after = test_db.execute(text("SELECT rowid FROM chunks_fts WHERE rowid = :chunk_id"), {"chunk_id": chunk_id}).fetchone()
        assert fts_after is None, "Chunk should be removed from FTS after delete"