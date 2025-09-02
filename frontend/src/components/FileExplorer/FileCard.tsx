import React, { useState, useRef } from 'react';
import { useDrag } from 'react-dnd';
import { FileItem } from '../../types/index';
import { FileIcon } from '../Icons/FileIcon';
import { PermissionBadge } from '../Permissions/PermissionBadge';
import { formatFileSize, formatDate } from '../../utils/formatters';
import clsx from 'clsx';

interface FileCardProps {
  file: FileItem;
  isSelected: boolean;
  onSelect: (isCtrlClick?: boolean) => void;
  onContextMenu: (x: number, y: number) => void;
  onDragStart?: () => void;
  onDragEnd?: () => void;
  isDragging?: boolean;
  className?: string;
}

export function FileCard({
  file,
  isSelected,
  onSelect,
  onContextMenu,
  onDragStart,
  onDragEnd,
  isDragging,
  className,
}: FileCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  // Drag and drop
  const [{ isDragging: isDraggingState }, drag, preview] = useDrag({
    type: file.type === 'folder' ? 'folder' : 'file',
    item: () => {
      onDragStart?.();
      return { type: file.type, files: [file.id], file };
    },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
    end: () => {
      onDragEnd?.();
    },
  });

  // Combine refs
  const setRefs = (element: HTMLDivElement | null) => {
    cardRef.current = element;
    drag(element);
  };

  const handleClick = (event: React.MouseEvent) => {
    event.preventDefault();
    onSelect(event.ctrlKey || event.metaKey);
  };

  const handleContextMenu = (event: React.MouseEvent) => {
    event.preventDefault();
    onContextMenu(event.clientX, event.clientY);
  };

  const handleDoubleClick = () => {
    if (file.type === 'folder') {
      // Navigate into folder
      console.log('Navigate to folder:', file.path);
    } else {
      // Open file for editing
      console.log('Open file:', file.path);
    }
  };

  return (
    <div
      ref={setRefs}
      className={clsx(
        'file-card group relative p-4 rounded-xl border-2 transition-all duration-200 cursor-pointer select-none',
        isSelected
          ? 'bg-primary-50 border-primary-300 shadow-md'
          : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-md',
        isDraggingState || isDragging ? 'opacity-50 scale-95' : 'opacity-100 scale-100',
        `permission-${file.permission}`,
        className
      )}
      onClick={handleClick}
      onContextMenu={handleContextMenu}
      onDoubleClick={handleDoubleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* File Icon */}
      <div className="flex justify-center mb-3">
        <div className="relative">
          <FileIcon
            type={file.type}
            extension={file.type === 'file' ? file.name.split('.').pop() : undefined}
            size={48}
            className={clsx(
              'transition-transform duration-200',
              isHovered && 'scale-110'
            )}
          />
          
          {/* Permission indicator overlay */}
          <div
            className={clsx(
              'absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-white',
              file.permission === 'context' && 'bg-blue-500',
              file.permission === 'working' && 'bg-green-500', 
              file.permission === 'output' && 'bg-purple-500',
              !file.permission && 'bg-gray-300'
            )}
            title={file.permission ? `Permission: ${file.permission}` : 'No permission assigned'}
          />
        </div>
      </div>

      {/* File Name */}
      <div className="text-center mb-2">
        <h3
          className={clsx(
            'font-medium text-sm leading-tight line-clamp-2',
            isSelected ? 'text-primary-900' : 'text-gray-900'
          )}
          title={file.name}
        >
          {file.name}
        </h3>
      </div>

      {/* File Metadata */}
      <div className="text-xs text-gray-500 space-y-1">
        {file.type === 'file' && (
          <div className="flex justify-between items-center">
            <span>{formatFileSize(file.size)}</span>
            <span>{formatDate(file.modified)}</span>
          </div>
        )}
        
        {file.category && (
          <div className="text-center">
            <span className="inline-block px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
              {file.category}
            </span>
          </div>
        )}
      </div>

      {/* Permission Badge */}
      <div className="absolute top-2 right-2">
        <PermissionBadge permission={file.permission} size="sm" />
      </div>

      {/* Selection Overlay */}
      {isSelected && (
        <div className="absolute inset-0 bg-primary-500 bg-opacity-10 rounded-xl pointer-events-none" />
      )}

      {/* Drag Preview */}
      {isDraggingState && (
        <div className="absolute inset-0 bg-gray-900 bg-opacity-20 rounded-xl flex items-center justify-center">
          <div className="bg-white px-3 py-1 rounded shadow text-sm font-medium">
            Moving...
          </div>
        </div>
      )}
    </div>
  );
}

// CSS for line-clamp (add to global styles or use Tailwind plugin)
const lineClampStyles = `
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
`;