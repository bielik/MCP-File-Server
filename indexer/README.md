# Indexer Service - MCP KnowledgeExplorer

## Overview
The Indexer Service is a specialized FastAPI application responsible for file system monitoring, job queue management, and metadata extraction in the MCP KnowledgeExplorer system. It works in conjunction with the main backend to provide advanced search and indexing capabilities.

## 🎉 STATUS: PHASE 4A COMPLETE ✅
**All critical production issues resolved - Fully operational service**

The indexer service is now production-ready with robust file watching, job processing, and database integration. All import errors and configuration issues have been resolved.

## Architecture

### Service Role
The indexer operates as an independent service within the MCP KnowledgeExplorer ecosystem:
- **Primary Function**: File system monitoring and metadata extraction
- **Database**: Shared SQLite database with main backend (`/data/database.db`)
- **Mount Point**: Monitors `/source` directory for file system changes
- **Job Processing**: Background queue with crash recovery and throttling
- **Control Interface**: REST API for pause/resume/throttle operations

### Technology Stack
- **Framework**: FastAPI with background task processing
- **Database**: SQLite with WAL mode for concurrent access
- **File Watching**: Python `watchdog` library with stability checking
- **Job Queue**: Custom implementation with atomic claiming
- **Dependencies**: `uvicorn`, `sqlalchemy`, `watchdog`, `pillow`, `python-magic`

## Core Components

### 1. File Watcher System
**Location**: `app/watcher.py` (referenced in main.py)
```python
# Monitors file system changes with intelligent stability checking
class FileWatcher:
    - Watches /source directory recursively
    - Detects create, modify, delete, and move operations
    - Implements 2-second stability check before processing
    - Handles rename operations to preserve document identity
```

**Features:**
- **Recursive Monitoring**: Watches entire `/source` directory tree
- **Stability Checking**: Waits for file operations to complete before indexing
- **Rename Handling**: Preserves document IDs across file renames
- **Event Filtering**: Ignores temporary files and system files

### 2. Job Queue Management
**Location**: `app/queue.py` (referenced in main.py)
```python
# Crash-resilient job processing with atomic operations
class JobQueueManager:
    - Atomic job claiming with SELECT FOR UPDATE
    - Exponential backoff for failed jobs
    - Dead letter queue for permanently failed jobs
    - Duplicate job prevention with content-based signatures
```

**Job Processing Features:**
- **Atomic Claims**: Uses database transactions for safe job claiming
- **Retry Logic**: Exponential backoff (2^attempt_count seconds)
- **Failure Handling**: Dead letter queue after 5 failed attempts
- **De-duplication**: Prevents duplicate jobs for same file content
- **Status Tracking**: Comprehensive job state management (pending, processing, completed, failed)

### 3. Database Models
**Location**: `app/models/indexing.py`

#### IndexedFile Model
```python
class IndexedFile(Base):
    __tablename__ = "indexed_files"

    doc_id: str = Column(String, primary_key=True)      # Unique document identifier
    file_path: str = Column(String, nullable=False)     # Relative path from /source
    file_name: str = Column(String, nullable=False)     # Just the filename
    file_size: int = Column(BigInteger, nullable=False) # Size in bytes
    file_type: str = Column(String, nullable=True)      # MIME type
    last_modified: datetime = Column(DateTime, nullable=False)
    indexed_at: datetime = Column(DateTime, default=datetime.utcnow)
    content_hash: str = Column(String, nullable=True)   # For duplicate detection
    metadata: str = Column(Text, nullable=True)         # JSON metadata
```

#### IndexJob Model
```python
class IndexJob(Base):
    __tablename__ = "index_jobs"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    file_path: str = Column(String, nullable=False)
    job_type: str = Column(String, nullable=False)      # 'index', 'update', 'delete'
    status: str = Column(String, default="pending")     # 'pending', 'processing', 'completed', 'failed'
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    started_at: datetime = Column(DateTime, nullable=True)
    completed_at: datetime = Column(DateTime, nullable=True)
    attempt_count: int = Column(Integer, default=0)
    error_message: str = Column(Text, nullable=True)
    job_signature: str = Column(String, nullable=True)   # For de-duplication
```

#### ControlSetting Model
```python
class ControlSetting(Base):
    __tablename__ = "control_settings"

    key: str = Column(String, primary_key=True)
    value: str = Column(String, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow)
```

## API Endpoints

### Health Check Endpoints
```http
GET /live   - Liveness check (always returns 200)
GET /ready  - Readiness check (validates database connectivity)
```

### Control Endpoints
```http
POST /control/pause   - Pause job processing
POST /control/resume  - Resume job processing
POST /control/throttle/{percentage} - Set processing throttle (0-100%)
```

