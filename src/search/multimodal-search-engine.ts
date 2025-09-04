/**
 * Multimodal Search Engine
 * Advanced cross-modal search capabilities with text-to-image and image-to-text search
 * Implements hybrid ranking with semantic similarity, keyword matching, and relevance scoring
 */

import { QdrantClient } from '@qdrant/js-client-rest';
import FlexSearch from 'flexsearch';
import { EventEmitter } from 'events';
import { performance } from 'perf_hooks';
import EmbeddingService from '../embeddings/embedding-service';
import MCLIPClient from '../embeddings/mclip-client';

// Types and interfaces
export interface SearchQuery {
  text?: string;
  image_path?: string;
  filters?: SearchFilters;
  options?: SearchOptions;
}

export interface SearchFilters {
  document_ids?: string[];
  page_numbers?: number[];
  content_types?: ('text' | 'image' | 'table')[];
  languages?: string[];
  confidence_threshold?: number;
  date_range?: {
    start: Date;
    end: Date;
  };
  authors?: string[];
  keywords?: string[];
}

export interface SearchOptions {
  search_type: 'semantic' | 'keyword' | 'hybrid' | 'cross_modal';
  top_k: number;
  similarity_threshold: number;
  enable_reranking: boolean;
  include_snippets: boolean;
  snippet_length: number;
  diversify_results: boolean;
  explain_ranking: boolean;
}

export interface SearchResult {
  node_id: string;
  score: number;
  content: string;
  snippet?: string;
  metadata: {
    document_id: string;
    page_number: number;
    content_type: 'text' | 'image' | 'table';
    position: { x: number; y: number };
    confidence: number;
    language?: string;
    image_path?: string;
    image_type?: string;
  };
  ranking_explanation?: {
    semantic_score: number;
    keyword_score: number;
    cross_modal_score: number;
    final_score: number;
    ranking_factors: string[];
  };
  relationships?: Array<{
    related_node_id: string;
    relationship_type: string;
    confidence: number;
  }>;
}

export interface SearchResponse {
  query: SearchQuery;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
  search_strategy: string;
  facets?: {
    documents: Array<{ document_id: string; count: number }>;
    content_types: Array<{ type: string; count: number }>;
    languages: Array<{ language: string; count: number }>;
    pages: Array<{ page: number; count: number }>;
  };
  suggestions?: string[];
}

export interface SearchEngineConfig {
  qdrant_url: string;
  embedding_service: EmbeddingService;
  collections: {
    text_chunks: string;
    image_embeddings: string;
    cross_modal_index: string;
  };
  flexsearch_config: {
    encode: string;
    tokenize: string;
    threshold: number;
    resolution: number;
    depth: number;
  };
  ranking_weights: {
    semantic: number;
    keyword: number;
    cross_modal: number;
    recency: number;
    confidence: number;
  };
  performance: {
    max_concurrent_searches: number;
    cache_size: number;
    cache_ttl_ms: number;
  };
}

// Default configuration
const DEFAULT_CONFIG: SearchEngineConfig = {
  qdrant_url: 'http://localhost:6333',
  embedding_service: null as any, // Will be injected
  collections: {
    text_chunks: 'mcp_text_chunks',
    image_embeddings: 'mcp_image_embeddings',
    cross_modal_index: 'mcp_cross_modal_index'
  },
  flexsearch_config: {
    encode: 'icase',
    tokenize: 'forward',
    threshold: 1,
    resolution: 3,
    depth: 2
  },
  ranking_weights: {
    semantic: 0.4,
    keyword: 0.3,
    cross_modal: 0.2,
    recency: 0.05,
    confidence: 0.05
  },
  performance: {
    max_concurrent_searches: 5,
    cache_size: 1000,
    cache_ttl_ms: 300000 // 5 minutes
  }
};

export class MultimodalSearchEngine extends EventEmitter {
  private config: SearchEngineConfig;
  private qdrantClient: QdrantClient;
  private embeddingService: EmbeddingService;
  private flexSearchIndex: any;
  private documentIndex: Map<string, any> = new Map();
  private searchCache: Map<string, { result: SearchResponse; timestamp: number }> = new Map();
  private searchStats = {
    total_searches: 0,
    semantic_searches: 0,
    keyword_searches: 0,
    hybrid_searches: 0,
    cross_modal_searches: 0,
    average_search_time: 0,
    cache_hits: 0,
    cache_misses: 0
  };

