import express from 'express';
import cors from 'cors';
import path from 'path';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { config } from '../config/index.js';
import { filePermissionManager } from '../files/permissions.js';
import { logWithContext } from '../utils/logger.js';
import { keywordSearchService } from '../src/features/search/keywordSearch.js';
import { semanticSearchService } from '../src/features/search/semanticSearch.js';
import type { 
  FilePermissionMatrix, 
  FileMetadata, 
  FilePermission 
} from '../types/index.js';

export class WebServer {
  private app: express.Application;
  private httpServer?: any;
  private io?: SocketIOServer;

  constructor() {
    this.app = express();
    this.setupMiddleware();
    this.setupRoutes();
  }

  private setupMiddleware(): void {
    this.app.use(cors());
    this.app.use(express.json());
    
    // Only serve static files if dist directory exists (production mode)
    const distPath = path.join(process.cwd(), '../frontend/dist');
    try {
      import('fs').then(fs => {
        if (fs.existsSync(distPath)) {
          this.app.use(express.static(distPath));
        }
      });
    } catch (error) {
      // In development mode, frontend is served by Vite
      logWithContext.info('Frontend dist directory not found - running in development mode');
    }
  }

  private isAccessibleDirectory(entryName: string, fullPath: string): boolean {
    // Skip hidden files and system directories
    if (entryName.startsWith('.') || 
        entryName.startsWith('NTUSER') || 
        entryName.includes('regtrans-ms')) {
      return false;
    }

    // Windows system directories to skip
    const windowsSystemDirs = [
      'AppData', 'Application Data', 'Local Settings', 'NetHood', 'PrintHood', 
      'SendTo', 'Start Menu', 'Templates', 'Recent', 'Cookies', 'Favorites',
      'My Music', 'My Pictures', 'My Videos', 'My Documents'
    ];

    if (windowsSystemDirs.includes(entryName)) {
      return false;
    }

    // Windows junction points and special folders that may cause permission issues
    const problematicDirs = [
      'ntuser.dat.LOG1', 'ntuser.dat.LOG2', 'ntuser.ini',
      'Tracing', 'Saved Games', 'Searches'
    ];

    if (problematicDirs.some(dir => entryName.toLowerCase().includes(dir.toLowerCase()))) {
      return false;
    }

    // If it's in the user profile, be more permissive for common directories
    const userProfile = process.env.USERPROFILE || '';
    if (fullPath.startsWith(userProfile)) {
      const commonUserDirs = [
        'Documents', 'Downloads', 'Desktop', 'Pictures', 'Music', 'Videos',
        'OneDrive', 'Dropbox', 'Google Drive', 'iCloud Drive'
      ];
      
      // Allow common directories or directories that start with common prefixes
      const isCommonDir = commonUserDirs.some(dir => 
        entryName === dir || entryName.startsWith(dir + ' ') || entryName.startsWith(dir + '-')
      );
      
      if (isCommonDir) {
        return true;
      }

      // Allow other user directories that don't look like system files
      return !entryName.startsWith('NTUSER') && 
             !entryName.includes('.dat') && 
             !entryName.includes('.log');
    }

    return true;
  }

  private async isDirectoryOrJunction(path: string): Promise<{ isDirectory: boolean; stats: any }> {
    const fs = await import('fs/promises');
    
    try {
      // Use lstat to detect symbolic links and junction points
      const stats = await fs.lstat(path);
      
      // Check if it's a directory OR a symbolic link pointing to a directory
      let isDirectory = stats.isDirectory();
      
      if (!isDirectory && stats.isSymbolicLink()) {
        try {
          // For symbolic links, check what they point to
          const realStats = await fs.stat(path);
          isDirectory = realStats.isDirectory();
        } catch {
          // If we can't follow the link, assume it's not a directory
          isDirectory = false;
        }
      }
      
      return { isDirectory, stats };
    } catch (error) {
      return { isDirectory: false, stats: null };
    }
  }

