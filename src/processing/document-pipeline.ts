/**
 * Document Processing Pipeline
 * Orchestrates multimodal document processing using Docling, M-CLIP, and LlamaIndex patterns
 * Implements research-optimized chunking and indexing workflows
 */

import { EventEmitter } from 'events';
import * as path from 'path';
import { performance } from 'perf_hooks';
import { QdrantClient } from '@qdrant/js-client-rest';
import DoclingClient, { ProcessingResult, TextChunk, ExtractedImage } from './docling-client';
import MCLIPClient, { EmbeddingResponse } from '../embeddings/mclip-client';
import EmbeddingService from '../embeddings/embedding-service';

// Types and interfaces
export interface DocumentNode {
  node_id: string;
  node_type: 'text' | 'image' | 'table' | 'mixed';
  content: string;
  metadata: {
    document_id: string;
    page_number: number;
    position: { x: number; y: number };
    source_chunk_id?: string;
    source_image_id?: string;
    chunk_size: number;
    chunk_overlap: number;
    language?: string;
    confidence: number;
  };
  embedding?: number[];
  relationships: Array<{
    target_node_id: string;
    relationship_type: 'contains' | 'references' | 'follows' | 'caption' | 'similar';
    confidence: number;
  }>;
}

export interface IndexedDocument {
  document_id: string;
  file_path: string;
  nodes: DocumentNode[];
  metadata: {
    title?: string;
    authors: string[];
    total_pages: number;
    word_count: number;
    processing_time: number;
    quality_score: number;
    chunk_strategy: string;
    embedding_model: string;
    indexed_at: Date;
  };
  statistics: {
    total_nodes: number;
    text_nodes: number;
    image_nodes: number;
    table_nodes: number;
    average_chunk_size: number;
    embedding_coverage: number;
  };
}

export interface ChunkingOptions {
  strategy: 'semantic' | 'fixed' | 'sentence' | 'paragraph';
  chunk_size: number;
  chunk_overlap: number;
  preserve_sentences: boolean;
  preserve_paragraphs: boolean;
  min_chunk_size: number;
  max_chunk_size: number;
  split_on_headers: boolean;
  include_metadata: boolean;
}

export interface IndexingOptions {
  generate_embeddings: boolean;
  embedding_batch_size: number;
  store_in_qdrant: boolean;
  identify_relationships: boolean;
  extract_keywords: boolean;
  detect_language: boolean;
  calculate_quality: boolean;
}

export interface PipelineConfig {
  docling_service_url: string;
  mclip_service_url: string;
  qdrant_url: string;
  temp_directory: string;
  cache_directory: string;
  max_concurrent_documents: number;
  chunk_options: ChunkingOptions;
  index_options: IndexingOptions;
}

// Default configuration
const DEFAULT_CONFIG: PipelineConfig = {
  docling_service_url: 'http://localhost:8003',
  mclip_service_url: 'http://localhost:8002',
  qdrant_url: 'http://localhost:6333',
  temp_directory: './temp/pipeline',
  cache_directory: './cache/pipeline',
  max_concurrent_documents: 3,
  chunk_options: {
    strategy: 'semantic',
    chunk_size: 800,
    chunk_overlap: 50,
    preserve_sentences: true,
    preserve_paragraphs: true,
    min_chunk_size: 100,
    max_chunk_size: 1200,
    split_on_headers: true,
    include_metadata: true
  },
  index_options: {
    generate_embeddings: true,
    embedding_batch_size: 16,
    store_in_qdrant: true,
    identify_relationships: true,
    extract_keywords: true,
    detect_language: true,
    calculate_quality: true
  }
};

export class DocumentPipeline extends EventEmitter {
  private config: PipelineConfig;
  private doclingClient: DoclingClient;
  private embeddingService: EmbeddingService;
  private qdrantClient: QdrantClient;
  private processingQueue: Map<string, Promise<IndexedDocument>> = new Map();
  private processingStats = {
    documents_processed: 0,
    documents_failed: 0,
    total_nodes_created: 0,
    total_processing_time: 0,
    average_processing_time: 0
  };

