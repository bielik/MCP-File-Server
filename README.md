# MCP KnowledgeExplorer

> **🎉 Status: Phase 4A COMPLETE - Ready for Phase 4B Semantic Search!**
> Phase 4A advanced search infrastructure is 100% complete with comprehensive documentation for independent development. All critical production issues have been resolved, and the system is fully operational with indexer service, 7 MCP tools, and robust job processing. Complete implementation guide and Phase 4B roadmap provided for semantic search development.

## Quick Start

```bash
# Start the entire system with one command
# This will now start three services: backend, frontend, and the new indexer
docker-compose up --build

# Access the services
# Frontend UI: http://localhost:5173
# Backend API: http://localhost:8000
# MCP HTTP: http://localhost:8000/mcp (for AI clients)

# View logs for a specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f indexer
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
- ✅ Tests all 7 MCP tools with permission enforcement
- ✅ Security testing (directory traversal, unauthorized access)
- ✅ Performance validation (sub-25ms response times)
- ✅ JSON reporting with detailed metrics

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

### 4.2. Planned Advanced Search Tools (Phase 4)
| Tool | Description | Status |
|------|-------------|---------|
| `search_content_by_keyword` | High-quality, typo-tolerant full-text search | 📋 Planned |
| `search_content_by_semantic` | Semantic similarity search using embeddings | 📋 Planned |

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

---

## 6. Technology Stack

| Category | Technology | Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Containerization** | Docker Compose | 3-service orchestration: backend, frontend, indexer | ✅ Phase 4A |
| **Backend** | FastAPI | MCP/API endpoints and Query Engine with search tools | ✅ Phase 4A |
| **Frontend** | React, Vite | Web UI with indexer dashboard and controls | ✅ Phase 4A |
| **Indexer** | Python/Watchdog | Background file monitoring and job processing | ✅ Phase 4A |
| **Application DB** | SQLite (WAL) | Concurrent storage: workspaces, permissions, files, jobs | ✅ Phase 4A |
| **Job Queue** | SQLite | Crash-resilient job queue with atomic claiming | ✅ Phase 4A |
| **RAG Framework** | **LlamaIndex** | Core toolkit for data ingestion, indexing, and querying. | 📋 Phase 4B |
| **Vector Database** | **Qdrant** | High-performance storage and retrieval of vector embeddings. | 📋 Phase 4B |
| **Embedding Model** | **`paraphrase-multilingual-MiniLM-L12-v2`** | A high-quality, CPU-based multilingual model to ensure broad compatibility. | 📋 Phase 4B |
| **OCR Engine**| **Tesseract** | Extracts text from images and scanned documents. | 📋 Phase 4B |

---

## 6. Project Structure

```
MCPFileServer/
├── 📁 backend/                  # Python FastAPI backend (Query Engine)
├── 📁 frontend/                 # React TypeScript frontend (UI)
├── 📁 indexer/                  # NEW: Python background service for indexing
├── 📁 config/                   # Global configuration
├── 📁 data/                      # SQLite database (gitignored)
├── 📄 docker-compose.yml       # 3-service setup: backend, frontend, indexer
├── 📄 .env                      # Environment variables
├── 📄 README.md                 # This file
└── 📄 plan.md                   # Development roadmap
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

### 7.3. MCP Tools Testing

**Complete MCP Protocol Validation:**
```bash
# Test all 7 MCP tools with comprehensive suite
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