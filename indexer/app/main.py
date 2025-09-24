"""
Main Indexer Service for MCP KnowledgeExplorer Phase 4A

This is the main entry point for the indexer service, which handles
background file monitoring, job processing, and system health monitoring.
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Import configuration and components
sys.path.insert(0, '/backend/app')  # Add backend/app first so relative imports work
sys.path.append('/app')  # Add app root to path
sys.path.append('/config')  # Add config directory to path

# Import proper configuration from config directory
from env_config import get_config, Phase4AConfig

# Import database bootstrap from backend (shared with backend container)
from db.bootstrap import DatabaseBootstrap, create_session_factory
from models.indexing import IndexedFile, IndexJob, ControlSetting

# Global database components
engine = None
SessionLocal = None

def initialize_database():
    """Initialize database using proper DatabaseBootstrap with WAL mode and concurrency settings."""
    global engine, SessionLocal

    try:
        config = get_config()

        # Standardized database URL construction (consistent with backend)
        from pathlib import Path
        import os

        # In Docker containers, always use /data regardless of DATABASE_PATH env var
        if os.path.exists('/data'):
            # Running in Docker container
            database_path = '/data'
        else:
            # Running locally
            database_path = config.DATABASE_PATH

        db_path = Path(database_path)

        # If it's a directory path, append database.db
        if not str(db_path).endswith('.db'):
            db_path = db_path / 'database.db'

        database_url = f"sqlite:///{db_path}"

        logger.info(f"Indexer database URL: {database_url}")

        # Use DatabaseBootstrap for proper SQLite configuration
        engine = DatabaseBootstrap.bootstrap_database(
            database_url=database_url
        )

        SessionLocal = create_session_factory(engine)

        # Ensure Phase 4A schema is created by importing and creating all tables
        try:
            # Import all models to register them with SQLAlchemy metadata
            import sys
            sys.path.insert(0, '/backend/app')
            from database import Base

            # Create all tables (will only create missing ones)
            Base.metadata.create_all(bind=engine)
            logger.info("Phase 4A database schema verified/created")

        except Exception as e:
            logger.warning(f"Schema creation warning (may already exist): {e}")

        logger.info("Database initialized with WAL mode and concurrency settings")

        # Log database info to verify proper configuration
        db_info = DatabaseBootstrap.get_database_info(engine)
        logger.info(f"Database configuration: {db_info}")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def get_db():
    """FastAPI dependency to get database session with proper bootstrap."""
    if SessionLocal is None:
        initialize_database()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from app.queue import JobQueueManager, JobProcessor
from app.watcher import FileWatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndexerService:
    """
    Main indexer service that coordinates file watching and job processing.

    This service runs the file watcher, processes indexing jobs, and provides
    health monitoring and control endpoints.
    """

    def __init__(self, config: Phase4AConfig):
        """
        Initialize the indexer service.

        Args:
            config: Configuration object
        """
        self.config = config
        self.is_running = False
        self.should_stop = False

        # Initialize components
        self.queue_manager = JobQueueManager()
        self.job_processor = JobProcessor(self.queue_manager)
        self.file_watcher: Optional[FileWatcher] = None

        # Performance tracking
        self.stats = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "last_activity": None,
            "start_time": None
        }

        logger.info("IndexerService initialized")

    async def start(self) -> None:
        """Start the indexer service."""
        try:
            logger.info("Starting indexer service...")
            self.stats["start_time"] = time.time()

            # Initialize database
            initialize_database()

            # Start file watcher with container-aware path detection
            if self.config.SHARED_FS_PATH:
                # Detect container environment and use correct path
                import os
                if os.path.exists('/source'):
                    watch_path = '/source'  # Container path
                    logger.info("Using container path /source for file watching")
                else:
                    watch_path = self.config.SHARED_FS_PATH  # Local development
                    logger.info(f"Using local development path: {watch_path}")

                self.file_watcher = FileWatcher(
                    source_path=watch_path,
                    config=self.config
                )
                self.file_watcher.start()
                logger.info(f"File watcher started for: {watch_path}")

            # Perform startup recovery
            await self._startup_recovery()

            self.is_running = True
            logger.info("Indexer service started successfully")

        except Exception as e:
            logger.error(f"Failed to start indexer service: {e}")
            raise

    async def stop(self) -> None:
        """Stop the indexer service."""
        logger.info("Stopping indexer service...")
        self.should_stop = True

        # Stop file watcher
        if self.file_watcher:
            self.file_watcher.stop()

        self.is_running = False
        logger.info("Indexer service stopped")

    async def _startup_recovery(self) -> None:
        """Perform startup recovery operations."""
        try:
            with next(get_db()) as session:
                # Recover stale jobs
                recovered_count = self.queue_manager.recover_stale_jobs(session)
                logger.info(f"Recovered {recovered_count} stale jobs on startup")

                # Clean up old jobs if configured
                if hasattr(self.config, 'JOB_RETENTION_DAYS'):
                    cleaned_count = self.queue_manager.cleanup_old_jobs(
                        session, self.config.JOB_RETENTION_DAYS
                    )
                    logger.info(f"Cleaned up {cleaned_count} old jobs on startup")

        except Exception as e:
            logger.error(f"Startup recovery failed: {e}")

    async def run_main_loop(self) -> None:
        """
        Main processing loop for the indexer service.

        This loop handles job processing, file stability checks, and
        control setting monitoring.
        """
        logger.info("Starting main indexer loop")

        while not self.should_stop:
            try:
                # Check if indexing is paused
                with next(get_db()) as session:
                    if self.queue_manager.is_paused(session):
                        logger.debug("Indexing is paused, sleeping...")
                        await asyncio.sleep(self.config.INDEXER_POLL_INTERVAL)
                        continue

                # Process stable files from watcher
                if self.file_watcher:
                    stable_count = self.file_watcher.process_stable_files()
                    if stable_count > 0:
                        logger.debug(f"Processed {stable_count} stable files")

                # Process jobs from queue
                jobs_processed = await self._process_jobs_batch()

                # Update activity tracking
                if jobs_processed > 0:
                    self.stats["last_activity"] = time.time()
                    self.stats["jobs_processed"] += jobs_processed

                # Sleep if no work was done
                if jobs_processed == 0:
                    await asyncio.sleep(self.config.INDEXER_POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(self.config.INDEXER_POLL_INTERVAL * 2)  # Back off on errors

        logger.info("Main indexer loop stopped")

    async def _process_jobs_batch(self) -> int:
        """
        Process a batch of jobs from the queue.

        Returns:
            Number of jobs processed
        """
        jobs_processed = 0
        max_batch_size = min(self.config.INDEXER_BATCH_SIZE, 10)  # Cap batch size

        try:
            with next(get_db()) as session:
                for _ in range(max_batch_size):
                    # Check if we should stop
                    if self.should_stop:
                        break

                    # Check throttling
                    throttle_pct = self.queue_manager.get_throttle_percentage(session)
                    if throttle_pct > 0:
                        # Apply CPU throttling by sleeping
                        sleep_time = (throttle_pct / 100.0) * 0.1  # Up to 100ms delay
                        await asyncio.sleep(sleep_time)

                    # Claim a job
                    job = self.queue_manager.claim_job(session)
                    if not job:
                        break  # No more jobs available

                    # Process the job
                    success = self.job_processor.process_job(session, job)
                    if success:
                        jobs_processed += 1
                    else:
                        self.stats["jobs_failed"] += 1

        except Exception as e:
            logger.error(f"Error processing jobs batch: {e}")

        return jobs_processed

    def get_status(self) -> dict:
        """
        Get comprehensive service status.

        Returns:
            Status information dictionary
        """
        status = {
            "service": {
                "is_running": self.is_running,
                "should_stop": self.should_stop,
                "uptime_seconds": time.time() - self.stats["start_time"] if self.stats["start_time"] else 0,
                "last_activity": self.stats["last_activity"]
            },
            "stats": self.stats.copy(),
            "config": {
                "batch_size": self.config.INDEXER_BATCH_SIZE,
                "max_workers": self.config.INDEXER_MAX_WORKERS,
                "poll_interval": self.config.INDEXER_POLL_INTERVAL,
                "source_path": self.config.SHARED_FS_PATH
            }
        }

        # Add file watcher status
        if self.file_watcher:
            status["file_watcher"] = self.file_watcher.get_status()

        # Add queue statistics
        try:
            with next(get_db()) as session:
                status["queue"] = self.queue_manager.get_queue_stats(session)
        except Exception as e:
            status["queue"] = {"error": str(e)}

        return status


# Global service instance
indexer_service: Optional[IndexerService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    global indexer_service

    # Startup
    try:
        config = get_config()
        indexer_service = IndexerService(config)
        await indexer_service.start()

        # Start the main processing loop in background
        main_loop_task = asyncio.create_task(indexer_service.run_main_loop())

        yield

    except Exception as e:
        logger.error(f"Failed to start indexer service: {e}")
        raise

    finally:
        # Shutdown
        if indexer_service:
            await indexer_service.stop()
            # Cancel the main loop task
            if 'main_loop_task' in locals():
                main_loop_task.cancel()
                try:
                    await main_loop_task
                except asyncio.CancelledError:
                    pass


# FastAPI application with health endpoints
app = FastAPI(
    title="MCP KnowledgeExplorer Indexer Service",
    description="Background indexing service for Phase 4A",
    version="4.0.0",
    lifespan=lifespan
)


@app.get("/live")
async def liveness_probe():
    """
    Liveness probe endpoint.

    Returns:
        Simple OK response to indicate the service is running
    """
    return {"status": "ok", "timestamp": time.time()}


@app.get("/ready")
async def readiness_probe():
    """
    Readiness probe endpoint.

    Returns:
        Detailed status including database connectivity and service readiness
    """
    try:
        # Check database connectivity
        with next(get_db()) as session:
            from sqlalchemy import text
            session.execute(text("SELECT 1")).fetchone()

        # Check service status
        if not indexer_service or not indexer_service.is_running:
            raise HTTPException(status_code=503, detail="Service not ready")

        return {
            "status": "ready",
            "timestamp": time.time(),
            "database": "connected",
            "service": "running"
        }

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service not ready: {e}")


@app.get("/status")
async def get_service_status():
    """
    Get comprehensive service status.

    Returns:
        Detailed status information about the indexer service
    """
    try:
        if not indexer_service:
            raise HTTPException(status_code=503, detail="Service not initialized")

        status = indexer_service.get_status()
        return JSONResponse(content=status)

    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


@app.post("/control/pause")
async def pause_indexing():
    """
    Pause the indexing process.

    Returns:
        Confirmation of pause action
    """
    try:
        with next(get_db()) as session:
            ControlSetting.set_setting(session, "indexer_paused", "true", "boolean")

        logger.info("Indexing paused via API")
        return {"status": "paused", "timestamp": time.time()}

    except Exception as e:
        logger.error(f"Failed to pause indexing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause: {e}")


@app.post("/control/resume")
async def resume_indexing():
    """
    Resume the indexing process.

    Returns:
        Confirmation of resume action
    """
    try:
        with next(get_db()) as session:
            ControlSetting.set_setting(session, "indexer_paused", "false", "boolean")

        logger.info("Indexing resumed via API")
        return {"status": "resumed", "timestamp": time.time()}

    except Exception as e:
        logger.error(f"Failed to resume indexing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume: {e}")


@app.post("/control/throttle/{percentage}")
async def set_throttle(percentage: int):
    """
    Set CPU throttling percentage.

    Args:
        percentage: Throttling percentage (0-100)

    Returns:
        Confirmation of throttle setting
    """
    try:
        if not 0 <= percentage <= 100:
            raise HTTPException(status_code=400, detail="Percentage must be between 0 and 100")

        with next(get_db()) as session:
            ControlSetting.set_setting(session, "throttle_pct", str(percentage), "integer")

        logger.info(f"CPU throttling set to {percentage}% via API")
        return {"status": "throttle_set", "percentage": percentage, "timestamp": time.time()}

    except Exception as e:
        logger.error(f"Failed to set throttle: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set throttle: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    if indexer_service:
        indexer_service.should_stop = True


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    import uvicorn

    # Load configuration
    try:
        config = get_config()
        logger.info("Configuration loaded successfully")

        # Log hardware information
        hw_info = config.get_hardware_info()
        logger.info(f"Hardware info: {hw_info}")

        # Log any configuration warnings
        warnings = config.validate_startup_requirements()
        for warning in warnings:
            logger.warning(warning)

    except Exception as e:
        logger.error(f"Configuration failed: {e}")
        sys.exit(1)

    # Start the service
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=config.INDEXER_PORT,
            reload=False,  # Disable reload in production
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start indexer service: {e}")
        sys.exit(1)