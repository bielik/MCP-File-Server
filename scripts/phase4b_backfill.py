#!/usr/bin/env python3
"""
Phase 4B Backfill Script

This script processes existing indexed files and creates Phase 4B processing jobs
for them. It should be run once after upgrading to Phase 4B to ensure all existing
files are processed through the new chunking and embedding pipeline.

Usage:
    python scripts/phase4b_backfill.py [--dry-run] [--batch-size N]
"""

import argparse
import logging
import sys
import os
from typing import List, Optional

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend/app'))

from database import get_db, initialize_database
from models.indexing import IndexedFile, IndexJob, JobStatus
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class Phase4BBackfillManager:
    """Manages the backfill process for Phase 4B functionality."""

    def __init__(self, batch_size: int = 100, dry_run: bool = False):
        """
        Initialize backfill manager.

        Args:
            batch_size: Number of files to process in each batch
            dry_run: If True, only report what would be done without making changes
        """
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.stats = {
            'files_processed': 0,
            'jobs_created': 0,
            'jobs_skipped': 0,
            'errors': 0
        }

    def get_eligible_files(self, session: Session, last_file_id: int = 0) -> List[IndexedFile]:
        """
        Get files that are eligible for Phase 4B processing using cursor-based pagination.

        Args:
            session: Database session
            last_file_id: ID of the last processed file (for cursor pagination)

        Returns:
            List of IndexedFile objects that need Phase 4B processing
        """
        # Get indexed files starting from last_file_id (cursor-based pagination)
        # We get ONLY text files to avoid processing binary/PDF/etc. files
        query = session.query(IndexedFile).filter(
            IndexedFile.is_indexed == True,
            IndexedFile.is_text == True,  # Only process text files for Phase 4B
            IndexedFile.id > last_file_id
        ).order_by(IndexedFile.id).limit(self.batch_size)

        return query.all()

    def get_missing_jobs_for_file(self, session: Session, file: IndexedFile) -> List[str]:
        """
        Determine which Phase 4B jobs are missing for a specific file.

        Args:
            session: Database session
            file: IndexedFile to check

        Returns:
            List of missing job types
        """
        # All Phase 4B job types
        all_job_types = ['TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX', 'EMBED']

        # Get existing job types for this file
        existing_jobs = session.query(IndexJob.job_type).filter(
            IndexJob.file_id == file.id,
            IndexJob.job_type.in_(all_job_types)
        ).all()

        existing_job_types = {job[0] for job in existing_jobs}
        missing_job_types = [jt for jt in all_job_types if jt not in existing_job_types]

        return missing_job_types

    def create_phase4b_jobs(self, session: Session, file: IndexedFile) -> int:
        """
        Create missing Phase 4B processing jobs for a file.

        Args:
            session: Database session
            file: IndexedFile to process

        Returns:
            Number of jobs created
        """
        jobs_created = 0

        # Get missing job types for this file
        missing_job_types = self.get_missing_jobs_for_file(session, file)

        if not missing_job_types:
            logger.debug(f"File {file.path} already has all Phase 4B jobs")
            return 0

        logger.info(f"File {file.path} needs jobs: {missing_job_types}")

        for job_type in missing_job_types:
            try:
                if not self.dry_run:
                    # Create new job
                    job = IndexJob(
                        file_id=file.id,
                        job_type=job_type
                    )
                    session.add(job)
                    jobs_created += 1
                    logger.debug(f"Created {job_type} job for file {file.path}")
                else:
                    logger.info(f"[DRY RUN] Would create {job_type} job for {file.path}")
                    jobs_created += 1

            except Exception as e:
                logger.error(f"Failed to create {job_type} job for file {file.path}: {e}")
                self.stats['errors'] += 1

        return jobs_created

    def process_files_batch(self, session: Session, files: List[IndexedFile]) -> None:
        """
        Process a batch of files, creating only missing Phase 4B jobs.

        Args:
            session: Database session
            files: List of files to process
        """
        files_with_jobs = 0
        files_complete = 0

        for file in files:
            try:
                logger.debug(f"Checking file: {file.path}")

                jobs_created = self.create_phase4b_jobs(session, file)
                if jobs_created > 0:
                    self.stats['jobs_created'] += jobs_created
                    files_with_jobs += 1
                    logger.info(f"Created {jobs_created} jobs for file: {file.path}")
                else:
                    files_complete += 1
                    self.stats['jobs_skipped'] += 1

                self.stats['files_processed'] += 1

            except Exception as e:
                logger.error(f"Failed to process file {file.path}: {e}")
                self.stats['errors'] += 1

        logger.info(f"Batch summary: {files_with_jobs} files needed jobs, {files_complete} files already complete")

        if not self.dry_run:
            try:
                session.commit()
                logger.info(f"Committed batch of {len(files)} files")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to commit batch: {e}")
                self.stats['errors'] += len(files)

    def run_backfill(self) -> None:
        """Run the complete backfill process."""
        logger.info(f"Starting Phase 4B backfill process (dry_run={self.dry_run})")

        try:
            # Initialize database
            initialize_database()

            # Get database session
            session = next(get_db())

            try:
                last_file_id = 0
                total_files_processed = 0

                while True:
                    # Get next batch of files using cursor-based pagination
                    files = self.get_eligible_files(session, last_file_id)

                    if not files:
                        logger.info("No more files to process")
                        break

                    logger.info(f"Processing batch of {len(files)} files (starting from file ID {last_file_id + 1})")
                    self.process_files_batch(session, files)

                    # Update cursor to the last processed file ID
                    last_file_id = files[-1].id
                    total_files_processed += len(files)

                    # Safety check to prevent infinite loops
                    if len(files) < self.batch_size:
                        break

                logger.info(f"Completed backfill process. Total files processed: {total_files_processed}")

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Backfill process failed: {e}")
            raise

    def print_summary(self) -> None:
        """Print backfill summary statistics."""
        logger.info("=== Phase 4B Backfill Summary ===")
        logger.info(f"Files processed: {self.stats['files_processed']}")
        logger.info(f"Jobs created: {self.stats['jobs_created']}")
        logger.info(f"Jobs skipped: {self.stats['jobs_skipped']}")
        logger.info(f"Errors: {self.stats['errors']}")

        if self.dry_run:
            logger.info("*** This was a DRY RUN - no changes were made ***")


def main():
    """Main function for backfill script."""
    parser = argparse.ArgumentParser(description='Phase 4B backfill script for existing files')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    parser.add_argument('--batch-size', type=int, default=100,
                        help='Number of files to process in each batch')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        # Create and run backfill manager
        backfill = Phase4BBackfillManager(
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )

        backfill.run_backfill()
        backfill.print_summary()

        if backfill.stats['errors'] > 0:
            logger.warning(f"Backfill completed with {backfill.stats['errors']} errors")
            return 1

        logger.info("Backfill completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Backfill script failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())