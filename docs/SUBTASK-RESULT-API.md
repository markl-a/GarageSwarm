# Subtask Result Upload API

## Overview

The subtask result upload API allows worker agents to submit execution results for completed or failed subtasks. This endpoint is a critical component of the BMAD (Break-down, Multi-agent, Assemble, Deliver) workflow, enabling the distributed execution and coordination of decomposed tasks.

## Endpoint

```
POST /api/v1/subtasks/{subtask_id}/result
```

## Purpose

When a worker completes (or fails) a subtask execution, it must upload the result to the backend. This endpoint:

1. **Updates Subtask Status**: Marks the subtask as completed or failed in PostgreSQL
2. **Stores Execution Results**: Persists output data, metrics, and error information
3. **Updates Redis Cache**: Synchronizes real-time status in Redis for fast lookups
4. **Releases Worker**: Makes the worker available for new task assignments
5. **Triggers Scheduling**: Automatically allocates newly ready subtasks (whose dependencies are now satisfied)

## Request

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `subtask_id` | UUID | Unique identifier of the subtask |

### Request Body

```json
{
  "status": "completed",
  "result": {
    "output": "Task completed successfully",
    "files_created": ["main.py", "test.py"],
    "tokens_used": 1500,
    "lines_of_code": 250
  },
  "execution_time": 45.3,
  "error": null
}
```

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | Yes | Execution status: `"completed"` or `"failed"` |
| `result` | object | No | Dictionary containing execution output data, files, metrics, etc. |
| `execution_time` | float | Yes | Execution duration in seconds (must be >= 0) |
| `error` | string | No | Error message if the subtask failed |

#### Status Values

- **`completed`**: Subtask executed successfully
  - Progress is set to 100%
  - Triggers scheduling of dependent subtasks
  - Worker is released for new assignments

- **`failed`**: Subtask execution failed
  - Progress is reset to 0%
  - Error message is stored
  - Worker is released but dependent subtasks remain blocked

## Response

### Success Response (200 OK)

```json
{
  "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
  "status": "completed",
  "progress": 100,
  "message": "Subtask result uploaded successfully. Status: completed",
  "newly_allocated": 2
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `subtask_id` | UUID | UUID of the updated subtask |
| `status` | string | New subtask status |
| `progress` | integer | Subtask progress percentage (0-100) |
| `message` | string | Success message |
| `newly_allocated` | integer | Number of subtasks that were newly allocated as a result of this completion |

### Error Responses

#### 404 Not Found
```json
{
  "detail": "Subtask {subtask_id} not found"
}
```

#### 400 Bad Request
```json
{
  "detail": "Subtask is not in progress. Current status: pending"
}
```

```json
{
  "detail": "Invalid status. Must be 'completed' or 'failed', got: unknown"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Failed to upload subtask result: {error_message}"
}
```

## Workflow

### 1. Worker Executes Subtask
Worker receives a subtask assignment and begins execution.

### 2. Worker Uploads Result
Upon completion or failure, worker calls this endpoint with the result.

### 3. Backend Updates State
```
┌─────────────────────────────────────┐
│  Update PostgreSQL                   │
│  - Set status (completed/failed)    │
│  - Store result data                │
│  - Set completed_at timestamp       │
│  - Update progress (100% or 0%)     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Update Redis Cache                  │
│  - Set subtask status (TTL: 1h)     │
│  - Set subtask progress (TTL: 1h)   │
│  - Remove from in-progress set      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Release Worker                      │
│  - Set worker status to "online"    │
│  - Clear current task in Redis      │
│  - Update worker status in DB       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Trigger Scheduler (if completed)   │
│  - Find newly ready subtasks        │
│  - Allocate to available workers    │
│  - Return newly_allocated count     │
└─────────────────────────────────────┘
```

### 4. Dependent Subtasks Are Scheduled
If the subtask completed successfully, the scheduler checks for subtasks that were waiting on this one. Those subtasks are now "ready" and can be allocated to available workers.

## Example Usage

### Using cURL

#### Upload Successful Result
```bash
curl -X POST "http://localhost:8000/api/v1/subtasks/456e7890-e89b-12d3-a456-426614174001/result" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "result": {
      "output": "Successfully generated user authentication module",
      "files_created": ["auth.py", "user_model.py", "test_auth.py"],
      "tokens_used": 3420,
      "test_results": {
        "passed": 15,
        "failed": 0,
        "coverage": 92.5
      }
    },
    "execution_time": 127.8,
    "error": null
  }'
```

#### Upload Failed Result
```bash
curl -X POST "http://localhost:8000/api/v1/subtasks/456e7890-e89b-12d3-a456-426614174001/result" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "failed",
    "result": {
      "partial_output": "Generated partial implementation",
      "error_type": "CompilationError",
      "attempted_files": ["auth.py"]
    },
    "execution_time": 45.2,
    "error": "Failed to resolve import: missing dependency 'bcrypt'"
  }'
```

### Using Python (requests)

```python
import requests
from uuid import UUID

