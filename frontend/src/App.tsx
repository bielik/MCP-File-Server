import { useState, useEffect } from 'react';
import { Settings, RefreshCw, Server, FolderOpen, FileText, Database, Eye, Edit, Upload } from 'lucide-react';
import { FileExplorer } from './components/FileExplorer';

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

function App() {
  const [config, setConfig] = useState<ServerConfig | null>(null);
  const [stats, setStats] = useState<ServerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPaths, setSelectedPaths] = useState<string[]>([]);
  const [showConfig, setShowConfig] = useState(false);
  const [clearingEmbeddings, setClearingEmbeddings] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch configuration
      const configResponse = await fetch('/api/config');
      if (!configResponse.ok) throw new Error('Failed to fetch config');
      const configData = await configResponse.json();
      setConfig(configData);

      // Fetch stats
      const statsResponse = await fetch('/api/stats');
      if (!statsResponse.ok) throw new Error('Failed to fetch stats');
      const statsData = await statsResponse.json();
      setStats(statsData);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionAssign = async (paths: string[], permission: 'context' | 'working' | 'output') => {
    try {
      const response = await fetch('/api/config/permissions/assign', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ paths, permission }),
      });

      if (!response.ok) {
        throw new Error(`Failed to assign permissions: ${response.statusText}`);
      }

      // Refresh configuration after assignment
      await fetchData();
      
      // Clear selected paths
      setSelectedPaths([]);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign permissions');
    }
  };

  const handleSelectionChange = (selected: string[]) => {
    setSelectedPaths(selected);
  };

  const handleClearEmbeddings = async () => {
    if (!window.confirm('Are you sure you want to clear all embeddings and cached data? This action cannot be undone.')) {
      return;
    }

    try {
      setClearingEmbeddings(true);
      const response = await fetch('/api/config/clear-embeddings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to clear embeddings: ${response.statusText}`);
      }

      const result = await response.json();
      alert(result.message || 'Embeddings cleared successfully');
      
      // Refresh stats after clearing
      await fetchData();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear embeddings');
    } finally {
      setClearingEmbeddings(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

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
            onClick={fetchData}
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
                onClick={fetchData}
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
            {/* File Explorer Header */}
            <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">File Explorer</h2>
                  <p className="text-sm text-gray-500">
                    Browse and assign MCP permissions to files and folders
                  </p>
                </div>
                
                {/* Permission Legend */}
                <div className="flex items-center space-x-4 text-sm">
                  <div className="flex items-center">
                    <Eye className="w-4 h-4 text-blue-600 mr-1" />
                    <span className="text-blue-600">Context (Read-Only)</span>
                  </div>
                  <div className="flex items-center">
                    <Edit className="w-4 h-4 text-green-600 mr-1" />
                    <span className="text-green-600">Working (Read-Write)</span>
                  </div>
                  <div className="flex items-center">
                    <Upload className="w-4 h-4 text-purple-600 mr-1" />
                    <span className="text-purple-600">Output (Agent-Controlled)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* File Explorer Component */}
            <div className="flex-1 overflow-hidden">
              <FileExplorer
                onSelectionChange={handleSelectionChange}
                onPermissionAssign={handlePermissionAssign}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;