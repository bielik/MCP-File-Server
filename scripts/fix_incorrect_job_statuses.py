#!/usr/bin/env python
"""
Fix incorrect job statuses in the database.

This script identifies and corrects jobs that are marked as "completed"
but don't have corresponding results in the database (chunks for CHUNK jobs,
FTS entries for FTS_INDEX jobs).
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.database import get_db
from backend.app.models.indexing import IndexJob, JobStatus, DocumentChunk, IndexedFile
from sqlalchemy import func, and_, create_engine
from sqlalchemy.orm import sessionmaker

# Create session
engine = create_engine("sqlite:///./data/database.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_chunk_job_statuses(session, dry_run=True):
    """
    Fix CHUNK jobs marked as completed but with no actual chunks created.
    """
    logger.info("Checking CHUNK jobs for incorrect completion status...")

    # Find all completed CHUNK jobs
    completed_chunk_jobs = session.query(IndexJob).filter(
        and_(
            IndexJob.job_type == 'CHUNK',
            IndexJob.status == JobStatus.COMPLETED
        )
    ).all()

    logger.info(f"Found {len(completed_chunk_jobs)} completed CHUNK jobs")

    incorrect_jobs = []
    for job in completed_chunk_jobs:
        # Check if this file actually has chunks
        chunk_count = session.query(func.count(DocumentChunk.id)).filter(
            DocumentChunk.file_id == job.file_id
        ).scalar()

        if chunk_count == 0:
            incorrect_jobs.append(job)

    logger.info(f"Found {len(incorrect_jobs)} CHUNK jobs incorrectly marked as completed")

    if not dry_run and incorrect_jobs:
        # Update these jobs to failed status
        for job in incorrect_jobs:
            job.status = JobStatus.FAILED
            job.last_error = "Retroactive fix: Job marked completed but no chunks were created"
            logger.debug(f"Updated job {job.id} for file_id {job.file_id} to FAILED")

        session.commit()
        logger.info(f"Updated {len(incorrect_jobs)} CHUNK jobs to FAILED status")

    return len(incorrect_jobs)


def fix_fts_index_job_statuses(session, dry_run=True):
    """
    Fix FTS_INDEX jobs marked as completed but with no actual FTS entries.
    """
    logger.info("Checking FTS_INDEX jobs for incorrect completion status...")

    # Find all completed FTS_INDEX jobs
    completed_fts_jobs = session.query(IndexJob).filter(
        and_(
            IndexJob.job_type == 'FTS_INDEX',
            IndexJob.status == JobStatus.COMPLETED
        )
    ).all()

    logger.info(f"Found {len(completed_fts_jobs)} completed FTS_INDEX jobs")

    incorrect_jobs = []
    for job in completed_fts_jobs:
        # Check if this file actually has chunks (FTS entries are based on chunks)
        chunk_count = session.query(func.count(DocumentChunk.id)).filter(
            DocumentChunk.file_id == job.file_id
        ).scalar()

        if chunk_count == 0:
            incorrect_jobs.append(job)

    logger.info(f"Found {len(incorrect_jobs)} FTS_INDEX jobs incorrectly marked as completed")

    if not dry_run and incorrect_jobs:
        # Update these jobs to failed status
        for job in incorrect_jobs:
            job.status = JobStatus.FAILED
            job.last_error = "Retroactive fix: Job marked completed but no chunks exist for FTS indexing"
            logger.debug(f"Updated job {job.id} for file_id {job.file_id} to FAILED")

        session.commit()
        logger.info(f"Updated {len(incorrect_jobs)} FTS_INDEX jobs to FAILED status")

    return len(incorrect_jobs)


def fix_file_indexed_flags(session, dry_run=True):
    """
    Fix indexed files that are marked as indexed but have no chunks.
    """
    logger.info("Checking file indexed flags...")

    # Find text files marked as indexed
    indexed_text_files = session.query(IndexedFile).filter(
        and_(
            IndexedFile.is_indexed == True,
            IndexedFile.is_text == True
        )
    ).all()

    logger.info(f"Found {len(indexed_text_files)} text files marked as indexed")

    incorrect_files = []
    for file in indexed_text_files:
        # Check if this file actually has chunks
        chunk_count = session.query(func.count(DocumentChunk.id)).filter(
            DocumentChunk.file_id == file.id
        ).scalar()

        if chunk_count == 0:
            incorrect_files.append(file)

    logger.info(f"Found {len(incorrect_files)} files incorrectly marked as indexed")

    if not dry_run and incorrect_files:
        # Update these files to not indexed
        for file in incorrect_files:
            file.is_indexed = False
            file.last_indexed_at = None
            logger.debug(f"Updated file {file.path} to not indexed")

        session.commit()
        logger.info(f"Updated {len(incorrect_files)} files to not indexed")

    return len(incorrect_files)


def main():
    """Main function to run all fixes."""
    import argparse

    parser = argparse.ArgumentParser(description='Fix incorrect job statuses in the database')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Show what would be fixed without making changes')
    parser.add_argument('--fix-chunk-jobs', action='store_true', default=False,
                        help='Fix CHUNK jobs with incorrect status')
    parser.add_argument('--fix-fts-jobs', action='store_true', default=False,
                        help='Fix FTS_INDEX jobs with incorrect status')
    parser.add_argument('--fix-file-flags', action='store_true', default=False,
                        help='Fix file indexed flags')
    parser.add_argument('--fix-all', action='store_true', default=False,
                        help='Fix all issues')

    args = parser.parse_args()

    # If no specific fix is requested, default to dry-run of all
    if not any([args.fix_chunk_jobs, args.fix_fts_jobs, args.fix_file_flags, args.fix_all]):
        args.dry_run = True
        args.fix_all = True

    session = SessionLocal()

    try:
        total_fixed = 0

        if args.fix_all or args.fix_chunk_jobs:
            chunk_fixed = fix_chunk_job_statuses(session, dry_run=args.dry_run)
            total_fixed += chunk_fixed
            print(f"\n{'Would fix' if args.dry_run else 'Fixed'} {chunk_fixed} CHUNK jobs")

        if args.fix_all or args.fix_fts_jobs:
            fts_fixed = fix_fts_index_job_statuses(session, dry_run=args.dry_run)
            total_fixed += fts_fixed
            print(f"{'Would fix' if args.dry_run else 'Fixed'} {fts_fixed} FTS_INDEX jobs")

        if args.fix_all or args.fix_file_flags:
            files_fixed = fix_file_indexed_flags(session, dry_run=args.dry_run)
            total_fixed += files_fixed
            print(f"{'Would fix' if args.dry_run else 'Fixed'} {files_fixed} file indexed flags")

        if args.dry_run:
            print(f"\nTotal issues found: {total_fixed}")
            print("Run with specific --fix-* flags (without --dry-run) to apply fixes")
            print("Example: python fix_incorrect_job_statuses.py --fix-all")
        else:
            print(f"\nTotal issues fixed: {total_fixed}")

    except Exception as e:
        logger.error(f"Error during fix: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()