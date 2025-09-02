// Core type definitions for MCP Research File Server

// File Management Types
export interface FilePermissionMatrix {
  contextFolders: string[];     // Read-only reference materials
  workingFolders: string[];     // Read/write proposal sections
  outputFolder: string;         // Agent creation zone with subfolder rights
}

export interface FileMetadata {
  id: string;
  path: string;
  filename: string;
  size: number;
  created: Date;
  modified: Date;
  type: string;
  permissions: FilePermission;
  language?: string;            // Auto-detected language
  category?: FileCategory;      // Document categorization
  tags?: string[];             // User-defined or auto-generated tags
}

export type FilePermission = 'context' | 'working' | 'output';

export type FileCategory = 
  | 'context'
  | 'working' 
  | 'output'
  | 'methodology'
  | 'literature'
  | 'budget'
  | 'timeline'
  | 'introduction'
  | 'conclusion'
  | 'other';

// Multimodal Content Types
export interface MultimodalChunk {
  id: string;
  documentId: string;
  content: string | ImageData;
  embedding: Float32Array;
  modality: 'text' | 'image';
  metadata: ChunkMetadata;
}

export interface ChunkMetadata {
  pageNumber?: number;
  section?: string;
  sectionType?: string;
  language?: string;
  imageCaption?: string;        // If available
  boundingBox?: BoundingBox;    // For image location in PDF
  startPosition?: number;       // Text chunk start
  endPosition?: number;         // Text chunk end
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ImageData {
  data: Buffer;
  format: 'png' | 'jpg' | 'jpeg' | 'gif' | 'webp';
  width: number;
  height: number;
  caption?: string;
}

// Search Types
export interface SearchResult {
  id: string;
  documentId: string;
  title: string;
  snippet: string;
  relevanceScore: number;
  modality: 'text' | 'image';
  source: 'keyword' | 'semantic' | 'multimodal';
  metadata: SearchResultMetadata;
}

export interface SearchResultMetadata {
  path: string;
  pageNumber?: number;
  section?: string;
  imageUrl?: string;           // For image results
  matchedKeywords?: string[];  // For keyword search
  similarity?: number;         // For semantic search
}

export interface SearchOptions {
  maxResults?: number;
  fileCategories?: FileCategory[];
  modalities?: ('text' | 'image')[];
  languages?: string[];
  includeImages?: boolean;
}

// MCP Tool Schemas
export interface MCPToolResult {
  success: boolean;
  data?: unknown;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface FileOperationResult extends MCPToolResult {
  data?: {
    content?: string;
    metadata?: FileMetadata;
    created?: boolean;
    modified?: boolean;
  };
}

export interface SearchToolResult extends MCPToolResult {
  data?: {
    results: SearchResult[];
    totalCount: number;
    searchTime: number;
    query: string;
    strategy: 'keyword' | 'semantic' | 'multimodal';
  };
}

// Document Processing Types
export interface DocumentProcessingJob {
  id: string;
  filePath: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  startTime: Date;
  endTime?: Date;
  error?: string;
  progress?: {
    totalPages?: number;
    processedPages: number;
    extractedImages: number;
    generatedChunks: number;
  };
}

export interface ProcessingConfig {
  maxFileSize: number;         // In bytes
  maxPages: number;            // For PDFs
  chunkSize: number;           // In tokens
  chunkOverlap: number;        // In tokens
  enableImageExtraction: boolean;
  supportedLanguages: string[];
  embeddingModel: string;
}

// Configuration Types
export interface ServerConfig {
  mcpPort: number;
  webUIPort: number;
  host: string;
  enableCaching: boolean;
  cacheTTL: number;            // In seconds
  maxConcurrentProcessing: number;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  logFile: string;
}

export interface QdrantConfig {
  url: string;
  apiKey?: string;
  collectionPrefix: string;
  embeddingDimension: number;
}

export interface MCLIPConfig {
  modelName: string;
  cacheDir: string;
  embeddingDimension: number;
}

// Web UI Types
export interface UIState {
  currentView: 'explorer' | 'list';
  selectedFiles: string[];
  filters: {
    permissions: FilePermission[];
    fileTypes: string[];
    categories: FileCategory[];
    dateRange?: {
      start: Date;
      end: Date;
    };
  };
  sorting: {
    field: 'name' | 'type' | 'size' | 'modified' | 'permissions';
    direction: 'asc' | 'desc';
  };
}

export interface FolderTreeNode {
  id: string;
  name: string;
  path: string;
  type: 'folder' | 'file';
  permission: FilePermission;
  children?: FolderTreeNode[];
  expanded?: boolean;
}

// Error Types
export class MCPServerError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number
  ) {
    super(message);
    this.name = 'MCPServerError';
  }
}

export class FilePermissionError extends MCPServerError {
  constructor(message: string, public filePath: string) {
    super(message, 'FILE_PERMISSION_ERROR', 403);
  }
}

export class DocumentProcessingError extends MCPServerError {
  constructor(message: string, public filePath: string) {
    super(message, 'DOCUMENT_PROCESSING_ERROR', 500);
  }
}

export class SearchError extends MCPServerError {
  constructor(message: string, public query: string) {
    super(message, 'SEARCH_ERROR', 500);
  }
}

// Utility Types
export type AsyncReturnType<T extends (...args: unknown[]) => Promise<unknown>> = 
  T extends (...args: unknown[]) => Promise<infer R> ? R : never;

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;