  constructor(config: Partial<SearchEngineConfig> & { embedding_service: EmbeddingService }) {
    super();
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.embeddingService = config.embedding_service;
    
    // Initialize Qdrant client
    this.qdrantClient = new QdrantClient({
      url: this.config.qdrant_url
    });

    // Initialize FlexSearch
    this.initializeFlexSearch();
  }

  private initializeFlexSearch(): void {
    // @ts-ignore - FlexSearch types may not be perfect
    this.flexSearchIndex = new FlexSearch.Document({
      document: {
        id: 'node_id',
        index: ['content', 'metadata.document_id', 'metadata.keywords']
      },
      ...this.config.flexsearch_config
    });
  }

  /**
   * Index documents for search
   */
  async indexDocument(document: {
    nodes: Array<{
      node_id: string;
      content: string;
      metadata: any;
      embedding?: number[];
    }>;
  }): Promise<void> {
    // Add to FlexSearch
    for (const node of document.nodes) {
      await this.flexSearchIndex.addAsync(node.node_id, {
        node_id: node.node_id,
        content: node.content,
        metadata: node.metadata
      });
      
      // Store in document index for metadata lookups
      this.documentIndex.set(node.node_id, node);
    }

    this.emit('document_indexed', {
      document_id: document.nodes[0]?.metadata?.document_id,
      nodes_count: document.nodes.length
    });
  }

  /**
   * Main search method with multiple strategies
   */
  async search(query: SearchQuery): Promise<SearchResponse> {
    const startTime = performance.now();
    
    // Generate cache key
    const cacheKey = this.generateCacheKey(query);
    
    // Check cache
    const cached = this.searchCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < this.config.performance.cache_ttl_ms) {
      this.searchStats.cache_hits++;
      this.emit('search_cache_hit', { query, cache_key: cacheKey });
      return cached.result;
    }

    this.searchStats.cache_misses++;
    
