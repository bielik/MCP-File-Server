# MCP KnowledgeExplorer - Project Context for Claude

## Project Overview
**Name:** MCP KnowledgeExplorer
**Type:** Full-stack web application with MCP (Model Context Protocol) server
**Purpose:** A sophisticated, local-first Model Context Protocol server that enables AI agents to assist with research, providing a web-based UI for configuration, real-time monitoring, and granular permission management over the local file system.

## 🎉 CURRENT STATUS: Phase 4B M2 Complete - Keyword Search Operational
**✅ PHASE 4B M2 100% COMPLETE - Full-Text Search with FTS5 and Permission Filtering**

Phase 4B Milestone 2 delivers production-ready full-text search capabilities using SQLite FTS5 with trigram tokenization, completing the keyword search path with comprehensive permission filtering and 8 MCP tools operational.

### 🎯 **Achievement Timeline (Progressive)**

**Phase 4B M2 (Current - ✅ COMPLETE):**
- 🔍 Full-Text Search: FTS5 with trigram tokenizer for advanced keyword search with typo tolerance
- 🛠️ 8th MCP Tool: search_fulltext with comprehensive query syntax and filtering
- 🔒 Security Layer: PermissionPostprocessor ensures zero data leakage through workspace filtering
- ⚙️ Job Pipeline: TEXT_EXTRACT → CHUNK → FTS_INDEX pipeline with LlamaIndex integration
- 📊 Advanced Queries: Phrase search, boolean operators, wildcards, highlighting, pagination
- 🧪 Comprehensive Testing: 49+ test methods with 100% TDD compliance
- 🚀 Performance: Sub-350ms search response times with O(1) permission filtering
- 📖 Production Ready: 2,400+ lines of tested code with comprehensive error handling
- 🧹 Hard reset now drops orphaned file records and rebuilds the Phase 4B FTS tables before enqueuing jobs, preventing stale paths from reappearing.
- ♻️ Queue processor reuses existing CHUNK/FTS jobs after text extraction so duplicate signatures no longer occur; use `POST /control/resume` or restart the indexer to refresh dashboard counters after large resets.

**Phase 4B M1 (Foundation - ✅ COMPLETE):**
- 📊 Database Schema Extended: DocumentChunk model with 13 fields for text chunk management
- 🔍 FTS5 Infrastructure: chunks_fts virtual table with trigram tokenizer
- ⚙️ SQLite Triggers: Automatic FTS synchronization via INSERT/UPDATE/DELETE triggers
- 🚀 Qdrant Integration: Vector database v1.7.4 with Docker orchestration and persistence
- 📦 Dependencies Updated: Complete ML stack (PyTorch, sentence-transformers, LlamaIndex)
- 🧪 TDD Implementation: 19 comprehensive tests with reliable skip logic

**Phase 4A (Search Infrastructure - ✅ COMPLETE):**
- 🚀 Indexer Service: File watching, job queue, metadata extraction, crash recovery
- 🛠️ 7 MCP Tools: 3 core file system + 4 search tools with cursor pagination
- 💾 Database Integration: Shared SQLite with WAL mode and proper bootstrap
- 📊 Performance Validated: Sub-100ms response times, comprehensive testing

**Phase 3 (Workspace Management - ✅ COMPLETE):**
- 🆕 Complete Workspace Management UI: Create, activate, delete workspaces with real-time updates
- 🆕 Two-Panel Permission Editor: Visual permission management with file tree navigation
- 🆕 Permission Inspector System: Detailed rule explanations with hover tooltips and click modals
- 🆕 Database-Driven Permissions: Full workspace and permission models with Trie caching
- 🆕 Batch Permission API: High-performance endpoint for efficient UI integration

**Phase 2 (MCP Foundation - ✅ COMPLETE):**
- Complete MCP JSON-RPC 2.0 protocol implementation (MCP 2024-11-05)
- File system tools: read_file, list_files, write_file with integrated security
- Real-time activity logging via WebSocket to UI
- Docker Environment with simplified single-mount containerization

