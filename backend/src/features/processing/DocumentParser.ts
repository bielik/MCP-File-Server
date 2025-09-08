import fs from 'fs/promises';
import path from 'path';
import { spawn } from 'child_process';
import { promisify } from 'util';
import pdfParse from 'pdf-parse';
import { config } from '../../../config/index.js';
import { logWithContext } from '../../../utils/logger.js';
import { validatePrerequisitesForStartup } from '../../../../scripts/check-prerequisites.js';

/**
 * Native Document Parser for PDF Processing
 * 
 * This service replaces the Python-based Docling microservice with a native
 * TypeScript implementation. It provides robust PDF parsing with both text
 * and image extraction capabilities.
 * 
 * Features:
 * - Text extraction using pdf-parse library
 * - Image extraction using Poppler's pdfimages utility
 * - Structured logging for monitoring and debugging
 * - Automatic prerequisite validation
 * - Proper error handling and cleanup
 * 
 * Dependencies:
 * - pdf-parse: Node.js PDF text extraction
 * - Poppler (pdfimages): External utility for robust image extraction
 */

export interface DocumentMetadata {
  title?: string;
  author?: string;
  subject?: string;
  creator?: string;
  producer?: string;
  creationDate?: Date;
  modificationDate?: Date;
  pageCount: number;
  fileSize: number;
  fileName: string;
  filePath: string;
}

export interface ExtractedImage {
  fileName: string;
  format: string;
  width?: number;
  height?: number;
  buffer: Buffer;
  pageNumber?: number;
}

export interface ParsedDocument {
  text: string;
  images: ExtractedImage[];
  metadata: DocumentMetadata;
  processingTime: number;
  textChunks?: string[];
}

export interface ParsingOptions {
  extractImages?: boolean;
  maxPages?: number;
  tempDir?: string;
  cleanupTemp?: boolean;
  chunkText?: boolean;
  chunkSize?: number;
  chunkOverlap?: number;
}

/**
 * Execute external command with proper error handling
 */
async function executeCommand(
  command: string,
  args: string[],
  options: { timeout?: number; cwd?: string } = {}
): Promise<{ stdout: string; stderr: string; code: number | null }> {
  return new Promise((resolve, reject) => {
    const { timeout = 30000, cwd } = options;
    
    const child = spawn(command, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: true,
      cwd,
    });

    let stdout = '';
    let stderr = '';

    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error(`Command timeout after ${timeout}ms`));
    }, timeout);

    child.stdout?.on('data', (data) => {
      stdout += data.toString();
    });

    child.stderr?.on('data', (data) => {
      stderr += data.toString();
    });

    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({ stdout, stderr, code });
    });

    child.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
}

/**
 * Document Parser Class
 */
export class DocumentParser {
  private static instance: DocumentParser | null = null;
  private isInitialized = false;

  private constructor() {
    logWithContext.info('DocumentParser: Creating document parser instance');
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): DocumentParser {
    if (!DocumentParser.instance) {
      DocumentParser.instance = new DocumentParser();
    }
    return DocumentParser.instance;
  }

  /**
   * Initialize the document parser
   * Validates prerequisites and sets up environment
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    const startTime = Date.now();

    try {
      logWithContext.info('DocumentParser: Initializing document parser');

      // Validate prerequisites (Poppler/pdfimages)
      logWithContext.debug('DocumentParser: Validating prerequisites');
      await validatePrerequisitesForStartup();

      this.isInitialized = true;
      const duration = Date.now() - startTime;

      logWithContext.info('DocumentParser: Initialization completed', {
        duration: `${duration}ms`,
        maxPages: config.processing.maxPages,
        imageExtraction: config.processing.enableImageExtraction,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('DocumentParser: Initialization failed', error as Error, {
        duration: `${duration}ms`,
      });

      this.isInitialized = false;
      throw new Error(`Failed to initialize DocumentParser: ${(error as Error).message}`);
    }
  }

  /**
   * Parse a PDF file and extract text and images
   */
  public async parseDocument(
    filePath: string,
    options: ParsingOptions = {}
  ): Promise<ParsedDocument> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const startTime = Date.now();
    const fileName = path.basename(filePath);

