/**
 * Automated Document Indexing Pipeline
 * File system monitoring with intelligent document processing queue
 * Handles batch processing, error recovery, and progress tracking
 */

import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as chokidar from 'chokidar';
import { performance } from 'perf_hooks';
import DocumentPipeline, { IndexedDocument, PipelineConfig } from '../processing/document-pipeline';
import SearchService from '../search/search-service';

// File system monitoring types
export interface WatcherConfig {
  paths: string[];
  ignored_patterns: string[];
  file_extensions: string[];
  debounce_ms: number;
  max_file_size_mb: number;
  enable_recursive: boolean;
}

export interface ProcessingQueue {
  pending: QueuedDocument[];
  processing: Map<string, ProcessingJob>;
  completed: CompletedDocument[];
  failed: FailedDocument[];
}

export interface QueuedDocument {
  id: string;
  file_path: string;
  detected_at: Date;
  file_size: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  retry_count: number;
  metadata: {
    change_type: 'added' | 'changed' | 'moved';
    previous_path?: string;
  };
}

export interface ProcessingJob {
  document: QueuedDocument;
  started_at: Date;
  progress: {
    stage: string;
    percentage: number;
    current_operation: string;
  };
  pipeline_promise: Promise<IndexedDocument>;
}

export interface CompletedDocument {
  id: string;
  file_path: string;
  indexed_document: IndexedDocument;
  processed_at: Date;
  processing_time_ms: number;
  quality_score: number;
}

export interface FailedDocument {
  id: string;
  file_path: string;
  failed_at: Date;
  error_message: string;
  retry_count: number;
  should_retry: boolean;
}

export interface IndexingStats {
  documents_discovered: number;
  documents_processed: number;
  documents_failed: number;
  documents_skipped: number;
  average_processing_time: number;
  total_nodes_created: number;
  total_images_extracted: number;
  queue_size: number;
  active_jobs: number;
  uptime_ms: number;
}

export interface IndexingConfig {
  watcher: WatcherConfig;
  pipeline: Partial<PipelineConfig>;
  queue: {
    max_concurrent_jobs: number;
    max_queue_size: number;
    retry_attempts: number;
    retry_delay_ms: number;
    priority_boost_hours: number;
  };
  optimization: {
    enable_duplicate_detection: boolean;
    enable_incremental_updates: boolean;
    batch_similar_documents: boolean;
    cache_file_hashes: boolean;
  };
  notifications: {
    enable_progress_events: boolean;
    enable_error_notifications: boolean;
    progress_update_interval_ms: number;
  };
}

// Default configuration
const DEFAULT_CONFIG: IndexingConfig = {
  watcher: {
    paths: ['./documents', './uploads'],
    ignored_patterns: [
      '**/.git/**',
      '**/node_modules/**',
      '**/.DS_Store',
      '**/Thumbs.db',
      '**/*.tmp',
      '**/*.temp'
    ],
    file_extensions: ['.pdf', '.docx', '.pptx', '.txt', '.md'],
    debounce_ms: 2000,
    max_file_size_mb: 100,
    enable_recursive: true
  },
  pipeline: {
    max_concurrent_documents: 2 // Conservative for resource management
  },
  queue: {
    max_concurrent_jobs: 3,
    max_queue_size: 100,
    retry_attempts: 3,
    retry_delay_ms: 5000,
    priority_boost_hours: 24
  },
  optimization: {
    enable_duplicate_detection: true,
    enable_incremental_updates: true,
    batch_similar_documents: false,
    cache_file_hashes: true
  },
  notifications: {
    enable_progress_events: true,
    enable_error_notifications: true,
    progress_update_interval_ms: 1000
  }
};

export class DocumentIndexingPipeline extends EventEmitter {
  private config: IndexingConfig;
  private documentPipeline: DocumentPipeline;
  private searchService: SearchService;
  private watcher?: chokidar.FSWatcher;
  private queue: ProcessingQueue;
  private fileHashes: Map<string, string> = new Map();
  private stats: IndexingStats;
  private startTime: number;
  private processingInterval?: NodeJS.Timeout;

