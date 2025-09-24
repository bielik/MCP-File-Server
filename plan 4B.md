# Final Phase 4B Implementation Plan: Advanced Search & Retrieval

This plan operationalizes the "Indexer-Query" architecture to deliver robust keyword and semantic search capabilities. It follows a Test-Driven Development (TDD) methodology and prioritizes a local-first, CPU-default approach while ensuring security and performance.

## 1. Final Technology Stack

-   **Vector Database**: **Qdrant**. A mature, high-performance vector DB that is simple to orchestrate via Docker.
-   **Keyword Search**: **SQLite FTS5 with `trigram` tokenizer**. The most efficient, integrated solution for typo-tolerant full-text search.
-   **RAG Framework**: **LlamaIndex**. To be used for its robust document parsers and text splitters.
-   **Embedding Model**: **`paraphrase-multilingual-MiniLM-L12-v2`**. The default for its excellent CPU performance and multilingual capabilities.
-   **Optional Reranker**: **`jina-ai/jina-reranker-v2-base-multilingual`**. A lightweight, CPU-friendly model enabled via the existing `RERANK_ENABLED` flag.

## 2. Database Schema Extensions

-   **New Table: `document_chunks`**: Will store the text content of each chunk.
    -   Fields: `id`, `file_id` (FK to `IndexedFile`), `ordinal`, `text`, `start_byte`, `end_byte`.
-   **New Virtual Table: `chunks_fts`**: An FTS5 table for keyword search.
    -   Configuration: `tokenize = 'trigram'`.
    -   Synchronization: Use SQLite triggers to automatically keep `chunks_fts` in sync with `document_chunks`.

## 3. Indexer Service Pipeline Extension

The existing job queue from Phase 4A will be extended with new job types.

-   **New Job Types**:
    1.  `TEXT_EXTRACT`: Parses raw file content into clean text.
    2.  `CHUNK`: Splits extracted text into manageable chunks.
    3.  `FTS_INDEX`: Populates the `document_chunks` and `chunks_fts` tables.
    4.  `EMBED`: Generates vector embeddings for each chunk and upserts them to the Qdrant collection.

## 4. Backend Query Engine (`SearchService`)

The `SearchService` will be upgraded to a full hybrid query engine.

-   **Retrieval Logic**: Implement hybrid search using **Reciprocal Rank Fusion (RRF)** to combine results from FTS5 and Qdrant.
-   **Permission Filtering (Critical)**: All search results **must** be passed through a `PermissionPostprocessor` class before being returned. This class will use the `doc_id` from a search result to look up the file's path and filter it against the active workspace's rules, using a pre-computed `set` of allowed paths for high performance.

## 5. New MCP Tools

Phase 4B will add four new tools, expanding the total from 7 to 11. All tools will support deterministic cursor pagination.

-   `search_fulltext(query: str, ...)`: Keyword-only search.
-   `search_semantic(query: str, ...)`: Vector-only similarity search.
-   `search_hybrid(query: str, ...)`: The primary search tool combining FTS and vector results.
-   `find_similar(doc_id: str, ...)`: "More like this" vector search.

---

## 6. Phased Implementation Plan (TDD Approach, 4-5 Weeks)

### M1 - Foundations (Database & Infrastructure)

#### **Tests to Write First:**

-   **`backend/tests/phase4b/test_database_schema.py`**:
    -   Asserts that `document_chunks` and `chunks_fts` tables are created correctly on startup.
    -   Tests the INSERT/UPDATE/DELETE triggers to ensure `chunks_fts` stays synchronized with `document_chunks`.
-   **`backend/tests/phase4b/test_qdrant_integration.py`**:
    -   A simple integration test to confirm the backend service can connect to the Qdrant container and get its health status.

#### **Implementation Steps:**

1.  **Task**: Implement the `document_chunks` and `chunks_fts` SQLAlchemy models and the corresponding FTS triggers in `backend/app/models/`.
2.  **Task**: Add the `qdrant` service to `docker-compose.yml` with a named volume for persistence.
3.  **Task**: Update `backend/` and `indexer/` `requirements.txt` with new dependencies (`llama-index`, `qdrant-client`, `sentence-transformers`).
4.  **Task**: Create a backfill script in `scripts/` to process existing files upon first run after the update.

### M2 - Keyword Search Path

#### **Tests to Write First:**

-   **`indexer/tests/phase4b/test_indexer_fts_pipeline.py`**:
    -   An integration test that creates a mock file, triggers the indexer, and asserts that the corresponding rows appear correctly in the `document_chunks` and `chunks_fts` tables.
