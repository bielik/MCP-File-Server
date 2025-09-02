import React, { useState, useRef, useEffect } from 'react';
import { Search, X, Filter, ChevronDown } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string, filters: SearchFilters) => void;
  onClear: () => void;
  placeholder?: string;
}

interface SearchFilters {
  fileTypes: string[];
  permissions: ('context' | 'working' | 'output' | 'none')[];
  includeHidden: boolean;
  caseSensitive: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  onClear,
  placeholder = "Search files and folders..."
}) => {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({
    fileTypes: [],
    permissions: [],
    includeHidden: false,
    caseSensitive: false,
  });
  const inputRef = useRef<HTMLInputElement>(null);
  const searchTimeout = useRef<NodeJS.Timeout>();

  // Debounced search
  useEffect(() => {
    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current);
    }

    if (query.length > 0) {
      searchTimeout.current = setTimeout(() => {
        onSearch(query, filters);
      }, 300);
    } else if (query.length === 0) {
      onClear();
    }

    return () => {
      if (searchTimeout.current) {
        clearTimeout(searchTimeout.current);
      }
    };
  }, [query, filters, onSearch, onClear]);

  const handleClear = () => {
    setQuery('');
    setFilters({
      fileTypes: [],
      permissions: [],
      includeHidden: false,
      caseSensitive: false,
    });
    onClear();
    inputRef.current?.focus();
  };

  const toggleFileType = (type: string) => {
    setFilters(prev => ({
      ...prev,
      fileTypes: prev.fileTypes.includes(type)
        ? prev.fileTypes.filter(t => t !== type)
        : [...prev.fileTypes, type]
    }));
  };

  const togglePermission = (permission: 'context' | 'working' | 'output' | 'none') => {
    setFilters(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permission)
        ? prev.permissions.filter(p => p !== permission)
        : [...prev.permissions, permission]
    }));
  };

  const fileTypes = ['js', 'ts', 'tsx', 'jsx', 'json', 'md', 'txt', 'py', 'html', 'css'];
  const hasActiveFilters = filters.fileTypes.length > 0 || 
                          filters.permissions.length > 0 || 
                          filters.includeHidden || 
                          filters.caseSensitive;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (query) {
        handleClear();
      } else {
        inputRef.current?.blur();
      }
    }
  };

  return (
    <div className="relative">
      {/* Main Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 flex items-center pl-3">
          <Search className="w-5 h-5 text-gray-400" />
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="block w-full pl-10 pr-12 py-2 border border-gray-300 rounded-lg bg-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <div className="absolute inset-y-0 right-0 flex items-center space-x-1 pr-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-1 rounded hover:bg-gray-100 ${hasActiveFilters ? 'text-blue-600 bg-blue-50' : 'text-gray-400'}`}
            title="Search filters"
          >
            <Filter className="w-4 h-4" />
          </button>
          {query && (
            <button
              onClick={handleClear}
              className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
              title="Clear search"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          <div className="p-4 space-y-4">
            {/* File Types Filter */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">File Types</h4>
              <div className="flex flex-wrap gap-2">
                {fileTypes.map(type => (
                  <button
                    key={type}
                    onClick={() => toggleFileType(type)}
                    className={`px-2 py-1 text-xs rounded border ${
                      filters.fileTypes.includes(type)
                        ? 'bg-blue-100 text-blue-700 border-blue-300'
                        : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                    }`}
                  >
                    .{type}
                  </button>
                ))}
              </div>
            </div>

            {/* Permissions Filter */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Permissions</h4>
              <div className="flex flex-wrap gap-2">
                {[
                  { key: 'context', label: 'Context', color: 'blue' },
                  { key: 'working', label: 'Working', color: 'green' },
                  { key: 'output', label: 'Output', color: 'purple' },
                  { key: 'none', label: 'No Permission', color: 'gray' }
                ].map(({ key, label, color }) => (
                  <button
                    key={key}
                    onClick={() => togglePermission(key as any)}
                    className={`px-2 py-1 text-xs rounded border ${
                      filters.permissions.includes(key as any)
                        ? `bg-${color}-100 text-${color}-700 border-${color}-300`
                        : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Additional Options */}
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={filters.includeHidden}
                  onChange={(e) => setFilters(prev => ({ ...prev, includeHidden: e.target.checked }))}
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                />
                <span className="ml-2 text-sm text-gray-600">Include hidden files</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={filters.caseSensitive}
                  onChange={(e) => setFilters(prev => ({ ...prev, caseSensitive: e.target.checked }))}
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                />
                <span className="ml-2 text-sm text-gray-600">Case sensitive</span>
              </label>
            </div>

            {/* Clear Filters */}
            {hasActiveFilters && (
              <div className="pt-2 border-t border-gray-200">
                <button
                  onClick={() => setFilters({
                    fileTypes: [],
                    permissions: [],
                    includeHidden: false,
                    caseSensitive: false,
                  })}
                  className="text-xs text-gray-500 hover:text-gray-700"
                >
                  Clear all filters
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};