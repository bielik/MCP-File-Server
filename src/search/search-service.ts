/**
 * Search Service
 * High-level search service providing MCP tools for AI agents
 * Implements agent choice architecture with separate tools for different search strategies
 */

import MultimodalSearchEngine, { 
  SearchQuery, 
  SearchResponse, 
  SearchOptions, 
  SearchFilters 
} from './multimodal-search-engine';
import EmbeddingService from '../embeddings/embedding-service';
import { EventEmitter } from 'events';
import * as path from 'path';
import { performance } from 'perf_hooks';

// MCP Tool interfaces
export interface SearchTextTool {
  name: 'search_text';
  description: 'Fast keyword and phrase search with multilingual support';
  inputSchema: {
    type: 'object';
    properties: {
      query: { type: 'string'; description: 'Text query to search for' };
      filters?: SearchFilters;
      top_k?: number;
      include_snippets?: boolean;
    };
    required: ['query'];
  };
}

export interface SearchSemanticTool {
  name: 'search_semantic';
  description: 'Conceptual search using M-CLIP text embeddings for meaning-based results';
  inputSchema: {
    type: 'object';
    properties: {
      query: { type: 'string'; description: 'Conceptual query for semantic search' };
      filters?: SearchFilters;
      top_k?: number;
      similarity_threshold?: number;
    };
    required: ['query'];
  };
}

export interface SearchMultimodalTool {
  name: 'search_multimodal';
  description: 'Cross-modal search across text and images - text→image and image→text';
  inputSchema: {
    type: 'object';
    properties: {
      text_query?: { type: 'string'; description: 'Text query for finding related images' };
      image_path?: { type: 'string'; description: 'Image path for finding related text' };
      search_mode: { 
        type: 'string'; 
        enum: ['text_to_image', 'image_to_text', 'cross_modal'];
        description: 'Type of cross-modal search to perform'
      };
      filters?: SearchFilters;
      top_k?: number;
    };
    required: ['search_mode'];
  };
}

export interface SearchAdvancedTool {
  name: 'search_advanced';
  description: 'Advanced hybrid search combining multiple strategies with custom options';
  inputSchema: {
    type: 'object';
    properties: {
      query: { type: 'string'; description: 'Search query' };
      image_path?: { type: 'string'; description: 'Optional image for multimodal search' };
      search_strategy: {
        type: 'string';
        enum: ['keyword', 'semantic', 'hybrid', 'cross_modal'];
        description: 'Search strategy to use'
      };
      options: SearchOptions;
      filters?: SearchFilters;
    };
    required: ['query', 'search_strategy'];
  };
}

// Search result formatting for MCP responses
export interface MCPSearchResult {
  node_id: string;
  score: number;
  content: string;
  snippet?: string;
  document_id: string;
  page_number: number;
  content_type: 'text' | 'image' | 'table';
  image_path?: string;
  confidence: number;
  relationships?: Array<{
    related_node_id: string;
    relationship_type: string;
  }>;
}

export interface MCPSearchResponse {
  results: MCPSearchResult[];
  total_results: number;
  search_time_ms: number;
  search_strategy: string;
  query_summary: string;
  suggestions?: string[];
  facets?: {
    documents: Array<{ document_id: string; count: number }>;
    content_types: Array<{ type: string; count: number }>;
    pages: Array<{ page: number; count: number }>;
  };
}

export interface SearchServiceConfig {
  embedding_service: EmbeddingService;
  qdrant_url: string;
  default_top_k: number;
  default_similarity_threshold: number;
  max_snippet_length: number;
  enable_query_expansion: boolean;
  enable_result_caching: boolean;
}

const DEFAULT_CONFIG: SearchServiceConfig = {
  embedding_service: null as any,
  qdrant_url: 'http://localhost:6333',
  default_top_k: 10,
  default_similarity_threshold: 0.7,
  max_snippet_length: 200,
  enable_query_expansion: true,
  enable_result_caching: true
};

export class SearchService extends EventEmitter {
  private config: SearchServiceConfig;
  private searchEngine: MultimodalSearchEngine;
  private queryHistory: Array<{ query: string; timestamp: Date; results_count: number }> = [];
  private searchStats = {
    total_searches: 0,
    text_searches: 0,
    semantic_searches: 0,
    multimodal_searches: 0,
    advanced_searches: 0,
    average_search_time: 0,
    popular_queries: new Map<string, number>()
  };

