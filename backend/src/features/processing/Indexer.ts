import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { documentParser, type DocumentMetadata, type ExtractedImage } from './DocumentParser.js';
import { aiService } from '../../services/AiService.js';
import { vectorDbService, type VectorDocument } from '../../services/VectorDb.js';
import { keywordSearchService } from '../search/keywordSearch.js';
import { config } from '../../../config/index.js';
import { logWithContext } from '../../../utils/logger.js';

/**
 * Document Indexer - Processing Pipeline Orchestrator
 * 
 * This service orchestrates the complete document processing pipeline,
 * coordinating the DocumentParser, AiService, and VectorDbService to
 * provide end-to-end document indexing functionality.
 * 
 * Pipeline Flow:
 * 1. Parse PDF → Extract text and images (DocumentParser)
 * 2. Chunk text → Create meaningful segments
 * 3. Generate embeddings → Text and image embeddings (AiService)
 * 4. Store vectors → Save to Qdrant collections (VectorDbService)
 * 5. Index text → Add to FlexSearch for keyword search (KeywordSearchService)
 * 
 * Features:
 * - Complete end-to-end processing pipeline
 * - Automatic text chunking with overlap
 * - Batch processing for efficiency
 * - Comprehensive error handling and recovery
 * - Detailed progress tracking and logging
 * - Concurrent processing where safe
 */

export interface IndexingOptions {
  extractImages?: boolean;
  maxPages?: number;
  chunkText?: boolean;
  chunkSize?: number;
  chunkOverlap?: number;
  batchSize?: number;
  skipExisting?: boolean;
  metadata?: Record<string, any>;
}

export interface IndexingResult {
  success: boolean;
  filePath: string;
  fileName: string;
  documentId: string;
  processingTime: number;
  textChunksProcessed: number;
  imagesProcessed: number;
  totalVectorsStored: number;
  errors?: string[];
  metadata?: DocumentMetadata;
}

export interface IndexingProgress {
  stage: 'parsing' | 'chunking' | 'embedding_text' | 'embedding_images' | 'storing' | 'completed' | 'error';
  progress: number; // 0-100
  currentItem?: string;
  totalItems?: number;
  processedItems?: number;
  timeElapsed: number;
  estimatedTimeRemaining?: number;
}

export type ProgressCallback = (progress: IndexingProgress) => void;

/**
 * Document Indexer Class
 */
export class Indexer {
  private static instance: Indexer | null = null;
  private isInitialized = false;

  private constructor() {
    logWithContext.info('Indexer: Creating document indexer instance');
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): Indexer {
    if (!Indexer.instance) {
      Indexer.instance = new Indexer();
    }
    return Indexer.instance;
  }

  /**
   * Initialize the indexer
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    const startTime = Date.now();

    try {
      logWithContext.info('Indexer: Starting initialization');

      // Initialize all required services
      logWithContext.debug('Indexer: Initializing document parser');
      await documentParser.initialize();

      logWithContext.debug('Indexer: Initializing AI service');
      await aiService.initialize();

      logWithContext.debug('Indexer: Initializing vector database service');
      await vectorDbService.initialize();

      logWithContext.debug('Indexer: Initializing keyword search service');
      await keywordSearchService.initialize();

      this.isInitialized = true;
      const duration = Date.now() - startTime;

      logWithContext.info('Indexer: Initialization completed', {
        duration: `${duration}ms`,
        services: ['DocumentParser', 'AiService', 'VectorDbService', 'KeywordSearchService'],
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('Indexer: Initialization failed', error as Error, {
        duration: `${duration}ms`,
      });

      this.isInitialized = false;
      throw new Error(`Failed to initialize Indexer: ${(error as Error).message}`);
    }
  }

  /**
   * Index a single document file
   */
  public async indexFile(
    filePath: string,
    options: IndexingOptions = {},
    progressCallback?: ProgressCallback
  ): Promise<IndexingResult> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const startTime = Date.now();
    const fileName = path.basename(filePath);
    const documentId = uuidv4();
    
