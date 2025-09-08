import { aiService } from '../../services/AiService.js';
import { vectorDbService, type SearchResult } from '../../services/VectorDb.js';
import { logWithContext } from '../../../utils/logger.js';

/**
 * Semantic Search Service using Vector Embeddings
 * 
 * This service provides semantic search capabilities using M-CLIP embeddings
 * and Qdrant vector similarity search. It supports both text-to-text semantic
 * search and cross-modal text-to-image/image-to-text search.
 * 
 * Features:
 * - Semantic text search using embedding similarity
 * - Cross-modal search (text queries find images, image queries find text)
 * - Configurable similarity thresholds and result limits
 * - Result ranking and filtering
 * - Support for both text and image collections
 */

export interface SemanticSearchResult {
  id: string;
  score: number;
  documentId?: string;
  filePath: string;
  contentType: 'text' | 'image';
  textContent?: string;
  imageCaption?: string;
  pageNumber?: number;
  chunkIndex?: number;
  documentTitle?: string;
  createdAt?: string;
}

export interface SemanticSearchOptions {
  limit?: number;
  threshold?: number;
  searchMode?: 'text_only' | 'image_only' | 'multimodal';
  includeText?: boolean;
  includeImages?: boolean;
  filter?: Record<string, any>;
  boostTextResults?: boolean;
  boostImageResults?: boolean;
}

export interface SearchStats {
  totalQueries: number;
  averageResponseTime: number;
  lastQuery: Date | null;
  textCollectionSize: number;
  imageCollectionSize: number;
}

/**
 * Semantic Search Service Class
 */
export class SemanticSearchService {
  private static instance: SemanticSearchService | null = null;
  private isInitialized = false;
  private stats: SearchStats = {
    totalQueries: 0,
    averageResponseTime: 0,
    lastQuery: null,
    textCollectionSize: 0,
    imageCollectionSize: 0,
  };

  private constructor() {
    logWithContext.info('SemanticSearchService: Creating semantic search service instance');
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): SemanticSearchService {
    if (!SemanticSearchService.instance) {
      SemanticSearchService.instance = new SemanticSearchService();
    }
    return SemanticSearchService.instance;
  }

  /**
   * Initialize the semantic search service
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    const startTime = Date.now();

    try {
      logWithContext.info('SemanticSearchService: Initializing semantic search service');

      // Ensure required services are initialized
      if (!aiService.isReady()) {
        throw new Error('AiService not ready - embeddings cannot be generated');
      }

      if (!vectorDbService.isReady()) {
        throw new Error('VectorDbService not ready - vector search unavailable');
      }

      // Update collection size stats
      await this.updateCollectionStats();

      this.isInitialized = true;
      const duration = Date.now() - startTime;

      logWithContext.info('SemanticSearchService: Initialization completed', {
        duration: `${duration}ms`,
        textCollectionSize: this.stats.textCollectionSize,
        imageCollectionSize: this.stats.imageCollectionSize,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('SemanticSearchService: Initialization failed', error as Error, {
        duration: `${duration}ms`,
      });

      this.isInitialized = false;
      throw new Error(`Failed to initialize SemanticSearchService: ${(error as Error).message}`);
    }
  }

  /**
   * Execute semantic text search
   */
  public async searchText(
    query: string,
    options: SemanticSearchOptions = {}
  ): Promise<SemanticSearchResult[]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const startTime = Date.now();
    const opts = {
      limit: 10,
      threshold: 0.7,
      searchMode: 'text_only' as const,
      includeText: true,
      includeImages: false,
      ...options,
    };

