/**
 * Embedding Service Interface
 * High-level abstraction for embedding operations with fallback strategies
 */

import MCLIPClient, { EmbeddingResponse, BatchEmbeddingResponse, EmbeddingRequest } from './mclip-client';
import { EventEmitter } from 'events';
import { performance } from 'perf_hooks';

export interface EmbeddingServiceConfig {
  mclipServiceUrl: string;
  fallbackStrategies: ('openai' | 'basic' | 'cache-only')[];
  timeout: number;
  maxRetries: number;
  enableMetrics: boolean;
  metricsRetentionDays: number;
}

export interface EmbeddingMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageLatency: number;
  cacheHitRate: number;
  serviceUptime: number;
  lastError?: string;
  lastErrorTime?: Date;
}

export interface EmbeddingOptions {
  useCache?: boolean;
  timeout?: number;
  fallback?: boolean;
  quality?: 'fast' | 'balanced' | 'high';
}

export interface ProcessedEmbedding {
  embedding: number[];
  dimension: number;
  model: string;
  source: 'mclip' | 'openai' | 'basic' | 'cache';
  processingTime: number;
  quality: number; // 0-1 quality score
  cached: boolean;
  metadata?: any;
}

export class EmbeddingService extends EventEmitter {
  private mclipClient: MCLIPClient;
  private config: EmbeddingServiceConfig;
  private metrics: EmbeddingMetrics;
  private serviceStartTime: number;

  constructor(config: Partial<EmbeddingServiceConfig> = {}) {
    super();

    this.config = {
      mclipServiceUrl: 'http://localhost:8002',
      fallbackStrategies: ['openai', 'basic'],
      timeout: 30000,
      maxRetries: 3,
      enableMetrics: true,
      metricsRetentionDays: 7,
      ...config
    };

    this.mclipClient = new MCLIPClient({
      serviceUrl: this.config.mclipServiceUrl,
      timeout: this.config.timeout,
      maxRetries: this.config.maxRetries
    });

    this.metrics = this.initializeMetrics();
    this.serviceStartTime = Date.now();
  }

  private initializeMetrics(): EmbeddingMetrics {
    return {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageLatency: 0,
      cacheHitRate: 0,
      serviceUptime: 0
    };
  }

  private updateMetrics(success: boolean, latency: number, cached: boolean = false): void {
    if (!this.config.enableMetrics) return;

    this.metrics.totalRequests++;
    
    if (success) {
      this.metrics.successfulRequests++;
      
      // Update average latency
      const totalLatency = this.metrics.averageLatency * (this.metrics.successfulRequests - 1) + latency;
      this.metrics.averageLatency = totalLatency / this.metrics.successfulRequests;
    } else {
      this.metrics.failedRequests++;
    }

    // Update cache hit rate
    if (cached) {
      this.metrics.cacheHitRate = (this.metrics.cacheHitRate * (this.metrics.totalRequests - 1) + 1) / this.metrics.totalRequests;
    } else {
      this.metrics.cacheHitRate = this.metrics.cacheHitRate * (this.metrics.totalRequests - 1) / this.metrics.totalRequests;
    }

    this.metrics.serviceUptime = Date.now() - this.serviceStartTime;
    
    this.emit('metricsUpdated', this.metrics);
  }

  /**
   * Generate text embedding with fallback strategies
   */
  async embedText(text: string, options: EmbeddingOptions = {}): Promise<ProcessedEmbedding> {
    const startTime = performance.now();
    
    try {
      // Try M-CLIP service first
      const result = await this.mclipClient.embedText(text);
      const processingTime = performance.now() - startTime;
      
      this.updateMetrics(true, processingTime, result.cached);
      
      return {
        embedding: result.embedding,
        dimension: result.dimension,
        model: result.model,
        source: 'mclip',
        processingTime,
        quality: 0.95, // High quality for M-CLIP
        cached: result.cached
      };
      
    } catch (error) {
      const processingTime = performance.now() - startTime;
      this.updateMetrics(false, processingTime);
      this.metrics.lastError = error.message;
      this.metrics.lastErrorTime = new Date();
      
      this.emit('error', {
        type: 'embedding_failed',
        source: 'mclip',
        error: error.message,
        input: { text }
      });

      // Try fallback strategies
      if (options.fallback !== false && this.config.fallbackStrategies.length > 0) {
        return await this.tryFallbackStrategies(text, 'text', options);
      }

      throw error;
    }
  }

