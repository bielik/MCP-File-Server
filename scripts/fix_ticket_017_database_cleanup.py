#!/usr/bin/env python3
"""
Database Cleanup Script for Ticket 017 Fix

This script performs the following critical database repairs after implementing
the Ticket 017 fixes:

1. Migrates mtime_epoch values from seconds to nanoseconds
2. Identifies and merges duplicate file records created by rename operations
3. Cleans up orphaned document chunks
4. Updates doc_id values to be path-independent

CRITICAL: Run this script AFTER deploying the Ticket 017 fixes but BEFORE
resuming normal operations to ensure database consistency.
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from app.database import get_db, initialize_database
from app.models.indexing import IndexedFile, DocumentChunk
from sqlalchemy import text, func
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_mtime_to_nanoseconds(session: Session) -> int:
    """
    Migrate existing mtime_epoch values from seconds to nanoseconds.

    Args:
        session: Database session

    Returns:
        Number of records updated
    """
    logger.info("Migrating mtime_epoch values from seconds to nanoseconds...")

    # Find records that likely have second-precision timestamps (< 2000000000000000)
    # Nanosecond timestamps are much larger than second timestamps
    records_to_update = session.query(IndexedFile).filter(
        IndexedFile.mtime_epoch < 2000000000000000  # Approximately year 2033 in seconds
    ).all()

    updated_count = 0
    for record in records_to_update:
        # Convert from seconds to nanoseconds by multiplying by 1e9
        old_mtime = record.mtime_epoch
        record.mtime_epoch = int(old_mtime * 1000000000)
        updated_count += 1

        if updated_count % 100 == 0:
            logger.info(f"Updated {updated_count} mtime values...")

    session.commit()
    logger.info(f"Successfully migrated {updated_count} mtime values to nanoseconds")
    return updated_count


def update_doc_ids_path_independent(session: Session) -> int:
    """
    Update doc_id values to be path-independent using size:mtime format.

    Args:
        session: Database session

    Returns:
        Number of records updated
    """
    logger.info("Updating doc_id values to be path-independent...")

    all_files = session.query(IndexedFile).all()
    updated_count = 0

    for file_record in all_files:
        # Generate new path-independent doc_id
        import hashlib
        content = f"{file_record.size_bytes}:{file_record.mtime_epoch}"
        new_doc_id = hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]

        if file_record.doc_id != new_doc_id:
            file_record.doc_id = new_doc_id
            updated_count += 1

        if updated_count % 100 == 0:
            logger.info(f"Updated {updated_count} doc_id values...")

    session.commit()
    logger.info(f"Successfully updated {updated_count} doc_id values")
    return updated_count


def find_and_merge_duplicate_files(session: Session) -> int:
    """
    Find and merge duplicate file records created by rename operations.

    Identifies files with the same size and mtime but different paths,
    merges their chunks to the most recent record, and deletes duplicates.

    Args:
        session: Database session

    Returns:
        Number of duplicate records cleaned up
    """
    logger.info("Finding and merging duplicate file records...")

    # Find potential duplicates by grouping on size and mtime
    duplicates_query = session.query(
        IndexedFile.size_bytes,
        IndexedFile.mtime_epoch,
        func.count(IndexedFile.id).label('count')
    ).group_by(
        IndexedFile.size_bytes,
        IndexedFile.mtime_epoch
    ).having(func.count(IndexedFile.id) > 1)

    duplicate_groups = duplicates_query.all()

    if not duplicate_groups:
        logger.info("No duplicate file records found")
        return 0

    logger.info(f"Found {len(duplicate_groups)} groups with duplicate files")

    total_cleaned = 0

    for size_bytes, mtime_epoch, count in duplicate_groups:
        # Get all files in this duplicate group
        duplicate_files = session.query(IndexedFile).filter(
            IndexedFile.size_bytes == size_bytes,
            IndexedFile.mtime_epoch == mtime_epoch
        ).order_by(IndexedFile.discovered_at.desc()).all()

        if len(duplicate_files) <= 1:
            continue

        # Keep the most recently discovered file (likely the renamed version)
        keeper = duplicate_files[0]
        duplicates_to_remove = duplicate_files[1:]

        logger.info(f"Merging {len(duplicates_to_remove)} duplicates into {keeper.path}")

        # Move chunks from duplicates to keeper
        chunks_moved = 0
        for duplicate in duplicates_to_remove:
            chunks = session.query(DocumentChunk).filter(
                DocumentChunk.file_id == duplicate.id
            ).all()

            for chunk in chunks:
                chunk.file_id = keeper.id
                chunks_moved += 1

            # Delete the duplicate file record
            session.delete(duplicate)
            total_cleaned += 1

        if chunks_moved > 0:
            logger.info(f"Moved {chunks_moved} chunks from duplicates to {keeper.path}")

    session.commit()
    logger.info(f"Successfully cleaned up {total_cleaned} duplicate file records")
    return total_cleaned


def cleanup_orphaned_chunks(session: Session) -> int:
    """
    Clean up document chunks that reference non-existent files.

    Args:
        session: Database session

    Returns:
        Number of orphaned chunks cleaned up
    """
    logger.info("Cleaning up orphaned document chunks...")

    # Find chunks whose file_id doesn't exist in indexed_files
    orphaned_chunks = session.query(DocumentChunk).filter(
        ~DocumentChunk.file_id.in_(
            session.query(IndexedFile.id)
        )
    ).all()

    if not orphaned_chunks:
        logger.info("No orphaned chunks found")
        return 0

    logger.info(f"Found {len(orphaned_chunks)} orphaned chunks")

    # Delete orphaned chunks
    for chunk in orphaned_chunks:
        session.delete(chunk)

    session.commit()
    logger.info(f"Successfully cleaned up {len(orphaned_chunks)} orphaned chunks")
    return len(orphaned_chunks)


def verify_database_consistency(session: Session) -> dict:
    """
    Verify database consistency after cleanup.

    Args:
        session: Database session

    Returns:
        Dictionary with consistency check results
    """
    logger.info("Verifying database consistency...")

    results = {}

    # Count total files and chunks
    total_files = session.query(IndexedFile).count()
    total_chunks = session.query(DocumentChunk).count()

    # Check for files with duplicate doc_ids
    duplicate_doc_ids = session.query(
        IndexedFile.doc_id,
        func.count(IndexedFile.id).label('count')
    ).group_by(IndexedFile.doc_id).having(func.count(IndexedFile.id) > 1).count()

    # Check for orphaned chunks
    orphaned_chunks = session.query(DocumentChunk).filter(
        ~DocumentChunk.file_id.in_(session.query(IndexedFile.id))
    ).count()

    # Check mtime precision (should all be nanosecond precision now)
    second_precision_files = session.query(IndexedFile).filter(
        IndexedFile.mtime_epoch < 2000000000000000
    ).count()

    results = {
        'total_files': total_files,
        'total_chunks': total_chunks,
        'duplicate_doc_ids': duplicate_doc_ids,
        'orphaned_chunks': orphaned_chunks,
        'second_precision_files': second_precision_files
    }

    logger.info(f"Database consistency check results:")
    logger.info(f"  Total files: {total_files}")
    logger.info(f"  Total chunks: {total_chunks}")
    logger.info(f"  Files with duplicate doc_ids: {duplicate_doc_ids}")
    logger.info(f"  Orphaned chunks: {orphaned_chunks}")
    logger.info(f"  Files with second precision mtime: {second_precision_files}")

    return results


def main():
    """Main cleanup function."""
    logger.info("=" * 60)
    logger.info("TICKET 017 DATABASE CLEANUP SCRIPT")
    logger.info("=" * 60)

    # Initialize database
    initialize_database()

    with next(get_db()) as session:
        try:
            # Step 1: Migrate mtime values to nanoseconds
            mtime_updated = migrate_mtime_to_nanoseconds(session)

            # Step 2: Update doc_id values to be path-independent
            docid_updated = update_doc_ids_path_independent(session)

            # Step 3: Find and merge duplicate files
            duplicates_cleaned = find_and_merge_duplicate_files(session)

            # Step 4: Clean up orphaned chunks
            orphans_cleaned = cleanup_orphaned_chunks(session)

            # Step 5: Verify consistency
            consistency_results = verify_database_consistency(session)

            # Summary
            logger.info("=" * 60)
            logger.info("CLEANUP SUMMARY")
            logger.info("=" * 60)
            logger.info(f"  Mtime values migrated: {mtime_updated}")
            logger.info(f"  Doc IDs updated: {docid_updated}")
            logger.info(f"  Duplicate files merged: {duplicates_cleaned}")
            logger.info(f"  Orphaned chunks cleaned: {orphans_cleaned}")
            logger.info("=" * 60)

            if (consistency_results['duplicate_doc_ids'] == 0 and
                consistency_results['orphaned_chunks'] == 0 and
                consistency_results['second_precision_files'] == 0):
                logger.info("✅ DATABASE CLEANUP SUCCESSFUL - All consistency checks passed!")
            else:
                logger.warning("⚠️  Some consistency issues remain - manual review may be needed")

        except Exception as e:
            logger.error(f"❌ Database cleanup failed: {e}")
            session.rollback()
            raise


if __name__ == "__main__":
    main()