  constructor(config: Partial<PipelineConfig> = {}) {
    super();
    this.config = { ...DEFAULT_CONFIG, ...config };
    
    // Initialize clients
    this.doclingClient = new DoclingClient({
      serviceUrl: this.config.docling_service_url
    });
    
    this.embeddingService = new EmbeddingService({
      mclipServiceUrl: this.config.mclip_service_url
    });
    
    this.qdrantClient = new QdrantClient({
      url: this.config.qdrant_url
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.embeddingService.on('error', (error) => {
      this.emit('embedding_error', error);
    });

    this.embeddingService.on('metricsUpdated', (metrics) => {
      this.emit('metrics_updated', { source: 'embedding', metrics });
    });
  }

  /**
   * Process a single document through the complete pipeline
   */
  async processDocument(filePath: string): Promise<IndexedDocument> {
    const documentId = this.generateDocumentId(filePath);
    
    // Check if already processing
    if (this.processingQueue.has(documentId)) {
      return this.processingQueue.get(documentId)!;
    }

    const processingPromise = this.executeDocumentProcessing(filePath, documentId);
    this.processingQueue.set(documentId, processingPromise);

    try {
      const result = await processingPromise;
      this.processingQueue.delete(documentId);
      return result;
    } catch (error) {
      this.processingQueue.delete(documentId);
      throw error;
    }
  }

  private async executeDocumentProcessing(filePath: string, documentId: string): Promise<IndexedDocument> {
    const startTime = performance.now();
    
    try {
      this.emit('processing_started', { document_id: documentId, file_path: filePath });
      
      // Stage 1: Extract content using Docling
      this.emit('stage_started', { stage: 'extraction', document_id: documentId });
      const processingResult = await this.doclingClient.processDocument(filePath, {
        extract_images: true,
        extract_tables: true,
        perform_ocr: true,
        max_pages: 500
      });
      
      if (!processingResult.success) {
        throw new Error(`Document extraction failed: ${processingResult.errors.join(', ')}`);
      }
      
      this.emit('stage_completed', { 
        stage: 'extraction', 
        document_id: documentId,
        text_chunks: processingResult.text_chunks.length,
        images: processingResult.images.length,
        tables: processingResult.tables.length
      });

      // Stage 2: Create optimized chunks
      this.emit('stage_started', { stage: 'chunking', document_id: documentId });
      const chunks = await this.createOptimizedChunks(processingResult, documentId);
      this.emit('stage_completed', { 
        stage: 'chunking', 
        document_id: documentId,
        chunks: chunks.length
      });

      // Stage 3: Create document nodes
      this.emit('stage_started', { stage: 'node_creation', document_id: documentId });
      const nodes = await this.createDocumentNodes(chunks, processingResult.images, documentId);
      this.emit('stage_completed', { 
        stage: 'node_creation', 
        document_id: documentId,
        nodes: nodes.length
      });

      // Stage 4: Generate embeddings
      if (this.config.index_options.generate_embeddings) {
        this.emit('stage_started', { stage: 'embedding', document_id: documentId });
        await this.generateNodeEmbeddings(nodes);
        this.emit('stage_completed', { 
          stage: 'embedding', 
          document_id: documentId,
          embedded_nodes: nodes.filter(n => n.embedding).length
        });
      }

      // Stage 5: Identify relationships
      if (this.config.index_options.identify_relationships) {
        this.emit('stage_started', { stage: 'relationships', document_id: documentId });
        this.identifyNodeRelationships(nodes);
        this.emit('stage_completed', { 
          stage: 'relationships', 
          document_id: documentId,
          total_relationships: nodes.reduce((sum, n) => sum + n.relationships.length, 0)
        });
      }

      // Stage 6: Store in vector database
      if (this.config.index_options.store_in_qdrant) {
        this.emit('stage_started', { stage: 'storage', document_id: documentId });
        await this.storeInVectorDatabase(nodes);
        this.emit('stage_completed', { 
          stage: 'storage', 
          document_id: documentId,
          stored_nodes: nodes.filter(n => n.embedding).length
        });
      }

      // Create final indexed document
      const processingTime = performance.now() - startTime;
      const indexedDocument: IndexedDocument = {
        document_id: documentId,
        file_path: filePath,
        nodes,
        metadata: {
          title: processingResult.metadata.title,
          authors: processingResult.metadata.authors,
          total_pages: processingResult.metadata.total_pages,
          word_count: processingResult.metadata.word_count,
          processing_time: processingTime,
          quality_score: processingResult.quality_score,
          chunk_strategy: this.config.chunk_options.strategy,
          embedding_model: 'clip-ViT-B-32-multilingual-v1',
          indexed_at: new Date()
        },
        statistics: this.calculateDocumentStatistics(nodes)
      };

      // Update global statistics
      this.updateProcessingStats(indexedDocument);
      
      this.emit('processing_completed', {
        document_id: documentId,
        processing_time: processingTime,
        nodes: nodes.length,
        quality_score: processingResult.quality_score
      });

      return indexedDocument;
      
    } catch (error) {
      const processingTime = performance.now() - startTime;
      this.processingStats.documents_failed++;
      
      this.emit('processing_failed', {
        document_id: documentId,
        error: error.message,
        processing_time: processingTime
      });
      
      throw error;
    }
  }

  /**
   * Create optimized chunks using research-focused strategies
   */
  private async createOptimizedChunks(
    processingResult: ProcessingResult, 
    documentId: string
  ): Promise<Array<{ content: string; metadata: any; chunk_type: string }>> {
    const chunks: Array<{ content: string; metadata: any; chunk_type: string }> = [];
    const options = this.config.chunk_options;

    // Group text chunks by page and type
    const pageGroups = new Map<number, TextChunk[]>();
    for (const chunk of processingResult.text_chunks) {
      if (!pageGroups.has(chunk.page_number)) {
        pageGroups.set(chunk.page_number, []);
      }
      pageGroups.get(chunk.page_number)!.push(chunk);
    }

    // Process each page
    for (const [pageNumber, pageChunks] of pageGroups.entries()) {
      // Sort chunks by position (top to bottom, left to right)
      pageChunks.sort((a, b) => {
        const posA = a.position?.y || 0;
        const posB = b.position?.y || 0;
        return posA - posB;
      });

      // Combine chunks based on strategy
      if (options.strategy === 'semantic') {
        chunks.push(...await this.semanticChunking(pageChunks, pageNumber, documentId));
      } else if (options.strategy === 'paragraph') {
        chunks.push(...this.paragraphChunking(pageChunks, pageNumber, documentId));
      } else {
        chunks.push(...this.fixedSizeChunking(pageChunks, pageNumber, documentId));
      }
    }

    return chunks;
  }

  private async semanticChunking(
    pageChunks: TextChunk[],
    pageNumber: number,
    documentId: string
  ): Promise<Array<{ content: string; metadata: any; chunk_type: string }>> {
    const chunks = [];
    let currentChunk = '';
    let currentMetadata: any = null;
    const options = this.config.chunk_options;

    for (let i = 0; i < pageChunks.length; i++) {
      const chunk = pageChunks[i];
      const chunkText = chunk.content;

      // Start new chunk if current is empty
      if (currentChunk.length === 0) {
        currentChunk = chunkText;
        currentMetadata = {
          document_id: documentId,
          page_number: pageNumber,
          source_chunk_ids: [chunk.chunk_id],
          chunk_type: chunk.chunk_type,
          position: chunk.position,
          confidence: chunk.confidence,
          language: chunk.language
        };
        continue;
      }

      // Check if adding this chunk would exceed size limits
      const combinedLength = currentChunk.length + chunkText.length + 1; // +1 for separator
      
      if (combinedLength <= options.max_chunk_size) {
        // Add to current chunk
        currentChunk += '\n' + chunkText;
        currentMetadata.source_chunk_ids.push(chunk.chunk_id);
        currentMetadata.confidence = Math.min(currentMetadata.confidence, chunk.confidence);
      } else {
        // Finalize current chunk if it meets minimum size
        if (currentChunk.length >= options.min_chunk_size) {
          chunks.push({
            content: currentChunk.trim(),
            metadata: currentMetadata,
            chunk_type: 'semantic_combined'
          });
        }

        // Start new chunk
        currentChunk = chunkText;
        currentMetadata = {
          document_id: documentId,
          page_number: pageNumber,
          source_chunk_ids: [chunk.chunk_id],
          chunk_type: chunk.chunk_type,
          position: chunk.position,
          confidence: chunk.confidence,
          language: chunk.language
        };
      }
    }

    // Add final chunk
    if (currentChunk.length >= options.min_chunk_size) {
      chunks.push({
        content: currentChunk.trim(),
        metadata: currentMetadata,
        chunk_type: 'semantic_combined'
      });
    }

    return chunks;
  }

  private paragraphChunking(
    pageChunks: TextChunk[],
    pageNumber: number,
    documentId: string
  ): Promise<Array<{ content: string; metadata: any; chunk_type: string }>> {
    // Implement paragraph-based chunking
    return Promise.resolve(pageChunks.map(chunk => ({
      content: chunk.content,
      metadata: {
        document_id: documentId,
        page_number: pageNumber,
        source_chunk_ids: [chunk.chunk_id],
        chunk_type: chunk.chunk_type,
        position: chunk.position,
        confidence: chunk.confidence,
        language: chunk.language
      },
      chunk_type: 'paragraph'
    })));
  }

  private fixedSizeChunking(
    pageChunks: TextChunk[],
    pageNumber: number,
    documentId: string
  ): Array<{ content: string; metadata: any; chunk_type: string }> {
    const chunks = [];
    const options = this.config.chunk_options;
    
    // Combine all page text
    const fullText = pageChunks.map(c => c.content).join('\n');
    
    // Split into fixed-size chunks with overlap
    for (let i = 0; i < fullText.length; i += options.chunk_size - options.chunk_overlap) {
      const chunkText = fullText.slice(i, i + options.chunk_size);
      
      if (chunkText.trim().length >= options.min_chunk_size) {
        chunks.push({
          content: chunkText.trim(),
          metadata: {
            document_id: documentId,
            page_number: pageNumber,
            start_position: i,
            end_position: i + chunkText.length,
            chunk_strategy: 'fixed_size'
          },
          chunk_type: 'fixed'
        });
      }
    }

    return chunks;
  }

  /**
   * Create document nodes from chunks and images
   */
  private async createDocumentNodes(
    chunks: Array<{ content: string; metadata: any; chunk_type: string }>,
    images: ExtractedImage[],
    documentId: string
  ): Promise<DocumentNode[]> {
    const nodes: DocumentNode[] = [];

    // Create text nodes
    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i];
      const node: DocumentNode = {
        node_id: `${documentId}_text_${i}`,
        node_type: 'text',
        content: chunk.content,
        metadata: {
          document_id: documentId,
          page_number: chunk.metadata.page_number,
          position: chunk.metadata.position || { x: 0, y: 0 },
          chunk_size: chunk.content.length,
          chunk_overlap: this.config.chunk_options.chunk_overlap,
          confidence: chunk.metadata.confidence || 0.8,
          language: chunk.metadata.language
        },
        relationships: []
      };

      nodes.push(node);
    }

    // Create image nodes
    for (let i = 0; i < images.length; i++) {
      const image = images[i];
      const node: DocumentNode = {
        node_id: `${documentId}_image_${i}`,
        node_type: 'image',
        content: image.extracted_text || image.caption || `Image: ${image.image_type}`,
        metadata: {
          document_id: documentId,
          page_number: image.page_number,
          position: { x: image.bbox.x || 0, y: image.bbox.y || 0 },
          source_image_id: image.image_id,
          image_path: image.image_path,
          image_type: image.image_type,
          chunk_size: (image.extracted_text || image.caption || '').length,
          chunk_overlap: 0,
          confidence: image.confidence
        },
        relationships: []
      };

      nodes.push(node);
    }

    return nodes;
  }