  constructor(
    config: Partial<IndexingConfig> & { 
      documentPipeline: DocumentPipeline;
      searchService: SearchService;
    }
  ) {
    super();
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.documentPipeline = config.documentPipeline;
    this.searchService = config.searchService;
    
    this.queue = {
      pending: [],
      processing: new Map(),
      completed: [],
      failed: []
    };

    this.stats = {
      documents_discovered: 0,
      documents_processed: 0,
      documents_failed: 0,
      documents_skipped: 0,
      average_processing_time: 0,
      total_nodes_created: 0,
      total_images_extracted: 0,
      queue_size: 0,
      active_jobs: 0,
      uptime_ms: 0
    };

    this.startTime = Date.now();
    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.documentPipeline.on('processing_started', (event) => {
      this.updateJobProgress(event.document_id, 'extraction', 10, 'Starting document extraction');
    });

    this.documentPipeline.on('stage_started', (event) => {
      this.updateJobProgress(event.document_id, event.stage, this.getStageProgress(event.stage), `Starting ${event.stage}`);
    });

    this.documentPipeline.on('stage_completed', (event) => {
      const progress = this.getStageProgress(event.stage) + 15;
      this.updateJobProgress(event.document_id, event.stage, progress, `Completed ${event.stage}`);
    });

    this.documentPipeline.on('processing_completed', (event) => {
      this.handleProcessingCompleted(event.document_id, event);
    });

    this.documentPipeline.on('processing_failed', (event) => {
      this.handleProcessingFailed(event.document_id, event.error);
    });
  }

  /**
   * Start the automated indexing pipeline
   */
  async start(): Promise<void> {
    try {
      console.log('🚀 Starting Document Indexing Pipeline');
      
      // Validate watched directories
      await this.validateWatchedPaths();
      
      // Load existing file hashes if caching enabled
      if (this.config.optimization.cache_file_hashes) {
        await this.loadFileHashCache();
      }

      // Start file system monitoring
      await this.startFileSystemMonitoring();
      
      // Start processing loop
      this.startProcessingLoop();
      
      // Start progress monitoring
      if (this.config.notifications.enable_progress_events) {
        this.startProgressMonitoring();
      }

      // Discover existing files for initial indexing
      await this.discoverExistingFiles();
      
      this.emit('pipeline_started', {
        watched_paths: this.config.watcher.paths,
        queue_capacity: this.config.queue.max_queue_size,
        concurrent_jobs: this.config.queue.max_concurrent_jobs
      });

      console.log('✅ Document Indexing Pipeline started successfully');
      
    } catch (error) {
      this.emit('pipeline_error', { stage: 'startup', error: error.message });
      throw new Error(`Failed to start indexing pipeline: ${error.message}`);
    }
  }

  /**
   * Stop the indexing pipeline
   */
  async stop(): Promise<void> {
    try {
      console.log('🛑 Stopping Document Indexing Pipeline');
      
      // Stop file system monitoring
      if (this.watcher) {
        await this.watcher.close();
      }
      
      // Stop processing loop
      if (this.processingInterval) {
        clearInterval(this.processingInterval);
      }
      
      // Wait for active jobs to complete (with timeout)
      await this.waitForActiveJobs(30000); // 30 second timeout
      
      // Save file hash cache
      if (this.config.optimization.cache_file_hashes) {
        await this.saveFileHashCache();
      }
      
      this.emit('pipeline_stopped', {
        processed_documents: this.stats.documents_processed,
        failed_documents: this.stats.documents_failed,
        uptime_ms: Date.now() - this.startTime
      });

      console.log('✅ Document Indexing Pipeline stopped');
      
    } catch (error) {
      this.emit('pipeline_error', { stage: 'shutdown', error: error.message });
      throw new Error(`Failed to stop indexing pipeline: ${error.message}`);
    }
  }

  private async validateWatchedPaths(): Promise<void> {
    for (const watchPath of this.config.watcher.paths) {
      try {
        const stat = await fs.stat(watchPath);
        if (!stat.isDirectory()) {
          throw new Error(`Path is not a directory: ${watchPath}`);
        }
      } catch (error) {
        if (error.code === 'ENOENT') {
          console.warn(`⚠️ Creating watched directory: ${watchPath}`);
          await fs.mkdir(watchPath, { recursive: true });
        } else {
          throw error;
        }
      }
    }
  }

