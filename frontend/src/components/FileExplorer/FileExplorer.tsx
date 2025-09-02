import React, { useState, useCallback } from 'react';
import { useDrop } from 'react-dnd';
import { FileItem, SortOptions } from '../../types/index';
import { FileCard } from './FileCard';
import { CreateFileModal } from './CreateFileModal';
import { FileContextMenu } from './FileContextMenu';
import { SortControls } from '../Sort/SortControls';
import { EmptyState } from '../EmptyState/EmptyState';
import { apiService } from '../../services/api';
import { Plus, FolderPlus } from 'lucide-react';
import clsx from 'clsx';

interface FileExplorerProps {
  files: FileItem[];
  selectedFiles: string[];
  onFileSelect: (fileIds: string[]) => void;
  onFileChange: () => void;
  sorting: SortOptions;
  onSortingChange: (sorting: SortOptions) => void;
  className?: string;
}

export function FileExplorer({
  files,
  selectedFiles,
  onFileSelect,
  onFileChange,
  sorting,
  onSortingChange,
  className,
}: FileExplorerProps) {
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    fileId: string;
  } | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [draggedFiles, setDraggedFiles] = useState<string[]>([]);

  // Drop zone for file operations
  const [{ isOver, canDrop }, drop] = useDrop({
    accept: ['file', 'folder'],
    drop: (item: { type: string; files: string[] }, monitor) => {
      if (!monitor.didDrop()) {
        handleFileDrop(item.files, 'move');
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver({ shallow: true }),
      canDrop: monitor.canDrop(),
    }),
  });

  const handleFileSelect = useCallback((fileId: string, isCtrlClick: boolean = false) => {
    if (isCtrlClick) {
      // Multi-select with Ctrl
      const newSelection = selectedFiles.includes(fileId)
        ? selectedFiles.filter(id => id !== fileId)
        : [...selectedFiles, fileId];
      onFileSelect(newSelection);
    } else {
      // Single select
      onFileSelect([fileId]);
    }
  }, [selectedFiles, onFileSelect]);

  const handleFileContextMenu = useCallback((fileId: string, x: number, y: number) => {
    setContextMenu({ fileId, x, y });
  }, []);

  const handleContextMenuClose = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleFileDrop = async (fileIds: string[], operation: 'move' | 'copy') => {
    try {
      // Implement file move/copy logic
      console.log(`${operation} files:`, fileIds);
      // TODO: Call API to move/copy files
      onFileChange();
    } catch (error) {
      console.error(`Failed to ${operation} files:`, error);
    }
  };

  const handleCreateFile = async (name: string, type: 'file' | 'folder', content: string = '') => {
    try {
      const filePath = `${name}${type === 'file' ? '.md' : ''}`;
      
      if (type === 'file') {
        await apiService.createFile(filePath, content, true);
      } else {
        // Create folder - will be handled by the API
        await apiService.createFile(`${filePath}/.gitkeep`, '', true);
      }
      
      onFileChange();
      setShowCreateModal(false);
    } catch (error) {
      console.error('Failed to create file/folder:', error);
    }
  };

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Delete' && selectedFiles.length > 0) {
      // TODO: Implement delete functionality
      console.log('Delete selected files:', selectedFiles);
    } else if (event.key === 'a' && event.ctrlKey) {
      // Select all
      event.preventDefault();
      onFileSelect(files.map(f => f.id));
    }
  }, [selectedFiles, files, onFileSelect]);

  const sortedFiles = [...files].sort((a, b) => {
    let aValue: any = a[sorting.field];
    let bValue: any = b[sorting.field];
    
    // Handle different field types
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
    <div
      ref={drop}
      className={clsx(
        'h-full flex flex-col',
        isOver && canDrop && 'bg-primary-50 border-2 border-dashed border-primary-300 rounded-lg',
        className
      )}
      onKeyDown={handleKeyDown}
      tabIndex={0}
    >
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
              { field: 'permissions', label: 'Permission' },
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

      {/* File Grid */}
      <div className="flex-1 overflow-auto">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
          {/* Folders first */}
          {groupedFiles.folder?.map((file) => (
            <FileCard
              key={file.id}
              file={file}
              isSelected={selectedFiles.includes(file.id)}
              onSelect={(isCtrlClick) => handleFileSelect(file.id, isCtrlClick)}
              onContextMenu={(x, y) => handleFileContextMenu(file.id, x, y)}
              onDragStart={() => setDraggedFiles([file.id])}
              onDragEnd={() => setDraggedFiles([])}
              isDragging={draggedFiles.includes(file.id)}
            />
          ))}
          
          {/* Files */}
          {groupedFiles.file?.map((file) => (
            <FileCard
              key={file.id}
              file={file}
              isSelected={selectedFiles.includes(file.id)}
              onSelect={(isCtrlClick) => handleFileSelect(file.id, isCtrlClick)}
              onContextMenu={(x, y) => handleFileContextMenu(file.id, x, y)}
              onDragStart={() => setDraggedFiles([file.id])}
              onDragEnd={() => setDraggedFiles([])}
              isDragging={draggedFiles.includes(file.id)}
            />
          ))}
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