import express from 'express';
import cors from 'cors';
import { createServer } from 'http';
import { Server } from 'socket.io';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const app = express();
const PORT = 3007;

// Permission storage - simple JSON file-based system
const PERMISSIONS_FILE = path.join(process.cwd(), 'file-permissions.json');
let filePermissions = new Map(); // filepath -> permission type

// Permission types
const PERMISSION_TYPES = {
  CONTEXT: 'context',     // read-only research files
  WORKING: 'working',     // read-write files
  OUTPUT: 'output'        // agent-controlled output files
};

// Initialize permissions from file
async function loadPermissions() {
  try {
    const data = await fs.readFile(PERMISSIONS_FILE, 'utf-8');
    const permissionsObj = JSON.parse(data);
    filePermissions = new Map(Object.entries(permissionsObj));
    console.log(`Loaded ${filePermissions.size} file permissions`);
  } catch (error) {
    console.log('No existing permissions file found, starting with empty permissions');
    filePermissions = new Map();
  }
}

// Save permissions to file
async function savePermissions() {
  try {
    const permissionsObj = Object.fromEntries(filePermissions);
    await fs.writeFile(PERMISSIONS_FILE, JSON.stringify(permissionsObj, null, 2), 'utf-8');
  } catch (error) {
    console.error('Failed to save permissions:', error);
  }
}

// Get permission for a file path
function getFilePermission(filePath) {
  const normalizedPath = path.normalize(filePath);
  return filePermissions.get(normalizedPath) || null;
}

// Set permission for a file path
async function setFilePermission(filePath, permission) {
  const normalizedPath = path.normalize(filePath);
  if (Object.values(PERMISSION_TYPES).includes(permission)) {
    filePermissions.set(normalizedPath, permission);
    await savePermissions();
    return true;
  }
  return false;
}

// Initialize permissions on startup
await loadPermissions();

// Create HTTP server and Socket.IO server
const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: {
    origin: ["http://localhost:3004", "http://localhost:3005"],
    methods: ["GET", "POST"],
    credentials: true
  },
  transports: ['websocket', 'polling']
});

// Middleware
app.use(cors());
app.use(express.json());

