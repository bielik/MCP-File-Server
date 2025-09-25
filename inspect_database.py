#!/usr/bin/env python3
"""
Comprehensive database inspection to verify structure and data.
"""
import sqlite3
import os

DATABASE_PATH = "C:/Users/MartinBielik/Dev/MCPFileServer/data/database.db"

def inspect_database():
    """Inspect the complete database structure and data."""

    if not os.path.exists(DATABASE_PATH):
        print(f"[ERROR] Database not found at {DATABASE_PATH}")
        return

    print(f"[OK] Database file exists: {DATABASE_PATH}")

    # Check file size
    size = os.path.getsize(DATABASE_PATH)
    print(f"[INFO] Database size: {size:,} bytes ({size/1024/1024:.1f} MB)")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print(f"\n[TABLES] Tables in database ({len(tables)} total):")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  {table_name}: {count} rows")

        # Check for Phase 4B specific tables
        phase4b_tables = ['document_chunks', 'chunks_fts']
        print(f"\n🔍 Phase 4B Tables Check:")
        for table in phase4b_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            exists = cursor.fetchone()
            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✅ {table}: EXISTS ({count} rows)")
            else:
                print(f"  ❌ {table}: MISSING")

        # Check for FTS virtual tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'")
        fts_tables = cursor.fetchall()
        print(f"\n🔍 FTS Virtual Tables:")
        for table in fts_tables:
            print(f"  📊 {table[0]}")

        # Check indexed_files details
        print(f"\n📂 Indexed Files Analysis:")
        cursor.execute("SELECT COUNT(*) FROM indexed_files WHERE is_text = 1")
        text_files = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM indexed_files WHERE is_text = 0")
        binary_files = cursor.fetchone()[0]
        print(f"  📝 Text files: {text_files}")
        print(f"  🔧 Binary files: {binary_files}")

        # Check job status distribution
        print(f"\n⚙️ Job Status Analysis:")
        cursor.execute("""
            SELECT job_type, status, COUNT(*)
            FROM index_jobs
            GROUP BY job_type, status
            ORDER BY job_type, status
        """)
        job_statuses = cursor.fetchall()
        for job_type, status, count in job_statuses:
            print(f"  🔄 {job_type} ({status}): {count}")

        # Check recent job activity
        print(f"\n⏱️ Recent Job Activity (last 10):")
        cursor.execute("""
            SELECT j.id, j.job_type, j.status, f.path,
                   datetime(j.created_at, 'unixepoch') as created_time
            FROM index_jobs j
            JOIN indexed_files f ON j.file_id = f.id
            ORDER BY j.id DESC
            LIMIT 10
        """)
        recent_jobs = cursor.fetchall()
        for job_id, job_type, status, file_path, created_time in recent_jobs:
            print(f"  🎯 Job {job_id}: {job_type} ({status}) - {file_path[:50]}... at {created_time}")

        # Sample some text files to verify they should have Phase 4B jobs
        print(f"\n📋 Sample Text Files:")
        cursor.execute("""
            SELECT f.id, f.path, f.is_text,
                   (SELECT COUNT(*) FROM index_jobs j WHERE j.file_id = f.id AND j.job_type = 'TEXT_EXTRACT') as text_extract_jobs,
                   (SELECT COUNT(*) FROM index_jobs j WHERE j.file_id = f.id AND j.job_type = 'CHUNK') as chunk_jobs,
                   (SELECT COUNT(*) FROM index_jobs j WHERE j.file_id = f.id AND j.job_type = 'FTS_INDEX') as fts_jobs
            FROM indexed_files f
            WHERE f.is_text = 1
            LIMIT 5
        """)
        sample_files = cursor.fetchall()
        for file_id, path, is_text, text_jobs, chunk_jobs, fts_jobs in sample_files:
            print(f"  📄 {path}: TEXT_EXTRACT:{text_jobs}, CHUNK:{chunk_jobs}, FTS_INDEX:{fts_jobs}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

    # Check for WAL and SHM files
    wal_file = DATABASE_PATH + "-wal"
    shm_file = DATABASE_PATH + "-shm"

    print(f"\n📁 Associated Files:")
    for file_path, name in [(wal_file, "WAL"), (shm_file, "SHM")]:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  ✅ {name} file: {size:,} bytes")
        else:
            print(f"  ❌ {name} file: MISSING")

if __name__ == "__main__":
    inspect_database()