## Architecture: The "Unified Hub" Model
The system follows a **"Unified Hub"** architecture - a single, persistent backend server acts as the central point of control for all clients (both browser UI and AI agents).

### Technology Stack
| Service | Technology | Purpose | Status |
|---------|------------|---------|---------|
| **Backend** | Python/FastAPI | MCP/API endpoints, Query Engine | ✅ Phase 4B M2 |
| **Frontend** | React/TypeScript/Vite | Web UI with workspace management | ✅ Phase 3 |
| **Indexer** | Python/FastAPI | Background file monitoring and job processing | ✅ Phase 4B M2 |
| **Database** | SQLite (WAL) | Concurrent storage: workspaces, permissions, files, chunks | ✅ Phase 4B M2 |
| **Search** | SQLite FTS5 | Trigram tokenizer for typo-tolerant keyword search | ✅ Phase 4B M2 |
| **Vectors** | Qdrant v1.7.4 | High-performance vector database for semantic search | ✅ Phase 4B M1 |
| **Infrastructure** | Docker Compose | 4-service orchestration with hot-reload | ✅ Production |

## MCP Protocol Implementation

### Available Tools (8 Total)
| Tool | Parameters | Security | Description | Phase |
|------|------------|----------|-------------|-------|
| **Core File System** | | | | |
| `read_file` | `path: string` | Permission check | Read complete file contents | 2 |
| `list_files` | `path: string` | Permission check | List directory with metadata | 2 |
| `write_file` | `path: string, content: string` | Permission check | Write content to file | 2 |
| **Search Tools** | | | | |
| `list_all_files` | `limit, cursor, sort_by` | Permission filter | List all indexed files with pagination | 4A |
| `search_files_by_metadata` | `filename_pattern, file_types, size_range` | Permission filter | Search files by metadata criteria | 4A |
| `get_file_info` | `doc_id: string` | Permission check | Get detailed file information | 4A |
| `get_search_statistics` | - | - | Retrieve indexing and search statistics | 4A |
| `search_fulltext` | `query: string, limit, cursor, highlight, file_types` | Permission filter | Full-text search with FTS5, highlighting, and filtering | 4B M2 |

### Protocol Details
- **JSON-RPC 2.0 compliant** with MCP 2024-11-05 specification
- **Dual Transport**: WebSocket (`/ws/mcp`) and HTTP (`/mcp`) endpoints
- **Tool Discovery**: Dynamic tool listing with parameter validation
- **Error Handling**: Comprehensive JSON-RPC error responses with custom codes

## Security Model

### Database-Driven Permissions
- **Principle:** Permission rules stored in SQLite database with workspace contexts
- **Implementation:** Trie caching with O(1) permission resolution
- **Validation:** Every file operation validated against active workspace rules
- **Post-Processing:** PermissionPostprocessor filters search results with pre-computed allowed path sets

**Security Features:**
- Docker bind mount isolation to `/source`
- Path validation preventing directory traversal
- Formal precedence logic: specificity → deny wins → write implies read → default deny
- Atomic updates with optimistic locking

### Permission Configuration Structure
```json
{
  "rules": [
    {
      "path": "materials", "permission_type": "read", "rule_type": "allow",
      "description": "Allow read access to materials directory"
    },
    {
      "path": "projects", "permission_type": "write", "rule_type": "allow",
      "description": "Allow write access to projects directory"
    }
  ]
}
```

## Working Directory Structure
**Shared Filesystem:** `./shared-fs/` (mounted to `/source` in containers)
- `docs/` - Documentation and reference materials
- `projects/` - Development projects and code
- `output/` - Generated outputs
- `tests_hard_reset/` - Test files for reset operations

## Development Workflow

### Starting the Application
```bash
# Primary method: Start all 4 services
docker-compose up

# Access services
# Frontend UI: http://localhost:5173
# Backend API: http://localhost:8000
# Indexer API: http://localhost:8002
# MCP HTTP: http://localhost:8000/mcp
```

