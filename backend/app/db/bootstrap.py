"""
Database Bootstrap Module for MCP KnowledgeExplorer Phase 4A

This module provides database initialization and configuration for SQLite
with WAL mode and concurrent access support.
"""

import logging
import sqlite3
from typing import Optional
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class DatabaseBootstrap:
    """
    Handles database initialization and configuration for Phase 4A.

    This class is responsible for:
    - Configuring SQLite for concurrent access (WAL mode)
    - Setting up performance optimizations
    - Implementing schema versioning
    - Creating shared functions for both backend and indexer services
    """

    # Current schema version for Phase 4A
    SCHEMA_VERSION = "4.0.0"

    @staticmethod
    def configure_sqlite_pragmas(dbapi_connection, connection_record):
        """
        Configure SQLite PRAGMAs for optimal concurrent performance.

        This function is called automatically when SQLite connections are created.
        It applies the following optimizations:
        - WAL mode for better read/write concurrency
        - NORMAL synchronous mode for performance
        - Foreign key constraints enabled
        - Busy timeout to handle concurrent access
        """
        cursor = dbapi_connection.cursor()

        try:
            # Enable WAL (Write-Ahead Logging) mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")

            # Set synchronous mode to NORMAL for performance
            # This is safe with WAL mode
            cursor.execute("PRAGMA synchronous=NORMAL")

            # Set busy timeout to handle concurrent access
            cursor.execute("PRAGMA busy_timeout=5000")

            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")

            # Optimize for performance
            cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O

            logger.info("SQLite PRAGMAs configured for concurrent access")

        except Exception as e:
            logger.error(f"Failed to configure SQLite PRAGMAs: {e}")
            raise
        finally:
            cursor.close()

    @staticmethod
    def create_engine_with_config(database_url: str, **kwargs) -> Engine:
        """
        Create SQLAlchemy engine with optimized SQLite configuration.

        Args:
            database_url: SQLite database URL
            **kwargs: Additional engine configuration

        Returns:
            Configured SQLAlchemy engine
        """
        # Default engine configuration for SQLite
        default_config = {
            "connect_args": {
                "check_same_thread": False,
                "timeout": 20  # Connection timeout
            },
            "pool_pre_ping": True,
            "echo": False  # Set to True for SQL debugging
        }

        # Merge with provided kwargs
        config = {**default_config, **kwargs}

        # Create engine
        engine = create_engine(database_url, **config)

        # Register PRAGMA configuration
        event.listen(engine, "connect", DatabaseBootstrap.configure_sqlite_pragmas)

        return engine

    @staticmethod
    def initialize_schema_versioning(engine: Engine) -> None:
        """
        Initialize schema versioning system.

        Creates a schema_version table if it doesn't exist and sets the current version.

        Args:
            engine: SQLAlchemy engine
        """
        with engine.connect() as conn:
            # Create schema_version table if it doesn't exist
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """))

            # Check current version
            result = conn.execute(text(
                "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
            )).fetchone()

            current_version = result[0] if result else None

            if current_version != DatabaseBootstrap.SCHEMA_VERSION:
                # Insert new version
                conn.execute(text("""
                    INSERT OR REPLACE INTO schema_version (version, description)
                    VALUES (:version, :description)
                """), {"version": DatabaseBootstrap.SCHEMA_VERSION, "description": "Phase 4A: Advanced Search & Retrieval"})

                conn.commit()
                logger.info(f"Schema version updated to {DatabaseBootstrap.SCHEMA_VERSION}")
            else:
                logger.info(f"Schema version {DatabaseBootstrap.SCHEMA_VERSION} is current")

    @staticmethod
    def validate_schema_version(engine: Engine) -> bool:
        """
        Validate that the database schema version matches the application version.

        Args:
            engine: SQLAlchemy engine

        Returns:
            True if schema version matches, False otherwise

        Raises:
            RuntimeError: If schema version is incompatible
        """
        try:
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
                )).fetchone()

                if not result:
                    raise RuntimeError(
                        "No schema version found. Database may not be initialized."
                    )

                current_version = result[0]

                if current_version != DatabaseBootstrap.SCHEMA_VERSION:
                    raise RuntimeError(
                        f"Schema version mismatch. Expected {DatabaseBootstrap.SCHEMA_VERSION}, "
                        f"found {current_version}. Please run database migration."
                    )

                logger.info(f"Schema version validation passed: {current_version}")
                return True

        except Exception as e:
            logger.error(f"Schema version validation failed: {e}")
            raise

    @staticmethod
    def create_database_if_not_exists(database_path: str) -> None:
        """
        Create database file and directory if they don't exist.

        Args:
            database_path: Path to the database file
        """
        db_path = Path(database_path)

        # Create directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create empty database file if it doesn't exist
        if not db_path.exists():
            # Touch the file to create it
            db_path.touch()
            logger.info(f"Created database file: {database_path}")

    @staticmethod
    def get_database_info(engine: Engine) -> dict:
        """
        Get database configuration and status information.

        Args:
            engine: SQLAlchemy engine

        Returns:
            Dictionary with database information
        """
        try:
            with engine.connect() as conn:
                # Get SQLite configuration
                pragmas = {}
                for pragma in ["journal_mode", "synchronous", "foreign_keys",
                              "cache_size", "busy_timeout"]:
                    result = conn.execute(text(f"PRAGMA {pragma}")).fetchone()
                    pragmas[pragma] = result[0] if result else None

                # Get schema version
                result = conn.execute(text(
                    "SELECT version, applied_at FROM schema_version ORDER BY applied_at DESC LIMIT 1"
                )).fetchone()

                schema_info = {
                    "version": result[0] if result else None,
                    "applied_at": result[1] if result else None
                } if result else None

                # Get database size
                result = conn.execute(text("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")).fetchone()
                db_size = result[0] if result else 0

                return {
                    "pragmas": pragmas,
                    "schema": schema_info,
                    "size_bytes": db_size,
                    "wal_enabled": pragmas.get("journal_mode") == "wal",
                    "foreign_keys_enabled": pragmas.get("foreign_keys") == 1
                }

        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}

    @staticmethod
    def bootstrap_database(database_url: str, create_tables_func=None) -> Engine:
        """
        Complete database bootstrap process.

        This is the main function that should be called by both backend and indexer
        services on startup.

        Args:
            database_url: SQLite database URL
            create_tables_func: Optional function to create application tables

        Returns:
            Configured SQLAlchemy engine

        Raises:
            RuntimeError: If bootstrap fails
        """
        try:
            # Extract database path from URL
            if database_url.startswith("sqlite:///"):
                db_path = database_url[10:]  # Remove sqlite:/// prefix
                DatabaseBootstrap.create_database_if_not_exists(db_path)

            # Create engine with optimized configuration
            engine = DatabaseBootstrap.create_engine_with_config(database_url)

            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1")).fetchone()

            # Initialize schema versioning
            DatabaseBootstrap.initialize_schema_versioning(engine)

            # Create application tables if function provided
            if create_tables_func:
                create_tables_func(engine)

            # Validate schema version
            DatabaseBootstrap.validate_schema_version(engine)

            # Log database info
            db_info = DatabaseBootstrap.get_database_info(engine)
            logger.info(f"Database bootstrap complete: {db_info}")

            return engine

        except Exception as e:
            logger.error(f"Database bootstrap failed: {e}")
            raise RuntimeError(f"Failed to bootstrap database: {e}")


def create_session_factory(engine: Engine) -> sessionmaker:
    """
    Create session factory with optimized configuration.

    Args:
        engine: SQLAlchemy engine

    Returns:
        Configured session factory
    """
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False  # Keep objects usable after commit
    )