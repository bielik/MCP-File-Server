#!/usr/bin/env python3
"""
Fix job status case mismatch - convert PENDING to pending to match JobStatus enum.
"""
import sqlite3
import os

DATABASE_PATH = "C:/Users/MartinBielik/Dev/MCPFileServer/data/database.db"

def fix_job_status_case():
    """Fix job status case to match JobStatus enum values."""

    if not os.path.exists(DATABASE_PATH):
        print(f"Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check current status distribution
        print("Current job status distribution:")
        cursor.execute("SELECT status, COUNT(*) FROM index_jobs GROUP BY status")
        for status, count in cursor.fetchall():
            print(f"  {status}: {count}")

        # Fix uppercase statuses to lowercase
        status_fixes = {
            "PENDING": "pending",
            "PROCESSING": "processing",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "DEAD_LETTER": "dead_letter"
        }

        total_fixed = 0
        for old_status, new_status in status_fixes.items():
            cursor.execute("UPDATE index_jobs SET status = ? WHERE status = ?", (new_status, old_status))
            fixed_count = cursor.rowcount
            if fixed_count > 0:
                print(f"Fixed {fixed_count} jobs: {old_status} -> {new_status}")
                total_fixed += fixed_count

        conn.commit()

        print(f"\nFixed {total_fixed} job statuses")

        # Show updated distribution
        print("\nUpdated job status distribution:")
        cursor.execute("SELECT status, COUNT(*) FROM index_jobs GROUP BY status")
        for status, count in cursor.fetchall():
            print(f"  {status}: {count}")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_job_status_case()