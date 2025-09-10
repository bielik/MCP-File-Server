import fs from 'fs/promises';
import path from 'path';
import { createReadStream, createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import mime from 'mime-types';
import { FileMetadata, FilePermission, FileCategory, MCPServerError } from '../types/index.js';
import { filePermissionMatrix, getAbsolutePath } from '../config/index.js';
import { logFileOperation } from './logger.js';

// Path validation and security
export function validatePath(filePath: string): string {
  // Resolve to absolute path
  const absolutePath = getAbsolutePath(filePath);
  
  // Check for directory traversal attempts
  const normalizedPath = path.normalize(absolutePath);
  if (normalizedPath.includes('..')) {
    throw new MCPServerError(
      `Invalid path: directory traversal detected in ${filePath}`,
      'INVALID_PATH'
    );
  }
  
  return normalizedPath;
}

export function isPathInAllowedDirectory(filePath: string): { allowed: boolean; permission: FilePermission } {
  // Import here to avoid circular dependency
  const { filePermissionManager } = require('../files/permissions.js');
  return filePermissionManager.getFilePermission(filePath);
}

export function requirePermission(filePath: string, requiredPermission: 'read' | 'write'): void {
  // Import here to avoid circular dependency
  const { filePermissionManager } = require('@/files/permissions.js');
  
  const operation = requiredPermission === 'read' ? 'read' : 'write';
  filePermissionManager.checkOperationPermission(filePath, operation);
}

// File metadata extraction
export async function getFileMetadata(filePath: string): Promise<FileMetadata> {
  const absolutePath = validatePath(filePath);
  const stats = await fs.stat(absolutePath);
  const { permission } = isPathInAllowedDirectory(absolutePath);
  
  const metadata: FileMetadata = {
    id: generateFileId(absolutePath),
    path: absolutePath,
    filename: path.basename(absolutePath),
    size: stats.size,
    created: stats.birthtime,
    modified: stats.mtime,
    type: mime.lookup(absolutePath) || 'application/octet-stream',
    permissions: permission,
  };
  
  // Detect file category based on path and content
  metadata.category = await detectFileCategory(absolutePath);
  
  return metadata;
}

function generateFileId(filePath: string): string {
  // Simple hash-based ID generation
  const crypto = require('crypto');
  return crypto.createHash('md5').update(filePath).digest('hex');
}

async function detectFileCategory(filePath: string): Promise<FileCategory> {
  const filename = path.basename(filePath).toLowerCase();
  const extension = path.extname(filename);
  
  // Category detection based on filename patterns
  if (filename.includes('method') || filename.includes('approach')) {
    return 'methodology';
  }
  
  if (filename.includes('literature') || filename.includes('review') || filename.includes('bibliography')) {
    return 'literature';
  }
  
  if (filename.includes('budget') || filename.includes('cost') || filename.includes('financial')) {
    return 'budget';
  }
  
  if (filename.includes('timeline') || filename.includes('schedule') || filename.includes('gantt')) {
    return 'timeline';
  }
  
  if (filename.includes('introduction') || filename.includes('intro')) {
    return 'introduction';
  }
  
  if (filename.includes('conclusion') || filename.includes('summary') || filename.includes('end')) {
    return 'conclusion';
  }
  
  // Determine by directory
  const { permission } = isPathInAllowedDirectory(filePath);
  if (permission === 'read-only') return 'context';
  if (permission === 'read-write') return 'working';
  if (permission === 'agent-controlled') return 'output';
  
  return 'other';
}

// File operations
export async function readFileContent(filePath: string): Promise<string> {
  requirePermission(filePath, 'read');
  const absolutePath = validatePath(filePath);
  
  try {
    const content = await fs.readFile(absolutePath, 'utf-8');
    logFileOperation('read', absolutePath, true);
    return content;
  } catch (error) {
    logFileOperation('read', absolutePath, false, undefined, (error as Error).message);
    throw new MCPServerError(
      `Failed to read file: ${(error as Error).message}`,
      'FILE_READ_ERROR'
    );
  }
}

export async function writeFileContent(filePath: string, content: string): Promise<void> {
  requirePermission(filePath, 'write');
  const absolutePath = validatePath(filePath);
  
  // Ensure directory exists
  await ensureDirectoryExists(path.dirname(absolutePath));
  
  try {
    await fs.writeFile(absolutePath, content, 'utf-8');
    logFileOperation('write', absolutePath, true);
  } catch (error) {
    logFileOperation('write', absolutePath, false, undefined, (error as Error).message);
    throw new MCPServerError(
      `Failed to write file: ${(error as Error).message}`,
      'FILE_WRITE_ERROR'
    );
  }
}

export async function createFile(filePath: string, content: string, createDirectories = true): Promise<void> {
  const absolutePath = validatePath(filePath);
  
  // For file creation, we need to be in the output directory or have write permission
  const { allowed, permission } = isPathInAllowedDirectory(absolutePath);
  
  if (!allowed) {
    throw new MCPServerError(
      `Cannot create file: ${filePath} is not in an allowed directory`,
      'CREATE_PERMISSION_DENIED',
      403
    );
  }
  
  if (permission === 'read-only') {
    throw new MCPServerError(
      `Cannot create file: ${filePath} is in a read-only directory`,
      'CREATE_PERMISSION_DENIED',
      403
    );
  }
  
  if (createDirectories) {
    await ensureDirectoryExists(path.dirname(absolutePath));
  }
  
  // Check if file already exists
  try {
    await fs.access(absolutePath);
    throw new MCPServerError(
      `File already exists: ${filePath}`,
      'FILE_EXISTS'
    );
  } catch (error) {
    // File doesn't exist, which is what we want
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
      throw error;
    }
  }
  
  try {
    await fs.writeFile(absolutePath, content, 'utf-8');
    logFileOperation('create', absolutePath, true);
  } catch (error) {
    logFileOperation('create', absolutePath, false, undefined, (error as Error).message);
    throw new MCPServerError(
      `Failed to create file: ${(error as Error).message}`,
      'FILE_CREATE_ERROR'
    );
  }
}

