# MCP Research File Server - Implementation Plan

**Last Updated:** 2025-09-10
**Current Status:** Phase 1 (Foundation) Complete. Ready to begin Phase 2.
**Priority:** High

## 1. Project Objective

To build upon the existing foundational server to create a full-featured MCP server for AI-assisted research. This plan adopts a staged approach, prioritizing the implementation of a robust keyword search before introducing more complex semantic and multimodal capabilities.

## 2. Implementation Roadmap

### Phase 1: Foundation & Basic UI ✅ **COMPLETED**

This phase represents the current state of the project codebase. It provides a solid, working foundation for file system interaction and permission management.

* **Core Deliverables:**
    * [x] Basic MCP server with TypeScript SDK integration.
    * [x] Functional React-based file explorer UI for assigning permissions.
    * [x] A stable three-tier permission system (`context`/`working`/`output`).
    * [x] Basic file operation tools (`read_file`, `write_file`, `list_files`).
    * [x] WebSocket integration for real-time UI updates.

---

### Phase 2: Keyword Search Implementation (Next Step)

* **Goal:** Implement a complete, fast, and reliable keyword search feature. This provides immediate value and a solid indexing foundation.
* **Key Deliverables:**
    1.  **Document Processing Pipeline:**
        * [ ] Create a `DocumentParser` service using `pdf-parse` to reliably extract text from PDF files.
        * [ ] Create an `Indexer` service that orchestrates the process: when a file is added, it should be parsed and its text content indexed.
    2.  **Keyword Search Service:**
        * [ ] Integrate **FlexSearch** into a `KeywordSearchService`.
        * [ ] The `Indexer` will feed extracted text into this service to build and maintain the search index.
    3.  **MCP Tool Integration:**
        * [ ] Implement the `search_text` tool handler in `backend/server/handlers.ts`.
        * [ ] This handler will use the `KeywordSearchService` to find documents matching the agent's query.
        * [ ] The handler will format results clearly, including the file path and a relevant text snippet.
    4.  **Testing:**
        * [ ] Write unit tests for the `DocumentParser` and `KeywordSearchService`.
        * [ ] Create an end-to-end integration test that adds a PDF, searches for its content via the `search_text` tool, and verifies the correct result is returned.

---

### Phase 3: Semantic & Multimodal Search Integration (Future Phase)

* **Goal:** Enhance the search capabilities with AI-powered semantic and cross-modal search.
* **Key Deliverables:**
    1.  **Upgrade Processing Pipeline:**
        * [ ] Enhance the `DocumentParser` to also extract images from PDFs, likely by integrating the **Poppler** command-line utility.
        * [ ] Create an `AiService` using `@xenova/transformers` to generate vector embeddings for text chunks and images.
        * [ ] Integrate **Qdrant** via a `VectorDbService` to store these embeddings.
    2.  **Implement New Search Tools:**
        * [ ] Implement the `search_semantic` tool handler, which will use the `AiService` and `VectorDbService` to find conceptually similar text.
        * [ ] Implement the `search_multimodal` tool handler for text-to-image search.
    3.  **Result Ranking:**
        * [ ] Develop a ranking algorithm to combine keyword and semantic search results for relevance.
    4.  **Testing:**
        * [ ] Write unit tests for the `AiService` and `VectorDbService`.
        * [ ] Write integration tests for the new `search_semantic` and `search_multimodal` tools.

---

### Phase 4: UI Integration & Final Polish

* **Goal:** Expose all search functionality through the web UI and complete the agent toolset.
* **Key Deliverables:**
    * [ ] A `POST /api/search` endpoint on the backend that can handle keyword, semantic, and multimodal search types.
    * [ ] A "Search" tab in the frontend UI with a search bar and results display.
    * [ ] A `create_folder` tool for agents to organize their output.
    * [ ] Frontend state managed cleanly by **Zustand**.