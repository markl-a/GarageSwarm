# Error Handling Guide

Quick reference for using the BMAD error handling system.

## Backend API Error Handling

### Available Exceptions

```python
from src.exceptions import (
    NotFoundError,       # 404 - Resource not found
    ValidationError,     # 400 - Invalid input
    ConflictError,       # 409 - Resource conflict
    UnauthorizedError,   # 401 - Authentication required
    ForbiddenError,      # 403 - Insufficient permissions
    ServiceUnavailableError,  # 503 - External service down
    TaskExecutionError,  # 500 - Task execution failed
    DatabaseError,       # 500 - Database operation failed
    RateLimitError,      # 429 - Rate limit exceeded
    TimeoutError,        # 504 - Operation timeout
)
```

### Usage Examples

#### 1. Resource Not Found
```python
async def get_task(task_id: str):
    task = await db.get(task_id)
    if not task:
        raise NotFoundError("Task", task_id)
    return task
```

#### 2. Input Validation
```python
async def create_task(description: str):
    if len(description) < 10:
        raise ValidationError(
            "Task description too short",
            details={
                "field": "description",
                "min_length": 10,
                "provided": len(description)
            }
        )
```

#### 3. Resource Conflict
```python
async def cancel_task(task_id: str):
    task = await get_task(task_id)
    if task.status == "completed":
        raise ConflictError(
            "Cannot cancel completed task",
            details={"task_id": task_id, "status": task.status}
        )
```

#### 4. Service Unavailable
```python
async def connect_redis():
    try:
        await redis.ping()
    except Exception as e:
        raise ServiceUnavailableError(
            "Redis",
            details={"host": redis_url, "error": str(e)}
        )
```

### Error Response Format

All errors return this format:
```json
{
    "status": "error",
    "message": "Human-readable error message",
    "details": {
        "additional": "context"
    },
    "path": "/api/v1/endpoint"
}
```

## Worker Agent Error Handling

### Available Exceptions

```python
from exceptions import (
    ConnectionError,        # Connection failures (recoverable)
    TaskExecutionError,     # Task execution failures
    ToolError,              # AI tool failures (recoverable)
    TimeoutError,           # Operation timeouts (non-recoverable)
    ConfigurationError,     # Invalid config (non-recoverable)
    RegistrationError,      # Worker registration failures (recoverable)
    HeartbeatError,         # Heartbeat failures (recoverable)
    SubtaskFetchError,      # Subtask fetch failures (recoverable)
    ResultSubmissionError,  # Result submission failures (recoverable)
)
```

### Retry Mechanisms

#### 1. Function Retry
```python
from utils.retry import retry_with_backoff

async def fetch_data():
    result = await retry_with_backoff(
        lambda: api.get("/data"),
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0
    )
    return result
```

#### 2. Decorator
```python
from utils.retry import with_retry

@with_retry(max_retries=3, base_delay=2.0)
async def submit_result(subtask_id: str, result: dict):
    response = await api.post(f"/subtasks/{subtask_id}/result", json=result)
    if response.status_code != 200:
        raise ResultSubmissionError("Failed to submit result")
    return response.json()
```

#### 3. Context Manager
```python
from utils.retry import RetryContext

async with RetryContext(max_retries=3, base_delay=1.0) as retry:
    while retry.should_retry():
        try:
            data = await api.fetch()
            retry.success()
            return data
        except ConnectionError as e:
            await retry.failed(e)
```

#### 4. Async Generator
```python
from utils.retry import retry_async_generator

async def stream_items():
    async for item in retry_async_generator(
        api.stream_updates,
        max_retries=3,
        base_delay=1.0
    ):
        yield item
```

### Retry Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | 3 | Maximum number of retry attempts |
| `base_delay` | 1.0 | Initial delay in seconds |
| `max_delay` | 60.0 | Maximum delay cap in seconds |
| `exponential_base` | 2.0 | Base for exponential backoff |
| `jitter` | True | Add random jitter to delays |
| `exceptions` | None | Specific exceptions to retry (None = all recoverable) |

### Backoff Calculation

```
delay = min(base_delay × (exponential_base ^ attempt), max_delay)

With jitter:
delay = delay × (0.5 + random() × 0.5)
```

**Examples:**
- Attempt 1: 1.0s
- Attempt 2: 2.0s
- Attempt 3: 4.0s
- Attempt 4: 8.0s
- etc.

## Best Practices

### 1. Choose the Right Exception
```python
# ❌ DON'T use generic exceptions
raise Exception("Task not found")

# ✅ DO use specific exceptions
raise NotFoundError("Task", task_id)
```

### 2. Provide Helpful Details
```python
# ❌ DON'T use vague messages
raise ValidationError("Invalid input")

# ✅ DO provide context
raise ValidationError(
    "Invalid task type",
    details={
        "field": "task_type",
        "allowed": ["develop_feature", "bug_fix"],
        "provided": "unknown_type"
    }
)
```