  /**
   * Generate embeddings for all nodes
   */
  private async generateNodeEmbeddings(nodes: DocumentNode[]): Promise<void> {
    const batchSize = this.config.index_options.embedding_batch_size;
    
    for (let i = 0; i < nodes.length; i += batchSize) {
      const batch = nodes.slice(i, i + batchSize);
      const batchRequests = batch.map(node => ({
        text: node.content,
        imagePath: node.node_type === 'image' ? node.metadata.image_path : undefined
      }));

      try {
        const embeddings = await this.embeddingService.embedBatch(batchRequests);
        
        for (let j = 0; j < batch.length; j++) {
          if (embeddings[j] && embeddings[j].embedding) {
            batch[j].embedding = embeddings[j].embedding;
          }
        }
      } catch (error) {
        console.warn(`Failed to generate embeddings for batch ${i}-${i+batchSize}: ${error.message}`);
        
        // Try individual embedding generation as fallback
        for (const node of batch) {
          try {
            const embedding = node.node_type === 'image' && node.metadata.image_path
              ? await this.embeddingService.embedImage(node.metadata.image_path)
              : await this.embeddingService.embedText(node.content);
            
            node.embedding = embedding.embedding;
          } catch (individualError) {
            console.warn(`Failed to generate embedding for node ${node.node_id}: ${individualError.message}`);
          }
        }
      }
    }
  }

