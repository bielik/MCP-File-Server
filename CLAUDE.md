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
**Shared Filesystem:** `C:/Users/MartinBielik/MCP Test/` (mounted to `/source`)
- `materials/` - Read-only access (course materials and documentation)
- `projects/` - Read-write access (development projects and code)
- `private stuff/` - No access (default deny)

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
SHARED_FS_PATH=C:/Users/MartinBielik/MCP Test
ENABLE_DATABASE_PERMISSIONS=true
```

## MCP Integration with Claude Code

### Setup
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
├── docker-compose.yml        # 4-service orchestration
└── .env                      # Environment variables
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