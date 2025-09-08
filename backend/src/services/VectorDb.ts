import { QdrantClient } from '@qdrant/js-client-rest';
import { config } from '../../config/index.js';
import { logWithContext } from '../../utils/logger.js';
import type { 
  CollectionInfo, 
  PointStruct, 
  ScoredPoint,
  CreateCollection,
  Distance,
  VectorParams
} from '@qdrant/js-client-rest';

/**
 * Vector Database Service for Qdrant Operations
 * 
 * This service provides a TypeScript wrapper for Qdrant operations, replacing
 * the previous Python-based collection management. It handles automatic
 * collection creation, vector storage, and similarity search operations.
 * 
 * Enhanced Features:
 * - Automatic collection creation with correct specifications
 * - Programmatic setup of text and image collections
 * - Vector similarity search with configurable parameters
 * - Structured logging for monitoring and debugging
 * - Connection health checking and retry logic
 * 
 * Collections:
 * - mcp_text_chunks: For text chunk embeddings
 * - mcp_image_embeddings: For image embeddings
 */

export interface VectorDocument {
  id: string;
  vector: number[];
  payload: {
    file_path: string;
    content_type: 'text' | 'image';
    text_content?: string;
    image_caption?: string;
    page_number?: number;
    chunk_index?: number;
    created_at: string;
    file_size?: number;
    document_title?: string;
    [key: string]: any;
  };
}

export interface SearchResult {
  id: string;
  score: number;
  payload: VectorDocument['payload'];
}

export interface SearchOptions {
  limit?: number;
  threshold?: number;
  filter?: Record<string, any>;
  with_payload?: boolean;
  with_vector?: boolean;
}

export interface CollectionStats {
  name: string;
  vectors_count: number;
  indexed_vectors_count: number;
  points_count: number;
  segments_count: number;
  disk_data_size: number;
  ram_data_size: number;
}

/**
 * Vector Database Service Class
 */
export class VectorDbService {
  private static instance: VectorDbService | null = null;
  private client: QdrantClient | null = null;
  private isInitialized = false;
  private initializationPromise: Promise<void> | null = null;

  // Collection configuration
  private readonly collections = {
    textChunks: `${config.qdrant.collectionPrefix}_text_chunks`,
    imageEmbeddings: `${config.qdrant.collectionPrefix}_image_embeddings`,
  };

  private constructor() {
    logWithContext.info('VectorDbService: Creating vector database service instance');
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): VectorDbService {
    if (!VectorDbService.instance) {
      VectorDbService.instance = new VectorDbService();
    }
    return VectorDbService.instance;
  }

  /**
   * Initialize the vector database service
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    if (this.initializationPromise) {
      return this.initializationPromise;
    }

    this.initializationPromise = this._initialize();
    return this.initializationPromise;
  }

  private async _initialize(): Promise<void> {
    const startTime = Date.now();

    try {
      logWithContext.info('VectorDbService: Starting initialization', {
        qdrantUrl: config.qdrant.url,
        collectionPrefix: config.qdrant.collectionPrefix,
        embeddingDimension: config.qdrant.embeddingDimension,
      });

      // Create Qdrant client
      this.client = new QdrantClient({
        url: config.qdrant.url,
        apiKey: config.qdrant.apiKey,
      });

      // Test connection
      logWithContext.debug('VectorDbService: Testing connection to Qdrant');
      await this.client.getCollections();

      // Create collections if they don't exist
      await this.ensureCollectionsExist();

      this.isInitialized = true;
      const duration = Date.now() - startTime;

      logWithContext.info('VectorDbService: Initialization completed', {
        duration: `${duration}ms`,
        textCollection: this.collections.textChunks,
        imageCollection: this.collections.imageEmbeddings,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('VectorDbService: Initialization failed', error as Error, {
        duration: `${duration}ms`,
        qdrantUrl: config.qdrant.url,
      });

      this.isInitialized = false;
      this.initializationPromise = null;
      this.client = null;

      throw new Error(`Failed to initialize VectorDbService: ${(error as Error).message}`);
    }
  }

  /**
   * Ensure required collections exist, create them if they don't
   */
  private async ensureCollectionsExist(): Promise<void> {
    if (!this.client) {
      throw new Error('Qdrant client not initialized');
    }

    const startTime = Date.now();

    try {
      logWithContext.debug('VectorDbService: Checking existing collections');

      // Get list of existing collections
      const { collections } = await this.client.getCollections();
      const existingCollectionNames = collections.map(c => c.name);

      // Check and create text chunks collection
      if (!existingCollectionNames.includes(this.collections.textChunks)) {
        logWithContext.info('VectorDbService: Creating text chunks collection', {
          collectionName: this.collections.textChunks,
        });

        await this.createCollection(this.collections.textChunks, {
          vectors: {
            size: config.qdrant.embeddingDimension,
            distance: 'Cosine' as Distance,
          }
        });
      } else {
        logWithContext.debug('VectorDbService: Text chunks collection already exists', {
          collectionName: this.collections.textChunks,
        });
      }

      // Check and create image embeddings collection
      if (!existingCollectionNames.includes(this.collections.imageEmbeddings)) {
        logWithContext.info('VectorDbService: Creating image embeddings collection', {
          collectionName: this.collections.imageEmbeddings,
        });

        await this.createCollection(this.collections.imageEmbeddings, {
          vectors: {
            size: config.qdrant.embeddingDimension,
            distance: 'Cosine' as Distance,
          }
        });
      } else {
        logWithContext.debug('VectorDbService: Image embeddings collection already exists', {
          collectionName: this.collections.imageEmbeddings,
        });
      }

      const duration = Date.now() - startTime;
      logWithContext.info('VectorDbService: Collection setup completed', {
        duration: `${duration}ms`,
        textCollection: this.collections.textChunks,
        imageCollection: this.collections.imageEmbeddings,
      });

    } catch (error) {
      logWithContext.error('VectorDbService: Failed to ensure collections exist', error as Error);
      throw error;
    }
  }

