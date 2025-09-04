/**
 * Docling PDF Processing Client
 * TypeScript client for the Docling Python service
 * Provides comprehensive PDF processing with image extraction and OCR
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import * as fs from 'fs/promises';
import * as path from 'path';
import FormData from 'form-data';
import { performance } from 'perf_hooks';

// Types and interfaces
export interface ProcessingOptions {
  extract_images?: boolean;
  extract_tables?: boolean;
  extract_equations?: boolean;
  perform_ocr?: boolean;
  ocr_languages?: string[];
  max_pages?: number;
  image_min_size?: number;
  preserve_layout?: boolean;
}

export interface ExtractedImage {
  image_id: string;
  page_number: number;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  image_path: string;
  image_type: 'figure' | 'diagram' | 'chart' | 'photo' | 'equation' | 'table';
  caption?: string;
  extracted_text?: string;
  confidence: number;
  metadata: Record<string, any>;
}

export interface ExtractedTable {
  table_id: string;
  page_number: number;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  table_data: string[][];
  caption?: string;
  headers?: string[];
  metadata: Record<string, any>;
}

export interface TextChunk {
  chunk_id: string;
  page_number: number;
  content: string;
  chunk_type: 'paragraph' | 'heading' | 'list' | 'caption' | 'footnote';
  position: {
    x: number;
    y: number;
  };
  font_info?: Record<string, any>;
  language?: string;
  confidence: number;
}

export interface DocumentMetadata {
  title?: string;
  authors: string[];
  abstract?: string;
  keywords: string[];
  doi?: string;
  publication_date?: string;
  language: string;
  total_pages: number;
  word_count: number;
  processing_time: number;
  extraction_method: 'docling' | 'fallback' | 'hybrid';
}

export interface ProcessingResult {
  document_id: string;
  success: boolean;
  metadata: DocumentMetadata;
  text_chunks: TextChunk[];
  images: ExtractedImage[];
  tables: ExtractedTable[];
  relationships: Array<{
    type: 'reference' | 'caption' | 'proximity';
    text_chunk_id: string;
    image_id: string;
    confidence: number;
    reason: string;
  }>;
  processing_time: number;
  quality_score: number;
  errors: string[];
  warnings: string[];
}

export interface ServiceHealth {
  status: string;
  docling_available: boolean;
  fallback_available: boolean;
  ocr_available: boolean;
  temp_space_mb: number;
  cache_size_mb: number;
  statistics: {
    documents_processed: number;
    pages_processed: number;
    images_extracted: number;
    processing_failures: number;
    average_processing_time: number;
  };
}

export interface ProcessingStats {
  service_stats: {
    documents_processed: number;
    pages_processed: number;
    images_extracted: number;
    processing_failures: number;
    average_processing_time: number;
  };
  system_info: {
    temp_directory: string;
    temp_size_mb: number;
    cache_directory: string;
    cache_size_mb: number;
    max_file_size_mb: number;
    max_pages: number;
    supported_formats: string[];
  };
}

export interface DoclingClientConfig {
  serviceUrl: string;
  timeout: number;
  maxRetries: number;
  retryDelay: number;
  maxFileSize: number;
}

// Default configuration
const DEFAULT_CONFIG: DoclingClientConfig = {
  serviceUrl: 'http://localhost:8003',
  timeout: 300000, // 5 minutes for large documents
  maxRetries: 3,
  retryDelay: 2000,
  maxFileSize: 100 * 1024 * 1024 // 100MB
};

export class DoclingClient {
  private client: AxiosInstance;
  private config: DoclingClientConfig;

  constructor(config: Partial<DoclingClientConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };

    this.client = axios.create({
      baseURL: this.config.serviceUrl,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`📤 Docling API: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        console.log(`📥 Docling API: ${response.status} ${response.config.url} (${response.config.method?.toUpperCase()})`);
        return response;
      },
      (error) => {
        console.error(`❌ Docling API Error: ${error.response?.status} ${error.config?.url}`);
        return Promise.reject(error);
      }
    );
  }

  private async retryWithBackoff<T>(
    operation: () => Promise<T>,
    retries: number = this.config.maxRetries
  ): Promise<T> {
    try {
      return await operation();
    } catch (error) {
      if (retries > 0 && this.isRetryableError(error)) {
        console.log(`⏳ Retrying operation in ${this.config.retryDelay}ms... (${retries} retries left)`);
        await new Promise(resolve => setTimeout(resolve, this.config.retryDelay));
        return this.retryWithBackoff(operation, retries - 1);
      }
      throw error;
    }
  }

  private isRetryableError(error: any): boolean {
    // Retry on network errors and 5xx server errors
    return !error.response || (error.response.status >= 500 && error.response.status < 600);
  }

  /**
   * Check service health
   */
  async health(): Promise<ServiceHealth> {
    try {
      const response: AxiosResponse<ServiceHealth> = await this.client.get('/health');
      return response.data;
    } catch (error) {
      throw new Error(`Health check failed: ${error}`);
    }
  }

  /**
   * Get service statistics
   */
  async getStats(): Promise<ProcessingStats> {
    try {
      const response: AxiosResponse<ProcessingStats> = await this.client.get('/stats');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get stats: ${error}`);
    }
  }

  /**
   * Process document from file path
   */
  async processDocument(
    filePath: string,
    options: ProcessingOptions = {}
  ): Promise<ProcessingResult> {
    if (!filePath || filePath.trim().length === 0) {
      throw new Error('File path cannot be empty');
    }

    // Check if file exists
    try {
      await fs.access(filePath);
    } catch {
      throw new Error(`File not found: ${filePath}`);
    }

    // Check file size
    const stat = await fs.stat(filePath);
    if (stat.size > this.config.maxFileSize) {
      throw new Error(
        `File too large: ${(stat.size / 1024 / 1024).toFixed(1)}MB > ${(this.config.maxFileSize / 1024 / 1024).toFixed(1)}MB`
      );
    }

    const defaultOptions: ProcessingOptions = {
      extract_images: true,
      extract_tables: true,
      extract_equations: true,
      perform_ocr: true,
      ocr_languages: ['eng', 'deu', 'fra', 'spa', 'ita'],
      max_pages: 500,
      image_min_size: 100,
      preserve_layout: true
    };

    const finalOptions = { ...defaultOptions, ...options };

    const operation = async () => {
      const response: AxiosResponse<ProcessingResult> = await this.client.post('/process', {
        file_path: filePath,
        options: finalOptions,
        cache_results: true
      });
      return response.data;
    };

    try {
      console.log(`📄 Processing document: ${filePath}`);
      const startTime = performance.now();
      
      const result = await this.retryWithBackoff(operation);
      const clientTime = performance.now() - startTime;
      
      console.log(`✅ Document processed in ${clientTime.toFixed(0)}ms (service: ${result.processing_time.toFixed(0)}ms)`);
      console.log(`📊 Extracted: ${result.text_chunks.length} text chunks, ${result.images.length} images, ${result.tables.length} tables`);
      
      return result;
    } catch (error) {
      console.error(`❌ Document processing failed: ${error}`);
      throw new Error(`Document processing failed: ${error}`);
    }
  }

  /**
   * Process uploaded file
   */
  async processUploadedFile(
    filePath: string,
    options: ProcessingOptions = {}
  ): Promise<ProcessingResult> {
    if (!filePath || filePath.trim().length === 0) {
      throw new Error('File path cannot be empty');
    }

    // Check if file exists
    try {
      await fs.access(filePath);
    } catch {
      throw new Error(`File not found: ${filePath}`);
    }

    // Check file size
    const stat = await fs.stat(filePath);
    if (stat.size > this.config.maxFileSize) {
      throw new Error(
        `File too large: ${(stat.size / 1024 / 1024).toFixed(1)}MB > ${(this.config.maxFileSize / 1024 / 1024).toFixed(1)}MB`
      );
    }

    const operation = async () => {
      // Create form data
      const formData = new FormData();
      const fileBuffer = await fs.readFile(filePath);
      formData.append('file', fileBuffer, {
        filename: path.basename(filePath),
        contentType: this.getContentType(filePath)
      });

      // Add options as form fields
      if (options.extract_images !== undefined) {
        formData.append('extract_images', options.extract_images.toString());
      }
      if (options.extract_tables !== undefined) {
        formData.append('extract_tables', options.extract_tables.toString());
      }
      if (options.perform_ocr !== undefined) {
        formData.append('perform_ocr', options.perform_ocr.toString());
      }
      if (options.max_pages !== undefined) {
        formData.append('max_pages', options.max_pages.toString());
      }

      const response: AxiosResponse<ProcessingResult> = await this.client.post(
        '/process-upload',
        formData,
        {
          headers: {
            ...formData.getHeaders(),
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      return response.data;
    };

    try {
      console.log(`📤 Uploading and processing: ${filePath}`);
      const startTime = performance.now();
      
      const result = await this.retryWithBackoff(operation);
      const clientTime = performance.now() - startTime;
      
      console.log(`✅ Upload processed in ${clientTime.toFixed(0)}ms (service: ${result.processing_time.toFixed(0)}ms)`);
      console.log(`📊 Extracted: ${result.text_chunks.length} text chunks, ${result.images.length} images, ${result.tables.length} tables`);
      
      return result;
    } catch (error) {
      console.error(`❌ Upload processing failed: ${error}`);
      throw new Error(`Upload processing failed: ${error}`);
    }
  }

  private getContentType(filePath: string): string {
    const ext = path.extname(filePath).toLowerCase();
    switch (ext) {
      case '.pdf':
        return 'application/pdf';
      case '.docx':
        return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      case '.pptx':
        return 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
      default:
        return 'application/octet-stream';
    }
  }

  /**
   * Clear service cache
   */
  async clearCache(): Promise<{ message: string }> {
    try {
      const response = await this.client.post('/cache/clear');
      console.log('🧹 Service cache cleared');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to clear cache: ${error}`);
    }
  }

  /**
   * Clean up temporary files
   */
  async cleanupTempFiles(): Promise<{ message: string }> {
    try {
      const response = await this.client.post('/cleanup');
      console.log('🧹 Temporary files cleaned up');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to cleanup temp files: ${error}`);
    }
  }

  /**
   * Test connectivity and performance
   */
  async testConnection(): Promise<{
    connected: boolean;
    latency: number;
    serviceHealth: ServiceHealth;
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
        serviceHealth: {} as ServiceHealth
      };
    }
  }

  /**
   * Extract only images from a document
   */
  async extractImages(filePath: string): Promise<ExtractedImage[]> {
    const options: ProcessingOptions = {
      extract_images: true,
      extract_tables: false,
      extract_equations: false,
      perform_ocr: true,
      max_pages: 500
    };

    const result = await this.processDocument(filePath, options);
    return result.images;
  }

  /**
   * Extract only text from a document
   */
  async extractText(filePath: string): Promise<{
    text_chunks: TextChunk[];
    full_text: string;
    metadata: DocumentMetadata;
  }> {
    const options: ProcessingOptions = {
      extract_images: false,
      extract_tables: false,
      extract_equations: false,
      perform_ocr: false
    };

    const result = await this.processDocument(filePath, options);
    const fullText = result.text_chunks
      .sort((a, b) => a.page_number - b.page_number)
      .map(chunk => chunk.content)
      .join('\n\n');

    return {
      text_chunks: result.text_chunks,
      full_text: fullText,
      metadata: result.metadata
    };
  }

  /**
   * Get document summary and statistics
   */
  async getDocumentSummary(filePath: string): Promise<{
    metadata: DocumentMetadata;
    content_stats: {
      total_chunks: number;
      total_images: number;
      total_tables: number;
      pages_with_images: number;
      avg_chunk_length: number;
      language_distribution: Record<string, number>;
    };
    quality_metrics: {
      overall_score: number;
      text_confidence: number;
      image_confidence: number;
      extraction_completeness: number;
    };
  }> {
    const result = await this.processDocument(filePath);

    // Calculate content statistics
    const pagesWithImages = new Set(result.images.map(img => img.page_number)).size;
    const avgChunkLength = result.text_chunks.reduce((sum, chunk) => sum + chunk.content.length, 0) / result.text_chunks.length;
    
    const languageDistribution: Record<string, number> = {};
    result.text_chunks.forEach(chunk => {
      if (chunk.language) {
        languageDistribution[chunk.language] = (languageDistribution[chunk.language] || 0) + 1;
      }
    });

    // Calculate quality metrics
    const textConfidence = result.text_chunks.reduce((sum, chunk) => sum + chunk.confidence, 0) / result.text_chunks.length;
    const imageConfidence = result.images.reduce((sum, img) => sum + img.confidence, 0) / (result.images.length || 1);
    const extractionCompleteness = Math.min(result.metadata.word_count / 1000, 1.0); // Assume 1000 words = complete

    return {
      metadata: result.metadata,
      content_stats: {
        total_chunks: result.text_chunks.length,
        total_images: result.images.length,
        total_tables: result.tables.length,
        pages_with_images: pagesWithImages,
        avg_chunk_length: avgChunkLength,
        language_distribution: languageDistribution
      },
      quality_metrics: {
        overall_score: result.quality_score,
        text_confidence: textConfidence || 0,
        image_confidence: imageConfidence || 0,
        extraction_completeness: extractionCompleteness
      }
    };
  }
}

export default DoclingClient;