# API Reference

Complete API documentation for the Multi-Agent on the Web platform.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Workers API](#workers-api)
- [Tasks API](#tasks-api)
- [Subtasks API](#subtasks-api)
- [Checkpoints API](#checkpoints-api)
- [Evaluations API](#evaluations-api)
- [WebSocket API](#websocket-api)
- [Health API](#health-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## Overview

The Multi-Agent on the Web API is a RESTful API built with FastAPI. It provides endpoints for managing distributed workers, orchestrating tasks, and monitoring execution.

### API Version

Current version: **v1**

### Response Format

All responses are in JSON format with the following structure:

**Success Response:**
```json
{
  "data": { ... },
  "status": "success"
}
```

**Error Response:**
```json
{
  "detail": "Error message",
  "status": "error"
}
```

## Authentication

The API uses JWT-based authentication for most endpoints.

### Authentication Endpoints

**Register**: `POST /api/v1/auth/register`
**Login**: `POST /api/v1/auth/login`
**Logout**: `POST /api/v1/auth/logout`
**Refresh Token**: `POST /api/v1/auth/refresh`

### Using Authentication

**Header Format:**
```
Authorization: Bearer <jwt_token>
```

**Development Mode**: Health endpoints do not require authentication
**Production Mode**: All endpoints except `/health` and `/auth/*` require authentication

## Base URL

**Development:**
```
http://localhost:8002/api/v1
```

**Production:**
```
https://your-domain.com/api/v1
```

## Workers API

Endpoints for managing worker agents.

### Register Worker

Register a new worker agent or update an existing one (idempotent).

**Endpoint:** `POST /workers/register`

**Request Body:**
```json
{
  "machine_id": "unique-machine-identifier",
  "machine_name": "Development Machine",
  "system_info": {
    "os": "Linux",
    "os_version": "Ubuntu 22.04",
    "cpu_count": 8,
    "cpu_model": "Intel Core i7",
    "total_memory_gb": 16,
    "total_disk_gb": 512,
    "python_version": "3.11.0",
    "hostname": "dev-machine"
  },
  "tools": ["claude_code", "gemini_cli", "ollama"]
}
```

**Response:** `200 OK`
```json
{
  "status": "registered",
  "worker_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Worker registered successfully"
}
```

**Status Values:**
- `registered`: New worker registered
- `updated`: Existing worker updated

---

### Send Heartbeat

Update worker status and resource usage.

**Endpoint:** `POST /workers/{worker_id}/heartbeat`

**Path Parameters:**
- `worker_id` (UUID): Worker identifier

**Request Body:**
```json
{
  "status": "online",
  "resources": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "disk_percent": 35.5,
    "network_io": {
      "bytes_sent": 1048576,
      "bytes_recv": 2097152
    }
  },
  "current_task": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Status Values:**
- `online`: Available for tasks
- `busy`: Executing tasks
- `idle`: Online but no active tasks
- `offline`: Disconnected

**Response:** `200 OK`
```json
{
  "acknowledged": true,
  "message": "Heartbeat received"
}
```

**Notes:**
- Workers should send heartbeat every 30 seconds
- Workers without heartbeat for 90+ seconds are marked offline

---

### List Workers

Get list of all registered workers.

**Endpoint:** `GET /workers`

**Query Parameters:**
- `status` (optional): Filter by status (online, offline, busy, idle)
- `limit` (optional, default=50): Maximum results (1-100)
- `offset` (optional, default=0): Pagination offset

**Example Request:**
```
GET /workers?status=online&limit=10&offset=0
```

**Response:** `200 OK`
```json
{
  "workers": [
    {
      "worker_id": "550e8400-e29b-41d4-a716-446655440000",
      "machine_id": "machine-001",
      "machine_name": "Development Machine",
      "status": "online",
      "tools": ["claude_code", "gemini_cli"],
      "current_task": null,
      "resources": {
        "cpu_percent": 45.2,
        "memory_percent": 62.8,
        "disk_percent": 35.5
      },
      "registered_at": "2025-12-08T10:00:00Z",
      "last_heartbeat": "2025-12-08T12:30:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

---

### Get Worker Details

Get detailed information about a specific worker.

**Endpoint:** `GET /workers/{worker_id}`

**Path Parameters:**
- `worker_id` (UUID): Worker identifier

**Response:** `200 OK`
```json
{
  "worker_id": "550e8400-e29b-41d4-a716-446655440000",
  "machine_id": "machine-001",
  "machine_name": "Development Machine",
  "status": "online",
  "tools": ["claude_code", "gemini_cli"],
  "system_info": {
    "os": "Linux",
    "os_version": "Ubuntu 22.04",
    "cpu_count": 8,
    "cpu_model": "Intel Core i7",
    "total_memory_gb": 16,
    "total_disk_gb": 512,
    "python_version": "3.11.0",
    "hostname": "dev-machine"
  },
  "resources": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "disk_percent": 35.5
  },
  "current_task": null,
  "registered_at": "2025-12-08T10:00:00Z",
  "last_heartbeat": "2025-12-08T12:30:00Z"
}
```

---

### Unregister Worker

Mark a worker as offline (graceful shutdown).

**Endpoint:** `POST /workers/{worker_id}/unregister`

**Path Parameters:**
- `worker_id` (UUID): Worker identifier

**Response:** `200 OK`
```json
{
  "status": "unregistered",
  "worker_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Tasks API

Endpoints for task management.

### Create Task

Submit a new task for processing.

**Endpoint:** `POST /tasks`

**Request Body:**
```json
{
  "description": "# Add User Authentication\n\nImplement JWT-based authentication system",
  "task_type": "develop_feature",
  "requirements": {
    "tech_stack": ["Python", "FastAPI", "JWT"],
    "must_have": ["Login", "Logout", "Token refresh"],
    "nice_to_have": ["Remember me", "2FA"]
  },
  "checkpoint_frequency": "medium",
  "privacy_level": "normal",
  "tool_preferences": ["claude_code", "gemini_cli"]
}
```

**Field Descriptions:**
- `description` (required, 10-10000 chars): Task description (Markdown supported)
- `task_type` (optional, default="develop_feature"): Task type
- `requirements` (optional): Additional requirements as JSON object
- `checkpoint_frequency` (optional, default="medium"): low, medium, or high
- `privacy_level` (optional, default="normal"): normal or sensitive
- `tool_preferences` (optional): Preferred AI tools

**Task Types:**
- `develop_feature`: Develop new features
- `bug_fix`: Fix bugs
- `refactor`: Refactor code
- `code_review`: Review code
- `documentation`: Write documentation
- `testing`: Create tests

**Response:** `201 Created`
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "pending",
  "message": "Task created successfully"
}
```

---

### List Tasks

Get list of all tasks.

**Endpoint:** `GET /tasks`

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional, default=50): Maximum results (1-100)
- `offset` (optional, default=0): Pagination offset

**Task Status Values:**
- `pending`: Waiting for decomposition
- `decomposing`: Being broken into subtasks
- `ready`: Ready for execution
- `in_progress`: Currently executing
- `completed`: Successfully completed
- `failed`: Failed after retries
- `cancelled`: Cancelled by user

**Example Request:**
```
GET /tasks?status=in_progress&limit=20
```

**Response:** `200 OK`
```json
{
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440001",
      "description": "Add User Authentication...",
      "status": "in_progress",
      "progress": 65,
      "created_at": "2025-12-08T10:00:00Z",
      "updated_at": "2025-12-08T12:30:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### Get Task Details

Get detailed information about a specific task.

**Endpoint:** `GET /tasks/{task_id}`

**Path Parameters:**
- `task_id` (UUID): Task identifier

**Response:** `200 OK`
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "description": "# Add User Authentication\n\nImplement JWT-based authentication",
  "status": "in_progress",
  "progress": 65,
  "checkpoint_frequency": "medium",
  "privacy_level": "normal",
  "tool_preferences": ["claude_code", "gemini_cli"],
  "task_metadata": {
    "total_subtasks": 4,
    "completed_subtasks": 2,
    "failed_subtasks": 0
  },
  "subtasks": [
    {
      "subtask_id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "Code Generation",
      "status": "completed",
      "progress": 100,
      "assigned_worker": "550e8400-e29b-41d4-a716-446655440000",
      "assigned_tool": "claude_code",
      "evaluation": {
        "code_quality": 8.5,
        "completeness": 9.0,
        "security": 8.0,
        "architecture_alignment": 8.5,
        "testability": 7.5,
        "overall_score": 8.3
      }
    }
  ],
  "created_at": "2025-12-08T10:00:00Z",
  "updated_at": "2025-12-08T12:30:00Z",
  "started_at": "2025-12-08T10:05:00Z",
  "completed_at": null
}
```

---

### Get Task Progress

Get real-time task progress from Redis cache.

**Endpoint:** `GET /tasks/{task_id}/progress`

**Path Parameters:**
- `task_id` (UUID): Task identifier

**Response:** `200 OK`
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "in_progress",
  "progress": 65
}
```

**Note:** This endpoint is optimized for frequent polling.

---

### Cancel Task

Cancel a pending or in-progress task.

**Endpoint:** `POST /tasks/{task_id}/cancel`

**Path Parameters:**
- `task_id` (UUID): Task identifier

**Response:** `200 OK`
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "cancelled",
  "message": "Task cancelled successfully"
}
```

**Error Response:** `400 Bad Request`
```json
{
  "detail": "Cannot cancel task with status: completed"
}
```

---

### Decompose Task

Decompose a task into subtasks.

**Endpoint:** `POST /tasks/{task_id}/decompose`

**Path Parameters:**
- `task_id` (UUID): Task identifier

**Response:** `200 OK`
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "subtask_count": 4,
  "subtasks": [
    {
      "subtask_id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "Code Generation",
      "description": "Generate authentication code",
      "status": "pending",
      "recommended_tool": "claude_code",
      "complexity": "medium",
      "priority": 1,
      "dependencies": []
    }
  ],
  "message": "Task decomposed into 4 subtasks"
}
```

---

### Get Ready Subtasks

Get subtasks ready for execution (all dependencies satisfied).

**Endpoint:** `GET /tasks/{task_id}/ready-subtasks`

**Path Parameters:**
- `task_id` (UUID): Task identifier

**Response:** `200 OK`
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "ready_subtasks": [
    {
      "subtask_id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "Code Generation",
      "status": "pending",
      "dependencies": []
    }
  ],
  "total_ready": 1
}
```

## Subtasks API

Endpoints for subtask management.

### Get Subtask Details

Get detailed information about a specific subtask.

**Endpoint:** `GET /subtasks/{subtask_id}`

**Path Parameters:**
- `subtask_id` (UUID): Subtask identifier

**Response:** `200 OK`
```json
{
  "subtask_id": "550e8400-e29b-41d4-a716-446655440010",
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Code Generation",
  "description": "Generate authentication code with JWT",
  "status": "completed",
  "progress": 100,
  "recommended_tool": "claude_code",
  "assigned_worker": "550e8400-e29b-41d4-a716-446655440000",
  "assigned_tool": "claude_code",
  "complexity": "medium",
  "priority": 1,
  "dependencies": [],
  "output": {
    "files_created": ["auth.py", "token.py"],
    "files_modified": ["main.py"],
    "summary": "Implemented JWT authentication"
  },
  "error": null,
  "created_at": "2025-12-08T10:05:00Z",
  "started_at": "2025-12-08T10:10:00Z",
  "completed_at": "2025-12-08T11:00:00Z"
}
```

---

### Submit Subtask Result

Submit the result of a completed subtask (called by worker agents).

**Endpoint:** `POST /subtasks/{subtask_id}/result`

**Path Parameters:**
- `subtask_id` (UUID): Subtask identifier

**Request Body:**
```json
{
  "status": "completed",
  "output": {
    "files_created": ["auth.py", "token.py"],
    "files_modified": ["main.py"],
    "summary": "Implemented JWT authentication with login/logout endpoints"
  },
  "error": null,
  "metrics": {
    "execution_time_seconds": 180,
    "lines_of_code": 250,
    "test_coverage": 85
  }
}
```

**Response:** `200 OK`
```json
{
  "message": "Subtask result recorded successfully",
  "evaluation_triggered": true,
  "next_action": "evaluation"
}
```

---

### Allocate Subtask

Allocate a subtask to a worker (internal use).

**Endpoint:** `POST /subtasks/{subtask_id}/allocate`

**Request Body:**
```json
{
  "worker_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool": "claude_code"
}
```

**Response:** `200 OK`
```json
{
  "subtask_id": "550e8400-e29b-41d4-a716-446655440010",
  "worker_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool": "claude_code",
  "allocated_at": "2025-12-08T10:10:00Z"
}
```

## Checkpoints API

Endpoints for human review checkpoints.

### List Task Checkpoints

Get all checkpoints for a task.

**Endpoint:** `GET /tasks/{task_id}/checkpoints`

**Path Parameters:**
- `task_id` (UUID): Task identifier

**Response:** `200 OK`
```json
{
  "checkpoints": [
    {
      "checkpoint_id": "550e8400-e29b-41d4-a716-446655440020",
      "task_id": "550e8400-e29b-41d4-a716-446655440001",
      "status": "pending_review",
      "subtasks_completed": [
        "550e8400-e29b-41d4-a716-446655440010",
        "550e8400-e29b-41d4-a716-446655440011"
      ],
      "user_decision": null,
      "decision_notes": null,
      "triggered_at": "2025-12-08T11:00:00Z",
      "reviewed_at": null
    }
  ],
  "total": 1
}
```

**Checkpoint Status:**
- `pending_review`: Waiting for human review
- `approved`: Accepted by reviewer
- `needs_correction`: Needs minor adjustments
- `rejected`: Rejected, requires major rework

---

### Get Checkpoint Details

Get detailed information about a checkpoint.

**Endpoint:** `GET /checkpoints/{checkpoint_id}`

**Path Parameters:**
- `checkpoint_id` (UUID): Checkpoint identifier

**Response:** `200 OK`
```json
{
  "checkpoint_id": "550e8400-e29b-41d4-a716-446655440020",
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "pending_review",
  "subtasks": [
    {
      "subtask_id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "Code Generation",
      "status": "completed",
      "output": { ... }
    }
  ],
  "evaluation_summary": {
    "average_score": 8.3,
    "min_score": 7.5,
    "max_score": 9.0,
    "dimensions": {
      "code_quality": 8.5,
      "completeness": 9.0,
      "security": 8.0
    }
  },
  "triggered_at": "2025-12-08T11:00:00Z"
}
```

---

### Submit Checkpoint Decision

Submit a review decision for a checkpoint.

**Endpoint:** `POST /tasks/{task_id}/checkpoint/{checkpoint_id}/decision`

**Path Parameters:**
- `task_id` (UUID): Task identifier
- `checkpoint_id` (UUID): Checkpoint identifier

**Request Body:**
```json
{
  "decision": "correct",
  "notes": "Good implementation, but add rate limiting",
  "specific_feedback": {
    "security": "Add rate limiting to login endpoint (max 5 attempts per minute)",
    "testing": "Need tests for token expiration edge cases",
    "documentation": "Add API endpoint documentation"
  }
}
```

**Decision Values:**
- `accept`: Approve and continue
- `correct`: Request minor corrections
- `reject`: Reject and reassign

**Response:** `200 OK`
```json
{
  "checkpoint_id": "550e8400-e29b-41d4-a716-446655440020",
  "status": "approved",
  "message": "Checkpoint decision recorded",
  "next_action": "continue_execution"
}
```

## Evaluations API

Endpoints for quality evaluation.

### Get Subtask Evaluation

Get evaluation scores for a completed subtask.

**Endpoint:** `GET /subtasks/{subtask_id}/evaluation`

**Path Parameters:**
- `subtask_id` (UUID): Subtask identifier

**Response:** `200 OK`
```json
{
  "subtask_id": "550e8400-e29b-41d4-a716-446655440010",
  "evaluation": {
    "code_quality": 8.5,
    "completeness": 9.0,
    "security": 8.0,
    "architecture_alignment": 8.5,
    "testability": 7.5,
    "overall_score": 8.3
  },
  "details": {
    "code_quality": {
      "score": 8.5,
      "issues": ["Consider extracting helper function"],
      "tools_used": ["pylint", "radon"]
    },
    "security": {
      "score": 8.0,
      "issues": ["Add rate limiting"],
      "tools_used": ["bandit"]
    }
  },
  "evaluated_at": "2025-12-08T11:05:00Z",
  "evaluator": "system"
}
```

## WebSocket API

Real-time updates via WebSocket.

### Connect to Task Log Stream

Subscribe to real-time task log messages.

**Endpoint:** `WS /ws/tasks/{task_id}/logs`

**Path Parameters:**
- `task_id` (UUID): Task identifier

**Authentication:** Query parameter `token` (for future implementation)

**Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8002/api/v1/ws/tasks/550e8400-e29b-41d4-a716-446655440001/logs');

ws.onopen = () => {
  console.log('Connected to task logs');

  // Subscribe to additional tasks
  ws.send(JSON.stringify({
    action: 'subscribe',
    task_id: '550e8400-e29b-41d4-a716-446655440002'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch(message.type) {
    case 'log':
      console.log(`[${message.data.level}] ${message.data.message}`);
      break;
    case 'subscribed':
      console.log('Subscribed to task:', message.data.task_id);
      break;
    case 'error':
      console.error('Error:', message.data.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from task logs');
};
```

**Message Types:**

**Log Message (Server → Client):**
```json
{
  "type": "log",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440001",
    "subtask_id": "550e8400-e29b-41d4-a716-446655440010",
    "level": "info",
    "message": "Generating authentication code...",
    "timestamp": "2025-12-08T12:00:00.123Z",
    "worker_id": "worker-001",
    "metadata": {}
  }
}
```

**Subscription Confirmation (Server → Client):**
```json
{
  "type": "subscribed",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440001"
  }
}
```

**Subscribe Request (Client → Server):**
```json
{
  "action": "subscribe",
  "task_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Unsubscribe Request (Client → Server):**
```json
{
  "action": "unsubscribe",
  "task_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Ping/Pong (Heartbeat):**
```json
// Client → Server
{"action": "ping"}

// Server → Client
{"type": "pong"}
```

---

### Submit Worker Log

Workers submit log messages during task execution.

**Endpoint:** `POST /subtasks/{subtask_id}/log`

**Path Parameters:**
- `subtask_id` (UUID): Subtask identifier

**Request Body:**
```json
{
  "level": "info",
  "message": "Processing task step 3/10",
  "metadata": {
    "step": 3,
    "total_steps": 10,
    "file": "auth.py"
  }
}
```

**Log Levels:**
- `debug`: Detailed debugging information
- `info`: General informational messages
- `warning`: Warning messages
- `error`: Error messages

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Log stored and broadcast successfully",
  "broadcasted": 2
}
```

---

### Get Task Logs

Retrieve historical logs for a task.

**Endpoint:** `GET /tasks/{task_id}/logs`

**Path Parameters:**
- `task_id` (UUID): Task identifier

**Query Parameters:**
- `limit` (optional, default=100, max=1000): Maximum number of logs to return

**Response:** `200 OK`
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "logs": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440001",
      "subtask_id": "550e8400-e29b-41d4-a716-446655440010",
      "level": "info",
      "message": "Task completed successfully",
      "timestamp": "2025-12-08T12:30:00.123Z",
      "worker_id": "worker-001",
      "metadata": {}
    }
  ],
  "count": 42
}
```

**Note:** Logs are stored in Redis with 1-hour TTL and ordered by timestamp (newest first).

## Health API

Endpoints for service health monitoring.

### Health Check

Check overall system health.

**Endpoint:** `GET /health`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

**Error Response:** `503 Service Unavailable`
```json
{
  "status": "unhealthy",
  "database": "connected",
  "redis": "disconnected"
}
```

---

### Database Health

Check database connectivity.

**Endpoint:** `GET /health/database`

**Response:** `200 OK`
```json
{
  "status": "connected",
  "database": "multi_agent_db",
  "version": "PostgreSQL 15.3"
}
```

---

### Redis Health

Check Redis connectivity.

**Endpoint:** `GET /health/redis`

**Response:** `200 OK`
```json
{
  "status": "connected",
  "redis_version": "7.0.5",
  "connected_clients": 5,
  "used_memory": "1.5M",
  "uptime_days": 3
}
```

---

### Detailed Health Check

Get comprehensive system health information.

**Endpoint:** `GET /health/detailed`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "app": {
    "name": "Multi-Agent Backend",
    "version": "1.0.0",
    "environment": "development",
    "debug_mode": true
  },
  "services": {
    "database": {
      "status": "connected",
      "name": "multi_agent_db",
      "version": "PostgreSQL 15.3"
    },
    "redis": {
      "status": "connected",
      "version": "7.0.5",
      "clients": 5,
      "memory": "1.5M",
      "uptime_days": 3
    }
  }
}
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong",
  "status": "error"
}
```

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "description"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Common Errors

**Worker Not Found:**
```json
{
  "detail": "Worker 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Task Not Found:**
```json
{
  "detail": "Task 550e8400-e29b-41d4-a716-446655440001 not found"
}
```

**Invalid Status Transition:**
```json
{
  "detail": "Cannot cancel task with status: completed"
}
```

## Rate Limiting

**Current Limits:**
- No rate limiting in development mode
- Production: 100 requests per minute per IP

**Rate Limit Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1701964800
```

**Rate Limit Exceeded Response:** `429 Too Many Requests`
```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

## API Versioning

The API uses URL-based versioning:

- Current: `/api/v1/...`
- Future: `/api/v2/...` (when available)

Breaking changes will be introduced in new versions while maintaining backward compatibility for existing versions.

## Interactive Documentation

Explore the API interactively:

- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

Both provide:
- Complete API documentation
- Request/response schemas
- Try-it-out functionality
- Code generation examples

## Code Examples

### Python (httpx)

```python
import httpx

# Create a task
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8002/api/v1/tasks",
        json={
            "description": "Add user authentication",
            "task_type": "develop_feature",
            "checkpoint_frequency": "medium"
        }
    )
    task = response.json()
    print(f"Task created: {task['task_id']}")
```

### JavaScript (fetch)

```javascript
// Create a task
const response = await fetch('http://localhost:8002/api/v1/tasks', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    description: 'Add user authentication',
    task_type: 'develop_feature',
    checkpoint_frequency: 'medium'
  })
});
const task = await response.json();
console.log(`Task created: ${task.task_id}`);
```

### cURL

```bash
# Create a task
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Add user authentication",
    "task_type": "develop_feature",
    "checkpoint_frequency": "medium"
  }'
```

## Support

For additional help:

- **Interactive Docs**: http://localhost:8002/docs
- **User Guide**: [user-guide.md](user-guide.md)
- **Architecture**: [architecture.md](architecture.md)
- **GitHub Issues**: Report bugs or request features
