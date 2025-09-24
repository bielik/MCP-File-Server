/**
 * Indexer Dashboard Component for MCP KnowledgeExplorer Phase 4A
 *
 * This component provides a comprehensive interface for monitoring and controlling
 * the indexer service, displaying real-time metrics, queue status, and file indexing progress.
 */

import React, { useState, useEffect } from 'react';

// Types for indexer data
interface IndexerStatus {
  is_running: boolean;
  is_paused: boolean;
  throttle_percentage: number;
  queue_stats: {
    pending_jobs: number;
    processing_jobs: number;
    completed_jobs: number;
    failed_jobs: number;
    dead_letter_jobs: number;
    queue_depth: number;
  };
  file_stats: {
    total_files: number;
    indexed_files: number;
    pending_files: number;
    indexing_progress: number;
  };
  performance_stats: {
    jobs_processed: number;
    jobs_failed: number;
    last_activity?: number;
    uptime_seconds?: number;
    eta_minutes?: number;
  };
}

interface FileMetadata {
  doc_id: string;
  path: string;
  size_bytes: number;
  mtime_epoch: number;
  is_indexed: boolean;
  mime_type?: string;
  discovered_at: number;
  last_indexed_at?: number;
}

interface JobInfo {
  id: number;
  job_type: string;
  status: string;
  created_at: number;
  retry_count: number;
  file_path?: string;
}

