# MCP KnowledgeExplorer

> **🎉 Status: Now Implementing Phase 4: Advanced Search & Retrieval!**
> The project has successfully completed its goal of building a production-ready, database-driven workspace management system. The next major phase will transform the application into a powerful knowledge retrieval engine by adding comprehensive metadata, keyword, and semantic search capabilities.

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

---

## 1. Introduction

### 1.1. Purpose

This project is a **production-ready Model Context Protocol (MCP) server** that enables AI agents to safely interact with your local file system. It provides a web-based management interface for real-time monitoring and granular permission control, and is being extended with a powerful, local-first search and retrieval engine.

### 1.2. Current Status - ✅ Phase 3B Complete

The application currently features a complete, database-driven workspace management system with a two-panel permission editor and real-time UI updates. The focus is now on implementing Phase 4.

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

### 4.1. Existing File System Tools
| Tool | Parameters | Description |
|------|------------|-------------|
| `read_file` | `path: string` | Read complete file contents |
| `list_files` | `path: string` | List directory contents with metadata |
| `write_file` | `path: string, content: string` | Write content to file |

### 4.2. Planned Search Tools (Phase 4)
| Tool | Description |
|------|-------------|
| `list_all_files` | Lists all discoverable files and directories within the workspace scope, with depth control. |
| `search_files_by_metadata` | Searches for files based on properties like filename, file type, size, and modification date. |
| `search_content_by_keyword` | Performs a high-quality, typo-tolerant full-text search across all document content. |
| `search_content_by_semantic` | Finds text chunks based on conceptual similarity to a natural language query. |

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
| **Containerization** | Docker Compose | Multi-container application orchestration. | ✅ |
| **Backend** | FastAPI | Hosts the MCP/API endpoints and the Query Engine. | ✅ |
| **Frontend** | React, Vite | Web UI for configuration and monitoring. | ✅ |
| **Application DB** | SQLite | Stores workspaces, permissions, file metadata, FTS index, and indexer jobs. | ✅ |
| **RAG Framework** | **LlamaIndex** | Core toolkit for data ingestion, indexing, and querying. | 📋 Planned |
| **Vector Database** | **Qdrant** | High-performance storage and retrieval of vector embeddings. | 📋 Planned |
| **Embedding Model** | **`paraphrase-multilingual-MiniLM-L12-v2`** | A high-quality, CPU-based multilingual model to ensure broad compatibility. | 📋 Planned |
| **OCR Engine**| **Tesseract** | Extracts text from images and scanned documents. | 📋 Planned |

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

### 7.2. Indexer Dashboard
The UI will feature a dedicated "Indexer Dashboard" to monitor the status of the indexing process, view metrics, and pause or resume the indexer to manage system resources.

---

*(The remainder of this document, including setup and troubleshooting for the existing system, remains unchanged.)*