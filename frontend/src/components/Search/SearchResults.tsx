import React from 'react';
import { FileText, Image, Clock, ExternalLink, Star, Zap, Globe } from 'lucide-react';
import clsx from 'clsx';

interface SearchResult {
  id: string;
  filePath: string;
  score: number;
  contentType: 'text' | 'image' | 'unknown';
  textContent?: string;
  highlight?: string;
  imageCaption?: string;
  documentTitle?: string;
  pageNumber?: number;
  chunkIndex?: number;
  createdAt?: string;
}

interface SearchResponse {
  success: boolean;
  query: string;
  searchType: string;
  results: SearchResult[];
  total: number;
  searchDetails: {
    service: string;
    type: string;
    threshold?: number;
    fuzzy?: boolean;
    modalities?: {
      text: boolean;
      images: boolean;
    };
  };
  timing: {
    duration: string;
    searchTime: number;
  };
  timestamp: string;
}

interface SearchResultsProps {
  searchResponse: SearchResponse | null;
  isLoading?: boolean;
  error?: string;
  onResultClick?: (result: SearchResult) => void;
  onClear?: () => void;
  className?: string;
}

export function SearchResults({
  searchResponse,
  isLoading = false,
  error,
  onResultClick,
  onClear,
  className,
}: SearchResultsProps) {
  if (isLoading) {
    return (
      <div className={clsx('bg-white rounded-lg border border-gray-200 p-6', className)}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-500 border-t-transparent" />
          <span className="ml-3 text-gray-600">Searching...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={clsx('bg-white rounded-lg border border-red-200 p-6', className)}>
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
              <ExternalLink size={16} className="text-red-600" />
            </div>
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-red-800">Search Error</h3>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
          {onClear && (
            <button
              onClick={onClear}
              className="ml-3 text-sm text-red-600 hover:text-red-800"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!searchResponse) {
    return (
      <div className={clsx('bg-white rounded-lg border border-gray-200 p-8 text-center', className)}>
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <FileText size={24} className="text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to Search</h3>
        <p className="text-sm text-gray-500">
          Enter your search query above to find files and content using AI-powered search.
        </p>
      </div>
    );
  }

  const { results, total, query, searchType, searchDetails, timing } = searchResponse;

  const getSearchTypeIcon = () => {
    switch (searchType) {
      case 'text':
        return <FileText size={16} className="text-blue-600" />;
      case 'semantic':
        return <Zap size={16} className="text-purple-600" />;
      case 'multimodal':
        return <Globe size={16} className="text-green-600" />;
      default:
        return <FileText size={16} className="text-gray-600" />;
    }
  };

  const getResultIcon = (result: SearchResult) => {
    if (result.contentType === 'image') {
      return <Image size={16} className="text-orange-500" />;
    }
    return <FileText size={16} className="text-blue-500" />;
  };

  const formatScore = (score: number) => {
    return (score * 100).toFixed(1);
  };

  const formatFilePath = (path: string) => {
    const parts = path.split(/[/\\]/);
    if (parts.length > 3) {
      return `.../${parts.slice(-2).join('/')}`;
    }
    return path;
  };

  const highlightText = (text: string, highlight?: string) => {
    if (!highlight) return text;
    
    // Simple highlighting - in a real app you'd want more sophisticated highlighting
    const highlighted = highlight.replace(/\*\*(.*?)\*\*/g, '<mark class="bg-yellow-200 px-0.5 rounded">$1</mark>');
    return <span dangerouslySetInnerHTML={{ __html: highlighted }} />;
  };

  return (
    <div className={clsx('bg-white rounded-lg border border-gray-200', className)}>
      {/* Search Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getSearchTypeIcon()}
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Search Results
              </h2>
              <p className="text-sm text-gray-500">
                Found {total} results for "{query}" • {timing.duration}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="text-xs text-gray-500">
              {searchDetails.service}
            </div>
            {onClear && (
              <button
                onClick={onClear}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Results List */}
      <div className="max-h-96 overflow-y-auto">
        {results.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText size={20} className="text-gray-400" />
            </div>
            <h3 className="text-sm font-medium text-gray-900 mb-2">No results found</h3>
            <p className="text-sm text-gray-500">
              Try adjusting your search query or switching to a different search mode.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {results.map((result, index) => (
              <div
                key={result.id}
                className={clsx(
                  'px-6 py-4 hover:bg-gray-50 transition-colors cursor-pointer',
                  onResultClick && 'hover:bg-blue-50'
                )}
                onClick={() => onResultClick?.(result)}
              >
                <div className="flex items-start space-x-3">
                  {/* Result Icon */}
                  <div className="flex-shrink-0 mt-0.5">
                    {getResultIcon(result)}
                  </div>

                  {/* Result Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {result.documentTitle || formatFilePath(result.filePath)}
                      </h3>
                      <div className="flex items-center space-x-1 text-xs text-gray-500">
                        <Star size={12} />
                        <span>{formatScore(result.score)}%</span>
                      </div>
                    </div>

                    <p className="text-xs text-gray-500 mb-2 truncate">
                      {result.filePath}
                      {result.pageNumber && ` • Page ${result.pageNumber}`}
                      {result.chunkIndex !== undefined && ` • Section ${result.chunkIndex + 1}`}
                    </p>

                    {/* Content Preview */}
                    {result.contentType === 'image' && result.imageCaption ? (
                      <p className="text-sm text-gray-700 italic">
                        📸 {result.imageCaption}
                      </p>
                    ) : result.highlight ? (
                      <div className="text-sm text-gray-700 line-clamp-2">
                        {highlightText(result.textContent || '', result.highlight)}
                      </div>
                    ) : result.textContent ? (
                      <p className="text-sm text-gray-700 line-clamp-2">
                        {result.textContent.substring(0, 200)}
                        {result.textContent.length > 200 ? '...' : ''}
                      </p>
                    ) : null}

                    {/* Metadata */}
                    <div className="flex items-center space-x-4 mt-2 text-xs text-gray-400">
                      <span className="capitalize">{result.contentType}</span>
                      {result.createdAt && (
                        <div className="flex items-center space-x-1">
                          <Clock size={10} />
                          <span>{new Date(result.createdAt).toLocaleDateString()}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  {onResultClick && (
                    <div className="flex-shrink-0">
                      <ExternalLink size={14} className="text-gray-400" />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer with Search Details */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 rounded-b-lg">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center space-x-4">
            <span>Search mode: <span className="capitalize font-medium">{searchType}</span></span>
            <span>Service: {searchDetails.service}</span>
            {searchDetails.threshold && (
              <span>Threshold: {(searchDetails.threshold * 100).toFixed(0)}%</span>
            )}
          </div>
          <div>
            Completed at {new Date(searchResponse.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
}