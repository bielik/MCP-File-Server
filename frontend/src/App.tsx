import { useState, useEffect } from 'react';

function App() {
  const [config, setConfig] = useState<any>(null);
  const [status, setStatus] = useState('Connecting...');
  const [logs, setLogs] = useState<string[]>([]);

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

  return (
    <div className="bg-gray-900 text-white min-h-screen p-8 font-mono">
      <div className="container mx-auto">
        <h1 className="text-3xl font-bold text-cyan-400 mb-2">MCP KnowledgeExplorer</h1>
        <p className="text-lg text-gray-400 mb-6">Unified Hub Control Panel</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Status & Config Panel */}
          <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-semibold text-gray-200 border-b border-gray-700 pb-2 mb-4">Server Status</h2>
            <p className="text-md"><span className="font-bold text-green-400">Status:</span> {status}</p>
            <h3 className="text-lg font-semibold text-gray-300 mt-6 mb-2">Loaded Configuration:</h3>
            <pre className="bg-gray-900 p-4 rounded-md text-sm overflow-auto">
              {config ? JSON.stringify(config, null, 2) : "Loading config..."}
            </pre>
          </div>

          {/* Activity Log Panel */}
          <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-semibold text-gray-200 border-b border-gray-700 pb-2 mb-4">Live Activity Log</h2>
            <div className="bg-gray-900 p-4 rounded-md h-64 overflow-y-auto">
              {logs.length > 0 ? (
                logs.map((log, index) => (
                  <p key={index} className="text-sm text-green-300">
                    <span className="text-gray-500 mr-2">{`>`}</span>{log}
                  </p>
                ))
              ) : (
                <p className="text-gray-500">Awaiting activity...</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;