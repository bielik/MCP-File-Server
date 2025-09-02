import fs from 'fs/promises';
import path from 'path';
import chokidar from 'chokidar';
import crypto from 'crypto';
import mimeTypes from 'mime-types';
import {
  FilePermission,
  FilePermissionMatrix,
  FileMetadata,
  MCPServerError,
  FilePermissionError,
} from '../types/index.js';
import { config, getAbsolutePath } from '../config/index.js';
import { logWithContext, logFileOperation } from '../utils/logger.js';

export class FilePermissionManager {
  private permissionMatrix: FilePermissionMatrix;
  private watchers: Map<string, chokidar.FSWatcher> = new Map();
  private permissionCache: Map<string, { permission: FilePermission; timestamp: number }> = new Map();
  private readonly cacheTimeout = 5 * 60 * 1000; // 5 minutes
  private readonly settingsFile = path.join(process.cwd(), 'user-settings.json');

  constructor(permissionMatrix?: FilePermissionMatrix) {
    this.permissionMatrix = permissionMatrix || config.filePermissions;
    this.loadUserSettings();
    this.validatePermissionMatrix();
  }

  /**
   * Load user settings from disk
   */
  private loadUserSettings(): void {
    try {
      import('fs').then(fsModule => {
        if (fsModule.existsSync(this.settingsFile)) {
          const settingsData = fsModule.readFileSync(this.settingsFile, 'utf8');
          const userSettings = JSON.parse(settingsData);
          
          if (userSettings.permissionMatrix) {
            // Override default settings with user settings
            this.permissionMatrix = {
              contextFolders: userSettings.permissionMatrix.contextFolders || this.permissionMatrix.contextFolders,
              workingFolders: userSettings.permissionMatrix.workingFolders || this.permissionMatrix.workingFolders,
              outputFolder: userSettings.permissionMatrix.outputFolder || this.permissionMatrix.outputFolder,
            };
            logWithContext.info('User settings loaded', { settingsFile: this.settingsFile });
          }
        }
      }).catch(error => {
        logWithContext.warn('Failed to load user settings, using defaults', { error: (error as Error).message });
      });
    } catch (error) {
      logWithContext.warn('Failed to load user settings, using defaults', { error: (error as Error).message });
    }
  }

  /**
   * Save user settings to disk
   */
  private async saveUserSettings(): Promise<void> {
    try {
      const userSettings = {
        permissionMatrix: this.permissionMatrix,
        lastModified: new Date().toISOString(),
      };
      
      await fs.writeFile(this.settingsFile, JSON.stringify(userSettings, null, 2), 'utf8');
      logWithContext.info('User settings saved', { settingsFile: this.settingsFile });
    } catch (error) {
      logWithContext.error('Failed to save user settings', error as Error);
    }
  }

  /**
   * Validate the permission matrix configuration
   */
  private validatePermissionMatrix(): void {
    // Check for overlapping directories
    const allDirs = [
      ...this.permissionMatrix.contextFolders.map(d => ({ dir: d, type: 'context' })),
      ...this.permissionMatrix.workingFolders.map(d => ({ dir: d, type: 'working' })),
      { dir: this.permissionMatrix.outputFolder, type: 'output' },
    ];

    for (let i = 0; i < allDirs.length; i++) {
      for (let j = i + 1; j < allDirs.length; j++) {
        const entry1 = allDirs[i];
        const entry2 = allDirs[j];
        
        if (!entry1 || !entry2) continue;
        
        const dir1 = getAbsolutePath(entry1.dir);
        const dir2 = getAbsolutePath(entry2.dir);
        
        if (dir1.startsWith(dir2) || dir2.startsWith(dir1)) {
          logWithContext.warn('Overlapping permission directories detected', {
            dir1: { path: dir1, type: entry1.type },
            dir2: { path: dir2, type: entry2.type },
          });
        }
      }
    }
  }

  /**
   * Get the permission for a given file path
   */
  public getFilePermission(filePath: string): { permission: FilePermission; allowed: boolean } {
    const absolutePath = this.validateAndNormalizePath(filePath);
    
    // Check cache first
    const cached = this.permissionCache.get(absolutePath);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return { permission: cached.permission, allowed: true };
    }

    let permission: FilePermission;
    let allowed = false;

    // Check context folders (read-only)
    for (const folder of this.permissionMatrix.contextFolders) {
      const contextPath = getAbsolutePath(folder);
      if (absolutePath.startsWith(contextPath + path.sep) || absolutePath === contextPath) {
        permission = 'context';
        allowed = true;
        break;
      }
    }

    // Check working folders (read-write) - higher priority than context
    if (!allowed) {
      for (const folder of this.permissionMatrix.workingFolders) {
        const workingPath = getAbsolutePath(folder);
        if (absolutePath.startsWith(workingPath + path.sep) || absolutePath === workingPath) {
          permission = 'working';
          allowed = true;
          break;
        }
      }
    }

