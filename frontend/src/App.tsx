import { useState, useEffect } from 'react';
import FileExplorer from './components/FileExplorer';
import { PermissionIndicator, PermissionLegend } from './components/PermissionIndicator';

function App() {
  const [config, setConfig] = useState<any>(null);
  const [status, setStatus] = useState('Connecting...');
  const [logs, setLogs] = useState<string[]>([]);
  const [currentPath, setCurrentPath] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'explorer' | 'status'>('explorer');

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
        if (!ignore) {
            setStatus("Failed to connect to backend API.");
        }
      });

    // Establish WebSocket connection for UI logs
    const ws = new WebSocket('ws://localhost:8000/ws/ui');

    ws.onopen = () => {
      if (!ignore) {
        setStatus('Connected to backend WebSocket.');
        ws.send("Hello from UI!");
      }
    };

    ws.onmessage = (event) => {
        if (!ignore) {
            setLogs(prevLogs => [...prevLogs, event.data]);
        }
    };

    ws.onclose = () => {
        if (!ignore) {
            setStatus('WebSocket connection closed.');
        }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      if (!ignore) {
          setStatus('WebSocket connection error.');
      }
    };

    // Cleanup on component unmount
    return () => {
      ignore = true;
      ws.close();
    };
  }, []);

  const handlePathChange = (newPath: string) => {
    setCurrentPath(newPath);
  };

  return (
    <div className="bg-gray-900 text-white min-h-screen p-8 font-mono">
      <div className="container mx-auto max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-cyan-400 mb-2">MCP KnowledgeExplorer</h1>
          <p className="text-lg text-gray-400 mb-4">Dynamic Workspace & Permission Management</p>

          {/* Tab Navigation */}
          <div className="flex space-x-1 bg-gray-800 p-1 rounded-lg w-fit">
            <button
              onClick={() => setActiveTab('explorer')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'explorer'
                  ? 'bg-cyan-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              File Explorer
            </button>
            <button
              onClick={() => setActiveTab('status')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'status'
                  ? 'bg-cyan-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              Server Status
            </button>
          </div>
        </div>

        {activeTab === 'explorer' && (
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
            {/* File Explorer - Main Panel */}
            <div className="xl:col-span-3">
              <FileExplorer onPathChange={handlePathChange} pageSize={5} />

              {/* Current Path Info */}
              {currentPath && (
                <div className="mt-4 bg-gray-800 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">Current Selection</h3>
                  <div className="flex items-center space-x-3">
                    <div className="text-sm text-gray-400">
                      <span className="font-medium">Path:</span> /{currentPath}
                    </div>
                    <PermissionIndicator path={currentPath} />
                  </div>
                </div>
              )}
            </div>

            {/* Sidebar with Permission Legend and Activity */}
            <div className="xl:col-span-1 space-y-6">
              {/* Permission Legend */}
              <PermissionLegend />

              {/* Compact Activity Log */}
              <div className="bg-gray-800 p-4 rounded-lg">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">Recent Activity</h3>
                <div className="bg-gray-900 p-3 rounded-md h-48 overflow-y-auto">
                  {logs.length > 0 ? (
                    logs.slice(-10).map((log, index) => (
                      <p key={index} className="text-xs text-green-300 mb-1">
                        <span className="text-gray-500 mr-1">{`>`}</span>{log}
                      </p>
                    ))
                  ) : (
                    <p className="text-gray-500 text-xs">Awaiting activity...</p>
                  )}
                </div>
              </div>

              {/* Connection Status */}
              <div className="bg-gray-800 p-4 rounded-lg">
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Connection</h3>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    status.includes('Connected') ? 'bg-green-400' : 'bg-red-400'
                  }`}></div>
                  <span className="text-xs text-gray-400">{status}</span>
                </div>
              </div>
            </div>
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
                    status.includes('Connected') ? 'bg-green-400' : 'bg-red-400'
                  }`}></div>
                  <span className="text-sm">
                    <span className="font-bold text-gray-300">WebSocket:</span> {status}
                  </span>
                </div>

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
                    onClick={() => setLogs([])}
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