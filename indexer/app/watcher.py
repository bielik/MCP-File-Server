"""
File Watcher with Stability Checks for MCP KnowledgeExplorer Phase 4A

This module provides intelligent file system monitoring with stability gates,
debouncing, and discovery epoch management to prevent duplicate jobs.
"""

import os
import time
import logging
import hashlib
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
                 stability_tracker: FileStabilityTracker):
        """
        Initialize event handler.

        Args:
            source_path: Root path being monitored
            queue_manager: Job queue manager for creating indexing jobs
            stability_tracker: File stability tracker
        """
        super().__init__()
        self.source_path = Path(source_path).resolve()
        self.queue_manager = queue_manager
        self.stability_tracker = stability_tracker
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
        if not event.is_directory and not self.should_ignore_path(event.src_path):
            logger.debug(f"File created: {event.src_path}")
            self.stability_tracker.add_file(event.src_path)

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and not self.should_ignore_path(event.src_path):
            logger.debug(f"File modified: {event.src_path}")
            self.stability_tracker.add_file(event.src_path)

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

        # Initialize components
        self.queue_manager = JobQueueManager()
        self.stability_tracker = FileStabilityTracker(
            stability_checks=config.WATCHER_STABILITY_CHECKS,
            debounce_seconds=config.WATCHER_DEBOUNCE_SECONDS
        )

        self.event_handler = IndexerFileSystemEventHandler(
            source_path=str(self.source_path),
            queue_manager=self.queue_manager,
            stability_tracker=self.stability_tracker
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

            logger.info("File watcher started")

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
            for item in directory.iterdir():
                if item.is_file() and not self.event_handler.should_ignore_path(str(item)):
                    yield item
                elif item.is_dir() and not self.event_handler.should_ignore_path(str(item)):
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
            stat = os.stat(file_path)
            current_mtime = int(stat.st_mtime)
            current_size = stat.st_size

            with next(get_db()) as session:
                # Check if file already exists
                existing_file = session.query(IndexedFile).filter(
                    IndexedFile.path == relative_path
                ).first()

                if existing_file:
                    # Check if file needs reindexing
                    if existing_file.needs_reindexing(current_mtime, current_size):
                        logger.debug(f"File needs reindexing: {relative_path}")

                        # Update file metadata
                        existing_file.mtime_epoch = current_mtime
                        existing_file.size_bytes = current_size
                        existing_file.is_indexed = False

                        # Create indexing job
                        job = self.queue_manager.create_job(session, existing_file.id)
                        if job:
                            logger.debug(f"Created reindexing job for: {relative_path}")
                            return True

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

                    # Create indexing job
                    job = self.queue_manager.create_job(session, new_file.id)
                    if job:
                        logger.debug(f"Created indexing job for new file: {relative_path}")
                        return True

                return False

        except Exception as e:
            logger.error(f"Failed to create/update file record {relative_path}: {e}")
            return False

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

    def get_status(self) -> Dict[str, any]:
        """
        Get watcher status information.

        Returns:
            Dictionary with status information
        """
        return {
            "is_running": self.is_running,
            "source_path": str(self.source_path),
            "pending_stability_checks": self.stability_tracker.get_pending_count(),
            "observer_alive": self.observer.is_alive() if self.observer else False
        }