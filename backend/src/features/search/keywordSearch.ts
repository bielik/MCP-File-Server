import FlexSearch from 'flexsearch';
import { logWithContext } from '../../../utils/logger.js';

/**
 * Keyword Search Service using FlexSearch
 * 
 * This service provides fast, in-memory keyword search across all indexed
 * document content. It maintains a FlexSearch index that is populated
 * during the document indexing process.
 * 
 * Features:
 * - Fast full-text keyword search
 * - Fuzzy matching and typo tolerance
 * - Result ranking and scoring
 * - Multi-language support
 * - Memory-efficient indexing
 */

export interface KeywordSearchResult {
  id: string;
  score: number;
  documentId: string;
  filePath: string;
  textContent: string;
  chunkIndex?: number;
  pageNumber?: number;
  documentTitle?: string;
  highlight?: string;
}

export interface KeywordSearchOptions {
  limit?: number;
  threshold?: number;
  fuzzy?: boolean;
  highlight?: boolean;
  fields?: string[];
}

export interface SearchStats {
  totalDocuments: number;
  totalChunks: number;
  indexSize: number;
  lastUpdated: Date | null;
}

/**
 * Document content for indexing
 */
interface IndexedDocument {
  id: string;
  content: string;
  documentId: string;
  filePath: string;
  chunkIndex?: number;
  pageNumber?: number;
  documentTitle?: string;
  createdAt: string;
}

/**
 * Keyword Search Service Class
 */
export class KeywordSearchService {
  private static instance: KeywordSearchService | null = null;
  private index: FlexSearch.Index | null = null;
  private documents: Map<string, IndexedDocument> = new Map();
  private isInitialized = false;

  private constructor() {
    logWithContext.info('KeywordSearchService: Creating keyword search service instance');
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): KeywordSearchService {
    if (!KeywordSearchService.instance) {
      KeywordSearchService.instance = new KeywordSearchService();
    }
    return KeywordSearchService.instance;
  }

