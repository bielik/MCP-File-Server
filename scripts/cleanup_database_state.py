#!/usr/bin/env python
"""
Clean up the database state after a failed hard reset.

This script removes old chunks, job history, and resets file states
to prepare for a proper reindex operation.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Create session
engine = create_engine("sqlite:///./data/database.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def cleanup_database(dry_run=True):
    """
    Clean up the database state.

    Args:
        dry_run: If True, only show what would be done without making changes
    """
    session = SessionLocal()

    try:
        logger.info("Starting database cleanup...")

        # 1. Mark stuck RUNNING batch as FAILED
        running_batches = session.execute(
            text("SELECT COUNT(*) FROM reindex_batches WHERE status = 'RUNNING'")
        ).scalar()

        if running_batches > 0:
            logger.info(f"Found {running_batches} stuck RUNNING batch(es)")
            if not dry_run:
                session.execute(
                    text("""
                        UPDATE reindex_batches
                        SET status = 'FAILED',
                            completed_at = :now,
                            last_error = 'Batch was stuck in RUNNING state and manually failed'
                        WHERE status = 'RUNNING'
                    """),
                    {"now": datetime.utcnow()}
                )
                logger.info("Marked RUNNING batches as FAILED")

        # 2. Count existing data that will be deleted
        chunk_count = session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        ).scalar()

        job_count = session.execute(
            text("""
                SELECT COUNT(*) FROM index_jobs
                WHERE job_type IN ('TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX', 'index_file', 'reindex_file')
            """)
        ).scalar()

        indexed_count = session.execute(
            text("SELECT COUNT(*) FROM indexed_files WHERE is_indexed = 1")
        ).scalar()

        logger.info(f"\nData to be cleaned:")
        logger.info(f"  - {chunk_count} document chunks")
        logger.info(f"  - {job_count} job records")
        logger.info(f"  - {indexed_count} files marked as indexed")

        if not dry_run:
            # 3. Delete all document chunks
            logger.info("\nDeleting all document chunks...")
            session.execute(text("DELETE FROM document_chunks"))
            logger.info(f"Deleted {chunk_count} chunks")

            # 4. Delete all indexing jobs
            logger.info("Deleting all indexing job history...")
            session.execute(
                text("""
                    DELETE FROM index_jobs
                    WHERE job_type IN ('TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX', 'index_file', 'reindex_file')
                """)
            )
            logger.info(f"Deleted {job_count} job records")

            # 5. Reset all file indexed flags
            logger.info("Resetting file indexed flags...")
            session.execute(
                text("""
                    UPDATE indexed_files
                    SET is_indexed = 0,
                        last_indexed_at = NULL,
                        index_version = NULL
                """)
            )
            logger.info(f"Reset {indexed_count} file indexed flags")

            # 6. Clear FTS index (if it exists)
            try:
                fts_count = session.execute(
                    text("SELECT COUNT(*) FROM chunks_fts")
                ).scalar()

                if fts_count > 0:
                    logger.info(f"Clearing {fts_count} FTS entries...")
                    # FTS table gets cleared automatically via triggers when chunks are deleted
                    logger.info("FTS index cleared via triggers")
            except Exception as e:
                logger.debug(f"FTS table check failed (might not exist): {e}")

            # Commit all changes
            session.commit()
            logger.info("\nDatabase cleanup completed successfully!")

        else:
            logger.info("\nDRY RUN - No changes made")
            logger.info("Run with --execute to apply these changes")

        # Show final state
        if not dry_run:
            final_chunks = session.execute(
                text("SELECT COUNT(*) FROM document_chunks")
            ).scalar()
            final_jobs = session.execute(
                text("""
                    SELECT COUNT(*) FROM index_jobs
                    WHERE job_type IN ('TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX')
                """)
            ).scalar()
            final_indexed = session.execute(
                text("SELECT COUNT(*) FROM indexed_files WHERE is_indexed = 1")
            ).scalar()

            logger.info("\nFinal state:")
            logger.info(f"  - Document chunks: {final_chunks} (should be 0)")
            logger.info(f"  - Pipeline jobs: {final_jobs} (should be 0)")
            logger.info(f"  - Files marked indexed: {final_indexed} (should be 0)")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description='Clean up database after failed reindex')
    parser.add_argument('--execute', action='store_true', default=False,
                        help='Actually execute the cleanup (default is dry run)')

    args = parser.parse_args()

    if args.execute:
        response = input("\nWARNING: This will DELETE all chunks and job history!\n"
                        "Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return

    cleanup_database(dry_run=not args.execute)


if __name__ == "__main__":
    main()