const IndexerDashboard: React.FC = () => {
  const [status, setStatus] = useState<IndexerStatus | null>(null);
  const [recentFiles, setRecentFiles] = useState<FileMetadata[]>([]);
  const [recentJobs, setRecentJobs] = useState<JobInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [controlLoading, setControlLoading] = useState<string | null>(null);

  // Resolve API base URL (configurable)
  const apiBase = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

  // Fetch indexer status
  const fetchStatus = async () => {
    try {
      const response = await fetch(`${apiBase}/api/indexer/status`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch indexer status:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    }
  };

  // Fetch recent files
  const fetchRecentFiles = async () => {
    try {
      const response = await fetch(`${apiBase}/api/indexer/files?limit=10`);
      if (response.ok) {
        const data = await response.json();
        setRecentFiles(data);
      }
    } catch (err) {
      console.error('Failed to fetch recent files:', err);
    }
  };

  // Fetch recent jobs
  const fetchRecentJobs = async () => {
    try {
      const response = await fetch(`${apiBase}/api/indexer/jobs?limit=10`);
      if (response.ok) {
        const data = await response.json();
        setRecentJobs(data);
      }
    } catch (err) {
      console.error('Failed to fetch recent jobs:', err);
    }
  };

  // Control actions
  const handleControlAction = async (action: string, value?: number) => {
    setControlLoading(action);
    try {
      const body: any = { action };
      if (value !== undefined) {
        body.value = value;
      }

      const response = await fetch(`${apiBase}/api/indexer/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`Control action failed: ${response.statusText}`);
      }

      // Refresh status after action
      await fetchStatus();
    } catch (err) {
      console.error(`Control action ${action} failed:`, err);
      setError(err instanceof Error ? err.message : 'Control action failed');
    } finally {
      setControlLoading(null);
    }
  };

  // Format utilities
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDateTime = (epoch: number): string => {
    return new Date(epoch * 1000).toLocaleString();
  };

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  // Effect for auto-refresh
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      await Promise.all([
        fetchStatus(),
        fetchRecentFiles(),
        fetchRecentJobs(),
      ]);
      setLoading(false);
    };

    fetchData();

    // Auto-refresh status every 5 seconds
    const statusInterval = setInterval(fetchStatus, 5000);
    // Periodically refresh lists every 15 seconds
    const listsInterval = setInterval(() => {
      fetchRecentFiles();
      fetchRecentJobs();
    }, 15000);
    return () => {
      clearInterval(statusInterval);
      clearInterval(listsInterval);
    };
  }, []);

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading indexer status...</p>
        </div>
      </div>
    );
  }

  if (error && !status) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Indexer Service Error</h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
          </div>
        </div>
        <div className="mt-4">
          <button
            onClick={() => {
              setError(null);
              fetchStatus();
            }}
            className="bg-red-100 text-red-800 px-3 py-1 rounded text-sm hover:bg-red-200 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="indexer-dashboard">
      {/* Status Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Indexer Service</h2>
            <div className="flex items-center mt-2 space-x-4">
              <div className="flex items-center">
                <div className={`w-3 h-3 rounded-full mr-2 ${
                  status?.is_running ? 'bg-green-400' : 'bg-red-400'
                }`}></div>
                <span className="text-sm text-gray-600">
                  {status?.is_running ? 'Running' : 'Stopped'}
                </span>
              </div>
              {status?.is_paused && (
                <div className="flex items-center">
                  <div className="w-3 h-3 rounded-full mr-2 bg-yellow-400"></div>
                  <span className="text-sm text-gray-600">Paused</span>
                </div>
              )}
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex space-x-2">
            <button
              onClick={() => handleControlAction(status?.is_paused ? 'resume' : 'pause')}
              disabled={controlLoading === 'pause' || controlLoading === 'resume'}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                status?.is_paused
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-yellow-600 text-white hover:bg-yellow-700'
              } disabled:opacity-50`}
              data-testid={status?.is_paused ? 'resume-indexer' : 'pause-indexer'}
            >
              {controlLoading === 'pause' || controlLoading === 'resume'
                ? 'Loading...'
                : status?.is_paused
                ? 'Resume'
                : 'Pause'
              }
            </button>

            <button
              onClick={() => {
                const newThrottle = status?.throttle_percentage === 0 ? 50 : 0;
                handleControlAction('throttle', newThrottle);
              }}
              disabled={controlLoading === 'throttle'}
              className="px-4 py-2 bg-gray-600 text-white rounded-md text-sm font-medium hover:bg-gray-700 transition-colors disabled:opacity-50"
              data-testid="throttle-indexer"
            >
              {controlLoading === 'throttle'
                ? 'Loading...'
                : status?.throttle_percentage === 0
                ? 'Throttle 50%'
                : 'Remove Throttle'
              }
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* File Progress */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">File Progress</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Total Files</span>
              <span className="text-sm font-medium">{status?.file_stats.total_files || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Indexed</span>
              <span className="text-sm font-medium text-green-600">{status?.file_stats.indexed_files || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Pending</span>
              <span className="text-sm font-medium text-yellow-600">{status?.file_stats.pending_files || 0}</span>
            </div>
            <div className="mt-4">
              <div className="flex justify-between mb-1">
                <span className="text-xs text-gray-600">Progress</span>
                <span className="text-xs text-gray-600">{Math.round(status?.file_stats.indexing_progress || 0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${status?.file_stats.indexing_progress || 0}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Queue Status */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Queue Status</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Pending</span>
              <span className="text-sm font-medium text-blue-600">{status?.queue_stats.pending_jobs || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Processing</span>
              <span className="text-sm font-medium text-yellow-600">{status?.queue_stats.processing_jobs || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Completed</span>
              <span className="text-sm font-medium text-green-600">{status?.queue_stats.completed_jobs || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Failed</span>
              <span className="text-sm font-medium text-red-600">{status?.queue_stats.failed_jobs || 0}</span>
            </div>
          </div>
        </div>

        {/* Performance */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Jobs Processed</span>
              <span className="text-sm font-medium">{status?.performance_stats.jobs_processed || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Jobs Failed</span>
              <span className="text-sm font-medium text-red-600">{status?.performance_stats.jobs_failed || 0}</span>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Jobs / Minute</span>
              <span className="text-sm font-medium">{(status?.performance_stats.jobs_per_minute || 0).toFixed ? status?.performance_stats.jobs_per_minute.toFixed(1) : (status?.performance_stats.jobs_per_minute || 0)}</span>
            </div>
            </div>
            {status?.performance_stats.uptime_seconds && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Uptime</span>
                <span className="text-sm font-medium">{formatDuration(status.performance_stats.uptime_seconds)}</span>
              </div>
            )}
            {status?.performance_stats.eta_minutes && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">ETA</span>
                <span className="text-sm font-medium">{formatDuration(status.performance_stats.eta_minutes * 60)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Configuration */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Throttle</span>
              <span className="text-sm font-medium">{status?.throttle_percentage || 0}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Queue Depth</span>
              <span className="text-sm font-medium">{status?.queue_stats.queue_depth || 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Files and Jobs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Files */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Recent Files</h3>
          </div>
          <div className="p-6">
            {recentFiles.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No files discovered yet</p>
            ) : (
              <div className="space-y-3">
                {recentFiles.map((file) => (
                  <div key={file.doc_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{file.path}</p>
                      <p className="text-xs text-gray-500">
                        {formatBytes(file.size_bytes)} • {formatDateTime(file.discovered_at)}
                      </p>
                    </div>
                    <div className="flex-shrink-0">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        file.is_indexed
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {file.is_indexed ? 'Indexed' : 'Pending'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Recent Jobs */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Recent Jobs</h3>
          </div>
          <div className="p-6">
            {recentJobs.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No jobs yet</p>
            ) : (
              <div className="space-y-3">
                {recentJobs.map((job) => (
                  <div key={job.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">
                        Job #{job.id} • {job.job_type}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {job.file_path || 'Unknown file'} • {formatDateTime(job.created_at)}
                      </p>
                    </div>
                    <div className="flex-shrink-0 flex items-center space-x-2">
                      {job.retry_count > 0 && (
                        <span className="text-xs text-orange-600">
                          Retry {job.retry_count}
                        </span>
                      )}
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        job.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : job.status === 'failed' || job.status === 'dead_letter'
                          ? 'bg-red-100 text-red-800'
                          : job.status === 'processing'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {job.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-700">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IndexerDashboard;
