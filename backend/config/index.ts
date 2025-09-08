import { config as dotenvConfig } from 'dotenv';
import { z } from 'zod';
import path from 'path';
import {
  ServerConfig,
  QdrantConfig,
  MCLIPConfig,
  ProcessingConfig,
  FilePermissionMatrix,
} from '../types/index.ts';

// Load environment variables from root directory
dotenvConfig({ path: path.resolve(process.cwd(), '.env') });

// Environment validation schema
const envSchema = z.object({
  // Server Configuration
  MCP_PORT: z.string().transform(Number).pipe(z.number().min(1000).max(65535)).default('3000'),
  MCP_HOST: z.string().default('localhost'),
  WEB_UI_PORT: z.string().transform(Number).pipe(z.number().min(1000).max(65535)).default('3001'),

  // File System
  CONTEXT_FOLDERS: z.string().default(''),
  WORKING_FOLDERS: z.string().default(''),
  OUTPUT_FOLDER: z.string().default('./output'),
  MAX_FILE_SIZE: z.string().transform(Number).pipe(z.number().positive()).default('52428800'), // 50MB
  MAX_FILES_PER_DIRECTORY: z.string().transform(Number).pipe(z.number().positive()).default('5000'),

  // Qdrant
  QDRANT_URL: z.string().url().default('http://localhost:6333'),
  QDRANT_COLLECTION_PREFIX: z.string().default('research_mcp'),
  QDRANT_API_KEY: z.string().optional(),

  // M-CLIP
  MCLIP_MODEL_NAME: z.string().default('sentence-transformers/clip-ViT-B-32-multilingual-v1'),
  MCLIP_CACHE_DIR: z.string().default('./models/mclip'),
  EMBEDDING_DIMENSION: z.string().transform(Number).pipe(z.number().positive()).default('512'),

  // Document Processing
  DOCLING_MAX_PAGES: z.string().transform(Number).pipe(z.number().positive()).default('500'),
  IMAGE_EXTRACTION: z.string().transform(val => val.toLowerCase() === 'true').default('true'),
  LANGUAGES: z.string().default('en,de,fr,es,it'),
  CHUNK_SIZE: z.string().transform(Number).pipe(z.number().positive()).default('800'),
  CHUNK_OVERLAP: z.string().transform(Number).pipe(z.number().min(0)).default('50'),

  // Performance
  ENABLE_CACHING: z.string().transform(val => val.toLowerCase() === 'true').default('true'),
  CACHE_TTL: z.string().transform(Number).pipe(z.number().positive()).default('3600'),
  MAX_CONCURRENT_PROCESSING: z.string().transform(Number).pipe(z.number().positive()).default('4'),

  // Logging
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  LOG_FILE: z.string().default('logs/mcp-research-server.log'),
});

// Parse and validate environment variables
const env = envSchema.parse(process.env);

// Configuration builders
export const serverConfig: ServerConfig = {
  mcpPort: env.MCP_PORT,
  webUIPort: env.WEB_UI_PORT,
  host: env.MCP_HOST,
  enableCaching: env.ENABLE_CACHING,
  cacheTTL: env.CACHE_TTL,
  maxConcurrentProcessing: env.MAX_CONCURRENT_PROCESSING,
  logLevel: env.LOG_LEVEL,
  logFile: env.LOG_FILE,
};

export const qdrantConfig: QdrantConfig = {
  url: env.QDRANT_URL,
  ...(env.QDRANT_API_KEY ? { apiKey: env.QDRANT_API_KEY } : {}),
  collectionPrefix: env.QDRANT_COLLECTION_PREFIX,
  embeddingDimension: env.EMBEDDING_DIMENSION,
};

export const mclipConfig: MCLIPConfig = {
  modelName: env.MCLIP_MODEL_NAME,
  cacheDir: env.MCLIP_CACHE_DIR,
  embeddingDimension: env.EMBEDDING_DIMENSION,
};

export const processingConfig: ProcessingConfig = {
  maxFileSize: env.MAX_FILE_SIZE,
  maxPages: env.DOCLING_MAX_PAGES,
  chunkSize: env.CHUNK_SIZE,
  chunkOverlap: env.CHUNK_OVERLAP,
  enableImageExtraction: env.IMAGE_EXTRACTION,
  supportedLanguages: env.LANGUAGES.split(',').map(lang => lang.trim()),
  embeddingModel: env.MCLIP_MODEL_NAME,
};

export const filePermissionMatrix: FilePermissionMatrix = {
  contextFolders: env.CONTEXT_FOLDERS
    ? env.CONTEXT_FOLDERS.split(',').map(folder => folder.trim())
    : [],
  workingFolders: env.WORKING_FOLDERS
    ? env.WORKING_FOLDERS.split(',').map(folder => folder.trim())
    : [],
  outputFolder: env.OUTPUT_FOLDER,
};

// Utility functions
export function getAbsolutePath(relativePath: string): string {
  return path.resolve(process.cwd(), relativePath);
}

export function validateDirectories(): void {
  const allFolders = [
    ...filePermissionMatrix.contextFolders,
    ...filePermissionMatrix.workingFolders,
    filePermissionMatrix.outputFolder,
  ];

  // Create log directory if it doesn't exist
  const logDir = path.dirname(getAbsolutePath(serverConfig.logFile));
  try {
    import('fs').then(fs => {
      if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
      }
    });
  } catch (error) {
    console.warn(`Warning: Could not create log directory ${logDir}:`, error);
  }

  // Create model cache directory if it doesn't exist
  const modelDir = getAbsolutePath(mclipConfig.cacheDir);
  try {
    import('fs').then(fs => {
      if (!fs.existsSync(modelDir)) {
        fs.mkdirSync(modelDir, { recursive: true });
      }
    });
  } catch (error) {
    console.warn(`Warning: Could not create model cache directory ${modelDir}:`, error);
  }

  // Validate that configured folders exist (warn if they don't)
  allFolders.forEach(folder => {
    if (folder) {
      const absolutePath = getAbsolutePath(folder);
      import('fs').then(fs => {
        if (!fs.existsSync(absolutePath)) {
          console.warn(`Warning: Configured folder does not exist: ${absolutePath}`);
        }
      });
    }
  });
}

// Configuration validation
export function validateConfiguration(): void {
  // Validate that required configurations are present
  if (filePermissionMatrix.contextFolders.length === 0 && 
      filePermissionMatrix.workingFolders.length === 0) {
    console.warn('Warning: No context or working folders configured. The system will have limited functionality.');
  }

  if (!filePermissionMatrix.outputFolder) {
    throw new Error('OUTPUT_FOLDER must be configured for agent file creation');
  }

  // Validate processing configuration
  if (processingConfig.chunkOverlap >= processingConfig.chunkSize) {
    throw new Error('CHUNK_OVERLAP must be less than CHUNK_SIZE');
  }

  if (processingConfig.supportedLanguages.length === 0) {
    throw new Error('At least one language must be configured in LANGUAGES');
  }

  validateDirectories();
}

// Development helpers
export const isDevelopment = process.env.NODE_ENV === 'development';
export const isProduction = process.env.NODE_ENV === 'production';
export const isTest = process.env.NODE_ENV === 'test';

// Export all configurations
export const config = {
  server: serverConfig,
  qdrant: qdrantConfig,
  mclip: mclipConfig,
  processing: processingConfig,
  filePermissions: filePermissionMatrix,
  isDevelopment,
  isProduction,
  isTest,
};

export default config;