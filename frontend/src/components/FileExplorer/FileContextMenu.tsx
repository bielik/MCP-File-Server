import React, { useEffect, useRef, useState } from 'react';
import { FileItem } from '../../types/index';
import { apiService } from '../../services/api';
import {
  Edit3,
  Copy,
  Trash2,
  Download,
  Share2,
  Lock,
  Unlock,
  FolderOpen,
  FileText,
  Info,
  Star,
  Archive,
  MoreHorizontal
} from 'lucide-react';
import clsx from 'clsx';

interface FileContextMenuProps {
  fileId: string;
  x: number;
  y: number;
  onClose: () => void;
  onFileChange: () => void;
}

interface MenuItem {
  id: string;
  label: string;
  icon: any;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  divider?: boolean;
}

export function FileContextMenu({
  fileId,
  x,
  y,
  onClose,
  onFileChange,
}: FileContextMenuProps) {
  const [file, setFile] = useState<FileItem | null>(null);
  const [loading, setLoading] = useState(true);
  const menuRef = useRef<HTMLDivElement>(null);

  // Load file details
  useEffect(() => {
    const loadFileDetails = async () => {
      try {
        setLoading(true);
        // TODO: Implement API call to get file details
        // For now, use mock data
        const mockFile: FileItem = {
          id: fileId,
          name: 'example.md',
          type: 'file',
          size: 1024,
          modified: new Date(),
          permission: 'read-write',
          path: '/working/example.md',
          category: 'document'
        };
        setFile(mockFile);
      } catch (error) {
        console.error('Failed to load file details:', error);
      } finally {
        setLoading(false);
      }
    };

    loadFileDetails();
  }, [fileId]);

  // Position menu and handle clicks outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    // Position the menu
    if (menuRef.current) {
      const menu = menuRef.current;
      const rect = menu.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      // Adjust horizontal position if menu would overflow
      if (x + rect.width > viewportWidth) {
        menu.style.left = `${viewportWidth - rect.width - 8}px`;
      } else {
        menu.style.left = `${x}px`;
      }

      // Adjust vertical position if menu would overflow
      if (y + rect.height > viewportHeight) {
        menu.style.top = `${viewportHeight - rect.height - 8}px`;
      } else {
        menu.style.top = `${y}px`;
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [x, y, onClose]);

  const handleAction = async (action: string) => {
    try {
      switch (action) {
        case 'open':
          console.log('Open file:', file?.path);
          break;
        case 'edit':
          console.log('Edit file:', file?.path);
          break;
        case 'copy':
          // TODO: Implement file copy
          break;
        case 'delete':
          if (file && window.confirm(`Are you sure you want to delete "${file.name}"?`)) {
            await apiService.deleteFile(file.path);
            onFileChange();
          }
          break;
        case 'download':
          if (file) {
            // TODO: Implement file download
            console.log('Download file:', file.path);
          }
          break;
        case 'share':
          console.log('Share file:', file?.path);
          break;
        case 'properties':
          console.log('Show properties for:', file?.path);
          break;
        case 'favorite':
          console.log('Toggle favorite for:', file?.path);
          break;
        case 'archive':
          console.log('Archive file:', file?.path);
          break;
      }
    } catch (error) {
      console.error(`Failed to ${action} file:`, error);
    } finally {
      onClose();
    }
  };

  if (loading || !file) {
    return (
      <div
        ref={menuRef}
        className="fixed bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-2"
        style={{ left: x, top: y }}
      >
        <div className="flex items-center space-x-2 px-3 py-2">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary-500 border-t-transparent" />
          <span className="text-sm text-gray-500">Loading...</span>
        </div>
      </div>
    );
  }

  const menuItems: MenuItem[] = [
    {
      id: 'open',
      label: file.type === 'folder' ? 'Open Folder' : 'Open File',
      icon: file.type === 'folder' ? FolderOpen : FileText,
      onClick: () => handleAction('open'),
    },
    {
      id: 'edit',
      label: 'Edit',
      icon: Edit3,
      onClick: () => handleAction('edit'),
      disabled: file.permission === 'read-only' || file.type === 'folder',
    },
    {
      id: 'divider1',
      label: '',
      icon: MoreHorizontal,
      onClick: () => {},
      divider: true,
    },
    {
      id: 'copy',
      label: 'Copy',
      icon: Copy,
      onClick: () => handleAction('copy'),
    },
    {
      id: 'download',
      label: 'Download',
      icon: Download,
      onClick: () => handleAction('download'),
    },
    {
      id: 'share',
      label: 'Share',
      icon: Share2,
      onClick: () => handleAction('share'),
    },
    {
      id: 'divider2',
      label: '',
      icon: MoreHorizontal,
      onClick: () => {},
      divider: true,
    },
    {
      id: 'favorite',
      label: 'Add to Favorites',
      icon: Star,
      onClick: () => handleAction('favorite'),
    },
    {
      id: 'archive',
      label: 'Archive',
      icon: Archive,
      onClick: () => handleAction('archive'),
    },
    {
      id: 'divider3',
      label: '',
      icon: MoreHorizontal,
      onClick: () => {},
      divider: true,
    },
    {
      id: 'properties',
      label: 'Properties',
      icon: Info,
      onClick: () => handleAction('properties'),
    },
    {
      id: 'delete',
      label: 'Delete',
      icon: Trash2,
      onClick: () => handleAction('delete'),
      disabled: file.permission === 'read-only',
      danger: true,
    },
  ];

  return (
    <div
      ref={menuRef}
      className="fixed bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1 min-w-48"
      style={{ left: x, top: y }}
    >
      {/* File Header */}
      <div className="px-3 py-2 border-b border-gray-100">
        <div className="flex items-center space-x-2">
          {file.type === 'folder' ? (
            <FolderOpen size={16} className="text-blue-500" />
          ) : (
            <FileText size={16} className="text-gray-600" />
          )}
          <span className="text-sm font-medium text-gray-900 truncate">
            {file.name}
          </span>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {file.type === 'file' && `${(file.size / 1024).toFixed(1)} KB • `}
          {new Date(file.modified).toLocaleDateString()}
        </div>
      </div>

      {/* Menu Items */}
      <div className="py-1">
        {menuItems.map((item) => {
          if (item.divider) {
            return <div key={item.id} className="border-t border-gray-100 my-1" />;
          }

          const IconComponent = item.icon;
          
          return (
            <button
              key={item.id}
              onClick={item.onClick}
              disabled={item.disabled}
              className={clsx(
                'w-full flex items-center space-x-3 px-3 py-2 text-sm transition-colors',
                item.disabled
                  ? 'text-gray-400 cursor-not-allowed'
                  : item.danger
                  ? 'text-red-700 hover:bg-red-50'
                  : 'text-gray-700 hover:bg-gray-50'
              )}
            >
              <IconComponent size={16} className="flex-shrink-0" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Permission indicator */}
      <div className="px-3 py-2 border-t border-gray-100 bg-gray-50">
        <div className="flex items-center space-x-2 text-xs">
          {file.permission === 'read-only' ? (
            <>
              <Lock size={12} className="text-warning-600" />
              <span className="text-warning-700">Read Only</span>
            </>
          ) : file.permission === 'agent-controlled' ? (
            <>
              <Lock size={12} className="text-primary-600" />
              <span className="text-primary-700">Agent Controlled</span>
            </>
          ) : (
            <>
              <Unlock size={12} className="text-success-600" />
              <span className="text-success-700">Read/Write</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}