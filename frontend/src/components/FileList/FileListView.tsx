import React, { useState, useCallback } from 'react';
import { FileItem, SortOptions } from '../../types/index';
import { FileIcon } from '../Icons/FileIcon';
import { PermissionBadge, PermissionIndicator } from '../Permissions/PermissionBadge';
import { formatFileSize, formatDate } from '../../utils/formatters';
import { FileContextMenu } from '../FileExplorer/FileContextMenu';
import { CreateFileModal } from '../FileExplorer/CreateFileModal';
import { SortControls } from '../Sort/SortControls';
import { EmptyState } from '../EmptyState/EmptyState';
import { apiService } from '../../services/api';
import { Plus, FolderPlus, ChevronRight, ChevronDown } from 'lucide-react';
import clsx from 'clsx';

interface FileListViewProps {
  files: FileItem[];
  selectedFiles: string[];
  onFileSelect: (fileIds: string[]) => void;
  onFileChange: () => void;
  sorting: SortOptions;
  onSortingChange: (sorting: SortOptions) => void;
  className?: string;
}

interface TableColumn {
  key: keyof FileItem | 'actions';
  label: string;
  sortable: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

const columns: TableColumn[] = [
  { key: 'name', label: 'Name', sortable: true, width: 'flex-1' },
  { key: 'type', label: 'Type', sortable: true, width: 'w-20', align: 'center' },
  { key: 'size', label: 'Size', sortable: true, width: 'w-24', align: 'right' },
  { key: 'modified', label: 'Modified', sortable: true, width: 'w-40' },
  { key: 'permission', label: 'Permission', sortable: true, width: 'w-32', align: 'center' },
  { key: 'actions', label: '', sortable: false, width: 'w-16', align: 'center' },
];

export function FileListView({
  files,
  selectedFiles,
  onFileSelect,
  onFileChange,
  sorting,
  onSortingChange,
  className,
}: FileListViewProps) {
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    fileId: string;
  } | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  const handleFileSelect = useCallback((fileId: string, isCtrlClick: boolean = false) => {
    if (isCtrlClick) {
      const newSelection = selectedFiles.includes(fileId)
        ? selectedFiles.filter(id => id !== fileId)
        : [...selectedFiles, fileId];
      onFileSelect(newSelection);
    } else {
      onFileSelect([fileId]);
    }
  }, [selectedFiles, onFileSelect]);

  const handleSelectAll = useCallback(() => {
    const allSelected = files.every(file => selectedFiles.includes(file.id));
    onFileSelect(allSelected ? [] : files.map(f => f.id));
  }, [files, selectedFiles, onFileSelect]);

  const handleSort = useCallback((field: SortOptions['field']) => {
    const newDirection = 
      sorting.field === field && sorting.direction === 'asc' ? 'desc' : 'asc';
    onSortingChange({ field, direction: newDirection });
  }, [sorting, onSortingChange]);

  const handleContextMenu = useCallback((fileId: string, x: number, y: number) => {
    setContextMenu({ fileId, x, y });
  }, []);

  const handleContextMenuClose = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleDoubleClick = (file: FileItem) => {
    if (file.type === 'folder') {
      console.log('Navigate to folder:', file.path);
    } else {
      console.log('Open file:', file.path);
    }
  };

  const toggleFolderExpansion = (folderId: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
  };

  const handleCreateFile = async (name: string, type: 'file' | 'folder', content: string = '') => {
    try {
      const filePath = `${name}${type === 'file' ? '.md' : ''}`;
      
      if (type === 'file') {
        await apiService.createFile(filePath, content, true);
      } else {
        await apiService.createFile(`${filePath}/.gitkeep`, '', true);
      }
      
      onFileChange();
      setShowCreateModal(false);
    } catch (error) {
      console.error('Failed to create file/folder:', error);
    }
  };

  const sortedFiles = [...files].sort((a, b) => {
    let aValue: any = a[sorting.field];
    let bValue: any = b[sorting.field];
    
    if (sorting.field === 'modified') {
      aValue = new Date(aValue).getTime();
      bValue = new Date(bValue).getTime();
    } else if (sorting.field === 'size') {
      aValue = Number(aValue);
      bValue = Number(bValue);
    } else {
      aValue = String(aValue).toLowerCase();
      bValue = String(bValue).toLowerCase();
    }
    
    const result = aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
    return sorting.direction === 'desc' ? -result : result;
  });

  const groupedFiles = sortedFiles.reduce((groups, file) => {
    const key = file.type;
    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(file);
    return groups;
  }, {} as Record<string, FileItem[]>);

  if (files.length === 0) {
    return (
      <EmptyState
        icon={FolderPlus}
        title="No files found"
        description="Get started by creating your first file or adjusting your search filters"
        actions={[
          {
            label: 'Create File',
            onClick: () => setShowCreateModal(true),
            primary: true,
          },
        ]}
      />
    );
  }