    // Check output folder (agent-controlled) - highest priority
    if (!allowed) {
      const outputPath = getAbsolutePath(this.permissionMatrix.outputFolder);
      if (absolutePath.startsWith(outputPath + path.sep) || absolutePath === outputPath) {
        permission = 'output';
        allowed = true;
      }
    }

    // If no match found
    if (!allowed) {
      permission = 'context'; // Default to most restrictive
    }

    // Cache the result
    this.permissionCache.set(absolutePath, {
      permission: permission!,
      timestamp: Date.now(),
    });

    logFileOperation('permission-check', absolutePath, allowed, undefined, allowed ? undefined : 'Path not in allowed directories');

    return { permission: permission!, allowed };
  }

  /**
   * Get file permission for browsing - more permissive for file explorer
   * Returns permission status without enforcing access restrictions
   */
  public async getFilePermissionForBrowsing(filePath: string): Promise<{ permission: 'context' | 'working' | 'output' | null; allowed: boolean }> {
    const absolutePath = getAbsolutePath(filePath);
    
    // Debug logging
    console.log(`🔍 Checking permission for: ${absolutePath}`);
    console.log(`📁 Context folders: ${JSON.stringify(this.permissionMatrix.contextFolders)}`);

    // Check cache first
    const cached = this.permissionCache.get(absolutePath);
    if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
      console.log(`💾 Using cached permission: ${cached.permission}`);
      return { permission: cached.permission, allowed: true }; // Always return allowed for browsing
    }

    let permission: 'context' | 'working' | 'output' | null = null;
    let allowed = false;

    // Check context folders
    for (const folder of this.permissionMatrix.contextFolders) {
      const contextPath = getAbsolutePath(folder);
      console.log(`🔄 Comparing: "${absolutePath}" with context: "${contextPath}"`);
      console.log(`🔄 StartsWith check: ${absolutePath.startsWith(contextPath + path.sep)}`);
      console.log(`🔄 Equals check: ${absolutePath === contextPath}`);
      if (absolutePath.startsWith(contextPath + path.sep) || absolutePath === contextPath) {
        console.log(`✅ MATCH! Setting permission to 'context'`);
        permission = 'context';
        allowed = true;
        break;
      }
    }

    // Check working folders - higher priority than context
    if (!allowed) {
      for (const folder of this.permissionMatrix.workingFolders) {
        const workingPath = getAbsolutePath(folder);
        if (absolutePath.startsWith(workingPath + path.sep) || absolutePath === workingPath) {
          permission = 'working';
          allowed = true;
          break;
        }
      }
    }

    // Check output folder - highest priority
    if (!allowed) {
      const outputPath = getAbsolutePath(this.permissionMatrix.outputFolder);
      if (absolutePath.startsWith(outputPath + path.sep) || absolutePath === outputPath) {
        permission = 'output';
        allowed = true;
      }
    }

    // For browsing, we allow access to all user-accessible directories
    // but only show permissions for configured directories
    const isUserAccessible = await this.isUserAccessiblePath(absolutePath);
    
    return { 
      permission: permission, // null if no permission assigned
      allowed: isUserAccessible // true for all user-accessible paths
    };
  }

  /**
   * Check if a path is in user-accessible directories (not system directories)
   */
  private async isUserAccessiblePath(absolutePath: string): Promise<boolean> {
    const pathModule = await import('path');
    const osModule = await import('os');
    
    // Allow user home directory and subdirectories
    const homedir = osModule.homedir();
    if (absolutePath.startsWith(homedir)) {
      return true;
    }

    // Block system directories on Windows
    if (process.platform === 'win32') {
      const systemDirs = ['C:\\Windows', 'C:\\System32', 'C:\\Program Files', 'C:\\ProgramData'];
      if (systemDirs.some(sysDir => absolutePath.startsWith(sysDir))) {
        return false;
      }
    }

    // Block system directories on Unix-like systems
    if (process.platform !== 'win32') {
      const systemDirs = ['/etc', '/proc', '/sys', '/dev', '/boot', '/root'];
      if (systemDirs.some(sysDir => absolutePath.startsWith(sysDir))) {
        return false;
      }
    }

    // Allow other directories (like C:\ root, but not system subdirs)
    return true;
  }

  /**
   * Check if an operation is allowed on a file
   */
  public checkOperationPermission(filePath: string, operation: 'read' | 'write' | 'create' | 'delete'): void {
    const { permission, allowed } = this.getFilePermission(filePath);
    
    if (!allowed) {
      throw new FilePermissionError(
        `Access denied: ${filePath} is not in an allowed directory`,
        filePath
      );
    }

    switch (operation) {
      case 'read':
        // All permission levels allow reading
        break;
        
      case 'write':
        if (permission === 'read-only') {
          throw new FilePermissionError(
            `Write permission denied: ${filePath} is in a read-only directory`,
            filePath
          );
        }
        break;
        
      case 'create':
        if (permission === 'read-only') {
          throw new FilePermissionError(
            `Create permission denied: ${filePath} is in a read-only directory`,
            filePath
          );
        }
        break;
        
      case 'delete':
        if (permission !== 'agent-controlled') {
          throw new FilePermissionError(
            `Delete permission denied: ${filePath} is not in an agent-controlled directory`,
            filePath
          );
        }
        break;
        
      default:
        throw new Error(`Unknown operation: ${operation}`);
    }
  }

  /**
   * Get all files with their permissions
   */
  public async getAllowedFiles(filter?: {
    permissions?: FilePermission[];
    recursive?: boolean;
    fileTypes?: string[];
  }): Promise<FileMetadata[]> {
    const results: FileMetadata[] = [];
    const options = {
      permissions: filter?.permissions || ['context', 'working', 'output'],
      recursive: filter?.recursive ?? true,
      fileTypes: filter?.fileTypes,
    };

    // Get directories to scan based on permission filter
    const dirsToScan: Array<{ dir: string; expectedPermission: FilePermission }> = [];
    
    if (options.permissions.includes('context')) {
      dirsToScan.push(...this.permissionMatrix.contextFolders.map(dir => ({ 
        dir, 
        expectedPermission: 'context' as FilePermission 
      })));
    }
    
    if (options.permissions.includes('working')) {
      dirsToScan.push(...this.permissionMatrix.workingFolders.map(dir => ({ 
        dir, 
        expectedPermission: 'working' as FilePermission 
      })));
    }
    
    if (options.permissions.includes('output')) {
      dirsToScan.push({ 
        dir: this.permissionMatrix.outputFolder, 
        expectedPermission: 'output' 
      });
    }

    // Scan each directory or file
    for (const { dir, expectedPermission } of dirsToScan) {
      try {
        const fullPath = getAbsolutePath(dir);
        const stats = await fs.stat(fullPath);
        
        if (stats.isFile()) {
          // Handle individual file
          const fileMetadata: FileMetadata = {
            id: this.generateFileId(fullPath),
            path: fullPath,
            filename: path.basename(fullPath),
            size: stats.size,
            created: stats.birthtime,
            modified: stats.mtime,
            type: this.getMimeType(fullPath),
            permissions: expectedPermission,
          };
          results.push(fileMetadata);
        } else if (stats.isDirectory()) {
          // Handle directory - scan recursively
          const files = await this.scanDirectory(fullPath, options.recursive, options.fileTypes);
          
          // Verify permissions match expectation and add to results
          for (const fileMetadata of files) {
            const { permission } = this.getFilePermission(fileMetadata.path);
            if (permission === expectedPermission) {
              fileMetadata.permissions = permission;
              results.push(fileMetadata);
            }
          }
        }
      } catch (error) {
        logWithContext.warn('Failed to scan directory', { 
          directory: dir, 
          error: (error as Error).message 
        });
      }
    }

    return results;
  }

  /**
   * Scan a directory for files
   */
  private async scanDirectory(
    dirPath: string, 
    recursive: boolean = true, 
    fileTypes?: string[]
  ): Promise<FileMetadata[]> {
    const files: FileMetadata[] = [];

    try {
      const entries = await fs.readdir(dirPath, { withFileTypes: true });

      for (const entry of entries) {
        const entryPath = path.join(dirPath, entry.name);

        if (entry.isFile()) {
          // Check file type filter
          if (fileTypes && fileTypes.length > 0) {
            const ext = path.extname(entry.name).toLowerCase();
            if (!fileTypes.includes(ext)) {
              continue;
            }
          }

          try {
            const stats = await fs.stat(entryPath);
            const metadata: FileMetadata = {
              id: this.generateFileId(entryPath),
              path: entryPath,
              filename: entry.name,
              size: stats.size,
              created: stats.birthtime,
              modified: stats.mtime,
              type: this.getMimeType(entryPath),
              permissions: 'context', // Will be set correctly by caller
            };

            files.push(metadata);
          } catch (error) {
            // Skip files we can't access
            continue;
          }
        } else if (entry.isDirectory() && recursive) {
          const subFiles = await this.scanDirectory(entryPath, recursive, fileTypes);
          files.push(...subFiles);
        }
      }
    } catch (error) {
      throw new MCPServerError(
        `Failed to scan directory ${dirPath}: ${(error as Error).message}`,
        'DIRECTORY_SCAN_ERROR'
      );
    }

    return files;
  }

  /**
   * Setup file system watchers for permission monitoring
   */
  public async setupFileWatchers(): Promise<void> {
    const allDirs = [
      ...this.permissionMatrix.contextFolders,
      ...this.permissionMatrix.workingFolders,
      this.permissionMatrix.outputFolder,
    ].filter(Boolean);

    for (const dir of allDirs) {
      try {
        const absolutePath = getAbsolutePath(dir);
        
        // Create directory if it doesn't exist (only for output folder)
        if (dir === this.permissionMatrix.outputFolder) {
          await fs.mkdir(absolutePath, { recursive: true });
        }

        const watcher = chokidar.watch(absolutePath, {
          ignored: /node_modules/,
          persistent: true,
          ignoreInitial: true,
        });

        watcher
          .on('add', (filePath) => {
            this.clearPermissionCache(filePath);
            logWithContext.debug('File added', { filePath });
          })
          .on('change', (filePath) => {
            this.clearPermissionCache(filePath);
            logWithContext.debug('File changed', { filePath });
          })
          .on('unlink', (filePath) => {
            this.clearPermissionCache(filePath);
            logWithContext.debug('File removed', { filePath });
          })
          .on('error', (error) => {
            logWithContext.error('File watcher error', error, { directory: dir });
          });

        this.watchers.set(dir, watcher);
        logWithContext.info('File watcher started', { directory: absolutePath });
      } catch (error) {
        logWithContext.warn('Failed to setup file watcher', { 
          directory: dir, 
          error: (error as Error).message 
        });
      }
    }
  }

  /**
   * Stop all file watchers
   */
  public async stopFileWatchers(): Promise<void> {
    for (const [dir, watcher] of this.watchers) {
      try {
        await watcher.close();
        logWithContext.info('File watcher stopped', { directory: dir });
      } catch (error) {
        logWithContext.error('Error stopping file watcher', error as Error, { directory: dir });
      }
    }
    this.watchers.clear();
  }

  /**
   * Update the permission matrix
   */
  public async updatePermissionMatrix(newMatrix: Partial<FilePermissionMatrix>): Promise<void> {
    this.permissionMatrix = {
      ...this.permissionMatrix,
      ...newMatrix,
    };
    
    this.validatePermissionMatrix();
    this.clearAllPermissionCache();
    
    // Save the updated settings to disk
    await this.saveUserSettings();
    
    logWithContext.info('Permission matrix updated', {
      contextFolders: this.permissionMatrix.contextFolders.length,
      workingFolders: this.permissionMatrix.workingFolders.length,
      outputFolder: !!this.permissionMatrix.outputFolder,
    });
  }

  /**
   * Get the current permission matrix
   */
  public getPermissionMatrix(): FilePermissionMatrix {
    return { ...this.permissionMatrix };
  }

  /**
   * Validate and normalize a file path
   */
  private validateAndNormalizePath(filePath: string): string {
    const absolutePath = getAbsolutePath(filePath);
    const normalizedPath = path.normalize(absolutePath);
    
    // Check for directory traversal
    if (normalizedPath.includes('..')) {
      throw new FilePermissionError(
        `Invalid path: directory traversal detected in ${filePath}`,
        filePath
      );
    }
    
    return normalizedPath;
  }

  /**
   * Clear permission cache for a specific file
   */
  private clearPermissionCache(filePath: string): void {
    const absolutePath = getAbsolutePath(filePath);
    this.permissionCache.delete(absolutePath);
  }

  /**
   * Clear all permission cache
   */
  private clearAllPermissionCache(): void {
    this.permissionCache.clear();
  }

  /**
   * Generate a unique file ID
   */
  private generateFileId(filePath: string): string {
    return crypto.createHash('md5').update(filePath).digest('hex');
  }

  /**
   * Get MIME type for a file
   */
  private getMimeType(filePath: string): string {
    return mimeTypes.lookup(filePath) || 'application/octet-stream';
  }

  /**
   * Get usage statistics for the permission system
   */
  public async getUsageStats(): Promise<{
    contextFiles: number;
    workingFiles: number;
    outputFiles: number;
    totalSize: number;
    lastAccess: Date;
  }> {
    const allFiles = await this.getAllowedFiles({ recursive: true });
    
    const stats = {
      contextFiles: allFiles.filter(f => f.permissions === 'context').length,
      workingFiles: allFiles.filter(f => f.permissions === 'working').length,
      outputFiles: allFiles.filter(f => f.permissions === 'output').length,
      totalSize: allFiles.reduce((sum, f) => sum + f.size, 0),
      lastAccess: new Date(),
    };

    return stats;
  }

  /**
   * Clean up resources
   */
  public async cleanup(): Promise<void> {
    await this.stopFileWatchers();
    this.clearAllPermissionCache();
    logWithContext.info('File permission manager cleaned up');
  }
}

// Export singleton instance
export const filePermissionManager = new FilePermissionManager();
export default filePermissionManager;