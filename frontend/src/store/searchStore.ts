import { create } from 'zustand';
import { apiService } from '../services/api.js';

// Types that match the existing SearchBar and SearchResults components
export interface SearchResult {
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

export interface SearchResponse {
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

export interface SearchHistory {
  id: string;
  query: string;
  searchType: 'text' | 'semantic' | 'multimodal';
  timestamp: string;
  resultsCount: number;
}

export interface SearchState {
  // Current search state
  query: string;
  searchType: 'text' | 'semantic' | 'multimodal';
  isLoading: boolean;
  error: string | null;
  
  // Results state
  currentResults: SearchResponse | null;
  
  // History state
  searchHistory: SearchHistory[];
  
  // Actions
  setQuery: (query: string) => void;
  setSearchType: (searchType: 'text' | 'semantic' | 'multimodal') => void;
  performSearch: (query?: string, searchType?: 'text' | 'semantic' | 'multimodal') => Promise<void>;
  clearResults: () => void;
  clearError: () => void;
  clearHistory: () => void;
  
  // Search service status
  searchServiceStatus: {
    keyword: { ready: boolean; documentsIndexed: number; service: string } | null;
    semantic: { ready: boolean; initialized: boolean; aiServiceReady: boolean; vectorDbServiceReady: boolean; totalQueries: number; service: string } | null;
    overall: { ready: boolean; timestamp: string } | null;
  };
  fetchSearchStatus: () => Promise<void>;
}

export const useSearchStore = create<SearchState>((set, get) => ({
  // Initial state
  query: '',
  searchType: 'text',
  isLoading: false,
  error: null,
  currentResults: null,
  searchHistory: [],
  searchServiceStatus: {
    keyword: null,
    semantic: null,
    overall: null,
  },

  // Actions
  setQuery: (query: string) => {
    set({ query, error: null });
  },

  setSearchType: (searchType: 'text' | 'semantic' | 'multimodal') => {
    set({ searchType, error: null });
  },

  performSearch: async (query?: string, searchType?: 'text' | 'semantic' | 'multimodal') => {
    const state = get();
    const searchQuery = query || state.query;
    const searchMethod = searchType || state.searchType;

    if (!searchQuery.trim()) {
      set({ error: 'Please enter a search query' });
      return;
    }

    set({ 
      isLoading: true, 
      error: null,
      query: searchQuery,
      searchType: searchMethod
    });

    try {
      const response = await apiService.searchFiles(searchQuery, searchMethod, {
        limit: 20,
        threshold: 0.7,
        fuzzy: searchMethod === 'text' ? true : undefined,
        highlight: searchMethod === 'text' ? true : undefined,
        includeText: searchMethod === 'multimodal' ? true : undefined,
        includeImages: searchMethod === 'multimodal' ? true : undefined,
      });

      if (response.success && response.data) {
        const searchResponse = response.data;
        
        // Add to search history
        const historyItem: SearchHistory = {
          id: `search-${Date.now()}`,
          query: searchQuery,
          searchType: searchMethod,
          timestamp: new Date().toISOString(),
          resultsCount: searchResponse.results.length,
        };

        set(state => ({
          currentResults: searchResponse,
          isLoading: false,
          error: null,
          searchHistory: [historyItem, ...state.searchHistory.slice(0, 9)], // Keep last 10 searches
        }));
      } else {
        set({
          isLoading: false,
          error: response.error || 'Search failed',
          currentResults: null,
        });
      }
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Search failed',
        currentResults: null,
      });
    }
  },

  clearResults: () => {
    set({
      currentResults: null,
      error: null,
    });
  },

  clearError: () => {
    set({ error: null });
  },

  clearHistory: () => {
    set({ searchHistory: [] });
  },

  fetchSearchStatus: async () => {
    try {
      const response = await apiService.getSearchStatus();
      
      if (response.success && response.data) {
        set({
          searchServiceStatus: {
            keyword: response.data.services.keyword,
            semantic: response.data.services.semantic,
            overall: response.data.overall,
          }
        });
      }
    } catch (error) {
      console.error('Failed to fetch search status:', error);
    }
  },
}));

// Helper hook for search history
export const useSearchHistory = () => {
  const searchHistory = useSearchStore(state => state.searchHistory);
  const clearHistory = useSearchStore(state => state.clearHistory);
  
  const getRecentQueries = (limit = 5) => {
    return searchHistory.slice(0, limit).map(item => item.query);
  };

  const getPopularSearchTypes = () => {
    const counts = searchHistory.reduce((acc, item) => {
      acc[item.searchType] = (acc[item.searchType] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    return Object.entries(counts).sort(([,a], [,b]) => b - a).map(([type]) => type);
  };

  return {
    searchHistory,
    clearHistory,
    getRecentQueries,
    getPopularSearchTypes,
  };
};

// Helper hook for search service status
export const useSearchServiceStatus = () => {
  const { searchServiceStatus, fetchSearchStatus } = useSearchStore(state => ({
    searchServiceStatus: state.searchServiceStatus,
    fetchSearchStatus: state.fetchSearchStatus,
  }));

  const isAnyServiceReady = () => {
    return searchServiceStatus.keyword?.ready || searchServiceStatus.semantic?.ready;
  };

  const getAllServicesReady = () => {
    return searchServiceStatus.keyword?.ready && searchServiceStatus.semantic?.ready;
  };

  const getServiceStatusText = () => {
    if (getAllServicesReady()) {
      return 'All search services ready';
    } else if (isAnyServiceReady()) {
      const readyServices = [];
      if (searchServiceStatus.keyword?.ready) readyServices.push('Text');
      if (searchServiceStatus.semantic?.ready) readyServices.push('Semantic');
      return `${readyServices.join(', ')} search ready`;
    } else {
      return 'Search services starting...';
    }
  };

  return {
    searchServiceStatus,
    fetchSearchStatus,
    isAnyServiceReady,
    getAllServicesReady,
    getServiceStatusText,
  };
};