  /**
   * Generate image embedding with fallback strategies
   */
  async embedImage(imagePath: string, options: EmbeddingOptions = {}): Promise<ProcessedEmbedding> {
    const startTime = performance.now();
    
    try {
      // Try M-CLIP service first
      const result = await this.mclipClient.embedImagePath(imagePath);
      const processingTime = performance.now() - startTime;
      
      this.updateMetrics(true, processingTime, result.cached);
      
      return {
        embedding: result.embedding,
        dimension: result.dimension,
        model: result.model,
        source: 'mclip',
        processingTime,
        quality: 0.95, // High quality for M-CLIP
        cached: result.cached
      };
      
    } catch (error) {
      const processingTime = performance.now() - startTime;
      this.updateMetrics(false, processingTime);
      this.metrics.lastError = error.message;
      this.metrics.lastErrorTime = new Date();
      
      this.emit('error', {
        type: 'embedding_failed',
        source: 'mclip',
        error: error.message,
        input: { imagePath }
      });

      // Try fallback strategies
      if (options.fallback !== false && this.config.fallbackStrategies.length > 0) {
        return await this.tryFallbackStrategies(imagePath, 'image', options);
      }

      throw error;
    }
  }

  /**
   * Generate batch embeddings with automatic batching optimization
   */
  async embedBatch(
    requests: Array<{ text?: string; imagePath?: string; options?: EmbeddingOptions }>,
    globalOptions: EmbeddingOptions = {}
  ): Promise<ProcessedEmbedding[]> {
    const startTime = performance.now();
    
    // Convert to M-CLIP request format
    const mclipRequests: EmbeddingRequest[] = requests.map(req => ({
      text: req.text,
      image_path: req.imagePath
    }));

    try {
      const result = await this.mclipClient.embedBatch(mclipRequests);
      const processingTime = performance.now() - startTime;
      
      this.updateMetrics(true, processingTime);
      
      return result.embeddings.map(embedding => ({
        embedding: embedding.embedding,
        dimension: embedding.dimension,
        model: embedding.model,
        source: 'mclip' as const,
        processingTime: embedding.processing_time,
        quality: 0.95,
        cached: embedding.cached
      }));
      
    } catch (error) {
      const processingTime = performance.now() - startTime;
      this.updateMetrics(false, processingTime);
      
      this.emit('error', {
        type: 'batch_embedding_failed',
        source: 'mclip',
        error: error.message,
        input: { batchSize: requests.length }
      });

      // Fall back to individual embeddings
      if (globalOptions.fallback !== false) {
        return await this.embedBatchFallback(requests, globalOptions);
      }

      throw error;
    }
  }

  private async embedBatchFallback(
    requests: Array<{ text?: string; imagePath?: string; options?: EmbeddingOptions }>,
    globalOptions: EmbeddingOptions
  ): Promise<ProcessedEmbedding[]> {
    const results: ProcessedEmbedding[] = [];
    
    // Process individually with limited concurrency
    const concurrency = 4;
    for (let i = 0; i < requests.length; i += concurrency) {
      const batch = requests.slice(i, i + concurrency);
      const batchPromises = batch.map(async req => {
        if (req.text) {
          return await this.embedText(req.text, { ...globalOptions, ...req.options });
        } else if (req.imagePath) {
          return await this.embedImage(req.imagePath, { ...globalOptions, ...req.options });
        }
        throw new Error('Invalid request: must have either text or imagePath');
      });
      
      const batchResults = await Promise.allSettled(batchPromises);
      for (const result of batchResults) {
        if (result.status === 'fulfilled') {
          results.push(result.value);
        } else {
          // Create dummy embedding for failed items
          results.push({
            embedding: new Array(512).fill(0),
            dimension: 512,
            model: 'fallback',
            source: 'basic',
            processingTime: 0,
            quality: 0.1,
            cached: false,
            metadata: { error: result.reason.message }
          });
        }
      }
    }
    
    return results;
  }

