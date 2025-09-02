import React from 'react';
import {
  FileText,
  Image,
  FileVideo,
  FileAudio,
  Archive,
  Code,
  Database,
  FileSpreadsheet,
  Presentation,
  File,
  Folder,
  FolderOpen,
} from 'lucide-react';
import clsx from 'clsx';

interface FileIconProps {
  type: 'file' | 'folder';
  extension?: string;
  size?: number;
  isOpen?: boolean;
  className?: string;
}

const getFileIconByExtension = (extension: string = '') => {
  const ext = extension.toLowerCase();
  
  // Text files
  if (['txt', 'md', 'markdown', 'rtf'].includes(ext)) {
    return { icon: FileText, color: 'text-blue-600' };
  }
  
  // Images
  if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'ico'].includes(ext)) {
    return { icon: Image, color: 'text-green-600' };
  }
  
  // Videos
  if (['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'].includes(ext)) {
    return { icon: FileVideo, color: 'text-red-600' };
  }
  
  // Audio
  if (['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'].includes(ext)) {
    return { icon: FileAudio, color: 'text-purple-600' };
  }
  
  // Archives
  if (['zip', 'rar', '7z', 'tar', 'gz', 'bz2'].includes(ext)) {
    return { icon: Archive, color: 'text-orange-600' };
  }
  
  // Code files
  if (['js', 'ts', 'jsx', 'tsx', 'html', 'css', 'scss', 'less', 'json', 'xml', 'yaml', 'yml'].includes(ext)) {
    return { icon: Code, color: 'text-indigo-600' };
  }
  
  // Programming languages
  if (['py', 'java', 'cpp', 'c', 'h', 'cs', 'php', 'rb', 'go', 'rs', 'swift', 'kt'].includes(ext)) {
    return { icon: Code, color: 'text-indigo-600' };
  }
  
  // Database
  if (['sql', 'db', 'sqlite', 'mdb'].includes(ext)) {
    return { icon: Database, color: 'text-yellow-600' };
  }
  
  // Spreadsheets
  if (['xlsx', 'xls', 'csv', 'ods'].includes(ext)) {
    return { icon: FileSpreadsheet, color: 'text-green-700' };
  }
  
  // Presentations
  if (['pptx', 'ppt', 'odp'].includes(ext)) {
    return { icon: Presentation, color: 'text-orange-700' };
  }
  
  // Documents
  if (['docx', 'doc', 'pdf', 'odt'].includes(ext)) {
    return { icon: FileText, color: 'text-blue-700' };
  }
  
  // Default file icon
  return { icon: File, color: 'text-gray-600' };
};

export function FileIcon({
  type,
  extension,
  size = 24,
  isOpen = false,
  className,
}: FileIconProps) {
  if (type === 'folder') {
    const FolderIcon = isOpen ? FolderOpen : Folder;
    return (
      <FolderIcon
        size={size}
        className={clsx('text-blue-500', className)}
      />
    );
  }

  const { icon: IconComponent, color } = getFileIconByExtension(extension);
  
  return (
    <IconComponent
      size={size}
      className={clsx(color, className)}
    />
  );
}

// Utility component for getting file type info
export const getFileTypeInfo = (filename: string) => {
  const extension = filename.split('.').pop()?.toLowerCase() || '';
  const { color } = getFileIconByExtension(extension);
  
  let category = 'Other';
  let description = 'File';
  
  if (['txt', 'md', 'markdown', 'rtf', 'docx', 'doc', 'pdf', 'odt'].includes(extension)) {
    category = 'Document';
    description = 'Text Document';
  } else if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'ico'].includes(extension)) {
    category = 'Image';
    description = 'Image File';
  } else if (['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'].includes(extension)) {
    category = 'Video';
    description = 'Video File';
  } else if (['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'].includes(extension)) {
    category = 'Audio';
    description = 'Audio File';
  } else if (['js', 'ts', 'jsx', 'tsx', 'html', 'css', 'scss', 'less', 'json', 'xml', 'yaml', 'yml', 'py', 'java', 'cpp', 'c', 'h', 'cs', 'php', 'rb', 'go', 'rs', 'swift', 'kt'].includes(extension)) {
    category = 'Code';
    description = 'Source Code';
  } else if (['xlsx', 'xls', 'csv', 'ods'].includes(extension)) {
    category = 'Spreadsheet';
    description = 'Spreadsheet';
  } else if (['pptx', 'ppt', 'odp'].includes(extension)) {
    category = 'Presentation';
    description = 'Presentation';
  } else if (['zip', 'rar', '7z', 'tar', 'gz', 'bz2'].includes(extension)) {
    category = 'Archive';
    description = 'Archive File';
  }
  
  return {
    category,
    description,
    extension: extension.toUpperCase(),
    color,
  };
};