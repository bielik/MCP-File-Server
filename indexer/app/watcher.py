"""
File Watcher with Stability Checks for MCP KnowledgeExplorer Phase 4A

This module provides intelligent file system monitoring with stability gates,
debouncing, and discovery epoch management to prevent duplicate jobs.
"""

import os
import time
import logging
import hashlib
import threading
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, FileMovedEvent

# Import database components
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend/app'))

from models.indexing import IndexedFile, ControlSetting
from database import get_db, initialize_database
from app.queue import JobQueueManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class FileStabilityTracker:
    """
    Tracks file stability to ensure files are only processed when stable.

    This prevents processing files that are still being written or modified.
    """

    def __init__(self, stability_checks: int = 3, debounce_seconds: float = 2.0):
        """
        Initialize stability tracker.

        Args:
            stability_checks: Number of consecutive stability checks required
            debounce_seconds: Time to wait between stability checks
        """
        self.stability_checks = stability_checks
        self.debounce_seconds = debounce_seconds
        self.pending_files: Dict[str, Dict] = {}  # path -> {last_check, checks_passed, size, mtime}

    def add_file(self, file_path: str) -> None:
        """
        Add a file to stability tracking.

        Args:
            file_path: Path to the file
        """
        try:
            stat = os.stat(file_path)
            self.pending_files[file_path] = {
                'last_check': time.time(),
                'checks_passed': 0,
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'first_seen': time.time()
            }
            logger.debug(f"Added file to stability tracking: {file_path}")
        except OSError as e:
            logger.warning(f"Could not track file {file_path}: {e}")

    def check_stable_files(self) -> Set[str]:
        """
        Check for files that have become stable.

        Returns:
            Set of file paths that are now stable
        """
        stable_files = set()
        current_time = time.time()
        to_remove = []

        for file_path, info in self.pending_files.items():
            # Check if enough time has passed for next stability check
            if current_time - info['last_check'] < self.debounce_seconds:
                continue

            try:
                # Check if file still exists
                if not os.path.exists(file_path):
                    logger.debug(f"File no longer exists: {file_path}")
                    to_remove.append(file_path)
                    continue

                stat = os.stat(file_path)
                current_size = stat.st_size
                current_mtime = stat.st_mtime

                # Check if file has changed
                if current_size != info['size'] or current_mtime != info['mtime']:
                    # File changed, reset stability tracking
                    info['size'] = current_size
                    info['mtime'] = current_mtime
                    info['checks_passed'] = 0
                    logger.debug(f"File changed, resetting stability: {file_path}")
                else:
                    # File is stable for this check
                    info['checks_passed'] += 1
                    logger.debug(f"File stable check {info['checks_passed']}/{self.stability_checks}: {file_path}")

                info['last_check'] = current_time

                # Check if file has passed all stability checks
                if info['checks_passed'] >= self.stability_checks:
                    stable_files.add(file_path)
                    to_remove.append(file_path)

            except OSError as e:
                logger.warning(f"Error checking file stability {file_path}: {e}")
                to_remove.append(file_path)

        # Remove files that are stable or had errors
        for file_path in to_remove:
            self.pending_files.pop(file_path, None)

        if stable_files:
            logger.info(f"Found {len(stable_files)} stable files")

        return stable_files

    def remove_file(self, file_path: str) -> None:
        """
        Remove a file from stability tracking.

        Args:
            file_path: Path to the file
        """
        self.pending_files.pop(file_path, None)

    def get_pending_count(self) -> int:
        """
        Get number of files pending stability checks.

        Returns:
            Number of pending files
        """
        return len(self.pending_files)


