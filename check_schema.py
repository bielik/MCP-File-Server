#!/usr/bin/env python3
"""
Check the schema of database tables.
"""
import sqlite3
import os

DATABASE_PATH = "C:/Users/MartinBielik/Dev/MCPFileServer/data/database.db"

def check_schema():
    """Check table schemas."""

    if not os.path.exists(DATABASE_PATH):
        print(f"Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check index_jobs schema
        cursor.execute("PRAGMA table_info(index_jobs)")
        columns = cursor.fetchall()
        print("index_jobs columns:")
        for col in columns:
            print(f"  {col}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_schema()