# Performance Testing Suite

This directory contains performance tests for the Multi-Agent platform to ensure the system meets Non-Functional Requirements (NFR).

## Performance Requirements (NFR)

| Metric | Requirement |
|--------|-------------|
| Task Submission | < 2 seconds |
| WebSocket Latency | < 500ms |
| Worker Registration | < 5 seconds |
| Concurrent Workers | 10 workers online |
| Concurrent Tasks | 20 tasks parallel execution |
| WebSocket Connections | 50 concurrent connections |

## Test Structure

### 1. API Performance Tests (`test_api_performance.py`)

Tests individual API endpoint performance:

**Worker API Tests:**
- Worker registration response time
- Worker heartbeat response time
- Worker list API response time
- Worker get API response time

**Task API Tests:**
- Task submission response time (must meet < 2s requirement)
- Task query response time
- Task list API response time
- Task progress query response time (Redis-backed, should be < 200ms)
- Task decomposition performance

**Health API Tests:**
- Health check response time
- Health check consistency across multiple calls

### 2. Concurrent Workers Tests (`test_concurrent_workers.py`)

Tests system performance with multiple workers:

**Concurrent Registration:**
- 10 workers registering simultaneously (NFR requirement)
- 20 workers registering simultaneously (stress test)

**Concurrent Heartbeat:**
- 10 workers sending heartbeats simultaneously
- Sustained heartbeat load (10 workers × 5 heartbeats each)

**Worker Listing Under Load:**
- List workers with 10 registered
- List workers with 50 registered
- List workers with status filters

### 3. Concurrent Tasks Tests (`test_concurrent_tasks.py`)

Tests system performance with multiple tasks:

**Concurrent Submission:**
- 20 tasks submitted simultaneously (NFR requirement)
- 50 tasks submitted simultaneously (stress test)

**Concurrent Queries:**
- Querying 20 tasks simultaneously
- Concurrent progress queries (Redis-backed)

**Task Decomposition:**
- Concurrent task decomposition
- Sequential decomposition performance

**Task Listing Under Load:**
- List tasks with 20 created
- List tasks with 100 created
- Pagination performance
- Filter performance

**Mixed Workload:**
- Combined worker and task operations

### 4. Locust Load Testing (`locustfile.py`)

Locust-based load testing for realistic user scenarios:

**User Types:**
- `WorkerUser`: Simulates worker lifecycle (register → heartbeat → unregister)
- `TaskUser`: Simulates task lifecycle (create → query → decompose)
- `MixedUser`: Simulates mixed workload (lists + creates)

## Running Performance Tests

### Prerequisites

Ensure the application and dependencies are running:

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Apply database migrations
cd backend
alembic upgrade head
```

### Running Pytest Performance Tests

**Run all performance tests:**
```bash
pytest tests/performance/ -m performance -v
```

**Run specific test class:**
```bash
pytest tests/performance/test_api_performance.py::TestWorkerAPIPerformance -v
```

**Run with detailed output:**
```bash
pytest tests/performance/ -m performance -v -s
```

**Generate performance report:**
```bash
pytest tests/performance/ -m performance -v --tb=short > performance_report.txt
```

### Running Locust Load Tests

**1. Worker Load Test (10 workers):**
```bash
cd tests/performance
locust -f locustfile.py --host=http://localhost:8000 \
    --users=10 --spawn-rate=2 --run-time=60s \
    --only-summary WorkerUser
```

**2. Task Load Test (20 tasks):**
```bash
locust -f locustfile.py --host=http://localhost:8000 \
    --users=20 --spawn-rate=4 --run-time=60s \
    --only-summary TaskUser
```

**3. Mixed Load Test:**
```bash
locust -f locustfile.py --host=http://localhost:8000 \
    --users=30 --spawn-rate=5 --run-time=120s \
    --only-summary MixedUser
