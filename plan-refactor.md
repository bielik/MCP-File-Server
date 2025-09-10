<./plan-frontend-refactor.md>
### **Step 2: Implement Frontend State Management**

**Goal:** Refactor the main `App.tsx` component to use **Zustand** for global state management. [cite_start]This will resolve the "Architectural Drift" identified in the initial review [cite: 19][cite_start], simplify the main component, improve performance by preventing redundant data fetching, and align the code with the project's documented architecture[cite: 169].

---
#### **Code Changes**

First, add the `zustand` dependency to the frontend workspace. Then, create the new state store and replace the content of `App.tsx`.

**1. Install Dependency**
Run the following command in your terminal at the project root:
```sh
pnpm --filter frontend add zustand
```

**2. Create/Update Files**
Create the new file `frontend/src/state/store.ts` and replace the entire content of `frontend/src/App.tsx` with the code below.

```plaintext
<./frontend/src/state/store.ts>
import { create } from 'zustand';

// Re-using existing interfaces from App.tsx
interface ServerConfig {
  permissionMatrix: {
    contextFolders: string[];
    workingFolders: string[];
    outputFolder: string;
  };
  serverConfig: {
    mcpPort: number;
    webUIPort: number;
    enableCaching: boolean;
    logLevel: string;
  };
}

interface ServerStats {
  contextFiles: number;
  workingFiles: number;
  outputFiles: number;
  totalSize: number;
  lastAccess: string;
}

interface AppState {
  config: ServerConfig | null;
  stats: ServerStats | null;
  loading: boolean;
  error: string | null;
  fetchInitialData: () => Promise<void>;
  clearAllEmbeddings: () => Promise<string>;
}

export const useAppStore = create<AppState>((set, get) => ({
  config: null,
  stats: null,
  loading: true,
  error: null,
  fetchInitialData: async () => {
    set({ loading: true, error: null });
    try {
      const configRes = await fetch('/api/config');
      if (!configRes.ok) throw new Error('Failed to fetch server config');
      const configData = await configRes.json();

      const statsRes = await fetch('/api/stats');
      if (!statsRes.ok) throw new Error('Failed to fetch server stats');
      const statsData = await statsRes.json();
      
      set({ config: configData, stats: statsData, loading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Unknown error', loading: false });
    }
  },
  clearAllEmbeddings: async () => {
    const response = await fetch('/api/config/clear-embeddings', { method: 'POST' });
    if (!response.ok) {
        const result = await response.json();
        throw new Error(result.error || 'Failed to clear embeddings');
    }
    const result = await response.json();
    // Re-fetch stats after clearing to update the UI
    get().fetchInitialData();
    return result.message || 'Embeddings cleared successfully';
  }
}));

<./frontend/src/App.tsx>
import { useState, useEffect } from 'react';
import { Settings, RefreshCw, Server, FolderOpen, Database, Eye, Edit, Upload } from 'lucide-react';
import { FileExplorer } from './components/FileExplorer';
import { useAppStore } from './state/store';

function App() {
  const { config, stats, loading, error, fetchInitialData, clearAllEmbeddings } = useAppStore();
  const [showConfig, setShowConfig] = useState(false);
  const [clearingEmbeddings, setClearingEmbeddings] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Fetch initial data when the component mounts
  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  const handlePermissionAssign = async (paths: string[], permission: 'context' | 'working' | 'output') => {
    try {
      setActionError(null);
      const response = await fetch('/api/config/permissions/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths, permission }),
      });
      if (!response.ok) {
        throw new Error(`Failed to assign permissions: ${response.statusText}`);
      }
      // Trigger a re-fetch of all data from the store
      await fetchInitialData();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to assign permissions');
    }
  };

  const handleClearEmbeddings = async () => {
    if (!window.confirm('Are you sure you want to clear all embeddings and cached data? This action cannot be undone.')) {
      return;
    }
    setClearingEmbeddings(true);
    setActionError(null);
    try {
        const message = await clearAllEmbeddings();
        alert(message);
    } catch (err) {
        setActionError(err instanceof Error ? err.message : 'Failed to clear embeddings');
    } finally {
        setClearingEmbeddings(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading MCP Server Configuration...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <p className="font-bold">Error:</p>
            <p>{error}</p>
          </div>
          <button
            onClick={fetchInitialData}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Server className="w-8 h-8 text-blue-500 mr-3" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">MCP Research File Server</h1>
                <p className="text-sm text-gray-500">Configuration & Monitoring Dashboard</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setShowConfig(false)}
                  className={`px-3 py-1 rounded text-sm ${!showConfig ? 'bg-blue-600 text-white' : 'text-gray-600 hover:text-gray-800'}`}
                >
                  <FolderOpen className="w-4 h-4 inline mr-1" />
                  File Explorer
                </button>
                <button
                  onClick={() => setShowConfig(true)}
                  className={`px-3 py-1 rounded text-sm ${showConfig ? 'bg-blue-600 text-white' : 'text-gray-600 hover:text-gray-800'}`}
                >
                  <Settings className="w-4 h-4 inline mr-1" />
                  Configuration
                </button>
              </div>
              <div className="flex items-center text-sm text-gray-500">
                <div className="w-3 h-3 bg-green-400 rounded-full mr-2"></div>
                Connected
              </div>
              <button
                onClick={fetchInitialData}
                className="p-2 text-gray-400 hover:text-gray-600"
                title="Refresh"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {actionError && (
             <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 m-4" role="alert">
                <p className="font-bold">Action Failed</p>
                <p>{actionError}</p>
            </div>
        )}
        {showConfig ? (
          <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            <div className="px-4 py-6 sm:px-0">
              
              {/* Server Configuration */}
              <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
                <div className="px-4 py-5 sm:p-6">
                  <div className="flex items-center mb-4">
                    <Settings className="w-6 h-6 text-gray-400 mr-3" />
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Server Configuration
                    </h3>
                  </div>
                  
                  {config && (
                    <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                      <div>
                        <dt className="text-sm font-medium text-gray-500">MCP Port</dt>
                        <dd className="mt-1 text-sm text-gray-900">{config.serverConfig.mcpPort}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Web UI Port</dt>
                        <dd className="mt-1 text-sm text-gray-900">{config.serverConfig.webUIPort}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Caching</dt>
                        <dd className="mt-1 text-sm text-gray-900">
                          {config.serverConfig.enableCaching ? 'Enabled' : 'Disabled'}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Log Level</dt>
                        <dd className="mt-1 text-sm text-gray-900">{config.serverConfig.logLevel}</dd>
                      </div>
                    </dl>
                  )}
                </div>
              </div>

              {/* File Permissions */}
              <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
                <div className="px-4 py-5 sm:p-6">
                  <div className="flex items-center mb-4">
                    <FolderOpen className="w-6 h-6 text-gray-400 mr-3" />
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      File Permissions
                    </h3>
                  </div>
                  
                  {config && (
                    <div className="space-y-4">
                      <div>
                        <dt className="text-sm font-medium text-gray-500 mb-2">Context Folders (Read-Only)</dt>
                        <dd className="text-sm text-gray-900">
                          {config.permissionMatrix.contextFolders.length > 0 ? (
                            <ul className="list-disc list-inside">
                              {config.permissionMatrix.contextFolders.map((folder, index) => (
                                <li key={index} className="flex items-center text-blue-600">
                                  <Eye className="w-4 h-4 mr-2" />
                                  {folder}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-yellow-600">No context folders configured</span>
                          )}
                        </dd>
                      </div>
                      
                      <div>
                        <dt className="text-sm font-medium text-gray-500 mb-2">Working Folders (Read-Write)</dt>
                        <dd className="text-sm text-gray-900">
                          {config.permissionMatrix.workingFolders.length > 0 ? (
                            <ul className="list-disc list-inside">
                              {config.permissionMatrix.workingFolders.map((folder, index) => (
                                <li key={index} className="flex items-center text-green-600">
                                  <Edit className="w-4 h-4 mr-2" />
                                  {folder}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-yellow-600">No working folders configured</span>
                          )}
                        </dd>
                      </div>
                      
                      <div>
                        <dt className="text-sm font-medium text-gray-500 mb-2">Output Folder (Agent-Controlled)</dt>
                        <dd className="text-sm text-gray-900">
                          <div className="flex items-center text-purple-600">
                            <Upload className="w-4 h-4 mr-2" />
                            {config.permissionMatrix.outputFolder}
                          </div>
                        </dd>
                      </div>
                    </div>
                  )}
                  
                  {/* Clear Embeddings Button */}
                  <div className="mt-6 pt-6 border-t border-gray-200">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-1">Embedding Management</h4>
                        <p className="text-sm text-gray-500">Clear all processed embeddings and cached vector data</p>
                      </div>
                      <button
                        onClick={handleClearEmbeddings}
                        disabled={clearingEmbeddings}
                        className={`px-4 py-2 text-sm font-medium rounded-md border ${
                          clearingEmbeddings
                            ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
                            : 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100 hover:border-red-300'
                        }`}
                      >
                        {clearingEmbeddings ? (
                          <>
                            <RefreshCw className="w-4 h-4 inline mr-2 animate-spin" />
                            Clearing...
                          </>
                        ) : (
                          <>
                            <Database className="w-4 h-4 inline mr-2" />
                            Clear All Embeddings
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Statistics */}
              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                  <div className="flex items-center mb-4">
                    <Database className="w-6 h-6 text-gray-400 mr-3" />
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      File System Statistics
                    </h3>
                  </div>
                  
                  {stats && (
                    <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2 lg:grid-cols-4">
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <dt className="text-sm font-medium text-blue-600">Context Files</dt>
                        <dd className="mt-1 text-2xl font-semibold text-blue-900">{stats.contextFiles}</dd>
                      </div>
                      <div className="bg-green-50 p-4 rounded-lg">
                        <dt className="text-sm font-medium text-green-600">Working Files</dt>
                        <dd className="mt-1 text-2xl font-semibold text-green-900">{stats.workingFiles}</dd>
                      </div>
                      <div className="bg-purple-50 p-4 rounded-lg">
                        <dt className="text-sm font-medium text-purple-600">Output Files</dt>
                        <dd className="mt-1 text-2xl font-semibold text-purple-900">{stats.outputFiles}</dd>
                      </div>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <dt className="text-sm font-medium text-gray-600">Total Size</dt>
                        <dd className="mt-1 text-2xl font-semibold text-gray-900">{formatBytes(stats.totalSize)}</dd>
                      </div>
                    </dl>
                  )}
                  
                  {stats && (
                    <div className="mt-6 pt-4 border-t border-gray-200">
                      <p className="text-sm text-gray-500">
                        Last updated: {formatDate(stats.lastAccess)}
                      </p>
                    </div>
                  )}
                </div>
              </div>

            </div>
          </div>
        ) : (
          <div className="flex flex-col h-full">
            <FileExplorer
                onPermissionAssign={handlePermissionAssign}
              />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
```
---
#### **How to Test**

