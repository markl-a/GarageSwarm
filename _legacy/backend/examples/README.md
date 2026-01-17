# WebSocket Examples

This directory contains example scripts demonstrating how to use the WebSocket real-time log streaming API.

## Prerequisites

Install required dependencies:

```bash
pip install websockets httpx
```

## Examples

### 1. WebSocket Client (websocket_client.py)

Connect to the WebSocket endpoint and receive real-time logs.

**Usage:**
```bash
python websocket_client.py <task_id> [base_url]
```

**Examples:**
```bash
# Connect to local backend
python websocket_client.py 550e8400-e29b-41d4-a716-446655440000

# Connect to remote backend
python websocket_client.py 550e8400-e29b-41d4-a716-446655440000 ws://backend.example.com
```

**Features:**
- Real-time log streaming
- Colored output by log level
- Automatic reconnection handling
- Subscription management
- Ping/pong heartbeat

### 2. Worker Log Sender (send_log_example.py)

Send log messages from workers during task execution.

**Usage:**

**Simulate task execution with multiple logs:**
```bash
python send_log_example.py simulate <subtask_id> [base_url]
```

**Send a single log message:**
```bash
python send_log_example.py send <subtask_id> <level> <message> [base_url]
```

**Examples:**
```bash
# Simulate task execution
python send_log_example.py simulate 550e8400-e29b-41d4-a716-446655440001

# Send single log
python send_log_example.py send 550e8400-e29b-41d4-a716-446655440001 info "Processing data"

# Send with remote backend
python send_log_example.py send 550e8400-e29b-41d4-a716-446655440001 warning "High memory" http://backend.example.com
```

## Testing Workflow

### Setup

1. **Start the backend server:**
   ```bash
   cd backend
   python -m src.main
   ```

2. **Create a task** (in another terminal):
   ```bash
   curl -X POST http://localhost:8000/api/v1/tasks \
     -H "Content-Type: application/json" \
     -d '{"description": "Test task for WebSocket logging"}'
   ```

   Note the returned `task_id` and `subtask_id` (after task decomposition).

### Test 1: Real-time Streaming

**Terminal 1 - Start WebSocket client:**
```bash
cd backend/examples
python websocket_client.py <task_id>
```

**Terminal 2 - Send logs:**
```bash
cd backend/examples
python send_log_example.py simulate <subtask_id>
```

You should see logs appearing in real-time in Terminal 1.

### Test 2: Multiple Clients

**Terminal 1 - Client 1:**
```bash
python websocket_client.py <task_id>
```

**Terminal 2 - Client 2:**
```bash
python websocket_client.py <task_id>
```

**Terminal 3 - Send logs:**
```bash
python send_log_example.py simulate <subtask_id>
```

Both clients should receive the same logs simultaneously.

### Test 3: Historical Logs

After sending logs, retrieve historical logs:

```bash
curl http://localhost:8000/api/v1/tasks/<task_id>/logs?limit=50
```

## Integration with Worker Agent

To integrate log streaming into your worker agent:

```python
from uuid import UUID
import httpx

class WorkerAgent:
    def __init__(self, subtask_id: UUID, backend_url: str):
        self.subtask_id = subtask_id
        self.backend_url = backend_url
        self.client = httpx.AsyncClient()

    async def send_log(self, level: str, message: str, metadata: dict = None):
        """Send log to backend"""
        url = f"{self.backend_url}/api/v1/subtasks/{self.subtask_id}/log"
        payload = {
            "level": level,
            "message": message,
            "metadata": metadata or {}
        }
        try:
            response = await self.client.post(url, json=payload, timeout=5.0)
            response.raise_for_status()
        except Exception as e:
            # Log failure shouldn't block task execution
            print(f"Warning: Failed to send log: {e}")

    async def execute_task(self):
        """Execute task with logging"""
        await self.send_log("info", "Task execution started")

        try:
            # Your task logic here
            await self.send_log("info", "Processing step 1")
            # ... more processing ...

            await self.send_log("info", "Task completed successfully")
        except Exception as e:
            await self.send_log("error", f"Task failed: {str(e)}")
            raise
```

## Troubleshooting

### Connection Refused
- Ensure the backend server is running
- Check the base URL (default: ws://localhost:8000)
- Verify firewall settings

### Task Not Found (1008 Close Code)
- Verify the task_id exists
- Create a task first using the API
- Check the task status in the database

### Subtask Not Found (404)
- Verify the subtask_id exists
- Ensure the task has been decomposed
- Check subtask status in the database

### No Logs Received
- Verify WebSocket connection is established
- Check that logs are being sent from workers
- Ensure task_id matches between client and logs
- Check Redis is running and accessible

### Logs Expired
- Logs have 1-hour TTL in Redis
- Retrieve historical logs before expiration
- For longer retention, implement persistent storage

## Performance Tips

1. **Batch Logs**: For high-frequency logs, consider batching multiple logs into a single request
2. **Async Sending**: Send logs asynchronously to avoid blocking task execution
3. **Error Handling**: Don't let log failures stop task execution
4. **Reconnection**: Implement exponential backoff for WebSocket reconnection
5. **Filtering**: Use appropriate log levels (debug for development, info/warning/error for production)

## Security Notes

- Currently no authentication required (implement in production)
- Validate all UUIDs before making requests
- Sanitize log messages to prevent XSS when displaying in UI
- Consider rate limiting to prevent log spam
- Monitor Redis memory usage with many active tasks
