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
  TrendingUp
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

        {systemStatus?.storage && (
          <div className="flex items-center space-x-1">
            <HardDrive size={14} className="text-gray-400" />
            <span className="text-gray-600">
              {formatBytes(systemStatus.storage.used)} / {formatBytes(systemStatus.storage.total)} used
            </span>
            <div className="w-16 h-1.5 bg-gray-200 rounded-full ml-1">
              <div 
                className={clsx(
                  'h-full rounded-full transition-all',
                  systemStatus.storage.used / systemStatus.storage.total > 0.9 
                    ? 'bg-danger-500'
                    : systemStatus.storage.used / systemStatus.storage.total > 0.7
                    ? 'bg-warning-500'
                    : 'bg-success-500'
                )}
                style={{
                  width: `${Math.min(100, (systemStatus.storage.used / systemStatus.storage.total) * 100)}%`
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Center Section - System Status */}
      <div className="flex items-center space-x-4">
        {systemStatus && (
          <>
            {systemStatus.cpu !== undefined && (
              <div className="flex items-center space-x-1">
                <Cpu size={14} className="text-gray-400" />
                <span className="text-gray-600">
                  CPU: {systemStatus.cpu.toFixed(1)}%
                </span>
              </div>
            )}

            {systemStatus.memory && (
              <div className="flex items-center space-x-1">
                <TrendingUp size={14} className="text-gray-400" />
                <span className="text-gray-600">
                  RAM: {formatBytes(systemStatus.memory.used)} / {formatBytes(systemStatus.memory.total)}
                </span>
              </div>
            )}

            {systemStatus.uptime !== undefined && (
              <div className="flex items-center space-x-1">
                <Clock size={14} className="text-gray-400" />
                <span className="text-gray-600">
                  Uptime: {formatUptime(systemStatus.uptime)}
                </span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Right Section - Connection & Health */}
      <div className="flex items-center space-x-4">
        {/* System Health */}
        {systemStatus?.status && (
          <div className="flex items-center space-x-1">
            {(() => {
              const StatusIcon = getStatusIcon(systemStatus.status);
              return (
                <StatusIcon 
                  size={14} 
                  className={getStatusColor(systemStatus.status)} 
                />
              );
            })()}
            <span className={clsx('capitalize', getStatusColor(systemStatus.status))}>
              {systemStatus.status}
            </span>
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