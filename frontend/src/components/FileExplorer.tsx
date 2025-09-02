import React, { useState, useEffect, useCallback } from 'react';
import { 
  Folder, 
  FolderOpen, 
  File, 
  ChevronRight, 
  ChevronDown, 
  Home,
  Check,
  X,
  Eye,
  Edit,
  Upload,
  RefreshCw,
  Settings,
  Undo,
  Redo,
  Zap,
  Search
} from 'lucide-react';
import { PermissionAssignmentPanel } from './PermissionAssignmentPanel';
import { SearchBar } from './SearchBar';
import { VirtualizedFileList } from './VirtualizedFileList';
import { LoadingSkeleton, SearchLoading } from './LoadingSkeleton';
import { BulkOperationsBar } from './BulkOperationsBar';
import { AddressBar } from './FileExplorer/AddressBar';
import { useUndoRedo } from '../hooks/useUndoRedo';
import { useWebSocketEvent } from '../hooks/useWebSocket';

interface FileSystemEntry {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  modified?: string;
  permissions?: 'context' | 'working' | 'output' | null;
  children?: FileSystemEntry[];
  isExpanded?: boolean;
}

interface FileExplorerProps {
  onSelectionChange?: (selected: string[]) => void;
  onPermissionAssign?: (paths: string[], permission: 'context' | 'working' | 'output') => void;
}

