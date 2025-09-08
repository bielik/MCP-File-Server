import { pipeline, env } from '@xenova/transformers';
import { config } from '../../config/index.js';
import { logWithContext } from '../../utils/logger.js';
import type { Pipeline } from '@xenova/transformers';
import path from 'path';
import { fileURLToPath } from 'url';

// Configure transformers environment for Node.js
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Set model cache directory
env.cacheDir = path.resolve(process.cwd(), config.mclip.cacheDir);

/**
 * Native AI Service using @xenova/transformers for M-CLIP embeddings
 * 
 * This service provides a TypeScript-native implementation of multimodal embeddings,
 * replacing the previous Python microservices architecture. It uses the M-CLIP model
 * to generate 512-dimensional embeddings for both text and images.
 * 
 * Features:
 * - Singleton pattern for efficient model loading
 * - Support for text embeddings 
 * - Support for image embeddings from buffers
 * - Structured logging for monitoring and debugging
 * - Automatic model caching for faster startup
 */
export class AiService {
  private static instance: AiService | null = null;
  private textPipeline: Pipeline | null = null;
  private imagePipeline: Pipeline | null = null;
  private isInitialized = false;
  private initializationPromise: Promise<void> | null = null;

  private constructor() {
    logWithContext.info('AiService: Creating new AI service instance');
  }

  /**
   * Get singleton instance of AiService
   */
  public static getInstance(): AiService {
    if (!AiService.instance) {
      AiService.instance = new AiService();
    }
    return AiService.instance;
  }

  /**
   * Initialize the AI service by loading the M-CLIP model
   * This method is idempotent and can be called multiple times safely
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
      logWithContext.info('AiService: Starting model initialization', {
        modelName: config.mclip.modelName,
        cacheDir: config.mclip.cacheDir,
        embeddingDimension: config.mclip.embeddingDimension,
      });

      // Load the feature extraction pipeline for M-CLIP
      // This model supports both text and image inputs
      logWithContext.debug('AiService: Loading feature extraction pipeline');
      
      this.textPipeline = await pipeline(
        'feature-extraction',
        config.mclip.modelName,
        {
          revision: 'main',
          device: 'cpu', // Use CPU for better compatibility
        }
      );

      // For now, use the same pipeline for both text and images
      // M-CLIP models can handle both modalities
      this.imagePipeline = this.textPipeline;

      this.isInitialized = true;
      const duration = Date.now() - startTime;

      logWithContext.info('AiService: Model initialization completed', {
        duration: `${duration}ms`,
        modelLoaded: true,
        embeddingDimension: config.mclip.embeddingDimension,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('AiService: Model initialization failed', error as Error, {
        duration: `${duration}ms`,
        modelName: config.mclip.modelName,
        cacheDir: config.mclip.cacheDir,
      });
      
      // Reset state on failure
      this.isInitialized = false;
      this.initializationPromise = null;
      this.textPipeline = null;
      this.imagePipeline = null;
      
      throw new Error(`Failed to initialize AI service: ${(error as Error).message}`);
    }
  }

  /**
   * Generate text embedding using M-CLIP
   * @param text - Input text string
   * @returns Promise<number[]> - 512-dimensional embedding vector
   */
  public async embedText(text: string): Promise<number[]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    if (!this.textPipeline) {
      throw new Error('Text pipeline not initialized');
    }

    const startTime = Date.now();
    
