import threading
from sqlalchemy.orm import declarative_base
try:
    from app.db.bootstrap import DatabaseBootstrap, create_session_factory
except ImportError:
    # Handle import from external context (like indexer)
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from db.bootstrap import DatabaseBootstrap, create_session_factory

# Import config to get correct database path
try:
    from app.config import get_config
    config = get_config()
    SQLALCHEMY_DATABASE_URL = config.DATABASE_URL
except ImportError:
    # Handle import from external context (like indexer)
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        from config import get_config
        config = get_config()
        SQLALCHEMY_DATABASE_URL = config.DATABASE_URL
    except ImportError:
        # Final fallback for cases where config isn't available (like migrations)
        SQLALCHEMY_DATABASE_URL = "sqlite:///./data/database.db"

# Thread-safe initialization state
_init_lock = threading.Lock()
_initialized = False

# Use bootstrap module for engine creation with Phase 4A optimizations
engine = None
SessionLocal = None

def initialize_database():
    """
    Initialize database with thread-safe idempotent configuration.

    This function can be called safely from multiple threads/workers.
    Only the first call will perform initialization.
    """
    global engine, SessionLocal, _initialized

    # Double-check pattern for thread safety
    if _initialized and engine is not None and SessionLocal is not None:
        return engine

    with _init_lock:
        # Check again after acquiring lock
        if _initialized and engine is not None and SessionLocal is not None:
            return engine

        if engine is None:
            # Use bootstrap for proper SQLite configuration
            try:
                engine = DatabaseBootstrap.create_engine_with_config(SQLALCHEMY_DATABASE_URL)
                SessionLocal = create_session_factory(engine)
            except Exception as e:
                # Fallback to simple engine creation if bootstrap fails
                print(f"Bootstrap failed, using simple engine: {e}")
                from sqlalchemy import create_engine
                engine = create_engine(
                    SQLALCHEMY_DATABASE_URL,
                    # Add SQLite concurrency settings
                    connect_args={
                        "check_same_thread": False,  # Allow sharing across threads
                        "timeout": 30  # 30 second timeout for locked database
                    }
                )
                SessionLocal = create_session_factory(engine)

            # Create tables
            create_db_and_tables(engine)

        _initialized = True

    return engine

Base = declarative_base()

def create_db_and_tables(engine_param=None):
    """
    Create all database tables.

    Args:
        engine_param: Optional engine parameter for bootstrap process
    """
    # Use provided engine or global engine
    target_engine = engine_param or engine

    # Import all models to ensure they're registered with Base.metadata
    try:
        from app.models import Setting, Workspace, Permission
        # Import Phase 4A models for indexing functionality
        from app.models.indexing import IndexedFile, IndexJob, ControlSetting
    except ImportError as e:
        # In case models aren't available (like during testing)
        print(f"Warning: Could not import all models: {e}")
        pass

    if target_engine:
        try:
            Base.metadata.create_all(bind=target_engine)
        except Exception as e:
            # For now, just log the error and continue - Phase 4A will work without tables initially
            print(f"Warning: Could not create all tables: {e}")
            pass

# Dependency to get a DB session
def get_db():
    """
    FastAPI dependency to get database session.

    Ensures database is initialized before providing session.
    """
    if SessionLocal is None:
        initialize_database()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
