import React, { useState, useEffect } from 'react';

interface PermissionData {
  permissions: {
    context: string[];
    working: string[];
  };
  description: string;
  context_description: string;
  working_description: string;
}

interface PermissionIndicatorProps {
  path: string;
  className?: string;
}

type PermissionLevel = 'none' | 'context' | 'working';

export const PermissionIndicator: React.FC<PermissionIndicatorProps> = ({
  path,
  className = ""
}) => {
  const [permissions, setPermissions] = useState<PermissionData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPermissions = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/current-permissions');

        if (!response.ok) {
          throw new Error(`Failed to fetch permissions: ${response.statusText}`);
        }

        const data: PermissionData = await response.json();
        setPermissions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
        setPermissions(null);
      } finally {
        setLoading(false);
      }
    };

    fetchPermissions();
  }, []);

  const getPermissionLevel = (filePath: string): PermissionLevel => {
    if (!permissions) return 'none';

    // Extract the top-level directory from the path
    const topLevelDir = filePath.split('/')[0] || filePath;

    // Check if it's in working directories (read-write)
    if (permissions.permissions.working.includes(topLevelDir)) {
      return 'working';
    }

    // Check if it's in context directories (read-only)
    if (permissions.permissions.context.includes(topLevelDir)) {
      return 'context';
    }

    return 'none';
  };

  const permissionLevel = getPermissionLevel(path);

  const getPermissionConfig = (level: PermissionLevel) => {
    switch (level) {
      case 'working':
        return {
          icon: (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path>
            </svg>
          ),
          color: 'text-green-400',
          bgColor: 'bg-green-900/30',
          borderColor: 'border-green-600',
          label: 'Read-Write',
          tooltip: 'Full read and write access'
        };
      case 'context':
        return {
          icon: (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"></path>
              <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd"></path>
            </svg>
          ),
          color: 'text-blue-400',
          bgColor: 'bg-blue-900/30',
          borderColor: 'border-blue-600',
          label: 'Read-Only',
          tooltip: 'Read-only access for context'
        };
      case 'none':
      default:
        return {
          icon: (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM4 10a6 6 0 1012 0A6 6 0 004 10z" clipRule="evenodd"></path>
            </svg>
          ),
          color: 'text-gray-500',
          bgColor: 'bg-gray-900/30',
          borderColor: 'border-gray-600',
          label: 'No Access',
          tooltip: 'No permission configured'
        };
    }
  };

  if (loading) {
    return (
      <div className={`inline-flex items-center px-2 py-1 text-xs rounded ${className}`}>
        <div className="w-4 h-4 mr-1 bg-gray-600 animate-pulse rounded"></div>
        <span className="text-gray-500">...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`inline-flex items-center px-2 py-1 text-xs rounded bg-red-900/30 border border-red-600 text-red-400 ${className}`}>
        <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"></path>
        </svg>
        Error
      </div>
    );
  }

  const config = getPermissionConfig(permissionLevel);

  return (
    <div
      className={`inline-flex items-center px-2 py-1 text-xs rounded border ${config.bgColor} ${config.borderColor} ${config.color} ${className}`}
      title={config.tooltip}
    >
      <div className="mr-1">
        {config.icon}
      </div>
      <span className="font-medium">{config.label}</span>
    </div>
  );
};

interface PermissionLegendProps {
  className?: string;
}

export const PermissionLegend: React.FC<PermissionLegendProps> = ({ className = "" }) => {
  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Permission Levels</h3>
      <div className="space-y-2 text-xs">
        <div className="flex items-center">
          <div className="inline-flex items-center px-2 py-1 rounded border bg-green-900/30 border-green-600 text-green-400 mr-2">
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path>
            </svg>
            <span className="font-medium">Read-Write</span>
          </div>
          <span className="text-gray-400">Full read and write access</span>
        </div>

        <div className="flex items-center">
          <div className="inline-flex items-center px-2 py-1 rounded border bg-blue-900/30 border-blue-600 text-blue-400 mr-2">
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"></path>
              <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd"></path>
            </svg>
            <span className="font-medium">Read-Only</span>
          </div>
          <span className="text-gray-400">Read-only access for context</span>
        </div>

        <div className="flex items-center">
          <div className="inline-flex items-center px-2 py-1 rounded border bg-gray-900/30 border-gray-600 text-gray-500 mr-2">
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM4 10a6 6 0 1012 0A6 6 0 004 10z" clipRule="evenodd"></path>
            </svg>
            <span className="font-medium">No Access</span>
          </div>
          <span className="text-gray-400">No permission configured</span>
        </div>
      </div>
    </div>
  );
};

export default PermissionIndicator;