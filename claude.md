# MCP Research File Server - Project Context & Architecture

## 1. Project Overview

**Project Name:** MCP Research File Server
**Type:** Model Context Protocol (MCP) File Server for Research
**Current Status:** Foundational backend and UI are complete. This document outlines the plan to evolve it into a full-featured, AI-powered research assistant.
**Purpose:** To create a sophisticated, local-first MCP server that enables AI agents to assist with research by providing intelligent file management and advanced search capabilities.

---

## 2. Target Architecture: The Integrated Monolithic Approach

The project will be built using a unified **Node.js/TypeScript backend** that handles all functionality in a single, manageable process. This architecture is designed for stability, simplicity, and performance, eliminating the need for complex external microservices which proved problematic in earlier design iterations.

* **Single Process, Single Language:** The MCP server, web API, file operations, document parsing, and all search functionality will run within one Node.js process.
* **Staged AI Integration:** We will first implement a robust keyword search using FlexSearch. In a later phase, we will add semantic and multimodal search capabilities using the `@xenova/transformers` library.
* **Unified Logic:** A single server entry point will manage all operations, sharing a unified configuration and state to ensure consistency and reliability.

---

## 3. Technology Stack

### Unified Backend (Node.js/TypeScript)

* **Runtime:** Node.js (v18+)
* **Language:** TypeScript
* **MCP Server:** Official **`@modelcontextprotocol/sdk`** for guaranteed protocol compliance.
* **Web API:** Express.js for serving the frontend UI and handling API requests.
* **Keyword Search:** **FlexSearch** for fast, in-memory, multi-language text search.
* **Semantic/Multimodal AI (Future Phase):** **`@xenova/transformers`** for running a compatible CLIP model natively.
* **Document Processing:** **`pdf-parse`** for text extraction.
* **Vector Database (Future Phase):** **Qdrant** for storing and searching multimodal embeddings.

### Web Interface (React)

* **Framework:** React with TypeScript and Vite.
* **State Management:** **Zustand** for simple, robust global state management.
* **UI:** Tailwind CSS for styling.
* **Real-time Updates:** WebSockets for live communication between the frontend and backend.

---

## 4. Key Features & Staged Workflow

The server's features will be built incrementally to ensure stability at each step.

### Stage 1: Keyword Search Foundation (Immediate Goal)

* **Document Processing:** A pipeline that automatically:
    1.  Parses PDF documents using `pdf-parse` to extract raw text.
    2.  Indexes the extracted text into a FlexSearch document index.
* **Agent Tool: `search_text`:** A fast and reliable keyword search tool available to AI agents.

### Stage 2: Semantic & Multimodal Search (Future Phase)

* **Enhanced Document Processing:** The pipeline will be upgraded to:
    1.  Extract images from PDFs using a robust tool like the **Poppler** utility.
    2.  Generate vector embeddings for text chunks and images using `@xenova/transformers`.
    3.  Store these embeddings in a **Qdrant** vector database.
* **New Agent Tools:**
    * **`search_semantic`:** For conceptual, meaning-based search.
    * **`search_multimodal`:** For cross-modal (text-to-image) search.

---

## 5. Target Project Structure

This structure promotes clear separation of concerns and maintainability.

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
│       ├── components/         # React components
│       ├── hooks/              # Custom React hooks
│       ├── services/           # API and WebSocket services
│       └── state/              # Zustand store for global state
└── .env                        # Single source of truth for all configuration