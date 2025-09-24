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
        # Import Phase 4B models for advanced search
        from app.models.indexing import DocumentChunk
    except ImportError as e:
        # In case models aren't available (like during testing)
        print(f"Warning: Could not import all models: {e}")
        pass

    if target_engine:
        try:
            Base.metadata.create_all(bind=target_engine)

            # Create FTS5 virtual table and triggers for Phase 4B
            _create_fts_tables(target_engine)

        except Exception as e:
            # For now, just log the error and continue - Phase 4A will work without tables initially
            print(f"Warning: Could not create all tables: {e}")
            pass


def _create_fts_tables(engine):
    """
    Create FTS5 virtual tables and triggers for Phase 4B search functionality.

    Args:
        engine: SQLAlchemy engine
    """
    from sqlalchemy import text

    try:
        with engine.connect() as connection:
            # Create FTS5 virtual table
            connection.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    text,
                    content='document_chunks',
                    content_rowid='id',
                    tokenize = 'trigram'
                );
            """))

            # Create INSERT trigger
            connection.execute(text("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON document_chunks BEGIN
                    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
                END;
            """))

            # Create UPDATE trigger
            connection.execute(text("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_update AFTER UPDATE ON document_chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
                    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
                END;
            """))

            # Create DELETE trigger
            connection.execute(text("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_delete AFTER DELETE ON document_chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
                END;
            """))

            connection.commit()

    except Exception as e:
        print(f"Warning: Could not create FTS tables: {e}")

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
