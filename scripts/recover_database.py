#!/usr/bin/env python3
"""
Database Recovery Script for Ticket 017 Testing

This script recovers from database corruption by:
1. Dumping all valid data from the corrupted database
2. Creating a fresh database with the correct schema
3. Restoring the data
"""

import sqlite3
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

def recover_database():
    """Recover database from corruption."""

    corrupted_db = "data/database.db"
    recovery_db = "data/database_recovered.db"

    print("=" * 60)
    print("DATABASE RECOVERY SCRIPT")
    print("=" * 60)

    if not os.path.exists(corrupted_db):
        print(f"ERROR: Database not found at {corrupted_db}")
        return False

    print(f"1. Reading data from corrupted database...")

    try:
        # Connect to corrupted database
        old_conn = sqlite3.connect(corrupted_db)
        old_conn.row_factory = sqlite3.Row
        old_cursor = old_conn.cursor()

        # Extract all data
        data = {}

        # Get all tables
        tables = old_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()

        print(f"   Found {len(tables)} tables to recover")

        for table_row in tables:
            table_name = table_row[0]
            try:
                # Get table schema
                schema = old_cursor.execute(
                    f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';"
                ).fetchone()

                # Get all data from table
                rows = old_cursor.execute(f"SELECT * FROM {table_name}").fetchall()

                data[table_name] = {
                    'schema': schema[0] if schema else None,
                    'rows': [dict(row) for row in rows]
                }

                print(f"   - {table_name}: {len(rows)} rows recovered")

            except Exception as e:
                print(f"   WARNING: Could not recover {table_name}: {e}")
                continue

        # Get indexes
        indexes = old_cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL;"
        ).fetchall()

        old_conn.close()

    except Exception as e:
        print(f"ERROR: Failed to read corrupted database: {e}")
        return False

    print(f"\n2. Creating fresh database at {recovery_db}...")

    try:
        # Remove existing recovery database
        if os.path.exists(recovery_db):
            os.remove(recovery_db)

        # Create new database
        new_conn = sqlite3.connect(recovery_db)
        new_cursor = new_conn.cursor()

        # Enable WAL mode and other optimizations
        new_cursor.execute("PRAGMA journal_mode = WAL;")
        new_cursor.execute("PRAGMA synchronous = NORMAL;")
        new_cursor.execute("PRAGMA cache_size = -64000;")
        new_cursor.execute("PRAGMA temp_store = MEMORY;")
        new_cursor.execute("PRAGMA mmap_size = 30000000000;")

        # Create tables
        for table_name, table_data in data.items():
            if table_data['schema']:
                try:
                    new_cursor.execute(table_data['schema'])
                    print(f"   Created table: {table_name}")
                except Exception as e:
                    print(f"   WARNING: Could not create {table_name}: {e}")

        # Restore data
        print("\n3. Restoring data...")
        for table_name, table_data in data.items():
            if table_data['rows'] and table_data['schema']:
                try:
                    # Get column names from first row
                    if table_data['rows']:
                        columns = list(table_data['rows'][0].keys())
                        placeholders = ','.join(['?' for _ in columns])
                        column_list = ','.join(columns)

                        insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"

                        for row in table_data['rows']:
                            values = [row.get(col) for col in columns]
                            new_cursor.execute(insert_sql, values)

                        print(f"   Restored {len(table_data['rows'])} rows to {table_name}")

                except Exception as e:
                    print(f"   WARNING: Could not restore data to {table_name}: {e}")

        # Create indexes
        print("\n4. Creating indexes...")
        for index_row in indexes:
            try:
                new_cursor.execute(index_row[0])
                # Extract index name from SQL
                index_name = index_row[0].split('INDEX')[1].split('ON')[0].strip()
                print(f"   Created index: {index_name}")
            except Exception as e:
                print(f"   WARNING: Could not create index: {e}")

        # Create FTS5 virtual tables if needed
        print("\n5. Creating FTS5 tables...")
        try:
            new_cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_text,
                    content='document_chunks',
                    content_rowid='id',
                    tokenize='trigram'
                )
            """)
            print("   Created chunks_fts virtual table")

            # Populate FTS5 from document_chunks
            new_cursor.execute("""
                INSERT INTO chunks_fts(rowid, chunk_text)
                SELECT id, chunk_text FROM document_chunks
            """)

            fts_count = new_cursor.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
            print(f"   Populated FTS5 with {fts_count} entries")

        except Exception as e:
            print(f"   WARNING: Could not create FTS5 tables: {e}")

        new_conn.commit()

        # Verify integrity
        print("\n6. Verifying database integrity...")
        result = new_cursor.execute("PRAGMA integrity_check;").fetchone()
        print(f"   Integrity check: {result[0]}")

        if result[0] == "ok":
            print("\n" + "=" * 60)
            print("DATABASE RECOVERY SUCCESSFUL!")
            print("=" * 60)

            # Replace corrupted database with recovered one
            import shutil
            shutil.copy2(corrupted_db, f"{corrupted_db}.corrupted_backup")
            shutil.copy2(recovery_db, corrupted_db)
            print(f"\nCorrupted database backed up to: {corrupted_db}.corrupted_backup")
            print(f"Recovered database installed at: {corrupted_db}")

            # Print statistics
            file_count = new_cursor.execute("SELECT COUNT(*) FROM indexed_files").fetchone()[0]
            chunk_count = new_cursor.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
            job_count = new_cursor.execute("SELECT COUNT(*) FROM index_jobs").fetchone()[0]

            print(f"\nDatabase Statistics:")
            print(f"  - Files: {file_count}")
            print(f"  - Chunks: {chunk_count}")
            print(f"  - Jobs: {job_count}")

            new_conn.close()
            return True
        else:
            print("\nERROR: Database integrity check failed")
            new_conn.close()
            return False

    except Exception as e:
        print(f"ERROR: Failed to create recovery database: {e}")
        return False

if __name__ == "__main__":
    success = recover_database()
    sys.exit(0 if success else 1)