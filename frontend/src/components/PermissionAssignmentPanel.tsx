import React, { useState } from 'react';
import { 
  Eye, 
  Edit, 
  Upload, 
  AlertTriangle, 
  Check, 
  X, 
  Info,
  Users,
  Shield,
  Lock
} from 'lucide-react';

interface PermissionAssignmentPanelProps {
  selectedPaths: string[];
  currentPermissions: Record<string, 'context' | 'working' | 'output' | null>;
  onAssign: (paths: string[], permission: 'context' | 'working' | 'output') => void;
  onRemove: (paths: string[]) => void;
  onClose: () => void;
}

export const PermissionAssignmentPanel: React.FC<PermissionAssignmentPanelProps> = ({
  selectedPaths,
  currentPermissions,
  onAssign,
  onRemove,
  onClose
}) => {
  const [selectedPermission, setSelectedPermission] = useState<'context' | 'working' | 'output'>('context');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [pendingAction, setPendingAction] = useState<{ type: 'assign' | 'remove'; permission?: string } | null>(null);

  // Analyze current permissions
  const permissionStats = selectedPaths.reduce((stats, path) => {
    const permission = currentPermissions[path];
    if (permission) {
      stats[permission] = (stats[permission] || 0) + 1;
    } else {
      stats.none = (stats.none || 0) + 1;
    }
    return stats;
  }, {} as Record<string, number>);

  const hasConflicts = Object.keys(permissionStats).length > 2 || 
    (Object.keys(permissionStats).length === 2 && !permissionStats.none);

  const getPermissionIcon = (permission: string) => {
    switch (permission) {
      case 'context': return <Eye className="w-4 h-4" />;
      case 'working': return <Edit className="w-4 h-4" />;
      case 'output': return <Upload className="w-4 h-4" />;
      default: return <Lock className="w-4 h-4" />;
    }
  };

  const getPermissionColor = (permission: string) => {
    switch (permission) {
      case 'context': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'working': return 'text-green-600 bg-green-50 border-green-200';
      case 'output': return 'text-purple-600 bg-purple-50 border-purple-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const handleAssign = () => {
    if (hasConflicts) {
      setPendingAction({ type: 'assign', permission: selectedPermission });
      setShowConfirmation(true);
    } else {
      onAssign(selectedPaths, selectedPermission);
    }
  };

  const handleRemove = () => {
    if (selectedPaths.some(path => currentPermissions[path])) {
      setPendingAction({ type: 'remove' });
      setShowConfirmation(true);
    }
  };

  const confirmAction = () => {
    if (pendingAction?.type === 'assign' && pendingAction.permission) {
      onAssign(selectedPaths, pendingAction.permission as 'context' | 'working' | 'output');
    } else if (pendingAction?.type === 'remove') {
      onRemove(selectedPaths);
    }
    setShowConfirmation(false);
    setPendingAction(null);
  };

  const cancelAction = () => {
    setShowConfirmation(false);
    setPendingAction(null);
  };

  if (selectedPaths.length === 0) {
    return null;
  }

  return (
    <>
      <div className="bg-white border-t border-gray-200 shadow-lg">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <Shield className="w-5 h-5 text-gray-400 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">
                Permission Assignment
              </h3>
              <div className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                {selectedPaths.length} selected
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Current Permission Status */}
          {Object.keys(permissionStats).length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Current Permissions:</h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(permissionStats).map(([permission, count]) => (
                  <div
                    key={permission}
                    className={`px-2 py-1 rounded-lg border text-sm ${getPermissionColor(permission)}`}
                  >
                    <div className="flex items-center">
                      {getPermissionIcon(permission)}
                      <span className="ml-1 capitalize">
                        {permission === 'none' ? 'No Permission' : permission}
                      </span>
                      <span className="ml-1 font-medium">({count})</span>
                    </div>
                  </div>
                ))}
              </div>

              {hasConflicts && (
                <div className="mt-2 flex items-center text-amber-600">
                  <AlertTriangle className="w-4 h-4 mr-1" />
                  <span className="text-sm">
                    Multiple permissions detected. Assignment will override existing permissions.
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Permission Selection */}
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-3">Select Permission Type:</h4>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => setSelectedPermission('context')}
                className={`p-3 rounded-lg border-2 transition-all ${
                  selectedPermission === 'context'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-blue-300'
                }`}
              >
                <div className="text-center">
                  <Eye className="w-6 h-6 text-blue-600 mx-auto mb-1" />
                  <div className="text-sm font-medium text-blue-900">Context</div>
                  <div className="text-xs text-blue-700">Read-Only</div>
                </div>
              </button>

              <button
                onClick={() => setSelectedPermission('working')}
                className={`p-3 rounded-lg border-2 transition-all ${
                  selectedPermission === 'working'
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-200 hover:border-green-300'
                }`}
              >
                <div className="text-center">
                  <Edit className="w-6 h-6 text-green-600 mx-auto mb-1" />
                  <div className="text-sm font-medium text-green-900">Working</div>
                  <div className="text-xs text-green-700">Read-Write</div>
                </div>
              </button>

              <button
                onClick={() => setSelectedPermission('output')}
                className={`p-3 rounded-lg border-2 transition-all ${
                  selectedPermission === 'output'
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-gray-200 hover:border-purple-300'
                }`}
              >
                <div className="text-center">
                  <Upload className="w-6 h-6 text-purple-600 mx-auto mb-1" />
                  <div className="text-sm font-medium text-purple-900">Output</div>
                  <div className="text-xs text-purple-700">Agent-Controlled</div>
                </div>
              </button>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-3">
            <button
              onClick={handleAssign}
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
            >
              <div className="flex items-center justify-center">
                <Check className="w-4 h-4 mr-2" />
                Assign Permission
              </div>
            </button>

            <button
              onClick={handleRemove}
              className="bg-red-100 text-red-700 py-2 px-4 rounded-lg hover:bg-red-200 transition-colors"
              disabled={!selectedPaths.some(path => currentPermissions[path])}
            >
              <div className="flex items-center justify-center">
                <X className="w-4 h-4 mr-2" />
                Remove
              </div>
            </button>
          </div>

          {/* Permission Info */}
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-start">
              <Info className="w-4 h-4 text-gray-500 mt-0.5 mr-2" />
              <div className="text-xs text-gray-600">
                <div className="font-medium mb-1">Permission Types:</div>
                <div><strong>Context:</strong> Files/folders that agents can read for understanding context</div>
                <div><strong>Working:</strong> Files/folders that agents can read and modify</div>
                <div><strong>Output:</strong> Folder where agents can create new files</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center mb-4">
              <AlertTriangle className="w-6 h-6 text-amber-500 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">Confirm Action</h3>
            </div>

            <div className="mb-6">
              {pendingAction?.type === 'assign' ? (
                <p className="text-gray-600">
                  Are you sure you want to assign <strong>{pendingAction.permission}</strong> permission 
                  to {selectedPaths.length} selected items? This will override any existing permissions.
                </p>
              ) : (
                <p className="text-gray-600">
                  Are you sure you want to remove permissions from {selectedPaths.length} selected items?
                </p>
              )}
            </div>

            <div className="flex space-x-3">
              <button
                onClick={confirmAction}
                className="flex-1 bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 transition-colors"
              >
                Confirm
              </button>
              <button
                onClick={cancelAction}
                className="flex-1 bg-gray-200 text-gray-800 py-2 px-4 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};