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

### 3.1. High-Level Diagram

```ascii
+-----------------------------+
|        LLM Agent            |
+-------------+---------------+
              | (MCP over HTTP)
+-------------v------------------------------------------------------------------+
|                            Backend Service (FastAPI)                           |
| +------------------------+   (QUERY ENGINE)         +------------------------+ |
| |     MCP Endpoint       |------------------------->|     SearchService      | |
| +------------------------+                          | (LlamaIndex)           | |
|                                                       +------------+-----------+ |
| +------------------------------------------------------------------+-----------+ |
|            (SQL) |                                                  | (Permission Check)
|                  |                                                  |
| +----------------v--------------------------------+      +----------v---------+
| |        Application DB (SQLite)                 |      |   PermissionService  |
| | (Metadata, FTS Index, Jobs)                    |      +--------------------+
| +------------------------------------------------+
|                     | (Qdrant Client)
| +-------------------v------------------------------------------------------+
| |                          Vector DB Service (Qdrant)                        |
| +--------------------------------------------------------------------------+
+------------------------------------------------------------------------------+
                                  ^
                                  | (Populates Indexes)
+---------------------------------+----------------------------------------------+
| |                           Indexer Service (Python)                         | |
| | +-----------------------+ +---------------------+ +----------------------+ | |
| | | Resumable Job Queue   | | LlamaIndex Ingestion| | CPU Embedding Model  | | |
| | +-----------------------+ +---------------------+ +----------------------+ | |
| +--------------------------------------------------------------------------+ |
+------------------------------------------------------------------------------+
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

## 5. Technology Stack

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