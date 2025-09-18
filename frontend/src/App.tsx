import { useState, useEffect } from 'react';
import WorkspaceManager from './components/WorkspaceManager';
import TwoPanelPermissionEditor from './components/TwoPanelPermissionEditor';
import { useWebSocketContext } from './contexts/WebSocketContext';
import { useWorkspaceStore, useActiveWorkspaceId } from './store/workspaceStore';

function App() {
  const [config, setConfig] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'workspaces' | 'permissions' | 'status'>('workspaces');

  // Use WebSocket context
  const { isConnected, logs, clearLogs, error: wsError } = useWebSocketContext();

  // Get workspace state
  const { activeWorkspace, fetchWorkspaces } = useWorkspaceStore();
  const activeWorkspaceId = useActiveWorkspaceId();

  useEffect(() => {
    // This flag helps prevent issues with React 18's StrictMode double-invoking effects.
    let ignore = false;

    // Fetch initial config via HTTP
    fetch('http://localhost:8000/api/config')
      .then(res => res.json())
      .then(data => {
        if (!ignore) {
            setConfig(data);
        }
      })
      .catch(err => {
        console.error("Failed to fetch config:", err);
      });

    // Fetch workspaces on mount
    fetchWorkspaces();

    // Add native DOM event listeners for Browser MCP compatibility
    const handleNativeClick = (event: Event) => {
      const target = event.target as HTMLElement;
      const testId = target.getAttribute('data-testid');

      switch (testId) {
        case 'workspaces-tab':
          setActiveTab('workspaces');
          break;
        case 'permissions-tab':
          setActiveTab('permissions');
          break;
        case 'status-tab':
          setActiveTab('status');
          break;
      }
    };

    // Attach native listeners to tab buttons
    const workspacesTab = document.querySelector('[data-testid="workspaces-tab"]');
    const permissionsTab = document.querySelector('[data-testid="permissions-tab"]');
    const statusTab = document.querySelector('[data-testid="status-tab"]');

    workspacesTab?.addEventListener('click', handleNativeClick);
    permissionsTab?.addEventListener('click', handleNativeClick);
    statusTab?.addEventListener('click', handleNativeClick);

    // Cleanup on component unmount
    return () => {
      ignore = true;
      workspacesTab?.removeEventListener('click', handleNativeClick);
      permissionsTab?.removeEventListener('click', handleNativeClick);
      statusTab?.removeEventListener('click', handleNativeClick);
    };
  }, [fetchWorkspaces]);


  return (
    <div className="bg-gray-900 text-white min-h-screen p-8 font-mono">
      <div className="container mx-auto max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-cyan-400 mb-2">MCP KnowledgeExplorer</h1>
          <p className="text-lg text-gray-400 mb-4">Dynamic Workspace & Permission Management</p>


          {/* Tab Navigation */}
          <div className="flex space-x-1 bg-gray-800 p-1 rounded-lg w-fit">
            <button
              data-testid="workspaces-tab"
              onClick={() => setActiveTab('workspaces')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'workspaces'
                  ? 'bg-cyan-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              🏠 Workspaces
            </button>
            {activeWorkspace && (
              <button
                data-testid="permissions-tab"
                onClick={() => setActiveTab('permissions')}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  activeTab === 'permissions'
                    ? 'bg-cyan-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                🔐 Permissions
              </button>
            )}
            <button
              data-testid="status-tab"
              onClick={() => setActiveTab('status')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'status'
                  ? 'bg-cyan-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              📊 Server Status
            </button>
          </div>

          {/* Active Workspace Info */}
          {activeWorkspace && (
            <div className="mt-3 text-sm text-gray-400">
              Active workspace: <span className="text-cyan-400 font-medium">{activeWorkspace.name}</span>
            </div>
          )}
        </div>

        {activeTab === 'workspaces' && (
          <WorkspaceManager />
        )}

        {activeTab === 'permissions' && activeWorkspaceId && (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden" style={{ height: '70vh' }}>
            <TwoPanelPermissionEditor workspaceId={activeWorkspaceId} />
          </div>
        )}


        {activeTab === 'status' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Status & Config Panel */}
            <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
              <h2 className="text-xl font-semibold text-gray-200 border-b border-gray-700 pb-2 mb-4">Server Status</h2>
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className={`w-3 h-3 rounded-full ${
                    isConnected ? 'bg-green-400' : 'bg-red-400'
                  }`}></div>
                  <span className="text-sm">
                    <span className="font-bold text-gray-300">WebSocket:</span> {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>

                {wsError && (
                  <div className="text-red-400 text-sm">
                    <span className="font-bold">Error:</span> {wsError}
                  </div>
                )}

                {activeWorkspace && (
                  <div className="text-cyan-400 text-sm">
                    <span className="font-bold text-gray-300">Active Workspace:</span> {activeWorkspace.name}
                    <div className="text-xs text-gray-400 mt-1">
                      ID: {activeWorkspace.id} • Created: {new Date(activeWorkspace.created_at).toLocaleDateString()}
                    </div>
                  </div>
                )}

                <div className="pt-4">
                  <h3 className="text-lg font-semibold text-gray-300 mb-3">Server Configuration</h3>
                  <pre className="bg-gray-900 p-4 rounded-md text-sm overflow-auto max-h-64">
                    {config ? JSON.stringify(config, null, 2) : "Loading config..."}
                  </pre>
                </div>
              </div>
            </div>

            {/* Full Activity Log Panel */}
            <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
              <h2 className="text-xl font-semibold text-gray-200 border-b border-gray-700 pb-2 mb-4">
                Live Activity Log
                <span className="text-sm font-normal text-gray-400 ml-2">({logs.length} events)</span>
              </h2>
              <div className="bg-gray-900 p-4 rounded-md h-96 overflow-y-auto">
                {logs.length > 0 ? (
                  logs.map((log, index) => (
                    <p key={index} className="text-sm text-green-300 mb-1">
                      <span className="text-gray-500 mr-2">{`[${String(index + 1).padStart(3, '0')}]`}</span>
                      {log}
                    </p>
                  ))
                ) : (
                  <p className="text-gray-500">Awaiting activity...</p>
                )}
              </div>

              {logs.length > 0 && (
                <div className="mt-3 flex justify-between items-center text-xs text-gray-400">
                  <span>Scroll to see all events</span>
                  <button
                    onClick={clearLogs}
                    className="text-red-400 hover:text-red-300 transition-colors"
                  >
                    Clear Log
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default App;