  constructor(config: Partial<SearchServiceConfig> & { embedding_service: EmbeddingService }) {
    super();
    this.config = { ...DEFAULT_CONFIG, ...config };

    // Initialize multimodal search engine
    this.searchEngine = new MultimodalSearchEngine({
      embedding_service: this.config.embedding_service,
      qdrant_url: this.config.qdrant_url
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.searchEngine.on('search_completed', (event) => {
      this.updateSearchStats(event.search_time, event.strategy);
      this.addToQueryHistory(event.query, event.results_count);
    });

    this.searchEngine.on('search_error', (event) => {
      this.emit('search_error', event);
    });
  }

  /**
   * MCP Tool: Fast keyword and phrase search
   */
  async searchText(params: {
    query: string;
    filters?: SearchFilters;
    top_k?: number;
    include_snippets?: boolean;
  }): Promise<MCPSearchResponse> {
    const startTime = performance.now();
    
    try {
      const searchQuery: SearchQuery = {
        text: params.query,
        filters: params.filters,
        options: {
          search_type: 'keyword',
          top_k: params.top_k || this.config.default_top_k,
          similarity_threshold: this.config.default_similarity_threshold,
          enable_reranking: false,
          include_snippets: params.include_snippets ?? true,
          snippet_length: this.config.max_snippet_length,
          diversify_results: false,
          explain_ranking: false
        }
      };

      // Expand query if enabled
      if (this.config.enable_query_expansion) {
        searchQuery.text = await this.expandQuery(params.query);
      }

      const response = await this.searchEngine.search(searchQuery);
      this.searchStats.text_searches++;
      
      return this.formatMCPResponse(response, 'Fast keyword search');
      
    } catch (error) {
      this.emit('search_error', { tool: 'search_text', query: params.query, error: error.message });
      throw error;
    }
  }

  /**
   * MCP Tool: Semantic search using embeddings
   */
  async searchSemantic(params: {
    query: string;
    filters?: SearchFilters;
    top_k?: number;
    similarity_threshold?: number;
  }): Promise<MCPSearchResponse> {
    const startTime = performance.now();
    
    try {
      const searchQuery: SearchQuery = {
        text: params.query,
        filters: params.filters,
        options: {
          search_type: 'semantic',
          top_k: params.top_k || this.config.default_top_k,
          similarity_threshold: params.similarity_threshold || this.config.default_similarity_threshold,
          enable_reranking: true,
          include_snippets: true,
          snippet_length: this.config.max_snippet_length,
          diversify_results: true,
          explain_ranking: false
        }
      };

      const response = await this.searchEngine.search(searchQuery);
      this.searchStats.semantic_searches++;
      
      return this.formatMCPResponse(response, 'Semantic concept search');
      
    } catch (error) {
      this.emit('search_error', { tool: 'search_semantic', query: params.query, error: error.message });
      throw error;
    }
  }

  /**
   * MCP Tool: Cross-modal search
   */
  async searchMultimodal(params: {
    text_query?: string;
    image_path?: string;
    search_mode: 'text_to_image' | 'image_to_text' | 'cross_modal';
    filters?: SearchFilters;
    top_k?: number;
  }): Promise<MCPSearchResponse> {
    const startTime = performance.now();
    
    try {
      // Validate input
      if (params.search_mode === 'text_to_image' && !params.text_query) {
        throw new Error('text_query required for text_to_image search');
      }
      if (params.search_mode === 'image_to_text' && !params.image_path) {
        throw new Error('image_path required for image_to_text search');
      }

      const searchQuery: SearchQuery = {
        text: params.text_query,
        image_path: params.image_path,
        filters: params.filters,
        options: {
          search_type: 'cross_modal',
          top_k: params.top_k || this.config.default_top_k,
          similarity_threshold: this.config.default_similarity_threshold,
          enable_reranking: true,
          include_snippets: true,
          snippet_length: this.config.max_snippet_length,
          diversify_results: true,
          explain_ranking: false
        }
      };

      const response = await this.searchEngine.search(searchQuery);
      this.searchStats.multimodal_searches++;
      
      const summary = this.generateMultimodalSummary(params.search_mode, params.text_query, params.image_path);
      return this.formatMCPResponse(response, summary);
      
    } catch (error) {
      this.emit('search_error', { tool: 'search_multimodal', params, error: error.message });
      throw error;
    }
  }

  /**
   * MCP Tool: Advanced hybrid search with custom options
   */
  async searchAdvanced(params: {
    query: string;
    image_path?: string;
    search_strategy: 'keyword' | 'semantic' | 'hybrid' | 'cross_modal';
    options: Partial<SearchOptions>;
    filters?: SearchFilters;
  }): Promise<MCPSearchResponse> {
    const startTime = performance.now();
    
    try {
      const defaultOptions: SearchOptions = {
        search_type: params.search_strategy,
        top_k: this.config.default_top_k,
        similarity_threshold: this.config.default_similarity_threshold,
        enable_reranking: true,
        include_snippets: true,
        snippet_length: this.config.max_snippet_length,
        diversify_results: true,
        explain_ranking: true
      };

      const searchQuery: SearchQuery = {
        text: params.query,
        image_path: params.image_path,
        filters: params.filters,
        options: { ...defaultOptions, ...params.options }
      };

      const response = await this.searchEngine.search(searchQuery);
      this.searchStats.advanced_searches++;
      
      return this.formatMCPResponse(response, `Advanced ${params.search_strategy} search`);
      
    } catch (error) {
      this.emit('search_error', { tool: 'search_advanced', params, error: error.message });
      throw error;
    }
  }

  /**
   * Search for similar documents or content
   */
  async findSimilar(nodeId: string, top_k: number = 5): Promise<MCPSearchResponse> {
    try {
      // This would need to be implemented based on stored node embeddings
      // For now, return a placeholder
      const response: MCPSearchResponse = {
        results: [],
        total_results: 0,
        search_time_ms: 0,
        search_strategy: 'similarity',
        query_summary: `Finding content similar to node: ${nodeId}`,
        suggestions: []
      };

      return response;
    } catch (error) {
      throw new Error(`Find similar failed: ${error.message}`);
    }
  }

  /**
   * Get search suggestions based on query
   */
  async getSearchSuggestions(partialQuery: string): Promise<string[]> {
    try {
      // Simple suggestion based on query history
      const suggestions = Array.from(this.searchStats.popular_queries.entries())
        .filter(([query, count]) => query.toLowerCase().includes(partialQuery.toLowerCase()))
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([query, count]) => query);

      return suggestions;
    } catch (error) {
      console.warn(`Failed to get suggestions: ${error.message}`);
      return [];
    }
  }

  /**
   * Format search response for MCP
   */
  private formatMCPResponse(response: SearchResponse, querySummary: string): MCPSearchResponse {
    const results: MCPSearchResult[] = response.results.map(result => ({
      node_id: result.node_id,
      score: Math.round(result.score * 1000) / 1000, // Round to 3 decimal places
      content: result.content,
      snippet: result.snippet,
      document_id: result.metadata.document_id,
      page_number: result.metadata.page_number,
      content_type: result.metadata.content_type,
      image_path: result.metadata.image_path,
      confidence: Math.round(result.metadata.confidence * 1000) / 1000,
      relationships: result.relationships?.map(rel => ({
        related_node_id: rel.related_node_id,
        relationship_type: rel.relationship_type
      }))
    }));

    return {
      results,
      total_results: response.total_results,
      search_time_ms: Math.round(response.search_time_ms),
      search_strategy: response.search_strategy,
      query_summary: querySummary,
      suggestions: response.suggestions,
      facets: response.facets
    };
  }

  private generateMultimodalSummary(
    searchMode: string, 
    textQuery?: string, 
    imagePath?: string
  ): string {
    switch (searchMode) {
      case 'text_to_image':
        return `Text→Image search: "${textQuery}"`;
      case 'image_to_text':
        return `Image→Text search: ${path.basename(imagePath || 'image')}`;
      case 'cross_modal':
        return `Cross-modal search combining text and image queries`;
      default:
        return 'Multimodal search';
    }
  }

  private async expandQuery(query: string): Promise<string> {
    // Simple query expansion - could be enhanced with ML models
    const synonyms: Record<string, string[]> = {
      'AI': ['artificial intelligence', 'machine learning', 'deep learning'],
      'ML': ['machine learning', 'AI', 'artificial intelligence'],
      'research': ['study', 'investigation', 'analysis'],
      'methodology': ['method', 'approach', 'technique'],
      'results': ['findings', 'outcomes', 'conclusions']
    };

    let expandedQuery = query;
    const words = query.split(/\s+/);
    
    for (const word of words) {
      const upperWord = word.toUpperCase();
      if (synonyms[upperWord]) {
        expandedQuery += ' ' + synonyms[upperWord][0]; // Add first synonym
      }
    }

    return expandedQuery;
  }

  private updateSearchStats(searchTime: number, strategy: string): void {
    this.searchStats.total_searches++;
    const totalTime = this.searchStats.average_search_time * (this.searchStats.total_searches - 1) + searchTime;
    this.searchStats.average_search_time = totalTime / this.searchStats.total_searches;
  }

  private addToQueryHistory(query: any, resultsCount: number): void {
    const queryText = query.text || 'multimodal_query';
    
    this.queryHistory.push({
      query: queryText,
      timestamp: new Date(),
      results_count: resultsCount
    });

    // Update popular queries
    const currentCount = this.searchStats.popular_queries.get(queryText) || 0;
    this.searchStats.popular_queries.set(queryText, currentCount + 1);

    // Keep only recent history
    if (this.queryHistory.length > 1000) {
      this.queryHistory = this.queryHistory.slice(-500);
    }
  }

  /**
   * Get MCP tool definitions for registration
   */
  getMCPTools(): Array<SearchTextTool | SearchSemanticTool | SearchMultimodalTool | SearchAdvancedTool> {
    return [
      {
        name: 'search_text',
        description: 'Fast keyword and phrase search with multilingual support',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'Text query to search for' },
            filters: {
              type: 'object',
              properties: {
                document_ids: { type: 'array', items: { type: 'string' } },
                page_numbers: { type: 'array', items: { type: 'number' } },
                content_types: { type: 'array', items: { type: 'string', enum: ['text', 'image', 'table'] } },
                languages: { type: 'array', items: { type: 'string' } }
              }
            },
            top_k: { type: 'number', default: 10, description: 'Maximum number of results' },
            include_snippets: { type: 'boolean', default: true, description: 'Include text snippets in results' }
          },
          required: ['query']
        }
      },
      {
        name: 'search_semantic',
        description: 'Conceptual search using M-CLIP text embeddings for meaning-based results',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'Conceptual query for semantic search' },
            filters: {
              type: 'object',
              properties: {
                document_ids: { type: 'array', items: { type: 'string' } },
                page_numbers: { type: 'array', items: { type: 'number' } },
                content_types: { type: 'array', items: { type: 'string', enum: ['text', 'image', 'table'] } },
                languages: { type: 'array', items: { type: 'string' } }
              }
            },
            top_k: { type: 'number', default: 10 },
            similarity_threshold: { type: 'number', default: 0.7, description: 'Minimum similarity score' }
          },
          required: ['query']
        }
      },
      {
        name: 'search_multimodal',
        description: 'Cross-modal search across text and images - text→image and image→text',
        inputSchema: {
          type: 'object',
          properties: {
            text_query: { type: 'string', description: 'Text query for finding related images' },
            image_path: { type: 'string', description: 'Image path for finding related text' },
            search_mode: { 
              type: 'string', 
              enum: ['text_to_image', 'image_to_text', 'cross_modal'],
              description: 'Type of cross-modal search to perform'
            },
            filters: {
              type: 'object',
              properties: {
                document_ids: { type: 'array', items: { type: 'string' } },
                page_numbers: { type: 'array', items: { type: 'number' } },
                content_types: { type: 'array', items: { type: 'string', enum: ['text', 'image', 'table'] } }
              }
            },
            top_k: { type: 'number', default: 10 }
          },
          required: ['search_mode']
        }
      },
      {
        name: 'search_advanced',
        description: 'Advanced hybrid search combining multiple strategies with custom options',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'Search query' },
            image_path: { type: 'string', description: 'Optional image for multimodal search' },
            search_strategy: {
              type: 'string',
              enum: ['keyword', 'semantic', 'hybrid', 'cross_modal'],
              description: 'Search strategy to use'
            },
            options: {
              type: 'object',
              properties: {
                top_k: { type: 'number', default: 10 },
                similarity_threshold: { type: 'number', default: 0.7 },
                enable_reranking: { type: 'boolean', default: true },
                include_snippets: { type: 'boolean', default: true },
                diversify_results: { type: 'boolean', default: true },
                explain_ranking: { type: 'boolean', default: false }
              }
            },
            filters: { type: 'object' }
          },
          required: ['query', 'search_strategy']
        }
      }
    ];
  }

  /**
   * Get search service statistics
   */
  getSearchStats() {
    const popularQueries = Array.from(this.searchStats.popular_queries.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([query, count]) => ({ query, count }));

    return {
      ...this.searchStats,
      popular_queries: popularQueries,
      query_history_size: this.queryHistory.length,
      engine_stats: this.searchEngine.getSearchStats()
    };
  }

  /**
   * Health check
   */
  async checkHealth() {
    const engineHealth = await this.searchEngine.checkHealth();
    
    return {
      search_service: true,
      search_engine: engineHealth.overall,
      tools_registered: 4,
      query_history_size: this.queryHistory.length,
      total_searches: this.searchStats.total_searches,
      overall: engineHealth.overall
    };
  }

  /**
   * Clear all caches and reset stats
   */
  async clearCaches(): Promise<void> {
    this.searchEngine.clearCache();
    this.queryHistory = [];
    this.searchStats.popular_queries.clear();
    this.emit('caches_cleared');
  }
}

export default SearchService;