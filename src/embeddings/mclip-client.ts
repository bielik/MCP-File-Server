/**
 * M-CLIP Embedding Service Client
 * TypeScript client wrapper for the M-CLIP Python FastAPI service
 * Provides type-safe, optimized access to multimodal embedding generation
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import * as fs from 'fs/promises';
import * as path from 'path';
import { createHash } from 'crypto';
import { performance } from 'perf_hooks';

// Types and interfaces
export interface EmbeddingResponse {
  embedding: number[];
  dimension: number;
  model: string;
  processing_time: number;
  cached: boolean;
}

export interface BatchEmbeddingResponse {
  embeddings: EmbeddingResponse[];
  batch_size: number;
  total_processing_time: number;
}

export interface ServiceHealthResponse {
  status: string;
  model_loaded: boolean;
  device: string;
  cache_size: number;
  memory_usage: {
    rss_mb: number;
    vms_mb: number;
    cpu_percent: number;
    gpu_memory_mb: number;
  };
  statistics: {
    requests_processed: number;
    embeddings_generated: number;
    cache_hits: number;
    cache_misses: number;
    batch_requests: number;
    average_processing_time: number;
  };
}

export interface ServiceStats {
  uptime: number;
  requests_processed: number;
  embeddings_generated: number;
  cache_hit_rate: number;
  average_processing_time: number;
  memory_usage: {
    rss_mb: number;
    vms_mb: number;
    cpu_percent: number;
    gpu_memory_mb: number;
  };
}

export interface EmbeddingRequest {
  text?: string;
  image_url?: string;
  image_path?: string;
  cache_key?: string;
}

export interface MCLIPClientConfig {
  serviceUrl: string;
  timeout: number;
  maxRetries: number;
  retryDelay: number;
  enableLocalCache: boolean;
  localCacheSize: number;
  localCacheTTL: number;
}

interface CacheEntry {
  embedding: number[];
  timestamp: number;
  ttl: number;
}

// Default configuration
const DEFAULT_CONFIG: MCLIPClientConfig = {
  serviceUrl: 'http://localhost:8002',
  timeout: 30000, // 30 seconds
  maxRetries: 3,
  retryDelay: 1000, // 1 second
  enableLocalCache: true,
  localCacheSize: 1000,
  localCacheTTL: 3600000 // 1 hour in milliseconds
};

export class MCLIPClient {
  private client: AxiosInstance;
  private config: MCLIPClientConfig;
  private localCache: Map<string, CacheEntry>;
  private circuitBreakerFailures: number = 0;
  private circuitBreakerResetTime: number = 0;
  private readonly maxCircuitBreakerFailures = 5;
  private readonly circuitBreakerResetDelay = 60000; // 1 minute

  constructor(config: Partial<MCLIPClientConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.localCache = new Map();

    // Initialize axios client
    this.client = axios.create({
      baseURL: this.config.serviceUrl,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Setup request/response interceptors
    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor for logging and circuit breaker
    this.client.interceptors.request.use(
      (config) => {
        // Check circuit breaker
        if (this.isCircuitBreakerOpen()) {
          throw new Error('Circuit breaker is open. Service may be unavailable.');
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling and circuit breaker
    this.client.interceptors.response.use(
      (response) => {
        // Reset circuit breaker on successful response
        this.circuitBreakerFailures = 0;
        return response;
      },
      (error) => {
        // Increment circuit breaker failures
        this.circuitBreakerFailures++;
        if (this.circuitBreakerFailures >= this.maxCircuitBreakerFailures) {
          this.circuitBreakerResetTime = Date.now() + this.circuitBreakerResetDelay;
        }
        return Promise.reject(error);
      }
    );
  }

  private isCircuitBreakerOpen(): boolean {
    if (this.circuitBreakerFailures >= this.maxCircuitBreakerFailures) {
      if (Date.now() > this.circuitBreakerResetTime) {
        // Reset circuit breaker
        this.circuitBreakerFailures = 0;
        this.circuitBreakerResetTime = 0;
        return false;
      }
      return true;
    }
    return false;
  }

  private generateCacheKey(content: string): string {
    return createHash('sha256').update(content).digest('hex');
  }

  private getCachedEmbedding(cacheKey: string): number[] | null {
    if (!this.config.enableLocalCache) {
      return null;
    }

    const entry = this.localCache.get(cacheKey);
    if (entry) {
      // Check if entry is still valid
      if (Date.now() - entry.timestamp < entry.ttl) {
        return entry.embedding;
      } else {
        // Remove expired entry
        this.localCache.delete(cacheKey);
      }
    }
    return null;
  }

  private setCachedEmbedding(cacheKey: string, embedding: number[]): void {
    if (!this.config.enableLocalCache) {
      return;
    }

    // Implement LRU cache behavior
    if (this.localCache.size >= this.config.localCacheSize) {
      // Remove oldest entry
      const firstKey = this.localCache.keys().next().value;
      this.localCache.delete(firstKey);
    }

    this.localCache.set(cacheKey, {
      embedding,
      timestamp: Date.now(),
      ttl: this.config.localCacheTTL
    });
  }

  private async retryWithBackoff<T>(
    operation: () => Promise<T>,
    retries: number = this.config.maxRetries
  ): Promise<T> {
    try {
      return await operation();
    } catch (error) {
      if (retries > 0) {
        await new Promise(resolve => setTimeout(resolve, this.config.retryDelay));
        return this.retryWithBackoff(operation, retries - 1);
      }
      throw error;
    }
  }

  /**
   * Check service health
   */
  async health(): Promise<ServiceHealthResponse> {
    try {
      const response: AxiosResponse<ServiceHealthResponse> = await this.client.get('/health');
      return response.data;
    } catch (error) {
      throw new Error(`Health check failed: ${error}`);
    }
  }

  /**
   * Get service statistics
   */
  async getStats(): Promise<ServiceStats> {
    try {
      const response: AxiosResponse<ServiceStats> = await this.client.get('/stats');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get stats: ${error}`);
    }
  }

  /**
   * Generate text embedding
   */
  async embedText(text: string): Promise<EmbeddingResponse> {
    if (!text || text.trim().length === 0) {
      throw new Error('Text cannot be empty');
    }

    const startTime = performance.now();
    const cacheKey = this.generateCacheKey(text);

    // Check local cache
    const cached = this.getCachedEmbedding(cacheKey);
    if (cached) {
      return {
        embedding: cached,
        dimension: cached.length,
        model: 'clip-ViT-B-32-multilingual-v1',
        processing_time: performance.now() - startTime,
        cached: true
      };
    }

    // Call service
    const operation = async () => {
      const response: AxiosResponse<EmbeddingResponse> = await this.client.post(
        '/embed/text',
        { text }
      );
      return response.data;
    };

    try {
      const result = await this.retryWithBackoff(operation);
      
      // Cache the result
      this.setCachedEmbedding(cacheKey, result.embedding);
      
      return result;
    } catch (error) {
      throw new Error(`Text embedding failed: ${error}`);
    }
  }

  /**
   * Generate image embedding from file path
   */
  async embedImagePath(imagePath: string): Promise<EmbeddingResponse> {
    if (!imagePath || imagePath.trim().length === 0) {
      throw new Error('Image path cannot be empty');
    }

    // Check if file exists
    try {
      await fs.access(imagePath);
    } catch {
      throw new Error(`Image file not found: ${imagePath}`);
    }

    const startTime = performance.now();
    
    // Generate cache key from file path and modification time
    const stat = await fs.stat(imagePath);
    const cacheContent = `${imagePath}:${stat.mtime.getTime()}`;
    const cacheKey = this.generateCacheKey(cacheContent);

    // Check local cache
    const cached = this.getCachedEmbedding(cacheKey);
    if (cached) {
      return {
        embedding: cached,
        dimension: cached.length,
        model: 'clip-ViT-B-32-multilingual-v1',
        processing_time: performance.now() - startTime,
        cached: true
      };
    }

    // Call service
    const operation = async () => {
      const response: AxiosResponse<EmbeddingResponse> = await this.client.post(
        '/embed/image',
        { image_path: imagePath }
      );
      return response.data;
    };

    try {
      const result = await this.retryWithBackoff(operation);
      
      // Cache the result
      this.setCachedEmbedding(cacheKey, result.embedding);
      
      return result;
    } catch (error) {
      throw new Error(`Image embedding failed: ${error}`);
    }
  }

  /**
   * Generate embedding from uploaded image file
   */
  async embedImageUpload(imagePath: string): Promise<EmbeddingResponse> {
    if (!imagePath || imagePath.trim().length === 0) {
      throw new Error('Image path cannot be empty');
    }

    try {
      // Check if file exists
      await fs.access(imagePath);
      
      // Read file and create form data
      const imageBuffer = await fs.readFile(imagePath);
      const formData = new FormData();
      const blob = new Blob([imageBuffer]);
      formData.append('file', blob, path.basename(imagePath));

      const response: AxiosResponse<EmbeddingResponse> = await this.client.post(
        '/embed/image-upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Image upload embedding failed: ${error}`);
    }
  }

  /**
   * Generate batch embeddings
   */
  async embedBatch(requests: EmbeddingRequest[]): Promise<BatchEmbeddingResponse> {
    if (!requests || requests.length === 0) {
      throw new Error('Batch requests cannot be empty');
    }

    if (requests.length > 32) {
      throw new Error('Batch size cannot exceed 32 items');
    }

    // Validate all requests
    for (const request of requests) {
      if (!request.text && !request.image_path && !request.image_url) {
        throw new Error('Each request must have either text, image_path, or image_url');
      }
    }

    const operation = async () => {
      const response: AxiosResponse<BatchEmbeddingResponse> = await this.client.post(
        '/embed/batch',
        { items: requests }
      );
      return response.data;
    };

    try {
      return await this.retryWithBackoff(operation);
    } catch (error) {
      throw new Error(`Batch embedding failed: ${error}`);
    }
  }

  /**
   * Clear service cache
   */
  async clearServiceCache(): Promise<{ message: string }> {
    try {
      const response = await this.client.post('/cache/clear');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to clear service cache: ${error}`);
    }
  }

  /**
   * Get service cache info
   */
  async getCacheInfo(): Promise<{
    cache_size: number;
    max_size: number;
    ttl: number;
    hit_rate: number;
  }> {
    try {
      const response = await this.client.get('/cache/info');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get cache info: ${error}`);
    }
  }

  /**
   * Clear local cache
   */
  clearLocalCache(): void {
    this.localCache.clear();
  }

  /**
   * Get local cache statistics
   */
  getLocalCacheStats(): {
    size: number;
    maxSize: number;
    hitRate: number;
  } {
    // Calculate hit rate based on cache size vs requests
    // This is a simplified implementation
    return {
      size: this.localCache.size,
      maxSize: this.config.localCacheSize,
      hitRate: 0 // TODO: Implement proper hit rate calculation
    };
  }

  /**
   * Test connectivity and performance
   */
  async testConnection(): Promise<{
    connected: boolean;
    latency: number;
    serviceHealth: ServiceHealthResponse;
  }> {
    try {
      const startTime = performance.now();
      const health = await this.health();
      const latency = performance.now() - startTime;

      return {
        connected: health.status === 'healthy',
        latency,
        serviceHealth: health
      };
    } catch (error) {
      return {
        connected: false,
        latency: -1,
        serviceHealth: {} as ServiceHealthResponse
      };
    }
  }

  /**
   * Compute cosine similarity between two embeddings
   */
  static cosineSimilarity(embedding1: number[], embedding2: number[]): number {
    if (embedding1.length !== embedding2.length) {
      throw new Error('Embeddings must have the same dimension');
    }

    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;

    for (let i = 0; i < embedding1.length; i++) {
      dotProduct += embedding1[i] * embedding2[i];
      norm1 += embedding1[i] * embedding1[i];
      norm2 += embedding2[i] * embedding2[i];
    }

    if (norm1 === 0 || norm2 === 0) {
      return 0;
    }

    return dotProduct / (Math.sqrt(norm1) * Math.sqrt(norm2));
  }

  /**
   * Find most similar embeddings from a list
   */
  static findMostSimilar(
    queryEmbedding: number[],
    embeddings: Array<{ embedding: number[]; metadata?: any }>,
    topK: number = 5
  ): Array<{ similarity: number; metadata?: any; index: number }> {
    const similarities = embeddings.map((item, index) => ({
      similarity: this.cosineSimilarity(queryEmbedding, item.embedding),
      metadata: item.metadata,
      index
    }));

    return similarities
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, topK);
  }
}

export default MCLIPClient;