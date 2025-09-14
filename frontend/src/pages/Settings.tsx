import React, { useState, useEffect } from 'react';
import PermissionEditor from '../components/PermissionEditor';

interface PermissionConfig {
  rules: any[];
  metadata?: any;
}

interface ServerConfig {
  server_port?: number;
  frontend_port?: number;
  config_file_permissions_enabled: boolean;
  feature_flags: {
    ENABLE_CONFIG_FILE_PERMISSIONS: boolean;
    ENABLE_DATABASE_PERMISSIONS: boolean;
  };
}

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'permissions' | 'general'>('permissions');
  const [permissionConfig, setPermissionConfig] = useState<PermissionConfig | null>(null);
  const [serverConfig, setServerConfig] = useState<ServerConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const [etag, setEtag] = useState<string>('');

  useEffect(() => {
    loadConfigurations();
  }, []);

  const loadConfigurations = async () => {
    setIsLoading(true);
    setError('');

    try {
      // Load server config to check feature flags
      const serverResponse = await fetch('/api/config');
      if (!serverResponse.ok) {
        throw new Error(`Server config failed: ${serverResponse.statusText}`);
      }
      const serverData = await serverResponse.json();
      setServerConfig(serverData);

      // Load permission config
      const permissionResponse = await fetch('/api/config/permissions');
      if (!permissionResponse.ok) {
        throw new Error(`Permission config failed: ${permissionResponse.statusText}`);
      }

      const permissionData = await permissionResponse.json();
      setPermissionConfig(permissionData);

      // Extract ETag for optimistic locking
      const responseEtag = permissionResponse.headers.get('ETag');
      if (responseEtag) {
        setEtag(responseEtag.replace(/"/g, ''));
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      setIsLoading(false);
    }
  };

  const savePermissionConfig = async (newConfig: PermissionConfig) => {
    setIsSaving(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch('/api/config/permissions', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'If-Match': etag
        },
        body: JSON.stringify({ config: newConfig })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);

        if (response.status === 412) {
          throw new Error('Configuration was modified by another user. Please refresh and try again.');
        } else if (response.status === 501) {
          throw new Error('Config file permissions are not enabled. Contact administrator to enable Phase 2 features.');
        } else {
          throw new Error(errorData?.message || `Save failed: ${response.statusText}`);
        }
      }

      const responseData = await response.json();
      setPermissionConfig(responseData);
      setSuccess('Permission configuration saved successfully!');

      // Update ETag for next save
      const newEtag = response.headers.get('ETag');
      if (newEtag) {
        setEtag(newEtag.replace(/"/g, ''));
      }

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(''), 3000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setIsSaving(false);
    }
  };

  const isPhase2Enabled = serverConfig?.config_file_permissions_enabled || false;
  const isPhase3Enabled = serverConfig?.feature_flags?.ENABLE_DATABASE_PERMISSIONS || false;

  return (
    <div className="settings-page max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold text-gray-800 mb-8">Settings</h1>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-8">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('permissions')}
            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'permissions'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            🔐 Permissions
          </button>
          <button
            onClick={() => setActiveTab('general')}
            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'general'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            ⚙️ General
          </button>
        </nav>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex">
            <div className="text-red-400 mr-3">❌</div>
            <div className="text-red-700">{error}</div>
          </div>
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex">
            <div className="text-green-400 mr-3">✅</div>
            <div className="text-green-700">{success}</div>
          </div>
        </div>
      )}

      {/* Tab Content */}
      {activeTab === 'permissions' && (
        <div className="permissions-tab">
          {/* Feature Status */}
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="font-semibold text-blue-800 mb-2">🚀 Feature Status</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center">
                <span className={`inline-block w-3 h-3 rounded-full mr-2 ${
                  isPhase2Enabled ? 'bg-green-500' : 'bg-gray-400'
                }`}></span>
                <span className={isPhase2Enabled ? 'text-green-700' : 'text-gray-600'}>
                  Phase 2: Config-file Permissions {isPhase2Enabled ? '(Active)' : '(Disabled)'}
                </span>
              </div>
              <div className="flex items-center">
                <span className={`inline-block w-3 h-3 rounded-full mr-2 ${
                  isPhase3Enabled ? 'bg-green-500' : 'bg-gray-400'
                }`}></span>
                <span className={isPhase3Enabled ? 'text-green-700' : 'text-gray-600'}>
                  Phase 3: Database Permissions {isPhase3Enabled ? '(Active)' : '(Coming Soon)'}
                </span>
              </div>
            </div>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-gray-600">Loading configuration...</span>
            </div>
          ) : !isPhase2Enabled ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
              <div className="text-6xl mb-4">🔒</div>
              <h3 className="text-xl font-semibold text-gray-700 mb-2">Config-File Permissions Not Enabled</h3>
              <p className="text-gray-600 mb-4">
                Phase 2 features are currently disabled. Contact your administrator to enable config-file based permissions.
              </p>
              <div className="text-sm text-gray-500 bg-gray-100 rounded p-3 inline-block">
                <strong>To enable:</strong> Set <code>ENABLE_CONFIG_FILE_PERMISSIONS=true</code> in environment
              </div>
            </div>
          ) : permissionConfig ? (
            <PermissionEditor
              initialConfig={permissionConfig}
              onSave={savePermissionConfig}
              isLoading={isSaving}
            />
          ) : (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">⚠️</div>
              <p className="text-gray-600">Failed to load permission configuration</p>
              <button
                onClick={loadConfigurations}
                className="mt-4 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded transition-colors"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'general' && (
        <div className="general-tab">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Server Configuration</h3>

            {serverConfig ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Server Port</label>
                    <div className="mt-1 text-sm text-gray-600 bg-gray-50 p-2 rounded">
                      {serverConfig.server_port || 8000}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Frontend Port</label>
                    <div className="mt-1 text-sm text-gray-600 bg-gray-50 p-2 rounded">
                      {serverConfig.frontend_port || 5173}
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Feature Flags</label>
                  <div className="bg-gray-50 p-3 rounded">
                    {serverConfig.feature_flags ? (
                      <div className="space-y-2">
                        {Object.entries(serverConfig.feature_flags).map(([key, value]) => (
                          <div key={key} className="flex justify-between items-center">
                            <span className="text-sm font-mono text-gray-600">{key}</span>
                            <span className={`text-sm px-2 py-1 rounded ${
                              value
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-600'
                            }`}>
                              {value ? 'Enabled' : 'Disabled'}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500">No feature flags available</span>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500">Loading server configuration...</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;