export async function ensureDirectoryExists(dirPath: string): Promise<void> {
  const absolutePath = validatePath(dirPath);
  
  try {
    await fs.mkdir(absolutePath, { recursive: true });
  } catch (error) {
    throw new MCPServerError(
      `Failed to create directory: ${(error as Error).message}`,
      'DIRECTORY_CREATE_ERROR'
    );
  }
}

export async function listFiles(
  directoryPath: string,
  recursive = false,
  filter?: (file: FileMetadata) => boolean
): Promise<FileMetadata[]> {
  requirePermission(directoryPath, 'read');
  const absolutePath = validatePath(directoryPath);
  
  const files: FileMetadata[] = [];
  
  async function scanDirectory(dir: string): Promise<void> {
    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const entryPath = path.join(dir, entry.name);
        
        if (entry.isFile()) {
          try {
            const metadata = await getFileMetadata(entryPath);
            if (!filter || filter(metadata)) {
              files.push(metadata);
            }
          } catch (error) {
            // Skip files we can't read
            console.warn(`Skipping file ${entryPath}: ${(error as Error).message}`);
          }
        } else if (entry.isDirectory() && recursive) {
          await scanDirectory(entryPath);
        }
      }
    } catch (error) {
      throw new MCPServerError(
        `Failed to list directory: ${(error as Error).message}`,
        'DIRECTORY_LIST_ERROR'
      );
    }
  }
  
  await scanDirectory(absolutePath);
  return files;
}

// Folder structure helpers for agents
export async function getFolderStructure(basePath: string): Promise<any> {
  const absolutePath = validatePath(basePath);
  const { allowed } = isPathInAllowedDirectory(absolutePath);
  
  if (!allowed) {
    throw new MCPServerError(
      `Access denied: ${basePath} is not in an allowed directory`,
      'ACCESS_DENIED',
      403
    );
  }
  
  async function buildTree(dirPath: string): Promise<any> {
    const stats = await fs.stat(dirPath);
    const name = path.basename(dirPath);
    
    if (stats.isFile()) {
      return {
        name,
        type: 'file',
        path: path.relative(absolutePath, dirPath) || name,
      };
    }
    
    if (stats.isDirectory()) {
      const entries = await fs.readdir(dirPath, { withFileTypes: true });
      const children = [];
      
      for (const entry of entries) {
        const entryPath = path.join(dirPath, entry.name);
        try {
          const child = await buildTree(entryPath);
          children.push(child);
        } catch (error) {
          // Skip inaccessible entries
          continue;
        }
      }
      
      return {
        name,
        type: 'directory',
        path: path.relative(absolutePath, dirPath) || '.',
        children: children.sort((a, b) => {
          // Directories first, then files, both alphabetically
          if (a.type !== b.type) {
            return a.type === 'directory' ? -1 : 1;
          }
          return a.name.localeCompare(b.name);
        }),
      };
    }
  }
  
  return buildTree(absolutePath);
}

