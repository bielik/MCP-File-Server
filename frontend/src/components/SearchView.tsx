import React, { useEffect } from 'react';
import { SearchBar } from './Search/SearchBar';
import { SearchResults } from './Search/SearchResults';
import { useSearchStore } from '../store/searchStore';

interface SearchViewProps {
  className?: string;
}

export function SearchView({ className }: SearchViewProps) {
  const {
    query,
    searchType,
    isLoading,
    error,
    currentResults,
    setQuery,
    setSearchType,
    performSearch,
    clearResults,
    clearError,
    fetchSearchStatus,
  } = useSearchStore();

  // Fetch search service status on component mount
  useEffect(() => {
    fetchSearchStatus();
  }, [fetchSearchStatus]);

  const handleSearch = async (searchQuery: string, type: 'text' | 'semantic' | 'multimodal') => {
    await performSearch(searchQuery, type);
  };

  const handleResultClick = (result: any) => {
    // Show detailed information about the clicked result
    console.log('Search result clicked:', result);
    
    // Copy file path to clipboard if available
    if (result.filePath && navigator.clipboard) {
      navigator.clipboard.writeText(result.filePath)
        .then(() => {
          // Show temporary success message - in a real app you'd use a toast/notification system
          const originalTitle = document.title;
          document.title = `📄 File path copied: ${result.filePath.split(/[/\\]/).pop()}`;
          setTimeout(() => {
            document.title = originalTitle;
          }, 2000);
        })
        .catch((err) => {
          console.warn('Failed to copy file path to clipboard:', err);
        });
    }
    
    // For now, we'll show an alert with file details
    // In a production app, this would open a file preview modal or navigate to the file
    const fileInfo = [
      `📁 File: ${result.filePath}`,
      `⭐ Score: ${(result.score * 100).toFixed(1)}%`,
      `📄 Type: ${result.contentType}`,
      result.documentTitle ? `📋 Title: ${result.documentTitle}` : '',
      result.pageNumber ? `📃 Page: ${result.pageNumber}` : '',
      result.chunkIndex !== undefined ? `📝 Section: ${result.chunkIndex + 1}` : '',
      result.createdAt ? `📅 Created: ${new Date(result.createdAt).toLocaleDateString()}` : '',
    ].filter(Boolean).join('\n');
    
    // Show file information (in a real app, this would be a modal or sidebar)
    alert(`File Information:\n\n${fileInfo}\n\n💾 File path has been copied to clipboard!`);
  };

  return (
    <div className={className}>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Search Bar */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <SearchBar
            value={query}
            onChange={setQuery}
            searchType={searchType}
            onSearchTypeChange={setSearchType}
            isLoading={isLoading}
            onSearch={handleSearch}
            onError={clearError}
            className="w-full"
          />
        </div>

        {/* Search Results */}
        <SearchResults
          searchResponse={currentResults}
          isLoading={isLoading}
          error={error}
          onResultClick={handleResultClick}
          onClear={clearResults}
          className="w-full"
        />
      </div>
    </div>
  );
}