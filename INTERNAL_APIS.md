# INTERNAL_APIS.md - MCP KnowledgeExplorer

This document formalizes internal service contracts between Backend and Indexer to aid maintenance and future development.

## 1) Database Contracts (shared SQLite at /data/database.db)

Tables (SQLAlchemy models in `backend/app/models/indexing.py`):

- indexed_files (IndexedFile)
  - id (int, PK)
  - doc_id (str, unique)
  - path (str) — relative to `/source`
  - file_hash (str)
  - size_bytes (int)
  - mtime_epoch (int)
  - discovered_at (int)
  - last_indexed_at (int | null)
  - is_indexed (bool)
  - index_version (str | null)
  - mime_type (str | null)
  - is_text (bool)
  - is_binary (bool)
  - has_ocr (bool)
  - Indexes: (path, file_hash), (mtime_epoch, is_indexed), (discovered_at, is_indexed)

- index_jobs (IndexJob)
  - id (int, PK)
  - job_signature (str, unique) — dedupe key on (file_id, job_type)
  - file_id (FK -> indexed_files.id)
  - job_type (str) — e.g., `index_file`, `reindex_file`
  - status (str) — `pending`, `processing`, `failed`, `completed`, `dead_letter`
  - created_at / claimed_at / started_at / completed_at (epoch int)
  - retry_count, max_retries, next_retry_at (epoch int)
  - last_error (text)
  - worker_id (str)

- control_settings (ControlSetting)
  - key (str, PK) — `indexer_paused`, `throttle_pct`, `discovery_epoch`
  - value (str) + value_type (str) — boolean/integer/float/string
  - description (text | null)
  - created_at / updated_at (epoch int)

## 2) Health & Status Endpoints

Indexer service (port 8002):
- GET `/live` → `{ status: "ok", timestamp: number }`
- GET `/ready` → `{ status: "ready", database: "connected", service: "running" }` (503 on not ready)
- GET `/status` → example shape:
```json
{
  "service": {
    "is_running": true,
    "should_stop": false,
    "uptime_seconds": 123.4,
    "last_activity": 1737300000.0
  },
  "stats": {
    "jobs_processed": 10,
    "jobs_failed": 1,
    "jobs_per_minute": 6.0
  },
  "file_watcher": {
    "is_running": true,
    "source_path": "/source",
    "pending_stability_checks": 0,
    "observer_alive": true
  },
  "queue": {
    "pending_jobs": 2,
    "processing_jobs": 1,
    "completed_jobs": 120,
    "failed_jobs": 0,
    "dead_letter_jobs": 0,
    "overdue_retries": 0,
    "avg_processing_time": 0.2,
    "max_processing_time": 0.4,
    "active_workers": 1,
    "total_files": 150,
    "indexed_files": 140,
    "indexing_progress": 93.3
  },
  "config": {
    "batch_size": 50,
    "max_workers": 2,
    "poll_interval": 5,
    "source_path": "/source"
  }
}
```

Backend API (port 8000):
- GET `/api/indexer/status` → aggregates DB + calls indexer `/status`
  - Response model: `{ is_running, is_paused, throttle_percentage, queue_stats, file_stats, performance_stats }`
  - performance_stats may include `eta_minutes` if `jobs_per_minute` > 0 and there are pending jobs
- POST `/api/indexer/control { action, value? }` → writes `control_settings`
- GET `/api/indexer/files?limit&offset&indexed_only` → returns file metadata list
- GET `/api/indexer/jobs?limit&offset&status_filter` → returns recent jobs
- POST `/api/indexer/reindex/{doc_id}` → queues reindexing job and marks file not indexed

## 3) Control Semantics

- Pause/resume: Single shared flag (`indexer_paused`) read by indexer main loop; backend writes via API.
- Throttle: `throttle_pct` (0–100) slows processing loop using async sleeps.
- Discovery epoch: `discovery_epoch` helps initial crawl avoid duplicate jobs.

## 4) Path Semantics

- Host (Windows) path: e.g., `C:\\Users\\<you>\\MCP Test` is bind-mounted to container `/source`.
- All internal DB `IndexedFile.path` values are relative to `/source`.
- All services read/write using `/source` (container path). Validators treat `/source` as authoritative when present.

## 5) Versioning & Compatibility

- Schema versioning: `schema_version` managed by `DatabaseBootstrap`; current Phase 4A version: `4.0.0`.
- SQLite PRAGMAs: WAL mode, NORMAL synchronous, busy_timeout=5000, foreign_keys=ON.
- Healthchecks: Containers rely on HTTP health endpoints; Python `requests` available in images.

