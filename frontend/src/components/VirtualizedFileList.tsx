import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { FixedSizeList as List } from 'react-window';
import { 
  Folder, 
  FolderOpen, 
  File, 
  ChevronRight, 
  ChevronDown,
  Eye,
  Edit,
  Upload
} from 'lucide-react';

interface FileSystemEntry {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  modified?: string;
  permissions?: 'context' | 'working' | 'output' | null;
  level: number;
  isExpanded?: boolean;
  hasChildren?: boolean;
}

interface VirtualizedFileListProps {
  entries: FileSystemEntry[];
  selectedPaths: Set<string>;
  expandedFolders: Set<string>;
  onToggleSelection: (path: string) => void;
  onToggleFolder: (path: string) => void;
  onDoubleClick?: (entry: FileSystemEntry) => void;
  searchQuery?: string;
  height?: number;
}

interface ListItemProps {
  index: number;
  style: React.CSSProperties;
  data: {
    filteredEntries: FileSystemEntry[];
    selectedPaths: Set<string>;
    expandedFolders: Set<string>;
    onToggleSelection: (path: string) => void;
    onToggleFolder: (path: string) => void;
    onDoubleClick?: (entry: FileSystemEntry) => void;
    searchQuery?: string;
  };
}

const ListItem: React.FC<ListItemProps> = ({ index, style, data }) => {
  const {
    filteredEntries,
    selectedPaths,
    expandedFolders,
    onToggleSelection,
    onToggleFolder,
    onDoubleClick,
    searchQuery
  } = data;

  const entry = filteredEntries[index];
  if (!entry) return null;

  const isSelected = selectedPaths.has(entry.path);
  const isExpanded = expandedFolders.has(entry.path);

  const getPermissionIcon = (permission: string | null) => {
    switch (permission) {
      case 'context': return <Eye className="w-4 h-4 text-blue-600" />;
      case 'working': return <Edit className="w-4 h-4 text-green-600" />;
      case 'output': return <Upload className="w-4 h-4 text-purple-600" />;
      default: return null;
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

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const highlightText = (text: string, query: string) => {
    if (!query) return text;
    
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, i) => 
      regex.test(part) ? 
        <span key={i} className="bg-yellow-200 text-yellow-800 font-medium">{part}</span> : 
        part
    );
  };

  const renderFileIcon = () => {
    if (entry.type === 'directory') {
      return isExpanded ? 
        <FolderOpen className="w-5 h-5 text-blue-500" /> : 
        <Folder className="w-5 h-5 text-blue-500" />;
    }
    return <File className="w-5 h-5 text-gray-500" />;
  };

  return (
    <div
      style={style}
      className={`flex items-center py-1 px-2 hover:bg-gray-50 cursor-pointer select-none ${
        isSelected ? 'bg-blue-100 hover:bg-blue-200' : ''
      }`}
      onClick={() => {
        if (entry.type === 'directory') {
          onToggleFolder(entry.path);
        } else {
          onToggleSelection(entry.path);
        }
      }}
      onDoubleClick={() => onDoubleClick?.(entry)}
    >
      {/* Indentation for nested items */}
      <div style={{ width: `${entry.level * 16}px` }} />

      {/* Expand/Collapse Arrow for directories */}
      {entry.type === 'directory' && (
        <div className="mr-1 flex-shrink-0">
          {isExpanded ? 
            <ChevronDown className="w-4 h-4 text-gray-400" /> : 
            <ChevronRight className="w-4 h-4 text-gray-400" />
          }
        </div>
      )}

      {/* File/Folder Icon */}
      <div className="mr-2 flex-shrink-0">
        {renderFileIcon()}
      </div>

      {/* Name */}
      <div className="flex-1 min-w-0 mr-2">
        <span className="text-sm text-gray-900 truncate block">
          {highlightText(entry.name, searchQuery || '')}
        </span>
      </div>

      {/* Permission Badge */}
      {entry.permissions && (
        <div className={`mr-2 px-2 py-1 rounded text-xs flex-shrink-0 ${getPermissionColor(entry.permissions)}`}>
          <div className="flex items-center">
            {getPermissionIcon(entry.permissions)}
            <span className="ml-1 capitalize">{entry.permissions}</span>
          </div>
        </div>
      )}

      {/* File Size */}
      {entry.type === 'file' && entry.size !== undefined && (
        <div className="mr-2 text-xs text-gray-500 flex-shrink-0 w-16 text-right">
          {formatFileSize(entry.size)}
        </div>
      )}

      {/* Checkbox */}
      <div className="flex-shrink-0">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onToggleSelection(entry.path)}
          onClick={(e) => e.stopPropagation()}
          className="form-checkbox h-4 w-4 text-blue-600 rounded"
        />
      </div>
    </div>
  );
};

export const VirtualizedFileList: React.FC<VirtualizedFileListProps> = ({
  entries,
  selectedPaths,
  expandedFolders,
  onToggleSelection,
  onToggleFolder,
  onDoubleClick,
  searchQuery,
  height = 400
}) => {
  const [containerHeight, setContainerHeight] = useState(height);

  // Create flattened list for virtualization
  const flattenedEntries = useMemo(() => {
    const result: FileSystemEntry[] = [];

    const addEntry = (entry: FileSystemEntry, level: number = 0) => {
      result.push({ ...entry, level });
      
      if (entry.type === 'directory' && expandedFolders.has(entry.path) && entry.children) {
        entry.children.forEach(child => addEntry(child, level + 1));
      }
    };

    entries.forEach(entry => addEntry(entry));
    return result;
  }, [entries, expandedFolders]);

  // Filter entries based on search query
  const filteredEntries = useMemo(() => {
    if (!searchQuery) return flattenedEntries;

    return flattenedEntries.filter(entry =>
      entry.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      entry.path.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [flattenedEntries, searchQuery]);

  // Adjust container height based on content
  useEffect(() => {
    const maxHeight = window.innerHeight - 300; // Reserve space for header/controls
    const contentHeight = Math.min(filteredEntries.length * 36, maxHeight);
    setContainerHeight(Math.max(contentHeight, 200));
  }, [filteredEntries.length]);

  const itemData = {
    filteredEntries,
    selectedPaths,
    expandedFolders,
    onToggleSelection,
    onToggleFolder,
    onDoubleClick,
    searchQuery
  };

  if (filteredEntries.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <div className="text-center">
          <File className="w-12 h-12 mx-auto mb-2 text-gray-300" />
          <p className="text-sm">
            {searchQuery ? 'No files match your search' : 'No files in this directory'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <List
        height={containerHeight}
        itemCount={filteredEntries.length}
        itemSize={36}
        itemData={itemData}
        overscanCount={10}
        width="100%"
      >
        {ListItem}
      </List>
    </div>
  );
};