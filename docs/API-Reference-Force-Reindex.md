# Force Reindex API Reference

**Version:** 1.0
**Base URL:** `http://localhost:8000/admin/reindex`
**Authentication:** Required (`X-Admin-Key` header)

## Overview

The Force Reindex API provides programmatic access to batch reindexing operations. All endpoints require admin authentication and support JSON request/response format.

## Authentication

### Admin Key Header
All endpoints require the `X-Admin-Key` header:

```http
X-Admin-Key: admin-secret-key-change-me
```

**Default Admin Key:** `admin-secret-key-change-me`
**Environment Variable:** `ADMIN_API_KEY`
**Security Note:** Change default key in production environments

### Error Responses for Authentication
```json
HTTP 403 Forbidden
{
  "detail": "Admin access required"
}
```

## Core Endpoints

### 1. Create Reindex Batch

Creates a new batch reindex operation.

**Endpoint:** `POST /admin/reindex/force`

#### Request

**Headers:**
```http
Content-Type: application/json
X-Admin-Key: admin-secret-key-change-me
```

**Body Schema:**
```json
{
  "mode": "string",           // Required: "soft" or "hard"
  "scope": {
    "path_prefix": "string",  // Optional: path filter (e.g., "/projects")
    "text_only": boolean      // Optional: text files only (default: true)
  },
  "dry_run": boolean          // Optional: count only, no execution (default: false)
}
```

**Example Request:**
```json
{
  "mode": "soft",
  "scope": {
    "path_prefix": "/projects",
    "text_only": true
  },
  "dry_run": false
}
```

#### Response

**Success (HTTP 200):**
```json
{
  "batch_id": "3ef39101-d734-4330-a989-5b75d8599c9d",
  "status": "RUNNING",
  "counts": {
    "candidates": 795,
    "jobs_created": 795
  },
  "message": "Reindex batch created. Processing 795 files."
}
```

**Dry Run Response:**
```json
{
  "batch_id": "3ef39101-d734-4330-a989-5b75d8599c9d",
  "status": "COMPLETED",
  "counts": {
    "candidates": 795,
    "jobs_created": 0
  },
  "message": "Dry run complete: Would reindex 795 files"
}
```

#### Error Responses

**Validation Error (HTTP 400):**
```json
{
  "detail": "Invalid mode: must be 'soft' or 'hard'"
}
```

**Active Batch Conflict (HTTP 409):**
```json
{
  "detail": "Another reindex batch is already active"
}
```

**Authentication Required (HTTP 403):**
```json
{
  "detail": "Admin access required"
}
```

**Server Error (HTTP 500):**
```json
{
  "detail": "Failed to create batch: [detailed error message]"
}
```

### 2. Get Batch Status

Retrieves detailed status information for a specific batch.

**Endpoint:** `GET /admin/reindex/batches/{batch_id}`

#### Request

**Headers:**
```http
X-Admin-Key: admin-secret-key-change-me
```

**Path Parameters:**
- `batch_id` (string, required): UUID of the batch

**Example:**
```http
GET /admin/reindex/batches/3ef39101-d734-4330-a989-5b75d8599c9d
```

#### Response

**Success (HTTP 200):**
```json
{
  "batch_id": "3ef39101-d734-4330-a989-5b75d8599c9d",
  "mode": "soft",
  "status": "RUNNING",
  "path_prefix": "/projects",
  "text_only": true,
  "candidates_count": 795,
  "jobs_created": 795,
  "files_processed": 423,
  "files_failed": 12,
  "progress_percentage": 53.2,
  "processing_rate": 2.8,
  "eta_seconds": 132,
  "created_at": "2025-01-29T10:30:00.000Z",
  "started_at": "2025-01-29T10:30:02.000Z",
  "completed_at": null,
  "job_summary": {
    "PENDING": 0,
    "PROCESSING": 7,
    "COMPLETED": 410,
    "FAILED": 12,
    "DEAD_LETTER": 0
  },
  "recent_errors": [
    "Failed to process file: permission denied",
    "Timeout reading file: connection lost"
  ]
}
```

**Completed Batch:**
```json
{
  "batch_id": "3ef39101-d734-4330-a989-5b75d8599c9d",
  "mode": "soft",
  "status": "COMPLETED",
  "path_prefix": "/projects",
  "text_only": true,
  "candidates_count": 795,
  "jobs_created": 795,
  "files_processed": 783,
  "files_failed": 12,
  "progress_percentage": 100.0,
  "processing_rate": 0,
  "eta_seconds": 0,
  "created_at": "2025-01-29T10:30:00.000Z",
  "started_at": "2025-01-29T10:30:02.000Z",
  "completed_at": "2025-01-29T10:45:30.000Z",
  "job_summary": {
    "PENDING": 0,
    "PROCESSING": 0,
    "COMPLETED": 783,
    "FAILED": 12,
    "DEAD_LETTER": 0
  }
}
```

