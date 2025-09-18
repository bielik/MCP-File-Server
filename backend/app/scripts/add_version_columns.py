#!/usr/bin/env python3
"""
Database Migration: Add Version Columns
Phase 3B: Fix missing version columns in workspaces and permissions tables

This script adds the missing 'version' columns to both workspaces and permissions tables
to match the SQLAlchemy models defined in app/models/workspace.py.
"""

import sys
import os
import sqlite3
import argparse
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import SQLALCHEMY_DATABASE_URL


def get_db_path():
    """Get the database path from configuration."""
    db_url = SQLALCHEMY_DATABASE_URL
    # Extract path from sqlite:///./data/database.db format
    if db_url.startswith('sqlite:///'):
        return db_url[10:]  # Remove 'sqlite:///' prefix
    else:
        raise ValueError(f"Unsupported database URL format: {db_url}")


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    return column_name in column_names


def add_version_columns(db_path, dry_run=False):
    """Add version columns to workspaces and permissions tables."""
    print(f"Database Migration: Add Version Columns")
    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print("-" * 50)

    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"ERROR: Database file not found: {db_path}")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check current schema
        print("Checking current schema...")

        # Check workspaces table
        workspaces_has_version = check_column_exists(cursor, 'workspaces', 'version')
        print(f"   workspaces.version: {'EXISTS' if workspaces_has_version else 'MISSING'}")

        # Check permissions table
        permissions_has_version = check_column_exists(cursor, 'permissions', 'version')
        print(f"   permissions.version: {'EXISTS' if permissions_has_version else 'MISSING'}")

        if workspaces_has_version and permissions_has_version:
            print("\nAll version columns already exist. No migration needed.")
            return True

        # Prepare migration SQL
        migration_sql = []

        if not workspaces_has_version:
            migration_sql.append(
                "ALTER TABLE workspaces ADD COLUMN version INTEGER NOT NULL DEFAULT 1;"
            )
            print("\nWill add version column to workspaces table")

        if not permissions_has_version:
            migration_sql.append(
                "ALTER TABLE permissions ADD COLUMN version INTEGER NOT NULL DEFAULT 1;"
            )
            print("Will add version column to permissions table")

        if dry_run:
            print("\nDRY RUN - SQL that would be executed:")
            for sql in migration_sql:
                print(f"   {sql}")
            print("\nTo execute this migration, run without --dry-run flag")
            return True

        # Execute migration
        print("\nExecuting migration...")

        for sql in migration_sql:
            print(f"   Executing: {sql}")
            cursor.execute(sql)

        # Commit changes
        conn.commit()
        print("Migration completed successfully!")

        # Verify migration
        print("\nVerifying migration...")

        workspaces_has_version = check_column_exists(cursor, 'workspaces', 'version')
        permissions_has_version = check_column_exists(cursor, 'permissions', 'version')

        print(f"   workspaces.version: {'EXISTS' if workspaces_has_version else 'MISSING'}")
        print(f"   permissions.version: {'EXISTS' if permissions_has_version else 'MISSING'}")

        if workspaces_has_version and permissions_has_version:
            print("\nMigration verification successful!")
            return True
        else:
            print("\nMigration verification failed!")
            return False

    except sqlite3.Error as e:
        print(f"\nSQLite error: {e}")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def update_existing_records(db_path, dry_run=False):
    """Update existing records to have version = 1."""
    print(f"\nUpdating existing records...")

    if dry_run:
        print("DRY RUN - Would update existing records to version = 1")
        return True

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Update workspaces records
        cursor.execute("UPDATE workspaces SET version = 1 WHERE version IS NULL OR version = 0")
        workspaces_updated = cursor.rowcount
        print(f"   Updated {workspaces_updated} workspace records")

        # Update permissions records
        cursor.execute("UPDATE permissions SET version = 1 WHERE version IS NULL OR version = 0")
        permissions_updated = cursor.rowcount
        print(f"   Updated {permissions_updated} permission records")

        conn.commit()
        print("Record updates completed")
        return True

    except sqlite3.Error as e:
        print(f"Error updating records: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Add version columns to database tables')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    parser.add_argument('--db-path', type=str,
                       help='Override database path')

    args = parser.parse_args()

    try:
        # Get database path
        if args.db_path:
            db_path = args.db_path
        else:
            db_path = get_db_path()

        # Convert to absolute path
        db_path = os.path.abspath(db_path)

        # Run migration
        success = add_version_columns(db_path, dry_run=args.dry_run)

        if success and not args.dry_run:
            # Update existing records
            update_existing_records(db_path, dry_run=args.dry_run)

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()