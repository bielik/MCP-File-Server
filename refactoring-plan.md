# MCP Research Server - Refactoring Plan

**Objective:** Refactor the existing project into a stable, maintainable, and performant **Integrated Monolithic Architecture** using a single Node.js/TypeScript backend. This plan eliminates the unreliable Python microservices, simplifies the entire stack, and provides a clear, test-driven path to completion.

**Guiding Principle:** Every step must result in a functional, testable improvement. No mock implementations are permitted.

---

## Phase 1: Foundation & Simplification (Estimated: 2-3 Days)

**Goal:** Consolidate the project into a single, stable, runnable Node.js server with a clean codebase.

### Step 1.1: Code & Dependency Cleanup
- **Description:** Remove all code related to the Python microservices and dead backend files.
- **Tasks:**
    - [ ] Delete all Python scripts from the `services/` directory (`mclip-service.py`, `docling-service.py`, etc.).
    - [ ] Delete all Python-related management scripts (`fix-service-deployment.py`, `fix-pytorch-gpu.py`, etc.).
    - [ ] Delete all redundant MCP server test files from `backend/` (`mcp-basic-test.ts`, `mcp-final.ts`, `mcp-minimal.js`, `mcp-debug.ts`, etc.).
    - [ ] Review `package.json` in both `backend/` and `frontend/` to remove any unnecessary dependencies related to the old architecture.
- **Testing:**
    - The project should still install dependencies (`npm install`) and start without errors, even though some functionality will be temporarily broken.

### Step 1.2: Unify Configuration
- **Description:** Consolidate all environment variables into a single `.env` file at the project root to eliminate configuration conflicts.
- **Tasks:**
    - [ ] Create a single `.env` file in the project root.
    - [ ] Define all necessary variables: `MCP_PORT`, `WEB_API_PORT`, `QDRANT_URL`, etc. Use consistent port numbers (e.g., `WEB_API_PORT=3006`).
    - [ ] Create a unified `backend/src/config/index.ts` module to load and export all configuration variables using `dotenv`.
    - [ ] Update all backend files to import configuration from this single source.
    - [ ] Update `frontend/vite.config.ts` to use the `WEB_API_PORT` for its proxy setting, ensuring frontend and backend can communicate.
- **Testing:**
    - Start the backend (`npm run dev:backend`). It should load the configuration from the root `.env` file without errors.
    - The frontend dev server (`npm run dev:frontend`) should successfully proxy API requests to the backend.

### Step 1.3: Consolidate Server Logic
- **Description:** Refactor the fragmented server code into a single, clean entry point that manages both the Web API and the MCP server.
- **Tasks:**
    - [ ] Create a new `backend/src/main.ts` as the primary application entry point.
    - [ ] Refactor the existing Express server logic from `backend/server/web-server.ts` into its own class or module.
    - [ ] Refactor the core MCP server logic from `backend/mcp-server-test.ts` into a clean `McpServer` class.
    - [ ] The `main.ts` file will be responsible for initializing the configuration, starting the web server, and then starting the MCP server.
    - [ ] Update `backend/package.json` so that `npm run dev` executes this new `main.ts` file.
- **Unit Tests:**
    - Write a unit test to ensure the `McpServer` class correctly registers tools.
    - Write a unit test to ensure the web server starts and a basic `/api/health` endpoint returns a `200 OK` status.

---

## Phase 2: Native AI & Processing Integration (Estimated: 3-4 Days)

**Goal:** Re-implement the entire multimodal processing pipeline within the Node.js backend using native JavaScript libraries and minimal external tools.

### Step 2.1: Implement the AI Service
- **Description:** Create a service to handle all AI model loading and embedding generation using `@xenova/transformers`.
- **Tasks:**
    - [ ] Add `@xenova/transformers` to the backend `package.json`.
    - [ ] Create `backend/src/services/AiService.ts`.
    - [ ] This service will be a singleton that loads the `Xenova/clip-vit-base-patch32` model on application startup.
    - [ ] Implement two public methods: `embedText(text: string): Promise<number[]>` and `embedImage(imageBuffer: Buffer): Promise<number[]>`.
- **Unit Tests:**
    - Write a test to ensure the `AiService` successfully loads the model.
    - Write a test that provides sample text to `embedText` and verifies it returns a vector of the correct dimension (512).
    - Write a test that provides a sample image buffer to `embedImage` and verifies it returns a vector of the correct dimension (512).

