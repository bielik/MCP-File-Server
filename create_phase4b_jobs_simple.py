#!/usr/bin/env python3
"""
Simple script to create Phase 4B jobs for existing text files by directly
interacting with the database through the backend API.
"""
import sqlite3
import os

DATABASE_PATH = "C:/Users/MartinBielik/Dev/MCPFileServer/data/database.db"

def create_phase4b_jobs():
    """Create Phase 4B jobs for existing indexed text files."""

    if not os.path.exists(DATABASE_PATH):
        print(f"Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Get text files that don't have Phase 4B jobs yet
        cursor.execute("""
            SELECT id, path FROM indexed_files
            WHERE is_text = 1 AND is_indexed = 1
            AND id NOT IN (
                SELECT DISTINCT file_id FROM index_jobs
                WHERE job_type IN ('TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX')
            )
            LIMIT 10
        """)

        eligible_files = cursor.fetchall()
        print(f"Found {len(eligible_files)} files that need Phase 4B jobs")

        jobs_created = 0
        for file_id, file_path in eligible_files:
            print(f"Creating Phase 4B jobs for: {file_path}")

            # Create Phase 4B jobs for this file
            for job_type in ["TEXT_EXTRACT", "CHUNK", "FTS_INDEX"]:
                cursor.execute("""
                    INSERT INTO index_jobs (file_id, job_type, status, created_at, updated_at)
                    VALUES (?, ?, 'PENDING', datetime('now'), datetime('now'))
                """, (file_id, job_type))
                jobs_created += 1
                print(f"  Created {job_type} job")

        conn.commit()
        print(f"Successfully created {jobs_created} Phase 4B jobs")

        # Show current job counts
        cursor.execute("SELECT job_type, COUNT(*) FROM index_jobs GROUP BY job_type")
        job_counts = cursor.fetchall()
        print("\nCurrent job counts:")
        for job_type, count in job_counts:
            print(f"  {job_type}: {count}")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_phase4b_jobs()