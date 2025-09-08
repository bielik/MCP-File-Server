# CLAUDE-patterns.md - Testing Patterns & Mock Strategies

**Last Updated:** September 8, 2025 - Updated with Frontend Testing Patterns  
**Status:** SYNCHRONIZED with full-stack implementation (Backend + Frontend)  
**Backend Test Results:** 67/67 tests passing across 3 test files  
**Frontend Test Results:** Playwright tests operational with screenshot generation

## Overview

This document captures the testing patterns, mock strategies, and architectural approaches discovered in the MCP Research File Server. These patterns reflect the current implementation state where comprehensive test coverage enables confident development of both real and mocked services.

## Testing Architecture Patterns

### 1. Comprehensive Mock Strategy (IMPLEMENTED)

**Pattern:** Layered Mocking System  
**Location:** `backend/tests/setup.ts`  
**Status:** ✅ FULLY IMPLEMENTED

```typescript
// Real Pattern from setup.ts
vi.mock('@qdrant/js-client-rest', () => ({
  QdrantClient: vi.fn().mockImplementation(() => ({
    search: vi.fn().mockResolvedValue([]),
    upsert: vi.fn().mockResolvedValue({ operation_id: 'mock-op-id' }),
    getCollections: vi.fn().mockResolvedValue({
      collections: [
        { name: 'mcp_text_embeddings' },
        { name: 'mcp_image_embeddings' },
        { name: 'mcp_multimodal_embeddings' }
      ]
    })
  }))
}));
```

**Key Features:**
- External service mocking (Qdrant, Winston, File System)
- Consistent mock data factories in `testUtils`
- Isolated test environment with separate ports
- Automatic mock cleanup between tests

### 2. Service Implementation Pattern (HYBRID: REAL + MOCKED)

**Pattern:** Real Services with Mock Fallbacks  
**Location:** `backend/server/handlers.ts`  
**Status:** ⚡ IMPLEMENTED with graceful degradation

```typescript
// Real Pattern from handlers.ts
export async function handleSearchSemantic(request: CallToolRequest): Promise<CallToolResult> {
  try {
    const params = searchSemanticSchema.parse(request.params.arguments);
    
    // Check if search services are available and ready
    let serviceAvailable = false;
    try {
      serviceAvailable = semanticSearchService && 
        typeof semanticSearchService.isReady === 'function' && 
        semanticSearchService.isReady();
    } catch (error) {
      serviceAvailable = false;
    }
    
    if (!serviceAvailable) {
      return {
        content: [{
          type: 'text',
          text: 'Semantic search functionality is not yet implemented. This feature will be available once the AI services are fully integrated.',
        }],
      };
    }
    
    // Use real implementation when available
    const searchResults = await semanticSearchService.searchText(params.query, {
      limit: params.max_results || 10,
      threshold: params.similarity_threshold || 0.7,
      searchMode: 'text_only',
    });
```

**Key Features:**
- Service availability checking before execution
- Graceful fallback messages for unimplemented features
- Real TypeScript service implementations exist
- MCP parameter parsing fixed to `request.params.arguments`

### 3. Zod Validation Pattern (ENHANCED)

**Pattern:** Robust Parameter Validation with Whitespace Handling  
**Location:** `backend/server/handlers.ts`  
**Status:** ✅ ENHANCED with whitespace validation

```typescript
// Real Enhanced Pattern from handlers.ts
const searchTextSchema = z.object({
  query: z.string().min(1).refine((query) => query.trim().length > 0, {
    message: "Query cannot be empty or contain only whitespace",
  }),
  file_categories: z.array(z.enum(['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other'])).optional(),
  file_types: z.array(z.string()).optional(),
  max_results: z.number().optional().default(20),
});
```

**Key Features:**
- Whitespace-aware query validation
- Comprehensive file category enums
- Optional parameters with defaults
- Custom error messages for better UX

### 4. Test Organization Pattern (3-FILE STRUCTURE)

**Pattern:** Purpose-Driven Test File Organization  
**Location:** `backend/tests/`  
**Status:** ✅ IMPLEMENTED with 67 tests

**Structure:**
1. **`handlers.test.ts`** - MCP handler integration tests
2. **`mcp-protocol.test.ts`** - Protocol compliance and validation
3. **`search-service-integration.test.ts`** - Service integration scenarios

**Coverage:**
- Unit tests: Handler functions
- Integration tests: Service connections
- Protocol tests: MCP compliance
- Edge cases: Error handling and validation

### 5. Mock Service Class Pattern (SOPHISTICATED)

**Pattern:** Complete Service Mocks with State Management  
**Location:** `backend/tests/search-service-integration.test.ts`  
**Status:** ✅ IMPLEMENTED with stateful mocks

```typescript
// Real Pattern from search-service-integration.test.ts
class MockSemanticSearchService {
  private initialized = false;
  private mclipClient: any;
  private vectorStore: any;

  constructor(mclipUrl?: string, qdrantUrl?: string) {
    this.mclipClient = {
      health: vi.fn().mockResolvedValue({
        status: 'healthy',
        device: 'cpu',
        model_loaded: true
      }),
      embedText: vi.fn().mockResolvedValue({
        embedding: new Array(512).fill(0).map(() => Math.random()),
        model: 'sentence-transformers/clip-ViT-B-32-multilingual-v1',
        dimensions: 512
      })
    };
  }
```

**Key Features:**
- Stateful mock services that track initialization
- Realistic method implementations with proper return types
- Error simulation capabilities for failure testing
- Health check and statistics mocking

### 6. Frontend Testing Pattern (✅ IMPLEMENTED)

