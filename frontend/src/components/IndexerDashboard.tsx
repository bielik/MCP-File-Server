/**
 * Indexer Dashboard Component for MCP KnowledgeExplorer Phase 4A
 *
 * This component provides a comprehensive interface for monitoring and controlling
 * the indexer service, displaying real-time metrics, queue status, and file indexing progress.
 */

import React, { useState, useEffect } from 'react';

// Types for indexer data
interface JobBacklogByType {
  pending: number;
  processing: number;
  failed: number;
  dead_letter: number;
  completed: number;
}

interface AlertMessage {
  title: string;
  detail?: string;
  severity: 'critical' | 'warning';
}

interface IndexerStatus {
  is_running: boolean;
  is_paused: boolean;
  throttle_percentage: number;
  queue_stats: {
    pending_jobs?: number;
    processing_jobs?: number;
    completed_jobs?: number;
    failed_jobs?: number;
    dead_letter_jobs?: number;
    queue_depth?: number;
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
    jobs_per_minute?: number;
  };
  service_error?: string | null;
  job_backlog?: {
    total?: number;
    total_pending?: number;
    total_processing?: number;
    total_failed?: number;
    total_dead_letter?: number;
    by_type?: Record<string, JobBacklogByType>;
  };
  integrity_stats?: {
    chunks_total?: number;
    files_without_chunks?: number;
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

  // Force Reindex state
  const [reindexModalOpen, setReindexModalOpen] = useState(false);
  const [reindexConfig, setReindexConfig] = useState({
    mode: 'soft' as 'soft' | 'hard',
  });
  const [reindexBatchId, setReindexBatchId] = useState<string | null>(null);
  const [reindexStatus, setReindexStatus] = useState<any>(null);
  const [reindexLoading, setReindexLoading] = useState(false);

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

  // Action center handlers
  const handleRequeueDeadLetter = async () => {
    setControlLoading('requeue');
    try {
      const response = await fetch(`${apiBase}/api/indexer/requeue-dead-letter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`Requeue failed: ${response.statusText}`);
      }

      // Refresh status after requeue
      await fetchStatus();
    } catch (err) {
      console.error('Requeue dead letter jobs failed:', err);
      setError(err instanceof Error ? err.message : 'Requeue operation failed');
    } finally {
      setControlLoading(null);
    }
  };

  const handleClearFailed = async () => {
    setControlLoading('clear');
    try {
      const response = await fetch(`${apiBase}/api/indexer/clear-failed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`Clear failed: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('Clear failed result:', result);

      await fetchStatus();
    } catch (err) {
      console.error('Clear failed jobs failed:', err);
      setError(err instanceof Error ? err.message : 'Clear operation failed');
    } finally {
      setControlLoading(null);
    }
  };

  const handleViewLogs = () => {
    // Open indexer logs in new tab
    window.open(`${apiBase}/api/indexer/logs`, '_blank');
  };

  const handleClearInvalidJobs = async () => {
    setControlLoading('clear-invalid');
    try {
      const response = await fetch(`${apiBase}/api/indexer/clear-invalid-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`Clear invalid jobs failed: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('Clear invalid jobs result:', result);

      await fetchStatus();
    } catch (err) {
      console.error('Clear invalid jobs failed:', err);
      setError(err instanceof Error ? err.message : 'Clear invalid jobs operation failed');
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

  const formatJobType = (jobType: string): string => {
    return jobType
      .toLowerCase()
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  };

  // Force Reindex functions
  const triggerReindex = async () => {
    setReindexLoading(true);
    try {
      const adminKey = localStorage.getItem('adminApiKey') || 'admin-secret-key-change-me';

      const response = await fetch(`${apiBase}/admin/reindex/force`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Key': adminKey,
        },
        body: JSON.stringify({
          mode: reindexConfig.mode,
          scope: {
            path_prefix: null,
            text_only: false,
          },
          dry_run: false,
        }),
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const error = await response.json();
          errorMessage = error.detail || errorMessage;
        } catch (e) {
          // If response isn't JSON, use the status text
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const result = await response.json();
      setReindexBatchId(result.batch_id);

      // Start polling for status
      fetchReindexStatus(result.batch_id);

      return result;
    } catch (err) {
      console.error('Failed to trigger reindex:', err);
      throw err;
    } finally {
      setReindexLoading(false);
    }
  };

  const fetchReindexStatus = async (batchId: string) => {
    try {
      const adminKey = localStorage.getItem('adminApiKey') || 'admin-secret-key-change-me';

      const response = await fetch(`${apiBase}/admin/reindex/batches/${batchId}`, {
        headers: {
          'X-Admin-Key': adminKey,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setReindexStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch reindex status:', err);
    }
  };

  const controlReindexBatch = async (action: 'pause' | 'resume' | 'cancel') => {
    if (!reindexBatchId) return;

    try {
      const adminKey = localStorage.getItem('adminApiKey') || 'admin-secret-key-change-me';

      const response = await fetch(`${apiBase}/admin/reindex/batches/${reindexBatchId}/${action}`, {
        method: 'POST',
        headers: {
          'X-Admin-Key': adminKey,
        },
      });

      if (response.ok) {
        // Refresh status
        fetchReindexStatus(reindexBatchId);
      }
    } catch (err) {
      console.error(`Failed to ${action} batch:`, err);
    }
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

  // Effect for polling reindex status
  useEffect(() => {
    if (!reindexBatchId || !reindexStatus) return;

    // Only poll if batch is still running
    if (reindexStatus.status === 'RUNNING' || reindexStatus.status === 'PLANNING') {
      const interval = setInterval(() => {
        fetchReindexStatus(reindexBatchId);
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [reindexBatchId, reindexStatus?.status]);

  // Effect for closing dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const dropdown = document.getElementById('reindex-dropdown');
      const button = document.querySelector('[data-testid="force-reindex-dropdown"]');

      if (dropdown && !dropdown.contains(event.target as Node) &&
          button && !button.contains(event.target as Node)) {
        dropdown.classList.add('hidden');
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
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

  const queueDepth = status?.queue_stats?.queue_depth ?? 0;
  const jobBacklog = status?.job_backlog;
  const backlogByTypeEntries = Object.entries(jobBacklog?.by_type ?? {}) as Array<[string, JobBacklogByType]>;
  const missingChunks = status?.integrity_stats?.files_without_chunks ?? 0;
  const totalChunks = status?.integrity_stats?.chunks_total ?? 0;

  const totalFiles = status?.file_stats.total_files ?? 0;
  const indexedFiles = status?.file_stats.indexed_files ?? 0;
  const pendingFiles = status?.file_stats.pending_files ?? Math.max(totalFiles - indexedFiles, 0);
  const indexedPercent = totalFiles > 0 ? Math.min(100, (indexedFiles / totalFiles) * 100) : 0;
  const pendingPercent = totalFiles > 0 ? Math.max(0, Math.min(100 - indexedPercent, (pendingFiles / totalFiles) * 100)) : 0;

  // Calculate pipeline problems - safe to access at top level
  const pipelineJobTypes = ['TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX'];
  const pipelineBacklog = backlogByTypeEntries.filter(([jobType]) => pipelineJobTypes.includes(jobType));
  const pipelineProblems = pipelineBacklog.reduce((total, [, counts]) =>
    total + (counts.failed || 0) + (counts.dead_letter || 0), 0);

  const alerts: AlertMessage[] = [];

  if (status) {
    if (status.service_error) {
      alerts.push({
        severity: 'critical',
        title: 'Indexer service unreachable',
        detail: status.service_error,
      });
    }

    if (!status.is_running) {
      alerts.push({
        severity: 'critical',
        title: 'Indexer service is not running',
      });
    }

    // Separate reindex jobs for clearer alerts (pipelineProblems already calculated at top level)
    const reindexBacklog = backlogByTypeEntries.filter(([jobType]) => jobType === 'reindex_file');

    if (pipelineProblems > 0) {
      const problemDetails = pipelineBacklog
        .filter(([, counts]) => (counts.failed || 0) + (counts.dead_letter || 0) > 0)
        .map(([jobType, counts]) => {
          const parts: string[] = [];
          if (counts.failed > 0) parts.push(`${counts.failed} failed`);
          if (counts.dead_letter > 0) parts.push(`${counts.dead_letter} dead-letter`);
          return `${formatJobType(jobType)}: ${parts.join(', ')}`;
        });

      alerts.push({
        severity: 'warning',
        title: `${pipelineProblems} text processing job${pipelineProblems === 1 ? '' : 's'} need attention`,
        detail: problemDetails.join(' | '),
      });
    }

    // Reindex job issues (likely invalid jobs for non-text files)
    const reindexProblems = reindexBacklog.reduce((total, [, counts]) =>
      total + (counts.failed || 0) + (counts.dead_letter || 0), 0);

    if (reindexProblems > 0) {
      const invalidJobs = status?.integrity_stats?.invalid_reindex_jobs ?? 0;
      if (invalidJobs > 0) {
        alerts.push({
          severity: 'warning',
          title: `${invalidJobs} invalid reindex job${invalidJobs === 1 ? '' : 's'} for non-text files`,
          detail: 'These jobs can be safely cleared as non-text files don\'t require text processing',
        });
      } else {
        alerts.push({
          severity: 'warning',
          title: `${reindexProblems} reindex job${reindexProblems === 1 ? '' : 's'} need attention`,
        });
      }
    }

    // Only warn about missing chunks for TEXT files
    const textFilesWithoutChunks = status?.integrity_stats?.text_files_without_chunks ?? 0;
    if (textFilesWithoutChunks > 0) {
      alerts.push({
        severity: 'warning',
        title: `${textFilesWithoutChunks} text ${textFilesWithoutChunks === 1 ? 'file' : 'files'} failed processing`,
        detail: 'These text files were indexed but failed to create searchable chunks',
      });
    }
  }

  const hasCriticalAlert = alerts.some((alert) => alert.severity === 'critical');
  const alertContainerClass = hasCriticalAlert ? 'bg-red-50 border border-red-200' : 'bg-yellow-50 border border-yellow-200';
  const alertIconClass = hasCriticalAlert ? 'text-red-500' : 'text-yellow-500';
  const alertTitleClass = hasCriticalAlert ? 'text-red-800' : 'text-yellow-800';
  const alertTextClass = hasCriticalAlert ? 'text-red-700' : 'text-yellow-700';
  const isIndexerHealthy = Boolean(status?.is_running && !status?.service_error);

  return (
    <div className="space-y-6" data-testid="indexer-dashboard">
      {/* Status Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Indexer Service</h2>
            <div className="flex items-center mt-2 space-x-4">
              <div className="flex items-center">
                <div
                  className={`w-3 h-3 rounded-full mr-2 ${
                    isIndexerHealthy ? 'bg-green-400' : 'bg-red-400'
                  }`}
                ></div>
                <span
                  className="text-sm text-gray-600"
                  title={status?.service_error || undefined}
                >
                  {isIndexerHealthy ? 'Running' : 'Stopped'}
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

            {/* Force Reindex Dropdown */}
            <div className="relative inline-block text-left">
              <div>
                <button
                  type="button"
                  onClick={() => {
                    const dropdown = document.getElementById('reindex-dropdown');
                    dropdown?.classList.toggle('hidden');
                  }}
                  className="inline-flex w-full justify-center gap-x-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
                  data-testid="force-reindex-dropdown"
                >
                  Force Reindex
                  <svg className="-mr-1 h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>

              <div
                id="reindex-dropdown"
                className="hidden absolute right-0 z-10 mt-2 w-64 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
              >
                <div className="py-1">
                  <button
                    onClick={() => {
                      setReindexConfig({ ...reindexConfig, mode: 'soft' });
                      setReindexModalOpen(true);
                      document.getElementById('reindex-dropdown')?.classList.add('hidden');
                    }}
                    className="group flex w-full items-start px-4 py-3 text-sm text-gray-700 hover:bg-gray-50"
                    data-testid="soft-reindex"
                  >
                    <div>
                      <div className="font-medium">Soft Reindex</div>
                      <div className="text-xs text-gray-500">Recommended - keeps existing data</div>
                    </div>
                  </button>
                  <button
                    onClick={() => {
                      setReindexConfig({ ...reindexConfig, mode: 'hard' });
                      setReindexModalOpen(true);
                      document.getElementById('reindex-dropdown')?.classList.add('hidden');
                    }}
                    className="group flex w-full items-start px-4 py-3 text-sm text-gray-700 hover:bg-red-50"
                    data-testid="hard-reset"
                  >
                    <div>
                      <div className="font-medium text-red-600">Hard Reset ⚠️</div>
                      <div className="text-xs text-red-500">Purges all data - use carefully</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>

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

      {alerts.length > 0 && (
        <div className={`${alertContainerClass} rounded-lg p-4`}>
          <div className="flex items-start">
            <svg className={`h-5 w-5 ${alertIconClass}`} viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <div className="ml-3">
              <h3 className={`text-sm font-medium ${alertTitleClass}`}>Indexer Attention Required</h3>
              <ul className="mt-2 space-y-1">
                {alerts.map((alert, index) => (
                  <li key={index} className={`text-sm ${alertTextClass}`}>
                    <span className="font-medium">{alert.title}</span>
                    {alert.detail ? <span className="ml-1">- {alert.detail}</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* File Overview */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📁 File Discovery</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{totalFiles}</div>
            <div className="text-sm text-gray-600">Total Files</div>
            <div className="text-xs text-green-600 mt-1">✅ Discovered</div>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <div className="text-2xl font-bold text-orange-600">{status?.file_stats?.text_files || 0}</div>
            <div className="text-sm text-gray-600">Text Files</div>
            <div className="text-xs text-gray-500 mt-1">Processable</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-600">{status?.file_stats?.non_text_files || 0}</div>
            <div className="text-sm text-gray-600">Non-Text Files</div>
            <div className="text-xs text-gray-500 mt-1">Images, Binaries</div>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{status?.file_stats?.text_files_with_chunks || 0}</div>
            <div className="text-sm text-gray-600">Fully Processed</div>
            <div className="text-xs text-gray-500 mt-1">
              {status?.file_stats?.text_files ?
                `${((status.file_stats.text_files_with_chunks || 0) / status.file_stats.text_files * 100).toFixed(1)}% of text files`
                : '0% of text files'}
            </div>
          </div>
        </div>
      </div>

      {/* Text Processing Pipeline */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">🔄 Text Processing Pipeline</h3>
        <div className="mb-4 text-sm text-gray-600">
          Processing {status?.file_stats?.text_files || 0} text files through 3-stage pipeline
        </div>

        {/* Pipeline Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stage</th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Completed</th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Processing</th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Failed</th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Pending</th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Dead Letter</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {backlogByTypeEntries
                .filter(([jobType]) => ['TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX'].includes(jobType))
                .sort(([jobTypeA], [jobTypeB]) => {
                  // Sort in pipeline order: TEXT_EXTRACT -> CHUNK -> FTS_INDEX
                  const order = { 'TEXT_EXTRACT': 1, 'CHUNK': 2, 'FTS_INDEX': 3 };
                  return order[jobTypeA] - order[jobTypeB];
                })
                .map(([jobType, stats]) => {
                const completed = stats.completed || 0;
                const stageName = jobType === 'TEXT_EXTRACT' ? '1. Text Extract' :
                                jobType === 'CHUNK' ? '2. Chunking' :
                                jobType === 'FTS_INDEX' ? '3. FTS Index' : jobType;

                return (
                  <tr key={jobType}>
                    <td className="px-4 py-2 text-sm font-medium text-gray-900">{stageName}</td>
                    <td className="px-4 py-2 text-center text-sm text-green-600 font-medium">{completed}</td>
                    <td className="px-4 py-2 text-center text-sm text-yellow-600">{stats.processing || 0}</td>
                    <td className="px-4 py-2 text-center text-sm text-red-600">{stats.failed || 0}</td>
                    <td className="px-4 py-2 text-center text-sm text-blue-600">{stats.pending || 0}</td>
                    <td className="px-4 py-2 text-center text-sm">
                      <span className={`font-medium ${stats.dead_letter ? 'text-orange-600' : 'text-gray-400'}`}>
                        {stats.dead_letter || 0} {stats.dead_letter ? '⚠️' : ''}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-sm text-gray-600">
          {(() => {
            const pipelineJobs = backlogByTypeEntries
              .filter(([jobType]) => ['TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX'].includes(jobType))
              .reduce((total, [jobType, stats]) =>
                total + (stats.completed || 0) + (stats.pending || 0) + (stats.processing || 0) + (stats.failed || 0) + (stats.dead_letter || 0), 0);
            const pipelineCompleted = backlogByTypeEntries
              .filter(([jobType]) => ['TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX'].includes(jobType))
              .reduce((total, [jobType, stats]) => total + (stats.completed || 0), 0);
            const pipelineProblems = backlogByTypeEntries
              .filter(([jobType]) => ['TEXT_EXTRACT', 'CHUNK', 'FTS_INDEX'].includes(jobType))
              .reduce((total, [jobType, stats]) => total + (stats.failed || 0) + (stats.dead_letter || 0), 0);

            return (
              <>
                <strong>Pipeline Jobs:</strong> {pipelineJobs} total
                <span className="ml-2 text-green-600">({pipelineCompleted} completed)</span>
                {pipelineProblems > 0 && (
                  <span className="ml-2 text-orange-600 font-medium">
                    ⚠️ {pipelineProblems} need attention
                  </span>
                )}
                <div className="mt-1 text-xs text-gray-500">
                  Note: Only showing text processing pipeline jobs. Excludes reindex_file jobs which are managed separately.
                </div>
              </>
            );
          })()}
        </div>
      </div>

      {/* Content Extraction Results */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Text Processing Results</h3>
        <div className="mb-4 text-sm text-gray-600">
          Results based on {status?.file_stats?.text_files || 0} text files (excludes {status?.file_stats?.non_text_files || 0} non-text files)
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="text-xl font-bold text-green-600">{status?.file_stats?.text_files_with_chunks || 0}</div>
            <div className="text-sm text-gray-600">Successfully Processed</div>
            <div className="text-xs text-gray-500 mt-1">Text Files</div>
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-xl font-bold text-blue-600">{totalChunks}</div>
            <div className="text-sm text-gray-600">Text Chunks Created</div>
            <div className="text-xs text-gray-500 mt-1">Searchable Pieces</div>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <div className="text-xl font-bold text-purple-600">
              {(status?.file_stats?.text_files_with_chunks || 0) > 0 ?
                (totalChunks / Math.max(1, status?.file_stats?.text_files_with_chunks || 0)).toFixed(1) : '0'}
            </div>
            <div className="text-sm text-gray-600">Avg Chunks/File</div>
            <div className="text-xs text-gray-500 mt-1">For processed files</div>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <div className="text-xl font-bold text-orange-600">
              {status?.file_stats?.text_processing_progress?.toFixed(1) || '0.0'}%
            </div>
            <div className="text-sm text-gray-600">Processing Progress</div>
            <div className="text-xs text-gray-500 mt-1">
              {status?.file_stats?.text_files_with_chunks || 0} of {status?.file_stats?.text_files || 0} text files
            </div>
          </div>
        </div>
      </div>

      {/* Service Health & Performance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">⚙️ Service Status</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Status</span>
              <span className={`text-sm font-medium flex items-center ${
                !status?.is_running ? 'text-red-600' :
                status?.is_paused ? 'text-yellow-600' : 'text-green-600'
              }`}>
                {!status?.is_running ? '🔴 Stopped' :
                 status?.is_paused ? '⏸️ Paused' : '🟢 Running'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Processing Rate</span>
              <span className="text-sm font-medium text-gray-900">{(status?.performance_stats.jobs_per_minute ?? 0).toFixed(1)} jobs/min</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Active Workers</span>
              <span className="text-sm font-medium text-gray-900">{status?.performance_stats.active_workers || 2}</span>
            </div>
            {status?.performance_stats.uptime_seconds && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Uptime</span>
                <span className="text-sm font-medium text-gray-900">{formatDuration(status.performance_stats.uptime_seconds)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">File Watcher</span>
              <span className={`text-sm font-medium flex items-center ${
                status?.watcher_status?.is_running ? 'text-green-600' : 'text-red-600'
              }`}>
                {status?.watcher_status?.is_running ? '🟢 Active' : '🔴 Inactive'}
              </span>
            </div>
            {status?.watcher_status?.files_monitored !== undefined && status.watcher_status.files_monitored > 0 && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Files Monitored</span>
                <span className="text-sm font-medium text-gray-900">{status.watcher_status.files_monitored}</span>
              </div>
            )}
            {status?.watcher_status?.last_activity && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Last Activity</span>
                <span className="text-sm font-medium text-gray-900">{formatDateTime(status.watcher_status.last_activity)}</span>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 Queue Health</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Active Queue</span>
              <span className={`text-sm font-medium ${status?.queue_stats.pending_jobs ? 'text-blue-600' : 'text-gray-400'}`}>
                {status?.queue_stats.pending_jobs || 0} pending
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Pipeline Jobs Issues</span>
              <span className={`text-sm font-medium ${pipelineProblems > 0 ? 'text-orange-600' : 'text-gray-400'}`}>
                {pipelineProblems} {pipelineProblems > 0 ? '⚠️' : 'jobs'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Invalid Reindex Jobs</span>
              <span className={`text-sm font-medium ${(status?.integrity_stats?.invalid_reindex_jobs || 0) > 0 ? 'text-orange-600' : 'text-gray-400'}`}>
                {status?.integrity_stats?.invalid_reindex_jobs || 0} {(status?.integrity_stats?.invalid_reindex_jobs || 0) > 0 ? '⚠️' : 'jobs'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Total Completed</span>
              <span className="text-sm font-medium text-green-600">{status?.queue_stats.completed_jobs || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Valid Job Success Rate</span>
              <span className="text-sm font-medium text-gray-900">
                {(() => {
                  const completed = status?.queue_stats.completed_jobs || 0;
                  const validProblems = pipelineProblems; // Exclude invalid reindex jobs
                  const totalValid = completed + validProblems;
                  return totalValid > 0 ? ((completed / totalValid) * 100).toFixed(1) : '0';
                })()}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Action Center */}
      {(pipelineProblems > 0 || (status?.integrity_stats?.invalid_reindex_jobs || 0) > 0) && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-orange-800 mb-3 flex items-center">
            ⚠️ Action Required
          </h3>
          <div className="space-y-4">
            {pipelineProblems > 0 && (
              <div>
                <p className="text-sm text-orange-700">
                  <strong>{pipelineProblems} text processing job{pipelineProblems === 1 ? '' : 's'}</strong> need attention.
                </p>
                <p className="text-sm text-orange-600 mt-1">
                  These jobs failed during the text extraction, chunking, or FTS indexing pipeline.
                </p>
              </div>
            )}

            {(status?.integrity_stats?.invalid_reindex_jobs || 0) > 0 && (
              <div>
                <p className="text-sm text-orange-700">
                  <strong>{status?.integrity_stats?.invalid_reindex_jobs} invalid reindex job{(status?.integrity_stats?.invalid_reindex_jobs || 0) === 1 ? '' : 's'}</strong> for non-text files.
                </p>
                <p className="text-sm text-orange-600 mt-1">
                  These jobs cannot succeed because non-text files don't go through text processing.
                </p>
              </div>
            )}

            <div className="flex flex-wrap gap-3 mt-4">
              {pipelineProblems > 0 && (
                <button
                  className="bg-orange-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-orange-700 transition-colors disabled:opacity-50"
                  onClick={handleRequeueDeadLetter}
                  disabled={controlLoading === 'requeue'}
                >
                  {controlLoading === 'requeue' ? 'Requeuing...' : 'Retry Pipeline Jobs'}
                </button>
              )}

              {(status?.integrity_stats?.invalid_reindex_jobs || 0) > 0 && (
                <button
                  className="bg-red-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
                  onClick={handleClearInvalidJobs}
                  disabled={controlLoading === 'clear-invalid'}
                >
                  {controlLoading === 'clear-invalid' ? 'Clearing...' : 'Clear Invalid Jobs'}
                </button>
              )}

              <button
                className="bg-gray-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors disabled:opacity-50"
                onClick={handleClearFailed}
                disabled={controlLoading === 'clear'}
              >
                {controlLoading === 'clear' ? 'Clearing...' : 'Clear Failed History'}
              </button>

              <button
                className="border border-orange-600 text-orange-600 px-4 py-2 rounded-md text-sm font-medium hover:bg-orange-50 transition-colors"
                onClick={handleViewLogs}
              >
                View Error Logs
              </button>
            </div>
          </div>
        </div>
      )}

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
                        {formatBytes(file.size_bytes)} | {formatDateTime(file.discovered_at)}
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
                        Job #{job.id} | {job.job_type}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {job.file_path || 'Unknown file'} | {formatDateTime(job.created_at)}
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

      {/* Force Reindex Modal */}
      {reindexModalOpen && !reindexBatchId && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
            <h3 className="text-lg font-bold mb-4">Force Reindex</h3>

            <div className="space-y-4">
              <p className="text-sm text-gray-900">
                Ready to start {reindexConfig.mode === 'soft' ? 'soft reindex' : 'hard reset'} on all files.
              </p>

              <div className="bg-gray-50 p-4 rounded-md">
                <div className="text-sm text-gray-900">
                  <span className="font-medium">Mode:</span> {reindexConfig.mode === 'soft' ? 'Soft Reindex' : 'Hard Reset'}
                </div>
                <div className="text-sm mt-1 text-gray-900">
                  <span className="font-medium">Scope:</span> All files
                </div>
              </div>

              {reindexConfig.mode === 'hard' && (
                <div className="bg-red-50 border border-red-200 p-3 rounded-md">
                  <p className="text-sm text-red-800">
                    ⚠️ <strong>Warning:</strong> Hard reset will delete all existing chunks and search data.
                    Search will be unavailable until reindexing completes.
                  </p>
                </div>
              )}

              <div className="flex justify-end space-x-2 mt-6">
                <button
                  onClick={() => setReindexModalOpen(false)}
                  className="px-4 py-2 text-gray-900 bg-gray-200 rounded-md hover:bg-gray-300"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    try {
                      await triggerReindex();
                      // Don't close modal, it will switch to progress view
                    } catch (err) {
                      alert(`Failed to trigger reindex: ${err}`);
                    }
                  }}
                  disabled={reindexLoading}
                  className={`px-4 py-2 text-white rounded-md disabled:opacity-50 ${
                    reindexConfig.mode === 'hard'
                      ? 'bg-red-600 hover:bg-red-700'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {reindexLoading ? 'Starting...' : 'Start Reindex'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reindex Progress Modal */}
      {reindexBatchId && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">Force Reindex Progress</h3>
            <div className="space-y-4">
              <p className="text-sm text-gray-900 mb-4">
                Reindex in progress...
              </p>

              {reindexStatus && (
                <div className="space-y-4">
                  <div className="bg-gray-50 p-4 rounded-md space-y-2">
                    <div className="text-sm text-gray-900">
                      <span className="font-medium">Status:</span> {reindexStatus.status}
                    </div>
                    <div className="text-sm text-gray-900">
                      <span className="font-medium">Progress:</span> {reindexStatus.files_processed}/{reindexStatus.candidates_count} files
                    </div>
                    <div className="text-sm text-gray-900">
                      <span className="font-medium">Failed:</span> {reindexStatus.files_failed} files
                    </div>
                  </div>

                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${reindexStatus.progress_percentage}%` }}
                    ></div>
                  </div>

                  {reindexStatus.status === 'RUNNING' && (
                    <div className="flex justify-center space-x-2">
                      <button
                        onClick={() => controlReindexBatch('pause')}
                        className="px-3 py-1 bg-yellow-600 text-white rounded text-sm hover:bg-yellow-700"
                      >
                        Pause
                      </button>
                      <button
                        onClick={() => controlReindexBatch('cancel')}
                        className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                      >
                        Cancel
                      </button>
                    </div>
                  )}

                  {reindexStatus.status === 'PAUSED' && (
                    <button
                      onClick={() => controlReindexBatch('resume')}
                      className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                    >
                      Resume
                    </button>
                  )}
                </div>
              )}

              <div className="flex justify-end mt-6">
                <button
                  onClick={() => {
                    setReindexModalOpen(false);
                    setReindexBatchId(null);
                    setReindexStatus(null);
                  }}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IndexerDashboard;
