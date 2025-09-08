import React from 'react';
import { SystemStatus } from '../../types/index';
import { 
  Files, 
  CheckCircle2, 
  Wifi, 
  WifiOff, 
  HardDrive, 
  Cpu, 
  Clock,
  AlertCircle,
  TrendingUp,
  XCircle
} from 'lucide-react';
import clsx from 'clsx';

interface StatusBarProps {
  fileCount: number;
  selectedCount: number;
  isConnected: boolean;
  systemStatus?: SystemStatus;
  className?: string;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
}

export function StatusBar({
  fileCount,
  selectedCount,
  isConnected,
  systemStatus,
  className,
}: StatusBarProps) {
  const getStatusColor = (status?: 'healthy' | 'warning' | 'error') => {
    switch (status) {
      case 'healthy': return 'text-success-600';
      case 'warning': return 'text-warning-600';
      case 'error': return 'text-danger-600';
      default: return 'text-gray-500';
    }
  };

  const getStatusIcon = (status?: 'healthy' | 'warning' | 'error') => {
    switch (status) {
      case 'healthy': return CheckCircle2;
      case 'warning': return AlertCircle;
      case 'error': return AlertCircle;
      default: return Clock;
    }
  };

  return (
    <div className={clsx('flex items-center justify-between text-xs bg-gray-50 border-t', className)}>
      {/* Left Section - File Info */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-1">
          <Files size={14} className="text-gray-400" />
          <span className="text-gray-600">
            {fileCount} file{fileCount !== 1 ? 's' : ''}
            {selectedCount > 0 && (
              <span className="text-primary-600 font-medium">
                {' '}({selectedCount} selected)
              </span>
            )}
          </span>
        </div>

      </div>

      {/* Center Section - System Status */}
      <div className="flex items-center space-x-4">
        {systemStatus && (
          <>


          </>
        )}
      </div>

      {/* Right Section - Connection & Health */}
      <div className="flex items-center space-x-4">
        {/* System Health */}
        {systemStatus && (
          <div className="flex items-center space-x-1">
            {systemStatus.healthy ? (
              <>
                <CheckCircle2 size={14} className="text-success-600" />
                <span className="text-success-600">Healthy</span>
              </>
            ) : (
              <>
                <XCircle size={14} className="text-danger-600" />
                <span className="text-danger-600">Unhealthy</span>
              </>
            )}
          </div>
        )}

        {/* Connection Status */}
        <div className="flex items-center space-x-1">
          {isConnected ? (
            <>
              <Wifi size={14} className="text-success-600" />
              <span className="text-success-600">Connected</span>
            </>
          ) : (
            <>
              <WifiOff size={14} className="text-danger-600" />
              <span className="text-danger-600">Disconnected</span>
            </>
          )}
        </div>

        {/* Version Info */}
        <div className="text-gray-500 border-l border-gray-300 pl-3">
          <span>MCP File Server v1.0.0</span>
        </div>
      </div>
    </div>
  );
}