class IndexerFileSystemEventHandler(FileSystemEventHandler):
    """
    Handles file system events for the indexer service.

    This handler processes file creation, modification, deletion, and move events
    with proper debouncing and stability checking.
    """

    def __init__(self, source_path: str, queue_manager: JobQueueManager,
                 stability_tracker: FileStabilityTracker, activity_callback=None):
        """
        Initialize event handler.

        Args:
            source_path: Root path being monitored
            queue_manager: Job queue manager for creating indexing jobs
            stability_tracker: File stability tracker
            activity_callback: Optional callback to call when activity occurs
        """
        super().__init__()
        self.source_path = Path(source_path).resolve()
        self.queue_manager = queue_manager
        self.stability_tracker = stability_tracker
        self.activity_callback = activity_callback
        self.discovery_epoch = int(time.time())

        # File extensions to ignore
        self.ignored_extensions = {
            '.tmp', '.temp', '.lock', '.swp', '.~',
            '.DS_Store', 'Thumbs.db'
        }

        # Patterns to ignore
        self.ignored_patterns = {
            '__pycache__', '.git', '.svn', '.hg',
            'node_modules', '.venv', 'venv'
        }

        logger.info(f"File system event handler initialized for: {self.source_path}")

    def should_ignore_path(self, file_path: str) -> bool:
        """
        Check if a file path should be ignored.

        Args:
            file_path: Path to check

        Returns:
            True if the path should be ignored
        """
        path = Path(file_path)

        # Check file extension
        if path.suffix.lower() in self.ignored_extensions:
            return True

        # Check path components for ignored patterns
        for part in path.parts:
            if part in self.ignored_patterns:
                return True

        # Check if it's a symlink pointing outside the source directory
        try:
            if path.is_symlink():
                resolved_path = path.resolve()
                if not self._is_within_source(resolved_path):
                    logger.debug(f"Ignoring symlink outside source: {file_path}")
                    return True
        except (OSError, RuntimeError):
            # Broken symlink or resolution error
            logger.debug(f"Ignoring broken symlink: {file_path}")
            return True

        return False

    def _is_within_source(self, path: Path) -> bool:
        """
        Check if a path is within the source directory.

        Args:
            path: Path to check

        Returns:
            True if path is within source directory
        """
        try:
            path.relative_to(self.source_path)
            return True
        except ValueError:
            return False

    def _get_relative_path(self, file_path: str) -> str:
        """
        Get path relative to source directory.

        Args:
            file_path: Absolute file path

        Returns:
            Relative path from source directory
        """
        return str(Path(file_path).relative_to(self.source_path))

    def on_created(self, event):
        """Handle file creation events."""
        logger.info(f"[EVENT] File created: {event.src_path} (is_directory: {event.is_directory})")
        if not event.is_directory and not self.should_ignore_path(event.src_path):
            logger.info(f"File created: {event.src_path}")
            self.stability_tracker.add_file(event.src_path)
            if self.activity_callback:
                self.activity_callback()

    def on_modified(self, event):
        """Handle file modification events."""
        logger.info(f"[EVENT] File modified: {event.src_path} (is_directory: {event.is_directory})")
        if not event.is_directory and not self.should_ignore_path(event.src_path):
            logger.info(f"File modified: {event.src_path}")
            self.stability_tracker.add_file(event.src_path)
            if self.activity_callback:
                self.activity_callback()

    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            relative_path = self._get_relative_path(event.src_path)
            logger.debug(f"File deleted: {relative_path}")

            # Remove from stability tracking
            self.stability_tracker.remove_file(event.src_path)

            # Mark file as deleted in database
            self._mark_file_deleted(relative_path)

    def on_moved(self, event):
        """Handle file move/rename events."""
        if not event.is_directory:
            old_relative_path = self._get_relative_path(event.src_path)
            new_relative_path = self._get_relative_path(event.dest_path)

            logger.debug(f"File moved: {old_relative_path} -> {new_relative_path}")

            # Remove from stability tracking for old path
            self.stability_tracker.remove_file(event.src_path)

            # Handle the move in database
            self._handle_file_move(old_relative_path, new_relative_path)

            # Add new path to stability tracking if not ignored
            if not self.should_ignore_path(event.dest_path):
                self.stability_tracker.add_file(event.dest_path)

    def _mark_file_deleted(self, relative_path: str) -> None:
        """
        Mark a file as deleted in the database.

        Args:
            relative_path: Relative path of the deleted file
        """
        try:
            with next(get_db()) as session:
                file_obj = session.query(IndexedFile).filter(
                    IndexedFile.path == relative_path
                ).first()

                if file_obj:
                    # Remove the file record
                    session.delete(file_obj)
                    session.commit()
                    logger.info(f"Removed deleted file from database: {relative_path}")

        except Exception as e:
            logger.error(f"Failed to mark file as deleted {relative_path}: {e}")

    def _handle_file_move(self, old_path: str, new_path: str) -> None:
        """
        Handle file move/rename in the database.

        Args:
            old_path: Old relative path
            new_path: New relative path
        """
        try:
            with next(get_db()) as session:
                file_obj = session.query(IndexedFile).filter(
                    IndexedFile.path == old_path
                ).first()

                if file_obj:
                    # Update path while preserving doc_id and other metadata
                    file_obj.path = new_path
                    # Mark as needing reindexing since path changed
                    file_obj.is_indexed = False
                    session.commit()
                    logger.info(f"Updated file path in database: {old_path} -> {new_path}")

        except Exception as e:
            logger.error(f"Failed to handle file move {old_path} -> {new_path}: {e}")


