"""
Phase 4B FTS5 Table and Trigger Creation Script

This script creates the FTS5 virtual table for document chunks and sets up
triggers to keep it synchronized with the document_chunks table.

Usage:
    python -m app.scripts.create_fts_tables
"""

import logging
import sys
import os
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add backend to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db, initialize_database

logger = logging.getLogger(__name__)


def create_fts_table(session: Session) -> None:
    """
    Create the FTS5 virtual table for document chunks.

    Args:
        session: Database session
    """
    logger.info("Creating chunks_fts virtual table")

    # Create FTS5 virtual table with trigram tokenizer
    create_fts_sql = """
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
        text,
        content='document_chunks',
        content_rowid='id',
        tokenize = 'trigram'
    );
    """

    session.execute(text(create_fts_sql))
    logger.info("Created chunks_fts virtual table")


def create_fts_triggers(session: Session) -> None:
    """
    Create triggers to keep FTS5 table synchronized with document_chunks.

    Args:
        session: Database session
    """
    logger.info("Creating FTS synchronization triggers")

    # INSERT trigger
    insert_trigger_sql = """
    CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON document_chunks BEGIN
        INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
    END;
    """

    # UPDATE trigger
    update_trigger_sql = """
    CREATE TRIGGER IF NOT EXISTS chunks_fts_update AFTER UPDATE ON document_chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
        INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
    END;
    """

    # DELETE trigger
    delete_trigger_sql = """
    CREATE TRIGGER IF NOT EXISTS chunks_fts_delete AFTER DELETE ON document_chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
    END;
    """

    session.execute(text(insert_trigger_sql))
    session.execute(text(update_trigger_sql))
    session.execute(text(delete_trigger_sql))

    logger.info("Created FTS synchronization triggers")


def rebuild_fts_index(session: Session) -> None:
    """
    Rebuild the FTS index from existing document_chunks data.

    Args:
        session: Database session
    """
    logger.info("Rebuilding FTS index from existing data")

    # Use FTS5 rebuild command
    rebuild_sql = "INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild');"
    session.execute(text(rebuild_sql))

    logger.info("Rebuilt FTS index")


def verify_fts_setup(session: Session) -> bool:
    """
    Verify that FTS5 table and triggers were created correctly.

    Args:
        session: Database session

    Returns:
        True if setup is correct
    """
    logger.info("Verifying FTS setup")

    # Check if FTS table exists
    fts_table_check = """
    SELECT name FROM sqlite_master
    WHERE type='table' AND name='chunks_fts'
    """

    result = session.execute(text(fts_table_check)).fetchone()
    if not result:
        logger.error("chunks_fts table not found")
        return False

    # Check if triggers exist
    trigger_names = [
        'chunks_fts_insert',
        'chunks_fts_update',
        'chunks_fts_delete'
    ]

    for trigger_name in trigger_names:
        trigger_check = """
        SELECT name FROM sqlite_master
        WHERE type='trigger' AND name=:trigger_name
        """
        result = session.execute(text(trigger_check), {"trigger_name": trigger_name}).fetchone()
        if not result:
            logger.error(f"Trigger {trigger_name} not found")
            return False

    # Test FTS functionality with a simple query
    try:
        test_sql = "SELECT count(*) FROM chunks_fts WHERE chunks_fts MATCH 'test'"
        session.execute(text(test_sql)).fetchone()
        logger.info("FTS functionality test passed")
    except Exception as e:
        logger.error(f"FTS functionality test failed: {e}")
        return False

    logger.info("FTS setup verification passed")
    return True


def main():
    """Main function to create FTS tables and triggers."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting FTS5 table creation script")

    try:
        # Initialize database (creates tables)
        initialize_database()

        # Get database session
        session = next(get_db())

        try:
            # Create FTS table
            create_fts_table(session)

            # Create triggers
            create_fts_triggers(session)

            # Commit changes
            session.commit()

            # Verify setup
            if verify_fts_setup(session):
                logger.info("FTS5 setup completed successfully")
            else:
                logger.error("FTS5 setup verification failed")
                return 1

        except Exception as e:
            session.rollback()
            logger.error(f"FTS5 setup failed: {e}")
            raise
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Script failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())