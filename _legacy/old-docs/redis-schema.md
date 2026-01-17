# Redis Data Structures - Multi-Agent on the Web

This document describes the Redis key schema and data structures used for fast in-memory operations.

## Table of Contents

1. [Overview](#overview)
2. [Key Naming Convention](#key-naming-convention)
3. [Worker Status Management](#worker-status-management)
4. [Task Status & Progress](#task-status--progress)
5. [Task Queue](#task-queue)
6. [WebSocket Connection Management](#websocket-connection-management)
7. [Pub/Sub Channels](#pubsub-channels)
8. [Cache & Session Storage](#cache--session-storage)
9. [TTL and Expiration](#ttl-and-expiration)

---

## Overview

**Purpose:** Redis serves as:
- ✅ Fast in-memory cache for worker and task status
- ✅ Task queue for pending subtasks (FIFO)
- ✅ Pub/Sub messaging for real-time updates
- ✅ WebSocket session management
- ✅ Distributed locking for concurrent operations

**Redis Version:** 7.0+

**Data Types Used:**
- **String** - Simple key-value pairs (status, progress)
- **Set** - Unique collections (online workers, WebSocket clients)
- **List** - Ordered collections (task queue - FIFO)
- **Hash** - Object storage (worker info, task cache)
- **Sorted Set** - Ranked collections (priority queues)
- **Pub/Sub** - Event broadcasting

---

## Key Naming Convention

**Format:** `namespace:entity_type:[entity_id]:attribute`

**Examples:**
- `workers:abc-123:status` - Worker status
- `tasks:def-456:progress` - Task progress
- `task_queue:pending` - Pending task queue
- `websocket:connections` - Active WebSocket connections

**Naming Rules:**
1. Use lowercase with underscores for multi-word names
2. Use colons (`:`) as namespace separators
3. Always include entity type (workers, tasks, websocket)
4. Include entity ID for specific entities
5. End with attribute name for specific properties

---

## Worker Status Management

### 1. Worker Status (String with TTL)

**Key:** `workers:{worker_id}:status`
**Type:** String
**Values:** `"online"` | `"offline"` | `"busy"`
**TTL:** 120 seconds (2 minutes)

```redis
# Set worker status
SETEX workers:abc-123:status 120 "online"

# Get worker status
GET workers:abc-123:status
# Returns: "online"

# Worker goes offline if no heartbeat for 120s (TTL expires)
```

**Usage:**
- Set by Worker Agent on heartbeat (every 30s)
- TTL auto-expires if worker crashes or network fails
- Backend checks before assigning tasks

### 2. Online Workers Set (Set)

**Key:** `workers:online`
**Type:** Set
**Members:** Worker IDs (UUIDs as strings)

```redis
# Add worker to online set
SADD workers:online "abc-123"

# Remove worker from online set
SREM workers:online "abc-123"

# Get all online workers
SMEMBERS workers:online
# Returns: ["abc-123", "def-456", "ghi-789"]

# Count online workers
SCARD workers:online
# Returns: 3
```

**Usage:**
- Fast lookup of available workers
- Used for task allocation algorithm
- Automatically cleaned when worker status expires

### 3. Worker Current Task (String)

**Key:** `workers:{worker_id}:current_task`
**Type:** String
**Value:** Task ID (UUID)
**TTL:** 600 seconds (10 minutes)

```redis
# Assign task to worker
SETEX workers:abc-123:current_task 600 "task-uuid-123"

# Get worker's current task
GET workers:abc-123:current_task
# Returns: "task-uuid-123"

# Clear on task completion
DEL workers:abc-123:current_task
```

### 4. Worker Info Cache (Hash)

**Key:** `workers:{worker_id}:info`
**Type:** Hash
**Fields:** `machine_name`, `tools`, `cpu_percent`, `memory_percent`, `disk_percent`
**TTL:** 120 seconds

```redis
# Cache worker info
HSET workers:abc-123:info machine_name "Dev-Machine-1"
HSET workers:abc-123:info tools '["claude_code","gemini_cli"]'
HSET workers:abc-123:info cpu_percent "45.2"
HSET workers:abc-123:info memory_percent "62.8"
HSET workers:abc-123:info disk_percent "78.5"
EXPIRE workers:abc-123:info 120

# Get all worker info
HGETALL workers:abc-123:info
# Returns: {machine_name: "Dev-Machine-1", tools: '["claude_code","gemini_cli"]', ...}

# Get specific field
HGET workers:abc-123:info cpu_percent
# Returns: "45.2"
```

**Usage:**
- Cache frequently accessed worker data
- Reduce database queries for task allocation
- Updated on every heartbeat

---

## Task Status & Progress

### 1. Task Status (String)

**Key:** `tasks:{task_id}:status`
**Type:** String
**Values:** `"pending"` | `"initializing"` | `"in_progress"` | `"checkpoint"` | `"completed"` | `"failed"`
**TTL:** None (persists until task completion)

```redis
# Set task status
SET tasks:task-123:status "in_progress"

# Get task status
GET tasks:task-123:status
# Returns: "in_progress"

# Delete on task completion
DEL tasks:task-123:status
```

### 2. Task Progress (String)

**Key:** `tasks:{task_id}:progress`
**Type:** String (Integer as string)
**Value:** 0-100
**TTL:** None

```redis
# Set task progress
SET tasks:task-123:progress "45"

# Get task progress
GET tasks:task-123:progress
# Returns: "45"

# Increment progress atomically
INCR tasks:task-123:progress
```

### 3. Task Metadata Cache (Hash)

**Key:** `tasks:{task_id}:cache`
**Type:** Hash
**Fields:** `description`, `user_id`, `checkpoint_frequency`, `created_at`
**TTL:** 3600 seconds (1 hour)

```redis
# Cache task metadata
HMSET tasks:task-123:cache \
  description "Build authentication system" \
  user_id "user-abc" \
  checkpoint_frequency "medium" \
  created_at "2025-11-12T09:00:00Z"

EXPIRE tasks:task-123:cache 3600

# Get all task metadata
HGETALL tasks:task-123:cache
```

---

## Task Queue

### 1. Pending Subtasks Queue (List)

**Key:** `task_queue:pending`
**Type:** List (FIFO queue)
**Members:** Subtask IDs (UUIDs)

```redis
# Add subtask to queue (right push)
RPUSH task_queue:pending "subtask-123"

# Worker pulls subtask from queue (left pop)
LPOP task_queue:pending
# Returns: "subtask-123"

# Check queue length
LLEN task_queue:pending
# Returns: 5

# Peek at next subtask without removing
LINDEX task_queue:pending 0
# Returns: "subtask-456"
```

**Usage:**
- FIFO queue for subtask assignment
- Worker Agent pulls tasks from left
- Backend pushes tasks to right

### 2. In-Progress Subtasks Set (Set)

**Key:** `task_queue:in_progress`
**Type:** Set
**Members:** Subtask IDs currently being executed

```redis
# Mark subtask as in-progress
SADD task_queue:in_progress "subtask-123"

# Check if subtask is in-progress
SISMEMBER task_queue:in_progress "subtask-123"
# Returns: 1 (true)

# Remove on completion
SREM task_queue:in_progress "subtask-123"

# Get all in-progress subtasks
SMEMBERS task_queue:in_progress
```

### 3. Priority Queue (Sorted Set)

**Key:** `task_queue:priority`
**Type:** Sorted Set
**Members:** Subtask IDs
**Scores:** Priority scores (higher = more urgent)

```redis
# Add subtask with priority
ZADD task_queue:priority 100 "subtask-high-priority"
ZADD task_queue:priority 50 "subtask-medium-priority"
ZADD task_queue:priority 10 "subtask-low-priority"

# Get highest priority subtask
ZPOPMAX task_queue:priority
# Returns: ["subtask-high-priority", 100]

# Get subtasks by priority range
ZRANGEBYSCORE task_queue:priority 50 100
# Returns: ["subtask-medium-priority", "subtask-high-priority"]
```

**Usage:**
- For future implementation of priority-based task scheduling
- High-priority tasks pulled first
- Complexity-based prioritization

---

## WebSocket Connection Management

### 1. Active Connections Set (Set)

**Key:** `websocket:connections`
**Type:** Set
**Members:** Client IDs (connection IDs)

```redis
# Add new WebSocket connection
SADD websocket:connections "client-abc-123"

# Remove disconnected client
SREM websocket:connections "client-abc-123"

# Get all connected clients
SMEMBERS websocket:connections
# Returns: ["client-abc-123", "client-def-456"]

# Count active connections
SCARD websocket:connections
# Returns: 2
```

### 2. Client Subscriptions (Set)

**Key:** `websocket:subscriptions:{client_id}`
**Type:** Set
**Members:** Task IDs the client is subscribed to

```redis
# Client subscribes to task updates
SADD websocket:subscriptions:client-abc "task-123"
SADD websocket:subscriptions:client-abc "task-456"

# Get client's subscriptions
SMEMBERS websocket:subscriptions:client-abc
# Returns: ["task-123", "task-456"]

# Unsubscribe from task
SREM websocket:subscriptions:client-abc "task-123"

# Remove all subscriptions on disconnect
DEL websocket:subscriptions:client-abc
```

### 3. Task Subscribers (Set)

**Key:** `websocket:task_subscribers:{task_id}`
**Type:** Set
**Members:** Client IDs subscribed to this task

```redis
# Track which clients are watching this task
SADD websocket:task_subscribers:task-123 "client-abc"
SADD websocket:task_subscribers:task-123 "client-def"

# Get all clients watching a task
SMEMBERS websocket:task_subscribers:task-123
# Returns: ["client-abc", "client-def"]

# Remove client from task subscribers
SREM websocket:task_subscribers:task-123 "client-abc"
```

**Usage:**
- Efficient event broadcasting (only to interested clients)
- Cleanup on client disconnect
- Used by WebSocket manager to route events

---

## Pub/Sub Channels

### 1. Task Update Events

**Channel:** `events:task_update`
**Message Format:** JSON

```json
{
  "type": "task_update",
  "task_id": "task-123",
  "status": "in_progress",
  "progress": 45,
  "timestamp": "2025-11-12T10:30:00Z"
}
```

```redis
# Publish task update
PUBLISH events:task_update '{"type":"task_update","task_id":"task-123","status":"in_progress","progress":45}'

# Subscribe to task updates
SUBSCRIBE events:task_update
```

### 2. Worker Update Events

**Channel:** `events:worker_update`
**Message Format:** JSON

```json
{
  "type": "worker_update",
  "worker_id": "worker-abc",
  "status": "online",
  "cpu_percent": 45.2,
  "memory_percent": 62.8,
  "timestamp": "2025-11-12T10:30:00Z"
}
```

```redis
# Publish worker status change
PUBLISH events:worker_update '{"type":"worker_update","worker_id":"worker-abc","status":"online"}'

# Subscribe to worker updates
SUBSCRIBE events:worker_update
```

### 3. Subtask Completion Events

**Channel:** `events:subtask_complete`
**Message Format:** JSON

```json
{
  "type": "subtask_complete",
  "subtask_id": "subtask-123",
  "task_id": "task-123",
  "status": "completed",
  "evaluation_score": 8.5,
  "timestamp": "2025-11-12T10:30:00Z"
}
```

### 4. Checkpoint Events

**Channel:** `events:checkpoint`
**Message Format:** JSON

```json
{
  "type": "checkpoint_triggered",
  "checkpoint_id": "checkpoint-123",
  "task_id": "task-123",
  "reason": "evaluation_threshold",
  "timestamp": "2025-11-12T10:30:00Z"
}
```

**Usage:**
- Real-time event broadcasting to WebSocket clients
- Loosely coupled event-driven architecture
- Multiple subscribers can listen to same channel

---

## Cache & Session Storage

### 1. User Session (Hash)

**Key:** `session:{session_id}`
**Type:** Hash
**TTL:** 86400 seconds (24 hours)

```redis
# Create user session
HMSET session:abc-123 \
  user_id "user-def" \
  username "john_doe" \
  created_at "2025-11-12T09:00:00Z"

EXPIRE session:abc-123 86400

# Get session data
HGETALL session:abc-123
```

### 2. API Rate Limiting (String)

**Key:** `ratelimit:{user_id}:{endpoint}`
**Type:** String (counter)
**TTL:** 60 seconds

```redis
# Increment request counter
INCR ratelimit:user-123:/api/tasks
EXPIRE ratelimit:user-123:/api/tasks 60

# Check rate limit
GET ratelimit:user-123:/api/tasks
# Returns: "5"

# Rate limit: 100 requests per minute
```

### 3. Distributed Lock (String)

**Key:** `lock:{resource_name}`
**Type:** String
**TTL:** 10 seconds

```redis
# Acquire lock (returns 1 if successful, 0 if already locked)
SET lock:task-allocation "worker-abc" NX EX 10

# Release lock
DEL lock:task-allocation
```

**Usage:**
- Prevent concurrent task allocation to same worker
- Ensure only one process handles checkpoint trigger
- Auto-release on timeout (deadlock prevention)

---

## TTL and Expiration

### Default TTL Values

| Key Type | TTL | Reason |
|----------|-----|--------|
| `workers:{worker_id}:status` | 120s | 2x heartbeat interval (60s) |
| `workers:{worker_id}:info` | 120s | Sync with status expiration |
| `workers:{worker_id}:current_task` | 600s | Max task execution time |
| `tasks:{task_id}:cache` | 3600s | Reduce DB queries |
| `session:{session_id}` | 86400s | 24-hour session |
| `ratelimit:{user_id}:{endpoint}` | 60s | Per-minute rate limit |
| `lock:{resource}` | 10s | Prevent deadlocks |

### Cleanup Strategy

**Expired Keys:**
- Redis automatically removes expired keys (lazy deletion + periodic sampling)
- No manual cleanup needed for TTL-based keys

**Manual Cleanup:**
```python
# Clean up on task completion
await redis.delete(f"tasks:{task_id}:status")
await redis.delete(f"tasks:{task_id}:progress")
await redis.delete(f"tasks:{task_id}:cache")

# Clean up on worker disconnect
await redis.delete(f"workers:{worker_id}:status")
await redis.delete(f"workers:{worker_id}:current_task")
await redis.srem("workers:online", worker_id)
```

---

## Redis Configuration

### Connection String

```bash
# Development
REDIS_URL=redis://localhost:6379/0

# Production (with password)
REDIS_URL=redis://:password@redis-host:6379/0

# TLS (production)
REDIS_URL=rediss://:password@redis-host:6380/0
```

### Connection Pool Settings

```python
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=50,  # Maximum connections in pool
    decode_responses=True,  # Auto-decode bytes to strings
    socket_timeout=5,  # Socket timeout in seconds
    socket_connect_timeout=5,  # Connection timeout
    retry_on_timeout=True,  # Retry on timeout
)
```

### Performance Tuning

**Memory Management:**
```redis
# Set max memory (e.g., 2GB)
CONFIG SET maxmemory 2gb

# Eviction policy (LRU for cache data)
CONFIG SET maxmemory-policy allkeys-lru
```

**Persistence:**
```redis
# Disable persistence for pure cache (optional)
CONFIG SET save ""
CONFIG SET appendonly no
```

---

## Usage Examples

### Worker Heartbeat

```python
async def send_heartbeat(worker_id: UUID, status: str, resource_usage: dict):
    # Update status with TTL
    await redis.setex(f"workers:{worker_id}:status", 120, status)

    # Add to online set
    if status == "online":
        await redis.sadd("workers:online", str(worker_id))
    else:
        await redis.srem("workers:online", str(worker_id))

    # Cache resource info
    await redis.hset(f"workers:{worker_id}:info", mapping={
        "cpu_percent": resource_usage["cpu"],
        "memory_percent": resource_usage["memory"],
        "disk_percent": resource_usage["disk"]
    })
    await redis.expire(f"workers:{worker_id}:info", 120)
```

### Task Assignment

```python
async def assign_task_to_worker(worker_id: UUID, subtask_id: UUID):
    # Pop subtask from queue
    await redis.lrem("task_queue:pending", 1, str(subtask_id))

    # Mark as in-progress
    await redis.sadd("task_queue:in_progress", str(subtask_id))

    # Set worker's current task
    await redis.setex(f"workers:{worker_id}:current_task", 600, str(subtask_id))
```

### Real-time Progress Update

```python
async def update_task_progress(task_id: UUID, progress: int):
    # Update cache
    await redis.set(f"tasks:{task_id}:progress", progress)

    # Publish event
    event = {
        "type": "task_update",
        "task_id": str(task_id),
        "progress": progress,
        "timestamp": datetime.utcnow().isoformat()
    }
    await redis.publish("events:task_update", json.dumps(event))
```

---

## References

- Redis Documentation: https://redis.io/docs/
- Redis Pub/Sub: https://redis.io/docs/manual/pubsub/
- Redis Data Types: https://redis.io/docs/data-types/
- Architecture Document: `docs/architecture.md`
