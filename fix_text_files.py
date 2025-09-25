#!/usr/bin/env python3
"""
Fix existing files to properly set is_text flag and create Phase 4B jobs.
"""
import sqlite3
import os

DATABASE_PATH = "C:/Users/MartinBielik/Dev/MCPFileServer/data/database.db"

def is_text_file(file_path: str) -> bool:
    """Determine if a file is likely to be a text file based on extension."""
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.ts', '.json', '.xml', '.html', '.htm', '.css',
        '.scss', '.sass', '.less', '.yaml', '.yml', '.ini', '.cfg', '.conf',
        '.log', '.csv', '.tsv', '.sql', '.sh', '.bat', '.ps1', '.dockerfile',
        '.gitignore', '.gitattributes', '.env', '.properties', '.toml',
        '.rst', '.tex', '.latex', '.bib', '.r', '.rb', '.php', '.java', '.c',
        '.cpp', '.cxx', '.h', '.hpp', '.cs', '.go', '.rs', '.kt', '.swift',
        '.pl', '.pm', '.lua', '.tcl', '.awk', '.sed', '.vim', '.tmux'
    }

    # Get file extension
    _, ext = os.path.splitext(file_path.lower())

    # Check for common text extensions
    if ext in text_extensions:
        return True

    # Check for files without extensions that are often text
    filename = os.path.basename(file_path).lower()
    text_files = {
        'readme', 'license', 'changelog', 'authors', 'contributors',
        'makefile', 'dockerfile', 'vagrantfile', 'procfile'
    }

    if filename in text_files:
        return True

    return False

def fix_existing_files():
    """Fix existing files by updating is_text and creating Phase 4B jobs."""

    if not os.path.exists(DATABASE_PATH):
        print(f"Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Get all files
        cursor.execute("SELECT id, path FROM indexed_files")
        all_files = cursor.fetchall()
        print(f"Found {len(all_files)} total files")

        text_files_updated = 0
        jobs_created = 0

        for file_id, file_path in all_files:
            if is_text_file(file_path):
                # Update is_text flag
                cursor.execute(
                    "UPDATE indexed_files SET is_text = 1 WHERE id = ?",
                    (file_id,)
                )
                text_files_updated += 1

                # Create Phase 4B jobs
                for job_type in ["TEXT_EXTRACT", "CHUNK", "FTS_INDEX"]:
                    # Check if job already exists
                    cursor.execute(
                        "SELECT id FROM index_jobs WHERE file_id = ? AND job_type = ?",
                        (file_id, job_type)
                    )
                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO index_jobs (file_id, job_type, status, job_signature, created_at, retry_count, max_retries)
                            VALUES (?, ?, 'PENDING', ?, strftime('%s', 'now'), 0, 3)
                        """, (file_id, job_type, f"{file_id}_{job_type}"))
                        jobs_created += 1

        conn.commit()
        print(f"Updated {text_files_updated} files to is_text = True")
        print(f"Created {jobs_created} Phase 4B jobs")

        # Show updated stats
        cursor.execute("SELECT COUNT(*) FROM indexed_files WHERE is_text = 1")
        text_count = cursor.fetchone()[0]
        print(f"Total text files now: {text_count}")

        cursor.execute("SELECT job_type, COUNT(*) FROM index_jobs GROUP BY job_type ORDER BY job_type")
        job_counts = cursor.fetchall()
        print(f"\nJob counts after update:")
        for job_type, count in job_counts:
            print(f"  {job_type}: {count}")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_existing_files()