// Socket.IO connection handling
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  
  // Handle file change subscriptions
  socket.on('subscribe-file-changes', (data) => {
    console.log('Client subscribed to file changes:', data.paths);
    socket.join('file-changes');
  });
  
  socket.on('unsubscribe-file-changes', (data) => {
    console.log('Client unsubscribed from file changes:', data.paths);
    socket.leave('file-changes');
  });
  
  // Handle system status requests
  socket.on('request-system-status', () => {
    console.log('Client requested system status');
    socket.emit('system-status', {
      fileSystem: true,
      permissions: true,
      webSocket: true,
      totalFiles: 5,
      readOnlyFiles: 1,
      readWriteFiles: 1,
      agentFiles: 3,
      totalSize: 10485760
    });
  });
  
  // Handle indexing requests
  socket.on('start-indexing', () => {
    console.log('Client requested start indexing');
    socket.emit('indexing-progress', { progress: 100, status: 'completed' });
  });
  
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Basic config endpoint
app.get('/api/config', (req, res) => {
  res.json({
    server: {
      name: 'MCP Research File Server (Test)',
      version: '1.0.0-test',
      status: 'running'
    },
    permissions: {
      contextFolders: [],
      workingFolders: [],
      outputFolder: './output'
    },
    features: {
      searchEnabled: false,
      processingEnabled: false
    }
  });
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Simple file listing endpoint
app.get('/api/files', (req, res) => {
  res.json({
    files: [
      { name: 'example.txt', type: 'text', size: 1024 },
      { name: 'sample.pdf', type: 'pdf', size: 2048 }
    ]
  });
});

// Stats endpoint for frontend dashboard
app.get('/api/stats', (req, res) => {
  res.json({
    contextFiles: 3,
    workingFiles: 5,
    outputFiles: 2,
    totalSize: 10485760, // 10MB in bytes
    lastAccess: new Date().toISOString()
  });
});

// Filesystem endpoints for file explorer
app.get('/api/filesystem/browse', async (req, res) => {
  try {
    const targetPath = req.query.path || process.cwd();
    console.log(`Browsing directory: ${targetPath}`);
    
    // Read directory contents
    const dirEntries = await fs.readdir(targetPath, { withFileTypes: true });
    const items = [];
    
    // Process each entry
    for (const entry of dirEntries) {
      try {
        const fullPath = path.join(targetPath, entry.name);
        const stats = await fs.stat(fullPath);
        
        items.push({
          name: entry.name,
          type: entry.isDirectory() ? 'directory' : 'file',
          size: entry.isDirectory() ? 0 : stats.size,
          modified: stats.mtime.toISOString(),
          permission: getFilePermission(fullPath)
        });
      } catch (entryError) {
        console.warn(`Failed to process entry ${entry.name}:`, entryError.message);
        // Continue processing other entries
      }
    }
    
    res.json({
      currentPath: targetPath,
      items: items.sort((a, b) => {
        // Sort directories first, then files
        if (a.type !== b.type) {
          return a.type === 'directory' ? -1 : 1;
        }
        return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
      })
    });
    
  } catch (error) {
    console.error('Directory browse error:', error);
    res.status(500).json({
      error: 'Failed to browse directory',
      message: error.message,
      currentPath: req.query.path || process.cwd(),
      items: []
    });
  }
});

app.get('/api/filesystem/common-paths', (req, res) => {
  res.json({
    paths: [
      { name: 'Desktop', path: 'C:\\Users\\Public\\Desktop', icon: 'desktop' },
      { name: 'Documents', path: 'C:\\Users\\Documents', icon: 'folder' },
      { name: 'Downloads', path: 'C:\\Users\\Downloads', icon: 'download' },
      { name: 'Pictures', path: 'C:\\Users\\Pictures', icon: 'image' }
    ]
  });
});

app.post('/api/filesystem/validate-path', (req, res) => {
  const { path } = req.body;
  res.json({
    isValid: true,
    exists: true,
    type: 'directory'
  });
});

app.get('/api/filesystem/search', (req, res) => {
  const query = req.query.query || '';
  res.json({
    results: [
      { name: `${query}_result1.txt`, path: `C:\\Users\\Documents\\${query}_result1.txt`, type: 'file', size: 512 },
      { name: `${query}_result2.pdf`, path: `C:\\Users\\Downloads\\${query}_result2.pdf`, type: 'file', size: 1024 }
    ]
  });
});

// File permission endpoints
app.get('/api/filesystem/permissions/:*', (req, res) => {
  try {
    const filePath = req.params[0]; // Get the full path from the wildcard
    if (!filePath) {
      return res.status(400).json({ error: 'File path is required' });
    }
    
    const permission = getFilePermission(filePath);
    res.json({
      path: filePath,
      permission: permission,
      availablePermissions: Object.values(PERMISSION_TYPES)
    });
  } catch (error) {
    console.error('Get permission error:', error);
    res.status(500).json({
      error: 'Failed to get file permission',
      message: error.message
    });
  }
});

app.post('/api/filesystem/permissions', async (req, res) => {
  try {
    const { path: filePath, permission } = req.body;
    
    if (!filePath) {
      return res.status(400).json({ error: 'File path is required' });
    }
    
    if (!permission) {
      return res.status(400).json({ error: 'Permission type is required' });
    }
    
    if (!Object.values(PERMISSION_TYPES).includes(permission)) {
      return res.status(400).json({
        error: 'Invalid permission type',
        availablePermissions: Object.values(PERMISSION_TYPES)
      });
    }
    
    // Check if file exists
    try {
      await fs.access(filePath);
    } catch {
      return res.status(404).json({ error: 'File or directory not found' });
    }
    
    const success = await setFilePermission(filePath, permission);
    
    if (success) {
      console.log(`Set permission for ${filePath}: ${permission}`);
      res.json({
        success: true,
        path: filePath,
        permission: permission,
        message: `Permission set to ${permission}`
      });
    } else {
      res.status(500).json({ error: 'Failed to set permission' });
    }
  } catch (error) {
    console.error('Set permission error:', error);
    res.status(500).json({
      error: 'Failed to set file permission',
      message: error.message
    });
  }
});

app.get('/api/filesystem/permission-types', (req, res) => {
  res.json({
    types: PERMISSION_TYPES,
    descriptions: {
      [PERMISSION_TYPES.CONTEXT]: 'Read-only research files',
      [PERMISSION_TYPES.WORKING]: 'Read-write files for active work',
      [PERMISSION_TYPES.OUTPUT]: 'Agent-controlled output files'
    }
  });
});

httpServer.listen(PORT, () => {
  console.log(`Test server running on http://localhost:${PORT}`);
  console.log(`Frontend should connect to this server for testing`);
  console.log(`Socket.IO server ready for WebSocket connections`);
});