  private async startFileSystemMonitoring(): Promise<void> {
    this.watcher = chokidar.watch(this.config.watcher.paths, {
      ignored: this.config.watcher.ignored_patterns,
      persistent: true,
      ignoreInitial: false,
      followSymlinks: false,
      cwd: process.cwd(),
      disableGlobbing: false,
      usePolling: false,
      interval: 100,
      binaryInterval: 300,
      alwaysStat: false,
      depth: this.config.watcher.enable_recursive ? undefined : 0,
      ignorePermissionErrors: true,
      atomic: this.config.watcher.debounce_ms
    });

    // Set up event handlers
    this.watcher
      .on('add', (filePath, stats) => this.handleFileAdded(filePath, stats))
      .on('change', (filePath, stats) => this.handleFileChanged(filePath, stats))
      .on('unlink', (filePath) => this.handleFileRemoved(filePath))
      .on('addDir', (dirPath) => this.emit('directory_added', { path: dirPath }))
      .on('unlinkDir', (dirPath) => this.emit('directory_removed', { path: dirPath }))
      .on('error', (error) => this.emit('watcher_error', { error: error.message }))
      .on('ready', () => this.emit('watcher_ready', { paths: this.config.watcher.paths }));
  }

  private async handleFileAdded(filePath: string, stats?: fs.Stats): Promise<void> {
    if (!this.shouldProcessFile(filePath, stats)) {
      return;
    }

    const document = await this.createQueuedDocument(filePath, 'added', stats);
    this.addToQueue(document);
    
    this.stats.documents_discovered++;
    this.emit('file_discovered', { file_path: filePath, change_type: 'added' });
  }

  private async handleFileChanged(filePath: string, stats?: fs.Stats): Promise<void> {
    if (!this.shouldProcessFile(filePath, stats)) {
      return;
    }

    // Check if file actually changed using hash comparison
    if (this.config.optimization.enable_duplicate_detection) {
      const hasChanged = await this.hasFileChanged(filePath);
      if (!hasChanged) {
        this.stats.documents_skipped++;
        return;
      }
    }

    const document = await this.createQueuedDocument(filePath, 'changed', stats);
    this.addToQueue(document);
    
    this.emit('file_changed', { file_path: filePath });
  }

  private handleFileRemoved(filePath: string): void {
    // Remove from processing queue if pending
    this.queue.pending = this.queue.pending.filter(doc => doc.file_path !== filePath);
    
    // TODO: Remove from search index
    this.emit('file_removed', { file_path: filePath });
  }

  private shouldProcessFile(filePath: string, stats?: fs.Stats): boolean {
    // Check file extension
    const ext = path.extname(filePath).toLowerCase();
    if (!this.config.watcher.file_extensions.includes(ext)) {
      return false;
    }

    // Check file size
    if (stats) {
      const sizeInMB = stats.size / (1024 * 1024);
      if (sizeInMB > this.config.watcher.max_file_size_mb) {
        this.emit('file_too_large', { file_path: filePath, size_mb: sizeInMB });
        return false;
      }
    }

    return true;
  }

  private async createQueuedDocument(
    filePath: string, 
    changeType: 'added' | 'changed' | 'moved',
    stats?: fs.Stats
  ): Promise<QueuedDocument> {
    const id = this.generateDocumentId(filePath);
    const fileStats = stats || await fs.stat(filePath);
    
    return {
      id,
      file_path: filePath,
      detected_at: new Date(),
      file_size: fileStats.size,
      priority: this.calculatePriority(filePath, changeType),
      retry_count: 0,
      metadata: {
        change_type: changeType
      }
    };
  }

  private calculatePriority(filePath: string, changeType: string): 'low' | 'medium' | 'high' | 'critical' {
    // Priority based on file type and change type
    const ext = path.extname(filePath).toLowerCase();
    
    if (changeType === 'added') {
      if (ext === '.pdf') return 'high';
      if (ext === '.docx') return 'medium';
      return 'low';
    }
    
    if (changeType === 'changed') {
      return 'medium';
    }
    
    return 'low';
  }