```

**4. Interactive Load Test (with Web UI):**
```bash
locust -f locustfile.py --host=http://localhost:8000
# Then open http://localhost:8089 in browser
```

## Performance Fixtures

The test suite includes several custom fixtures in `conftest.py`:

### Timing Fixtures

- `perf_timer`: Context manager for timing operations
- `perf_analyzer`: Collects and analyzes performance metrics
- `assert_performance`: Assert operation meets performance requirement

### Concurrency Fixtures

- `run_concurrent`: Run coroutines concurrently
- `run_concurrent_timed`: Run and time concurrent operations

### Data Factory Fixtures

- `sample_worker_data_factory`: Generate test worker data
- `sample_task_data_factory`: Generate test task data

### Performance Thresholds

- `performance_thresholds`: Provides NFR thresholds for assertions

## Understanding Test Results

### Pytest Output

Each test reports performance metrics:
```
=== Worker Registration Performance (10 runs) ===
Average: 450.25ms
P95: 520.50ms
P99: 580.75ms
```

**Key Metrics:**
- **Average**: Mean response time
- **P95**: 95th percentile (95% of requests faster than this)
- **P99**: 99th percentile (99% of requests faster than this)
- **Min/Max**: Fastest and slowest response times
- **Std Dev**: Standard deviation (consistency measure)

### Locust Output

Locust provides comprehensive load testing metrics:
```
Type     Name                              # reqs    # fails   Avg    Min    Max  Median  req/s
POST     /api/v1/workers/register            100         0   450    320    850     420   1.67
POST     /api/v1/workers/{id}/heartbeat      500         0   120     80    300     110   8.33
```

**Key Metrics:**
- **# reqs**: Total requests
- **# fails**: Failed requests
- **Avg/Median**: Response time statistics
- **req/s**: Requests per second (throughput)

## Performance Analysis

### Expected Performance

Based on NFR requirements:

| Operation | Target | Expected P95 |
|-----------|--------|--------------|
| Worker Registration | < 5s | < 4s |
| Task Submission | < 2s | < 1.5s |
| Worker Heartbeat | Fast | < 500ms |
| Task Query | Fast | < 1s |
| Progress Query (Redis) | Very Fast | < 200ms |
| Health Check | Very Fast | < 100ms |

### Performance Bottlenecks

Common bottlenecks to watch for:

1. **Database Queries**
   - Slow queries without proper indexes
   - N+1 query problems
   - Large result sets without pagination

2. **Redis Operations**
   - Connection pool exhaustion
   - Large payload serialization
   - Network latency

3. **API Layer**
   - Request/response serialization
   - Database connection acquisition
   - Transaction overhead

4. **Concurrency Issues**
   - Lock contention
   - Connection pool limits
   - Resource exhaustion

## Performance Optimization

### Database Optimizations

1. **Indexes** (already implemented):
   - `tasks.status` - for filtering tasks by status
   - `tasks.user_id` - for user's tasks
   - `tasks.created_at` - for sorting by date
   - `workers.status` - for filtering online workers
   - `workers.last_heartbeat` - for stale worker detection
   - `subtasks.task_id` - for task's subtasks
   - `subtasks.status` - for filtering subtasks

2. **Connection Pooling** (already configured):
   - Production pool: 20 connections, 40 max overflow
   - Development: NullPool (no pooling for testing)

3. **Query Optimizations**:
   - Use `select_in_loading` for relationships to avoid N+1
   - Add `limit`/`offset` to all list endpoints
   - Use `defer()` for large columns not always needed

### Redis Optimizations

1. **Connection Pool** (configured in `redis_client.py`):
   - Max 50 connections
   - Health check every 30s
   - Retry on timeout

2. **Caching Strategy**:
   - Cache frequently accessed data (worker status, task progress)
   - Set appropriate TTLs (Time To Live)
   - Use pipeline for batch operations

3. **Key Design**:
   - Use consistent key patterns
   - Set expiration on temporary data
   - Clean up stale keys

### API Optimizations

1. **Response Compression**:
   - Enable gzip compression for large responses
   - Reduce payload size by returning only needed fields

2. **Async Operations**:
   - All database queries use async/await
   - Non-blocking I/O operations

3. **Caching Headers**:
   - Set cache-control headers for static data
   - Use ETags for conditional requests

## Troubleshooting

### Tests Running Slowly

1. **Check Database Connection**:
   ```bash
   # Ensure PostgreSQL is running and accessible
   docker-compose ps postgres
   ```

2. **Check Redis Connection**:
   ```bash
   # Ensure Redis is running
   docker-compose ps redis
   ```

3. **Check System Resources**:
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network latency

### Tests Failing

1. **Connection Errors**:
   - Verify DATABASE_URL and REDIS_URL in environment
   - Check firewall rules
   - Verify service health

2. **Timeout Errors**:
   - Increase pytest timeout: `pytest --timeout=300`
   - Check for deadlocks in database
   - Review application logs

3. **Assertion Failures**:
   - Review performance metrics output
   - Check if NFR requirements are too strict
   - Investigate specific slow operations

## Continuous Performance Testing

### CI/CD Integration

Add performance tests to CI pipeline:

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Performance Tests
        run: |
          docker-compose up -d
          pytest tests/performance/ -m performance
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: performance_report.txt
```

### Performance Monitoring

1. **Track Metrics Over Time**:
   - Store test results in a database
   - Create dashboards with trends
   - Alert on performance regressions

2. **Benchmark Baselines**:
   - Establish baseline performance
   - Compare new code against baseline
   - Reject changes that degrade performance significantly

3. **Production Monitoring**:
   - Use APM tools (New Relic, DataDog)
   - Track real user metrics
   - Set up alerts for SLO violations

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Locust Documentation](https://docs.locust.io/)
- [SQLAlchemy Performance Tips](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [FastAPI Performance](https://fastapi.tiangolo.com/async/)
- [Redis Performance](https://redis.io/docs/management/optimization/)
