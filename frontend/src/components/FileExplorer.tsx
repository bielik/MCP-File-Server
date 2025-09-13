import React, { useState, useEffect } from 'react';
import { PermissionIndicator } from './PermissionIndicator';

interface FileItem {
  name: string;
  path: string;
  is_directory: boolean;
  size?: number;
  modified?: string;
}

interface BrowseResponse {
  files: FileItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface FileExplorerProps {
  onPathChange?: (path: string) => void;
  className?: string;
  pageSize?: number;
}

export const FileExplorer: React.FC<FileExplorerProps> = ({
  onPathChange,
  className = "",
  pageSize = 10
}) => {
  const [currentPath, setCurrentPath] = useState<string>("");
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);

  const fetchFiles = async (path: string, page: number = 1) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        path: path,
        page: page.toString(),
        page_size: pageSize.toString()
      });

      const response = await fetch(`http://localhost:8000/api/browse?${params}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch files: ${response.statusText}`);
      }

      const data: BrowseResponse = await response.json();
      setFiles(data.files);
      setTotalPages(data.total_pages);
      setCurrentPage(data.page);
      setTotalCount(data.total_count);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles(currentPath);
  }, [currentPath]);

  const navigateToPath = (newPath: string) => {
    setCurrentPath(newPath);
    setCurrentPage(1);
    onPathChange?.(newPath);
  };

  const handleFolderClick = (folder: FileItem) => {
    if (folder.is_directory) {
      navigateToPath(folder.path);
    }
  };

  const handleBreadcrumbClick = (targetPath: string) => {
    navigateToPath(targetPath);
  };

  const renderBreadcrumbs = () => {
    if (!currentPath) {
      return (
        <div className="flex items-center text-sm text-gray-400 mb-4">
          <span className="text-cyan-400 font-semibold">/ (root)</span>
        </div>
      );
    }

    const pathParts = currentPath.split('/').filter(part => part !== '');
    const breadcrumbs = [''];

    // Build cumulative paths for each breadcrumb
    let cumulativePath = '';
    pathParts.forEach(part => {
      cumulativePath += (cumulativePath ? '/' : '') + part;
      breadcrumbs.push(cumulativePath);
    });

    return (
      <div className="flex items-center text-sm text-gray-400 mb-4 flex-wrap">
        <button
          onClick={() => handleBreadcrumbClick('')}
          className="text-cyan-400 hover:text-cyan-300 font-semibold"
        >
          /
        </button>

        {pathParts.map((part, index) => (
          <React.Fragment key={index}>
            <span className="mx-1 text-gray-500">/</span>
            <button
              onClick={() => handleBreadcrumbClick(breadcrumbs[index + 1])}
              className="text-cyan-400 hover:text-cyan-300 font-semibold"
            >
              {part}
            </button>
          </React.Fragment>
        ))}
      </div>
    );
  };

  const formatSize = (bytes?: number): string => {
    if (!bytes) return '-';

    const sizes = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let size = bytes;

    while (size >= 1024 && i < sizes.length - 1) {
      size /= 1024;
      i++;
    }

    return `${size.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
  };

  const formatDate = (timestamp?: string): string => {
    if (!timestamp) return '-';

    try {
      const date = new Date(parseFloat(timestamp) * 1000);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } catch {
      return '-';
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchFiles(currentPath, newPage);
    }
  };

  const renderPagination = () => {
    if (totalPages <= 1) return null;

    const startItem = (currentPage - 1) * pageSize + 1;
    const endItem = Math.min(currentPage * pageSize, totalCount);
    const totalItems = totalCount;

    return (
      <div className="flex items-center justify-between mt-4 text-sm">
        <div className="text-gray-400">
          Showing {startItem}-{endItem} of {totalItems} items | Page {currentPage} of {totalPages}
        </div>
        <div className="flex space-x-1">
          <button
            onClick={() => handlePageChange(1)}
            disabled={currentPage === 1}
            className="px-2 py-1 bg-gray-700 text-white rounded disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-600 text-xs"
          >
            ««
          </button>
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-3 py-1 bg-gray-700 text-white rounded disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-600"
          >
            Previous
          </button>

          {/* Page numbers */}
          <div className="flex space-x-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={`px-2 py-1 rounded text-xs ${
                    pageNum === currentPage
                      ? 'bg-cyan-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-3 py-1 bg-gray-700 text-white rounded disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-600"
          >
            Next
          </button>
          <button
            onClick={() => handlePageChange(totalPages)}
            disabled={currentPage === totalPages}
            className="px-2 py-1 bg-gray-700 text-white rounded disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-600 text-xs"
          >
            »»
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className={`bg-gray-800 rounded-lg p-6 ${className}`}>
      <h2 className="text-xl font-semibold text-gray-200 border-b border-gray-700 pb-2 mb-4">
        File Explorer
      </h2>

      {renderBreadcrumbs()}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="text-gray-400">Loading...</div>
        </div>
      )}

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded mb-4">
          Error: {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="space-y-1">
            {files.length === 0 ? (
              <div className="text-gray-500 text-center py-8">
                No files found in this directory
              </div>
            ) : (
              files.map((file, index) => (
                <div
                  key={`${file.path}-${index}`}
                  className={`flex items-center p-2 rounded hover:bg-gray-700 transition-colors ${
                    file.is_directory ? 'cursor-pointer' : 'cursor-default'
                  }`}
                  onClick={() => handleFolderClick(file)}
                >
                  {/* Icon */}
                  <div className="w-6 h-6 flex items-center justify-center mr-3">
                    {file.is_directory ? (
                      <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path>
                      </svg>
                    ) : (
                      <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd"></path>
                      </svg>
                    )}
                  </div>

                  {/* Name */}
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm truncate ${
                      file.is_directory ? 'text-blue-300 font-medium' : 'text-gray-300'
                    }`}>
                      {file.name}
                    </div>
                  </div>

                  {/* Size */}
                  <div className="w-20 text-right text-xs text-gray-500">
                    {formatSize(file.size)}
                  </div>

                  {/* Permission indicator */}
                  <div className="w-24 flex justify-center ml-4">
                    <PermissionIndicator path={file.path} />
                  </div>

                  {/* Modified date */}
                  <div className="w-36 text-right text-xs text-gray-500 ml-4">
                    {formatDate(file.modified)}
                  </div>
                </div>
              ))
            )}
          </div>

          {renderPagination()}
        </>
      )}
    </div>
  );
};

export default FileExplorer;