### Key Environment Variables
```bash
BACKEND_PORT=8000
FRONTEND_PORT=5173
INDEXER_PORT=8002
DATABASE_PATH=./data
SHARED_FS_PATH=./shared-fs
ENABLE_DATABASE_PERMISSIONS=true
```

## MCP Integration with AI Clients

### Claude Desktop (Recommended - Works Out of the Box)

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

## MCP Integration with ChatGPT Desktop

### Transport Compatibility Issue

**The Problem:**
- **Our Server:** Uses basic HTTP JSON-RPC transport (MCP 2024-11-05 style)
- **ChatGPT Desktop:** Expects Streamable HTTP transport (MCP 2025-03-26 spec)
- **Additional Issue:** ChatGPT Desktop may have localhost access restrictions

**The Solution:** Proxy + Tunneling approach to bridge the compatibility gap.

### Setup Instructions for ChatGPT Desktop

#### Step 1: Install Dependencies
```bash
# Install required Python packages for proxy
pip install aiohttp
```

#### Step 2: Start the MCP Compatibility Proxy
```bash
# Start proxy server (runs on port 9000, forwards to port 8000)
python chatgpt_proxy.py
```

The proxy server:
- Listens on port 9000 for ChatGPT requests
- Forwards requests to your MCP server on port 8000
- Logs all requests/responses for debugging
- Handles CORS and protocol translation

#### Step 3: Create Public Tunnel

ChatGPT Desktop typically cannot access localhost directly. Create a public HTTPS tunnel:

```bash
# Option A: Try specific subdomain first (preferred)
npx localtunnel --port 8000 --subdomain wisdom-direct  # Direct to MCP server
npx localtunnel --port 9000 --subdomain wisdom-proxy   # Through proxy

# Option B: Use random subdomain if specific fails
npx localtunnel --port 8000  # Gets URL like https://funny-cats-jump.loca.lt
npx localtunnel --port 9000  # Gets URL like https://quick-dogs-run.loca.lt
```

#### Step 4: Configure ChatGPT Desktop

In ChatGPT Desktop's Connector settings, use one of these URLs:

```
# Direct connection (bypasses proxy, faster)
https://wisdom-direct.loca.lt/mcp
# or
https://your-random-subdomain.loca.lt/mcp

# Through proxy (enables request logging for debugging)
https://wisdom-proxy.loca.lt/mcp
# or
https://your-proxy-random-subdomain.loca.lt/mcp
```

### Process Management for ChatGPT Integration

You need **these processes running simultaneously**:

1. **Docker Compose** (main services):
   ```bash
   docker-compose up
   ```
   - Backend MCP server (port 8000)
   - Frontend UI (port 5173)
   - Indexer service (port 8002)
   - Qdrant database (port 6333)

2. **Proxy Server** (compatibility layer):
   ```bash
   python chatgpt_proxy.py
   ```
   - Runs on port 9000
   - Forwards to port 8000

3. **Tunnel Process** (public access):
   ```bash
   npx localtunnel --port 8000  # or --port 9000 for proxy
   ```
   - Creates public HTTPS URL
   - Must stay running for ChatGPT access

### Troubleshooting ChatGPT Desktop Connection

#### Issue: "URL is invalid" or connection rejected

**Solutions:**
1. **Test tunnel manually:**
   ```bash
   curl -X POST https://your-tunnel.loca.lt/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}'
   ```

2. **Verify ChatGPT Desktop settings:**
   - Ensure ChatGPT Pro/Plus subscription
   - Enable Developer Mode in settings
   - Use Connectors (Beta) interface

3. **Check proxy logs:**
   If using proxy tunnel, check if requests appear in proxy logs. No logs = ChatGPT not reaching tunnel.

#### Issue: Tunnel connection refused or firewall errors

**Solutions:**
1. **Use random subdomain instead of specific:**
   ```bash
   npx localtunnel --port 8000  # Let service assign random name
   ```

2. **Try alternative tunnel service:**
   ```bash
   # If ngrok is installed
   ngrok http 8000
   ```

#### Issue: Proxy not working