After applying the changes, the application should look and behave exactly as before. This confirms the refactoring was successful.

1.  **Run the Application:**
    * Start the application as you normally would (`pnpm dev` or similar).

2.  **Verify Functionality (Manual Test):**
    * **Test 1: Initial Load & Data Display.**
        * The app should load without errors.
        * Navigate to the **"Configuration"** tab.
        * Confirm that all server configuration details, file permissions, and statistics are displayed correctly. This proves the Zustand store is fetching and providing data to the component.

    * **Test 2: Permission Assignment Action.**
        * Navigate to the **"File Explorer"** tab.
        * Select a file or folder.
        * Use the panel at the bottom to assign it a **"Context"** permission.
        * Verify that the UI updates immediately to show the new permission. This tests that actions that modify state and require a re-fetch are working correctly through the store.

    * **Test 3: Destructive Action & Refresh.**
        * Navigate back to the **"Configuration"** tab.
        * Click the **"Clear All Embeddings"** button and confirm the action.
        * Verify that the action completes and the **File System Statistics** panel updates to reflect the change (e.g., file counts might change if cache files are cleared). This confirms actions in the store can trigger data refreshes.

    * **Test 4: Error Handling.**
        * Stop the backend server.
        * Reload the frontend UI in your browser.
        * Verify that the application displays the error message correctly. This proves the error state in the Zustand store is working as intended.