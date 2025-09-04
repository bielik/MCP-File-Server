#!/usr/bin/env node
/**
 * Semantic Search Service for MCP Research File Server
 * Combines M-CLIP embeddings with Qdrant vector search
 */

import { MCLIPClient } from '../embeddings/mclip-client.js';
import { QdrantVectorStore, type EmbeddingMetadata, type SearchOptions } from '../storage/qdrant-client.js';
import type { SearchResult } from '@qdrant/js-client-rest';
import { performance } from 'perf_hooks';
import { v4 as uuidv4 } from 'uuid';
import * as path from 'path';

export interface SemanticSearchResult {
  id: string;
  score: number;
  document_id: string;
  file_path: string;
  content_type: 'text' | 'image';
  text_content?: string;
  image_caption?: string;
  chunk_index?: number;
  metadata: EmbeddingMetadata;
}

export interface SemanticSearchResponse {
  query: string;
  results: SemanticSearchResult[];
  total_results: number;
  search_time_ms: number;
  embedding_time_ms: number;
  search_type: 'semantic_text' | 'semantic_image' | 'cross_modal';
}

export interface IndexDocumentOptions {
  document_id?: string;
  chunk_size?: number;
  overlap?: number;
  extract_images?: boolean;
  force_reindex?: boolean;
}

export class SemanticSearchService {
  private mclipClient: MCLIPClient;
  private vectorStore: QdrantVectorStore;
  private isInitialized: boolean = false;

  constructor(mclipUrl?: string, qdrantUrl?: string) {
    this.mclipClient = new MCLIPClient({ 
      serviceUrl: mclipUrl || 'http://localhost:8002' 
    });
    this.vectorStore = new QdrantVectorStore(qdrantUrl || 'http://localhost:6333');
  }

  /**
   * Initialize the search service
   */
  async initialize(): Promise<void> {
    console.log('🔍 Initializing Semantic Search Service...');
    
    try {
      // Test M-CLIP connectivity
      const mclipHealth = await this.mclipClient.health();
      if (mclipHealth.status !== 'healthy') {
        throw new Error(`M-CLIP service is not healthy: ${mclipHealth.status}`);
      }
      
      console.log(`✅ M-CLIP connected: ${mclipHealth.device}, model loaded: ${mclipHealth.model_loaded}`);

      // Test Qdrant connectivity
      const qdrantHealthy = await this.vectorStore.healthCheck();
      if (!qdrantHealthy) {
        throw new Error('Qdrant is not accessible');
      }
      
      console.log('✅ Qdrant connected and ready');

      // Initialize collections if not exists
      await this.vectorStore.initializeCollections();
      
      this.isInitialized = true;
      console.log('🎉 Semantic Search Service initialized successfully!');
      
    } catch (error) {
      console.error('❌ Failed to initialize Semantic Search Service:', error);
      throw error;
    }
  }

  /**
   * Check if service is ready
   */
  isReady(): boolean {
    return this.isInitialized;
  }

  /**
   * Index a text document or text chunk
   */
  async indexText(
    text: string, 
    filePath: string, 
    options: IndexDocumentOptions = {}
  ): Promise<void> {
    if (!this.isInitialized) {
      throw new Error('Service not initialized. Call initialize() first.');
    }

    if (!text || text.trim().length === 0) {
      throw new Error('Text content cannot be empty');
    }

    try {
      // Generate embedding using M-CLIP
      const embeddingResponse = await this.mclipClient.embedText(text);
      
      // Create metadata
      const metadata: EmbeddingMetadata = {
        document_id: options.document_id || uuidv4(),
        file_path: filePath,
        content_type: 'text',
        chunk_index: options.chunk_size ? 0 : undefined,
        text_content: text.substring(0, 1000), // Store first 1000 chars
        source: 'mclip',
        created_at: new Date().toISOString()
      };

      // Store in Qdrant
      const pointId = uuidv4();
      await this.vectorStore.storeTextEmbedding(pointId, embeddingResponse.embedding, metadata);
      
      console.log(`📝 Indexed text: ${filePath} (${embeddingResponse.embedding.length}d embedding)`);
      
    } catch (error) {
      console.error(`Failed to index text from ${filePath}:`, error);
      throw error;
    }
  }