### 3. Use Recoverable Flags
```python
# Non-recoverable error - don't retry
raise TaskExecutionError(
    "Invalid code syntax",
    recoverable=False
)

# Recoverable error - retry is OK
raise ToolError(
    "API rate limit exceeded",
    recoverable=True
)
```

### 4. Don't Swallow Errors
```python
# ❌ DON'T swallow exceptions
try:
    result = await operation()
except Exception:
    return None  # Error lost!

# ✅ DO let them bubble up
result = await operation()
# Let error handler deal with it
```

### 5. Log Before Raising
```python
# ✅ DO log for debugging
logger.error(
    "Task execution failed",
    task_id=task_id,
    error=str(e),
    exc_info=True
)
raise TaskExecutionError("Task execution failed")
```

## Testing Error Handling

### Testing Exception Raising
```python
import pytest
from src.exceptions import NotFoundError

async def test_task_not_found():
    with pytest.raises(NotFoundError) as exc_info:
        await service.get_task("nonexistent")

    assert "Task" in str(exc_info.value)
    assert exc_info.value.status_code == 404
```

### Testing Error Responses
```python
def test_error_response(client):
    response = client.get("/tasks/nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"]
```

### Testing Retry Logic
```python
import pytest
from utils.retry import retry_with_backoff

@pytest.mark.asyncio
async def test_retry_success():
    call_count = 0

    async def func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Failed")
        return "success"

    result = await retry_with_backoff(func, max_retries=5)

    assert result == "success"
    assert call_count == 3  # Succeeded on 3rd attempt
```

## Common Patterns

### Pattern 1: Service Layer Error Handling
```python
class TaskService:
    async def get_task(self, task_id: str):
        task = await self.repository.get(task_id)
        if not task:
            raise NotFoundError("Task", task_id)
        return task

    async def cancel_task(self, task_id: str):
        task = await self.get_task(task_id)

        if task.status in ["completed", "cancelled"]:
            raise ConflictError(
                f"Cannot cancel {task.status} task",
                details={"task_id": task_id, "status": task.status}
            )

        task.status = "cancelled"
        await self.repository.update(task)
```

### Pattern 2: Worker Operation with Retry
```python
class WorkerAgent:
    @with_retry(max_retries=3, base_delay=2.0)
    async def fetch_subtask(self):
        """Fetch next subtask from backend"""
        try:
            response = await self.api_client.get(
                f"/workers/{self.worker_id}/subtasks"
            )
            if response.status_code == 404:
                return None  # No subtasks available
            if response.status_code != 200:
                raise SubtaskFetchError(
                    "Failed to fetch subtask",
                    details={"status_code": response.status_code}
                )
            return response.json()
        except httpx.TimeoutError:
            raise TimeoutError("Subtask fetch timeout")
        except httpx.ConnectError as e:
            raise ConnectionError(
                "Cannot connect to backend",
                details={"error": str(e)}
            )
```

### Pattern 3: Graceful Degradation
```python
async def get_task_with_cache(task_id: str):
    """Try cache first, fall back to database"""
    try:
        # Try cache first (fast but may fail)
        result = await cache.get(task_id)
        if result:
            return result
    except ServiceUnavailableError:
        logger.warning("Cache unavailable, using database")

    # Fall back to database (slower but reliable)
    task = await database.get(task_id)
    if not task:
        raise NotFoundError("Task", task_id)

    # Try to update cache (don't fail if it doesn't work)
    try:
        await cache.set(task_id, task)
    except ServiceUnavailableError:
        pass  # Cache update failed, but we have the data

    return task
```

## Troubleshooting

### Issue: Exceptions not being caught by handlers
**Solution:** Ensure you're importing from `src.exceptions` not built-in exceptions:
```python
# ❌ Wrong
from builtins import TimeoutError

# ✅ Correct
from src.exceptions import TimeoutError
```

### Issue: Retry not working
**Solution:** Check the `recoverable` flag:
```python
# This won't retry:
raise TaskExecutionError("Error", recoverable=False)

# This will retry:
raise TaskExecutionError("Error", recoverable=True)
```

### Issue: Too many retries causing delays
**Solution:** Adjust retry configuration:
```python
# Reduce retries and delays for fast-failing operations
@with_retry(max_retries=2, base_delay=0.5, max_delay=5.0)
async def quick_operation():
    pass
```

## Additional Resources

- API Documentation: `/docs` (when DEBUG=True)
- Exception Classes: `backend/src/exceptions.py`
- Error Handlers: `backend/src/middleware/error_handler.py`
- Retry Utils: `worker-agent/src/utils/retry.py`
- Tests: `backend/tests/unit/test_error_handling.py`