  private setupRoutes(): void {
    // API Routes
    const apiRouter = express.Router();

    // Configuration endpoints
    apiRouter.get('/config', (req, res) => {
      try {
        const permissionMatrix = filePermissionManager.getPermissionMatrix();
        res.json({
          permissionMatrix,
          serverConfig: {
            mcpPort: config.server.mcpPort,
            webUIPort: config.server.webUIPort,
            enableCaching: config.server.enableCaching,
            logLevel: config.server.logLevel,
          },
          processingConfig: config.processing,
        });
      } catch (error) {
        logWithContext.error('Error fetching configuration', error as Error);
        res.status(500).json({ error: 'Failed to fetch configuration' });
      }
    });

    apiRouter.post('/config/permissions', async (req, res) => {
      try {
        const newMatrix: Partial<FilePermissionMatrix> = req.body;
        await filePermissionManager.updatePermissionMatrix(newMatrix);
        
        logWithContext.info('Permission matrix updated via web UI', {
          contextFolders: newMatrix.contextFolders?.length,
          workingFolders: newMatrix.workingFolders?.length,
          outputFolder: !!newMatrix.outputFolder,
        });
        
        res.json({ success: true, message: 'Permission matrix updated' });
      } catch (error) {
        logWithContext.error('Error updating permission matrix', error as Error);
        res.status(500).json({ error: 'Failed to update permission matrix' });
      }
    });

    // Path validation endpoints
    apiRouter.post('/filesystem/validate-path', async (req, res) => {
      try {
        const { path: requestedPath } = req.body;
        
        if (!requestedPath) {
          res.status(400).json({ error: 'Path is required' });
          return;
        }

        const fs = await import('fs/promises');
        const path = await import('path');
        
        try {
          const normalizedPath = await this.validateAndSanitizePath(requestedPath);
          
          // Check if path exists and is accessible
          const stats = await fs.stat(normalizedPath);
          await fs.access(normalizedPath, fs.constants.R_OK);
          
          res.json({
            valid: true,
            exists: true,
            accessible: true,
            isDirectory: stats.isDirectory(),
            normalizedPath,
            suggestion: null
          });
        } catch (error) {
          // Try to suggest a corrected path
          let suggestion = null;
          try {
            // Common path corrections
            const corrections = [
              requestedPath.replace(/\//g, '\\'), // Convert forward slashes
              requestedPath.replace(/\\\\/g, '\\'), // Fix double backslashes
              requestedPath.replace(/^~/, process.env.USERPROFILE || 'C:\\Users'), // Expand ~
            ];
            
            for (const corrected of corrections) {
              if (corrected !== requestedPath) {
                try {
                  const testPath = path.resolve(corrected);
                  await fs.access(testPath, fs.constants.R_OK);
                  suggestion = testPath;
                  break;
                } catch {}
              }
            }
          } catch {}
          
          res.json({
            valid: false,
            exists: false,
            accessible: false,
            isDirectory: false,
            normalizedPath: requestedPath,
            suggestion,
            error: (error as Error).message
          });
        }
      } catch (error) {
        logWithContext.error('Error validating path', error as Error);
        res.status(500).json({ error: 'Failed to validate path' });
      }
    });

    apiRouter.get('/filesystem/common-paths', (req, res) => {
      try {
        const userProfile = process.env.USERPROFILE || 'C:\\Users\\DefaultUser';
        const userName = process.env.USERNAME || 'User';
        
        const commonPaths = [
          { name: 'This PC', path: '', icon: 'hard-drive' },
          { name: 'Documents', path: `${userProfile}\\Documents`, icon: 'folder' },
          { name: 'Downloads', path: `${userProfile}\\Downloads`, icon: 'folder' },
          { name: 'Desktop', path: `${userProfile}\\Desktop`, icon: 'folder' },
          { name: 'Pictures', path: `${userProfile}\\Pictures`, icon: 'folder' },
          { name: 'OneDrive - Decoding Spaces', path: `${userProfile}\\OneDrive - Decoding Spaces GbR`, icon: 'folder' },
          { name: 'OneDrive - Bauhaus', path: `${userProfile}\\OneDrive - Bauhaus - Universität Weimar`, icon: 'folder' },
          { name: 'C: Drive', path: 'C:\\', icon: 'hard-drive' },
        ];

        res.json(commonPaths);
      } catch (error) {
        logWithContext.error('Error getting common paths', error as Error);
        res.status(500).json({ error: 'Failed to get common paths' });
      }
    });

    // File system endpoints
    apiRouter.get('/files', async (req, res) => {
      try {
        const { permissions, recursive, fileTypes } = req.query;
        
        const filter: {
          permissions?: FilePermission[];
          recursive?: boolean;
          fileTypes?: string[];
        } = {
          recursive: recursive === 'true',
        };

        if (permissions) {
          filter.permissions = (permissions as string).split(',') as FilePermission[];
        }

        if (fileTypes) {
          filter.fileTypes = (fileTypes as string).split(',');
        }

        const files = await filePermissionManager.getAllowedFiles(filter);
        res.json(files);
      } catch (error) {
        logWithContext.error('Error fetching files', error as Error);
        res.status(500).json({ error: 'Failed to fetch files' });
      }
    });

    apiRouter.get('/files/permissions/:path(*)', (req, res) => {
      try {
        const filePath = req.params.path;
        if (!filePath) {
          res.status(400).json({ error: 'File path is required' });
          return;
        }
        const decodedPath = decodeURIComponent(filePath);
        const result = filePermissionManager.getFilePermission(decodedPath);
        res.json(result);
      } catch (error) {
        logWithContext.error('Error checking file permissions', error as Error);
        res.status(500).json({ error: 'Failed to check file permissions' });
      }
    });

    // Statistics endpoint
    apiRouter.get('/stats', async (req, res) => {
      try {
        const stats = await filePermissionManager.getUsageStats();
        res.json(stats);
      } catch (error) {
        logWithContext.error('Error fetching usage stats', error as Error);
        res.status(500).json({ error: 'Failed to fetch usage stats' });
      }
    });

    // Clear embeddings endpoint
    apiRouter.post('/config/clear-embeddings', async (req, res) => {
      try {
        // Clear Qdrant collections
        const { QdrantVectorStore } = await import('../storage/index.js');
        const vectorStore = new QdrantVectorStore();
        await vectorStore.clearAllCollections();

        // Clear cached embeddings directory
        const fs = await import('fs/promises');
        const path = await import('path');
        const embeddingsDir = path.join(process.cwd(), 'embeddings-cache');
        
        try {
          await fs.rm(embeddingsDir, { recursive: true, force: true });
          await fs.mkdir(embeddingsDir, { recursive: true });
          logWithContext.info('Embeddings cache directory cleared', { directory: embeddingsDir });
        } catch (error) {
          logWithContext.warn('Failed to clear embeddings cache directory', { 
            directory: embeddingsDir,
            error: (error as Error).message 
          });
        }

        logWithContext.info('All embeddings cleared via web UI');
        res.json({ success: true, message: 'All embeddings and cached data cleared successfully' });
      } catch (error) {
        logWithContext.error('Error clearing embeddings', error as Error);
        res.status(500).json({ error: 'Failed to clear embeddings' });
      }
    });

    // Search endpoints
    apiRouter.post('/search', async (req, res) => {
      const startTime = Date.now();
      
      try {
        const { query, searchType = 'text', options = {} } = req.body;
        
        // Validate input
        if (!query || typeof query !== 'string' || query.trim().length === 0) {
          res.status(400).json({ 
            error: 'Query is required and must be a non-empty string',
            searchType,
            duration: Date.now() - startTime,
          });
          return;
        }
        
        if (!['text', 'semantic', 'multimodal'].includes(searchType)) {
          res.status(400).json({ 
            error: 'Invalid search type. Must be one of: text, semantic, multimodal',
            searchType,
            duration: Date.now() - startTime,
          });
          return;
        }
        
        let results = [];
        let searchDetails = {};
        
        // Execute search based on type
        switch (searchType) {
          case 'text':
            // Keyword search using FlexSearch
            results = await keywordSearchService.search(query, {
              limit: options.limit || 20,
              fuzzy: options.fuzzy !== false, // Default to true
              highlight: options.highlight !== false, // Default to true
              ...options,
            });
            searchDetails = {
              service: 'FlexSearch',
              type: 'keyword_matching',
              fuzzy: options.fuzzy !== false,
            };
            break;
            
          case 'semantic':
            // Semantic search using vector embeddings
            results = await semanticSearchService.searchText(query, {
              limit: options.limit || 10,
              threshold: options.threshold || 0.7,
              searchMode: 'text_only',
              ...options,
            });
            searchDetails = {
              service: 'M-CLIP Embeddings + Qdrant',
              type: 'vector_similarity',
              threshold: options.threshold || 0.7,
            };
            break;
            
          case 'multimodal':
            // Multimodal search (text and images)
            results = await semanticSearchService.searchMultimodal(query, {
              limit: options.limit || 15,
              threshold: options.threshold || 0.7,
              includeText: options.includeText !== false, // Default to true
              includeImages: options.includeImages !== false, // Default to true
              searchMode: 'multimodal',
              ...options,
            });
            searchDetails = {
              service: 'M-CLIP Embeddings + Qdrant',
              type: 'cross_modal_similarity',
              threshold: options.threshold || 0.7,
              modalities: {
                text: options.includeText !== false,
                images: options.includeImages !== false,
              },
            };
            break;
        }
        
        const duration = Date.now() - startTime;
        
        // Format response
        const response = {
          success: true,
          query,
          searchType,
          results: results.map(result => ({
            id: result.id,
            filePath: result.filePath,
            score: result.score,
            contentType: result.contentType || (result.textContent ? 'text' : 'unknown'),
            textContent: result.textContent,
            highlight: result.highlight,
            imageCaption: result.imageCaption,
            documentTitle: result.documentTitle,
            pageNumber: result.pageNumber,
            chunkIndex: result.chunkIndex,
            createdAt: result.createdAt,
          })),
          total: results.length,
          searchDetails,
          timing: {
            duration: `${duration}ms`,
            searchTime: duration,
          },
          timestamp: new Date().toISOString(),
        };
        
        logWithContext.info('API search completed', {
          query,
          searchType,
          resultCount: results.length,
          duration: `${duration}ms`,
        });
        
        res.json(response);
      } catch (error) {
        const duration = Date.now() - startTime;
        const errorMessage = (error as Error).message;
        
        logWithContext.error('API search failed', error as Error, {
          query: req.body.query,
          searchType: req.body.searchType,
          duration: `${duration}ms`,
        });
        
        res.status(500).json({
          success: false,
          error: 'Search operation failed',
          details: errorMessage,
          searchType: req.body.searchType || 'unknown',
          duration: `${duration}ms`,
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Search service status endpoint
    apiRouter.get('/search/status', (req, res) => {
      try {
        const keywordStatus = keywordSearchService.getStatus();
        const semanticStatus = semanticSearchService.getStatus();
        
        res.json({
          services: {
            keyword: {
              ready: keywordStatus.ready,
              documentsIndexed: keywordStatus.documentsIndexed,
              service: 'FlexSearch',
            },
            semantic: {
              ready: semanticStatus.ready,
              initialized: semanticStatus.initialized,
              aiServiceReady: semanticStatus.aiServiceReady,
              vectorDbServiceReady: semanticStatus.vectorDbServiceReady,
              totalQueries: semanticStatus.totalQueries,
              service: 'M-CLIP + Qdrant',
            },
          },
          overall: {
            ready: keywordStatus.ready && semanticStatus.ready,
            timestamp: new Date().toISOString(),
          }
        });
      } catch (error) {
        logWithContext.error('Error fetching search service status', error as Error);
        res.status(500).json({ error: 'Failed to fetch search service status' });
      }
    });

    // Health check endpoint
    apiRouter.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        version: '1.0.0',
      });
    });

    // Logs endpoint (simple file reading - in production you'd want proper log management)
    apiRouter.get('/logs', async (req, res) => {
      try {
        const { lines = 100 } = req.query;
        // This is a simple implementation - in production you'd want proper log streaming
        res.json({ 
          message: 'Log endpoint not fully implemented yet',
          suggestion: 'Check console logs or log file directly',
        });
      } catch (error) {
        logWithContext.error('Error fetching logs', error as Error);
        res.status(500).json({ error: 'Failed to fetch logs' });
      }
    });

    // File system browsing endpoints
    apiRouter.get('/filesystem/browse', async (req, res) => {
      try {
        const { path: requestedPath = '' } = req.query;
        const targetPath = await this.validateAndSanitizePath(requestedPath as string);
        
        const fs = await import('fs/promises');
        const path = await import('path');
        
        const entries = await fs.readdir(targetPath, { withFileTypes: true });
        const items = await Promise.all(entries.map(async (entry) => {
          const fullPath = path.join(targetPath, entry.name);
          
          // Use improved filtering logic
          if (!this.isAccessibleDirectory(entry.name, fullPath)) {
            return null;
          }
          
          try {
            // Use junction-aware directory detection
            const { isDirectory, stats } = await this.isDirectoryOrJunction(fullPath);
            
            // For directories, do a quick access test
            if (isDirectory) {
              try {
                await fs.access(fullPath, fs.constants.R_OK);
              } catch {
                return null; // Skip inaccessible directories
              }
            }
            
            const permissionResult = await (async () => {
              // Use browsing-specific permission check (less noisy)
              try {
                const result = await filePermissionManager.getFilePermissionForBrowsing(fullPath);
                console.log(`🌐 API Response for ${fullPath}: permission = ${result.permission}`);
                return result.permission;
              } catch (error) {
                console.log(`❌ Permission check failed for ${fullPath}:`, error);
                return null;
              }
            })();

            return {
              name: entry.name,
              path: fullPath,
              type: isDirectory ? 'directory' : 'file',
              size: !isDirectory ? stats.size : null,
              modified: stats.mtime.toISOString(),
              permissions: permissionResult,
            };
          } catch (error) {
            return null; // Skip inaccessible files
          }
        }));

        const validItems = items.filter(item => item !== null);
        res.json({ 
          currentPath: targetPath, 
          entries: validItems 
        });
      } catch (error) {
        logWithContext.error('Error browsing filesystem', error as Error);
        res.status(500).json({ error: 'Failed to browse directory' });
      }
    });

    apiRouter.get('/filesystem/tree', async (req, res) => {
      try {
        const { path: requestedPath = '', depth = '2' } = req.query;
        const targetPath = await this.validateAndSanitizePath(requestedPath as string);
        const maxDepth = Math.min(parseInt(depth as string) || 2, 5); // Limit depth for performance
        
        const buildTree = async (currentPath: string, currentDepth: number): Promise<any> => {
          if (currentDepth >= maxDepth) return null;
          
          const fs = await import('fs/promises');
          const path = await import('path');
          
          try {
            const entries = await fs.readdir(currentPath, { withFileTypes: true });
            const directories = entries.filter(entry => {
              if (!entry.isDirectory()) return false;
              const fullPath = path.join(currentPath, entry.name);
              return this.isAccessibleDirectory(entry.name, fullPath);
            });
            
            const children = await Promise.all(directories.map(async (dir) => {
              const dirPath = path.join(currentPath, dir.name);
              
              // Test directory accessibility
              try {
                await fs.access(dirPath, fs.constants.R_OK);
              } catch {
                return null; // Skip inaccessible directories
              }
              
              const subtree = await buildTree(dirPath, currentDepth + 1);
              const permissionResult = await filePermissionManager.getFilePermissionForBrowsing(dirPath);
              
              return {
                name: dir.name,
                path: dirPath,
                type: 'directory',
                permissions: permissionResult.permission,
                children: subtree,
              };
            }));
            
            return children.filter(child => child !== null);
          } catch (error) {
            return null;
          }
        };

        const tree = await buildTree(targetPath, 0);
        res.json({ path: targetPath, tree });
      } catch (error) {
        logWithContext.error('Error building filesystem tree', error as Error);
        res.status(500).json({ error: 'Failed to build directory tree' });
      }
    });

    // Permission management endpoints
    apiRouter.post('/config/permissions/assign', async (req, res) => {
      try {
        const { paths, permission } = req.body;
        
        if (!Array.isArray(paths) || !permission || !['context', 'working', 'output'].includes(permission)) {
          res.status(400).json({ error: 'Invalid request format' });
          return;
        }

        // Validate all paths first
        const validatedPaths = await Promise.all(paths.map(path => this.validateAndSanitizePath(path)));
        
        // Update permission matrix based on permission type
        const currentMatrix = filePermissionManager.getPermissionMatrix();
        let newMatrix = { ...currentMatrix };

        validatedPaths.forEach(path => {
          // Remove from other permission types first
          newMatrix.contextFolders = newMatrix.contextFolders.filter(p => p !== path);
          newMatrix.workingFolders = newMatrix.workingFolders.filter(p => p !== path);
          
          // Add to appropriate permission type
          if (permission === 'context') {
            if (!newMatrix.contextFolders.includes(path)) {
              newMatrix.contextFolders.push(path);
            }
          } else if (permission === 'working') {
            if (!newMatrix.workingFolders.includes(path)) {
              newMatrix.workingFolders.push(path);
            }
          } else if (permission === 'output') {
            newMatrix.outputFolder = path;
          }
        });

        // Apply the changes
        await filePermissionManager.updatePermissionMatrix(newMatrix);

        // Emit WebSocket update
        if (this.io) {
          this.io.emit('server:permissions-updated', { permissionMatrix: newMatrix });
        }

        res.json({ success: true, message: 'Permissions updated successfully' });
        return;
      } catch (error) {
        logWithContext.error('Error assigning permissions', error as Error);
        res.status(500).json({ error: 'Failed to assign permissions' });
        return;
      }
    });

    apiRouter.post('/config/permissions/remove', async (req, res) => {
      try {
        const { paths } = req.body;
        
        if (!Array.isArray(paths)) {
          res.status(400).json({ error: 'Invalid request format' });
          return;
        }

        const validatedPaths = await Promise.all(paths.map(path => this.validateAndSanitizePath(path)));
        const currentMatrix = filePermissionManager.getPermissionMatrix();
        
        const newMatrix = {
          contextFolders: currentMatrix.contextFolders.filter(p => !validatedPaths.includes(p)),
          workingFolders: currentMatrix.workingFolders.filter(p => !validatedPaths.includes(p)),
          outputFolder: validatedPaths.includes(currentMatrix.outputFolder) ? '' : currentMatrix.outputFolder,
        };

        await filePermissionManager.updatePermissionMatrix(newMatrix);

        // Emit WebSocket update
        if (this.io) {
          this.io.emit('server:permissions-updated', { permissionMatrix: newMatrix });
        }

        res.json({ success: true, message: 'Permissions removed successfully' });
        return;
      } catch (error) {
        logWithContext.error('Error removing permissions', error as Error);
        res.status(500).json({ error: 'Failed to remove permissions' });
        return;
      }
    });

    this.app.use('/api', apiRouter);

    // Serve frontend for all other routes (SPA support) - only in production
    this.app.get('*', (req, res) => {
      const distPath = path.join(process.cwd(), '../frontend/dist/index.html');
      import('fs').then(fs => {
        if (fs.existsSync(distPath)) {
          res.sendFile(distPath);
        } else {
          // In development mode, show info about where to access the frontend
          res.json({
            message: 'MCP Research File Server - API Only',
            frontend: 'http://localhost:3004',
            api: `http://localhost:${config.server.webUIPort}/api`,
            endpoints: {
              health: '/api/health',
              config: '/api/config',
              files: '/api/files',
              stats: '/api/stats'
            }
          });
        }
      }).catch(() => {
        res.json({
          message: 'MCP Research File Server - API Only',
          frontend: 'http://localhost:3004',
          api: `http://localhost:${config.server.webUIPort}/api`
        });
      });
    });
  }

  private async validateAndSanitizePath(requestedPath: string): Promise<string> {
    const path = await import('path');
    const os = await import('os');
    
    // Default to user home directory if no path provided
    if (!requestedPath || requestedPath === '') {
      return os.homedir();
    }
    
    // Resolve and normalize the path
    const resolvedPath = path.resolve(requestedPath);
    const normalizedPath = path.normalize(resolvedPath);
    
    // Security checks
    if (normalizedPath.includes('..')) {
      throw new Error('Directory traversal not allowed');
    }
    
    // Prevent access to system directories on Windows
    if (process.platform === 'win32') {
      const systemDirs = ['C:\\Windows', 'C:\\System32', 'C:\\Program Files'];
      if (systemDirs.some(sysDir => normalizedPath.startsWith(sysDir))) {
        throw new Error('Access to system directories not allowed');
      }
    }
    
    // Prevent access to system directories on Unix-like systems
    if (process.platform !== 'win32') {
      const systemDirs = ['/etc', '/proc', '/sys', '/dev', '/boot'];
      if (systemDirs.some(sysDir => normalizedPath.startsWith(sysDir))) {
        throw new Error('Access to system directories not allowed');
      }
    }
    
    return normalizedPath;
  }

  private setupSocketHandlers(): void {
    if (!this.io) return;

    this.io.on('connection', (socket) => {
      logWithContext.info('WebSocket client connected', { socketId: socket.id });

      // Send initial data
      socket.emit('server:status', {
        status: 'healthy',
        timestamp: new Date().toISOString(),
      });

      // Handle client events
      socket.on('client:request-config', async () => {
        try {
          const permissionMatrix = filePermissionManager.getPermissionMatrix();
          socket.emit('server:config', {
            permissionMatrix,
            serverConfig: {
              mcpPort: config.server.mcpPort,
              webUIPort: config.server.webUIPort,
              enableCaching: config.server.enableCaching,
              logLevel: config.server.logLevel,
            },
            processingConfig: config.processing,
          });
        } catch (error) {
          logWithContext.error('Error sending config via WebSocket', error as Error);
          socket.emit('server:error', { message: 'Failed to fetch configuration' });
        }
      });

      socket.on('client:request-stats', async () => {
        try {
          const stats = await filePermissionManager.getUsageStats();
          socket.emit('server:stats', stats);
        } catch (error) {
          logWithContext.error('Error sending stats via WebSocket', error as Error);
          socket.emit('server:error', { message: 'Failed to fetch stats' });
        }
      });

      socket.on('disconnect', (reason) => {
        logWithContext.info('WebSocket client disconnected', { 
          socketId: socket.id, 
          reason 
        });
      });
    });
  }

  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Create HTTP server
        this.httpServer = createServer(this.app);

        // Setup Socket.IO
        this.io = new SocketIOServer(this.httpServer, {
          cors: {
            origin: "http://localhost:3005",
            methods: ["GET", "POST"]
          }
        });

        // Setup Socket.IO event handlers
        this.setupSocketHandlers();

        this.httpServer.listen(config.server.webUIPort, config.server.host, () => {
          logWithContext.info('Web server started', {
            port: config.server.webUIPort,
            host: config.server.host,
            url: `http://${config.server.host}:${config.server.webUIPort}`,
            websocket: true,
          });
          resolve();
        });

        this.httpServer.on('error', (error: Error) => {
          logWithContext.error('Web server error', error);
          reject(error);
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  async stop(): Promise<void> {
    return new Promise((resolve) => {
      if (this.io) {
        this.io.close();
      }
      
      if (this.httpServer) {
        this.httpServer.close(() => {
          logWithContext.info('Web server stopped');
          resolve();
        });
      } else {
        resolve();
      }
    });
  }
}

export default WebServer;