**Debug steps:**
1. **Verify proxy is running:**
   ```bash
   curl http://localhost:9000/health
   ```

2. **Test proxy locally:**
   ```bash
   curl -X POST http://localhost:9000/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
   ```

### Why This Approach Works

**Transport Bridging:**
- Our server speaks basic HTTP JSON-RPC
- ChatGPT Desktop expects Streamable HTTP
- Proxy translates between the two protocols

**Network Access:**
- ChatGPT Desktop may be sandboxed from localhost
- Public HTTPS tunnel bypasses network restrictions
- Maintains security through controlled proxy layer

**Development Benefits:**
- Continue using Claude Desktop with direct localhost connection
- Add ChatGPT Desktop support without changing main server
- Proxy provides detailed logging for debugging protocol issues

## Testing Strategy

### MCP Wisdom Comprehensive Test Suite
**Location:** `scripts/test-mcp-wisdom.sh`

```bash
# Quick test with current environment
./scripts/test-mcp-wisdom.sh

# Full comprehensive test suite
./scripts/test-mcp-wisdom.sh --comprehensive

# Create isolated test environment
./scripts/test-mcp-wisdom.sh --isolated
```

**Test Coverage:**
- Environment validation (Docker, backend health, MCP endpoint)
- Tool functionality (all 8 MCP tools)
- Permission enforcement (allow/deny rules, precedence)
- Security testing (path traversal, unauthorized access)
- Performance validation (response times, resource usage)
- Edge case handling (errors, malformed requests)

## Project Structure
```
MCPFileServer/
├── backend/                  # Python FastAPI backend (Query Engine)
├── frontend/                 # React TypeScript frontend (UI)
├── indexer/                  # Python background service for indexing
├── config/                   # Global configuration
├── data/                     # SQLite database (gitignored)
├── docs/                     # Phase documentation and guides
├── scripts/                  # Testing and utility scripts
├── tickets/                  # Development tickets and issue tracking
├── docker-compose.yml        # 4-service orchestration
├── chatgpt_proxy.py          # MCP compatibility proxy for ChatGPT Desktop
├── .env                      # Environment variables
├── README.md                 # Main project documentation
└── CLAUDE.md                 # This file - Project context for Claude
```

## Critical Production Issues Resolved
**All production-blocking issues from multiple independent reviews have been resolved:**

- ✅ **Database URL Misconfiguration**: Backend correctly connects to database file
- ✅ **Indexer Import Errors**: All duplicate import issues resolved
- ✅ **Frontend 404 Cascade**: Graceful empty state handling
- ✅ **SQLAlchemy Parameter Format**: Fixed database bootstrap query handling
- ✅ **Environment Variable Handling**: Corrected Docker container configurations
- ✅ **Qdrant Test Mocking**: Integration tests validate real infrastructure
- ✅ **DocumentChunk Export**: Added to models/__init__.py barrel exports
- ✅ **Processing Efficiency**: Non-text file filtering prevents wasteful job creation

## Current Performance Metrics ✅
- **Service Health:** All health checks passing (backend, indexer, frontend, qdrant)
- **MCP Response Times:** Tool calls complete in <100ms average, search in <350ms
- **Database Operations:** Workspace CRUD operations in <50ms
- **Permission Resolution:** Sub-millisecond with Trie caching and O(1) filtering
- **File Watching:** Indexer monitors with 2-second debounce and crash recovery
- **WebSocket Connectivity:** Real-time UI updates with <100ms latency
- **Test Coverage:** 49+ comprehensive tests with TDD methodology
- **Force Reindex Performance:** Soft reindex ~2-5s per 1000 files, Hard reset ~10-30s per 1000 files

## Next Phase: Phase 4B M3 Semantic Search 📋

**Ready for Semantic Search Development:**
- 📖 `docs/Phase4B-M2-Implementation-Summary.md` - Complete M2 achievement overview
- 📖 `docs/Phase4B-Plan.md` - Updated with M2 completion and M3 roadmap
- 🎯 **M3 Objectives**: Vector embeddings, semantic search, hybrid fusion, 3 new semantic MCP tools
- 🔗 **Foundation Ready**: DocumentChunk model, Qdrant integration, PermissionPostprocessor reusable

