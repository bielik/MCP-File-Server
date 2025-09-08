# Comprehensive Unit Test Plan for project refactor
2025-09-05-14:46

## 1. Testing Philosophy

This plan outlines the unit tests for the core backend services of the MCP Research File Server. The primary goal is to test each module in **complete isolation** to ensure its logic is correct and robust, independent of its dependencies.

-   **Framework:** Vitest will be used as the test runner and assertion library.
-   **Mocking:** All external dependencies and inter-service communications will be mocked. This is critical for true unit testing.
    -   The `@xenova/transformers` library will be mocked to simulate model loading and embedding generation.
    -   The `@qdrant/js-client-rest` client will be mocked to simulate all database interactions.
    -   Node.js's built-in `fs/promises` and `child_process` modules will be mocked to simulate file system operations and external command execution (`pdfimages`).
    -   Internal services will be mocked when testing orchestrator modules (e.g., `AiService` and `DocumentParser` will be mocked when testing the `Indexer`).

## 2. Test Suites

### 2.1. `backend/src/services/AiService.ts`

**Objective:** Verify the `AiService` wrapper correctly handles model loading and calls the underlying transformer pipeline.

-   **`getInstance()`**
    -   **[Test Case]** Should return the same instance when called multiple times (verifies singleton pattern).
-   **`initialize()`**
    -   **[Test Case]** On success, should call the `pipeline` function from `@xenova/transformers` with the correct model name from the configuration.
    -   **[Test Case]** On success, should set `isReady()` to `true`.
    -   **[Test Case]** Should handle errors gracefully if the `pipeline` function throws an exception and ensure `isReady()` remains `false`.
    -   **[Test Case]** Should be idempotent, meaning it only attempts to load the model on the first call.
-   **`embedText(text)`**
    -   **[Test Case]** Given a valid string, should call the text pipeline and return a `number[]` of the configured embedding dimension (512).
    -   **[Test Case]** Should handle an empty string gracefully without errors.
    -   **[Test Case]** Should throw a specific `AiService` error if the underlying pipeline fails.
-   **`embedImage(buffer)`**
    -   **[Test Case]** Given a valid image `Buffer`, should call the image pipeline and return a `number[]` of the configured embedding dimension.
    -   **[Test Case]** Should throw a specific `AiService` error if the underlying pipeline fails.

### 2.2. `backend/src/services/VectorDb.ts`

**Objective:** Verify the service correctly interacts with a mocked Qdrant client.

-   **`initialize()`**
    -   **[Test Case]** Should instantiate the `QdrantClient`.
    -   **[Test Case]** Should call `ensureCollectionsExist()` upon successful connection.
-   **`ensureCollectionsExist()`**
    -   **[Test Case]** When collections are missing, should call `client.createCollection()` for both `mcp_text_chunks` and `mcp_image_embeddings`.
    -   **[Test Case]** When collections already exist, should **not** call `client.createCollection()`.
-   **`storeTextEmbeddings(documents)`**
    -   **[Test Case]** Should call `client.upsert()` with the correct text collection name and properly formatted Qdrant point structures.
-   **`storeImageEmbeddings(documents)`**
    -   **[Test Case]** Should call `client.upsert()` with the correct image collection name and properly formatted Qdrant point structures.

### 2.3. `backend/src/features/processing/DocumentParser.ts`

**Objective:** Verify the parser correctly extracts text and images by mocking `fs`, `pdf-parse`, and `child_process`.

-   **`parseDocument(filePath)`**
    -   **[Test Case]** For a PDF with text and images, should correctly call `pdf-parse` and spawn a `pdfimages` process. Should return an object containing both extracted text and image buffers.
    -   **[Test Case]** For a text-only PDF, should return an object with text and an empty `images` array.
    -   **[Test Case]** Should throw a `DocumentProcessingError` if `pdf-parse` fails.
    -   **[Test Case]** Should **not** throw an error if the `pdfimages` process fails, but should log a warning and return an empty `images` array.
-   **`chunkText(text, chunkSize, chunkOverlap)` (Internal Logic)**
    -   **[Test Case]** Given a long text, should split it into chunks of approximately `chunkSize`.
    -   **[Test Case]** Should verify that consecutive chunks have the correct `chunkOverlap`.
    -   **[Test Case]** Should handle text shorter than the `chunkSize` by returning a single chunk.

### 2.4. `backend/src/features/processing/Indexer.ts`

**Objective:** Verify the orchestrator calls its dependent services in the correct sequence. Mock all dependencies.

-   **`indexFile(filePath)`**
    -   **[Test Case]** Should call `documentParser.parseDocument` first.
    -   **[Test Case]** Should then call `aiService.embedText` for each text chunk returned by the parser.
    -   **[Test Case]** Should then call `aiService.embedImage` for each image buffer returned by the parser.
    -   **[Test Case]** Should subsequently call `vectorDbService.storeTextEmbeddings` and `storeImageEmbeddings` with the generated vectors.
    -   **[Test Case]** Should finally call `keywordSearchService.addDocuments` with the text chunks.
    -   **[Test Case]** Should catch an error from any downstream service, stop processing, and return an `IndexingResult` with `success: false`.

### 2.5. Search Services

**Objective:** Verify the search logic is correct.

-   **`backend/src/features/search/keywordSearch.ts`**
    -   **[Test Case]** After adding documents, a search for an exact term should return the correct document.
    -   **[Test Case]** A search with a typo should still return the correct document (validates fuzzy search).
    -   **[Test Case]** A search for a non-existent term should return an empty array.
-   **`backend/src/features/search/semanticSearch.ts`**
    -   **[Test Case]** `searchText(query)` should call `aiService.embedText(query)` and then pass the resulting vector to `vectorDbService.searchText`.
    -   **[Test Case]** `searchMultimodal(query)` should call `aiService.embedText` once, then call both `vectorDbService.searchText` and `vectorDbService.searchImages`.

### 2.6. `backend/server/handlers.ts`

**Objective:** Verify the MCP handlers correctly parse requests, call services, and format responses. Mock all backend services.

-   **`handleSearchText(request)`**
    -   **[Test Case]** With a valid request, should call `keywordSearchService.search` and return a correctly formatted, non-error `CallToolResult`.
    -   **[Test Case]** With a request missing the `query` parameter, should return a Zod validation error formatted as a `CallToolResult`.
    -   **[Test Case]** If `keywordSearchService.search` throws an error, should catch it and return a formatted error `CallToolResult`.
-   **`handleSearchSemantic(request)`**
    -   **[Test Case]** With a valid request, should call `semanticSearchService.searchText` and return a correctly formatted, non-error `CallToolResult`.
    -   **[Test Case]** If `semanticSearchService.searchText` throws an error, should catch it and return a formatted error `CallToolResult`.
-   **`handleSearchMultimodal(request)`**
    -   **[Test Case]** With a valid request, should call `semanticSearchService.searchMultimodal` and return a correctly formatted, non-error `CallToolResult`.
    -   **[Test Case]** If `semanticSearchService.searchMultimodal` throws an error, should catch it and return a formatted error `CallToolResult`.