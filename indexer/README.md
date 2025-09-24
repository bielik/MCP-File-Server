# Indexer Service - MCP KnowledgeExplorer

## Overview
The Indexer Service is a FastAPI application that monitors the mounted filesystem, creates indexing jobs, and persists results to the shared SQLite database. It runs alongside the Backend and Frontend as part of the Phase 4B M2 architecture with full text processing capabilities.

- Database: shared SQLite at `/data/database.db`
- Watch root: `/source` (host folder bind-mounted)
- Control: pause/resume/throttle via REST
- Status: health and runtime metrics via REST

## Run-time Endpoints

- GET `/live`   — liveness probe (process up)
- GET `/ready`  — readiness probe (DB connectivity + service ready)
- GET `/status` — comprehensive status payload:
  - `service`: `is_running`, `should_stop`, `uptime_seconds`, `last_activity`
  - `stats`: `jobs_processed`, `jobs_failed`, `jobs_per_minute` (rolling)
  - `file_watcher`: `is_running`, `source_path`, `pending_stability_checks`, `observer_alive`
  - `queue`: counts by status, overdue retries, active workers, progress
- POST `/control/pause`   — persist `indexer_paused=true`
- POST `/control/resume`  — persist `indexer_paused=false`
- POST `/control/throttle/{percentage}` — set `throttle_pct` (0–100)

## Job Types (Phase 4B M2)

- `index_file`   — standard indexing (creates metadata record)
- `reindex_file` — reprocesses file (handled same as `index_file`)
- `TEXT_EXTRACT` — extracts text content using LlamaIndex SimpleDirectoryReader with fallback
- `CHUNK`        — splits text into 512-token chunks with 50-token overlap for processing
- `FTS_INDEX`    — populates FTS5 virtual table for full-text search capabilities
- `EMBED`        — prepares for vector embeddings (Phase 4B M3+)

## Configuration

The service uses the project-wide Phase4AConfig with Phase 4B M2 extensions. In Docker, paths are container-native:

- Database file: `/data/database.db` (backed by host `./data/database.db`)
- Source mount: `/source` (backed by host path from `.env` `SHARED_FS_PATH`)

Key env vars (see `config/env_config.py` for full list):

```bash
# Service ports
INDEXER_PORT=8002

# File watching
WATCHER_DEBOUNCE_SECONDS=2.0
WATCHER_STABILITY_CHECKS=3

# Queue behavior
JOB_RETRY_MAX_ATTEMPTS=3
JOB_RETENTION_DAYS=30
INDEXER_POLL_INTERVAL=5

# Database
DATABASE_PATH=./data   # Docker maps this to /data inside the container
```

## Host vs Container Paths

- Host path (Windows): e.g. `C:\Users\<you>\MCP Test`
- Container mount: `/source`
- All code inside containers operates on `/source`. The validator now treats `/source` as authoritative in Docker, so a Windows-style `SHARED_FS_PATH` in `.env` will not cause a false warning.

## Architecture Notes

- File watching: Watchdog observer with stability gating (debounce and consecutive checks) to avoid indexing in-progress writes.
- Queue: Crash-resilient job queue with atomic claims and exponential backoff; dead letter state for exhausted retries.
- Control settings: `control_settings` table stores pause/throttle and discovery epoch data.
- Throughput: Service reports `jobs_per_minute` (rolling) for dashboards/ETA.

## Docker Compose (excerpt)

```yaml
indexer:
  build:
    context: ./indexer
  ports:
    - "${INDEXER_PORT:-8002}:8002"
  volumes:
    - ./indexer:/app
    - ./backend:/backend
    - ${DATABASE_PATH:-./data}:/data
    - ${SHARED_FS_PATH:-./shared-fs}:/source
    - ./config:/config
  env_file:
    - ./.env
  command: uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

## Troubleshooting

- No files discovered: Verify your host folder exists and is mounted; inside container verify `/source` and that it contains files.
- Healthcheck failing: Confirm service responds at `/live`; ensure `requests` is installed (image includes it).
- Duplicate databases: Both backend and indexer must point to the same `/data/database.db`. Docker Compose handles this when `DATABASE_PATH=./data` in `.env`.

## Phase 4B M2 Status ✅ COMPLETE

**Keyword Search Path Implementation Complete**
- ✅ TEXT_EXTRACT → CHUNK → FTS_INDEX processing pipeline operational
- ✅ LlamaIndex integration with fallback strategies for reliable text extraction
- ✅ FTS5 virtual table with trigram tokenizer for typo-tolerant full-text search
- ✅ 49+ comprehensive tests validating all job processing functionality
- ✅ Maintains watcher, queue, and control foundations from Phase 4A

**Phase 4B M3 Roadmap:**
Phase 4B M3 will implement semantic search with vector embeddings, EMBED job processing, and hybrid search capabilities building on the current infrastructure.