    try {
      logWithContext.debug('SemanticSearchService: Executing text search', {
        query,
        limit: opts.limit,
        threshold: opts.threshold,
        searchMode: opts.searchMode,
      });

      // Generate query embedding
      const queryEmbedding = await aiService.embedText(query);

      // Search text collection
      const searchResults = await vectorDbService.searchText(queryEmbedding, {
        limit: opts.limit,
        threshold: opts.threshold,
        filter: opts.filter,
        with_payload: true,
        with_vector: false,
      });

      // Convert to our result format
      const results = this.convertSearchResults(searchResults, 'text');

      const duration = Date.now() - startTime;
      this.updateQueryStats(duration);

      logWithContext.debug('SemanticSearchService: Text search completed', {
        query,
        resultCount: results.length,
        duration: `${duration}ms`,
      });

      return results;

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('SemanticSearchService: Text search failed', error as Error, {
        query,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Execute semantic image search
   */
  public async searchImages(
    query: string,
    options: SemanticSearchOptions = {}
  ): Promise<SemanticSearchResult[]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const startTime = Date.now();
    const opts = {
      limit: 10,
      threshold: 0.7,
      searchMode: 'image_only' as const,
      includeText: false,
      includeImages: true,
      ...options,
    };

    try {
      logWithContext.debug('SemanticSearchService: Executing image search', {
        query,
        limit: opts.limit,
        threshold: opts.threshold,
        searchMode: opts.searchMode,
      });

      // Generate query embedding for cross-modal search (text query -> find images)
      const queryEmbedding = await aiService.embedText(query);

      // Search image collection with text query
      const searchResults = await vectorDbService.searchImages(queryEmbedding, {
        limit: opts.limit,
        threshold: opts.threshold,
        filter: opts.filter,
        with_payload: true,
        with_vector: false,
      });

      // Convert to our result format
      const results = this.convertSearchResults(searchResults, 'image');

      const duration = Date.now() - startTime;
      this.updateQueryStats(duration);

      logWithContext.debug('SemanticSearchService: Image search completed', {
        query,
        resultCount: results.length,
        duration: `${duration}ms`,
      });

      return results;

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('SemanticSearchService: Image search failed', error as Error, {
        query,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Execute multimodal search (both text and images)
   */
  public async searchMultimodal(
    query: string,
    options: SemanticSearchOptions = {}
  ): Promise<SemanticSearchResult[]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const startTime = Date.now();
    const opts = {
      limit: 15,
      threshold: 0.7,
      searchMode: 'multimodal' as const,
      includeText: true,
      includeImages: true,
      boostTextResults: false,
      boostImageResults: false,
      ...options,
    };

    try {
      logWithContext.debug('SemanticSearchService: Executing multimodal search', {
        query,
        limit: opts.limit,
        threshold: opts.threshold,
        includeText: opts.includeText,
        includeImages: opts.includeImages,
      });

      // Generate query embedding
      const queryEmbedding = await aiService.embedText(query);

      // Search both collections in parallel
      const [textResults, imageResults] = await Promise.all([
        opts.includeText 
          ? vectorDbService.searchText(queryEmbedding, {
              limit: Math.ceil(opts.limit / 2),
              threshold: opts.threshold,
              filter: opts.filter,
              with_payload: true,
              with_vector: false,
            })
          : Promise.resolve([]),
        opts.includeImages
          ? vectorDbService.searchImages(queryEmbedding, {
              limit: Math.ceil(opts.limit / 2),
              threshold: opts.threshold,
              filter: opts.filter,
              with_payload: true,
              with_vector: false,
            })
          : Promise.resolve([]),
      ]);

      // Convert and combine results
      const textSemanticResults = this.convertSearchResults(textResults, 'text');
      const imageSemanticResults = this.convertSearchResults(imageResults, 'image');

      // Apply result boosting if specified
      if (opts.boostTextResults) {
        textSemanticResults.forEach(result => result.score *= 1.2);
      }
      if (opts.boostImageResults) {
        imageSemanticResults.forEach(result => result.score *= 1.2);
      }

      // Combine and sort by score
      const allResults = [...textSemanticResults, ...imageSemanticResults]
        .sort((a, b) => b.score - a.score)
        .slice(0, opts.limit);

      const duration = Date.now() - startTime;
      this.updateQueryStats(duration);

      logWithContext.debug('SemanticSearchService: Multimodal search completed', {
        query,
        textResultCount: textSemanticResults.length,
        imageResultCount: imageSemanticResults.length,
        totalResultCount: allResults.length,
        duration: `${duration}ms`,
      });

      return allResults;

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('SemanticSearchService: Multimodal search failed', error as Error, {
        query,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Search with image input (upload an image, find similar images or related text)
   */
  public async searchWithImage(
    imageBuffer: Buffer,
    options: SemanticSearchOptions = {}
  ): Promise<SemanticSearchResult[]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const startTime = Date.now();
    const opts = {
      limit: 10,
      threshold: 0.7,
      searchMode: 'multimodal' as const,
      includeText: true,
      includeImages: true,
      ...options,
    };

    try {
      logWithContext.debug('SemanticSearchService: Executing image-to-content search', {
        imageSize: imageBuffer.length,
        limit: opts.limit,
        threshold: opts.threshold,
        includeText: opts.includeText,
        includeImages: opts.includeImages,
      });

      // Generate image embedding
      const queryEmbedding = await aiService.embedImage(imageBuffer);

      // Search both collections using image embedding
      const [textResults, imageResults] = await Promise.all([
        opts.includeText
          ? vectorDbService.searchText(queryEmbedding, {
              limit: Math.ceil(opts.limit / 2),
              threshold: opts.threshold,
              filter: opts.filter,
              with_payload: true,
              with_vector: false,
            })
          : Promise.resolve([]),
        opts.includeImages
          ? vectorDbService.searchImages(queryEmbedding, {
              limit: Math.ceil(opts.limit / 2),
              threshold: opts.threshold,
              filter: opts.filter,
              with_payload: true,
              with_vector: false,
            })
          : Promise.resolve([]),
      ]);

      // Convert and combine results
      const allResults = [
        ...this.convertSearchResults(textResults, 'text'),
        ...this.convertSearchResults(imageResults, 'image'),
      ]
        .sort((a, b) => b.score - a.score)
        .slice(0, opts.limit);

      const duration = Date.now() - startTime;
      this.updateQueryStats(duration);

      logWithContext.debug('SemanticSearchService: Image-to-content search completed', {
        imageSize: imageBuffer.length,
        resultCount: allResults.length,
        duration: `${duration}ms`,
      });

      return allResults;

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('SemanticSearchService: Image-to-content search failed', error as Error, {
        imageSize: imageBuffer.length,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Convert Qdrant search results to our format
   */
  private convertSearchResults(
    searchResults: SearchResult[],
    expectedContentType: 'text' | 'image'
  ): SemanticSearchResult[] {
    return searchResults.map(result => ({
      id: result.id,
      score: result.score,
      documentId: result.payload.document_id,
      filePath: result.payload.file_path,
      contentType: result.payload.content_type as 'text' | 'image',
      textContent: result.payload.text_content,
      imageCaption: result.payload.image_caption,
      pageNumber: result.payload.page_number,
      chunkIndex: result.payload.chunk_index,
      documentTitle: result.payload.document_title,
      createdAt: result.payload.created_at,
    }));
  }

  /**
   * Update query statistics
   */
  private updateQueryStats(duration: number): void {
    this.stats.totalQueries += 1;
    this.stats.averageResponseTime = 
      (this.stats.averageResponseTime * (this.stats.totalQueries - 1) + duration) / this.stats.totalQueries;
    this.stats.lastQuery = new Date();
  }

  /**
   * Update collection size statistics
   */
  private async updateCollectionStats(): Promise<void> {
    try {
      const collectionStats = await vectorDbService.getCollectionStats();
      
      const textStats = collectionStats.find(stat => stat.name.includes('text_chunks'));
      const imageStats = collectionStats.find(stat => stat.name.includes('image_embeddings'));

      this.stats.textCollectionSize = textStats?.points_count || 0;
      this.stats.imageCollectionSize = imageStats?.points_count || 0;

    } catch (error) {
      logWithContext.warn('SemanticSearchService: Failed to update collection stats', error as Error);
    }
  }

  /**
   * Get search statistics
   */
  public async getStats(): Promise<SearchStats> {
    await this.updateCollectionStats();
    return { ...this.stats };
  }

  /**
   * Check if service is ready
   */
  public isReady(): boolean {
    return this.isInitialized && aiService.isReady() && vectorDbService.isReady();
  }

  /**
   * Get service status
   */
  public getStatus(): {
    initialized: boolean;
    aiServiceReady: boolean;
    vectorDbServiceReady: boolean;
    ready: boolean;
    totalQueries: number;
  } {
    return {
      initialized: this.isInitialized,
      aiServiceReady: aiService.isReady(),
      vectorDbServiceReady: vectorDbService.isReady(),
      ready: this.isReady(),
      totalQueries: this.stats.totalQueries,
    };
  }
}

// Export singleton instance
export const semanticSearchService = SemanticSearchService.getInstance();