## Development Philosophy
1. **Simplicity First:** Single `docker-compose up` to start everything
2. **Clear Separation:** Backend handles logic, frontend is presentational
3. **Real-time by Default:** WebSockets for instant feedback
4. **Security through Clarity:** Explicit permissions with formal precedence
5. **TDD Compliance:** Test-first methodology with comprehensive coverage
6. **Production Ready:** Comprehensive error handling and performance optimization

## Getting Help
- **Architecture Details:** See `README.md` and `docs/` folder
- **API Documentation:** http://localhost:8000/docs when running
- **Version History:** Complete `changelog.md` with implementation details
- **Docker Logs:** `docker-compose logs -f [service]` for debugging

---

**🎉 MCP KnowledgeExplorer Phase 4B M2 Complete - Production-Ready Keyword Search!**

*Phase 4B M2 delivers comprehensive full-text search capabilities with FTS5, trigram tokenization, permission filtering, and the 8th MCP tool. The system provides 2,400+ lines of tested code with sub-350ms search performance and zero data leakage through workspace security.*

**Ready for Phase 4B M3 Semantic Search Development.**

---
*Last updated: 2025-01-24 - Phase 4B M2 Complete*

## Operational Notes
- **search_fulltext tool**: 8th MCP tool with comprehensive FTS5 support, highlighting, and filtering
- **PermissionPostprocessor**: O(1) security filtering using pre-computed allowed path sets
- **FTS5 Implementation**: Virtual table with trigram tokenizer enables typo-tolerant search
- **Processing Pipeline**: TEXT_EXTRACT → CHUNK → FTS_INDEX fully operational with LlamaIndex
- **Config Shim**: env_config.py re-exports for stable imports across tests/local runs
- **Docker Health**: All services include requests library for proper healthchecks
- **Path Handling**: Host paths mounted to container `/source`; services use `/source` internally

## Force Reindex Feature (Ticket 019 - ✅ Version 4.4.0 Complete)

### Overview
Administrative "Force Reindex" capability providing complete control over the content indexing pipeline. This feature enables administrators to rebuild indexes from scratch or refresh indexing flags, addressing scenarios such as recovery from indexing pipeline bugs, data corruption, system updates, or large-scale file system changes. Available through both Web UI and CLI for maximum operational flexibility.

### Architecture & Core Components

**System Flow:**
```
Web UI/CLI → Admin API → ReindexService → Database Operations → Indexer Jobs
                                    ↓
                           Maintenance Mode Control
```

**Key Components:**
- **ReindexService** (`backend/app/services/reindex_service.py`): Business logic orchestrator
- **Reindex API** (`backend/app/api/reindex.py`): REST endpoints with admin authentication
- **Database Models** (`backend/app/models/reindex.py`): ReindexBatch, SystemFlag tracking
- **CLI Tool** (`scripts/trigger_reindex.py`): Programmatic access for automation
- **Web UI Integration** (`frontend/src/components/IndexerDashboard.tsx`): Simplified interface

### Features & Capabilities

**Two Reindex Modes:**
- **Soft Reindex (Recommended)**: Non-destructive operation that clears indexed flags and re-queues files while preserving existing document_chunks and FTS data
- **Hard Reset (Destructive)**: Complete rebuild that purges all document_chunks, removes FTS entries, clears pending/failed jobs, and rebuilds everything from scratch

**Advanced Features:**
- **Chunked Processing**: 5000 files per chunk to prevent memory exhaustion
- **Maintenance Mode Coordination**: Pauses watcher/worker during critical operations
- **Scope Filtering**: Filter by path prefix and file types for targeted reindexing
- **Batch Management**: Full control with pause, resume, cancel operations
- **Progress Tracking**: Real-time status with processed counts, failure tracking, ETA calculations
- **Dry Run Support**: Preview operations without making changes
- **Transactional Safety**: Atomic operations with rollback support on failure