### Status Endpoints
```http
GET /status/jobs    - Get job queue statistics
GET /status/files   - Get indexed file statistics
GET /status/system  - Get overall system status
```

## Configuration

### Environment Variables
```bash
# Database Configuration
DATABASE_PATH=./data                    # Local path (Docker handles container mapping)

# File System
SOURCE_MOUNT_PATH=/source              # Directory to monitor

# Processing Configuration
JOB_BATCH_SIZE=10                      # Jobs processed per batch
FILE_STABILITY_DELAY=2                 # Seconds to wait before processing file changes
MAX_RETRY_ATTEMPTS=5                   # Maximum job retry attempts

# Server Configuration
INDEXER_PORT=8002                      # API server port
```

### Docker Configuration
```yaml
# docker-compose.yml
indexer:
  build: ./indexer
  ports:
    - "8002:8002"
  volumes:
    - ./data:/data                     # Shared database
    - ./config:/config                 # Configuration
    - "C:/Users/MartinBielik/MCP Test/:/source"  # Files to monitor
  environment:
    - DATABASE_PATH=./data
    - SOURCE_MOUNT_PATH=/source
```

## Database Integration

### Shared Database Access
The indexer shares the same SQLite database as the main backend:
- **Database File**: `/data/database.db` (mounted from `./data/database.db`)
- **WAL Mode**: Enables concurrent read/write access
- **Bootstrap Process**: Automatic database initialization with proper schema

### Database Bootstrap
```python
class DatabaseBootstrap:
    """Ensures proper database setup for indexer service"""

    def __init__(self, database_url: str):
        # Configure WAL mode for concurrent access
        # Create all Phase 4A tables if they don't exist
        # Validate database connectivity
```

**Bootstrap Features:**
- **WAL Mode Configuration**: `PRAGMA journal_mode=WAL` for concurrency
- **Schema Creation**: Creates all Phase 4A indexing tables
- **Connectivity Validation**: Ensures database is accessible before startup
- **Error Handling**: Graceful handling of database initialization issues

## File Processing Pipeline

### 1. File System Events
```
File Change Detected → Stability Check (2s) → Create Index Job → Queue Processing
```

### 2. Job Processing Flow
```
Job Claimed → File Analysis → Metadata Extraction → Database Update → Job Completion
```

### 3. Metadata Extraction
The indexer extracts comprehensive metadata from files:
- **Basic Attributes**: Size, modification time, MIME type
- **Content Hash**: For duplicate detection and change tracking
- **File Type Detection**: Using `python-magic` library
- **Image Metadata**: EXIF data extraction for image files
- **Document Properties**: Title, author, creation date (when available)

## Error Handling & Recovery

### Job Failure Recovery
```python
# Exponential backoff retry logic
retry_delay = 2 ** attempt_count  # 2, 4, 8, 16, 32 seconds
max_attempts = 5                  # Then move to dead letter queue
```

### Database Connection Recovery
- **Connection Pooling**: SQLAlchemy handles connection management
- **Retry Logic**: Automatic reconnection on database failures
- **Health Checks**: Regular database connectivity validation

### File System Recovery
- **Crash Recovery**: On startup, processes any pending jobs
- **Consistency Checks**: Validates indexed files against file system
- **Orphan Cleanup**: Removes index entries for deleted files

## Performance Characteristics

### Processing Metrics
- **File Watching**: Real-time file system monitoring with minimal overhead
- **Job Processing**: Configurable batch size and throttling
- **Database Operations**: Optimized with proper indexing and WAL mode
- **Memory Usage**: Efficient processing with controlled resource usage

### Scalability Features
- **Throttling Control**: Dynamic processing speed adjustment (0-100%)
- **Batch Processing**: Configurable job batch sizes
- **Queue Management**: Handles large volumes of file changes
- **Resource Monitoring**: Built-in status endpoints for monitoring

## Monitoring & Debugging

### Status Information
```http
GET /status/system
{
  "service": "indexer",
  "version": "4.0.1",
  "database_connected": true,
  "file_watcher_active": true,
  "processing_paused": false,
  "throttle_percentage": 100,
  "jobs_pending": 0,
  "jobs_processing": 0,
  "files_indexed": 1234
}
```

### Logging
The indexer provides comprehensive logging:
- **File Events**: All file system changes with timestamps
- **Job Processing**: Start, completion, and error states
- **Database Operations**: Connection status and query performance
- **Error Conditions**: Detailed error messages with context

## Testing

### Manual Testing
```bash
# Start indexer service
docker-compose up indexer

# Check health
curl http://localhost:8002/live
curl http://localhost:8002/ready

# Monitor status
curl http://localhost:8002/status/system

# Test control operations
curl -X POST http://localhost:8002/control/pause
curl -X POST http://localhost:8002/control/resume
curl -X POST http://localhost:8002/control/throttle/50
```

