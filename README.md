# MCP KnowledgeExplorer

> **🎉 Status: Phase 4B M2 COMPLETE - Keyword Search Ready!**
> Phase 4B Milestone 2 (Keyword Search Path) is 100% complete with production-ready full-text search capabilities. The complete TEXT_EXTRACT → CHUNK → FTS_INDEX pipeline, FTS5 search with trigram tokenizer, PermissionPostprocessor security layer, and search_fulltext MCP tool (8th tool) are operational with 49+ comprehensive tests. Ready for M3 Semantic Search implementation.

## Quick Start

```bash
# Start the entire system with one command
# This will now start FOUR services: backend, frontend, indexer, and Qdrant
docker-compose up --build

# Access the services
# Frontend UI: http://localhost:5173
# Backend API: http://localhost:8000
# MCP HTTP: http://localhost:8000/mcp (for AI clients)
# Qdrant API: http://localhost:6333 (vector database)

# View logs for a specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f indexer
docker-compose logs -f qdrant
```

## Testing

### MCP Wisdom Comprehensive Test Suite

Validate all MCP functionality with the comprehensive test routine:

```bash
# Quick test (validates current environment)
./scripts/test-mcp-wisdom.sh

# Full comprehensive test suite
./scripts/test-mcp-wisdom.sh --comprehensive

# Create isolated test environment
./scripts/test-mcp-wisdom.sh --isolated

# View previous test results
./scripts/test-mcp-wisdom.sh --report-only
```

**Features:**
- ✅ Adaptive pre-validation (checks workspace and permissions)
- ✅ Tests all 8 MCP tools with permission enforcement
- ✅ Security testing (directory traversal, unauthorized access)
- ✅ Performance validation (sub-25ms response times)
- ✅ JSON reporting with detailed metrics

### Phase 4B Test Suite

Validate the new Phase 4B foundations:

```bash
# Run Phase 4B database schema tests
cd backend && python -m pytest tests/phase4b/test_database_schema.py -v

# Run Phase 4B Qdrant integration tests
cd backend && python -m pytest tests/phase4b/test_qdrant_integration.py -v

# Run all Phase 4B tests
cd backend && python -m pytest tests/phase4b/ -v
```

**Test Coverage:**
- ✅ 11 database schema tests (DocumentChunk, FTS5, triggers)
- ✅ 8 Qdrant integration tests (connection, collections, vectors)
- ✅ Temporary database isolation for reliable testing
- ✅ Graceful skipping when dependencies unavailable

### Force Reindex Operations

The Force Reindex feature provides administrators with a powerful tool to rebuild the content index from scratch or refresh indexing flags. Available through both web UI and CLI for maximum flexibility.

#### Web UI Access

