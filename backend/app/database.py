from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Import config to get correct database path
try:
    from app.config import get_config
    config = get_config()
    SQLALCHEMY_DATABASE_URL = config.DATABASE_URL
except ImportError:
    # Fallback for cases where config isn't available (like migrations)
    SQLALCHEMY_DATABASE_URL = "sqlite:///./data/database.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def enable_sqlite_fks(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    if 'sqlite' in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def create_db_and_tables():
    # This function is called on startup to create all tables.
    # NOTE: This is simple and effective for prototypes, but for production
    # a proper migration tool like Alembic is recommended.

    # Import all models to ensure they're registered with Base.metadata
    try:
        from app.models import Setting, Workspace, Permission
    except ImportError:
        # In case models aren't available (like during testing)
        pass

    Base.metadata.create_all(bind=engine)

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
