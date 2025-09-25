#!/usr/bin/env python3
"""Simple database check without Unicode characters."""
import sqlite3
import os

DATABASE_PATH = "C:/Users/MartinBielik/Dev/MCPFileServer/data/database.db"

def check_db():
    if not os.path.exists(DATABASE_PATH):
        print(f"ERROR: Database not found at {DATABASE_PATH}")
        return

    size = os.path.getsize(DATABASE_PATH)
    print(f"Database size: {size:,} bytes ({size/1024/1024:.1f} MB)")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\nTables ({len(tables)} total):")

        for table_name in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  {table_name}: {count} rows")
            except Exception as e:
                print(f"  {table_name}: ERROR - {e}")

        # Check Phase 4B tables specifically
        print(f"\nPhase 4B Table Check:")
        phase4b_tables = ['document_chunks', 'chunks_fts']
        for table in phase4b_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: EXISTS ({count} rows)")
            else:
                print(f"  {table}: MISSING")

        # Check job counts by type and status
        print(f"\nJob Status Summary:")
        cursor.execute("""
            SELECT job_type, status, COUNT(*)
            FROM index_jobs
            GROUP BY job_type, status
            ORDER BY job_type, status
        """)
        for job_type, status, count in cursor.fetchall():
            print(f"  {job_type} ({status}): {count}")

        # Check text file count
        cursor.execute("SELECT COUNT(*) FROM indexed_files WHERE is_text = 1")
        text_count = cursor.fetchone()[0]
        print(f"\nText files: {text_count}")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        conn.close()

    # Check WAL/SHM files
    wal_exists = os.path.exists(DATABASE_PATH + "-wal")
    shm_exists = os.path.exists(DATABASE_PATH + "-shm")
    print(f"\nWAL file exists: {wal_exists}")
    print(f"SHM file exists: {shm_exists}")

if __name__ == "__main__":
    check_db()