#### Error Responses

**Batch Not Found (HTTP 404):**
```json
{
  "detail": "Batch not found: 3ef39101-d734-4330-a989-5b75d8599c9d"
}
```

**Authentication Required (HTTP 403):**
```json
{
  "detail": "Admin access required"
}
```

### 3. List Batches

Lists all reindex batches with optional filtering.

**Endpoint:** `GET /admin/reindex/batches`

#### Request

**Headers:**
```http
X-Admin-Key: admin-secret-key-change-me
```

**Query Parameters:**
- `include_completed` (boolean, optional): Include completed batches (default: false)
- `limit` (integer, optional): Maximum number of results (default: 50, max: 500)
- `offset` (integer, optional): Number of results to skip (default: 0)

**Examples:**
```http
GET /admin/reindex/batches
GET /admin/reindex/batches?include_completed=true&limit=10
GET /admin/reindex/batches?offset=50&limit=25
```

#### Response

**Success (HTTP 200):**
```json
{
  "batches": [
    {
      "id": "3ef39101-d734-4330-a989-5b75d8599c9d",
      "mode": "soft",
      "status": "RUNNING",
      "progress_percentage": 53.2,
      "files_processed": 423,
      "candidates_count": 795,
      "path_prefix": "/projects",
      "created_at": "2025-01-29T10:30:00.000Z"
    },
    {
      "id": "7a2b4c1e-9f8d-4e5a-b3c2-1d6e7f8a9b0c",
      "mode": "hard",
      "status": "COMPLETED",
      "progress_percentage": 100.0,
      "files_processed": 1200,
      "candidates_count": 1200,
      "path_prefix": null,
      "created_at": "2025-01-29T09:15:00.000Z",
      "completed_at": "2025-01-29T09:45:30.000Z"
    }
  ],
  "total": 2,
  "has_more": false
}
```

**No Batches:**
```json
{
  "batches": [],
  "total": 0,
  "has_more": false
}
```

### 4. Control Batch Operations

Control the execution of a running batch (pause, resume, cancel).

**Endpoints:**
- `POST /admin/reindex/batches/{batch_id}/pause`
- `POST /admin/reindex/batches/{batch_id}/resume`
- `POST /admin/reindex/batches/{batch_id}/cancel`

#### Request

**Headers:**
```http
Content-Type: application/json
X-Admin-Key: admin-secret-key-change-me
```

**Path Parameters:**
- `batch_id` (string, required): UUID of the batch

**Examples:**
```http
POST /admin/reindex/batches/3ef39101-d734-4330-a989-5b75d8599c9d/pause
POST /admin/reindex/batches/3ef39101-d734-4330-a989-5b75d8599c9d/resume
POST /admin/reindex/batches/3ef39101-d734-4330-a989-5b75d8599c9d/cancel
```

#### Response

**Success (HTTP 200):**
```json
{
  "message": "Batch paused successfully",
  "batch_id": "3ef39101-d734-4330-a989-5b75d8599c9d",
  "status": "PAUSED"
}
```

```json
{
  "message": "Batch resumed successfully",
  "batch_id": "3ef39101-d734-4330-a989-5b75d8599c9d",
  "status": "RUNNING"
}
```

```json
{
  "message": "Batch cancelled successfully",
  "batch_id": "3ef39101-d734-4330-a989-5b75d8599c9d",
  "status": "CANCELLED"
}
```

#### Error Responses

**Invalid State Transition (HTTP 400):**
```json
{
  "detail": "Cannot pause batch: batch is not running"
}
```

**Batch Not Found (HTTP 404):**
```json
{
  "detail": "Batch not found: 3ef39101-d734-4330-a989-5b75d8599c9d"
}
```

### 5. System Status

Get overall reindex system status and active batch information.

**Endpoint:** `GET /admin/reindex/status`

#### Request

**Headers:**
```http
X-Admin-Key: admin-secret-key-change-me
```

#### Response

**Success (HTTP 200):**
```json
{
  "has_active_batch": true,
  "active_batch_id": "3ef39101-d734-4330-a989-5b75d8599c9d",
  "active_batch_status": "RUNNING",
  "maintenance_mode": false,
  "total_batches": 15,
  "completed_batches": 12,
  "failed_batches": 2,
  "system_version": "1.0.0",
  "indexer_status": "healthy",
  "last_activity": "2025-01-29T10:45:30.000Z"
}
```