-   **`backend/tests/phase4b/test_permission_postprocessor.py`** (New File):
    -   This is a critical test. It must create mock search results containing `doc_id`s for files that are both allowed and forbidden by the active workspace rules.
    -   Assert that the `PermissionPostprocessor` correctly filters out all forbidden results.
-   **`backend/tests/phase4b/test_search_service_keyword.py`**:
    -   Unit tests for the FTS5 query logic, testing phrase matching, typo tolerance, and ranking.
-   **`backend/tests/test_mcp_wisdom_comprehensive.py`** (Extend):
    -   Add a new test, `test_mcp_wisdom_search_fulltext`, to validate the `search_fulltext` tool's input/output schema and basic functionality against a known dataset.

#### **Implementation Steps:**

1.  **Task**: Extend the `JobProcessor` in the indexer to run the `TEXT_EXTRACT`, `CHUNK`, and `FTS_INDEX` jobs.
2.  **Task**: Implement the keyword search logic (FTS5 query) in the `SearchService`.
3.  **Task**: Implement the `PermissionPostprocessor` class and integrate it into the search workflow.
4.  **Task**: Ship the `search_fulltext` MCP tool.

### M3 - Semantic Search Path

#### **Tests to Write First:**

-   **`indexer/tests/phase4b/test_indexer_embedding_pipeline.py`**:
    -   An integration test that feeds a file to the indexer and asserts that vector embeddings are generated and upserted into a test Qdrant collection with the correct payload (`doc_id`, `chunk_id`, etc.).
-   **`backend/tests/phase4b/test_search_service_vector.py`**:
    -   Unit tests for the Qdrant query logic, including similarity search and payload retrieval.
-   **`backend/tests/phase4b/test_permission_postprocessor.py`** (Extend):
    -   Add test cases to ensure the postprocessor correctly filters results originating from Qdrant.
-   **`backend/tests/test_mcp_wisdom_comprehensive.py`** (Extend):
    -   Add `test_mcp_wisdom_search_semantic` and `test_mcp_wisdom_find_similar` to validate the new tools' contracts.

#### **Implementation Steps:**

1.  **Task**: Extend the `JobProcessor` to run the `EMBED` job, generating embeddings and upserting them to Qdrant.
2.  **Task**: Implement the vector search logic (Qdrant query) in the `SearchService`.
3.  **Task**: Integrate the `PermissionPostprocessor` for vector search results.
4.  **Task**: Ship the `search_semantic` and `find_similar` MCP tools.

### M4 - Hybrid Fusion & Quality

#### **Tests to Write First:**

-   **`backend/tests/phase4b/test_search_service_hybrid.py`**:
    -   Test the RRF logic with known, pre-defined keyword and vector result sets, asserting that the final ranked list is correctly ordered and de-duplicated.
    -   Add a test to verify that setting the `rerank` flag correctly invokes the cross-encoder model.
-   **`backend/tests/phase4b/test_performance.py`** (Extend):
    -   Add a benchmark test that measures the p95 latency for a hybrid search against the <350ms target.
-   **`backend/tests/test_mcp_wisdom_comprehensive.py`** (Extend):
    -   Add `test_mcp_wisdom_search_hybrid` to validate the final tool's contract.

#### **Implementation Steps:**

1.  **Task**: Implement the RRF logic in the `SearchService` to merge keyword and semantic results.
2.  **Task**: Integrate the optional cross-encoder, controlled by the `RERANK_ENABLED` flag.
3.  **Task**: Ship the final `search_hybrid` MCP tool.
4.  **Task**: Run performance benchmarks and optimize queries as needed.

### M5 - UI & Finalization

#### **Tests to Write First:**

-   **`frontend/src/components/SearchTab.test.tsx`** (New File):
    -   Write basic React Testing Library tests to verify that the new Search UI component renders correctly, handles user input, and displays results.
-   **`frontend/src/components/IndexerDashboard.test.tsx`** (Extend):
    -   Add assertions to verify that the dashboard now correctly displays metrics for the new job types (chunking, embedding).
-   **`scripts/test-mcp-wisdom.sh`** (Extend):
    -   This is the final E2E validation. Extend the shell script to add calls to all four new search tools. The script should validate that the tools return a successful (non-error) response and that the results are in the expected JSON format.

#### **Implementation Steps:**

1.  **Task**: Create a minimal but functional "Search" tab in the frontend React application.
2.  **Task**: Update the `IndexerDashboard` to show progress for the new job types.
3.  **Task**: Update all project documentation (`README.md`, `CLAUDE.md`, `changelog.md`) and create new feature specification documents as per the project's modular documentation guidelines.
4.  **Task**: Extend the `test-mcp-wisdom.sh` script to provide E2E coverage for the new tools.