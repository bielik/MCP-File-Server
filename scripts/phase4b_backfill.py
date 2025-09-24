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

    def get_eligible_files(self, session: Session, offset: int = 0) -> List[IndexedFile]:
        """
        Get files that are eligible for Phase 4B processing.

        Args:
            session: Database session
            offset: Number of files to skip

        Returns:
            List of IndexedFile objects
        """
        # Get indexed files that don't already have Phase 4B jobs
        query = session.query(IndexedFile).filter(
            IndexedFile.is_indexed == True,
            ~IndexedFile.id.in_(
                session.query(IndexJob.file_id).filter(
                    IndexJob.job_type.in_(['TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX', 'EMBED'])
                )
            )
        ).offset(offset).limit(self.batch_size)

        return query.all()

    def create_phase4b_jobs(self, session: Session, file: IndexedFile) -> int:
        """
        Create Phase 4B processing jobs for a file.

        Args:
            session: Database session
            file: IndexedFile to process

        Returns:
            Number of jobs created
        """
        jobs_created = 0

        # Job types for Phase 4B pipeline
        job_types = ['TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX', 'EMBED']

        for job_type in job_types:
            try:
                # Check if job already exists
                existing_job = session.query(IndexJob).filter(
                    IndexJob.file_id == file.id,
                    IndexJob.job_type == job_type
                ).first()

                if existing_job:
                    logger.debug(f"Job {job_type} already exists for file {file.path}")
                    self.stats['jobs_skipped'] += 1
                    continue

                if not self.dry_run:
                    # Create new job
                    job = IndexJob(
                        file_id=file.id,
                        job_type=job_type
                    )
                    session.add(job)
                    jobs_created += 1
                else:
                    logger.info(f"[DRY RUN] Would create {job_type} job for {file.path}")
                    jobs_created += 1

            except Exception as e:
                logger.error(f"Failed to create {job_type} job for file {file.path}: {e}")
                self.stats['errors'] += 1

        return jobs_created

    def process_files_batch(self, session: Session, files: List[IndexedFile]) -> None:
        """
        Process a batch of files.

        Args:
            session: Database session
            files: List of files to process
        """
        for file in files:
            try:
                logger.info(f"Processing file: {file.path}")

                jobs_created = self.create_phase4b_jobs(session, file)
                self.stats['jobs_created'] += jobs_created
                self.stats['files_processed'] += 1

            except Exception as e:
                logger.error(f"Failed to process file {file.path}: {e}")
                self.stats['errors'] += 1

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
                offset = 0
                while True:
                    # Get next batch of files
                    files = self.get_eligible_files(session, offset)

                    if not files:
                        logger.info("No more files to process")
                        break

                    logger.info(f"Processing batch of {len(files)} files (offset: {offset})")
                    self.process_files_batch(session, files)

                    offset += len(files)

                    # Safety check to prevent infinite loops
                    if len(files) < self.batch_size:
                        break

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