  /**
   * Index an image file
   */
  async indexImage(
    imagePath: string, 
    options: IndexDocumentOptions = {}
  ): Promise<void> {
    if (!this.isInitialized) {
      throw new Error('Service not initialized. Call initialize() first.');
    }

    try {
      // Generate image embedding using M-CLIP
      const embeddingResponse = await this.mclipClient.embedImagePath(imagePath);
      
      // Create metadata
      const metadata: EmbeddingMetadata = {
        document_id: options.document_id || uuidv4(),
        file_path: imagePath,
        content_type: 'image',
        image_caption: undefined, // Could be enhanced with caption extraction
        source: 'mclip',
        created_at: new Date().toISOString()
      };

      // Store in Qdrant (both image collection and multimodal for cross-search)
      const pointId = uuidv4();
      await this.vectorStore.storeImageEmbedding(pointId, embeddingResponse.embedding, metadata);
      await this.vectorStore.storeMultimodalEmbedding(pointId, embeddingResponse.embedding, metadata);
      
      console.log(`🖼️ Indexed image: ${imagePath} (${embeddingResponse.embedding.length}d embedding)`);
      
    } catch (error) {
      console.error(`Failed to index image ${imagePath}:`, error);
      throw error;
    }
  }

  /**
   * Search for semantically similar text content
   */
  async searchText(
    query: string, 
    options: SearchOptions = {}
  ): Promise<SemanticSearchResponse> {
    if (!this.isInitialized) {
      throw new Error('Service not initialized. Call initialize() first.');
    }

    const startTime = performance.now();
    
    try {
      // Generate query embedding
      const embeddingStart = performance.now();
      const queryEmbedding = await this.mclipClient.embedText(query);
      const embeddingTime = performance.now() - embeddingStart;

      // Search in Qdrant
      const searchStart = performance.now();
      const qdrantResults = await this.vectorStore.searchTextEmbeddings(
        queryEmbedding.embedding,
        {
          limit: options.limit || 10,
          score_threshold: options.score_threshold || 0.7,
          filter: options.filter,
          with_payload: true
        }
      );
      const searchTime = performance.now() - searchStart;

      // Convert results
      const results: SemanticSearchResult[] = qdrantResults.map(result => ({
        id: result.id.toString(),
        score: result.score || 0,
        document_id: result.payload?.document_id || 'unknown',
        file_path: result.payload?.file_path || 'unknown',
        content_type: result.payload?.content_type || 'text',
        text_content: result.payload?.text_content,
        chunk_index: result.payload?.chunk_index,
        metadata: result.payload as EmbeddingMetadata
      }));

      return {
        query,
        results,
        total_results: results.length,
        search_time_ms: searchTime,
        embedding_time_ms: embeddingTime,
        search_type: 'semantic_text'
      };

    } catch (error) {
      console.error(`Semantic text search failed for query: "${query}"`, error);
      throw error;
    }
  }

  /**
   * Search for semantically similar images
   */
  async searchImages(
    query: string, 
    options: SearchOptions = {}
  ): Promise<SemanticSearchResponse> {
    if (!this.isInitialized) {
      throw new Error('Service not initialized. Call initialize() first.');
    }

    const startTime = performance.now();
    
    try {
      // Generate query embedding from text
      const embeddingStart = performance.now();
      const queryEmbedding = await this.mclipClient.embedText(query);
      const embeddingTime = performance.now() - embeddingStart;

      // Search in image embeddings (cross-modal)
      const searchStart = performance.now();
      const qdrantResults = await this.vectorStore.searchImageEmbeddings(
        queryEmbedding.embedding,
        {
          limit: options.limit || 10,
          score_threshold: options.score_threshold || 0.6, // Lower threshold for cross-modal
          filter: options.filter,
          with_payload: true
        }
      );
      const searchTime = performance.now() - searchStart;

      // Convert results
      const results: SemanticSearchResult[] = qdrantResults.map(result => ({
        id: result.id.toString(),
        score: result.score || 0,
        document_id: result.payload?.document_id || 'unknown',
        file_path: result.payload?.file_path || 'unknown',
        content_type: result.payload?.content_type || 'image',
        image_caption: result.payload?.image_caption,
        metadata: result.payload as EmbeddingMetadata
      }));

      return {
        query,
        results,
        total_results: results.length,
        search_time_ms: searchTime,
        embedding_time_ms: embeddingTime,
        search_type: 'semantic_image'
      };

    } catch (error) {
      console.error(`Semantic image search failed for query: "${query}"`, error);
      throw error;
    }
  }