  return (
    <div className={clsx('h-full flex flex-col', className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Files ({files.length})
          </h2>
          <SortControls
            sorting={sorting}
            onSortingChange={onSortingChange}
            options={[
              { field: 'name', label: 'Name' },
              { field: 'type', label: 'Type' },
              { field: 'size', label: 'Size' },
              { field: 'modified', label: 'Modified' },
              { field: 'permission', label: 'Permission' },
            ]}
          />
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary btn-sm"
            title="Create new file or folder"
          >
            <Plus size={16} className="mr-1" />
            New
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="w-8 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={files.length > 0 && files.every(file => selectedFiles.includes(file.id))}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                </th>
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className={clsx(
                      'px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider',
                      column.width,
                      column.align === 'center' && 'text-center',
                      column.align === 'right' && 'text-right',
                      column.sortable && 'cursor-pointer hover:text-gray-700'
                    )}
                    onClick={() => column.sortable && column.key !== 'actions' && handleSort(column.key as SortOptions['field'])}
                  >
                    <div className={clsx(
                      'flex items-center',
                      column.align === 'center' && 'justify-center',
                      column.align === 'right' && 'justify-end'
                    )}>
                      {column.label}
                      {column.sortable && sorting.field === column.key && (
                        <span className="ml-1">
                          {sorting.direction === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {/* Folders first */}
              {groupedFiles.folder?.map((file) => (
                <tr
                  key={file.id}
                  className={clsx(
                    'hover:bg-gray-50 cursor-pointer transition-colors',
                    selectedFiles.includes(file.id) && 'bg-primary-50'
                  )}
                  onClick={(e) => handleFileSelect(file.id, e.ctrlKey || e.metaKey)}
                  onDoubleClick={() => handleDoubleClick(file)}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    handleContextMenu(file.id, e.clientX, e.clientY);
                  }}
                >
                  <td className="px-4 py-4">
                    <input
                      type="checkbox"
                      checked={selectedFiles.includes(file.id)}
                      onChange={() => {}}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleFolderExpansion(file.id);
                        }}
                        className="mr-2 p-0.5 hover:bg-gray-200 rounded"
                      >
                        {expandedFolders.has(file.id) ? (
                          <ChevronDown size={16} />
                        ) : (
                          <ChevronRight size={16} />
                        )}
                      </button>
                      <FileIcon
                        type={file.type}
                        size={20}
                        className="mr-3 flex-shrink-0"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </div>
                        {file.category && (
                          <div className="text-xs text-gray-500">
                            {file.category}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      Folder
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right text-sm text-gray-500">
                    —
                  </td>
                  <td className="px-4 py-4 text-sm text-gray-500">
                    {formatDate(file.modified)}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <PermissionIndicator permission={file.permission} variant="dot" />
                  </td>
                  <td className="px-4 py-4 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleContextMenu(file.id, e.clientX, e.clientY);
                      }}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      ⋮
                    </button>
                  </td>
                </tr>
              ))}
              
              {/* Files */}
              {groupedFiles.file?.map((file) => (
                <tr
                  key={file.id}
                  className={clsx(
                    'hover:bg-gray-50 cursor-pointer transition-colors',
                    selectedFiles.includes(file.id) && 'bg-primary-50'
                  )}
                  onClick={(e) => handleFileSelect(file.id, e.ctrlKey || e.metaKey)}
                  onDoubleClick={() => handleDoubleClick(file)}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    handleContextMenu(file.id, e.clientX, e.clientY);
                  }}
                >
                  <td className="px-4 py-4">
                    <input
                      type="checkbox"
                      checked={selectedFiles.includes(file.id)}
                      onChange={() => {}}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center">
                      <FileIcon
                        type={file.type}
                        extension={file.name.split('.').pop()}
                        size={20}
                        className="mr-3 flex-shrink-0"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </div>
                        {file.category && (
                          <div className="text-xs text-gray-500">
                            {file.category}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className="text-xs text-gray-500 uppercase">
                      {file.name.split('.').pop() || 'File'}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right text-sm text-gray-500">
                    {formatFileSize(file.size)}
                  </td>
                  <td className="px-4 py-4 text-sm text-gray-500">
                    {formatDate(file.modified)}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <PermissionIndicator permission={file.permission} variant="dot" />
                  </td>
                  <td className="px-4 py-4 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleContextMenu(file.id, e.clientX, e.clientY);
                      }}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      ⋮
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <FileContextMenu
          fileId={contextMenu.fileId}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={handleContextMenuClose}
          onFileChange={onFileChange}
        />
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateFileModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateFile}
        />
      )}
    </div>
  );
}