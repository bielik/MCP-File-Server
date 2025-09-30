#!/usr/bin/env python
"""
Analyze how chunks were created to explain the data inconsistency.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Create session
engine = create_engine("sqlite:///./data/database.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def analyze_chunk_creation():
    """Analyze how the existing chunks were created."""
    session = SessionLocal()

    try:
        print("=== CHUNK CREATION ANALYSIS ===\n")

        # 1. Count chunks by file
        print("1. CHUNK COUNTS:")
        chunk_stats = session.execute(text("""
            SELECT COUNT(*) as total_chunks,
                   COUNT(DISTINCT file_id) as files_with_chunks
            FROM document_chunks
        """)).fetchone()

        print(f"   Total chunks: {chunk_stats.total_chunks}")
        print(f"   Files with chunks: {chunk_stats.files_with_chunks}")

        # 2. Check job types that created chunks
        print("\n2. JOB TYPE ANALYSIS:")
        job_stats = session.execute(text("""
            SELECT job_type, status, COUNT(*) as count
            FROM index_jobs
            WHERE job_type IN ('CHUNK', 'index_file', 'reindex_file')
            GROUP BY job_type, status
            ORDER BY job_type, status
        """)).fetchall()

        for stat in job_stats:
            print(f"   {stat.job_type} - {stat.status}: {stat.count}")

        # 3. Files with chunks vs job completion
        print("\n3. MISMATCH ANALYSIS:")

        # Files that have chunks
        files_with_chunks = session.execute(text("""
            SELECT DISTINCT file_id
            FROM document_chunks
        """)).fetchall()

        chunk_file_ids = {row.file_id for row in files_with_chunks}
        print(f"   Files with chunks: {len(chunk_file_ids)}")

        # Files with completed CHUNK jobs
        chunk_completed = session.execute(text("""
            SELECT DISTINCT file_id
            FROM index_jobs
            WHERE job_type = 'CHUNK' AND status = 'COMPLETED'
        """)).fetchall()

        chunk_job_file_ids = {row.file_id for row in chunk_completed}
        print(f"   Files with completed CHUNK jobs: {len(chunk_job_file_ids)}")

        # Files with completed index_file jobs
        index_completed = session.execute(text("""
            SELECT DISTINCT file_id
            FROM index_jobs
            WHERE job_type IN ('index_file', 'reindex_file') AND status = 'COMPLETED'
        """)).fetchall()

        index_job_file_ids = {row.file_id for row in index_completed}
        print(f"   Files with completed index_file/reindex_file jobs: {len(index_job_file_ids)}")

        # Check overlap
        chunk_from_index_jobs = chunk_file_ids.intersection(index_job_file_ids)
        chunk_from_chunk_jobs = chunk_file_ids.intersection(chunk_job_file_ids)

        print(f"\n4. CHUNK SOURCE ANALYSIS:")
        print(f"   Chunks created by index_file/reindex_file jobs: {len(chunk_from_index_jobs)}")
        print(f"   Chunks created by CHUNK jobs: {len(chunk_from_chunk_jobs)}")
        print(f"   Chunks with no clear job source: {len(chunk_file_ids) - len(chunk_from_index_jobs) - len(chunk_from_chunk_jobs)}")

        # 5. Recent activity
        print(f"\n5. RECENT JOB ACTIVITY:")
        recent_jobs = session.execute(text("""
            SELECT job_type, status, COUNT(*) as count,
                   MIN(created_at) as earliest,
                   MAX(created_at) as latest
            FROM index_jobs
            WHERE created_at > datetime('now', '-1 day')
            GROUP BY job_type, status
            ORDER BY latest DESC
        """)).fetchall()

        for job in recent_jobs:
            print(f"   {job.job_type} - {job.status}: {job.count} jobs (latest: {job.latest})")

        print(f"\n=== CONCLUSION ===")
        if len(chunk_from_index_jobs) > 0 and len(chunk_from_chunk_jobs) == 0:
            print("✓ Chunks were created by the OLD indexing system (index_file/reindex_file jobs)")
            print("✓ NEW chunking pipeline (CHUNK jobs) has failed completely")
            print("✓ UI is correct: all CHUNK jobs failed")
            print("✓ But chunks exist from previous successful index_file jobs")
            print("\nRECOMMENDAT ION: Run hard reset to clear old data and restart with new pipeline")
        else:
            print("Mixed chunk creation sources detected - needs investigation")

    except Exception as e:
        print(f"Error during analysis: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    analyze_chunk_creation()