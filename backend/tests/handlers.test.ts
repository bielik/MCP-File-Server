/**
 * Unit Tests for Phase 3 Step 1: Connect Existing Search to MCP Tools
 * 
 * Tests the integration between MCP handlers and search services:
 * - handleSearchSemantic: Connects to SemanticSearchService
 * - handleSearchMultimodal: Connects to MultimodalSearchEngine  
 * - handleSearchText: Will connect to FlexSearch (Step 2)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { CallToolRequest } from '@modelcontextprotocol/sdk/types.js';
import {
  handleSearchSemantic,
  handleSearchMultimodal,
  handleSearchText
} from '../server/handlers.js';

// Mock the search services
vi.mock('../src/search/semantic-search-service.js', () => ({
  SemanticSearchService: vi.fn().mockImplementation(() => ({
    initialize: vi.fn().mockResolvedValue(undefined),
    isReady: vi.fn().mockReturnValue(true),
    searchText: vi.fn().mockResolvedValue({
      query: 'test query',
      results: [
        {
          id: '1',
          score: 0.85,
          document_id: 'doc1',
          file_path: '/path/to/file1.txt',
          content_type: 'text',
          text_content: 'Sample text content matching the query',
          metadata: {
            document_id: 'doc1',
            file_path: '/path/to/file1.txt',
            content_type: 'text',
            source: 'mclip',
            created_at: '2025-01-04T10:00:00Z'
          }
        }
      ],
      total_results: 1,
      search_time_ms: 150,
      embedding_time_ms: 50,
      search_type: 'semantic_text'
    }),
    searchMultimodal: vi.fn().mockResolvedValue({
      query: 'multimodal test query',
      results: [
        {
          id: '2',
          score: 0.78,
          document_id: 'doc2',
          file_path: '/path/to/image1.png',
          content_type: 'image',
          metadata: {
            document_id: 'doc2',
            file_path: '/path/to/image1.png',
            content_type: 'image',
            source: 'mclip',
            created_at: '2025-01-04T10:00:00Z'
          }
        }
      ],
      total_results: 1,
      search_time_ms: 200,
      embedding_time_ms: 75,
      search_type: 'cross_modal'
    })
  }))
}));

vi.mock('../src/search/multimodal-search-engine.js', () => ({
  MultimodalSearchEngine: vi.fn().mockImplementation(() => ({
    search: vi.fn().mockResolvedValue({
      query: { text: 'multimodal query' },
      results: [
        {
          node_id: 'node1',
          score: 0.82,
          content: 'Multimodal search result content',
          metadata: {
            document_id: 'doc3',
            page_number: 1,
            content_type: 'text',
            position: { x: 0, y: 0 },
            confidence: 0.9
          }
        }
      ],
      total_results: 1,
      search_time_ms: 180,
      search_strategy: 'hybrid'
    })
  }))
}));

describe('Phase 3 Step 1: MCP Search Handler Integration', () => {
  let mockSemanticSearchService: any;
  let mockMultimodalSearchEngine: any;

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset any global state
    process.env.NODE_ENV = 'test';
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('handleSearchSemantic', () => {
    it('should handle valid semantic search requests', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: 'machine learning algorithms',
            similarity_threshold: 0.7,
            max_results: 10
          }
        }
      };

      const result = await handleSearchSemantic(request);

      expect(result).toBeDefined();
      expect(result.content).toBeDefined();
      expect(result.content).toHaveLength(1);
      expect(result.content[0]).toHaveProperty('type', 'text');
      expect(result.isError).toBeFalsy();
    });

    it('should validate required parameters', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            // Missing required 'query' parameter
            max_results: 10
          }
        }
      };

      const result = await handleSearchSemantic(request);

      expect(result.isError).toBe(true);
      expect(result.content[0].text).toContain('Error in search_semantic');
    });

    it('should handle search service errors gracefully', async () => {
      // Mock service to throw an error
      const mockService = {
        isReady: vi.fn().mockReturnValue(true),
        searchText: vi.fn().mockRejectedValue(new Error('Search service unavailable'))
      };

      // TODO: Inject mock service into handler
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: 'test query'
          }
        }
      };

      const result = await handleSearchSemantic(request);

      // Currently returns "not implemented" - will change when Step 1 is implemented
      expect(result.content[0].text).toContain('not yet implemented');
    });

    it('should format search results correctly', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: 'research methodology',
            similarity_threshold: 0.8,
            max_results: 5
          }
        }
      };

      const result = await handleSearchSemantic(request);

      expect(result.content[0]).toHaveProperty('type', 'text');
      
      // When implemented, should format results as structured text
      // expect(result.content[0].text).toContain('Found');
      // expect(result.content[0].text).toContain('results');
    });

    it('should apply filtering parameters', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: 'data analysis',
            file_categories: ['working', 'output'],
            similarity_threshold: 0.75,
            max_results: 15
          }
        }
      };

      const result = await handleSearchSemantic(request);

      expect(result).toBeDefined();
      // When implemented, should pass filters to search service
    });
  });

  describe('handleSearchMultimodal', () => {
    it('should handle valid multimodal search requests', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_multimodal',
          arguments: {
            query: 'neural network architecture diagram',
            modalities: ['text', 'image'],
            max_results: 15
          }
        }
      };

      const result = await handleSearchMultimodal(request);

      expect(result).toBeDefined();
      expect(result.content).toBeDefined();
      expect(result.content).toHaveLength(1);
      expect(result.content[0]).toHaveProperty('type', 'text');
      expect(result.isError).toBeFalsy();
    });

    it('should validate modalities parameter', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_multimodal',
          arguments: {
            query: 'test query',
            modalities: ['invalid_modality'], // Invalid modality
            max_results: 10
          }
        }
      };

      const result = await handleSearchMultimodal(request);

      expect(result.isError).toBe(true);
      expect(result.content[0].text).toContain('Error in search_multimodal');
    });

    it('should handle text-only modality', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_multimodal',
          arguments: {
            query: 'research findings',
            modalities: ['text'],
            max_results: 10
          }
        }
      };

      const result = await handleSearchMultimodal(request);

      expect(result).toBeDefined();
      // Currently returns "not implemented" - will change when Step 1 is implemented
      expect(result.content[0].text).toContain('not yet implemented');
    });

    it('should handle image-only modality', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_multimodal',
          arguments: {
            query: 'flowchart diagram',
            modalities: ['image'],
            max_results: 8
          }
        }
      };

      const result = await handleSearchMultimodal(request);

      expect(result).toBeDefined();
      // Currently returns "not implemented" - will change when Step 1 is implemented
      expect(result.content[0].text).toContain('not yet implemented');
    });

    it('should combine text and image results', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_multimodal',
          arguments: {
            query: 'data visualization techniques',
            modalities: ['text', 'image'],
            file_categories: ['context', 'working'],
            max_results: 20
          }
        }
      };

      const result = await handleSearchMultimodal(request);

      expect(result).toBeDefined();
      // When implemented, should combine and rank results from both modalities
    });
  });

  describe('handleSearchText (FlexSearch - Step 2)', () => {
    it('should return not implemented message for now', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_text',
          arguments: {
            query: 'keyword search test',
            max_results: 10
          }
        }
      };

      const result = await handleSearchText(request);

      expect(result).toBeDefined();
      expect(result.content[0].text).toContain('not yet implemented');
      expect(result.content[0].text).toContain('FlexSearch');
    });

    it('should validate text search parameters', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_text',
          arguments: {
            // Missing required 'query' parameter
            file_types: ['.txt', '.md'],
            max_results: 15
          }
        }
      };

      const result = await handleSearchText(request);

      expect(result.isError).toBe(true);
      expect(result.content[0].text).toContain('Error in search_text');
    });

    // More detailed keyword search tests
    it('should handle phrase matching', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_text',
          arguments: {
            query: '"exact phrase match"', // Quoted phrase for exact matching
            max_results: 10
          }
        }
      };

      const result = await handleSearchText(request);

      expect(result).toBeDefined();
      // Currently returns "not implemented"
      expect(result.content[0].text).toContain('not yet implemented');
      
      // When implemented, should handle quoted phrases for exact matching
      // expect(result.content[0].text).toContain('exact phrase');
      // Results should only contain documents with the exact phrase
    });

    it('should support multilingual search', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_text',
          arguments: {
            query: 'recherche académique', // French query
            max_results: 10
          }
        }
      };

      const result = await handleSearchText(request);

      expect(result).toBeDefined();
      // Currently returns "not implemented"
      expect(result.content[0].text).toContain('not yet implemented');
      
      // When implemented, should support queries in multiple languages
      // Should handle accented characters and non-English terms
    });

    it('should apply file type filters', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_text',
          arguments: {
            query: 'methodology',
            file_types: ['.pdf', '.md', '.txt'],
            max_results: 15
          }
        }
      };

      const result = await handleSearchText(request);

      expect(result).toBeDefined();
      // Currently returns "not implemented"
      expect(result.content[0].text).toContain('not yet implemented');
      
      // When implemented, should only return results from specified file types
      // Results should be filtered to only include .pdf, .md, and .txt files
    });

    it('should return results sorted by relevance', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_text',
          arguments: {
            query: 'machine learning',
            max_results: 20
          }
        }
      };

      const result = await handleSearchText(request);

      expect(result).toBeDefined();
      // Currently returns "not implemented"
      expect(result.content[0].text).toContain('not yet implemented');
      
      // When implemented, results should be sorted by relevance score
      // Higher relevance scores should appear first
      // The response should include relevance scores for verification
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle malformed request parameters', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: '', // Empty query
            similarity_threshold: 1.5, // Invalid threshold > 1
            max_results: -5 // Negative number
          }
        }
      };

      const result = await handleSearchSemantic(request);

      expect(result.isError).toBe(true);
      expect(result.content[0].text).toContain('Error in search_semantic');
    });

    it('should handle very long queries', async () => {
      const longQuery = 'a'.repeat(10000); // Very long query
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: longQuery,
            max_results: 10
          }
        }
      };

      const result = await handleSearchSemantic(request);

      // Should handle gracefully - either truncate or return error
      expect(result).toBeDefined();
    });

    it('should handle concurrent search requests', async () => {
      const request1: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: { query: 'query1', max_results: 5 }
        }
      };

      const request2: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_multimodal',
          arguments: { query: 'query2', max_results: 5 }
        }
      };

      // Execute concurrent requests
      const [result1, result2] = await Promise.all([
        handleSearchSemantic(request1),
        handleSearchMultimodal(request2)
      ]);

      expect(result1).toBeDefined();
      expect(result2).toBeDefined();
      expect(result1.isError).toBeFalsy();
      expect(result2.isError).toBeFalsy();
    });
  });

  describe('Performance and Logging', () => {
    it('should log MCP requests and responses', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: 'performance test query',
            max_results: 5
          }
        }
      };

      const result = await handleSearchSemantic(request);

      expect(result).toBeDefined();
      // When implemented, should verify logging calls
    });

    it('should measure and report performance timings', async () => {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: 'timing test query',
            max_results: 10
          }
        }
      };

      const startTime = Date.now();
      const result = await handleSearchSemantic(request);
      const endTime = Date.now();

      expect(result).toBeDefined();
      expect(endTime - startTime).toBeLessThan(5000); // Should complete within 5 seconds
    });
  });

  describe('Integration Test Scenarios', () => {
    it('should handle typical research query workflow', async () => {
      // Simulate a researcher looking for information about machine learning
      const semanticRequest: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: 'machine learning model evaluation metrics',
            similarity_threshold: 0.75,
            max_results: 15,
            file_categories: ['context', 'working']
          }
        }
      };

      const multimodalRequest: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_multimodal',
          arguments: {
            query: 'confusion matrix visualization',
            modalities: ['text', 'image'],
            max_results: 10
          }
        }
      };

      const [semanticResult, multimodalResult] = await Promise.all([
        handleSearchSemantic(semanticRequest),
        handleSearchMultimodal(multimodalRequest)
      ]);

      expect(semanticResult.isError).toBeFalsy();
      expect(multimodalResult.isError).toBeFalsy();
      
      // When implemented, verify result quality and relevance
    });

    it('should support academic writing workflow', async () => {
      // Simulate searching for literature review content
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: 'search_semantic',
          arguments: {
            query: 'systematic review methodology best practices',
            file_categories: ['literature', 'methodology'],
            similarity_threshold: 0.8,
            max_results: 20
          }
        }
      };

      const result = await handleSearchSemantic(request);

      expect(result).toBeDefined();
      // When implemented, should return relevant academic content
    });
  });
});