**No Active Batch:**
```json
{
  "has_active_batch": false,
  "active_batch_id": null,
  "active_batch_status": null,
  "maintenance_mode": false,
  "total_batches": 15,
  "completed_batches": 14,
  "failed_batches": 1,
  "system_version": "1.0.0",
  "indexer_status": "healthy",
  "last_activity": "2025-01-29T10:45:30.000Z"
}
```

### 6. Maintenance Mode Control

Emergency endpoint to clear maintenance mode if system gets stuck.

**Endpoint:** `DELETE /admin/reindex/maintenance-mode`

#### Request

**Headers:**
```http
X-Admin-Key: admin-secret-key-change-me
```

#### Response

**Success (HTTP 200):**
```json
{
  "message": "Maintenance mode cleared successfully",
  "maintenance_mode": false
}
```

**Already Clear:**
```json
{
  "message": "Maintenance mode was already cleared",
  "maintenance_mode": false
}
```

## Data Models

### ReindexScope
```typescript
interface ReindexScope {
  path_prefix?: string;    // Optional path filter
  text_only: boolean;      // Filter to text files only
}
```

### ReindexRequest
```typescript
interface ReindexRequest {
  mode: "soft" | "hard";   // Reindex mode
  scope: ReindexScope;     // Scope configuration
  dry_run: boolean;        // Execute or count only
}
```

### BatchStatus
```typescript
interface BatchStatus {
  batch_id: string;               // UUID
  mode: "soft" | "hard";          // Reindex mode
  status: BatchStatusEnum;        // Current status
  path_prefix?: string;           // Path filter
  text_only: boolean;             // File type filter
  candidates_count: number;       // Total files to process
  jobs_created: number;           // Jobs created
  files_processed: number;        // Files completed
  files_failed: number;           // Files failed
  progress_percentage: number;    // Completion percentage
  processing_rate: number;        // Files per second
  eta_seconds: number;            // Estimated time to completion
  created_at: string;             // ISO datetime
  started_at?: string;            // ISO datetime
  completed_at?: string;          // ISO datetime
  job_summary: JobSummary;        // Job counts by status
  recent_errors?: string[];       // Recent error messages
}
```

### BatchStatusEnum
```typescript
enum BatchStatusEnum {
  PLANNING = "PLANNING",
  RUNNING = "RUNNING",
  PAUSED = "PAUSED",
  CANCELLING = "CANCELLING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
  CANCELLED = "CANCELLED"
}
```

### JobSummary
```typescript
interface JobSummary {
  PENDING: number;        // Jobs waiting to start
  PROCESSING: number;     // Jobs currently running
  COMPLETED: number;      // Jobs finished successfully
  FAILED: number;         // Jobs that failed
  DEAD_LETTER: number;    // Jobs that exceeded retry limit
}
```

## Rate Limiting

### Global Constraints
- **Maximum 1 active batch** per system
- **No concurrent batch creation** (enforced by database constraints)
- **Request timeout**: 30 seconds for batch creation
- **Status polling**: Recommended interval 2-5 seconds

### Batch Constraints
- **Maximum batch size**: 100,000 files (configurable)
- **Chunk size**: 5,000 files processed per transaction
- **Job retry limit**: 3 attempts per file
- **Batch timeout**: 24 hours maximum runtime

## Error Codes Summary

| HTTP Code | Description | Common Causes |
|-----------|-------------|---------------|
| `200` | Success | Operation completed successfully |
| `400` | Bad Request | Invalid parameters, validation errors |
| `403` | Forbidden | Missing or invalid admin key |
| `404` | Not Found | Batch ID doesn't exist |
| `409` | Conflict | Another batch is already active |
| `422` | Unprocessable Entity | Valid JSON but invalid business logic |
| `429` | Too Many Requests | Rate limiting (future enhancement) |
| `500` | Internal Server Error | Database errors, service failures |
| `503` | Service Unavailable | System maintenance mode |

## Integration Examples

### Python Example