  private addToQueue(document: QueuedDocument): void {
    // Check queue capacity
    if (this.queue.pending.length >= this.config.queue.max_queue_size) {
      // Remove lowest priority document
      this.queue.pending.sort((a, b) => this.priorityValue(b.priority) - this.priorityValue(a.priority));
      const removed = this.queue.pending.pop();
      if (removed) {
        this.emit('document_dropped', { document_id: removed.id, reason: 'queue_full' });
      }
    }

    // Add document to queue
    this.queue.pending.push(document);
    this.stats.queue_size = this.queue.pending.length;
    
    this.emit('document_queued', {
      document_id: document.id,
      file_path: document.file_path,
      priority: document.priority,
      queue_size: this.queue.pending.length
    });
  }

  private priorityValue(priority: string): number {
    const values = { low: 1, medium: 2, high: 3, critical: 4 };
    return values[priority] || 1;
  }

  private startProcessingLoop(): void {
    this.processingInterval = setInterval(async () => {
      await this.processQueuedDocuments();
    }, 1000); // Check every second
  }

  private async processQueuedDocuments(): Promise<void> {
    // Update stats
    this.stats.queue_size = this.queue.pending.length;
    this.stats.active_jobs = this.queue.processing.size;
    this.stats.uptime_ms = Date.now() - this.startTime;

    // Process documents if capacity available
    while (
      this.queue.pending.length > 0 && 
      this.queue.processing.size < this.config.queue.max_concurrent_jobs
    ) {
      // Sort by priority and age
      this.queue.pending.sort((a, b) => {
        const priorityDiff = this.priorityValue(b.priority) - this.priorityValue(a.priority);
        if (priorityDiff !== 0) return priorityDiff;
        
        // If same priority, older documents first
        return a.detected_at.getTime() - b.detected_at.getTime();
      });

      const document = this.queue.pending.shift()!;
      await this.processDocument(document);
    }
  }

  private async processDocument(document: QueuedDocument): Promise<void> {
    const job: ProcessingJob = {
      document,
      started_at: new Date(),
      progress: {
        stage: 'initializing',
        percentage: 0,
        current_operation: 'Preparing document processing'
      },
      pipeline_promise: this.documentPipeline.processDocument(document.file_path)
    };

    // Add to processing map
    this.queue.processing.set(document.id, job);
    
    this.emit('processing_started', {
      document_id: document.id,
      file_path: document.file_path,
      priority: document.priority
    });

    try {
      const result = await job.pipeline_promise;
      this.handleProcessingCompleted(document.id, result);
      
    } catch (error) {
      this.handleProcessingFailed(document.id, error.message);
    }
  }

  private handleProcessingCompleted(documentId: string, result: any): void {
    const job = this.queue.processing.get(documentId);
    if (!job) return;

    const processingTime = Date.now() - job.started_at.getTime();
    
    // Move to completed
    const completedDoc: CompletedDocument = {
      id: documentId,
      file_path: job.document.file_path,
      indexed_document: result,
      processed_at: new Date(),
      processing_time_ms: processingTime,
      quality_score: result.quality_score || 0
    };
    
    this.queue.completed.push(completedDoc);
    this.queue.processing.delete(documentId);
    
    // Update stats
    this.stats.documents_processed++;
    this.stats.total_nodes_created += result.nodes?.length || 0;
    this.stats.total_images_extracted += result.images?.length || 0;
    
    const totalTime = this.stats.average_processing_time * (this.stats.documents_processed - 1) + processingTime;
    this.stats.average_processing_time = totalTime / this.stats.documents_processed;
    
    // Update search index
    this.indexDocumentForSearch(result);
    
    // Update file hash cache
    if (this.config.optimization.cache_file_hashes) {
      this.updateFileHash(job.document.file_path);
    }
    
    this.emit('processing_completed', {
      document_id: documentId,
      file_path: job.document.file_path,
      processing_time_ms: processingTime,
      quality_score: result.quality_score,
      nodes_created: result.nodes?.length || 0
    });
  }