### Step 2.2: Implement the Document Parser
- **Description:** Create a service to handle PDF parsing, replacing the `Docling` Python service. The `Poppler` utility will be used for robust image extraction, which is a stable and minimal external dependency.
- **Tasks:**
    - [ ] Add `pdf-parse` to the backend `package.json`.
    - [ ] Add a prerequisite check to ensure `Poppler` (specifically the `pdfimages` utility) is available in the system's PATH.
    - [ ] Create `backend/src/features/processing/DocumentParser.ts`.
    - [ ] Implement a method that takes a PDF file path. It will:
        1. Use `pdf-parse` to extract all text and metadata.
        2. Use Node.js's `child_process` to execute the `pdfimages` command, extracting all raw images from the PDF into a temporary directory.
        3. Read the extracted image files into buffers.
        4. Return the text content and an array of image buffers.
- **Unit Tests:**
    - Write a test that passes a sample PDF to the parser and asserts that both text content and a non-zero number of image buffers are returned.

### Step 2.3: Implement the Indexer
- **Description:** Create an `Indexer` service that orchestrates the processing pipeline.
- **Tasks:**
    - [ ] Create `backend/src/features/processing/Indexer.ts`.
    - [ ] This service will have a primary method: `indexFile(filePath: string)`.
    - [ ] Inside this method, it will:
        1. Call the `DocumentParser` to get text and images.
        2. Implement a basic chunking strategy for the extracted text.
        3. Call the `AiService` to generate embeddings for each text chunk and each extracted image.
        4. Call the `VectorDb` service (`src/services/VectorDb.ts`, a wrapper for the Qdrant client) to store the embeddings and their associated metadata (file path, page number, content type) in Qdrant.
- **Integration Test:**
    - Write a test that calls `Indexer.indexFile` with a path to a sample PDF. The test should verify that after execution, Qdrant contains new entries for both text chunks and images corresponding to the content of that PDF. This test validates the entire native processing pipeline end-to-end.

---

## Phase 3: Robust Search Implementation (Estimated: 2-3 Days)

**Goal:** Implement the three agent-facing search tools using the new native AI pipeline.

### Step 3.1: Implement Keyword Search
- **Description:** Implement the `search_text` tool using FlexSearch.
- **Tasks:**
    - [ ] Add `flexsearch` to the backend `package.json`.
    - [ ] Create `backend/src/features/search/keywordSearch.ts`. This module will manage the FlexSearch index.
    - [ ] Modify the `Indexer` service to also add text chunks to the FlexSearch index after processing a file.
    - [ ] Implement the search logic and connect it to the `search_text` MCP tool handler.
- **Unit Tests:**
    - Write a test to index sample documents in FlexSearch and then perform a search, asserting that the correct documents are returned.

### Step 3.2: Implement Semantic & Multimodal Search
- **Description:** Implement the `search_semantic` and `search_multimodal` tools.
- **Tasks:**
    - [ ] Create `backend/src/features/search/semanticSearch.ts`.
    - [ ] Implement the search logic:
        1. Take the user's query (text or image).
        2. Use the `AiService` to generate an embedding for the query.
        3. Use the `VectorDb` service to perform a similarity search in Qdrant against the indexed text and/or image vectors.
    - [ ] Connect the logic to the `search_semantic` and `search_multimodal` MCP tool handlers.
- **Integration Test:**
    - Write a test that first ensures a sample document is indexed (using the `Indexer`).
    - Then, perform a semantic search with a conceptually similar query.
    - Assert that the results returned from Qdrant include the content from the sample document. This validates the search pipeline end-to-end.

---

## Phase 4: Frontend State Management & Final Polish (Estimated: 1-2 Days)

**Goal:** Improve the reliability and user experience of the frontend.

### Step 4.1: Introduce Zustand for State Management
- **Description:** Refactor the frontend to use Zustand for managing global UI state.
- **Tasks:**
    - [ ] Add `zustand` to the `frontend/package.json`.
    - [ ] Create a store in `frontend/src/state/store.ts` to manage `currentPath`, `selectedFiles`, `serverStatus`, etc.
    - [ ] Refactor the `FileExplorer` and other components to use the Zustand store instead of local `useState` for shared state.
- **Testing:**
    - Manually verify that selecting files, navigating directories, and assigning permissions all correctly update the UI and reflect the state in the store. The application should feel more responsive and consistent.

### Step 4.2: Final Cleanup and Documentation Review
- **Description:** Perform a final review of the codebase and documentation to ensure consistency.
- **Tasks:**
    - [ ] Remove any remaining dead code or commented-out sections.
    - [ ] Ensure all code adheres to the ESLint and Prettier configurations.
    - [ ] Read through `README.md` and `claude.md` one last time to ensure they perfectly match the refactored codebase.
- **Final Test:**
    - Run the entire application and test every feature manually: file browsing, permission assignment (UI), and all three search tools (via an MCP client). The application should be fully functional and stable.