```python
import requests
import time

class ReindexClient:
    def __init__(self, base_url="http://localhost:8000", api_key="admin-secret-key-change-me"):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "X-Admin-Key": api_key
        }

    def trigger_reindex(self, mode="soft", path_prefix=None, text_only=True):
        """Trigger a reindex batch and return batch_id."""
        payload = {
            "mode": mode,
            "scope": {
                "path_prefix": path_prefix,
                "text_only": text_only
            },
            "dry_run": False
        }

        response = requests.post(
            f"{self.base_url}/admin/reindex/force",
            json=payload,
            headers=self.headers
        )

        if response.status_code == 200:
            return response.json()["batch_id"]
        else:
            raise Exception(f"Failed to trigger reindex: {response.text}")

    def wait_for_completion(self, batch_id):
        """Poll batch status until completion."""
        while True:
            response = requests.get(
                f"{self.base_url}/admin/reindex/batches/{batch_id}",
                headers=self.headers
            )

            if response.status_code == 200:
                status = response.json()
                print(f"Progress: {status['progress_percentage']:.1f}% "
                      f"({status['files_processed']}/{status['candidates_count']})")

                if status["status"] in ["COMPLETED", "FAILED", "CANCELLED"]:
                    return status

                time.sleep(5)  # Poll every 5 seconds
            else:
                raise Exception(f"Failed to get status: {response.text}")

# Usage
client = ReindexClient()
batch_id = client.trigger_reindex(mode="soft", path_prefix="/projects")
result = client.wait_for_completion(batch_id)
print(f"Reindex completed: {result['status']}")
```

### JavaScript/Node.js Example

```javascript
class ReindexClient {
    constructor(baseUrl = 'http://localhost:8000', apiKey = 'admin-secret-key-change-me') {
        this.baseUrl = baseUrl;
        this.headers = {
            'Content-Type': 'application/json',
            'X-Admin-Key': apiKey
        };
    }

    async triggerReindex(mode = 'soft', pathPrefix = null, textOnly = true) {
        const payload = {
            mode,
            scope: {
                path_prefix: pathPrefix,
                text_only: textOnly
            },
            dry_run: false
        };

        const response = await fetch(`${this.baseUrl}/admin/reindex/force`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const result = await response.json();
            return result.batch_id;
        } else {
            const error = await response.text();
            throw new Error(`Failed to trigger reindex: ${error}`);
        }
    }

    async getBatchStatus(batchId) {
        const response = await fetch(`${this.baseUrl}/admin/reindex/batches/${batchId}`, {
            headers: this.headers
        });

        if (response.ok) {
            return await response.json();
        } else {
            throw new Error(`Failed to get batch status: ${await response.text()}`);
        }
    }

    async waitForCompletion(batchId, pollInterval = 5000) {
        return new Promise((resolve, reject) => {
            const poll = async () => {
                try {
                    const status = await this.getBatchStatus(batchId);
                    console.log(`Progress: ${status.progress_percentage.toFixed(1)}% ` +
                              `(${status.files_processed}/${status.candidates_count})`);

                    if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(status.status)) {
                        resolve(status);
                    } else {
                        setTimeout(poll, pollInterval);
                    }
                } catch (error) {
                    reject(error);
                }
            };
            poll();
        });
    }
}

// Usage
(async () => {
    const client = new ReindexClient();
    const batchId = await client.triggerReindex('soft', '/projects');
    const result = await client.waitForCompletion(batchId);
    console.log(`Reindex completed: ${result.status}`);
})();
```

### cURL Examples

```bash
# Create soft reindex
curl -X POST http://localhost:8000/admin/reindex/force \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: admin-secret-key-change-me" \
  -d '{
    "mode": "soft",
    "scope": {
      "path_prefix": "/projects",
      "text_only": true
    },
    "dry_run": false
  }'

# Get batch status
curl -H "X-Admin-Key: admin-secret-key-change-me" \
  http://localhost:8000/admin/reindex/batches/3ef39101-d734-4330-a989-5b75d8599c9d

# Pause batch
curl -X POST \
  -H "X-Admin-Key: admin-secret-key-change-me" \
  http://localhost:8000/admin/reindex/batches/3ef39101-d734-4330-a989-5b75d8599c9d/pause

# Get system status
curl -H "X-Admin-Key: admin-secret-key-change-me" \
  http://localhost:8000/admin/reindex/status
```

## Best Practices

### API Usage
1. **Always check system status** before creating new batches
2. **Use dry run** for large operations to estimate impact
3. **Monitor progress regularly** but don't poll more than every 2 seconds
4. **Handle errors gracefully** with appropriate retry logic
5. **Store batch IDs** for later reference and monitoring

### Performance
1. **Use path filtering** to limit scope when possible
2. **Schedule large operations** during off-peak hours
3. **Monitor system resources** during batch operations
4. **Consider soft reindex first** before using hard reset
5. **Allow batches to complete** before starting new operations

### Security
1. **Change default admin key** in production environments
2. **Use HTTPS** for API communications
3. **Limit API access** to authorized administrators only
4. **Log and monitor** all reindex operations
5. **Regularly rotate** admin API keys

---

**Last Updated**: January 29, 2025
**Version**: 1.0
**Contact**: Development Team
**Status**: Production Ready ✅