    // Set default options
    const opts: Required<ParsingOptions> = {
      extractImages: config.processing.enableImageExtraction,
      maxPages: config.processing.maxPages,
      tempDir: path.join(process.cwd(), 'temp', `pdf_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`),
      cleanupTemp: true,
      chunkText: true,
      chunkSize: config.processing.chunkSize,
      chunkOverlap: config.processing.chunkOverlap,
      ...options,
    };

    let tempDirCreated = false;

    try {
      logWithContext.info('DocumentParser: Starting document parsing', {
        fileName,
        filePath,
        extractImages: opts.extractImages,
        maxPages: opts.maxPages,
      });

      // Create temporary directory for image extraction
      if (opts.extractImages) {
        await fs.mkdir(opts.tempDir, { recursive: true });
        tempDirCreated = true;
        logWithContext.debug('DocumentParser: Created temporary directory', {
          tempDir: opts.tempDir,
        });
      }

      // Read PDF file
      const pdfBuffer = await fs.readFile(filePath);
      const fileStats = await fs.stat(filePath);

      logWithContext.debug('DocumentParser: PDF file loaded', {
        fileSize: fileStats.size,
        fileName,
      });

      // Extract text using pdf-parse
      logWithContext.debug('DocumentParser: Extracting text content');
      const pdfData = await pdfParse(pdfBuffer, {
        max: opts.maxPages,
      });

      // Extract images using pdfimages if enabled
      let images: ExtractedImage[] = [];
      if (opts.extractImages) {
        logWithContext.debug('DocumentParser: Extracting images');
        images = await this.extractImages(filePath, opts.tempDir, opts.maxPages);
      }

      // Prepare metadata
      const metadata: DocumentMetadata = {
        title: pdfData.info?.Title,
        author: pdfData.info?.Author,
        subject: pdfData.info?.Subject,
        creator: pdfData.info?.Creator,
        producer: pdfData.info?.Producer,
        creationDate: pdfData.info?.CreationDate,
        modificationDate: pdfData.info?.ModDate,
        pageCount: pdfData.numpages,
        fileSize: fileStats.size,
        fileName,
        filePath,
      };

      // Chunk text if enabled
      let textChunks: string[] | undefined;
      if (opts.chunkText && pdfData.text) {
        textChunks = this.chunkText(pdfData.text, opts.chunkSize, opts.chunkOverlap);
      }

      const processingTime = Date.now() - startTime;

      const result: ParsedDocument = {
        text: pdfData.text,
        images,
        metadata,
        processingTime,
        textChunks,
      };

      logWithContext.info('DocumentParser: Document parsing completed', {
        fileName,
        pageCount: metadata.pageCount,
        textLength: pdfData.text.length,
        imageCount: images.length,
        chunkCount: textChunks?.length || 0,
        processingTime: `${processingTime}ms`,
      });

      return result;

    } catch (error) {
      const processingTime = Date.now() - startTime;
      logWithContext.error('DocumentParser: Document parsing failed', error as Error, {
        fileName,
        filePath,
        processingTime: `${processingTime}ms`,
      });

      throw new Error(`Failed to parse document ${fileName}: ${(error as Error).message}`);
    } finally {
      // Cleanup temporary directory
      if (tempDirCreated && opts.cleanupTemp) {
        try {
          await fs.rmdir(opts.tempDir, { recursive: true });
          logWithContext.debug('DocumentParser: Cleaned up temporary directory', {
            tempDir: opts.tempDir,
          });
        } catch (cleanupError) {
          logWithContext.warn('DocumentParser: Failed to cleanup temporary directory', cleanupError as Error, {
            tempDir: opts.tempDir,
          });
        }
      }
    }
  }

  /**
   * Extract images from PDF using pdfimages utility
   */
  private async extractImages(
    pdfPath: string,
    tempDir: string,
    maxPages?: number
  ): Promise<ExtractedImage[]> {
    const startTime = Date.now();

    try {
      // Build pdfimages command
      const args = [
        '-j', // Extract JPEG images
        '-jp2', // Extract JPEG2000 images
        '-png', // Extract PNG images
        '-all', // Extract all image formats
      ];

      // Add page range if specified
      if (maxPages && maxPages > 0) {
        args.push('-f', '1', '-l', maxPages.toString());
      }

      args.push(pdfPath, path.join(tempDir, 'img'));

      logWithContext.debug('DocumentParser: Executing pdfimages command', {
        args: args.join(' '),
        tempDir,
      });

      // Execute pdfimages command
      const { stdout, stderr, code } = await executeCommand('pdfimages', args, {
        timeout: 60000, // 60 second timeout for image extraction
        cwd: tempDir,
      });

      if (code !== 0) {
        throw new Error(`pdfimages failed with code ${code}: ${stderr}`);
      }

      // Read extracted image files
      const imageFiles = await fs.readdir(tempDir);
      const images: ExtractedImage[] = [];

      for (const fileName of imageFiles) {
        if (!fileName.startsWith('img-')) continue;

        const filePath = path.join(tempDir, fileName);
        const buffer = await fs.readFile(filePath);
        const format = path.extname(fileName).substring(1).toLowerCase();

        images.push({
          fileName,
          format,
          buffer,
          // Could extract width/height using image libraries if needed
        });
      }

      const duration = Date.now() - startTime;
      logWithContext.debug('DocumentParser: Image extraction completed', {
        imageCount: images.length,
        duration: `${duration}ms`,
      });

      return images;

    } catch (error) {
      const duration = Date.now() - startTime;
      logWithContext.error('DocumentParser: Image extraction failed', error as Error, {
        pdfPath,
        duration: `${duration}ms`,
      });

      // Return empty array rather than failing entire parsing
      logWithContext.warn('DocumentParser: Continuing without images due to extraction failure');
      return [];
    }
  }

  /**
   * Chunk text into smaller segments for processing
   */
  private chunkText(
    text: string,
    chunkSize: number,
    chunkOverlap: number
  ): string[] {
    if (!text || text.trim().length === 0) {
      return [];
    }

    const chunks: string[] = [];
    const words = text.split(/\s+/);
    let currentChunk: string[] = [];
    let currentLength = 0;

    for (const word of words) {
      const wordLength = word.length + 1; // +1 for space

      if (currentLength + wordLength > chunkSize && currentChunk.length > 0) {
        // Create chunk from current words
        chunks.push(currentChunk.join(' '));

        // Start new chunk with overlap
        const overlapWords = Math.min(chunkOverlap, currentChunk.length);
        currentChunk = currentChunk.slice(-overlapWords);
        currentLength = currentChunk.join(' ').length;
      }

      currentChunk.push(word);
      currentLength += wordLength;
    }

    // Add final chunk if it has content
    if (currentChunk.length > 0) {
      chunks.push(currentChunk.join(' '));
    }

    logWithContext.debug('DocumentParser: Text chunking completed', {
      originalLength: text.length,
      chunkCount: chunks.length,
      chunkSize,
      chunkOverlap,
    });

    return chunks;
  }

  /**
   * Check if the parser is ready
   */
  public isReady(): boolean {
    return this.isInitialized;
  }

  /**
   * Get parser status
   */
  public getStatus(): {
    initialized: boolean;
    maxPages: number;
    imageExtraction: boolean;
    chunkSize: number;
  } {
    return {
      initialized: this.isInitialized,
      maxPages: config.processing.maxPages,
      imageExtraction: config.processing.enableImageExtraction,
      chunkSize: config.processing.chunkSize,
    };
  }
}

// Export singleton instance
export const documentParser = DocumentParser.getInstance();