    try {
      let results: SearchResult[] = [];
      let searchStrategy = '';

      // Determine search strategy
      const options: SearchOptions = {
        search_type: 'hybrid',
        top_k: 10,
        similarity_threshold: 0.7,
        enable_reranking: true,
        include_snippets: true,
        snippet_length: 200,
        diversify_results: true,
        explain_ranking: false,
        ...query.options
      };

      switch (options.search_type) {
        case 'semantic':
          results = await this.semanticSearch(query, options);
          searchStrategy = 'semantic';
          this.searchStats.semantic_searches++;
          break;
        
        case 'keyword':
          results = await this.keywordSearch(query, options);
          searchStrategy = 'keyword';
          this.searchStats.keyword_searches++;
          break;
        
        case 'cross_modal':
          results = await this.crossModalSearch(query, options);
          searchStrategy = 'cross_modal';
          this.searchStats.cross_modal_searches++;
          break;
        
        case 'hybrid':
        default:
          results = await this.hybridSearch(query, options);
          searchStrategy = 'hybrid';
          this.searchStats.hybrid_searches++;
          break;
      }

      // Apply post-processing
      if (options.enable_reranking) {
        results = this.rerankResults(results, query, options);
      }

      if (options.diversify_results) {
        results = this.diversifyResults(results);
      }

      if (options.include_snippets) {
        results = this.addSnippets(results, query, options.snippet_length);
      }

      // Limit results
      results = results.slice(0, options.top_k);

      const searchTime = performance.now() - startTime;

      // Create response
      const response: SearchResponse = {
        query,
        results,
        total_results: results.length,
        search_time_ms: searchTime,
        search_strategy: searchStrategy,
        facets: await this.generateFacets(results),
        suggestions: await this.generateSuggestions(query)
      };

      // Cache result
      this.searchCache.set(cacheKey, {
        result: response,
        timestamp: Date.now()
      });

      // Clean cache if too large
      if (this.searchCache.size > this.config.performance.cache_size) {
        this.cleanCache();
      }

      // Update stats
      this.updateSearchStats(searchTime);
      
      this.emit('search_completed', {
        query,
        results_count: results.length,
        search_time: searchTime,
        strategy: searchStrategy
      });

      return response;

    } catch (error) {
      this.emit('search_error', { query, error: error.message });
      throw new Error(`Search failed: ${error.message}`);
    }
  }

  /**
   * Semantic search using vector similarity
   */
  private async semanticSearch(query: SearchQuery, options: SearchOptions): Promise<SearchResult[]> {
    const results: SearchResult[] = [];

    try {
      // Generate query embedding
      let queryEmbedding: number[];
      
      if (query.text) {
        const embedding = await this.embeddingService.embedText(query.text);
        queryEmbedding = embedding.embedding;
      } else if (query.image_path) {
        const embedding = await this.embeddingService.embedImage(query.image_path);
        queryEmbedding = embedding.embedding;
      } else {
        throw new Error('Either text or image_path must be provided for semantic search');
      }

      // Search text chunks
      if (!query.filters?.content_types || query.filters.content_types.includes('text')) {
        const textResults = await this.searchVectorCollection(
          this.config.collections.text_chunks,
          queryEmbedding,
          options,
          'text'
        );
        results.push(...textResults);
      }

      // Search image embeddings
      if (!query.filters?.content_types || query.filters.content_types.includes('image')) {
        const imageResults = await this.searchVectorCollection(
          this.config.collections.image_embeddings,
          queryEmbedding,
          options,
          'image'
        );
        results.push(...imageResults);
      }

      return results;

    } catch (error) {
      throw new Error(`Semantic search failed: ${error.message}`);
    }
  }

  private async searchVectorCollection(
    collection: string,
    queryEmbedding: number[],
    options: SearchOptions,
    contentType: 'text' | 'image'
  ): Promise<SearchResult[]> {
    const searchParams: any = {
      vector: queryEmbedding,
      limit: options.top_k * 2, // Get more for reranking
      with_payload: true,
      with_vector: false,
      score_threshold: options.similarity_threshold
    };

    // Add filters if provided
    if (Object.keys(query.filters || {}).length > 0) {
      searchParams.filter = this.buildQdrantFilter(query.filters!);
    }

    try {
      const response = await this.qdrantClient.search(collection, searchParams);

      return response.map(point => ({
        node_id: point.id as string,
        score: point.score!,
        content: point.payload!.content as string,
        metadata: {
          document_id: point.payload!.metadata.document_id,
          page_number: point.payload!.metadata.page_number,
          content_type: contentType,
          position: point.payload!.metadata.position || { x: 0, y: 0 },
          confidence: point.payload!.metadata.confidence || 0.8,
          language: point.payload!.metadata.language,
          image_path: point.payload!.metadata.image_path,
          image_type: point.payload!.metadata.image_type
        },
        relationships: point.payload!.relationships || []
      }));

    } catch (error) {
      console.warn(`Failed to search collection ${collection}: ${error.message}`);
      return [];
    }
  }

  /**
   * Keyword search using FlexSearch
   */
  private async keywordSearch(query: SearchQuery, options: SearchOptions): Promise<SearchResult[]> {
    if (!query.text) {
      throw new Error('Text query required for keyword search');
    }

    try {
      const searchResults = await this.flexSearchIndex.searchAsync(query.text, {
        limit: options.top_k * 2,
        suggest: true
      });

      const results: SearchResult[] = [];

      for (const result of searchResults) {
        const nodeData = this.documentIndex.get(result.id);
        if (nodeData) {
          results.push({
            node_id: result.id,
            score: result.score || 0.8,
            content: nodeData.content,
            metadata: {
              document_id: nodeData.metadata.document_id,
              page_number: nodeData.metadata.page_number,
              content_type: nodeData.metadata.content_type || 'text',
              position: nodeData.metadata.position || { x: 0, y: 0 },
              confidence: nodeData.metadata.confidence || 0.8,
              language: nodeData.metadata.language,
              image_path: nodeData.metadata.image_path,
              image_type: nodeData.metadata.image_type
            }
          });
        }
      }

      return results;

    } catch (error) {
      throw new Error(`Keyword search failed: ${error.message}`);
    }
  }

  /**
   * Cross-modal search (text-to-image, image-to-text)
   */
  private async crossModalSearch(query: SearchQuery, options: SearchOptions): Promise<SearchResult[]> {
    const results: SearchResult[] = [];

    try {
      if (query.text && query.image_path) {
        // Both text and image provided - find related content
        const textResults = await this.semanticSearch({ text: query.text, filters: query.filters }, options);
        const imageResults = await this.semanticSearch({ image_path: query.image_path, filters: query.filters }, options);
        
        // Merge and deduplicate
        const combined = [...textResults, ...imageResults];
        const unique = this.deduplicateResults(combined);
        results.push(...unique);

      } else if (query.text) {
        // Text-to-image search: find images related to text query
        const textEmbedding = await this.embeddingService.embedText(query.text);
        const imageResults = await this.searchVectorCollection(
          this.config.collections.image_embeddings,
          textEmbedding.embedding,
          options,
          'image'
        );
        results.push(...imageResults);

      } else if (query.image_path) {
        // Image-to-text search: find text related to image query
        const imageEmbedding = await this.embeddingService.embedImage(query.image_path);
        const textResults = await this.searchVectorCollection(
          this.config.collections.text_chunks,
          imageEmbedding.embedding,
          options,
          'text'
        );
        results.push(...textResults);
      }

      return results;

    } catch (error) {
      throw new Error(`Cross-modal search failed: ${error.message}`);
    }
  }

  /**
   * Hybrid search combining multiple strategies
   */
  private async hybridSearch(query: SearchQuery, options: SearchOptions): Promise<SearchResult[]> {
    const promises: Promise<SearchResult[]>[] = [];
    
    // Run semantic and keyword searches in parallel
    if (query.text) {
      promises.push(this.semanticSearch(query, { ...options, top_k: options.top_k * 2 }));
      promises.push(this.keywordSearch(query, { ...options, top_k: options.top_k * 2 }));
    }
    
    // Add cross-modal if applicable
    if (query.image_path) {
      promises.push(this.crossModalSearch(query, { ...options, top_k: options.top_k * 2 }));
    }

    try {
      const resultSets = await Promise.all(promises);
      
      // Merge results using reciprocal rank fusion
      const fusedResults = this.reciprocalRankFusion(resultSets, this.config.ranking_weights);
      
      return fusedResults;

    } catch (error) {
      throw new Error(`Hybrid search failed: ${error.message}`);
    }
  }

  /**
   * Reciprocal Rank Fusion for combining multiple result sets
   */
  private reciprocalRankFusion(resultSets: SearchResult[][], weights: any, k: number = 60): SearchResult[] {
    const nodeScores = new Map<string, { result: SearchResult; score: number; sources: string[] }>();

    for (let setIndex = 0; setIndex < resultSets.length; setIndex++) {
      const results = resultSets[setIndex];
      const setName = setIndex === 0 ? 'semantic' : setIndex === 1 ? 'keyword' : 'cross_modal';
      const weight = weights[setName] || 1.0;

      for (let rank = 0; rank < results.length; rank++) {
        const result = results[rank];
        const nodeId = result.node_id;
        const rrfScore = weight / (k + rank + 1);

        if (nodeScores.has(nodeId)) {
          const existing = nodeScores.get(nodeId)!;
          existing.score += rrfScore;
          existing.sources.push(setName);
        } else {
          nodeScores.set(nodeId, {
            result,
            score: rrfScore,
            sources: [setName]
          });
        }
      }
    }

    // Sort by combined score and return results
    return Array.from(nodeScores.values())
      .sort((a, b) => b.score - a.score)
      .map(item => ({
        ...item.result,
        score: item.score,
        ranking_explanation: {
          semantic_score: 0,
          keyword_score: 0,
          cross_modal_score: 0,
          final_score: item.score,
          ranking_factors: [`RRF from: ${item.sources.join(', ')}`]
        }
      }));
  }

  /**
   * Re-rank results using additional signals
   */
  private rerankResults(results: SearchResult[], query: SearchQuery, options: SearchOptions): SearchResult[] {
    return results.map(result => {
      let boostedScore = result.score;
      const factors: string[] = [];

      // Confidence boost
      const confidenceBoost = result.metadata.confidence * this.config.ranking_weights.confidence;
      boostedScore += confidenceBoost;
      factors.push(`confidence_boost: +${confidenceBoost.toFixed(3)}`);

      // Content type preference (boost images for visual queries)
      if (query.image_path && result.metadata.content_type === 'image') {
        boostedScore *= 1.2;
        factors.push('visual_query_image_boost: +20%');
      }

      // Language matching
      if (query.filters?.languages && result.metadata.language) {
        if (query.filters.languages.includes(result.metadata.language)) {
          boostedScore *= 1.1;
          factors.push('language_match_boost: +10%');
        }
      }

      return {
        ...result,
        score: boostedScore,
        ranking_explanation: {
          ...result.ranking_explanation,
          final_score: boostedScore,
          ranking_factors: factors
        }
      };
    }).sort((a, b) => b.score - a.score);
  }

  /**
   * Diversify results using Maximal Marginal Relevance
   */
  private diversifyResults(results: SearchResult[], lambda: number = 0.7): SearchResult[] {
    if (results.length <= 1) return results;

    const diversified: SearchResult[] = [results[0]]; // Always include top result
    const remaining = results.slice(1);

    while (diversified.length < Math.min(results.length, 10) && remaining.length > 0) {
      let bestIndex = 0;
      let bestMMRScore = -Infinity;

      for (let i = 0; i < remaining.length; i++) {
        const candidate = remaining[i];
        
        // Calculate max similarity with already selected results
        let maxSim = 0;
        for (const selected of diversified) {
          const similarity = this.calculateTextSimilarity(candidate.content, selected.content);
          maxSim = Math.max(maxSim, similarity);
        }

        // MMR score: λ * relevance - (1-λ) * max_similarity
        const mmrScore = lambda * candidate.score - (1 - lambda) * maxSim;
        
        if (mmrScore > bestMMRScore) {
          bestMMRScore = mmrScore;
          bestIndex = i;
        }
      }

      diversified.push(remaining.splice(bestIndex, 1)[0]);
    }

    return diversified;
  }

  /**
   * Add contextual snippets to search results
   */
  private addSnippets(results: SearchResult[], query: SearchQuery, snippetLength: number): SearchResult[] {
    if (!query.text) return results;

    return results.map(result => {
      const snippet = this.extractSnippet(result.content, query.text!, snippetLength);
      return {
        ...result,
        snippet
      };
    });
  }

  private extractSnippet(content: string, query: string, maxLength: number): string {
    const words = content.split(/\s+/);
    const queryWords = query.toLowerCase().split(/\s+/);
    
    // Find best matching position
    let bestScore = 0;
    let bestStart = 0;
    
    for (let i = 0; i < words.length - 10; i++) {
      let score = 0;
      for (let j = i; j < Math.min(i + 30, words.length); j++) {
        if (queryWords.some(qw => words[j].toLowerCase().includes(qw))) {
          score += 1;
        }
      }
      if (score > bestScore) {
        bestScore = score;
        bestStart = i;
      }
    }
    
    // Extract snippet around best position
    const start = Math.max(0, bestStart - 5);
    const snippet = words.slice(start, start + Math.floor(maxLength / 6)).join(' ');
    
    return snippet.length > maxLength ? snippet.substring(0, maxLength) + '...' : snippet;
  }

  /**
   * Generate search facets for filtering
   */
  private async generateFacets(results: SearchResult[]): Promise<SearchResponse['facets']> {
    const documents = new Map<string, number>();
    const contentTypes = new Map<string, number>();
    const languages = new Map<string, number>();
    const pages = new Map<number, number>();

    for (const result of results) {
      // Document counts
      const docId = result.metadata.document_id;
      documents.set(docId, (documents.get(docId) || 0) + 1);

      // Content type counts
      const contentType = result.metadata.content_type;
      contentTypes.set(contentType, (contentTypes.get(contentType) || 0) + 1);

      // Language counts
      if (result.metadata.language) {
        const lang = result.metadata.language;
        languages.set(lang, (languages.get(lang) || 0) + 1);
      }

      // Page counts
      const page = result.metadata.page_number;
      pages.set(page, (pages.get(page) || 0) + 1);
    }

    return {
      documents: Array.from(documents.entries()).map(([document_id, count]) => ({ document_id, count })),
      content_types: Array.from(contentTypes.entries()).map(([type, count]) => ({ type, count })),
      languages: Array.from(languages.entries()).map(([language, count]) => ({ language, count })),
      pages: Array.from(pages.entries()).map(([page, count]) => ({ page, count }))
    };
  }

  /**
   * Generate search suggestions
   */
  private async generateSuggestions(query: SearchQuery): Promise<string[]> {
    // Simple suggestion implementation - could be enhanced with ML models
    const suggestions: string[] = [];
    
    if (query.text) {
      const words = query.text.split(/\s+/);
      if (words.length > 1) {
        suggestions.push(words.slice(0, -1).join(' ')); // Remove last word
        suggestions.push(query.text + ' analysis'); // Add common suffix
        suggestions.push(query.text + ' methodology');
      }
    }

    return suggestions;
  }

  // Utility methods
  private buildQdrantFilter(filters: SearchFilters): any {
    const conditions: any[] = [];

    if (filters.document_ids?.length) {
      conditions.push({
        key: 'metadata.document_id',
        match: { any: filters.document_ids }
      });
    }

    if (filters.page_numbers?.length) {
      conditions.push({
        key: 'metadata.page_number',
        match: { any: filters.page_numbers }
      });
    }

    if (filters.languages?.length) {
      conditions.push({
        key: 'metadata.language',
        match: { any: filters.languages }
      });
    }

    if (filters.confidence_threshold !== undefined) {
      conditions.push({
        key: 'metadata.confidence',
        range: { gte: filters.confidence_threshold }
      });
    }

    return conditions.length > 0 ? { must: conditions } : undefined;
  }

  private generateCacheKey(query: SearchQuery): string {
    return JSON.stringify({
      text: query.text,
      image: query.image_path ? 'has_image' : undefined,
      filters: query.filters,
      options: query.options
    });
  }

  private deduplicateResults(results: SearchResult[]): SearchResult[] {
    const seen = new Set<string>();
    return results.filter(result => {
      if (seen.has(result.node_id)) return false;
      seen.add(result.node_id);
      return true;
    });
  }

  private calculateTextSimilarity(text1: string, text2: string): number {
    // Simple Jaccard similarity
    const words1 = new Set(text1.toLowerCase().split(/\s+/));
    const words2 = new Set(text2.toLowerCase().split(/\s+/));
    const intersection = new Set([...words1].filter(x => words2.has(x)));
    const union = new Set([...words1, ...words2]);
    return intersection.size / union.size;
  }

  private cleanCache(): void {
    const entries = Array.from(this.searchCache.entries());
    entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
    
    // Remove oldest 20% of entries
    const toRemove = Math.floor(entries.length * 0.2);
    for (let i = 0; i < toRemove; i++) {
      this.searchCache.delete(entries[i][0]);
    }
  }

  private updateSearchStats(searchTime: number): void {
    this.searchStats.total_searches++;
    const totalTime = this.searchStats.average_search_time * (this.searchStats.total_searches - 1) + searchTime;
    this.searchStats.average_search_time = totalTime / this.searchStats.total_searches;
  }

  /**
   * Get search statistics
   */
  getSearchStats() {
    return {
      ...this.searchStats,
      cache_hit_rate: this.searchStats.cache_hits / (this.searchStats.cache_hits + this.searchStats.cache_misses),
      cache_size: this.searchCache.size
    };
  }

  /**
   * Clear search cache
   */
  clearCache(): void {
    this.searchCache.clear();
    this.emit('cache_cleared');
  }

  /**
   * Health check
   */
  async checkHealth() {
    const health = {
      search_engine: true,
      qdrant: false,
      embedding_service: false,
      flexsearch: true,
      overall: false
    };

    try {
      await this.qdrantClient.api('cluster').clusterStatus();
      health.qdrant = true;
    } catch (error) {
      console.warn(`Qdrant health check failed: ${error.message}`);
    }

    try {
      const embeddingHealth = await this.embeddingService.checkHealth();
      health.embedding_service = embeddingHealth.overall;
    } catch (error) {
      console.warn(`Embedding service health check failed: ${error.message}`);
    }

    health.overall = health.qdrant && health.embedding_service && health.flexsearch;
    return health;
  }
}

export default MultimodalSearchEngine;