import React, { useState, useCallback } from 'react';
import { FileItem } from '../../types/index';
import { FileIcon } from '../Icons/FileIcon';
import { PermissionIndicator } from '../Permissions/PermissionBadge';
import { 
  ChevronRight, 
  ChevronDown, 
  RefreshCw, 
  Folder,
  FolderOpen,
  Home,
  Settings,
  Search
} from 'lucide-react';
import clsx from 'clsx';

interface SidebarProps {
  folderStructure: FileItem | null;
  selectedFolder?: string;
  onFolderSelect: (folder: string) => void;
  onRefresh: () => void;
  className?: string;
}

interface FolderTreeNodeProps {
  folder: FileItem;
  level: number;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: (path: string) => void;
  onToggle: (path: string) => void;
}

function FolderTreeNode({
  folder,
  level,
  isSelected,
  isExpanded,
  onSelect,
  onToggle,
}: FolderTreeNodeProps) {
  const hasChildren = folder.children && folder.children.some(child => child.type === 'folder');
  
  return (
    <div>
      <div
        className={clsx(
          'group flex items-center px-2 py-1.5 text-sm cursor-pointer rounded-md transition-colors',
          isSelected 
            ? 'bg-primary-100 text-primary-900 font-medium' 
            : 'text-gray-700 hover:bg-gray-100',
          level > 0 && 'ml-4'
        )}
        onClick={() => onSelect(folder.path)}
        style={{ paddingLeft: `${8 + level * 16}px` }}
      >
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle(folder.path);
            }}
            className="mr-1 p-0.5 hover:bg-gray-200 rounded transition-colors"
          >
            {isExpanded ? (
              <ChevronDown size={14} />
            ) : (
              <ChevronRight size={14} />
            )}
          </button>
        )}
        
        {!hasChildren && <div className="w-5" />}
        
        <FileIcon
          type="folder"
          isOpen={isExpanded}
          size={16}
          className="mr-2 flex-shrink-0"
        />
        
        <span className="flex-1 truncate">{folder.name}</span>
        
        <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <PermissionIndicator 
            permission={folder.permission} 
            variant="dot" 
            className="w-2 h-2"
          />
        </div>
      </div>
      
      {hasChildren && isExpanded && folder.children && (
        <div>
          {folder.children
            .filter(child => child.type === 'folder')
            .map((child) => (
              <FolderTreeNode
                key={child.path}
                folder={child}
                level={level + 1}
                isSelected={child.path === folder.path}
                isExpanded={false} // TODO: Track expanded state for nested folders
                onSelect={onSelect}
                onToggle={onToggle}
              />
            ))}
        </div>
      )}
    </div>
  );
}

export function Sidebar({
  folderStructure,
  selectedFolder,
  onFolderSelect,
  onRefresh,
  className,
}: SidebarProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['']));
  const [loading, setLoading] = useState(false);

  const handleToggleFolder = useCallback((path: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  }, []);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    try {
      await onRefresh();
    } finally {
      setLoading(false);
    }
  }, [onRefresh]);

  const renderFolderTree = (folder: FileItem, level = 0) => {
    const children = folder.children?.filter(child => child.type === 'folder') || [];
    
    return (
      <div key={folder.path}>
        <FolderTreeNode
          folder={folder}
          level={level}
          isSelected={selectedFolder === folder.path}
          isExpanded={expandedFolders.has(folder.path)}
          onSelect={onFolderSelect}
          onToggle={handleToggleFolder}
        />
        
        {expandedFolders.has(folder.path) && children.map(child => 
          renderFolderTree(child, level + 1)
        )}
      </div>
    );
  };

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Explorer</h2>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
            title="Refresh folder structure"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Quick Navigation */}
      <div className="px-3 py-3 border-b border-gray-200">
        <div className="space-y-1">
          <button
            onClick={() => onFolderSelect('')}
            className={clsx(
              'w-full flex items-center px-2 py-1.5 text-sm rounded-md transition-colors',
              selectedFolder === '' 
                ? 'bg-primary-100 text-primary-900 font-medium' 
                : 'text-gray-700 hover:bg-gray-100'
            )}
          >
            <Home size={16} className="mr-2" />
            All Files
          </button>
          
          <button
            onClick={() => onFolderSelect('context')}
            className={clsx(
              'w-full flex items-center px-2 py-1.5 text-sm rounded-md transition-colors',
              selectedFolder === 'context' 
                ? 'bg-primary-100 text-primary-900 font-medium' 
                : 'text-gray-700 hover:bg-gray-100'
            )}
          >
            <Folder size={16} className="mr-2 text-warning-600" />
            Context Files
            <div className="ml-auto">
              <PermissionIndicator permission="read-only" variant="dot" className="w-2 h-2" />
            </div>
          </button>
          
          <button
            onClick={() => onFolderSelect('working')}
            className={clsx(
              'w-full flex items-center px-2 py-1.5 text-sm rounded-md transition-colors',
              selectedFolder === 'working' 
                ? 'bg-primary-100 text-primary-900 font-medium' 
                : 'text-gray-700 hover:bg-gray-100'
            )}
          >
            <Folder size={16} className="mr-2 text-success-600" />
            Working Files
            <div className="ml-auto">
              <PermissionIndicator permission="read-write" variant="dot" className="w-2 h-2" />
            </div>
          </button>
          
          <button
            onClick={() => onFolderSelect('output')}
            className={clsx(
              'w-full flex items-center px-2 py-1.5 text-sm rounded-md transition-colors',
              selectedFolder === 'output' 
                ? 'bg-primary-100 text-primary-900 font-medium' 
                : 'text-gray-700 hover:bg-gray-100'
            )}
          >
            <Folder size={16} className="mr-2 text-primary-600" />
            Output Files
            <div className="ml-auto">
              <PermissionIndicator permission="agent-controlled" variant="dot" className="w-2 h-2" />
            </div>
          </button>
        </div>
      </div>

      {/* Folder Tree */}
      <div className="flex-1 overflow-auto px-3 py-3">
        <div className="mb-2">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider px-2">
            Folders
          </h3>
        </div>
        
        {folderStructure ? (
          <div className="space-y-0.5">
            {folderStructure.children?.filter(child => child.type === 'folder').map(folder =>
              renderFolderTree(folder)
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
            <Folder size={32} className="mb-2 opacity-50" />
            <p className="text-sm">No folders found</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-gray-200">
        <div className="space-y-1">
          <button
            className="w-full flex items-center px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            title="Advanced Search"
          >
            <Search size={16} className="mr-2" />
            Advanced Search
          </button>
          
          <button
            className="w-full flex items-center px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            title="Settings"
          >
            <Settings size={16} className="mr-2" />
            Settings
          </button>
        </div>
        
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="text-xs text-gray-500">
            <div className="flex items-center justify-between mb-1">
              <span>Permission Legend:</span>
            </div>
            <div className="space-y-1">
              <div className="flex items-center">
                <PermissionIndicator permission="read-only" variant="dot" className="w-2 h-2 mr-2" />
                <span>Context (Read-only)</span>
              </div>
              <div className="flex items-center">
                <PermissionIndicator permission="read-write" variant="dot" className="w-2 h-2 mr-2" />
                <span>Working (Read/Write)</span>
              </div>
              <div className="flex items-center">
                <PermissionIndicator permission="agent-controlled" variant="dot" className="w-2 h-2 mr-2" />
                <span>Output (AI Managed)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}