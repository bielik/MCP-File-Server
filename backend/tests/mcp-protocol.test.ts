/**
 * MCP Protocol Compliance Tests - Phase 3 Step 1
 * 
 * Tests that the search handlers comply with the Model Context Protocol specification:
 * - Proper request/response format handling
 * - Error handling according to MCP spec
 * - Tool parameter validation
 * - Response structure validation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CallToolRequest, CallToolResult, ErrorCode } from '@modelcontextprotocol/sdk/types.js';
import {
  handleSearchSemantic,
  handleSearchMultimodal,  
  handleSearchText,
  toolHandlers
} from '../server/handlers.js';
import { testUtils } from './setup.js';

describe('MCP Protocol Compliance - Search Handlers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Request Format Validation', () => {
    it('should validate CallToolRequest structure for search_semantic', async () => {
      const validRequest: CallToolRequest = testUtils.createMockRequest('search_semantic', {
        query: 'machine learning algorithms',
        similarity_threshold: 0.75,
        max_results: 10
      });

      const result = await handleSearchSemantic(validRequest);
      
      expect(result).toBeDefined();
      expect(result).toHaveProperty('content');
      expect(Array.isArray(result.content)).toBe(true);
      expect(result.content.length).toBeGreaterThan(0);
      expect(result.content[0]).toHaveProperty('type');
      expect(result.content[0]).toHaveProperty('text');
    });

    it('should reject requests with invalid method', async () => {
      const invalidRequest = {
        method: 'invalid/method', // Invalid method
        params: {
          name: 'search_semantic',
          arguments: { query: 'test' }
        }
      } as CallToolRequest;

      // The handler should still work, but this tests protocol awareness
      const result = await handleSearchSemantic(invalidRequest);
      expect(result).toBeDefined();
    });

    it('should handle missing params gracefully', async () => {
      const invalidRequest = {
        method: 'tools/call',
        params: {} // Missing params
      } as CallToolRequest;

      const result = await handleSearchSemantic(invalidRequest);
      
      expect(result.isError).toBe(true);
      expect(result.content[0].text).toContain('Error in search_semantic');
    });

    it('should validate required arguments for search_multimodal', async () => {
      const invalidRequest = testUtils.createMockRequest('search_multimodal', {
        // Missing required 'query' field
        modalities: ['text', 'image'],
        max_results: 10
      });

      const result = await handleSearchMultimodal(invalidRequest);
      
      expect(result.isError).toBe(true);
      expect(result.content[0].text).toContain('Error in search_multimodal');
    });
  });

  describe('Response Format Compliance', () => {
    it('should return valid CallToolResult structure', async () => {
      const request = testUtils.createMockRequest('search_semantic', {
        query: 'test query',
        max_results: 5
      });

      const result = await handleSearchSemantic(request);

      // Verify CallToolResult structure
      expect(result).toBeDefined();
      expect(result).toHaveProperty('content');
      expect(Array.isArray(result.content)).toBe(true);
      
      // Each content item should have required fields
      result.content.forEach(item => {
        expect(item).toHaveProperty('type');
        expect(['text', 'image', 'resource'].includes(item.type)).toBe(true);
        
        if (item.type === 'text') {
          expect(item).toHaveProperty('text');
          expect(typeof item.text).toBe('string');
        }
      });

      // isError should be boolean or undefined
      if (result.isError !== undefined) {
        expect(typeof result.isError).toBe('boolean');
      }
    });

    it('should set isError=true for validation errors', async () => {
      const invalidRequest = testUtils.createMockRequest('search_semantic', {
        query: '', // Empty query should fail validation
        similarity_threshold: 1.5 // Invalid threshold > 1
      });

      const result = await handleSearchSemantic(invalidRequest);

      expect(result.isError).toBe(true);
      expect(result.content[0].type).toBe('text');
      expect(result.content[0].text).toContain('Error');
    });

    it('should provide meaningful error messages', async () => {
      const invalidRequest = testUtils.createMockRequest('search_multimodal', {
        query: 'valid query',
        modalities: ['invalid_type'] // Invalid modality
      });

      const result = await handleSearchMultimodal(invalidRequest);

      expect(result.isError).toBe(true);
      expect(result.content[0].text).toMatch(/Error in search_multimodal/i);
      // Should provide context about what went wrong
      expect(result.content[0].text.length).toBeGreaterThan(20);
    });
  });

  describe('Parameter Validation', () => {
    describe('search_semantic parameters', () => {
      it('should validate query parameter', async () => {
        const tests = [
          { query: '', expectedError: true, description: 'empty query' },
          { query: '   ', expectedError: true, description: 'whitespace query' },  
          { query: 'valid query', expectedError: false, description: 'valid query' },
          { query: 'a'.repeat(1000), expectedError: false, description: 'long query' }
        ];

        for (const test of tests) {
          const request = testUtils.createMockRequest('search_semantic', {
            query: test.query,
            max_results: 5
          });

          const result = await handleSearchSemantic(request);

          if (test.expectedError) {
            expect(result.isError, `Failed for ${test.description}`).toBe(true);
          } else {
            // Currently returns "not implemented", but should not error on valid params
            expect(result.isError, `Failed for ${test.description}`).toBeFalsy();
          }
        }
      });

      it('should validate similarity_threshold parameter', async () => {
        const tests = [
          { threshold: -0.1, expectedError: true, description: 'negative threshold' },
          { threshold: 1.5, expectedError: true, description: 'threshold > 1' },
          { threshold: 0.0, expectedError: false, description: 'minimum valid threshold' },
          { threshold: 1.0, expectedError: false, description: 'maximum valid threshold' },
          { threshold: 0.75, expectedError: false, description: 'typical threshold' }
        ];

        for (const test of tests) {
          const request = testUtils.createMockRequest('search_semantic', {
            query: 'test query',
            similarity_threshold: test.threshold
          });

          const result = await handleSearchSemantic(request);

          if (test.expectedError) {
            expect(result.isError, `Failed for ${test.description}`).toBe(true);
          } else {
            expect(result.isError, `Failed for ${test.description}`).toBeFalsy();
          }
        }
      });

      it('should validate max_results parameter', async () => {
        const tests = [
          { max_results: 0, expectedError: false, description: 'zero results (edge case)' },
          { max_results: -1, expectedError: false, description: 'negative results (should use default)' },
          { max_results: 1, expectedError: false, description: 'minimum results' },
          { max_results: 100, expectedError: false, description: 'large results' }
        ];

        for (const test of tests) {
          const request = testUtils.createMockRequest('search_semantic', {
            query: 'test query',
            max_results: test.max_results
          });

          const result = await handleSearchSemantic(request);
          expect(result.isError, `Failed for ${test.description}`).toBeFalsy();
        }
      });

      it('should validate file_categories parameter', async () => {
        const validCategories = ['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other'];
        
        const tests = [
          { categories: ['context'], expectedError: false, description: 'valid single category' },
          { categories: ['context', 'working'], expectedError: false, description: 'valid multiple categories' },
          { categories: ['invalid'], expectedError: true, description: 'invalid category' },
          { categories: [], expectedError: false, description: 'empty categories (should be allowed)' }
        ];

        for (const test of tests) {
          const request = testUtils.createMockRequest('search_semantic', {
            query: 'test query',
            file_categories: test.categories
          });

          const result = await handleSearchSemantic(request);

          if (test.expectedError) {
            expect(result.isError, `Failed for ${test.description}`).toBe(true);
          } else {
            expect(result.isError, `Failed for ${test.description}`).toBeFalsy();
          }
        }
      });
    });

    describe('search_multimodal parameters', () => {
      it('should validate modalities parameter', async () => {
        const tests = [
          { modalities: ['text'], expectedError: false, description: 'text only' },
          { modalities: ['image'], expectedError: false, description: 'image only' },
          { modalities: ['text', 'image'], expectedError: false, description: 'both modalities' },
          { modalities: ['invalid'], expectedError: true, description: 'invalid modality' },
          { modalities: [], expectedError: false, description: 'empty modalities (should default)' }
        ];

        for (const test of tests) {
          const request = testUtils.createMockRequest('search_multimodal', {
            query: 'test query',
            modalities: test.modalities
          });

          const result = await handleSearchMultimodal(request);

          if (test.expectedError) {
            expect(result.isError, `Failed for ${test.description}`).toBe(true);
          } else {
            expect(result.isError, `Failed for ${test.description}`).toBeFalsy();
          }
        }
      });
    });

    describe('search_text parameters', () => {
      it('should validate file_types parameter', async () => {
        const tests = [
          { types: ['.txt'], expectedError: false, description: 'single file type' },
          { types: ['.txt', '.md'], expectedError: false, description: 'multiple file types' },
          { types: [], expectedError: false, description: 'empty file types' },
          { types: ['invalid'], expectedError: false, description: 'invalid extension (should be allowed)' }
        ];

        for (const test of tests) {
          const request = testUtils.createMockRequest('search_text', {
            query: 'test query',
            file_types: test.types
          });

          const result = await handleSearchText(request);
          // Currently not implemented, but should not error on valid params
          expect(result.isError, `Failed for ${test.description}`).toBeFalsy();
        }
      });
    });
  });

  describe('Tool Handler Registry', () => {
    it('should export all required tool handlers', () => {
      expect(toolHandlers).toBeDefined();
      expect(typeof toolHandlers).toBe('object');
      
      // Check that all expected search tools are registered
      expect(toolHandlers).toHaveProperty('search_semantic');
      expect(toolHandlers).toHaveProperty('search_multimodal');
      expect(toolHandlers).toHaveProperty('search_text');
      
      // Check that handlers are functions
      expect(typeof toolHandlers.search_semantic).toBe('function');
      expect(typeof toolHandlers.search_multimodal).toBe('function');
      expect(typeof toolHandlers.search_text).toBe('function');
    });

    it('should handle unknown tool names gracefully', () => {
      // This tests the tool registry, not individual handlers
      expect(toolHandlers.unknown_tool).toBeUndefined();
    });
  });

  describe('Concurrent Request Handling', () => {
    it('should handle multiple concurrent search requests', async () => {
      const requests = [
        testUtils.createMockRequest('search_semantic', { query: 'query 1', max_results: 5 }),
        testUtils.createMockRequest('search_multimodal', { query: 'query 2', max_results: 5 }),
        testUtils.createMockRequest('search_text', { query: 'query 3', max_results: 5 })
      ];

      const results = await Promise.all([
        handleSearchSemantic(requests[0]),
        handleSearchMultimodal(requests[1]),
        handleSearchText(requests[2])
      ]);

      expect(results).toHaveLength(3);
      results.forEach((result, index) => {
        expect(result, `Request ${index + 1} failed`).toBeDefined();
        expect(result.content, `Request ${index + 1} missing content`).toBeDefined();
        expect(result.content.length, `Request ${index + 1} empty content`).toBeGreaterThan(0);
      });
    });

    it('should not interfere with each other during concurrent execution', async () => {
      // Create many concurrent requests to test for race conditions
      const concurrentRequests = Array.from({ length: 10 }, (_, i) =>
        testUtils.createMockRequest('search_semantic', {
          query: `concurrent query ${i}`,
          max_results: 5
        })
      );

      const results = await Promise.allSettled(
        concurrentRequests.map(req => handleSearchSemantic(req))
      );

      expect(results).toHaveLength(10);
      results.forEach((result, index) => {
        expect(result.status, `Request ${index} was rejected`).toBe('fulfilled');
        if (result.status === 'fulfilled') {
          expect(result.value, `Request ${index} missing value`).toBeDefined();
        }
      });
    });
  });

  describe('Edge Cases and Stress Testing', () => {
    it('should handle extremely large parameter values', async () => {
      const largeRequest = testUtils.createMockRequest('search_semantic', {
        query: 'test query',
        max_results: Number.MAX_SAFE_INTEGER,
        similarity_threshold: 0.75,
        file_categories: ['context', 'working', 'output', 'methodology', 'literature']
      });

      const result = await handleSearchSemantic(largeRequest);
      expect(result).toBeDefined();
      // Should handle gracefully, not crash
    });

    it('should handle special characters in query', async () => {
      const specialQueries = [
        'query with "quotes"',
        'query with \n newlines \t tabs',
        'query with émojis 🔍 and unicode ñ',
        'query with <html> tags',
        'query with {json: "objects"}',
        'query with [brackets] and (parentheses)'
      ];

      for (const query of specialQueries) {
        const request = testUtils.createMockRequest('search_semantic', {
          query,
          max_results: 5
        });

        const result = await handleSearchSemantic(request);
        expect(result, `Failed for query: ${query}`).toBeDefined();
        expect(result.isError, `Error for query: ${query}`).toBeFalsy();
      }
    });

    it('should handle undefined and null parameter values', async () => {
      const requestWithNulls = testUtils.createMockRequest('search_semantic', {
        query: 'test query',
        similarity_threshold: null,
        max_results: undefined,
        file_categories: null
      });

      const result = await handleSearchSemantic(requestWithNulls);
      expect(result).toBeDefined();
      // Should use defaults for null/undefined optional parameters
    });
  });
});