### Web UI Access (Simplified Interface)

1. Navigate to **Indexer** tab in web interface (http://localhost:5173)
2. Click **Force Reindex** dropdown button
3. Select reindex mode:
   - **Soft Reindex (recommended)** - Non-destructive reindexing
   - **Hard Reset ⚠️** - Complete rebuild (destructive)
4. Click to start operation immediately (no confirmation dialogs)
5. Monitor real-time progress with:
   - Progress percentage and processed file counts
   - Processing rate (files per minute) and ETA
   - Pause/Resume/Cancel controls
   - Detailed batch status information

### CLI Operations & Automation

**Basic Commands:**
```bash
# Trigger soft reindex (all files, recommended)
python scripts/trigger_reindex.py trigger --mode soft

# Trigger hard reset (all files, destructive)
python scripts/trigger_reindex.py trigger --mode hard

# Path-filtered reindexing
python scripts/trigger_reindex.py trigger --mode soft --path /projects

# Include all file types (not just text)
python scripts/trigger_reindex.py trigger --mode soft --no-text-only

# Dry run to preview changes
python scripts/trigger_reindex.py trigger --mode soft --dry-run

# Wait for completion with progress monitoring
python scripts/trigger_reindex.py trigger --mode soft --wait
```

**Batch Management:**
```bash
# Check batch status
python scripts/trigger_reindex.py status <batch_id>

# Real-time status monitoring
python scripts/trigger_reindex.py status <batch_id> --watch

# List all batches (active and historical)
python scripts/trigger_reindex.py list --all

# Control batch execution
python scripts/trigger_reindex.py pause <batch_id>
python scripts/trigger_reindex.py resume <batch_id>
python scripts/trigger_reindex.py cancel <batch_id>
```

**System Management:**
```bash
# Check overall system status
python scripts/trigger_reindex.py system

# Emergency: Clear stuck maintenance mode
python scripts/trigger_reindex.py clear-maintenance

# Custom API configuration
python scripts/trigger_reindex.py --api-base http://localhost:8000 \
  --api-key custom-admin-key trigger --mode soft
```

### REST API Integration

**Authentication:**
All admin endpoints require the `X-Admin-Key` header with admin authentication.

**Create Reindex Batch:**
```bash
curl -X POST http://localhost:8000/admin/reindex/force \
  -H "X-Admin-Key: admin-secret-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "soft",
    "scope": {
      "path_prefix": "/projects",
      "text_only": true
    },
    "dry_run": false
  }'
```

**Monitor Progress:**
```bash
# Get specific batch status
curl -H "X-Admin-Key: admin-secret-key-change-me" \
  http://localhost:8000/admin/reindex/batches/{batch_id}

# Control batch execution
curl -X POST http://localhost:8000/admin/reindex/batches/{batch_id}/pause \
  -H "X-Admin-Key: admin-secret-key-change-me"
```

### Implementation Details

**Database Schema:**
- **reindex_batches**: Tracks batch operations with progress counters, status, timing
- **system_flags**: Manages maintenance mode and system-wide settings
- **Enhanced index_jobs**: Added batch_id field for job association and deduplication

**Security & Safety:**
- Admin-only access via configurable API key authentication
- Transactional database operations with rollback on failure
- Maintenance mode prevents race conditions with normal indexing
- Single active batch constraint prevents conflicts
- Idempotent operations safe for restart after crashes

**Performance Characteristics:**
- Soft reindex: ~2-5 seconds per 1000 files (flag clearing and job creation)
- Hard reset: ~10-30 seconds per 1000 files (includes chunk deletion and FTS cleanup)
- Memory usage: <100MB additional during processing (chunked operations)
- Concurrent processing: Single active batch ensures resource control
- Error handling: Failed files tracked separately without stopping batch

**Error Recovery & Troubleshooting:**
- Comprehensive error logging with batch IDs and operation details
- Resumable operations after service restarts
- Emergency maintenance mode clearing for stuck situations
- Detailed batch history preserved for audit and debugging