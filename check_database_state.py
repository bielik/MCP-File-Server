#!/usr/bin/env python3
"""
Check the current state of the database to understand the Phase 4B job situation.
"""
import sqlite3
import os

DATABASE_PATH = "C:/Users/MartinBielik/Dev/MCPFileServer/data/database.db"

def check_database_state():
    """Check the current state of files and jobs in the database."""

    if not os.path.exists(DATABASE_PATH):
        print(f"Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check indexed files
        cursor.execute("SELECT COUNT(*) FROM indexed_files")
        total_files = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM indexed_files WHERE is_text = 1")
        text_files = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM indexed_files WHERE is_indexed = 1")
        indexed_files = cursor.fetchone()[0]

        print(f"Files in database:")
        print(f"  Total files: {total_files}")
        print(f"  Text files: {text_files}")
        print(f"  Indexed files: {indexed_files}")

        # Check jobs
        cursor.execute("SELECT job_type, COUNT(*) FROM index_jobs GROUP BY job_type ORDER BY job_type")
        job_counts = cursor.fetchall()
        print(f"\nJobs in database:")
        for job_type, count in job_counts:
            print(f"  {job_type}: {count}")

        # Check document chunks
        cursor.execute("SELECT COUNT(*) FROM document_chunks")
        chunk_count = cursor.fetchone()[0]
        print(f"\nDocument chunks: {chunk_count}")

        # Sample some specific files
        cursor.execute("""
            SELECT f.id, f.path, f.is_text,
                   COUNT(j.id) as job_count,
                   GROUP_CONCAT(j.job_type) as job_types
            FROM indexed_files f
            LEFT JOIN index_jobs j ON f.id = j.file_id
            WHERE f.path LIKE '%test%' OR f.path LIKE '%txt'
            GROUP BY f.id, f.path, f.is_text
            LIMIT 5
        """)

        sample_files = cursor.fetchall()
        print(f"\nSample files (focusing on test files and txt files):")
        for file_id, path, is_text, job_count, job_types in sample_files:
            print(f"  ID: {file_id}, Path: {path}, IsText: {is_text}, Jobs: {job_count} ({job_types})")

        # Check recent jobs
        cursor.execute("""
            SELECT j.id, j.job_type, j.status, f.path, j.created_at
            FROM index_jobs j
            JOIN indexed_files f ON j.file_id = f.id
            ORDER BY j.id DESC
            LIMIT 5
        """)

        recent_jobs = cursor.fetchall()
        print(f"\nRecent jobs:")
        for job_id, job_type, status, file_path, created_at in recent_jobs:
            print(f"  Job {job_id}: {job_type} ({status}) for {file_path} at {created_at}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_database_state()