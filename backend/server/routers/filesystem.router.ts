import express from 'express';
import { filePermissionManager } from '../../files/permissions.js';
import { logWithContext } from '../../utils/logger.js';
import { validateAndSanitizePath, isAccessibleDirectory, isDirectoryOrJunction } from '../../utils/file-utils.js';

const router = express.Router();


// Path validation endpoints
router.post('/validate-path', async (req, res) => {
  try {
    const { path: requestedPath } = req.body;
    
    if (!requestedPath) {
      res.status(400).json({ error: 'Path is required' });
      return;
    }

    const fs = await import('fs/promises');
    const path = await import('path');
    
    try {
      const normalizedPath = await validateAndSanitizePath(requestedPath);
      
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
      let suggestion = null;
      try {
        const corrections = [
          requestedPath.replace(/\//g, '\\'),
          requestedPath.replace(/\\\\/g, '\\'),
          requestedPath.replace(/^~/, process.env.USERPROFILE || 'C:\\Users'),
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

router.get('/common-paths', (req, res) => {
  try {
    const userProfile = process.env.USERPROFILE || 'C:\\Users\\DefaultUser';
    
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

// File system browsing endpoints
router.get('/browse', async (req, res) => {
  try {
    const { path: requestedPath = '' } = req.query;
    const targetPath = await validateAndSanitizePath(requestedPath as string);
    
    const fs = await import('fs/promises');
    const path = await import('path');
    
    const entries = await fs.readdir(targetPath, { withFileTypes: true });
    const items = await Promise.all(entries.map(async (entry) => {
      const fullPath = path.join(targetPath, entry.name);
      
      if (!isAccessibleDirectory(entry.name, fullPath)) {
        return null;
      }
      
      try {
        const { isDirectory, stats } = await isDirectoryOrJunction(fullPath);
        
        if (isDirectory) {
          try {
            await fs.access(fullPath, fs.constants.R_OK);
          } catch {
            return null;
          }
        }
        
        const permissionResult = await (async () => {
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
        return null;
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

router.get('/tree', async (req, res) => {
  try {
    const { path: requestedPath = '', depth = '2' } = req.query;
    const targetPath = await validateAndSanitizePath(requestedPath as string);
    const maxDepth = Math.min(parseInt(depth as string) || 2, 5);
    
    const buildTree = async (currentPath: string, currentDepth: number): Promise<any> => {
      if (currentDepth >= maxDepth) return null;
      
      const fs = await import('fs/promises');
      const path = await import('path');
      
      try {
        const entries = await fs.readdir(currentPath, { withFileTypes: true });
        const directories = entries.filter(entry => {
          if (!entry.isDirectory()) return false;
          const fullPath = path.join(currentPath, entry.name);
          return isAccessibleDirectory(entry.name, fullPath);
        });
        
        const children = await Promise.all(directories.map(async (dir) => {
          const dirPath = path.join(currentPath, dir.name);
          try {
            await fs.access(dirPath, fs.constants.R_OK);
          } catch {
            return null;
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


export const filesystemRouter = router;