/**
 * Test Setup Configuration
 * 
 * Global test setup for Phase 3 Step 1 unit tests
 * Configures environment, mocks, and test utilities
 */

import { vi, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { config } from 'dotenv';
import path from 'path';

// Load test environment variables
config({ path: path.resolve(__dirname, '../.env.test') });

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.MCP_PORT = '3001';
process.env.QDRANT_URL = 'http://localhost:6334'; // Different port for testing
process.env.MCLIP_SERVICE_URL = 'http://localhost:8003'; // Different port for testing
process.env.LOG_LEVEL = 'error'; // Suppress logs during testing

// Global test timeout
vi.setConfig({ testTimeout: 10000 });

// Mock external services by default
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
    }),
    api: vi.fn().mockReturnValue({
      clusterStatus: vi.fn().mockResolvedValue({ status: 'green' })
    })
  }))
}));

// Mock Winston logger to prevent log output during tests
vi.mock('winston', () => ({
  default: {
    createLogger: vi.fn(() => ({
      info: vi.fn(),
      error: vi.fn(),
      warn: vi.fn(),
      debug: vi.fn(),
      silly: vi.fn(),
      add: vi.fn()
    })),
    format: {
      combine: vi.fn(() => ({})),
      timestamp: vi.fn(() => ({})),
      printf: vi.fn(() => ({})),
      colorize: vi.fn(() => ({})),
      simple: vi.fn(() => ({})),
      json: vi.fn(() => ({})),
      errors: vi.fn(() => ({}))
    },
    transports: {
      Console: vi.fn(() => ({})),
      File: vi.fn(() => ({}))
    }
  },
  createLogger: vi.fn(() => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
    silly: vi.fn(),
    add: vi.fn()
  })),
  format: {
    combine: vi.fn(() => ({})),
    timestamp: vi.fn(() => ({})),
    printf: vi.fn(() => ({})),
    colorize: vi.fn(() => ({})),
    simple: vi.fn(() => ({})),
    json: vi.fn(() => ({})),
    errors: vi.fn(() => ({}))
  },
  transports: {
    Console: vi.fn(() => ({})),
    File: vi.fn(() => ({}))
  }
}));

// Mock file system operations to prevent actual file I/O during tests
vi.mock('fs/promises', () => ({
  readFile: vi.fn().mockResolvedValue('mock file content'),
  writeFile: vi.fn().mockResolvedValue(undefined),
  access: vi.fn().mockResolvedValue(undefined),
  mkdir: vi.fn().mockResolvedValue(undefined),
  stat: vi.fn().mockResolvedValue({
    size: 1000,
    mtime: new Date(),
    ctime: new Date(),
    isFile: () => true,
    isDirectory: () => false
  }),
  readdir: vi.fn().mockResolvedValue(['file1.txt', 'file2.pdf'])
}));

// Mock chokidar file watcher
vi.mock('chokidar', () => ({
  watch: vi.fn(() => ({
    on: vi.fn(),
    close: vi.fn(),
    add: vi.fn(),
    unwatch: vi.fn()
  }))
}));

// Global test setup
beforeAll(async () => {
  // Initialize any global test resources
  console.log('🧪 Starting MCP Research File Server tests...');
});

// Global test cleanup
afterAll(async () => {
  // Clean up any global test resources
  console.log('✅ MCP Research File Server tests completed');
});

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks();
});

// Clean up after each test
afterEach(() => {
  vi.resetAllMocks();
});

// Custom test utilities
export const testUtils = {
  /**
   * Create a mock CallToolRequest for MCP handlers
   */
  createMockRequest: (toolName: string, args: any) => ({
    method: 'tools/call' as const,
    params: {
      name: toolName,
      arguments: args
    }
  }),

  /**
   * Create mock search results
   */
  createMockSearchResults: (count: number = 3) => ({
    query: 'test query',
    results: Array.from({ length: count }, (_, i) => ({
      id: `result-${i + 1}`,
      score: 0.9 - (i * 0.1),
      document_id: `doc-${i + 1}`,
      file_path: `/path/to/file${i + 1}.txt`,
      content_type: 'text' as const,
      text_content: `Sample content for result ${i + 1}`,
      metadata: {
        document_id: `doc-${i + 1}`,
        file_path: `/path/to/file${i + 1}.txt`,
        content_type: 'text' as const,
        source: 'mclip',
        created_at: new Date().toISOString()
      }
    })),
    total_results: count,
    search_time_ms: 150,
    embedding_time_ms: 50,
    search_type: 'semantic_text' as const
  }),

  /**
   * Create mock embeddings
   */
  createMockEmbedding: (dimensions: number = 512) => ({
    embedding: new Array(dimensions).fill(0).map(() => Math.random()),
    model: 'sentence-transformers/clip-ViT-B-32-multilingual-v1',
    dimensions
  }),

  /**
   * Create mock Qdrant search results
   */
  createMockQdrantResults: (count: number = 2) => Array.from({ length: count }, (_, i) => ({
    id: `qdrant-point-${i + 1}`,
    score: 0.85 - (i * 0.1),
    payload: {
      document_id: `doc-${i + 1}`,
      file_path: `/path/to/document${i + 1}.txt`,
      content_type: 'text',
      text_content: `Mock document content ${i + 1}`,
      source: 'mclip',
      created_at: new Date().toISOString()
    }
  })),

  /**
   * Wait for async operations to complete
   */
  waitFor: (ms: number = 100) => new Promise(resolve => setTimeout(resolve, ms)),

  /**
   * Simulate network delay
   */
  simulateNetworkDelay: () => testUtils.waitFor(Math.random() * 100 + 50),

  /**
   * Mock service health response
   */
  mockHealthyService: () => ({
    status: 'healthy' as const,
    timestamp: new Date().toISOString(),
    services: {
      mclip: true,
      qdrant: true,
      embedding_service: true
    }
  }),

  /**
   * Mock degraded service response
   */
  mockDegradedService: () => ({
    status: 'degraded' as const,
    timestamp: new Date().toISOString(),
    services: {
      mclip: true,
      qdrant: false,
      embedding_service: true
    }
  })
};

// Export test environment configuration
export const testConfig = {
  ports: {
    mcp: 3001,
    qdrant: 6334,
    mclip: 8003,
    web: 3005
  },
  timeouts: {
    test: 10000,
    network: 5000,
    initialization: 15000
  },
  mock: {
    embeddings: {
      dimensions: 512,
      similarity_threshold: 0.7
    },
    search: {
      max_results: 20,
      default_results: 10
    }
  }
};