export const FileExplorer: React.FC<FileExplorerProps> = ({ 
  onSelectionChange, 
  onPermissionAssign 
}) => {
  const [currentPath, setCurrentPath] = useState<string>('');
  const [entries, setEntries] = useState<FileSystemEntry[]>([]);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [currentPermissions, setCurrentPermissions] = useState<Record<string, 'context' | 'working' | 'output' | null>>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFilters, setSearchFilters] = useState<any>({});
  const [useVirtualization, setUseVirtualization] = useState(false);
  const [isSearchActive, setIsSearchActive] = useState(false);

  // Initialize undo/redo functionality
  const {
    addAction,
    undo,
    redo,
    canUndo,
    canRedo,
    getUndoDescription,
    getRedoDescription
  } = useUndoRedo();

  // WebSocket event handlers for real-time updates
  useWebSocketEvent('permission-updated', useCallback((data: { path: string; permission: string | null }) => {
    setCurrentPermissions(prev => ({
      ...prev,
      [data.path]: data.permission as any
    }));
    
    // Update entries to reflect new permissions
    setEntries(prevEntries => 
      prevEntries.map(entry => 
        entry.path === data.path 
          ? { ...entry, permissions: data.permission as any }
          : entry
      )
    );
  }, []));

  useWebSocketEvent('filesystem-changed', useCallback((data: { path: string; type: 'created' | 'deleted' | 'modified' }) => {
    // Refresh the current directory if a file/folder was changed
    if (data.path.startsWith(currentPath)) {
      fetchDirectoryContents(currentPath);
    }
  }, [currentPath]));

  const fetchDirectoryContents = async (path: string = '') => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/filesystem/browse?path=${encodeURIComponent(path)}`);
      if (!response.ok) {
        throw new Error(`Failed to browse directory: ${response.statusText}`);
      }

      const data = await response.json();
      setEntries(data.entries || []);
      setCurrentPath(data.currentPath || path);
      
      // Update permissions mapping
      const permissionsMap: Record<string, 'context' | 'working' | 'output' | null> = {};
      (data.entries || []).forEach((entry: FileSystemEntry) => {
        permissionsMap[entry.path] = entry.permissions || null;
      });
      setCurrentPermissions(prev => ({ ...prev, ...permissionsMap }));
      
      // Enable virtualization for large directories
      setUseVirtualization((data.entries || []).length > 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load directory');
      console.error('Directory fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleFolder = async (folderPath: string) => {
    const newExpanded = new Set(expandedFolders);
    
    if (expandedFolders.has(folderPath)) {
      newExpanded.delete(folderPath);
    } else {
      newExpanded.add(folderPath);
      
      // Fetch children if not already loaded
      try {
        const response = await fetch(`/api/filesystem/browse?path=${encodeURIComponent(folderPath)}`);
        if (response.ok) {
          const data = await response.json();
          // Update the entries with children data
          setEntries(prevEntries => updateEntriesWithChildren(prevEntries, folderPath, data.entries));
        }
      } catch (err) {
        console.error('Failed to load folder contents:', err);
      }
    }
    
    setExpandedFolders(newExpanded);
  };

  const updateEntriesWithChildren = (entries: FileSystemEntry[], targetPath: string, children: FileSystemEntry[]): FileSystemEntry[] => {
    return entries.map(entry => {
      if (entry.path === targetPath && entry.type === 'directory') {
        return { ...entry, children, isExpanded: true };
      }
      if (entry.children) {
        return { ...entry, children: updateEntriesWithChildren(entry.children, targetPath, children) };
      }
      return entry;
    });
  };

  const navigateToDirectory = (path: string) => {
    setCurrentPath(path);
    fetchDirectoryContents(path);
    setSelectedPaths(new Set());
  };

  const toggleSelection = (path: string) => {
    const newSelected = new Set(selectedPaths);
    if (newSelected.has(path)) {
      newSelected.delete(path);
    } else {
      newSelected.add(path);
    }
    setSelectedPaths(newSelected);
    onSelectionChange?.(Array.from(newSelected));
  };

  const handlePermissionAssign = async (paths: string[], permission: 'context' | 'working' | 'output') => {
    try {
      // Store old permissions for undo
      const oldPermissions: Record<string, string | null> = {};
      paths.forEach(path => {
        oldPermissions[path] = currentPermissions[path];
      });

      await onPermissionAssign?.(paths, permission);
      
      // Update local permissions state
      const updatedPermissions = { ...currentPermissions };
      paths.forEach(path => {
        updatedPermissions[path] = permission;
      });
      setCurrentPermissions(updatedPermissions);
      
      // Update entries to reflect new permissions
      const updatedEntries = entries.map(entry => ({
        ...entry,
        permissions: paths.includes(entry.path) ? permission : entry.permissions
      }));
      setEntries(updatedEntries);

      // Add to undo history
      const newPermissions: Record<string, string | null> = {};
      paths.forEach(path => {
        newPermissions[path] = permission;
      });

      addAction({
        type: 'permission-assign',
        data: {
          paths,
          oldPermissions,
          newPermissions
        },
        description: `Assign ${permission} permission to ${paths.length} item${paths.length > 1 ? 's' : ''}`
      });
      
      setSelectedPaths(new Set());
      setShowPermissionPanel(false);
    } catch (error) {
      console.error('Failed to assign permissions:', error);
    }
  };

  const handlePermissionRemove = async (paths: string[]) => {
    try {
      // Call backend to remove permissions
      const response = await fetch('/api/permissions/remove', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ paths }),
      });

      if (!response.ok) {
        throw new Error(`Failed to remove permissions: ${response.statusText}`);
      }
      
      // Update local permissions state
      const updatedPermissions = { ...currentPermissions };
      paths.forEach(path => {
        updatedPermissions[path] = null;
      });
      setCurrentPermissions(updatedPermissions);
      
      // Update entries to reflect removed permissions
      const updatedEntries = entries.map(entry => ({
        ...entry,
        permissions: paths.includes(entry.path) ? null : entry.permissions
      }));
      setEntries(updatedEntries);
      
      setSelectedPaths(new Set());
      setShowPermissionPanel(false);
    } catch (error) {
      console.error('Failed to remove permissions:', error);
    }
  };

  const getPermissionColor = (permission: string | null) => {
    switch (permission) {
      case 'context': return 'text-blue-600 bg-blue-50';
      case 'working': return 'text-green-600 bg-green-50';
      case 'output': return 'text-purple-600 bg-purple-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getPermissionIcon = (permission: string | null) => {
    switch (permission) {
      case 'context': return <Eye className="w-4 h-4" />;
      case 'working': return <Edit className="w-4 h-4" />;
      case 'output': return <Upload className="w-4 h-4" />;
      default: return null;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };


  // Search functionality
  const handleSearch = useCallback(async (query: string, filters: any) => {
    setSearchQuery(query);
    setSearchFilters(filters);
    setIsSearchActive(query.length > 0);

    if (query.length > 0) {
      try {
        setLoading(true);
        
        const params = new URLSearchParams({
          query,
          path: currentPath,
          includeHidden: filters.includeHidden.toString(),
          caseSensitive: filters.caseSensitive.toString()
        });

        if (filters.fileTypes.length > 0) {
          params.append('fileTypes', filters.fileTypes.join(','));
        }

        if (filters.permissions.length > 0) {
          params.append('permissions', filters.permissions.join(','));
        }

        const response = await fetch(`/api/filesystem/search?${params}`);
        if (response.ok) {
          const data = await response.json();
          setEntries(data.results || []);
        }
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setLoading(false);
      }
    }
  }, [currentPath]);

  const handleClearSearch = useCallback(() => {
    setSearchQuery('');
    setSearchFilters({});
    setIsSearchActive(false);
    fetchDirectoryContents(currentPath);
  }, [currentPath]);

  // Bulk operations
  const handleSelectAll = useCallback(() => {
    const allPaths = new Set(entries.map(entry => entry.path));
    setSelectedPaths(allPaths);
    onSelectionChange?.(Array.from(allPaths));
  }, [entries, onSelectionChange]);

  const handleSelectVisible = useCallback(() => {
    handleSelectAll();
  }, [handleSelectAll]);

  const handleInvertSelection = useCallback(() => {
    const allPaths = new Set(entries.map(entry => entry.path));
    const newSelection = new Set<string>();
    
    allPaths.forEach(path => {
      if (!selectedPaths.has(path)) {
        newSelection.add(path);
      }
    });
    
    setSelectedPaths(newSelection);
    onSelectionChange?.(Array.from(newSelection));
  }, [entries, selectedPaths, onSelectionChange]);

  const handleExportSelection = useCallback((paths: string[]) => {
    const data = {
      timestamp: new Date().toISOString(),
      paths,
      permissions: paths.map(path => ({
        path,
        permission: currentPermissions[path] || null
      }))
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mcp-permissions-${new Date().getTime()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [currentPermissions]);

  const handleCopyPaths = useCallback(async (paths: string[]) => {
    try {
      await navigator.clipboard.writeText(paths.join('\n'));
      // Could show a toast notification here
    } catch (error) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = paths.join('\n');
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle keyboard shortcuts when not in an input field
      if (document.activeElement?.tagName === 'INPUT') return;

      switch (e.key) {
        case 'Escape':
          setSelectedPaths(new Set());
          setShowPermissionPanel(false);
          if (isSearchActive) {
            handleClearSearch();
          }
          break;
        
        case '/':
          e.preventDefault();
          // Focus search input
          document.querySelector('input[placeholder*="Search"]')?.focus();
          break;

        case 'a':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            // Select all visible items
            const allPaths = new Set(entries.map(entry => entry.path));
            setSelectedPaths(allPaths);
            onSelectionChange?.(Array.from(allPaths));
          }
          break;

        case 'z':
          if ((e.ctrlKey || e.metaKey) && !e.shiftKey && canUndo) {
            e.preventDefault();
            handleUndo();
          } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && canRedo) {
            e.preventDefault();
            handleRedo();
          }
          break;

        case 'Enter':
          if (selectedPaths.size > 0) {
            setShowPermissionPanel(true);
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedPaths, isSearchActive, canUndo, canRedo, entries, onSelectionChange]);

  // Undo/Redo handlers
  const handleUndo = useCallback(async () => {
    await undo(
      async (paths, permissions) => {
        // Restore permissions
        for (const [path, permission] of Object.entries(permissions)) {
          if (permission) {
            await onPermissionAssign?.([path], permission as any);
          } else {
            await handlePermissionRemove([path]);
          }
        }
      },
      (selection) => {
        setSelectedPaths(new Set(selection));
        onSelectionChange?.(selection);
      }
    );
  }, [undo, onPermissionAssign]);

  const handleRedo = useCallback(async () => {
    await redo(
      async (paths, permissions) => {
        // Restore permissions
        for (const [path, permission] of Object.entries(permissions)) {
          if (permission) {
            await onPermissionAssign?.([path], permission as any);
          } else {
            await handlePermissionRemove([path]);
          }
        }
      },
      (selection) => {
        setSelectedPaths(new Set(selection));
        onSelectionChange?.(selection);
      }
    );
  }, [redo, onPermissionAssign]);

  useEffect(() => {
    fetchDirectoryContents();
  }, []);

  const renderFileIcon = (entry: FileSystemEntry) => {
    if (entry.type === 'directory') {
      return expandedFolders.has(entry.path) ? 
        <FolderOpen className="w-5 h-5 text-blue-500" /> : 
        <Folder className="w-5 h-5 text-blue-500" />;
    }
    return <File className="w-5 h-5 text-gray-500" />;
  };

  const renderTreeEntry = (entry: FileSystemEntry, level: number = 0) => (
    <div key={entry.path} className="select-none">
      <div
        className={`flex items-center py-1 px-2 hover:bg-gray-100 cursor-pointer ${
          selectedPaths.has(entry.path) ? 'bg-blue-100' : ''
        }`}
        style={{ paddingLeft: `${level * 20 + 8}px` }}
        onClick={() => {
          if (entry.type === 'directory') {
            toggleFolder(entry.path);
          } else {
            toggleSelection(entry.path);
          }
        }}
      >
        {/* Permission indicator dot - positioned first */}
        <div 
          className={`mr-2 w-2 h-2 rounded-full flex-shrink-0 ${
            currentPermissions[entry.path] === 'context' ? 'bg-blue-500' :
            currentPermissions[entry.path] === 'working' ? 'bg-green-500' :
            currentPermissions[entry.path] === 'output' ? 'bg-purple-500' :
            'bg-gray-300'
          }`}
          title={currentPermissions[entry.path] ? `Permission: ${currentPermissions[entry.path]}` : 'No permission assigned'}
        />
        
        {entry.type === 'directory' && (
          <div className="mr-1">
            {expandedFolders.has(entry.path) ? 
              <ChevronDown className="w-4 h-4" /> : 
              <ChevronRight className="w-4 h-4" />
            }
          </div>
        )}
        
        <div className="mr-2">
          {renderFileIcon(entry)}
        </div>
        
        <div className="flex-1 min-w-0">
          <span className="text-sm text-gray-900 truncate">{entry.name}</span>
        </div>
        
        {entry.type === 'file' && entry.size !== undefined && (
          <div className="ml-2 text-xs text-gray-500">
            {formatFileSize(entry.size)}
          </div>
        )}
        
        <div className="ml-2">
          <input
            type="checkbox"
            checked={selectedPaths.has(entry.path)}
            onChange={() => toggleSelection(entry.path)}
            onClick={(e) => e.stopPropagation()}
            className="form-checkbox h-4 w-4 text-blue-600"
          />
        </div>
      </div>
      
      {entry.type === 'directory' && expandedFolders.has(entry.path) && entry.children && (
        <div>
          {entry.children.map(child => renderTreeEntry(child, level + 1))}
        </div>
      )}
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header with address bar and actions */}
      <div className="flex-shrink-0 border-b border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex-1 mr-4">
            <AddressBar
              currentPath={currentPath}
              onNavigate={navigateToDirectory}
              isNavigating={loading}
            />
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Undo/Redo Controls */}
            <button
              onClick={handleUndo}
              disabled={!canUndo}
              className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded"
              title={getUndoDescription()}
            >
              <Undo className="w-4 h-4" />
            </button>
            <button
              onClick={handleRedo}
              disabled={!canRedo}
              className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded"
              title={getRedoDescription()}
            >
              <Redo className="w-4 h-4" />
            </button>

            {/* Performance Toggle */}
            {entries.length > 50 && (
              <button
                onClick={() => setUseVirtualization(!useVirtualization)}
                className={`p-2 rounded ${useVirtualization ? 'text-blue-600 bg-blue-50' : 'text-gray-400 hover:text-gray-600'}`}
                title={`${useVirtualization ? 'Disable' : 'Enable'} virtualization for better performance`}
              >
                <Zap className="w-4 h-4" />
              </button>
            )}

            {/* Refresh */}
            <button
              onClick={() => isSearchActive ? handleClearSearch() : fetchDirectoryContents(currentPath)}
              className="p-2 text-gray-400 hover:text-gray-600 rounded"
              title={isSearchActive ? "Clear search" : "Refresh"}
              disabled={loading}
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Selection info and permission panel toggle */}
        {selectedPaths.size > 0 && (
          <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded">
            <div className="flex items-center">
              <Check className="w-5 h-5 text-blue-600 mr-2" />
              <span className="text-sm font-medium text-blue-800">
                {selectedPaths.size} item{selectedPaths.size > 1 ? 's' : ''} selected
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setSelectedPaths(new Set())}
                className="px-3 py-2 text-blue-600 hover:text-blue-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Search Bar */}
        <div className="px-4 pb-2">
          <SearchBar
            onSearch={handleSearch}
            onClear={handleClearSearch}
            placeholder="Search files and folders... (Press / to focus)"
          />
          {isSearchActive && (
            <div className="mt-2 flex items-center text-sm text-gray-600">
              <Search className="w-4 h-4 mr-1" />
              <span>
                {entries.length} result{entries.length !== 1 ? 's' : ''} for "{searchQuery}"
              </span>
              {useVirtualization && (
                <div className="ml-2 flex items-center text-blue-600">
                  <Zap className="w-3 h-3 mr-1" />
                  <span className="text-xs">Virtualized</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bulk Operations Bar */}
      {entries.length > 0 && (
        <BulkOperationsBar
          totalItems={entries.length}
          selectedPaths={Array.from(selectedPaths)}
          onSelectAll={handleSelectAll}
          onClearSelection={() => setSelectedPaths(new Set())}
          onSelectVisible={handleSelectVisible}
          onInvertSelection={handleInvertSelection}
          onBulkPermissionAssign={handlePermissionAssign}
          onExportSelection={handleExportSelection}
          onCopyPaths={handleCopyPaths}
          currentPermissions={currentPermissions}
        />
      )}

      {/* File tree */}
      <div className="flex-1 overflow-auto">
        {loading && (
          isSearchActive && searchQuery ? (
            <SearchLoading query={searchQuery} />
          ) : (
            <LoadingSkeleton rows={10} />
          )
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded m-4">
            <div className="flex items-center">
              <X className="w-5 h-5 text-red-400 mr-2" />
              <span className="text-red-700">{error}</span>
            </div>
          </div>
        )}

        {!loading && !error && (
          <div className="py-2">
            {useVirtualization && entries.length > 100 ? (
              <VirtualizedFileList
                entries={entries}
                selectedPaths={selectedPaths}
                expandedFolders={expandedFolders}
                onToggleSelection={toggleSelection}
                onToggleFolder={toggleFolder}
                searchQuery={searchQuery}
              />
            ) : (
              entries.map(entry => renderTreeEntry(entry))
            )}
          </div>
        )}
      </div>


    </div>
  );
};