class FileWatcher:
    """
    Main file watcher service with intelligent monitoring and job creation.

    This class coordinates file system monitoring, stability checking,
    and job queue management for the indexing service.
    """

    def __init__(self, source_path: str, config):
        """
        Initialize file watcher.

        Args:
            source_path: Root directory to monitor
            config: Configuration object with watcher settings
        """
        self.source_path = Path(source_path).resolve()
        self.config = config
        self._last_activity = None  # Track last activity for monitoring
        self._polling_timer = None  # Timer for polling fallback
        self._file_mtimes = {}  # Cache for file modification times

        # Initialize components
        self.queue_manager = JobQueueManager()
        self.stability_tracker = FileStabilityTracker(
            stability_checks=config.WATCHER_STABILITY_CHECKS,
            debounce_seconds=config.WATCHER_DEBOUNCE_SECONDS
        )

        self.event_handler = IndexerFileSystemEventHandler(
            source_path=str(self.source_path),
            queue_manager=self.queue_manager,
            stability_tracker=self.stability_tracker,
            activity_callback=self._update_activity  # Pass callback for activity tracking
        )

        self.observer = Observer()
        self.is_running = False

        logger.info(f"FileWatcher initialized for: {self.source_path}")

    def start(self) -> None:
        """Start the file watcher."""
        try:
            # Ensure database is initialized
            initialize_database()

            # Perform initial discovery
            self._initial_discovery()

            # Start file system observer
            self.observer.schedule(
                self.event_handler,
                str(self.source_path),
                recursive=True
            )
            self.observer.start()
            self.is_running = True

            # Start polling fallback for Windows Docker environments
            # This provides a backup mechanism when file system events don't propagate properly
            self._start_polling_fallback()

            logger.info("File watcher started (with polling fallback)")

        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            raise

    def stop(self) -> None:
        """Stop the file watcher."""
        if self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.info("File watcher stopped")

    def process_stable_files(self) -> int:
        """
        Process files that have become stable.

        Returns:
            Number of stable files processed
        """
        # Check maintenance mode before processing
        try:
            with next(get_db()) as session:
                # Import here to avoid circular dependency
                try:
                    from models.reindex import SystemFlag
                    if SystemFlag.is_maintenance_mode(session):
                        logger.debug("System is in maintenance mode, skipping file processing")
                        return 0
                except Exception:
                    # Continue if can't check maintenance mode
                    pass
        except Exception:
            pass

        stable_files = self.stability_tracker.check_stable_files()
        processed_count = 0

        for file_path in stable_files:
            try:
                relative_path = str(Path(file_path).relative_to(self.source_path))
                if self._create_or_update_file_record(file_path, relative_path):
                    processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process stable file {file_path}: {e}")

        return processed_count

    def _initial_discovery(self) -> None:
        """
        Perform initial discovery of all files in the source directory.

        This creates database records for all existing files and uses
        a discovery epoch to prevent duplicate job creation.
        """
        logger.info("Starting initial file discovery")

        try:
            with next(get_db()) as session:
                # Update discovery epoch
                current_epoch = int(time.time())
                ControlSetting.set_setting(
                    session, "discovery_epoch", current_epoch,
                    "integer", "Current file discovery epoch"
                )

                discovered_count = 0
                for file_path in self._scan_directory(self.source_path):
                    try:
                        relative_path = str(file_path.relative_to(self.source_path))

                        # Initialize polling cache
                        try:
                            stat = os.stat(file_path)
                            self._file_mtimes[str(file_path)] = {
                                'mtime': stat.st_mtime,  # Keep float for polling comparison
                                'mtime_ns': stat.st_mtime_ns,  # Add nanosecond precision for database
                                'size': stat.st_size
                            }
                        except OSError:
                            pass

                        if self._create_or_update_file_record(str(file_path), relative_path):
                            discovered_count += 1

                        # Progress logging for large directories
                        if discovered_count % 1000 == 0:
                            logger.info(f"Discovered {discovered_count} files...")

                    except Exception as e:
                        logger.warning(f"Failed to process file {file_path}: {e}")

                logger.info(f"Initial discovery complete: {discovered_count} files")

        except Exception as e:
            logger.error(f"Initial discovery failed: {e}")
            raise

    def _scan_directory(self, directory: Path):
        """
        Recursively scan directory for files.

        Args:
            directory: Directory to scan

        Yields:
            Path objects for discovered files
        """
        try:
            logger.debug(f"Scanning directory: {directory}")
            items = list(directory.iterdir())
            logger.debug(f"Found {len(items)} items in {directory}")

            for item in items:
                logger.debug(f"Processing item: {item}, is_file: {item.is_file()}, is_dir: {item.is_dir()}")
                if item.is_file():
                    should_ignore = self.event_handler.should_ignore_path(str(item))
                    logger.debug(f"File {item} should_ignore: {should_ignore}")
                    if not should_ignore:
                        logger.info(f"Yielding file: {item}")
                        yield item
                elif item.is_dir():
                    should_ignore = self.event_handler.should_ignore_path(str(item))
                    logger.debug(f"Directory {item} should_ignore: {should_ignore}")
                    if not should_ignore:
                        logger.debug(f"Recursing into directory: {item}")
                        yield from self._scan_directory(item)
        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot access directory {directory}: {e}")

    def _create_or_update_file_record(self, file_path: str, relative_path: str) -> bool:
        """
        Create or update a file record in the database.

        Args:
            file_path: Absolute file path
            relative_path: Relative file path

        Returns:
            True if a job was created or file was updated
        """
        try:
            logger.debug(f"Processing file record for: {relative_path}")
            stat = os.stat(file_path)
            current_mtime = int(stat.st_mtime_ns)  # Use nanosecond precision instead of seconds
            current_size = stat.st_size

            with next(get_db()) as session:
                # Check if file already exists
                existing_file = session.query(IndexedFile).filter(
                    IndexedFile.path == relative_path
                ).first()

                logger.debug(f"File {relative_path} exists in DB: {existing_file is not None}")

                if existing_file:
                    # Check if file needs reindexing
                    needs_reindex = existing_file.needs_reindexing(current_mtime, current_size)
                    logger.debug(f"File {relative_path} needs reindexing: {needs_reindex}")

                    if needs_reindex:
                        logger.debug(f"File needs reindexing: {relative_path}")

                        # Update file metadata
                        existing_file.mtime_epoch = current_mtime
                        existing_file.size_bytes = current_size
                        existing_file.is_indexed = False

                        # CRITICAL FIX: Ensure metadata updates are committed even if job creation fails
                        session.commit()

                        # Create indexing job
                        job = self.queue_manager.create_job(session, existing_file.id, "reindex_file")
                        if job:
                            logger.debug(f"Created reindexing job for: {relative_path}")
                            return True
                        else:
                            logger.debug(f"Job creation failed for {relative_path}, but metadata updated")
                            return True  # Metadata was still updated successfully
                    else:
                        logger.debug(f"File {relative_path} already up-to-date, skipping")

                else:
                    # Create new file record
                    is_text = self._is_text_file(relative_path)
                    new_file = IndexedFile(
                        path=relative_path,
                        size_bytes=current_size,
                        mtime_epoch=current_mtime,
                        is_text=is_text
                    )
                    session.add(new_file)
                    session.flush()  # Get the ID

                    # CRITICAL FIX: Ensure new file record is committed even if job creation fails
                    session.commit()

                    # Create indexing job
                    job = self.queue_manager.create_job(session, new_file.id, "index_file")
                    if job:
                        logger.debug(f"Created indexing job for new file: {relative_path}")
                        return True
                    else:
                        logger.debug(f"Job creation failed for new file {relative_path}, but file record created")
                        return True  # File record was still created successfully

                return False

        except Exception as e:
            logger.error(f"Failed to create/update file record {relative_path}: {e}")
            return False

    def _start_polling_fallback(self) -> None:
        """Start polling fallback mechanism for Windows Docker environments."""
        polling_interval = 30  # 30 seconds
        logger.info(f"Starting polling fallback mechanism (interval: {polling_interval}s)")

        def polling_loop():
            while self.is_running:
                try:
                    self._poll_for_changes()
                    time.sleep(polling_interval)
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}")
                    time.sleep(polling_interval)

        self._polling_timer = threading.Thread(target=polling_loop, daemon=True)
        self._polling_timer.start()

    def _poll_for_changes(self) -> None:
        """Poll filesystem for changes as a fallback when Observer events don't work."""
        try:
            # Build current file state
            current_files = {}
            for file_path in self._scan_directory(self.source_path):
                try:
                    stat = os.stat(file_path)
                    current_files[str(file_path)] = {
                        'mtime': stat.st_mtime,  # Keep float for polling comparison
                        'mtime_ns': stat.st_mtime_ns,  # Add nanosecond precision for database
                        'size': stat.st_size
                    }
                except OSError:
                    continue

            # Compare with cached state
            changes_detected = 0

            # Check for new or modified files
            for file_path, current_info in current_files.items():
                cached_info = self._file_mtimes.get(file_path)

                # Skip files already in stability tracking
                if file_path in self.stability_tracker.pending_files:
                    logger.debug(f"[POLLING] Skipping file already in stability tracking: {file_path}")
                    continue

                if cached_info is None:
                    # New file
                    logger.info(f"[POLLING] New file detected: {file_path}")
                    self._handle_file_change(file_path)
                    changes_detected += 1
                elif (cached_info['mtime'] != current_info['mtime'] or
                      cached_info['size'] != current_info['size']):
                    # Modified file
                    logger.info(f"[POLLING] Modified file detected: {file_path}")
                    self._handle_file_change(file_path)
                    changes_detected += 1

            # CRITICAL FIX: Add rename detection before treating files as deleted
            # This prevents duplicate database entries when files are renamed
            disappeared_files = {}
            appeared_files = {}

            # Collect disappeared files (files that were cached but not in current scan)
            for cached_path in list(self._file_mtimes.keys()):
                if cached_path not in current_files:
                    cached_info = self._file_mtimes[cached_path]
                    disappeared_files[cached_path] = cached_info

            # Collect newly appeared files
            for file_path, current_info in current_files.items():
                if file_path not in self._file_mtimes:
                    appeared_files[file_path] = current_info

            # Try to match disappeared files with appeared files by size/mtime
            # This detects renames and prevents duplicate database entries
            matched_renames = []
            for old_path, old_info in disappeared_files.items():
                for new_path, new_info in appeared_files.items():
                    # Match by size and mtime (both float and nanosecond precision)
                    if (old_info['size'] == new_info['size'] and
                        old_info['mtime'] == new_info['mtime']):
                        logger.info(f"[POLLING] Rename detected: {old_path} → {new_path}")
                        self._handle_file_rename(old_path, new_path)
                        matched_renames.append((old_path, new_path))
                        changes_detected += 1
                        break

            # Remove matched files from appeared/disappeared lists
            for old_path, new_path in matched_renames:
                disappeared_files.pop(old_path, None)
                appeared_files.pop(new_path, None)

            # Handle remaining disappeared files as true deletions
            for cached_path in disappeared_files.keys():
                logger.info(f"[POLLING] Deleted file detected: {cached_path}")
                self._handle_file_deletion(cached_path)
                changes_detected += 1

            # Handle remaining appeared files as new files (already handled above in new file detection)

            # Update cache
            self._file_mtimes = current_files

            if changes_detected > 0:
                logger.info(f"[POLLING] Detected {changes_detected} file changes")
                self._last_activity = time.time()

        except Exception as e:
            logger.error(f"Error during polling: {e}")

    def _handle_file_change(self, file_path: str) -> None:
        """Handle file change detected by polling."""
        try:
            relative_path = str(Path(file_path).relative_to(self.source_path))
            if not self.event_handler.should_ignore_path(file_path):
                self.stability_tracker.add_file(file_path)
        except Exception as e:
            logger.error(f"Error handling file change {file_path}: {e}")

    def _handle_file_rename(self, old_path: str, new_path: str) -> None:
        """
        Handle file rename detected by polling mechanism.

        CRITICAL FIX: This method updates the existing database record's path instead of
        creating a duplicate entry, preserving the doc_id and associated chunks.

        Args:
            old_path: Previous file path
            new_path: New file path
        """
        try:
            old_relative = str(Path(old_path).relative_to(self.source_path))
            new_relative = str(Path(new_path).relative_to(self.source_path))

            logger.info(f"Processing rename: {old_relative} → {new_relative}")

            with next(get_db()) as session:
                # Find existing record by old path
                existing_file = session.query(IndexedFile).filter(
                    IndexedFile.path == old_relative
                ).first()

                if existing_file:
                    # Update path to new location, preserving all other data
                    existing_file.path = new_relative
                    # Mark for reindexing since path changed
                    existing_file.is_indexed = False

                    # Commit the path update
                    session.commit()

                    logger.info(f"Updated database record path: {old_relative} → {new_relative}")

                    # Create reindex job for the renamed file
                    reindex_job = self.queue_manager.create_job(session, existing_file.id, "reindex_file")
                    if reindex_job:
                        logger.info(f"Created reindex job for renamed file: {new_relative}")
                else:
                    logger.warning(f"No database record found for renamed file: {old_relative}")
                    # Treat as new file if no existing record
                    self._handle_file_change(new_path)

        except Exception as e:
            logger.error(f"Error handling file rename {old_path} → {new_path}: {e}")

    def _handle_file_deletion(self, file_path: str) -> None:
        """Handle file deletion detected by polling."""
        try:
            relative_path = str(Path(file_path).relative_to(self.source_path))

            # Mark file as deleted in database
            with next(get_db()) as session:
                existing_file = session.query(IndexedFile).filter(
                    IndexedFile.path == relative_path
                ).first()

                if existing_file:
                    # For now, hard delete the record and its chunks
                    # TODO: Consider soft delete with deleted_at timestamp
                    session.delete(existing_file)
                    session.commit()
                    logger.info(f"Deleted database record for: {relative_path}")

            # Remove from stability tracking
            self.stability_tracker.remove_file(file_path)
            # Remove from cache
            self._file_mtimes.pop(file_path, None)

        except Exception as e:
            logger.error(f"Error handling file deletion {file_path}: {e}")

    def _is_text_file(self, file_path: str) -> bool:
        """
        Determine if a file is likely to be a text file based on extension.

        Args:
            file_path: Path to the file

        Returns:
            True if the file is likely to be text
        """
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
        import os
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

    def _update_activity(self) -> None:
        """Update last activity timestamp for monitoring."""
        self._last_activity = time.time()

    def get_status(self) -> Dict[str, any]:
        """
        Get watcher status information.

        Returns:
            Dictionary with status information
        """
        # Get pending files count for monitoring
        pending_files = self.stability_tracker.get_pending_count() if self.stability_tracker else 0

        # Calculate total files being monitored (pending + recently processed)
        files_monitored = pending_files

        # Get last activity timestamp
        last_activity = None
        if hasattr(self, '_last_activity'):
            last_activity = self._last_activity
        elif pending_files > 0:
            last_activity = time.time()  # If files are pending, activity is current

        return {
            "is_running": self.is_running,
            "source_path": str(self.source_path),
            "pending_stability_checks": pending_files,
            "observer_alive": self.observer.is_alive() if self.observer else False,
            "files_monitored": files_monitored,
            "last_activity": last_activity
        }