  private async tryFallbackStrategies(
    input: string,
    type: 'text' | 'image',
    options: EmbeddingOptions
  ): Promise<ProcessedEmbedding> {
    for (const strategy of this.config.fallbackStrategies) {
      try {
        switch (strategy) {
          case 'openai':
            return await this.embedWithOpenAI(input, type);
          case 'basic':
            return await this.embedWithBasicStrategy(input, type);
          case 'cache-only':
            return await this.embedFromCacheOnly(input, type);
        }
      } catch (error) {
        this.emit('fallbackFailed', {
          strategy,
          error: error.message,
          input: { [type]: input }
        });
        continue;
      }
    }
    
    throw new Error('All fallback strategies failed');
  }

  private async embedWithOpenAI(input: string, type: 'text' | 'image'): Promise<ProcessedEmbedding> {
    // TODO: Implement OpenAI embedding fallback
    throw new Error('OpenAI fallback not implemented yet');
  }

  private async embedWithBasicStrategy(input: string, type: 'text' | 'image'): Promise<ProcessedEmbedding> {
    // Basic TF-IDF or random embedding as last resort
    const dimension = 512;
    const embedding = new Array(dimension).fill(0).map(() => Math.random() - 0.5);
    
    return {
      embedding,
      dimension,
      model: 'basic-fallback',
      source: 'basic',
      processingTime: 1,
      quality: 0.1,
      cached: false,
      metadata: { fallback: true, reason: 'service_unavailable' }
    };
  }

  private async embedFromCacheOnly(input: string, type: 'text' | 'image'): Promise<ProcessedEmbedding> {
    // Try to get from local cache only
    throw new Error('Cache-only strategy not implemented yet');
  }

  /**
   * Check service health
   */
  async checkHealth(): Promise<{
    mclip: boolean;
    overall: boolean;
    latency: number;
    details: any;
  }> {
    try {
      const connectionTest = await this.mclipClient.testConnection();
      return {
        mclip: connectionTest.connected,
        overall: connectionTest.connected,
        latency: connectionTest.latency,
        details: connectionTest.serviceHealth
      };
    } catch (error) {
      return {
        mclip: false,
        overall: false,
        latency: -1,
        details: { error: error.message }
      };
    }
  }

  /**
   * Get service metrics
   */
  getMetrics(): EmbeddingMetrics {
    return { ...this.metrics };
  }

  /**
   * Reset metrics
   */
  resetMetrics(): void {
    this.metrics = this.initializeMetrics();
    this.serviceStartTime = Date.now();
    this.emit('metricsReset');
  }

  /**
   * Compute semantic similarity between two texts or images
   */
  async computeSimilarity(
    item1: { text?: string; imagePath?: string },
    item2: { text?: string; imagePath?: string },
    options: EmbeddingOptions = {}
  ): Promise<{ similarity: number; embeddings: [ProcessedEmbedding, ProcessedEmbedding] }> {
    const [embedding1, embedding2] = await Promise.all([
      item1.text 
        ? this.embedText(item1.text, options)
        : this.embedImage(item1.imagePath!, options),
      item2.text 
        ? this.embedText(item2.text, options)
        : this.embedImage(item2.imagePath!, options)
    ]);

    const similarity = MCLIPClient.cosineSimilarity(
      embedding1.embedding,
      embedding2.embedding
    );

    return {
      similarity,
      embeddings: [embedding1, embedding2]
    };
  }

  /**
   * Find similar items from a collection
   */
  async findSimilar(
    query: { text?: string; imagePath?: string },
    collection: Array<{ text?: string; imagePath?: string; metadata?: any }>,
    topK: number = 5,
    options: EmbeddingOptions = {}
  ): Promise<Array<{ item: any; similarity: number; embedding: ProcessedEmbedding }>> {
    // Generate query embedding
    const queryEmbedding = query.text
      ? await this.embedText(query.text, options)
      : await this.embedImage(query.imagePath!, options);

    // Generate embeddings for collection
    const collectionEmbeddings = await this.embedBatch(
      collection.map(item => ({
        text: item.text,
        imagePath: item.imagePath,
        options
      })),
      options
    );

    // Compute similarities
    const similarities = collectionEmbeddings.map((embedding, index) => ({
      item: collection[index],
      similarity: MCLIPClient.cosineSimilarity(queryEmbedding.embedding, embedding.embedding),
      embedding
    }));

    // Sort by similarity and return top K
    return similarities
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, topK);
  }

  /**
   * Clear all caches
   */
  async clearAllCaches(): Promise<void> {
    await this.mclipClient.clearServiceCache();
    this.mclipClient.clearLocalCache();
    this.emit('cachesCleared');
  }
}

export default EmbeddingService;