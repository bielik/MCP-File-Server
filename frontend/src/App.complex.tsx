import { useState, useEffect } from 'react';
import { FileExplorer } from './components/FileExplorer/FileExplorer';
import { FileListView } from './components/FileList/FileListView';
import { SearchBar } from './components/Search/SearchBar';
import { FilterPanel } from './components/Filters/FilterPanel';
import { StatusBar } from './components/StatusBar/StatusBar';
import { ToastContainer } from './components/Toast/ToastContainer';
import { Header } from './components/Layout/Header';
import { Sidebar } from './components/Layout/Sidebar';
import { useWebSocket, useFileSystemEvents, useSystemStatus } from './hooks/useWebSocket';
import { apiService } from './services/api';
import { UIState, FileItem, ToastNotification } from './types/index';
import { 
  Filter, 
  Grid, 
  List, 
  Settings,
  RefreshCw,
  Wifi,
  WifiOff 
} from 'lucide-react';

function App() {
  // UI State Management
  const [uiState, setUIState] = useState<UIState>({
    currentView: 'explorer',
    selectedFiles: [],
    searchQuery: '',
    filters: {
      permissions: [],
      fileTypes: [],
      categories: [],
    },
    sorting: {
      field: 'name',
      direction: 'asc',
    },
  });

  // Data State
  const [files, setFiles] = useState<FileItem[]>([]);
  const [folderStructure, setFolderStructure] = useState<FileItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // WebSocket Connection
  const { isConnected, reconnect } = useWebSocket();
  const { status: systemStatus, requestStatus } = useSystemStatus();

  // Handle file system events
  useFileSystemEvents((event) => {
    console.log('File system event:', event);
    
    // Show toast notification for file changes
    addToast({
      type: 'info',
      title: `File ${event.type}`,
      message: `${event.file}`,
      duration: 3000,
    });

    // Refresh file list after changes
    loadFiles();
  });

  // Toast management
  const addToast = (toast: Omit<ToastNotification, 'id'>) => {
    const newToast: ToastNotification = {
      ...toast,
      id: Math.random().toString(36).substr(2, 9),
    };
    
    setToasts(prev => [...prev, newToast]);

    // Auto-remove toast
    if (toast.duration && toast.duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== newToast.id));
      }, toast.duration);
    }
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  // Data Loading
  const loadFiles = async () => {
    try {
      setLoading(true);
      const response = await apiService.getFiles(
        {
          query: uiState.searchQuery || undefined,
          permissions: uiState.filters.permissions.length > 0 ? uiState.filters.permissions : undefined,
          fileTypes: uiState.filters.fileTypes.length > 0 ? uiState.filters.fileTypes : undefined,
          categories: uiState.filters.categories.length > 0 ? uiState.filters.categories : undefined,
        },
        uiState.sorting
      );

      if (response.success && response.data) {
        setFiles(response.data);
      } else {
        addToast({
          type: 'error',
          title: 'Failed to load files',
          message: response.error || 'Unknown error occurred',
          duration: 5000,
        });
      }
    } catch (error) {
      console.error('Error loading files:', error);
      addToast({
        type: 'error',
        title: 'Error loading files',
        message: error instanceof Error ? error.message : 'Unknown error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const loadFolderStructure = async (basePath?: string) => {
    try {
      const response = await apiService.getFolderStructure(basePath);
      if (response.success && response.data) {
        setFolderStructure(response.data);
      }
    } catch (error) {
      console.error('Error loading folder structure:', error);
    }
  };

  // UI Event Handlers
  const handleViewChange = (view: 'explorer' | 'list') => {
    setUIState(prev => ({ ...prev, currentView: view }));
  };

  const handleSearchChange = (query: string) => {
    setUIState(prev => ({ ...prev, searchQuery: query }));
  };

  const handleFilterChange = (filters: UIState['filters']) => {
    setUIState(prev => ({ ...prev, filters }));
  };

  const handleSortChange = (sorting: UIState['sorting']) => {
    setUIState(prev => ({ ...prev, sorting }));
  };

  const handleFileSelect = (fileIds: string[]) => {
    setUIState(prev => ({ ...prev, selectedFiles: fileIds }));
  };

  const handleRefresh = () => {
    loadFiles();
    loadFolderStructure();
    requestStatus();
  };

  // Initialize data on mount and when filters change
  useEffect(() => {
    loadFiles();
  }, [uiState.searchQuery, uiState.filters, uiState.sorting]);

  useEffect(() => {
    loadFolderStructure();
    requestStatus();
  }, []);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar 
        folderStructure={folderStructure}
        selectedFolder={uiState.selectedFolder}
        onFolderSelect={(folder) => setUIState(prev => ({ ...prev, selectedFolder: folder }))}
        onRefresh={loadFolderStructure}
        className="w-64 border-r border-gray-200 bg-white"
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <Header className="h-16 border-b border-gray-200 bg-white px-6">
          <div className="flex items-center justify-between w-full">
            {/* Left side - Search */}
            <div className="flex items-center space-x-4">
              <SearchBar
                value={uiState.searchQuery}
                onChange={handleSearchChange}
                placeholder="Search files and content..."
                className="w-80"
              />
            </div>

            {/* Right side - Controls */}
            <div className="flex items-center space-x-2">
              {/* View Toggle */}
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => handleViewChange('explorer')}
                  className={`p-2 rounded ${
                    uiState.currentView === 'explorer'
                      ? 'bg-white shadow-sm text-primary-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                  title="Explorer View"
                >
                  <Grid size={18} />
                </button>
                <button
                  onClick={() => handleViewChange('list')}
                  className={`p-2 rounded ${
                    uiState.currentView === 'list'
                      ? 'bg-white shadow-sm text-primary-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                  title="List View"
                >
                  <List size={18} />
                </button>
              </div>

              {/* Filter Toggle */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`p-2 rounded-lg ${
                  showFilters
                    ? 'bg-primary-100 text-primary-600'
                    : 'bg-gray-100 text-gray-500 hover:text-gray-700'
                }`}
                title="Toggle Filters"
              >
                <Filter size={18} />
              </button>

              {/* Refresh */}
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="p-2 rounded-lg bg-gray-100 text-gray-500 hover:text-gray-700 disabled:opacity-50"
                title="Refresh"
              >
                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
              </button>

              {/* Connection Status */}
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-100">
                {isConnected ? (
                  <>
                    <Wifi size={16} className="text-success-600" />
                    <span className="text-sm text-success-600">Connected</span>
                  </>
                ) : (
                  <>
                    <WifiOff size={16} className="text-danger-600" />
                    <span className="text-sm text-danger-600">Disconnected</span>
                    <button
                      onClick={reconnect}
                      className="text-xs text-primary-600 hover:text-primary-700 ml-2"
                    >
                      Reconnect
                    </button>
                  </>
                )}
              </div>

              {/* Settings */}
              <button
                className="p-2 rounded-lg bg-gray-100 text-gray-500 hover:text-gray-700"
                title="Settings"
              >
                <Settings size={18} />
              </button>
            </div>
          </div>
        </Header>

        {/* Filter Panel */}
        {showFilters && (
          <FilterPanel
            filters={uiState.filters}
            onFiltersChange={handleFilterChange}
            onClose={() => setShowFilters(false)}
            className="border-b border-gray-200 bg-gray-50 p-4"
          />
        )}

        {/* Main Content Area */}
        <div className="flex-1 p-6 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <RefreshCw className="w-8 h-8 animate-spin text-primary-600 mx-auto mb-4" />
                <p className="text-gray-500">Loading files...</p>
              </div>
            </div>
          ) : uiState.currentView === 'explorer' ? (
            <FileExplorer
              files={files}
              selectedFiles={uiState.selectedFiles}
              onFileSelect={handleFileSelect}
              onFileChange={loadFiles}
              sorting={uiState.sorting}
              onSortingChange={handleSortChange}
            />
          ) : (
            <FileListView
              files={files}
              selectedFiles={uiState.selectedFiles}
              onFileSelect={handleFileSelect}
              onFileChange={loadFiles}
              sorting={uiState.sorting}
              onSortingChange={handleSortChange}
            />
          )}
        </div>

        {/* Status Bar */}
        <StatusBar
          fileCount={files.length}
          selectedCount={uiState.selectedFiles.length}
          isConnected={isConnected}
          systemStatus={systemStatus}
          className="h-8 border-t border-gray-200 bg-gray-50 px-6"
        />
      </div>

      {/* Toast Notifications */}
      <ToastContainer
        toasts={toasts}
        onRemove={removeToast}
      />
    </div>
  );
}

export default App;