  /**
   * Identify relationships between nodes
   */
  private identifyNodeRelationships(nodes: DocumentNode[]): void {
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      
      // Find relationships with other nodes
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue;
        
        const otherNode = nodes[j];
        
        // Same page proximity
        if (node.metadata.page_number === otherNode.metadata.page_number) {
          const distance = Math.abs(node.metadata.position.y - otherNode.metadata.position.y);
          
          if (distance < 100) { // Close proximity threshold
            node.relationships.push({
              target_node_id: otherNode.node_id,
              relationship_type: 'proximity' as any,
              confidence: Math.max(0.1, 1 - distance / 100)
            });
          }
        }

        // Text-image relationships
        if (node.node_type === 'text' && otherNode.node_type === 'image') {
          const hasImageReference = this.checkImageReference(node.content, otherNode);
          if (hasImageReference.isReference) {
            node.relationships.push({
              target_node_id: otherNode.node_id,
              relationship_type: 'references',
              confidence: hasImageReference.confidence
            });
          }
          
          const isCaption = this.checkImageCaption(node.content, otherNode);
          if (isCaption.isCaption) {
            node.relationships.push({
              target_node_id: otherNode.node_id,
              relationship_type: 'caption' as any,
              confidence: isCaption.confidence
            });
          }
        }

        // Semantic similarity (if embeddings available)
        if (node.embedding && otherNode.embedding) {
          const similarity = this.cosineSimilarity(node.embedding, otherNode.embedding);
          if (similarity > 0.7) { // High similarity threshold
            node.relationships.push({
              target_node_id: otherNode.node_id,
              relationship_type: 'similar' as any,
              confidence: similarity
            });
          }
        }
      }
    }
  }

  private checkImageReference(text: string, imageNode: DocumentNode): { isReference: boolean; confidence: number } {
    const lowerText = text.toLowerCase();
    const imageType = imageNode.metadata.image_type;
    
    const patterns = [
      /fig\.?\s*\d+/i,
      /figure\s*\d+/i,
      /image\s*\d+/i,
      /diagram\s*\d+/i,
      new RegExp(`${imageType}\\s*\\d+`, 'i')
    ];
    
    for (const pattern of patterns) {
      if (pattern.test(lowerText)) {
        return { isReference: true, confidence: 0.8 };
      }
    }
    
    return { isReference: false, confidence: 0 };
  }

  private checkImageCaption(text: string, imageNode: DocumentNode): { isCaption: boolean; confidence: number } {
    const lowerText = text.toLowerCase();
    
    // Check if text is short and contains figure-related words
    if (text.length < 200 && 
        (lowerText.includes('figure') || lowerText.includes('fig') || 
         lowerText.includes('image') || lowerText.includes(imageNode.metadata.image_type))) {
      return { isCaption: true, confidence: 0.9 };
    }
    
    return { isCaption: false, confidence: 0 };
  }

  private cosineSimilarity(vec1: number[], vec2: number[]): number {
    if (vec1.length !== vec2.length) return 0;
    
    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;
    
    for (let i = 0; i < vec1.length; i++) {
      dotProduct += vec1[i] * vec2[i];
      norm1 += vec1[i] * vec1[i];
      norm2 += vec2[i] * vec2[i];
    }
    
    if (norm1 === 0 || norm2 === 0) return 0;
    return dotProduct / (Math.sqrt(norm1) * Math.sqrt(norm2));
  }

  /**
   * Store nodes in Qdrant vector database
   */
  private async storeInVectorDatabase(nodes: DocumentNode[]): Promise<void> {
    const textNodes = nodes.filter(n => n.node_type === 'text' && n.embedding);
    const imageNodes = nodes.filter(n => n.node_type === 'image' && n.embedding);

    // Store text nodes
    if (textNodes.length > 0) {
      const textPoints = textNodes.map(node => ({
        id: node.node_id,
        vector: node.embedding!,
        payload: {
          content: node.content,
          metadata: node.metadata,
          relationships: node.relationships
        }
      }));

      try {
        await this.qdrantClient.upsert('mcp_text_chunks', {
          wait: true,
          points: textPoints
        });
      } catch (error) {
        console.warn(`Failed to store text nodes: ${error.message}`);
      }
    }

    // Store image nodes
    if (imageNodes.length > 0) {
      const imagePoints = imageNodes.map(node => ({
        id: node.node_id,
        vector: node.embedding!,
        payload: {
          content: node.content,
          metadata: node.metadata,
          relationships: node.relationships
        }
      }));

      try {
        await this.qdrantClient.upsert('mcp_image_embeddings', {
          wait: true,
          points: imagePoints
        });
      } catch (error) {
        console.warn(`Failed to store image nodes: ${error.message}`);
      }
    }
  }

  private calculateDocumentStatistics(nodes: DocumentNode[]): IndexedDocument['statistics'] {
    const textNodes = nodes.filter(n => n.node_type === 'text');
    const imageNodes = nodes.filter(n => n.node_type === 'image');
    const tableNodes = nodes.filter(n => n.node_type === 'table');
    
    const avgChunkSize = textNodes.length > 0 
      ? textNodes.reduce((sum, n) => sum + n.content.length, 0) / textNodes.length
      : 0;
    
    const embeddingCoverage = nodes.filter(n => n.embedding).length / nodes.length;

    return {
      total_nodes: nodes.length,
      text_nodes: textNodes.length,
      image_nodes: imageNodes.length,
      table_nodes: tableNodes.length,
      average_chunk_size: avgChunkSize,
      embedding_coverage: embeddingCoverage
    };
  }

  private updateProcessingStats(document: IndexedDocument): void {
    this.processingStats.documents_processed++;
    this.processingStats.total_nodes_created += document.nodes.length;
    this.processingStats.total_processing_time += document.metadata.processing_time;
    this.processingStats.average_processing_time = 
      this.processingStats.total_processing_time / this.processingStats.documents_processed;
  }

  private generateDocumentId(filePath: string): string {
    const basename = path.basename(filePath, path.extname(filePath));
    const timestamp = Date.now();
    return `${basename}_${timestamp}`.replace(/[^a-zA-Z0-9_]/g, '_');
  }

  /**
   * Get processing statistics
   */
  getProcessingStats() {
    return { ...this.processingStats };
  }

  /**
   * Process multiple documents concurrently
   */
  async processBatch(filePaths: string[]): Promise<IndexedDocument[]> {
    const maxConcurrent = this.config.max_concurrent_documents;
    const results: IndexedDocument[] = [];
    
    for (let i = 0; i < filePaths.length; i += maxConcurrent) {
      const batch = filePaths.slice(i, i + maxConcurrent);
      const batchPromises = batch.map(path => this.processDocument(path));
      
      try {
        const batchResults = await Promise.allSettled(batchPromises);
        
        for (const result of batchResults) {
          if (result.status === 'fulfilled') {
            results.push(result.value);
          } else {
            console.error(`Batch processing failed: ${result.reason.message}`);
          }
        }
      } catch (error) {
        console.error(`Batch processing error: ${error.message}`);
      }
    }
    
    return results;
  }

  /**
   * Health check for all services
   */
  async checkHealth() {
    const health = {
      pipeline: true,
      docling: false,
      embedding: false,
      qdrant: false,
      overall: false
    };

    try {
      // Check Docling service
      const doclingHealth = await this.doclingClient.health();
      health.docling = doclingHealth.status === 'healthy';
    } catch (error) {
      console.warn(`Docling health check failed: ${error.message}`);
    }

    try {
      // Check embedding service
      const embeddingHealth = await this.embeddingService.checkHealth();
      health.embedding = embeddingHealth.overall;
    } catch (error) {
      console.warn(`Embedding health check failed: ${error.message}`);
    }

    try {
      // Check Qdrant
      const qdrantHealth = await this.qdrantClient.api('cluster').clusterStatus();
      health.qdrant = true; // If no error thrown
    } catch (error) {
      console.warn(`Qdrant health check failed: ${error.message}`);
    }

    health.overall = health.docling && health.embedding && health.qdrant;
    return health;
  }
}

export default DocumentPipeline;