  private handleProcessingFailed(documentId: string, error: string): void {
    const job = this.queue.processing.get(documentId);
    if (!job) return;

    const failedDoc: FailedDocument = {
      id: documentId,
      file_path: job.document.file_path,
      failed_at: new Date(),
      error_message: error,
      retry_count: job.document.retry_count,
      should_retry: job.document.retry_count < this.config.queue.retry_attempts
    };
    
    this.queue.processing.delete(documentId);
    
    if (failedDoc.should_retry) {
      // Retry after delay
      setTimeout(() => {
        const retryDoc = {
          ...job.document,
          retry_count: job.document.retry_count + 1,
          priority: 'high' as const // Boost priority for retries
        };
        this.addToQueue(retryDoc);
      }, this.config.queue.retry_delay_ms * (job.document.retry_count + 1));
      
      this.emit('processing_retry_scheduled', {
        document_id: documentId,
        retry_count: job.document.retry_count + 1,
        delay_ms: this.config.queue.retry_delay_ms * (job.document.retry_count + 1)
      });
      
    } else {
      this.queue.failed.push(failedDoc);
      this.stats.documents_failed++;
      
      this.emit('processing_failed', {
        document_id: documentId,
        file_path: job.document.file_path,
        error_message: error,
        final_failure: true
      });
    }
  }

  private updateJobProgress(documentId: string, stage: string, percentage: number, operation: string): void {
    const job = this.queue.processing.get(documentId);
    if (job) {
      job.progress = { stage, percentage, current_operation: operation };
      
      if (this.config.notifications.enable_progress_events) {
        this.emit('processing_progress', {
          document_id: documentId,
          stage,
          percentage,
          operation
        });
      }
    }
  }

  private getStageProgress(stage: string): number {
    const stageProgress = {
      'extraction': 20,
      'chunking': 40,
      'node_creation': 60,
      'embedding': 80,
      'relationships': 90,
      'storage': 95
    };
    return stageProgress[stage] || 0;
  }

  private async indexDocumentForSearch(indexedDocument: IndexedDocument): Promise<void> {
    try {
      // Index document nodes for search
      // This would integrate with the search service
      this.emit('document_indexed_for_search', {
        document_id: indexedDocument.document_id,
        nodes_count: indexedDocument.nodes.length
      });
    } catch (error) {
      console.warn(`Failed to index document for search: ${error.message}`);
    }
  }

  private async hasFileChanged(filePath: string): Promise<boolean> {
    try {
      const currentHash = await this.calculateFileHash(filePath);
      const storedHash = this.fileHashes.get(filePath);
      return currentHash !== storedHash;
    } catch (error) {
      return true; // Assume changed if we can't calculate hash
    }
  }

  private async calculateFileHash(filePath: string): Promise<string> {
    // Simple hash based on file stats (size + mtime)
    const stats = await fs.stat(filePath);
    return `${stats.size}_${stats.mtime.getTime()}`;
  }

  private async updateFileHash(filePath: string): Promise<void> {
    try {
      const hash = await this.calculateFileHash(filePath);
      this.fileHashes.set(filePath, hash);
    } catch (error) {
      console.warn(`Failed to update file hash for ${filePath}: ${error.message}`);
    }
  }

  private async loadFileHashCache(): Promise<void> {
    // Load from persistent storage (simplified - in production use database)
    try {
      const cacheFile = path.join(process.cwd(), 'cache', 'file_hashes.json');
      const data = await fs.readFile(cacheFile, 'utf-8');
      const hashes = JSON.parse(data);
      this.fileHashes = new Map(Object.entries(hashes));
      console.log(`📁 Loaded ${this.fileHashes.size} file hashes from cache`);
    } catch (error) {
      console.log('📁 No file hash cache found, starting fresh');
    }
  }

  private async saveFileHashCache(): Promise<void> {
    try {
      const cacheDir = path.join(process.cwd(), 'cache');
      await fs.mkdir(cacheDir, { recursive: true });
      
      const cacheFile = path.join(cacheDir, 'file_hashes.json');
      const hashes = Object.fromEntries(this.fileHashes);
      await fs.writeFile(cacheFile, JSON.stringify(hashes, null, 2));
      console.log(`💾 Saved ${this.fileHashes.size} file hashes to cache`);
    } catch (error) {
      console.warn(`Failed to save file hash cache: ${error.message}`);
    }
  }

  private async discoverExistingFiles(): Promise<void> {
    console.log('🔍 Discovering existing files for initial indexing...');
    
    for (const watchPath of this.config.watcher.paths) {
      await this.scanDirectory(watchPath);
    }
  }