### Integration Testing
```bash
# Use comprehensive MCP test routine
./scripts/test-mcp-wisdom.sh --comprehensive

# Test file processing pipeline
touch "/path/to/source/test.txt"    # Should create index job
echo "content" > "/path/to/source/test.txt"  # Should update index
rm "/path/to/source/test.txt"       # Should mark as deleted
```

## Development Workflow

### Local Development
```bash
# Run indexer standalone for debugging
cd indexer
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Monitor logs
docker-compose logs -f indexer
```

### Code Structure
```
indexer/
├── app/
│   ├── main.py              # FastAPI application and endpoints
│   ├── models/
│   │   ├── __init__.py      # Model imports
│   │   └── indexing.py      # IndexedFile, IndexJob, ControlSetting models
│   ├── config.py            # Configuration management
│   └── database.py          # Database setup and bootstrap
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
└── README.md               # This file
```

## Critical Fixes Applied (v4.0.1)

### Issue 014: Import Resolution ✅
**Problem**: Duplicate import statements causing module resolution conflicts
```python
# FIXED: Removed duplicate imports at lines 420, 441, 468
# from app.models.indexing import ControlSetting  # Already imported at top
```

**Resolution**: Removed 3 duplicate import statements, utilizing existing module-level import

### Database Configuration ✅
**Problem**: Database URL construction inconsistencies
**Resolution**: Standardized database path resolution to match backend pattern
```python
# Container detection and proper database URL construction
if os.path.exists('/data'):
    database_path = '/data'
else:
    database_path = getattr(config, 'DATABASE_PATH', './data')

# Proper database URL with file path
db_path = Path(database_path) / 'database.db'
DATABASE_URL = f"sqlite:///{db_path}"
```

## Phase 4B Integration Points

### Search Tool Backend
The indexer provides the foundation for Phase 4B search tools:
- **File Discovery**: `list_all_files` tool uses indexed file data
- **Metadata Search**: `search_files_by_metadata` leverages extracted metadata
- **File Information**: `get_file_info` provides detailed indexed file data
- **Statistics**: `get_search_statistics` reports indexing progress

### Semantic Search Preparation
Phase 4B semantic search can build on this foundation:
- **Content Extraction**: Extend metadata extraction to include full text
- **Vector Embeddings**: Add embedding generation to job processing pipeline
- **Search Index**: Build on existing indexed file structure
- **Performance**: Leverage existing job queue for embedding generation

### API Extensions for Phase 4B
Planned extensions for semantic search:
```python
# Future Phase 4B endpoints (not yet implemented)
POST /index/generate-embeddings    # Trigger embedding generation
GET  /search/semantic              # Semantic search endpoint
POST /search/similar               # Find similar documents
GET  /status/embeddings            # Embedding generation status
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose logs indexer

# Common causes:
# 1. Database connection issues
# 2. Mount point permissions
# 3. Port conflicts (8002)
```

#### File Changes Not Detected
```bash
# Verify file watcher is active
curl http://localhost:8002/status/system

# Check file permissions in /source mount
# Ensure files are actually changing (timestamps)
```

#### Jobs Stuck in Processing
```bash
# Check job status
curl http://localhost:8002/status/jobs

# Reset stuck jobs (requires database access)
# Update stuck jobs to 'failed' status to retry
```

### Performance Tuning
```bash
# Reduce processing load
curl -X POST http://localhost:8002/control/throttle/25

# Pause during heavy operations
curl -X POST http://localhost:8002/control/pause

# Resume normal operations
curl -X POST http://localhost:8002/control/resume
```

## Success Metrics ✅

All Phase 4A indexer objectives achieved:
- ✅ **Service Operational**: Indexer starts successfully without import errors
- ✅ **Database Integration**: Shared SQLite database with WAL mode
- ✅ **File Watching**: Real-time monitoring of `/source` directory
- ✅ **Job Processing**: Robust queue with crash recovery and throttling
- ✅ **Metadata Extraction**: Comprehensive file analysis and indexing
- ✅ **API Control**: Pause/resume/throttle operations working
- ✅ **Health Monitoring**: Status endpoints providing real-time metrics
- ✅ **Error Recovery**: Graceful handling of failures with retry logic
- ✅ **Performance**: Optimized processing with configurable throttling
- ✅ **Phase 4B Ready**: Foundation complete for semantic search development

---

**🚀 The Indexer Service Phase 4A implementation is complete and operational!**

*This service provides a robust, production-ready foundation for file indexing and metadata extraction, with all critical issues resolved and comprehensive monitoring capabilities.*

---
*Last updated: 2025-01-23 - Phase 4A Critical Production Issues Resolved*