    try {
      logWithContext.debug('AiService: Generating text embedding', {
        textLength: text.length,
        textPreview: text.substring(0, 50) + (text.length > 50 ? '...' : ''),
      });

      // Generate embedding
      const result = await this.textPipeline(text, {
        pooling: 'mean',
        normalize: true,
      });

      // Extract the embedding tensor and convert to array
      let embedding: number[];
      if (result && typeof result === 'object' && 'data' in result) {
        embedding = Array.from(result.data as Float32Array);
      } else if (Array.isArray(result)) {
        embedding = result.flat();
      } else {
        throw new Error('Unexpected embedding result format');
      }

      const duration = Date.now() - startTime;

      // Validate embedding dimension
      if (embedding.length !== config.mclip.embeddingDimension) {
        logWithContext.warn('AiService: Unexpected embedding dimension', {
          expected: config.mclip.embeddingDimension,
          actual: embedding.length,
          duration: `${duration}ms`,
        });
      }

      logWithContext.debug('AiService: Text embedding generated', {
        embeddingDimension: embedding.length,
        duration: `${duration}ms`,
        embeddingNorm: Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0)),
      });

      return embedding;

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('AiService: Text embedding generation failed', error as Error, {
        textLength: text.length,
        duration: `${duration}ms`,
      });
      
      throw new Error(`Failed to generate text embedding: ${(error as Error).message}`);
    }
  }

  /**
   * Generate image embedding using M-CLIP
   * @param imageBuffer - Image data as Buffer (PNG, JPEG, etc.)
   * @returns Promise<number[]> - 512-dimensional embedding vector
   */
  public async embedImage(imageBuffer: Buffer): Promise<number[]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    if (!this.imagePipeline) {
      throw new Error('Image pipeline not initialized');
    }

    const startTime = Date.now();
    
    try {
      logWithContext.debug('AiService: Generating image embedding', {
        imageSize: imageBuffer.length,
        imageType: this.detectImageType(imageBuffer),
      });

      // Convert buffer to base64 data URL for the pipeline
      const base64 = imageBuffer.toString('base64');
      const mimeType = this.detectImageType(imageBuffer);
      const dataUrl = `data:${mimeType};base64,${base64}`;

      // Generate embedding
      const result = await this.imagePipeline(dataUrl, {
        pooling: 'mean',
        normalize: true,
      });

      // Extract the embedding tensor and convert to array
      let embedding: number[];
      if (result && typeof result === 'object' && 'data' in result) {
        embedding = Array.from(result.data as Float32Array);
      } else if (Array.isArray(result)) {
        embedding = result.flat();
      } else {
        throw new Error('Unexpected embedding result format');
      }

      const duration = Date.now() - startTime;

      // Validate embedding dimension
      if (embedding.length !== config.mclip.embeddingDimension) {
        logWithContext.warn('AiService: Unexpected embedding dimension for image', {
          expected: config.mclip.embeddingDimension,
          actual: embedding.length,
          duration: `${duration}ms`,
        });
      }

      logWithContext.debug('AiService: Image embedding generated', {
        embeddingDimension: embedding.length,
        duration: `${duration}ms`,
        embeddingNorm: Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0)),
      });

      return embedding;

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('AiService: Image embedding generation failed', error as Error, {
        imageSize: imageBuffer.length,
        duration: `${duration}ms`,
      });
      
      throw new Error(`Failed to generate image embedding: ${(error as Error).message}`);
    }
  }

  /**
   * Detect image MIME type from buffer
   */
  private detectImageType(buffer: Buffer): string {
    // Check for common image signatures
    if (buffer.length >= 8) {
      // PNG signature
      if (buffer[0] === 0x89 && buffer[1] === 0x50 && buffer[2] === 0x4E && buffer[3] === 0x47) {
        return 'image/png';
      }
      
      // JPEG signature
      if (buffer[0] === 0xFF && buffer[1] === 0xD8 && buffer[2] === 0xFF) {
        return 'image/jpeg';
      }
      
      // WebP signature
      if (buffer.slice(0, 4).toString() === 'RIFF' && buffer.slice(8, 12).toString() === 'WEBP') {
        return 'image/webp';
      }
    }
    
    // Default to JPEG if unknown
    return 'image/jpeg';
  }

  /**
   * Check if the service is initialized and ready
   */
  public isReady(): boolean {
    return this.isInitialized && this.textPipeline !== null && this.imagePipeline !== null;
  }

  /**
   * Get service status information
   */
  public getStatus(): {
    initialized: boolean;
    modelName: string;
    embeddingDimension: number;
    cacheDir: string;
  } {
    return {
      initialized: this.isInitialized,
      modelName: config.mclip.modelName,
      embeddingDimension: config.mclip.embeddingDimension,
      cacheDir: config.mclip.cacheDir,
    };
  }

  /**
   * Cleanup resources (for testing or shutdown)
   */
  public async cleanup(): Promise<void> {
    logWithContext.info('AiService: Cleaning up resources');
    
    this.textPipeline = null;
    this.imagePipeline = null;
    this.isInitialized = false;
    this.initializationPromise = null;
    
    logWithContext.info('AiService: Cleanup completed');
  }
}

// Export singleton instance
export const aiService = AiService.getInstance();