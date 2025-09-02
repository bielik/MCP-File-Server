// File Management Module
// Exports all file-related functionality including permissions, operations, and utilities

// Permission management
export {
  FilePermissionManager,
  filePermissionManager,
} from './permissions.js';

// File operations utilities
export {
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
} from '../utils/file-utils.js';

// Re-export relevant types
export type {
  FilePermissionMatrix,
  FilePermission,
  FileMetadata,
  FileCategory,
} from '../types/index.js';

// File management utilities
import { filePermissionManager } from './permissions.js';
import { logWithContext } from '../utils/logger.js';

/**
 * Initialize the file management system
 */
export async function initializeFileSystem(): Promise<void> {
  try {
    logWithContext.info('Initializing file management system');
    
    // Setup file watchers for real-time permission monitoring
    await filePermissionManager.setupFileWatchers();
    
    // Get initial statistics
    const stats = await filePermissionManager.getUsageStats();
    logWithContext.info('File system initialized', {
      contextFiles: stats.contextFiles,
      workingFiles: stats.workingFiles,
      outputFiles: stats.outputFiles,
      totalFiles: stats.contextFiles + stats.workingFiles + stats.outputFiles,
      totalSizeMB: Math.round(stats.totalSize / (1024 * 1024) * 100) / 100,
    });
    
  } catch (error) {
    logWithContext.error('Failed to initialize file system', error as Error);
    throw error;
  }
}

/**
 * Cleanup file management system
 */
export async function cleanupFileSystem(): Promise<void> {
  try {
    logWithContext.info('Cleaning up file management system');
    await filePermissionManager.cleanup();
    logWithContext.info('File system cleanup completed');
  } catch (error) {
    logWithContext.error('Error during file system cleanup', error as Error);
  }
}

/**
 * Get comprehensive file system status
 */
export async function getFileSystemStatus(): Promise<{
  permissionMatrix: any;
  stats: any;
  health: {
    accessible: boolean;
    watchersActive: boolean;
    cacheSize: number;
  };
}> {
  try {
    const permissionMatrix = filePermissionManager.getPermissionMatrix();
    const stats = await filePermissionManager.getUsageStats();
    
    return {
      permissionMatrix,
      stats,
      health: {
        accessible: true,
        watchersActive: true, // TODO: Add method to check watcher status
        cacheSize: 0, // TODO: Add cache size tracking
      },
    };
  } catch (error) {
    logWithContext.error('Failed to get file system status', error as Error);
    throw error;
  }
}

/**
 * Validate file system configuration and accessibility
 */
export async function validateFileSystemConfiguration(): Promise<{
  valid: boolean;
  issues: string[];
  recommendations: string[];
}> {
  const issues: string[] = [];
  const recommendations: string[] = [];
  
  try {
    const matrix = filePermissionManager.getPermissionMatrix();
    
    // Check if directories exist and are accessible
    const allDirs = [
      ...matrix.contextFolders.map(d => ({ path: d, type: 'context' })),
      ...matrix.workingFolders.map(d => ({ path: d, type: 'working' })),
      { path: matrix.outputFolder, type: 'output' },
    ];
    
    for (const { path: dirPath, type } of allDirs) {
      try {
        const { getAbsolutePath } = await import('../config/index.js');
        const absolutePath = getAbsolutePath(dirPath);
        const { access, constants } = await import('fs/promises');
        
        await access(absolutePath, constants.F_OK);
        
        // Check write permissions for non-context folders
        if (type !== 'context') {
          await access(absolutePath, constants.W_OK);
        }
      } catch (error) {
        issues.push(`Directory ${dirPath} (${type}) is not accessible`);
        if (type === 'output') {
          recommendations.push(`Create output directory: mkdir -p "${dirPath}"`);
        } else {
          recommendations.push(`Check if directory exists and has correct permissions: ${dirPath}`);
        }
      }
    }
    
    // Check for configuration issues
    if (matrix.contextFolders.length === 0 && matrix.workingFolders.length === 0) {
      issues.push('No context or working folders configured');
      recommendations.push('Configure at least one context or working folder in .env');
    }
    
    if (!matrix.outputFolder) {
      issues.push('No output folder configured');
      recommendations.push('Set OUTPUT_FOLDER in .env');
    }
    
    const valid = issues.length === 0;
    
    logWithContext.info('File system configuration validation completed', {
      valid,
      issueCount: issues.length,
      recommendationCount: recommendations.length,
    });
    
    return { valid, issues, recommendations };
    
  } catch (error) {
    logWithContext.error('Failed to validate file system configuration', error as Error);
    return {
      valid: false,
      issues: ['Failed to validate configuration: ' + (error as Error).message],
      recommendations: ['Check system logs for detailed error information'],
    };
  }
}

// Default export for convenience
export default {
  initialize: initializeFileSystem,
  cleanup: cleanupFileSystem,
  getStatus: getFileSystemStatus,
  validate: validateFileSystemConfiguration,
  permissionManager: filePermissionManager,
};