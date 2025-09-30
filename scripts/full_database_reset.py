#!/usr/bin/env python
"""
Completely reset the database to a truly clean state.
Removes ALL indexing data while preserving workspaces.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Create session
engine = create_engine("sqlite:///./data/database.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def full_reset(dry_run=True):
    """
    Completely reset all indexing data.

    Args:
        dry_run: If True, only show what would be done
    """
    session = SessionLocal()

    try:
        logger.info("Starting full database reset...")

        # Tables to clear completely
        tables_to_clear = [
            'document_chunks',
            'index_jobs',
            'reindex_batches',
            'system_flags'
        ]

        # Count records before deletion
        logger.info("\nRecords to be deleted:")
        for table in tables_to_clear:
            try:
                count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                logger.info(f"  {table}: {count} records")
            except Exception as e:
                logger.debug(f"  {table}: table might not exist ({e})")

        # Also reset indexed_files
        indexed_count = session.execute(
            text("SELECT COUNT(*) FROM indexed_files WHERE is_indexed = 1")
        ).scalar()
        logger.info(f"  indexed_files to reset: {indexed_count}")

        if not dry_run:
            # Delete all records from tables
            for table in tables_to_clear:
                try:
                    session.execute(text(f"DELETE FROM {table}"))
                    logger.info(f"Cleared {table}")
                except Exception as e:
                    logger.debug(f"Could not clear {table}: {e}")

            # Reset indexed_files but keep the file records
            session.execute(text("""
                UPDATE indexed_files
                SET is_indexed = 0,
                    last_indexed_at = NULL,
                    index_version = NULL,
                    extracted_text_hash = NULL
            """))
            logger.info("Reset all indexed_files flags")

            # Clear FTS index if exists
            try:
                session.execute(text("DELETE FROM chunks_fts"))
                logger.info("Cleared FTS index")
            except:
                logger.debug("FTS index not found or already empty")

            session.commit()
            logger.info("\nFull reset completed successfully!")

            # Verify final state
            logger.info("\nFinal state:")
            for table in tables_to_clear:
                try:
                    count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    logger.info(f"  {table}: {count} records (should be 0)")
                except:
                    pass

            indexed_count = session.execute(
                text("SELECT COUNT(*) FROM indexed_files WHERE is_indexed = 1")
            ).scalar()
            logger.info(f"  Files marked indexed: {indexed_count} (should be 0)")

        else:
            logger.info("\nDRY RUN - No changes made")
            logger.info("Run with --execute to apply reset")

    except Exception as e:
        logger.error(f"Error during reset: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description='Completely reset indexing data')
    parser.add_argument('--execute', action='store_true', default=False,
                        help='Actually execute the reset (default is dry run)')

    args = parser.parse_args()

    if args.execute:
        response = input("\nWARNING: This will DELETE all indexing data!\n"
                        "Workspaces and permissions will be preserved.\n"
                        "Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return

    full_reset(dry_run=not args.execute)


if __name__ == "__main__":
    main()