import express from 'express';
import cors from 'cors';
import path from 'path';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { config } from '../config/index.js';
import { filePermissionManager } from '../files/permissions.js';
import { logWithContext } from '../utils/logger.js';
import type { 
  FilePermissionMatrix, 
  FileMetadata, 
  FilePermission 
} from '../types/index.js';
import { filesystemRouter } from './routers/filesystem.router.js';

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
    
    const distPath = path.join(process.cwd(), '../frontend/dist');
    try {
      import('fs').then(fs => {
        if (fs.existsSync(distPath)) {
          this.app.use(express.static(distPath));
        }
      });
    } catch (error) {
      logWithContext.info('Frontend dist directory not found - running in development mode');
    }
  }

  private setupRoutes(): void {
    const apiRouter = express.Router();
    
    // Mount the modular routers
    apiRouter.use('/filesystem', filesystemRouter);

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
        const { QdrantVectorStore } = await import('../storage/index.js');
        const vectorStore = new QdrantVectorStore();
        await vectorStore.clearAllCollections();

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

    // Health check endpoint
    apiRouter.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        version: '1.0.0',
      });
    });

    // Logs endpoint
    apiRouter.get('/logs', async (req, res) => {
      try {
        const { lines = 100 } = req.query;
        res.json({ 
          message: 'Log endpoint not fully implemented yet',
          suggestion: 'Check console logs or log file directly',
        });
      } catch (error) {
        logWithContext.error('Error fetching logs', error as Error);
        res.status(500).json({ error: 'Failed to fetch logs' });
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

        const { validateAndSanitizePath } = await import('./routers/filesystem.router.js');
        const validatedPaths = await Promise.all(paths.map(path => validateAndSanitizePath(path)));
        
        const currentMatrix = filePermissionManager.getPermissionMatrix();
        let newMatrix = { ...currentMatrix };

        validatedPaths.forEach(path => {
          newMatrix.contextFolders = newMatrix.contextFolders.filter(p => p !== path);
          newMatrix.workingFolders = newMatrix.workingFolders.filter(p => p !== path);
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

        await filePermissionManager.updatePermissionMatrix(newMatrix);
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
        
        const { validateAndSanitizePath } = await import('./routers/filesystem.router.js');
        const validatedPaths = await Promise.all(paths.map(path => validateAndSanitizePath(path)));
        const currentMatrix = filePermissionManager.getPermissionMatrix();
        
        const newMatrix = {
          contextFolders: currentMatrix.contextFolders.filter(p => !validatedPaths.includes(p)),
          workingFolders: currentMatrix.workingFolders.filter(p => !validatedPaths.includes(p)),
          outputFolder: validatedPaths.includes(currentMatrix.outputFolder) ? '' : currentMatrix.outputFolder,
        };

        await filePermissionManager.updatePermissionMatrix(newMatrix);

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

    // Serve frontend for all other routes
    this.app.get('*', (req, res) => {
      const distPath = path.join(process.cwd(), '../frontend/dist/index.html');
      import('fs').then(fs => {
        if (fs.existsSync(distPath)) {
          res.sendFile(distPath);
        } else {
          res.json({
            message: 'MCP Research File Server - API Only',
            frontend: 'http://localhost:3004',
            api: 'http://localhost:3003/api',
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
          api: 'http://localhost:3003/api'
        });
      });
    });
  }
  
  private setupSocketHandlers(): void {
    if (!this.io) return;
    this.io.on('connection', (socket) => {
      logWithContext.info('WebSocket client connected', { socketId: socket.id });

      socket.emit('server:status', {
        status: 'healthy',
        timestamp: new Date().toISOString(),
      });

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
        this.httpServer = createServer(this.app);

        this.io = new SocketIOServer(this.httpServer, {
          cors: {
            origin: "http://localhost:3005",
            methods: ["GET", "POST"]
          }
        });

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