**Pattern:** Playwright Visual Testing with Multi-Viewport Support  
**Location:** `frontend/tests/` directory  
**Status:** ✅ FULLY OPERATIONAL

```typescript
// Real Pattern from app.spec.ts
test('checks responsive design', async ({ page }) => {
  // Test desktop view
  await page.setViewportSize({ width: 1200, height: 800 });
  await page.screenshot({ 
    path: './screenshots/desktop-view.png', 
    fullPage: true 
  });
  
  // Test tablet view
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.screenshot({ 
    path: './screenshots/tablet-view.png', 
    fullPage: true 
  });
  
  // Test mobile view
  await page.setViewportSize({ width: 375, height: 667 });
  await page.screenshot({ 
    path: './screenshots/mobile-view.png', 
    fullPage: true 
  });
});
```

**Key Features:**
- Multi-viewport responsive testing (desktop, tablet, mobile)
- Screenshot generation for visual regression testing
- API connectivity verification through frontend proxy
- UI component interaction testing (button clicks, navigation)
- Performance testing with page load monitoring
- Automated test execution with CI/CD readiness

### 7. Vite Configuration Pattern (✅ IMPLEMENTED)

**Pattern:** Windows-Compatible Development Environment  
**Location:** `frontend/vite.config.ts`  
**Status:** ✅ PRODUCTION-READY

```typescript
// Real Pattern from vite.config.ts
export default defineConfig({
  // Move cache to temp directory to avoid Windows permission issues
  cacheDir: path.join(process.env.TEMP || 'C:/temp', 'vite-cache'),
  
  server: {
    port: 3004,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',  // Fixed: was 3006
        changeOrigin: true,
        secure: false,
      },
      '/socket.io': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
```

**Key Features:**
- Windows permission issue resolution (cache directory)
- Fixed port configuration for stable API communication
- WebSocket proxy support for real-time features
- Path alias configuration for clean imports
- Production build optimization with chunk splitting

## Implementation Status Matrix

| Component | Implementation Status | Test Status | Notes |
|-----------|----------------------|-------------|-------|
| **MCP Handlers** | ✅ REAL & FUNCTIONAL | ✅ 67/67 PASS | Fixed parameter parsing, robust validation |
| **File Operations** | ✅ REAL & WORKING | ✅ TESTED | Complete file system integration |
| **Zod Validation** | ✅ ENHANCED | ✅ TESTED | Added whitespace validation |
| **Search Services (Classes)** | ✅ REAL TS CLASSES | 🔄 MOCKED IN TESTS | TypeScript implementations exist |
| **AI Services** | ✅ REAL TS CLASSES | 🔄 MOCKED IN TESTS | Full @xenova/transformers integration |
| **Vector Services** | ✅ REAL TS CLASSES | 🔄 MOCKED IN TESTS | Complete Qdrant client wrapper |
| **Frontend Application** | ✅ REAL & OPERATIONAL | ✅ PLAYWRIGHT TESTS | React + Vite + Playwright testing |
| **Backend Test Infrastructure** | ✅ COMPLETE | ✅ 67 TESTS | Vitest + comprehensive mocking |
| **Frontend Test Infrastructure** | ✅ COMPLETE | ✅ SCREENSHOT TESTS | Playwright + visual regression |

## Key Testing Insights (September 5, 2025)

### 1. Fixed MCP Parameter Bug
**Issue:** Tests revealed parameter parsing bug  
**Fix:** Changed from `request.params` to `request.params.arguments`  
**Impact:** All MCP handlers now correctly parse tool arguments

### 2. Enhanced Validation
**Addition:** Whitespace query validation prevents empty searches  
**Implementation:** Zod `.refine()` method with custom error messages  
**Benefit:** Better user experience and error handling

### 3. Service Availability Pattern
**Pattern:** Check service availability before execution  
**Benefit:** Graceful degradation when services not ready  
**Future:** Enables gradual service activation

### 4. Comprehensive Mock Coverage
**Achievement:** 100% external service mocking  
**Services:** Qdrant, Winston, File System, AI services  
**Result:** Fast, reliable, isolated tests

## Development Recommendations

### For New Features
1. **Follow Service Availability Pattern** - Always check if services are ready
2. **Use Comprehensive Mocking** - Mock all external dependencies
3. **Implement Zod Validation** - Include whitespace and edge case handling
4. **Write Integration Tests** - Test real service connections when available

### For Service Integration
1. **Real TypeScript Implementations Exist** - Actual service classes are implemented
2. **Tests Use Mocks** - Production will use real services
3. **Graceful Degradation** - Handlers work with or without services
4. **Health Checking** - All services include health/ready checks

### For Testing
1. **Use `testUtils` Factory Functions** - Consistent mock data generation
2. **Test Both Success and Failure Paths** - Include error scenarios
3. **Validate MCP Protocol Compliance** - Ensure proper request/response structure
4. **Test Edge Cases** - Empty queries, invalid parameters, etc.

## Phase Status (September 5, 2025)

- **Phase 3 Step 1: COMPLETED** ✅ - Test suite with 67 passing tests
- **Phase 4 Task 1: COMPLETED** ✅ - Test coverage and infrastructure
- **Phase 4 Task 2: PENDING** ⏳ - Frontend Search Experience (next step)

## References

- **Test Files:** `backend/tests/*.test.ts`
- **Mock Setup:** `backend/tests/setup.ts`
- **Real Handlers:** `backend/server/handlers.ts`
- **Service Implementations:** `backend/src/services/`, `backend/src/features/`
- **Test Configuration:** `backend/vitest.config.ts`