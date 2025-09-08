# MCP Research File Server - Project Context & Setup Guide

## Project Overview
**Project Name:** MCP Research File Server
**Type:** Multimodal Model Context Protocol (MCP) File Server for Research
**Status:** Undergoing refactoring to an Integrated Monolithic Architecture
**Purpose:** Create a sophisticated, stable, and local-first MCP server that enables AI agents to assist with research by providing intelligent, multimodal access to local files.

## Core Architecture: Integrated Monolithic Approach
This project uses a unified **Node.js/TypeScript backend** that handles all functionality in a single process. This architecture was chosen to maximize stability, reduce complexity, and simplify deployment by eliminating the need for external Python microservices.

- **Single Process, Single Language:** The MCP server, web API, file operations, document parsing, and AI-powered embedding generation all run within one Node.js process.
- **Native AI/ML:** The system leverages modern JavaScript libraries to run powerful AI models natively, removing all Python dependencies.
- **Unified Logic:** A single server entry point manages all operations, sharing a unified configuration and state, which ensures consistency and reliability.

## Technology Stack

### Unified Backend (Node.js/TypeScript)
- **Runtime:** Node.js (v18+)
- **Language:** TypeScript
- **MCP Server:** Official **`@modelcontextprotocol/sdk`** for guaranteed protocol compliance.
- **Web API:** Express.js for serving the frontend UI and handling API requests.
- **Multimodal AI:** **`@xenova/transformers`** for running the M-CLIP model natively to generate both text and image embeddings.
- **PDF Processing:** **`pdf-parse`** for text extraction and **Poppler (`pdfimages`)** for robust, high-fidelity image extraction.
- **Vector Database:** **Qdrant** for storing and searching multimodal embeddings.
- **Keyword Search:** **FlexSearch** for fast, in-memory text search.

### Web Interface (React)
- **Framework:** React with TypeScript and Vite.
- **State Management:** **Zustand** for simple, robust global state management.
- **UI:** Tailwind CSS for styling.
- **Real-time Updates:** WebSockets for live communication between the frontend and backend.

## Key Features & Workflow
- **Three-Tier Permissions:** A secure file system with `context` (read-only), `working` (read-write), and `output` (agent-controlled) directories, mirroring a typical research workflow.
- **On-Demand Document Processing:** When a file is added or requested, the pipeline automatically:
    1.  Parses the document, extracting text with `pdf-parse` and images via the `pdfimages` utility.
    2.  Chunks the text into meaningful segments.
    3.  Uses the native M-CLIP model via `@xenova/transformers` to generate vector embeddings for all text chunks and images.
    4.  Stores the embeddings in Qdrant and indexes the text in FlexSearch.
- **Agent-Choice Search Strategy:** AI agents are provided with three distinct tools, allowing them to choose the best search method for their specific query:
    1.  **`search_text`:** Fast keyword search powered by FlexSearch.
    2.  **`search_semantic`:** Conceptual, meaning-based search powered by M-CLIP embeddings in Qdrant.
    3.  **`search_multimodal`:** Cross-modal search (text-to-image, image-to-text) to find visual data or related text.

## Project Structure
```plaintext
/
├── backend/
│   └── src/
│       ├── core/               # Main server logic (MCP, Web API)
│       ├── features/           # Self-contained modules (files, processing, search)
│       ├── services/           # Wrappers for external libraries (AI, Vector DB)
│       └── main.ts             # Application entry point
├── frontend/
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       └── state/              # Zustand store for global state
└── .env                        # Single source of truth for configuration

## Memory Bank Documentation (Updated: September 5, 2025)

**Status:** ✅ FULLY SYNCHRONIZED with actual codebase implementation  
**Test Results:** 67/67 tests passing across 3 comprehensive test files  
**Implementation Accuracy:** 100% verified against actual code

The project includes comprehensive memory bank documentation that accurately reflects the current implementation state:

- **CLAUDE-patterns.md** - Testing patterns, mock strategies, and development approaches
- **CLAUDE-architecture.md** - Current implementation status and architectural state  
- **CLAUDE-development.md** - Testing workflow and phase completion tracking
- **CLAUDE-status.md** - Memory bank synchronization status and accuracy verification

These files provide trustworthy navigation aids that reflect actual implementation reality, distinguishing clearly between:
- ✅ **REAL Implementations** - MCP handlers, file operations, TypeScript service classes
- 🔄 **MOCKED in Tests** - AI/Vector services (real classes exist but connection pending)
- ⏳ **PENDING** - Frontend interface and full service integration

**Current Phase:** Phase 4 Task 1 COMPLETED, Task 2 (Frontend Search Experience) PENDING