// File type detection
export function getFileType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  
  const typeMap: Record<string, string> = {
    '.md': 'markdown',
    '.txt': 'text',
    '.pdf': 'pdf',
    '.doc': 'document',
    '.docx': 'document',
    '.xls': 'spreadsheet',
    '.xlsx': 'spreadsheet',
    '.ppt': 'presentation',
    '.pptx': 'presentation',
    '.jpg': 'image',
    '.jpeg': 'image',
    '.png': 'image',
    '.gif': 'image',
    '.svg': 'image',
    '.json': 'data',
    '.csv': 'data',
    '.xml': 'data',
  };
  
  return typeMap[ext] || 'other';
}

// Filesystem browsing utilities (shared between web-server and filesystem router)
import os from 'os';

/**
 * Validates and sanitizes a path for filesystem browsing to prevent directory traversal and access to system folders.
 * @param requestedPath The path to validate.
 * @returns A normalized, absolute path.
 */
export const validateAndSanitizePath = async (requestedPath: string): Promise<string> => {
    if (!requestedPath || requestedPath === '') {
      return os.homedir();
    }
    const resolvedPath = path.resolve(requestedPath);
    const normalizedPath = path.normalize(resolvedPath);

    if (normalizedPath.includes('..')) {
      throw new Error('Directory traversal not allowed');
    }

    if (process.platform === 'win32') {
      const systemDirs = ['C:\\Windows', 'C:\\System32', 'C:\\Program Files'];
      if (systemDirs.some(sysDir => normalizedPath.startsWith(sysDir))) {
        throw new Error('Access to system directories not allowed');
      }
    } else {
      const systemDirs = ['/etc', '/proc', '/sys', '/dev', '/boot'];
      if (systemDirs.some(sysDir => normalizedPath.startsWith(sysDir))) {
        throw new Error('Access to system directories not allowed');
      }
    }
    return normalizedPath;
};

/**
 * Checks if a directory entry is generally accessible and not a system or hidden file.
 * @param entryName The name of the file or directory.
 * @param fullPath The full path to the entry.
 * @returns True if the directory is accessible.
 */
export const isAccessibleDirectory = (entryName: string, fullPath: string): boolean => {
  if (entryName.startsWith('.') || entryName.startsWith('NTUSER') || entryName.includes('regtrans-ms')) {
    return false;
  }
  const windowsSystemDirs = ['AppData', 'Application Data', 'Local Settings', 'NetHood', 'PrintHood', 'SendTo', 'Start Menu', 'Templates', 'Recent', 'Cookies', 'Favorites', 'My Music', 'My Pictures', 'My Videos', 'My Documents'];
  if (windowsSystemDirs.includes(entryName)) {
    return false;
  }
  const problematicDirs = ['ntuser.dat.LOG1', 'ntuser.dat.LOG2', 'ntuser.ini', 'Tracing', 'Saved Games', 'Searches'];
  if (problematicDirs.some(dir => entryName.toLowerCase().includes(dir.toLowerCase()))) {
    return false;
  }
  const userProfile = process.env.USERPROFILE || '';
  if (fullPath.startsWith(userProfile)) {
    const commonUserDirs = ['Documents', 'Downloads', 'Desktop', 'Pictures', 'Music', 'Videos', 'OneDrive', 'Dropbox', 'Google Drive', 'iCloud Drive'];
    const isCommonDir = commonUserDirs.some(dir => entryName === dir || entryName.startsWith(dir + ' ') || entryName.startsWith(dir + '-'));
    if (isCommonDir) {
      return true;
    }
    return !entryName.startsWith('NTUSER') && !entryName.includes('.dat') && !entryName.includes('.log');
  }
  return true;
};

/**
 * Determines if a path points to a directory or a symbolic link pointing to a directory.
 * @param path The path to check.
 * @returns An object indicating if it's a directory and its stats.
 */
export const isDirectoryOrJunction = async (path: string): Promise<{ isDirectory: boolean; stats: any }> => {
  try {
    const stats = await fs.lstat(path);
    let isDirectory = stats.isDirectory();
    if (!isDirectory && stats.isSymbolicLink()) {
      try {
        const realStats = await fs.stat(path);
        isDirectory = realStats.isDirectory();
      } catch {
        isDirectory = false;
      }
    }
    return { isDirectory, stats };
  } catch (error) {
    return { isDirectory: false, stats: null };
  }
};

// Export utility functions
export default {
  validatePath,
  isPathInAllowedDirectory,
  requirePermission,
  getFileMetadata,
  readFileContent,
  writeFileContent,
  createFile,
  listFiles,
  getFolderStructure,
  getFileType,
  ensureDirectoryExists,
  validateAndSanitizePath,
  isAccessibleDirectory,
  isDirectoryOrJunction,
};