  private async scanDirectory(dirPath: string): Promise<void> {
    try {
      const entries = await fs.readdir(dirPath, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);
        
        if (entry.isDirectory()) {
          if (this.config.watcher.enable_recursive) {
            await this.scanDirectory(fullPath);
          }
        } else if (entry.isFile()) {
          const stats = await fs.stat(fullPath);
          if (this.shouldProcessFile(fullPath, stats)) {
            await this.handleFileAdded(fullPath, stats);
          }
        }
      }
    } catch (error) {
      console.warn(`Failed to scan directory ${dirPath}: ${error.message}`);
    }
  }

  private startProgressMonitoring(): void {
    setInterval(() => {
      this.emit('pipeline_status', {
        queue: {
          pending: this.queue.pending.length,
          processing: this.queue.processing.size,
          completed: this.queue.completed.length,
          failed: this.queue.failed.length
        },
        stats: this.stats,
        active_jobs: Array.from(this.queue.processing.values()).map(job => ({
          document_id: job.document.id,
          file_path: job.document.file_path,
          progress: job.progress,
          elapsed_ms: Date.now() - job.started_at.getTime()
        }))
      });
    }, this.config.notifications.progress_update_interval_ms);
  }

  private async waitForActiveJobs(timeoutMs: number): Promise<void> {
    const startTime = Date.now();
    
    while (this.queue.processing.size > 0 && (Date.now() - startTime) < timeoutMs) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    if (this.queue.processing.size > 0) {
      console.warn(`⚠️ Timed out waiting for ${this.queue.processing.size} active jobs`);
    }
  }

  private generateDocumentId(filePath: string): string {
    const basename = path.basename(filePath, path.extname(filePath));
    const timestamp = Date.now();
    return `${basename}_${timestamp}`.replace(/[^a-zA-Z0-9_]/g, '_');
  }

  /**
   * Get current indexing statistics
   */
  getStats(): IndexingStats {
    return { ...this.stats };
  }

  /**
   * Get current queue status
   */
  getQueueStatus() {
    return {
      pending: this.queue.pending.length,
      processing: this.queue.processing.size,
      completed: this.queue.completed.length,
      failed: this.queue.failed.length,
      total_capacity: this.config.queue.max_queue_size,
      concurrent_capacity: this.config.queue.max_concurrent_jobs
    };
  }

  /**
   * Manually add document to processing queue
   */
  async queueDocument(filePath: string, priority: 'low' | 'medium' | 'high' | 'critical' = 'medium'): Promise<void> {
    try {
      const stats = await fs.stat(filePath);
      const document = await this.createQueuedDocument(filePath, 'added', stats);
      document.priority = priority;
      
      this.addToQueue(document);
    } catch (error) {
      throw new Error(`Failed to queue document ${filePath}: ${error.message}`);
    }
  }

  /**
   * Clear failed documents from queue
   */
  clearFailedDocuments(): void {
    this.queue.failed = [];
    this.emit('failed_queue_cleared');
  }

  /**
   * Retry all failed documents
   */
  retryFailedDocuments(): void {
    const failedToRetry = this.queue.failed.filter(doc => 
      doc.retry_count < this.config.queue.retry_attempts
    );
    
    for (const failed of failedToRetry) {
      const retryDoc: QueuedDocument = {
        id: this.generateDocumentId(failed.file_path),
        file_path: failed.file_path,
        detected_at: new Date(),
        file_size: 0,
        priority: 'high',
        retry_count: failed.retry_count + 1,
        metadata: { change_type: 'changed' }
      };
      
      this.addToQueue(retryDoc);
    }
    
    this.queue.failed = this.queue.failed.filter(doc => 
      doc.retry_count >= this.config.queue.retry_attempts
    );
    
    this.emit('failed_documents_retried', { count: failedToRetry.length });
  }

  /**
   * Health check
   */
  async checkHealth() {
    const health = {
      indexing_pipeline: true,
      file_watcher: this.watcher !== undefined,
      processing_loop: this.processingInterval !== undefined,
      queue_status: this.getQueueStatus(),
      stats: this.stats,
      uptime_ms: Date.now() - this.startTime,
      overall: true
    };

    // Check if any critical issues
    if (this.queue.failed.length > 10) {
      health.overall = false;
    }
    
    if (this.queue.pending.length >= this.config.queue.max_queue_size * 0.9) {
      health.overall = false;
    }

    return health;
  }
}

export default DocumentIndexingPipeline;