def upload_subtask_result(
    base_url: str,
    subtask_id: UUID,
    status: str,
    result: dict,
    execution_time: float,
    error: str = None
):
    """Upload subtask execution result"""
    url = f"{base_url}/api/v1/subtasks/{subtask_id}/result"

    payload = {
        "status": status,
        "result": result,
        "execution_time": execution_time,
        "error": error
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()

    return response.json()

# Example: Upload successful result
result = upload_subtask_result(
    base_url="http://localhost:8000",
    subtask_id=UUID("456e7890-e89b-12d3-a456-426614174001"),
    status="completed",
    result={
        "output": "Task completed successfully",
        "files_created": ["main.py", "test.py"],
        "tokens_used": 1500
    },
    execution_time=45.3
)

print(f"Uploaded result: {result}")
print(f"Newly allocated subtasks: {result['newly_allocated']}")
```

## Integration with Worker Agent

Worker agents should integrate this API as follows:

```python
class WorkerAgent:
    async def execute_subtask(self, subtask: Subtask):
        """Execute a subtask and upload result"""
        start_time = time.time()

        try:
            # Execute the subtask
            result = await self.run_task(subtask)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Upload successful result
            await self.upload_result(
                subtask_id=subtask.subtask_id,
                status="completed",
                result=result,
                execution_time=execution_time
            )

        except Exception as e:
            # Calculate execution time
            execution_time = time.time() - start_time

            # Upload failed result
            await self.upload_result(
                subtask_id=subtask.subtask_id,
                status="failed",
                result={"error_type": type(e).__name__},
                execution_time=execution_time,
                error=str(e)
            )

            raise

    async def upload_result(self, subtask_id, status, result, execution_time, error=None):
        """Upload subtask result to backend"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.backend_url}/api/v1/subtasks/{subtask_id}/result",
                json={
                    "status": status,
                    "result": result,
                    "execution_time": execution_time,
                    "error": error
                }
            )
            response.raise_for_status()
            return response.json()
```

## Best Practices

### 1. Always Upload Results
Even if execution fails, always upload a result with status="failed" and an error message. This ensures:
- The worker is properly released
- The subtask state is correctly tracked
- System administrators can debug failures

### 2. Include Rich Metadata
The `result` field is flexible - include any relevant information:
- Files created/modified
- Test results
- Resource usage (CPU, memory, tokens)
- Intermediate outputs
- Performance metrics

### 3. Accurate Execution Time
Track the full execution time, including:
- Tool initialization
- Actual task execution
- Result processing
- File I/O operations

### 4. Descriptive Error Messages
For failed subtasks, provide:
- Clear error description
- Error type/category
- Relevant context (stack trace, file location)
- Partial results if available

### 5. Idempotency
The endpoint is idempotent for the same status. If a worker crashes and restarts, it can safely re-upload the same result.

## Database Schema Impact

This endpoint updates the following fields in the `subtasks` table:

```sql
UPDATE subtasks SET
    status = 'completed',  -- or 'failed'
    output = '{"output": "...", "execution_time": 45.3}',
    error = NULL,  -- or error message
    progress = 100,  -- or 0 for failed
    completed_at = NOW()
WHERE subtask_id = ?;
```

## Redis Cache Updates

The endpoint synchronizes the following Redis keys:

```
subtasks:{subtask_id}:status         → "completed" or "failed" (TTL: 1h)
subtasks:{subtask_id}:progress       → 100 or 0 (TTL: 1h)
task_queue:in_progress              → Remove subtask_id from set
workers:{worker_id}:current_task    → Delete key
workers:{worker_id}:status          → Set to "online"
```

## Related Endpoints

- **GET /api/v1/subtasks/{subtask_id}**: Get subtask details and status
- **POST /api/v1/subtasks/{subtask_id}/allocate**: Allocate subtask to a worker
- **POST /api/v1/scheduler/run**: Manually trigger scheduling cycle
- **POST /api/v1/workers/{worker_id}/release**: Manually release a worker

## Troubleshooting

### "Subtask is not in progress"
The subtask must be in "in_progress" or "queued" status to accept results. Check the subtask status before uploading.

### "Worker not released"
If worker release fails, the error is logged but doesn't prevent the result upload. Check worker status manually and release if needed.

### "Scheduler trigger failed"
Scheduler errors are logged as warnings but don't prevent result upload. Dependent subtasks may need manual allocation.

## Performance Considerations

- **Database Transaction**: The endpoint uses a single transaction to update the subtask
- **Redis Operations**: All Redis updates are non-blocking and logged on failure
- **Async Scheduling**: Scheduler is triggered asynchronously after the result is persisted
- **Average Latency**: ~50-100ms for typical result uploads
- **Concurrent Uploads**: The endpoint is safe for concurrent uploads from multiple workers

## Security Considerations

1. **Authentication**: In production, add authentication to verify worker identity
2. **Authorization**: Ensure workers can only upload results for their assigned subtasks
3. **Input Validation**: Request data is validated using Pydantic schemas
4. **Rate Limiting**: Consider rate limiting to prevent abuse

## Monitoring

Key metrics to monitor:

- **Upload Rate**: Number of result uploads per minute
- **Success Rate**: Percentage of completed vs. failed results
- **Average Execution Time**: Mean execution time across all subtasks
- **Scheduler Effectiveness**: Average `newly_allocated` value
- **Error Types**: Distribution of error messages for failed subtasks

---

## Change Log

### v1.0 (2024-12-08)
- Initial implementation of subtask result upload API
- Support for completed and failed status
- Automatic worker release
- Integrated scheduler triggering
- Redis cache synchronization
