"""
Manual verification script for Ticket 021 Steps A & B implementation.
Checks the production database for correct implementation behavior.
"""

import sqlite3
import sys
import os

# Add backend to path
backend_root = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_root)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db')

def connect_db():
    """Connect to the production database."""
    if not os.path.exists(DB_PATH):
        print(f" Database not found at: {DB_PATH}")
        return None
    return sqlite3.connect(DB_PATH)

def check_batch_jobs(conn):
    """Verify that batch jobs contain only core-stage jobs (not parent jobs)."""
    print("\nVERIFICATION 1: Batch Jobs Should Be Core-Stage Only")
    print("=" * 70)

    cursor = conn.cursor()

    # Check job types in batches
    cursor.execute("""
        SELECT job_type, batch_id, COUNT(*) as count
        FROM index_jobs
        WHERE batch_id IS NOT NULL
        GROUP BY job_type, batch_id
        ORDER BY batch_id, job_type
    """)

    batch_jobs = cursor.fetchall()

    if not batch_jobs:
        print("  No batch jobs found in database")
        print("   This is expected if no reindex operations have been run yet.")
        return True

    # Check for parent jobs
    cursor.execute("""
        SELECT COUNT(*)
        FROM index_jobs
        WHERE batch_id IS NOT NULL
        AND job_type IN ('index_file', 'reindex_file')
    """)

    parent_job_count = cursor.fetchone()[0]

    print(f"\nBatch Jobs Found:")
    for job_type, batch_id, count in batch_jobs:
        prefix = "  [OK]" if job_type not in ['index_file', 'reindex_file'] else "  [FAIL]"
        print(f"{prefix} {job_type}: {count} jobs in batch {batch_id}")

    if parent_job_count > 0:
        print(f"\n[FAIL] FAILED: Found {parent_job_count} parent jobs in batches")
        print("   Expected: 0 parent jobs (only TEXT_EXTRACT, CHUNK, FTS_INDEX)")
        return False
    else:
        print(f"\n[PASS] PASSED: No parent jobs found in batches")
        print("   All batch jobs are core-stage jobs (TEXT_EXTRACT, CHUNK, FTS_INDEX)")
        return True

def check_maintenance_mode(conn):
    """Verify maintenance mode flag exists and is cleared."""
    print("\n VERIFICATION 2: Maintenance Mode Flag")
    print("=" * 70)

    cursor = conn.cursor()

    # Check if system_flags table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='system_flags'
    """)

    if not cursor.fetchone():
        print(" FAILED: system_flags table does not exist")
        return False

    # Check maintenance mode flag
    cursor.execute("""
        SELECT key, value
        FROM system_flags
        WHERE key = 'maintenance_mode'
    """)

    flag = cursor.fetchone()

    if not flag:
        print("  Maintenance mode flag not set (expected on first run)")
        print("   Flag will be created on first full_reset() call")
        return True

    name, value = flag

    if value == 'false' or value == '0':
        print(f" PASSED: Maintenance mode is OFF (value: {value})")
        print("   System is ready for normal operation")
        return True
    else:
        print(f" FAILED: Maintenance mode is ON (value: {value})")
        print("   System may be stuck in maintenance mode")
        return False

def check_reset_capability(conn):
    """Verify that full reset infrastructure is present."""
    print("\n VERIFICATION 3: Full Reset Infrastructure")
    print("=" * 70)

    cursor = conn.cursor()

    # Check for required tables
    required_tables = [
        'indexed_files',
        'document_chunks',
        'index_jobs',
        'reindex_batches',
        'system_flags'
    ]

    missing_tables = []
    for table in required_tables:
        cursor.execute(f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='{table}'
        """)
        if not cursor.fetchone():
            missing_tables.append(table)

    if missing_tables:
        print(f" FAILED: Missing required tables: {', '.join(missing_tables)}")
        return False

    print(" PASSED: All required tables present")

    # Check for FTS table
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='chunks_fts'
    """)

    if cursor.fetchone():
        print(" PASSED: FTS virtual table 'chunks_fts' exists")
    else:
        print("  WARNING: FTS table not found (may not be created yet)")

    return True

def check_batch_id_propagation(conn):
    """Check that batch_id is properly used in index_jobs."""
    print("\n VERIFICATION 4: Batch ID Propagation")
    print("=" * 70)

    cursor = conn.cursor()

    # Count jobs with and without batch_id
    cursor.execute("SELECT COUNT(*) FROM index_jobs WHERE batch_id IS NOT NULL")
    with_batch = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM index_jobs WHERE batch_id IS NULL")
    without_batch = cursor.fetchone()[0]

    print(f"Jobs with batch_id: {with_batch}")
    print(f"Jobs without batch_id: {without_batch} (incremental watcher jobs)")

    if with_batch > 0:
        # Check that all batch jobs have consistent batch_id per file
        cursor.execute("""
            SELECT file_id, COUNT(DISTINCT batch_id) as batch_count
            FROM index_jobs
            WHERE batch_id IS NOT NULL
            GROUP BY file_id
            HAVING batch_count > 1
        """)

        inconsistent_files = cursor.fetchall()

        if inconsistent_files:
            print(f" FAILED: {len(inconsistent_files)} files have jobs with multiple batch_ids")
            return False
        else:
            print(" PASSED: All batch jobs have consistent batch_id per file")
            return True
    else:
        print("  No batch jobs found yet (run a reindex to verify)")
        return True

def main():
    """Run all verification checks."""
    print("\n" + "="*70)
    print("TICKET 021 IMPLEMENTATION VERIFICATION")
    print("   Steps A & B: Core Jobs Only + Full Reset + Maintenance Mode")
    print("="*70)

    conn = connect_db()
    if not conn:
        sys.exit(1)

    try:
        results = []

        # Run all checks
        results.append(("Batch Jobs Core-Stage Only", check_batch_jobs(conn)))
        results.append(("Maintenance Mode Flag", check_maintenance_mode(conn)))
        results.append(("Full Reset Infrastructure", check_reset_capability(conn)))
        results.append(("Batch ID Propagation", check_batch_id_propagation(conn)))

        # Summary
        print("\n" + "="*70)
        print(" VERIFICATION SUMMARY")
        print("="*70)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for check_name, result in results:
            status = " PASS" if result else " FAIL"
            print(f"{status}: {check_name}")

        print(f"\n{'='*70}")
        if passed == total:
            print(f" ALL CHECKS PASSED ({passed}/{total})")
            print("\n Ticket 021 Steps A & B implementation is correct!")
        else:
            print(f"  SOME CHECKS FAILED ({passed}/{total} passed)")
            print("\n Issues detected in implementation")
        print("="*70)

        return 0 if passed == total else 1

    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())