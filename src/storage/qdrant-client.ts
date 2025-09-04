#!/usr/bin/env node
/**
 * Qdrant Vector Database Client for MCP Research File Server
 * Handles multimodal embeddings storage and retrieval
 */

import { QdrantClient } from '@qdrant/js-client-rest';
import type { 
  CreateCollection, 
  SearchResult, 
  PointStruct,
  Filter
} from '@qdrant/js-client-rest';

export interface EmbeddingMetadata {
  document_id: string;
  file_path: string;
  content_type: 'text' | 'image';
  chunk_index?: number;
  text_content?: string;
  image_caption?: string;
  source: 'mclip' | 'docling';
  created_at: string;
}

export interface SearchOptions {
  limit?: number;
  score_threshold?: number;
  filter?: Filter;
  with_payload?: boolean;
  with_vector?: boolean;
}

export class QdrantVectorStore {
  private client: QdrantClient;
  private readonly COLLECTION_TEXT = 'mcp_text_embeddings';
  private readonly COLLECTION_IMAGE = 'mcp_image_embeddings';
  private readonly COLLECTION_MULTIMODAL = 'mcp_multimodal_embeddings';
  
  constructor(url: string = 'http://localhost:6333') {
    this.client = new QdrantClient({ url });
  }

  /**
   * Initialize collections for multimodal embeddings
   */
  async initializeCollections(): Promise<void> {
    try {
      // Text embeddings collection (M-CLIP: 384 dimensions)
      await this.createCollectionIfNotExists(this.COLLECTION_TEXT, {
        vectors: {
          size: 384,
          distance: 'Cosine'
        }
      });

      // Image embeddings collection (M-CLIP: 384 dimensions) 
      await this.createCollectionIfNotExists(this.COLLECTION_IMAGE, {
        vectors: {
          size: 384,
          distance: 'Cosine'
        }
      });

      // Multimodal embeddings (cross-modal search)
      await this.createCollectionIfNotExists(this.COLLECTION_MULTIMODAL, {
        vectors: {
          size: 384,
          distance: 'Cosine'
        }
      });

      console.log('✅ Qdrant collections initialized successfully');
    } catch (error) {
      console.error('❌ Failed to initialize Qdrant collections:', error);
      throw error;
    }
  }

  private async createCollectionIfNotExists(
    name: string, 
    config: CreateCollection
  ): Promise<void> {
    try {
      const collections = await this.client.getCollections();
      const exists = collections.collections.some(c => c.name === name);
      
      if (!exists) {
        await this.client.createCollection(name, config);
        console.log(`📦 Created Qdrant collection: ${name}`);
      } else {
        console.log(`📦 Collection already exists: ${name}`);
      }
    } catch (error) {
      console.error(`Failed to create collection ${name}:`, error);
      throw error;
    }
  }

  /**
   * Store text embedding in Qdrant
   */
  async storeTextEmbedding(
    id: string,
    embedding: number[],
    metadata: EmbeddingMetadata
  ): Promise<void> {
    const point: PointStruct = {
      id,
      vector: embedding,
      payload: metadata
    };

    await this.client.upsert(this.COLLECTION_TEXT, {
      wait: true,
      points: [point]
    });
  }

  /**
   * Store image embedding in Qdrant
   */
  async storeImageEmbedding(
    id: string,
    embedding: number[],
    metadata: EmbeddingMetadata
  ): Promise<void> {
    const point: PointStruct = {
      id,
      vector: embedding,
      payload: metadata
    };

    await this.client.upsert(this.COLLECTION_IMAGE, {
      wait: true,
      points: [point]
    });
  }

  /**
   * Store multimodal embedding (for cross-modal search)
   */
  async storeMultimodalEmbedding(
    id: string,
    embedding: number[],
    metadata: EmbeddingMetadata
  ): Promise<void> {
    const point: PointStruct = {
      id,
      vector: embedding,
      payload: metadata
    };

    await this.client.upsert(this.COLLECTION_MULTIMODAL, {
      wait: true,
      points: [point]
    });
  }

  /**
   * Search for similar text embeddings
   */
  async searchTextEmbeddings(
    queryVector: number[],
    options: SearchOptions = {}
  ): Promise<SearchResult[]> {
    const response = await this.client.search(this.COLLECTION_TEXT, {
      vector: queryVector,
      limit: options.limit || 10,
      score_threshold: options.score_threshold || 0.7,
      filter: options.filter,
      with_payload: options.with_payload ?? true,
      with_vector: options.with_vector ?? false
    });

    return response;
  }

  /**
   * Search for similar image embeddings
   */
  async searchImageEmbeddings(
    queryVector: number[],
    options: SearchOptions = {}
  ): Promise<SearchResult[]> {
    const response = await this.client.search(this.COLLECTION_IMAGE, {
      vector: queryVector,
      limit: options.limit || 10,
      score_threshold: options.score_threshold || 0.7,
      filter: options.filter,
      with_payload: options.with_payload ?? true,
      with_vector: options.with_vector ?? false
    });

    return response;
  }

  /**
   * Cross-modal search across both text and images
   */
  async searchMultimodal(
    queryVector: number[],
    options: SearchOptions = {}
  ): Promise<SearchResult[]> {
    const response = await this.client.search(this.COLLECTION_MULTIMODAL, {
      vector: queryVector,
      limit: options.limit || 10,
      score_threshold: options.score_threshold || 0.6,
      filter: options.filter,
      with_payload: options.with_payload ?? true,
      with_vector: options.with_vector ?? false
    });

    return response;
  }

  /**
   * Get collection info and statistics
   */
  async getCollectionInfo(): Promise<any> {
    const collections = await this.client.getCollections();
    const info = {};
    
    for (const collection of collections.collections) {
      const collInfo = await this.client.getCollection(collection.name);
      info[collection.name] = collInfo;
    }
    
    return info;
  }

  /**
   * Health check for Qdrant connection
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.client.getCollections();
      return true;
    } catch (error) {
      console.error('Qdrant health check failed:', error);
      return false;
    }
  }

  /**
   * Clear all data (for testing)
   */
  async clearAll(): Promise<void> {
    const collections = [
      this.COLLECTION_TEXT,
      this.COLLECTION_IMAGE, 
      this.COLLECTION_MULTIMODAL
    ];

    for (const collection of collections) {
      try {
        await this.client.deleteCollection(collection);
        console.log(`🗑️ Cleared collection: ${collection}`);
      } catch (error) {
        console.warn(`Collection ${collection} may not exist:`, error);
      }
    }
  }
}

export default QdrantVectorStore;