  /**
   * Initialize the keyword search service
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    const startTime = Date.now();

    try {
      logWithContext.info('KeywordSearchService: Initializing FlexSearch index');

      // Create FlexSearch index with optimized configuration
      this.index = new FlexSearch.Index({
        // Use memory-optimized preset
        preset: 'memory',
        
        // Tokenization and language settings
        tokenize: 'forward',
        resolution: 5,
        
        // Enable fuzzy search
        matcher: {
          '^': 'startswith',
          '$': 'endswith',
          '?': 'fuzzy'
        },
        
        // Stemming and case sensitivity
        stemmer: 'en',
        filter: (word: string) => {
          // Filter out very short words and common stop words
          if (word.length < 2) return false;
          
          const stopWords = new Set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 
            'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 
            'would', 'could', 'should', 'may', 'might', 'must', 'can',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 
            'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
          ]);
          
          return !stopWords.has(word.toLowerCase());
        }
      });

      this.isInitialized = true;
      const duration = Date.now() - startTime;

      logWithContext.info('KeywordSearchService: Initialization completed', {
        duration: `${duration}ms`,
        indexType: 'FlexSearch',
        preset: 'memory',
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('KeywordSearchService: Initialization failed', error as Error, {
        duration: `${duration}ms`,
      });

      this.isInitialized = false;
      throw new Error(`Failed to initialize KeywordSearchService: ${(error as Error).message}`);
    }
  }

  /**
   * Add document content to the search index
   */
  public async addDocument(document: IndexedDocument): Promise<void> {
    if (!this.isInitialized || !this.index) {
      await this.initialize();
    }

    if (!this.index) {
      throw new Error('FlexSearch index not initialized');
    }

    const startTime = Date.now();

    try {
      logWithContext.debug('KeywordSearchService: Adding document to index', {
        documentId: document.id,
        contentLength: document.content.length,
        filePath: document.filePath,
      });

      // Add to FlexSearch index
      this.index.add(document.id, document.content);

      // Store document metadata for retrieval
      this.documents.set(document.id, document);

      const duration = Date.now() - startTime;
      logWithContext.debug('KeywordSearchService: Document added successfully', {
        documentId: document.id,
        duration: `${duration}ms`,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('KeywordSearchService: Failed to add document', error as Error, {
        documentId: document.id,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Add multiple documents to the index
   */
  public async addDocuments(documents: IndexedDocument[]): Promise<void> {
    const startTime = Date.now();

    try {
      logWithContext.info('KeywordSearchService: Adding batch of documents', {
        documentCount: documents.length,
      });

      for (const document of documents) {
        await this.addDocument(document);
      }

      const duration = Date.now() - startTime;
      logWithContext.info('KeywordSearchService: Batch indexing completed', {
        documentCount: documents.length,
        duration: `${duration}ms`,
        averageTimePerDoc: `${Math.round(duration / documents.length)}ms`,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('KeywordSearchService: Batch indexing failed', error as Error, {
        documentCount: documents.length,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Search for documents using keywords
   */
  public async search(
    query: string,
    options: KeywordSearchOptions = {}
  ): Promise<KeywordSearchResult[]> {
    if (!this.isInitialized || !this.index) {
      await this.initialize();
    }

    if (!this.index) {
      throw new Error('FlexSearch index not initialized');
    }

    const startTime = Date.now();
    const opts = {
      limit: 10,
      threshold: 0.0, // FlexSearch handles its own scoring
      fuzzy: true,
      highlight: false,
      fields: ['content'],
      ...options,
    };

    try {
      logWithContext.debug('KeywordSearchService: Executing search', {
        query,
        limit: opts.limit,
        fuzzy: opts.fuzzy,
        highlight: opts.highlight,
      });

      // Prepare search query with fuzzy matching if enabled
      const searchQuery = opts.fuzzy && !query.includes('?') ? `${query}?` : query;

      // Execute search
      const searchResults = this.index.search(searchQuery, {
        limit: opts.limit,
      });

      // Convert results to our format
      const results: KeywordSearchResult[] = [];
      
      for (const resultId of searchResults) {
        const document = this.documents.get(String(resultId));
        if (!document) {
          logWithContext.warn('KeywordSearchService: Document not found in cache', {
            resultId,
          });
          continue;
        }

        // Create highlight if requested
        let highlight = '';
        if (opts.highlight) {
          highlight = this.createHighlight(document.content, query);
        }

        results.push({
          id: document.id,
          score: 1.0, // FlexSearch doesn't provide explicit scores, use 1.0
          documentId: document.documentId,
          filePath: document.filePath,
          textContent: document.content,
          chunkIndex: document.chunkIndex,
          pageNumber: document.pageNumber,
          documentTitle: document.documentTitle,
          highlight: highlight || undefined,
        });
      }

      const duration = Date.now() - startTime;
      logWithContext.debug('KeywordSearchService: Search completed', {
        query,
        resultCount: results.length,
        duration: `${duration}ms`,
      });

      return results;

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('KeywordSearchService: Search failed', error as Error, {
        query,
        duration: `${duration}ms`,
      });
      throw error;
    }
  }

  /**
   * Create highlighted text snippet
   */
  private createHighlight(content: string, query: string, contextLength = 150): string {
    const queryWords = query.toLowerCase().split(/\s+/).filter(word => word.length > 0);
    if (queryWords.length === 0) return content.substring(0, contextLength);

    const contentLower = content.toLowerCase();
    
    // Find the first occurrence of any query word
    let firstMatchIndex = -1;
    for (const word of queryWords) {
      const index = contentLower.indexOf(word);
      if (index !== -1 && (firstMatchIndex === -1 || index < firstMatchIndex)) {
        firstMatchIndex = index;
      }
    }

    if (firstMatchIndex === -1) {
      return content.substring(0, contextLength);
    }

    // Calculate context window around the match
    const halfContext = Math.floor(contextLength / 2);
    const startIndex = Math.max(0, firstMatchIndex - halfContext);
    const endIndex = Math.min(content.length, firstMatchIndex + halfContext);

    let highlight = content.substring(startIndex, endIndex);

    // Add ellipsis if content is truncated
    if (startIndex > 0) highlight = '...' + highlight;
    if (endIndex < content.length) highlight = highlight + '...';

    // Highlight query terms (simple replacement)
    for (const word of queryWords) {
      const regex = new RegExp(`\\b${word}\\b`, 'gi');
      highlight = highlight.replace(regex, `**${word}**`);
    }

    return highlight;
  }

  /**
   * Remove document from index
   */
  public async removeDocument(documentId: string): Promise<void> {
    if (!this.isInitialized || !this.index) {
      return;
    }

    try {
      this.index.remove(documentId);
      this.documents.delete(documentId);

      logWithContext.debug('KeywordSearchService: Document removed from index', {
        documentId,
      });
    } catch (error) {
      logWithContext.error('KeywordSearchService: Failed to remove document', error as Error, {
        documentId,
      });
      throw error;
    }
  }

  /**
   * Clear all documents from index
   */
  public async clear(): Promise<void> {
    if (!this.isInitialized || !this.index) {
      return;
    }

    try {
      // FlexSearch doesn't have a clear method, so we reinitialize
      await this.initialize();
      this.documents.clear();

      logWithContext.info('KeywordSearchService: Index cleared');
    } catch (error) {
      logWithContext.error('KeywordSearchService: Failed to clear index', error as Error);
      throw error;
    }
  }

  /**
   * Get search statistics
   */
  public getStats(): SearchStats {
    return {
      totalDocuments: this.documents.size,
      totalChunks: this.documents.size, // In our case, each document is a chunk
      indexSize: this.documents.size,
      lastUpdated: this.documents.size > 0 ? new Date() : null,
    };
  }

  /**
   * Check if service is ready
   */
  public isReady(): boolean {
    return this.isInitialized && this.index !== null;
  }

  /**
   * Get service status
   */
  public getStatus(): {
    initialized: boolean;
    documentsIndexed: number;
    ready: boolean;
  } {
    return {
      initialized: this.isInitialized,
      documentsIndexed: this.documents.size,
      ready: this.isReady(),
    };
  }
}

// Export singleton instance
export const keywordSearchService = KeywordSearchService.getInstance();