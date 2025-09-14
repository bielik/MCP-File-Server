import React, { useState, useEffect } from 'react';

interface PermissionRule {
  id: string;
  path: string;
  permission_type: 'read' | 'write';
  rule_type: 'allow' | 'deny';
  description?: string;
  created_at?: string;
}

interface PermissionConfig {
  rules: PermissionRule[];
  metadata?: {
    version: string;
    description: string;
  };
  precedence_rules?: {
    description: string;
    rules: string[];
  };
}

interface PermissionEditorProps {
  onSave?: (config: PermissionConfig) => void;
  onCancel?: () => void;
  initialConfig?: PermissionConfig;
  isLoading?: boolean;
}

const PermissionEditor: React.FC<PermissionEditorProps> = ({
  onSave,
  onCancel,
  initialConfig,
  isLoading = false
}) => {
  const [config, setConfig] = useState<PermissionConfig>(
    initialConfig || {
      rules: [],
      metadata: {
        version: '1.0.0',
        description: 'Permission rules for MCP KnowledgeExplorer'
      }
    }
  );
  const [editMode, setEditMode] = useState<'visual' | 'json'>('visual');
  const [jsonError, setJsonError] = useState<string>('');
  const [jsonText, setJsonText] = useState<string>('');

  useEffect(() => {
    if (initialConfig) {
      setConfig(initialConfig);
      setJsonText(JSON.stringify(initialConfig, null, 2));
    }
  }, [initialConfig]);

  const addRule = () => {
    const newRule: PermissionRule = {
      id: `rule-${Date.now()}`,
      path: '',
      permission_type: 'read',
      rule_type: 'allow',
      description: '',
      created_at: new Date().toISOString()
    };

    setConfig(prev => ({
      ...prev,
      rules: [...prev.rules, newRule]
    }));
  };

  const updateRule = (index: number, field: keyof PermissionRule, value: any) => {
    setConfig(prev => ({
      ...prev,
      rules: prev.rules.map((rule, i) =>
        i === index ? { ...rule, [field]: value } : rule
      )
    }));
  };

  const deleteRule = (index: number) => {
    setConfig(prev => ({
      ...prev,
      rules: prev.rules.filter((_, i) => i !== index)
    }));
  };

  const handleJsonChange = (text: string) => {
    setJsonText(text);
    setJsonError('');

    try {
      const parsed = JSON.parse(text);

      // Basic validation
      if (!parsed.rules || !Array.isArray(parsed.rules)) {
        setJsonError('Config must contain a "rules" array');
        return;
      }

      // Validate each rule
      for (const rule of parsed.rules) {
        if (!rule.id || !rule.path || !rule.permission_type || !rule.rule_type) {
          setJsonError('Each rule must have id, path, permission_type, and rule_type');
          return;
        }
        if (!['read', 'write'].includes(rule.permission_type)) {
          setJsonError('permission_type must be "read" or "write"');
          return;
        }
        if (!['allow', 'deny'].includes(rule.rule_type)) {
          setJsonError('rule_type must be "allow" or "deny"');
          return;
        }
      }

      setConfig(parsed);
    } catch (e) {
      setJsonError(`Invalid JSON: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  const handleSave = () => {
    if (editMode === 'json' && jsonError) {
      alert('Please fix JSON errors before saving');
      return;
    }
    onSave?.(config);
  };

  const switchToJson = () => {
    setJsonText(JSON.stringify(config, null, 2));
    setEditMode('json');
  };

  const getRuleTypeColor = (ruleType: string) => {
    return ruleType === 'allow' ? 'text-green-600' : 'text-red-600';
  };

  const getPermissionTypeIcon = (permissionType: string) => {
    return permissionType === 'read' ? '👁️' : '✏️';
  };

  return (
    <div className="permission-editor bg-white rounded-lg shadow-lg p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Permission Editor</h2>
        <div className="flex space-x-2">
          <button
            onClick={() => setEditMode('visual')}
            className={`px-4 py-2 rounded ${
              editMode === 'visual'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Visual Editor
          </button>
          <button
            onClick={switchToJson}
            className={`px-4 py-2 rounded ${
              editMode === 'json'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            JSON Editor
          </button>
        </div>
      </div>

      {editMode === 'visual' ? (
        <div className="visual-editor">
          {/* Rules List */}
          <div className="mb-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-700">Permission Rules</h3>
              <button
                onClick={addRule}
                className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded transition-colors"
                disabled={isLoading}
              >
                + Add Rule
              </button>
            </div>

            {config.rules.length === 0 ? (
              <div className="text-center py-8 text-gray-500 bg-gray-50 rounded">
                No permission rules defined. Click "Add Rule" to get started.
              </div>
            ) : (
              <div className="space-y-4">
                {config.rules.map((rule, index) => (
                  <div key={rule.id} className="border rounded-lg p-4 bg-gray-50">
                    {/* Rule ID Display */}
                    <div className="mb-3 pb-2 border-b border-gray-200">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-gray-600 bg-gray-200 px-2 py-1 rounded">
                          ID: {rule.id}
                        </span>
                        <span className="text-xs text-gray-500">
                          Rule #{index + 1}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      {/* Path */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Path
                        </label>
                        <input
                          type="text"
                          value={rule.path}
                          onChange={(e) => updateRule(index, 'path', e.target.value)}
                          placeholder="e.g., docs or projects/folder"
                          className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>

                      {/* Permission Type */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Permission
                        </label>
                        <select
                          value={rule.permission_type}
                          onChange={(e) => updateRule(index, 'permission_type', e.target.value as 'read' | 'write')}
                          className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="read">👁️ Read</option>
                          <option value="write">✏️ Write</option>
                        </select>
                      </div>

                      {/* Rule Type */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Rule Type
                        </label>
                        <select
                          value={rule.rule_type}
                          onChange={(e) => updateRule(index, 'rule_type', e.target.value as 'allow' | 'deny')}
                          className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="allow" className="text-green-600">✅ Allow</option>
                          <option value="deny" className="text-red-600">❌ Deny</option>
                        </select>
                      </div>

                      {/* Actions */}
                      <div className="flex items-end">
                        <button
                          onClick={() => deleteRule(index)}
                          className="bg-red-500 hover:bg-red-600 text-white px-3 py-2 rounded text-sm transition-colors"
                          disabled={isLoading}
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </div>

                    {/* Description */}
                    <div className="mt-3">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Description (Optional)
                      </label>
                      <input
                        type="text"
                        value={rule.description || ''}
                        onChange={(e) => updateRule(index, 'description', e.target.value)}
                        placeholder="Describe what this rule does..."
                        className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>

                    {/* Rule Summary */}
                    <div className="mt-2 p-2 bg-blue-50 rounded text-sm">
                      <span className="font-mono">
                        {getPermissionTypeIcon(rule.permission_type)}
                        <span className={getRuleTypeColor(rule.rule_type)}>
                          {rule.rule_type.toUpperCase()}
                        </span>
                        {' '}
                        <span className="font-bold">{rule.permission_type}</span>
                        {' '}
                        access to
                        {' '}
                        <span className="bg-gray-200 px-1 rounded font-mono">
                          {rule.path || '(empty path)'}
                        </span>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Precedence Rules Info */}
          <div className="bg-blue-50 rounded-lg p-4 mb-6">
            <h4 className="font-semibold text-blue-800 mb-2">Precedence Rules</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>1. ⬆️ <strong>Specificity:</strong> Child paths override parent paths</li>
              <li>2. ❌ <strong>Deny wins:</strong> If rules have equal specificity, deny overrides allow</li>
              <li>3. ✏️ <strong>Write implies read:</strong> Write permission automatically grants read</li>
              <li>4. 🚫 <strong>Default deny:</strong> If no rules match, access is denied</li>
            </ul>
          </div>
        </div>
      ) : (
        <div className="json-editor">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              JSON Configuration
            </label>
            <textarea
              value={jsonText}
              onChange={(e) => handleJsonChange(e.target.value)}
              className={`w-full h-96 border rounded px-3 py-2 text-sm font-mono focus:ring-2 focus:border-blue-500 ${
                jsonError ? 'border-red-500 focus:ring-red-500' : 'focus:ring-blue-500'
              }`}
              placeholder="Enter JSON configuration..."
            />
            {jsonError && (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                <strong>JSON Error:</strong> {jsonError}
              </div>
            )}
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
            <strong>💡 Tip:</strong> You can edit the JSON directly here. Changes will be reflected in the visual editor when you switch back.
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end space-x-3 pt-6 border-t">
        {onCancel && (
          <button
            onClick={onCancel}
            className="px-6 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition-colors"
            disabled={isLoading}
          >
            Cancel
          </button>
        )}
        <button
          onClick={handleSave}
          className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded transition-colors disabled:opacity-50"
          disabled={isLoading || (editMode === 'json' && !!jsonError)}
        >
          {isLoading ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </div>
  );
};

export default PermissionEditor;