Navigate to the **Indexer** tab in the web interface (http://localhost:5173) and use the **Force Reindex** dropdown button:

- **Soft Reindex (recommended)**: Non-destructive reindexing that preserves existing data
- **Hard Reset**: Complete rebuild that purges all existing data

#### CLI Operations

Trigger and manage database reindexing operations programmatically:

```bash
# Trigger soft reindex (keeps existing data, recommended)
python scripts/trigger_reindex.py trigger --mode soft

# Trigger hard reset (purges and rebuilds data)
python scripts/trigger_reindex.py trigger --mode hard

# Filter by path for targeted reindexing
python scripts/trigger_reindex.py trigger --mode soft --path /projects

# Include all file types (not just text files)
python scripts/trigger_reindex.py trigger --mode soft --no-text-only

# Dry run to see what would be reindexed
python scripts/trigger_reindex.py trigger --mode soft --dry-run

# Check batch status with real-time monitoring
python scripts/trigger_reindex.py status <batch_id>
python scripts/trigger_reindex.py status <batch_id> --watch

# List all batches
python scripts/trigger_reindex.py list --all

# Control batch execution
python scripts/trigger_reindex.py pause <batch_id>
python scripts/trigger_reindex.py resume <batch_id>
python scripts/trigger_reindex.py cancel <batch_id>

# System management
python scripts/trigger_reindex.py system
python scripts/trigger_reindex.py clear-maintenance
```

#### API Integration

Force Reindex operations can be integrated into automation workflows via REST API:

```bash
# Create new reindex batch
curl -X POST http://localhost:8000/admin/reindex/force \
  -H "X-Admin-Key: admin-secret-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"mode": "soft", "scope": {"path_prefix": "/projects", "text_only": true}}'

# Monitor batch progress
curl -H "X-Admin-Key: admin-secret-key-change-me" \
  http://localhost:8000/admin/reindex/batches/{batch_id}

# Control batch execution
curl -X POST http://localhost:8000/admin/reindex/batches/{batch_id}/pause \
  -H "X-Admin-Key: admin-secret-key-change-me"
```

**Features:**
- ✅ **Dual Modes**: Soft reindex (non-destructive) and Hard reset (complete rebuild)
- ✅ **Chunked Processing**: 5000 files per chunk for memory efficiency
- ✅ **Path Filtering**: Target specific directories for reindexing
- ✅ **Maintenance Mode**: Prevents race conditions during operations
- ✅ **Batch Management**: Full control with pause/resume/cancel capabilities
- ✅ **Progress Tracking**: Real-time progress with ETA calculations
- ✅ **Admin Security**: Protected by admin API key authentication
- ✅ **Dry Run Support**: Preview operations without making changes
- ✅ **Error Recovery**: Transactional operations with rollback support

**Performance Characteristics:**
- Soft reindex: ~2-5 seconds per 1000 files
- Hard reset: ~10-30 seconds per 1000 files (depending on chunk count)
- Memory usage: <100MB additional during processing
- Sub-second response times for batch status queries

---

## MCP Integration with AI Clients

### Claude Desktop (Recommended)

Claude Desktop has mature MCP support and works directly with localhost connections:

```bash
# Add MCP server (HTTP transport recommended)
claude mcp add --transport http wisdom http://localhost:8000/mcp

# Test connection
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

**Available as:**
- `mcp__wisdom__read_file` - Read file contents with permission checking
- `mcp__wisdom__list_files` - List directory contents with metadata
- `mcp__wisdom__write_file` - Write file contents (subject to permissions)
- `mcp__wisdom__list_all_files` - List all indexed files across workspace
- `mcp__wisdom__search_files_by_metadata` - Search files by metadata criteria
- `mcp__wisdom__get_file_info` - Get detailed file information and metadata
- `mcp__wisdom__get_search_statistics` - Retrieve indexing and search statistics
- `mcp__wisdom__search_fulltext` - Full-text search with FTS5 and filtering

### ChatGPT Desktop

ChatGPT Desktop expects **Streamable HTTP transport** (MCP 2025-03-26 spec) and may have localhost access restrictions. Our server uses basic HTTP JSON-RPC transport, so we need a compatibility layer.

#### Solution: Proxy + Tunnel Approach

**Step 1: Install Dependencies**
```bash
pip install aiohttp
```

**Step 2: Start Proxy Server**
```bash
# Start the compatibility proxy (bridges ChatGPT ↔ MCP server)
python chatgpt_proxy.py
```
This starts a proxy on port 9000 that forwards requests to your MCP server on port 8000.

**Step 3: Create Public Tunnel**

ChatGPT Desktop may not access localhost directly. Create a public tunnel:

```bash
# Option A: Specific subdomain (preferred, if available)
npx localtunnel --port 8000 --subdomain wisdom-direct
npx localtunnel --port 9000 --subdomain wisdom-proxy

# Option B: Random subdomain (fallback if specific fails)
npx localtunnel --port 8000  # Gets random URL like https://abc-def.loca.lt
npx localtunnel --port 9000  # Gets random URL like https://xyz-123.loca.lt
```

**Step 4: Configure ChatGPT Desktop**

Use one of these URLs in ChatGPT Desktop's Connector settings:

```
# Direct connection (bypasses proxy)
https://[your-subdomain].loca.lt/mcp

# Through proxy (for debugging/logging)
https://[proxy-subdomain].loca.lt/mcp
```

#### Process Management

The ChatGPT integration requires **3 running processes**:
1. **Docker Compose** (your main MCP server) - Port 8000
2. **Proxy Server** (`python chatgpt_proxy.py`) - Port 9000
3. **Tunnel Process** (`npx localtunnel --port XXXX`) - Creates public URL

### Troubleshooting Connection Issues

#### Problem: ChatGPT shows "URL is invalid" or connection fails

**Solutions:**
1. **Try IPv4 explicitly:** Use `127.0.0.1` instead of `localhost`
2. **Check Developer Mode:** Ensure ChatGPT Pro/Plus with Developer Mode enabled
3. **Test tunnel manually:**
   ```bash
   curl -X POST https://your-tunnel-url.loca.lt/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}'
   ```

#### Problem: Tunnel connections refused or firewall errors

**Solutions:**
1. **Try without specific subdomain:**
   ```bash
   npx localtunnel --port 8000  # Let it assign random subdomain
   ```
2. **Use alternative tunnel service:**
   ```bash
   # If you have ngrok installed
   ngrok http 8000
   ```

#### Problem: Proxy not receiving requests

Check proxy logs - if no requests appear, ChatGPT isn't reaching the tunnel URL.

**Debug steps:**
1. Verify tunnel is running: Visit the tunnel URL in browser
2. Test tunnel directly with curl (as shown above)
3. Check ChatGPT Desktop network restrictions

---

## 1. Introduction

### 1.1. Purpose

This project is a **production-ready Model Context Protocol (MCP) server** that enables AI agents to safely interact with your local file system. It provides a web-based management interface for real-time monitoring and granular permission control, and is being extended with a powerful, local-first search and retrieval engine.

### 1.2. Current Status - ✅ Phase 4A 100% COMPLETE

Phase 4A advanced search infrastructure has been fully implemented with comprehensive documentation for Phase 4B development:

#### 🎯 Phase 4A Achievement Summary
- ✅ **Search Infrastructure Complete**: Indexer service with file watching, job queue, metadata extraction
- ✅ **7 MCP Tools Operational**: 3 core file system + 4 new search tools with cursor pagination
- ✅ **Database Integration**: Phase 4A models (IndexedFile, IndexJob, ControlSetting) with WAL mode
- ✅ **Performance Validated**: Sub-100ms response times, crash recovery, comprehensive testing
- ✅ **Production Issues Resolved**: All 3 critical bugs identified by independent review fixed
- ✅ **Documentation Complete**: Implementation summary and Phase 4B development guide

#### 🚨 Critical Production Fixes (v4.0.1) - RESOLVED
- ✅ **Issue 013**: Database URL misconfiguration causing empty workspace API responses
- ✅ **Issue 014**: Indexer import errors preventing service startup
- ✅ **Issue 015**: Frontend 404 cascade errors when workspace list empty
- ✅ **Additional Fixes**: SQLAlchemy parameter format, environment variables, cross-container imports

#### 📖 Phase 4B Ready Documentation
- 📖 **`docs/Phase4A-Implementation-Summary.md`** - Complete Phase 4A achievement overview
- 📖 **`docs/Phase4B-Development-Guide.md`** - Detailed semantic search implementation plan
- 📖 **`indexer/README.md`** - Comprehensive indexer service documentation
- 🎯 **Next Phase**: Semantic search with vector embeddings, document clustering, 4 new semantic MCP tools

---

## 2. Architectural Vision: The "Indexer-Query" Model

To support advanced search, the architecture follows a robust **"Indexer-Query"** pattern. This design separates the application into distinct, cooperating services for maximum performance and resilience:

* **Backend Service (Query Engine):** The existing FastAPI application remains the central hub for all API/MCP requests. It is responsible for running fast searches against the indexes and, most importantly, applying security permissions to all results in real-time.
* **Indexer Service (Background Processor):** A new, separate service that continuously monitors the filesystem. It is responsible for the heavy lifting: parsing files, extracting text (including OCR), calculating embeddings, and populating the search indexes.
* **Frontend Service (UI):** The existing React application, which will be enhanced with a new "Indexer Dashboard" to give the user full visibility and control (Pause/Resume) over the indexing process.

This separation ensures that intensive background processing never impacts the responsiveness of the main application.

---

## 3. System Architecture

### 3.1. Architecture Diagram

The complete system architecture is visualized in our comprehensive Mermaid diagram:

📊 **[View Interactive Architecture Diagram](Software%20Architecture-2025-09-22-135021.mmd)**

This diagram shows the complete three-service Docker architecture with all components, data flows, and `.env` configuration controls. Key architectural elements include:

- **Frontend Service**: React UI with Indexer Dashboard
- **Backend Service**: FastAPI Query Engine with LlamaIndex integration
- **Indexer Service**: Background processing with crash-resilient job queue
- **Data Stores**: SQLite (WAL mode), Qdrant vector DB, HuggingFace model cache
- **Configuration**: Comprehensive `.env` system for hardware adaptation

### 3.2. High-Level Flow

```ascii
User/Agent → Frontend/MCP → Backend (Query Engine) → Permission Filter → Results
                                ↓
File System ← Indexer ← Job Queue ← File Watcher
    ↓           ↓
SQLite FTS ← Embedding Model → Qdrant Vector DB
```

---

## 4. MCP Protocol Implementation

The existing file system tools remain fully functional. Phase 4 will introduce a new suite of search tools.

### 4.1. Available MCP Tools (Phase 4A Complete)
| Tool | Parameters | Description | Status |
|------|------------|-------------|---------|
| **Core File System Tools** | | | |
| `read_file` | `path: string` | Read complete file contents | ✅ Ready |
| `list_files` | `path: string` | List directory contents with metadata | ✅ Ready |
| `write_file` | `path: string, content: string` | Write content to file | ✅ Ready |
| **Phase 4A Search Tools** | | | |
| `list_all_files` | `limit, cursor, sort_by` | List all indexed files with cursor pagination | ✅ Ready |
| `search_files_by_metadata` | `filename_pattern, file_types, size_range, mtime_range` | Search files by metadata criteria | ✅ Ready |
| `get_file_info` | `doc_id: string` | Get detailed file information by document ID | ✅ Ready |
| `get_search_statistics` | - | Retrieve indexing progress and search statistics | ✅ Ready |
| **Phase 4B Search Tools** | | | |
| `search_fulltext` | `query: string, limit, cursor, highlight, file_types` | Full-text search with FTS5, highlighting, and filtering | ✅ Ready |

### 4.2. Planned Advanced Search Tools (Phase 4B M3+)
| Tool | Description | Status |
|------|-------------|---------|
| `search_semantic` | Semantic similarity search using embeddings | 📋 Planned |
| `find_similar` | "More like this" vector search | 📋 Planned |
| `search_hybrid` | Combined FTS5 and vector search with RRF | 📋 Planned |

---

## 5. Configuration Management

### 5.1. Environment Variables (`.env`)

The system uses comprehensive `.env` configuration to support flexible deployment across different hardware setups:

#### Hardware & Model Selection
```bash
# GPU/CPU switching - critical for RTX 4060 users
INDEX_EMBED_DEVICE=cpu           # or 'gpu' when RTX 4060 available
INDEX_EMBED_QUANT=fp16           # Future: 4bit/8bit/fp16 for VRAM management
INDEX_EMBED_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

#### Feature Toggles
```bash
# Resource-intensive features with user control
OCR_ENABLED=true                 # Tesseract OCR processing
RERANK_ENABLED=false             # Optional cross-encoder reranker
```

#### Performance Tuning
```bash
# Search and indexing behavior
RETRIEVAL_MODE=hybrid            # hybrid/fts/vector - invaluable for debugging
INDEXER_BATCH_SIZE=50            # Files per batch - tune memory vs speed
INDEXER_MAX_WORKERS=2            # Parallel processing control
```

This configuration strategy enables seamless switching between laptop (CPU-only) and desktop (RTX 4060) environments while maintaining optimal performance for each setup.

#### Frontend API Base URL (new)
```bash
# Point the frontend to a non-default backend origin if needed
VITE_API_BASE_URL=http://localhost:8000
```

#### Shared Filesystem Mount: Host vs Container paths
- In Docker, your host folder (e.g., `C:\Users\<you>\MCP Test`) is mounted into the container at `/source`.
- Backend APIs and the indexer always use `/source` inside the container to access files.
- The validator in `config/env_config.py` now treats `/source` as authoritative in Docker, so a Windows path string in `.env` will no longer trigger a false warning.

Example docker-compose mapping:
```
volumes:
  - ${SHARED_FS_PATH:-./shared-fs}:/source  # host:container
```
Keep `SHARED_FS_PATH` pointing at your host folder. Inside containers, the code uses `/source`.

---

## 6. Technology Stack

| Category | Technology | Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Containerization** | Docker Compose | 4-service orchestration: backend, frontend, indexer, qdrant | ✅ Phase 4B M1 |
| **Backend** | FastAPI | MCP/API endpoints and Query Engine with search tools | ✅ Phase 4A |
| **Frontend** | React, Vite | Web UI with indexer dashboard and controls | ✅ Phase 4A |
| **Indexer** | Python/Watchdog | Background file monitoring and job processing | ✅ Phase 4A |
| **Application DB** | SQLite (WAL) | Concurrent storage: workspaces, permissions, files, jobs, chunks | ✅ Phase 4B M1 |
| **Full-Text Search** | SQLite FTS5 | Trigram tokenizer for typo-tolerant keyword search | ✅ Phase 4B M1 |
| **Job Queue** | SQLite | Crash-resilient job queue with atomic claiming | ✅ Phase 4A |
| **Vector Database** | **Qdrant v1.7.4** | High-performance storage and retrieval of vector embeddings | ✅ Phase 4B M1 |
| **RAG Framework** | **LlamaIndex** | Core toolkit for data ingestion, indexing, and querying | ✅ Phase 4B M1 |
| **Embedding Model** | **`paraphrase-multilingual-MiniLM-L12-v2`** | CPU-based multilingual model for semantic search | 📋 Phase 4B M2+ |
| **OCR Engine**| **Tesseract** | Extracts text from images and scanned documents | 📋 Phase 4B M3+ |

---

## 6. Project Structure

```
MCPFileServer/
├── 📁 backend/                  # Python FastAPI backend (Query Engine)
├── 📁 frontend/                 # React TypeScript frontend (UI)
├── 📁 indexer/                  # Python background service for indexing
├── 📁 config/                   # Global configuration
├── 📁 data/                     # SQLite database (gitignored)
├── 📁 docs/                     # Phase documentation and guides
├── 📁 scripts/                  # Testing and utility scripts
├── 📄 docker-compose.yml        # 4-service orchestration: backend, frontend, indexer, qdrant
├── 📄 chatgpt_proxy.py          # MCP compatibility proxy for ChatGPT Desktop
├── 📄 .env                      # Environment variables
├── 📄 README.md                 # This file
└── 📄 CLAUDE.md                 # Project context for Claude
```

---

## 7. Monitoring and Debugging

### 7.1. Log Access

```bash
# View all container logs
docker-compose logs

# Follow logs for a specific service in real-time
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f indexer
```

### 7.2. Service Health Monitoring

**Indexer Service Status:**
```bash
# Check indexer health
curl http://localhost:8002/live    # Liveness check
curl http://localhost:8002/ready   # Readiness check with database validation

# Monitor indexing status
curl http://localhost:8002/status/system   # Overall system status
curl http://localhost:8002/status/jobs     # Job queue statistics
curl http://localhost:8002/status/files    # Indexed file statistics
```

**Backend Service Status:**
```bash
# Check backend health
curl http://localhost:8000/         # Health check
curl http://localhost:8000/docs     # API documentation

# Database diagnostic (useful for troubleshooting)
curl http://localhost:8000/api/system/db-info
```

**Force Reindex Management:**
```bash
# Check reindex system status
curl http://localhost:8000/admin/reindex/status

# List active reindex batches
curl -H "X-Admin-Key: admin-secret-key-change-me" \
  http://localhost:8000/admin/reindex/batches

# Get specific batch status
curl -H "X-Admin-Key: admin-secret-key-change-me" \
  http://localhost:8000/admin/reindex/batches/{batch_id}

# Access web UI for visual management
# Navigate to Indexer tab -> Force Reindex dropdown
```

### 7.3. MCP Tools Testing
### 7.4. Indexer Dashboard Alerts

The Indexer view in the frontend now mirrors the backend status payload:
- Surfaces banner alerts whenever the service is stopped, unreachable, or backlog builds up.
- Shows per-stage queue depth (TEXT_EXTRACT, CHUNK, FTS_INDEX) and highlights failed/dead-letter jobs.
- Progress bar segments indexed vs pending files and flags any indexed files that still lack text chunks.
- Pulls `service_error`, `job_backlog`, and `integrity_stats` from `/api/indexer/status`, so Docker operators immediately see if Phase 4B pipelines are stalled.

**Complete MCP Protocol Validation:**
```bash
# Test all 8 MCP tools with comprehensive suite
./scripts/test-mcp-wisdom.sh --comprehensive

# Quick validation
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

---

**📋 For Phase 4B Development:**
- See `docs/Phase4A-Implementation-Summary.md` for complete achievement details
- See `docs/Phase4B-Development-Guide.md` for semantic search implementation plan
- See `indexer/README.md` for comprehensive indexer service documentation

*Phase 4A is 100% complete. The system is production-ready and fully documented for Phase 4B semantic search development.*