  /**
   * Cross-modal search (text query finds both text and images)
   */
  async searchMultimodal(
    query: string, 
    options: SearchOptions = {}
  ): Promise<SemanticSearchResponse> {
    if (!this.isInitialized) {
      throw new Error('Service not initialized. Call initialize() first.');
    }

    const startTime = performance.now();
    
    try {
      // Generate query embedding
      const embeddingStart = performance.now();
      const queryEmbedding = await this.mclipClient.embedText(query);
      const embeddingTime = performance.now() - embeddingStart;

      // Search in multimodal collection
      const searchStart = performance.now();
      const qdrantResults = await this.vectorStore.searchMultimodal(
        queryEmbedding.embedding,
        {
          limit: options.limit || 15, // Get more results for diverse content
          score_threshold: options.score_threshold || 0.6,
          filter: options.filter,
          with_payload: true
        }
      );
      const searchTime = performance.now() - searchStart;

      // Convert results
      const results: SemanticSearchResult[] = qdrantResults.map(result => ({
        id: result.id.toString(),
        score: result.score || 0,
        document_id: result.payload?.document_id || 'unknown',
        file_path: result.payload?.file_path || 'unknown',
        content_type: result.payload?.content_type || 'text',
        text_content: result.payload?.text_content,
        image_caption: result.payload?.image_caption,
        chunk_index: result.payload?.chunk_index,
        metadata: result.payload as EmbeddingMetadata
      }));

      // Sort by relevance and content type diversity
      results.sort((a, b) => b.score - a.score);

      return {
        query,
        results,
        total_results: results.length,
        search_time_ms: searchTime,
        embedding_time_ms: embeddingTime,
        search_type: 'cross_modal'
      };

    } catch (error) {
      console.error(`Cross-modal search failed for query: "${query}"`, error);
      throw error;
    }
  }

  /**
   * Get collection statistics
   */
  async getStats(): Promise<any> {
    if (!this.isInitialized) {
      throw new Error('Service not initialized. Call initialize() first.');
    }

    try {
      const [qdrantInfo, mclipStats] = await Promise.all([
        this.vectorStore.getCollectionInfo(),
        this.mclipClient.getStats()
      ]);

      return {
        qdrant: qdrantInfo,
        mclip: mclipStats,
        service_status: 'healthy'
      };
    } catch (error) {
      console.error('Failed to get stats:', error);
      return {
        error: error.message,
        service_status: 'error'
      };
    }
  }

  /**
   * Health check for the entire service
   */
  async healthCheck(): Promise<{
    status: 'healthy' | 'degraded' | 'error';
    services: {
      mclip: boolean;
      qdrant: boolean;
    };
    details: any;
  }> {
    try {
      const [mclipHealth, qdrantHealth] = await Promise.all([
        this.mclipClient.health().catch(() => null),
        this.vectorStore.healthCheck().catch(() => false)
      ]);

      const mclipOk = mclipHealth?.status === 'healthy';
      const qdrantOk = qdrantHealth;

      let status: 'healthy' | 'degraded' | 'error' = 'healthy';
      if (!mclipOk && !qdrantOk) {
        status = 'error';
      } else if (!mclipOk || !qdrantOk) {
        status = 'degraded';
      }

      return {
        status,
        services: {
          mclip: mclipOk,
          qdrant: qdrantOk
        },
        details: {
          mclip: mclipHealth,
          qdrant: qdrantHealth
        }
      };
    } catch (error) {
      return {
        status: 'error',
        services: {
          mclip: false,
          qdrant: false
        },
        details: {
          error: error.message
        }
      };
    }
  }
}

export default SemanticSearchService;