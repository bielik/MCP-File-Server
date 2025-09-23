"""
Tests for Phase 4A database bootstrap functionality.

Tests SQLite WAL configuration, schema versioning, and concurrent access.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.bootstrap import DatabaseBootstrap, create_session_factory


class TestDatabaseBootstrap:
    """Test database bootstrap functionality."""

    def test_configure_sqlite_pragmas(self):
        """Test SQLite PRAGMA configuration."""
        # Create a test database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name

        try:
            # Create engine and test PRAGMA configuration
            engine = create_engine(f"sqlite:///{db_path}")

            # Mock the event listener
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value = mock_cursor

            # Call the configuration function
            DatabaseBootstrap.configure_sqlite_pragmas(mock_connection, None)

            # Verify PRAGMA commands were executed
            expected_calls = [
                "PRAGMA journal_mode=WAL",
                "PRAGMA synchronous=NORMAL",
                "PRAGMA busy_timeout=5000",
                "PRAGMA foreign_keys=ON",
                "PRAGMA cache_size=10000",
                "PRAGMA temp_store=MEMORY",
                "PRAGMA mmap_size=268435456"
            ]

            assert mock_cursor.execute.call_count == len(expected_calls)
            for call in expected_calls:
                mock_cursor.execute.assert_any_call(call)

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_create_engine_with_config(self):
        """Test engine creation with Phase 4A configuration."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            db_url = f"sqlite:///{db_path}"

        try:
            engine = DatabaseBootstrap.create_engine_with_config(db_url)

            # Test that engine was created
            assert engine is not None

            # Test connection works
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                assert result[0] == 1

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_initialize_schema_versioning(self):
        """Test schema versioning initialization."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            db_url = f"sqlite:///{db_path}"

        try:
            engine = create_engine(db_url)

            # Initialize schema versioning
            DatabaseBootstrap.initialize_schema_versioning(engine)

            # Verify schema_version table was created and populated
            with engine.connect() as conn:
                # Check table exists
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='schema_version'
                """)).fetchone()
                assert result is not None

                # Check version was inserted
                result = conn.execute(text("""
                    SELECT version FROM schema_version
                    ORDER BY applied_at DESC LIMIT 1
                """)).fetchone()
                assert result[0] == DatabaseBootstrap.SCHEMA_VERSION

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_validate_schema_version_success(self):
        """Test successful schema version validation."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            db_url = f"sqlite:///{db_path}"

        try:
            engine = create_engine(db_url)

            # Initialize schema versioning
            DatabaseBootstrap.initialize_schema_versioning(engine)

            # Validate should succeed
            result = DatabaseBootstrap.validate_schema_version(engine)
            assert result is True

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_validate_schema_version_mismatch(self):
        """Test schema version validation with version mismatch."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            db_url = f"sqlite:///{db_path}"

        try:
            engine = create_engine(db_url)

            # Create schema_version table with wrong version
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE schema_version (
                        version TEXT PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """))
                conn.execute(text("""
                    INSERT INTO schema_version (version, description)
                    VALUES ('999.0.0', 'Test version')
                """))
                conn.commit()

            # Validation should fail
            with pytest.raises(RuntimeError, match="Schema version mismatch"):
                DatabaseBootstrap.validate_schema_version(engine)

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_validate_schema_version_no_table(self):
        """Test schema version validation with no schema_version table."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            db_url = f"sqlite:///{db_path}"

        try:
            engine = create_engine(db_url)

            # Create empty database (no schema_version table)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1")).fetchone()

            # Validation should fail
            with pytest.raises(RuntimeError, match="No schema version found"):
                DatabaseBootstrap.validate_schema_version(engine)

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_create_database_if_not_exists(self):
        """Test database file creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "subdir", "test.db")

            # Database file should not exist
            assert not os.path.exists(db_path)

            # Create database
            DatabaseBootstrap.create_database_if_not_exists(db_path)

            # Database file and directory should now exist
            assert os.path.exists(db_path)
            assert os.path.exists(os.path.dirname(db_path))

    def test_get_database_info(self):
        """Test database information gathering."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            db_url = f"sqlite:///{db_path}"

        try:
            engine = DatabaseBootstrap.create_engine_with_config(db_url)
            DatabaseBootstrap.initialize_schema_versioning(engine)

            # Get database info
            info = DatabaseBootstrap.get_database_info(engine)

            # Verify expected fields
            assert 'pragmas' in info
            assert 'schema' in info
            assert 'size_bytes' in info
            assert 'wal_enabled' in info
            assert 'foreign_keys_enabled' in info

            # Verify schema information
            assert info['schema']['version'] == DatabaseBootstrap.SCHEMA_VERSION

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_bootstrap_database_complete(self):
        """Test complete database bootstrap process."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            db_url = f"sqlite:///{db_path}"

        try:
            # Mock table creation function
            def mock_create_tables(engine):
                with engine.connect() as conn:
                    conn.execute(text("""
                        CREATE TABLE test_table (
                            id INTEGER PRIMARY KEY,
                            name TEXT
                        )
                    """))
                    conn.commit()

            # Bootstrap database
            engine = DatabaseBootstrap.bootstrap_database(db_url, mock_create_tables)

            # Verify engine was created
            assert engine is not None

            # Verify tables were created
            with engine.connect() as conn:
                # Check schema_version table
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='schema_version'
                """)).fetchone()
                assert result is not None

                # Check test table
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='test_table'
                """)).fetchone()
                assert result is not None

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_bootstrap_database_failure(self):
        """Test database bootstrap failure handling."""
        # Use invalid database URL
        with pytest.raises(RuntimeError, match="Failed to bootstrap database"):
            DatabaseBootstrap.bootstrap_database("invalid://database/url")


class TestSessionFactory:
    """Test session factory creation."""

    def test_create_session_factory(self):
        """Test session factory creation with optimized configuration."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            db_url = f"sqlite:///{db_path}"

        try:
            engine = create_engine(db_url)
            session_factory = create_session_factory(engine)

            # Test session factory
            assert session_factory is not None
            assert isinstance(session_factory, sessionmaker)

            # Test session creation
            session = session_factory()
            assert session is not None

            # Test session works
            result = session.execute(text("SELECT 1")).fetchone()
            assert result[0] == 1

            session.close()

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__])