    // Set default options
    const opts: Required<IndexingOptions> = {
      extractImages: config.processing.enableImageExtraction,
      maxPages: config.processing.maxPages,
      chunkText: true,
      chunkSize: config.processing.chunkSize,
      chunkOverlap: config.processing.chunkOverlap,
      batchSize: 50,
      skipExisting: false,
      metadata: {},
      ...options,
    };

    const result: IndexingResult = {
      success: false,
      filePath,
      fileName,
      documentId,
      processingTime: 0,
      textChunksProcessed: 0,
      imagesProcessed: 0,
      totalVectorsStored: 0,
      errors: [],
    };

    const reportProgress = (stage: IndexingProgress['stage'], progress: number, currentItem?: string) => {
      if (progressCallback) {
        const timeElapsed = Date.now() - startTime;
        progressCallback({
          stage,
          progress,
          currentItem,
          timeElapsed,
        });
      }
    };

    try {
      logWithContext.info('Indexer: Starting document indexing', {
        filePath,
        fileName,
        documentId,
        options: opts,
      });

      reportProgress('parsing', 0, 'Parsing PDF document');

      // Step 1: Parse the document
      logWithContext.debug('Indexer: Step 1 - Parsing document');
      const parsedDoc = await documentParser.parseDocument(filePath, {
        extractImages: opts.extractImages,
        maxPages: opts.maxPages,
        chunkText: opts.chunkText,
        chunkSize: opts.chunkSize,
        chunkOverlap: opts.chunkOverlap,
      });

      result.metadata = parsedDoc.metadata;
      reportProgress('chunking', 20, 'Processing text chunks');

      // Step 2: Prepare text chunks for embedding
      const textChunks = parsedDoc.textChunks || [];
      logWithContext.debug('Indexer: Step 2 - Processing text chunks', {
        chunkCount: textChunks.length,
      });

      reportProgress('embedding_text', 30, 'Generating text embeddings');

      // Step 3: Generate text embeddings
      const textVectors: VectorDocument[] = [];
      if (textChunks.length > 0) {
        logWithContext.debug('Indexer: Step 3 - Generating text embeddings');
        
        for (let i = 0; i < textChunks.length; i++) {
          const chunk = textChunks[i];
          const chunkId = `${documentId}_text_${i}`;
          
          try {
            const embedding = await aiService.embedText(chunk);
            
            textVectors.push({
              id: chunkId,
              vector: embedding,
              payload: {
                file_path: filePath,
                content_type: 'text',
                text_content: chunk,
                page_number: Math.floor(i / 3) + 1, // Rough estimate
                chunk_index: i,
                created_at: new Date().toISOString(),
                file_size: parsedDoc.metadata.fileSize,
                document_title: parsedDoc.metadata.title || fileName,
                document_id: documentId,
                ...opts.metadata,
              },
            });

            // Report progress for text embeddings
            const textProgress = 30 + Math.floor((i / textChunks.length) * 30);
            reportProgress('embedding_text', textProgress, `Text chunk ${i + 1}/${textChunks.length}`);

          } catch (error) {
            logWithContext.warn('Indexer: Failed to generate embedding for text chunk', error as Error, {
              chunkIndex: i,
              chunkLength: chunk.length,
            });
            result.errors?.push(`Text embedding failed for chunk ${i}: ${(error as Error).message}`);
          }
        }
      }

      reportProgress('embedding_images', 60, 'Generating image embeddings');

      // Step 4: Generate image embeddings
      const imageVectors: VectorDocument[] = [];
      if (opts.extractImages && parsedDoc.images.length > 0) {
        logWithContext.debug('Indexer: Step 4 - Generating image embeddings', {
          imageCount: parsedDoc.images.length,
        });

        for (let i = 0; i < parsedDoc.images.length; i++) {
          const image = parsedDoc.images[i];
          const imageId = `${documentId}_image_${i}`;
          
          try {
            const embedding = await aiService.embedImage(image.buffer);
            
            imageVectors.push({
              id: imageId,
              vector: embedding,
              payload: {
                file_path: filePath,
                content_type: 'image',
                image_caption: `Image ${i + 1} from ${fileName}`,
                page_number: image.pageNumber,
                created_at: new Date().toISOString(),
                file_size: image.buffer.length,
                document_title: parsedDoc.metadata.title || fileName,
                document_id: documentId,
                image_format: image.format,
                image_width: image.width,
                image_height: image.height,
                ...opts.metadata,
              },
            });

            // Report progress for image embeddings
            const imageProgress = 60 + Math.floor((i / parsedDoc.images.length) * 20);
            reportProgress('embedding_images', imageProgress, `Image ${i + 1}/${parsedDoc.images.length}`);

          } catch (error) {
            logWithContext.warn('Indexer: Failed to generate embedding for image', error as Error, {
              imageIndex: i,
              imageFormat: image.format,
              imageSize: image.buffer.length,
            });
            result.errors?.push(`Image embedding failed for image ${i}: ${(error as Error).message}`);
          }
        }
      }

      reportProgress('storing', 80, 'Storing embeddings');

      // Step 5: Store embeddings in vector database
      let storedVectors = 0;
      
      if (textVectors.length > 0) {
        logWithContext.debug('Indexer: Step 5a - Storing text embeddings', {
          count: textVectors.length,
        });
        
        try {
          await vectorDbService.storeTextEmbeddings(textVectors);
          storedVectors += textVectors.length;
          result.textChunksProcessed = textVectors.length;
        } catch (error) {
          logWithContext.error('Indexer: Failed to store text embeddings', error as Error);
          result.errors?.push(`Failed to store text embeddings: ${(error as Error).message}`);
        }

        // Step 5c: Index text in FlexSearch for keyword search
        logWithContext.debug('Indexer: Step 5c - Indexing text for keyword search', {
          chunkCount: textChunks.length,
        });
        
        try {
          // Create documents for FlexSearch indexing
          const keywordDocs = textChunks.map((chunk, index) => ({
            id: `${documentId}_text_${index}`,
            content: chunk,
            documentId,
            filePath,
            chunkIndex: index,
            pageNumber: Math.floor(index / 3) + 1, // Rough estimate
            documentTitle: parsedDoc.metadata.title || fileName,
            createdAt: new Date().toISOString(),
          }));

          await keywordSearchService.addDocuments(keywordDocs);
          logWithContext.debug('Indexer: Text chunks indexed for keyword search', {
            count: keywordDocs.length,
          });
        } catch (error) {
          logWithContext.error('Indexer: Failed to index text for keyword search', error as Error);
          result.errors?.push(`Failed to index text for keyword search: ${(error as Error).message}`);
        }
      }

      if (imageVectors.length > 0) {
        logWithContext.debug('Indexer: Step 5b - Storing image embeddings', {
          count: imageVectors.length,
        });
        
        try {
          await vectorDbService.storeImageEmbeddings(imageVectors);
          storedVectors += imageVectors.length;
          result.imagesProcessed = imageVectors.length;
        } catch (error) {
          logWithContext.error('Indexer: Failed to store image embeddings', error as Error);
          result.errors?.push(`Failed to store image embeddings: ${(error as Error).message}`);
        }
      }

      result.totalVectorsStored = storedVectors;
      result.processingTime = Date.now() - startTime;
      result.success = storedVectors > 0 && (!result.errors || result.errors.length === 0);

      reportProgress('completed', 100, 'Indexing completed');

      logWithContext.info('Indexer: Document indexing completed', {
        fileName,
        documentId,
        success: result.success,
        textChunksProcessed: result.textChunksProcessed,
        imagesProcessed: result.imagesProcessed,
        totalVectorsStored: result.totalVectorsStored,
        processingTime: `${result.processingTime}ms`,
        errorCount: result.errors?.length || 0,
      });

      return result;

    } catch (error) {
      const processingTime = Date.now() - startTime;
      logWithContext.error('Indexer: Document indexing failed', error as Error, {
        fileName,
        documentId,
        processingTime: `${processingTime}ms`,
      });

      reportProgress('error', 0, 'Indexing failed');

      result.success = false;
      result.processingTime = processingTime;
      result.errors = result.errors || [];
      result.errors.push(`Indexing failed: ${(error as Error).message}`);

      return result;
    }
  }

  /**
   * Index multiple files in batch
   */
  public async indexFiles(
    filePaths: string[],
    options: IndexingOptions = {},
    progressCallback?: (fileIndex: number, fileResult: IndexingResult) => void
  ): Promise<IndexingResult[]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const startTime = Date.now();
    const results: IndexingResult[] = [];

    logWithContext.info('Indexer: Starting batch indexing', {
      fileCount: filePaths.length,
      options,
    });

    for (let i = 0; i < filePaths.length; i++) {
      const filePath = filePaths[i];
      
      try {
        logWithContext.debug('Indexer: Processing file in batch', {
          fileIndex: i + 1,
          totalFiles: filePaths.length,
          fileName: path.basename(filePath),
        });

        const result = await this.indexFile(filePath, options);
        results.push(result);

        if (progressCallback) {
          progressCallback(i, result);
        }

      } catch (error) {
        logWithContext.error('Indexer: Batch file processing failed', error as Error, {
          fileIndex: i + 1,
          filePath,
        });

        results.push({
          success: false,
          filePath,
          fileName: path.basename(filePath),
          documentId: uuidv4(),
          processingTime: 0,
          textChunksProcessed: 0,
          imagesProcessed: 0,
          totalVectorsStored: 0,
          errors: [(error as Error).message],
        });
      }
    }

    const totalDuration = Date.now() - startTime;
    const successCount = results.filter(r => r.success).length;
    const totalVectors = results.reduce((sum, r) => sum + r.totalVectorsStored, 0);

    logWithContext.info('Indexer: Batch indexing completed', {
      totalFiles: filePaths.length,
      successCount,
      failureCount: filePaths.length - successCount,
      totalVectors,
      totalDuration: `${totalDuration}ms`,
      averageTimePerFile: `${Math.round(totalDuration / filePaths.length)}ms`,
    });

    return results;
  }

  /**
   * Check if indexer is ready
   */
  public isReady(): boolean {
    return this.isInitialized && 
           documentParser.isReady() && 
           aiService.isReady() && 
           vectorDbService.isReady() &&
           keywordSearchService.isReady();
  }

  /**
   * Get indexer status
   */
  public getStatus(): {
    initialized: boolean;
    documentParser: boolean;
    aiService: boolean;
    vectorDbService: boolean;
    keywordSearchService: boolean;
    ready: boolean;
  } {
    return {
      initialized: this.isInitialized,
      documentParser: documentParser.isReady(),
      aiService: aiService.isReady(),
      vectorDbService: vectorDbService.isReady(),
      keywordSearchService: keywordSearchService.isReady(),
      ready: this.isReady(),
    };
  }

  /**
   * Get processing statistics from vector database
   */
  public async getProcessingStats(): Promise<{
    collections: any[];
    totalDocuments: number;
    totalVectors: number;
  }> {
    if (!vectorDbService.isReady()) {
      throw new Error('VectorDbService not ready');
    }

    try {
      const stats = await vectorDbService.getCollectionStats();
      const totalVectors = stats.reduce((sum, stat) => sum + stat.points_count, 0);
      
      // Estimate documents (assuming average chunks per document)
      const avgChunksPerDoc = 5;
      const totalDocuments = Math.ceil(totalVectors / avgChunksPerDoc);

      return {
        collections: stats,
        totalDocuments,
        totalVectors,
      };
    } catch (error) {
      logWithContext.error('Indexer: Failed to get processing stats', error as Error);
      throw error;
    }
  }
}

// Export singleton instance
export const indexer = Indexer.getInstance();