  /**
   * Create a new collection with specified configuration
   */
  private async createCollection(
    collectionName: string, 
    config: CreateCollection
  ): Promise<void> {
    if (!this.client) {
      throw new Error('Qdrant client not initialized');
    }

    const startTime = Date.now();

    try {
      await this.client.createCollection(collectionName, config);
      
      const duration = Date.now() - startTime;
      logWithContext.info('VectorDbService: Collection created successfully', {
        collectionName,
        duration: `${duration}ms`,
        vectorSize: config.vectors?.size,
        distance: config.vectors?.distance,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('VectorDbService: Failed to create collection', error as Error, {
        collectionName,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Store text chunk embeddings
   */
  public async storeTextEmbeddings(documents: VectorDocument[]): Promise<void> {
    await this.storeEmbeddings(this.collections.textChunks, documents, 'text');
  }

  /**
   * Store image embeddings
   */
  public async storeImageEmbeddings(documents: VectorDocument[]): Promise<void> {
    await this.storeEmbeddings(this.collections.imageEmbeddings, documents, 'image');
  }

  /**
   * Store embeddings in specified collection
   */
  private async storeEmbeddings(
    collectionName: string,
    documents: VectorDocument[],
    contentType: 'text' | 'image'
  ): Promise<void> {
    if (!this.isInitialized || !this.client) {
      await this.initialize();
    }

    if (!this.client) {
      throw new Error('Qdrant client not initialized');
    }

    const startTime = Date.now();

    try {
      logWithContext.debug('VectorDbService: Storing embeddings', {
        collectionName,
        documentCount: documents.length,
        contentType,
      });

      // Convert to Qdrant point format
      const points: PointStruct[] = documents.map(doc => ({
        id: doc.id,
        vector: doc.vector,
        payload: doc.payload,
      }));

      // Validate embedding dimensions
      for (const point of points) {
        if (point.vector.length !== config.qdrant.embeddingDimension) {
          logWithContext.warn('VectorDbService: Embedding dimension mismatch', {
            pointId: point.id,
            expected: config.qdrant.embeddingDimension,
            actual: point.vector.length,
          });
        }
      }

      // Store points in batches
      const batchSize = 100;
      for (let i = 0; i < points.length; i += batchSize) {
        const batch = points.slice(i, i + batchSize);
        await this.client.upsert(collectionName, {
          wait: true,
          points: batch,
        });

        logWithContext.debug('VectorDbService: Batch stored', {
          batchNumber: Math.floor(i / batchSize) + 1,
          batchSize: batch.length,
        });
      }

      const duration = Date.now() - startTime;
      logWithContext.info('VectorDbService: Embeddings stored successfully', {
        collectionName,
        documentCount: documents.length,
        contentType,
        duration: `${duration}ms`,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('VectorDbService: Failed to store embeddings', error as Error, {
        collectionName,
        documentCount: documents.length,
        contentType,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Search for similar vectors in text collection
   */
  public async searchText(
    queryVector: number[],
    options: SearchOptions = {}
  ): Promise<SearchResult[]> {
    return this.searchVectors(this.collections.textChunks, queryVector, options);
  }

  /**
   * Search for similar vectors in image collection
   */
  public async searchImages(
    queryVector: number[],
    options: SearchOptions = {}
  ): Promise<SearchResult[]> {
    return this.searchVectors(this.collections.imageEmbeddings, queryVector, options);
  }

  /**
   * Search for similar vectors across both collections (multimodal search)
   */
  public async searchMultimodal(
    queryVector: number[],
    options: SearchOptions = {}
  ): Promise<{ text: SearchResult[]; images: SearchResult[] }> {
    const [textResults, imageResults] = await Promise.all([
      this.searchText(queryVector, options),
      this.searchImages(queryVector, options),
    ]);

    return {
      text: textResults,
      images: imageResults,
    };
  }

  /**
   * Search for similar vectors in specified collection
   */
  private async searchVectors(
    collectionName: string,
    queryVector: number[],
    options: SearchOptions = {}
  ): Promise<SearchResult[]> {
    if (!this.isInitialized || !this.client) {
      await this.initialize();
    }

    if (!this.client) {
      throw new Error('Qdrant client not initialized');
    }

    const startTime = Date.now();
    const opts = {
      limit: 10,
      threshold: 0.7,
      with_payload: true,
      with_vector: false,
      ...options,
    };

    try {
      logWithContext.debug('VectorDbService: Searching vectors', {
        collectionName,
        vectorDimension: queryVector.length,
        limit: opts.limit,
        threshold: opts.threshold,
      });

      const searchResult = await this.client.search(collectionName, {
        vector: queryVector,
        limit: opts.limit,
        score_threshold: opts.threshold,
        filter: opts.filter,
        with_payload: opts.with_payload,
        with_vector: opts.with_vector,
      });

      const results: SearchResult[] = searchResult.map((point: ScoredPoint) => ({
        id: point.id.toString(),
        score: point.score,
        payload: point.payload as VectorDocument['payload'],
      }));

      const duration = Date.now() - startTime;
      logWithContext.debug('VectorDbService: Vector search completed', {
        collectionName,
        resultCount: results.length,
        duration: `${duration}ms`,
      });

      return results;

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('VectorDbService: Vector search failed', error as Error, {
        collectionName,
        vectorDimension: queryVector.length,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Get collection statistics
   */
  public async getCollectionStats(): Promise<CollectionStats[]> {
    if (!this.isInitialized || !this.client) {
      await this.initialize();
    }

    if (!this.client) {
      throw new Error('Qdrant client not initialized');
    }

    try {
      const stats: CollectionStats[] = [];

      for (const [key, collectionName] of Object.entries(this.collections)) {
        try {
          const info = await this.client.getCollection(collectionName);
          
          stats.push({
            name: collectionName,
            vectors_count: info.vectors_count || 0,
            indexed_vectors_count: info.indexed_vectors_count || 0,
            points_count: info.points_count || 0,
            segments_count: info.segments_count || 0,
            disk_data_size: info.disk_data_size || 0,
            ram_data_size: info.ram_data_size || 0,
          });
        } catch (error) {
          logWithContext.warn('VectorDbService: Failed to get stats for collection', error as Error, {
            collectionName,
          });
        }
      }

      return stats;

    } catch (error) {
      logWithContext.error('VectorDbService: Failed to get collection stats', error as Error);
      throw error;
    }
  }

  /**
   * Delete documents by filter
   */
  public async deleteDocuments(
    collectionName: string,
    filter: Record<string, any>
  ): Promise<void> {
    if (!this.isInitialized || !this.client) {
      await this.initialize();
    }

    if (!this.client) {
      throw new Error('Qdrant client not initialized');
    }

    try {
      await this.client.delete(collectionName, {
        filter,
        wait: true,
      });

      logWithContext.info('VectorDbService: Documents deleted', {
        collectionName,
        filter,
      });

    } catch (error) {
      logWithContext.error('VectorDbService: Failed to delete documents', error as Error, {
        collectionName,
        filter,
      });
      throw error;
    }
  }

  /**
   * Check if service is ready
   */
  public isReady(): boolean {
    return this.isInitialized && this.client !== null;
  }

  /**
   * Get service status
   */
  public getStatus(): {
    initialized: boolean;
    qdrantUrl: string;
    collections: typeof this.collections;
    embeddingDimension: number;
  } {
    return {
      initialized: this.isInitialized,
      qdrantUrl: config.qdrant.url,
      collections: this.collections,
      embeddingDimension: config.qdrant.embeddingDimension,
    };
  }

  /**
   * Cleanup resources
   */
  public async cleanup(): Promise<void> {
    logWithContext.info('VectorDbService: Cleaning up resources');
    
    this.client = null;
    this.isInitialized = false;
    this.initializationPromise = null;
    
    logWithContext.info('VectorDbService: Cleanup completed');
  }
}

// Export singleton instance
export const vectorDbService = VectorDbService.getInstance();