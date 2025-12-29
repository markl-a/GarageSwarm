"""
Redis Service Tests

Test Redis connection, operations, and Pub/Sub functionality.
"""

import asyncio
import pytest
from uuid import uuid4

from src.redis_client import RedisClient
from src.services.redis_service import RedisService


@pytest.fixture
async def redis_client():
    """Fixture for Redis client"""
    client = RedisClient("redis://localhost:6379/1")  # Use DB 1 for tests
    await client.connect()
    yield client
    # Cleanup
    await client.client.flushdb()  # Clear test database
    await client.close()


@pytest.fixture
async def redis_service(redis_client):
    """Fixture for Redis service"""
    return RedisService(redis_client.client)


@pytest.mark.asyncio
async def test_redis_connection(redis_client):
    """Test Redis connection"""
    assert redis_client.is_connected()
    assert await redis_client.ping()


@pytest.mark.asyncio
async def test_worker_status(redis_service):
    """Test worker status operations"""
    worker_id = uuid4()

    # Set worker status
    await redis_service.set_worker_status(worker_id, "online")

    # Get worker status
    status = await redis_service.get_worker_status(worker_id)
    assert status == "online"

    # Check online workers
    online = await redis_service.get_online_workers()
    assert str(worker_id) in online

    # Set to offline
    await redis_service.set_worker_status(worker_id, "offline")
    online = await redis_service.get_online_workers()
    assert str(worker_id) not in online


@pytest.mark.asyncio
async def test_worker_current_task(redis_service):
    """Test worker current task tracking"""
    worker_id = uuid4()
    task_id = uuid4()

    # Set current task
    await redis_service.set_worker_current_task(worker_id, task_id)

    # Get current task
    current = await redis_service.get_worker_current_task(worker_id)
    assert current == str(task_id)

    # Clear current task
    await redis_service.clear_worker_current_task(worker_id)
    current = await redis_service.get_worker_current_task(worker_id)
    assert current is None


@pytest.mark.asyncio
async def test_worker_info_cache(redis_service):
    """Test worker info caching"""
    worker_id = uuid4()
    info = {
        "machine_name": "Test-Machine",
        "tools": '["claude_code", "gemini_cli"]',
        "cpu_percent": 45.2,
        "memory_percent": 62.8,
    }

    # Cache worker info
    await redis_service.cache_worker_info(worker_id, info)

    # Get worker info
    cached = await redis_service.get_worker_info(worker_id)
    assert cached is not None
    assert cached["machine_name"] == "Test-Machine"
    assert cached["cpu_percent"] == "45.2"


@pytest.mark.asyncio
async def test_task_status_and_progress(redis_service):
    """Test task status and progress tracking"""
    task_id = uuid4()

    # Set task status
    await redis_service.set_task_status(task_id, "in_progress")
    status = await redis_service.get_task_status(task_id)
    assert status == "in_progress"

    # Set task progress
    await redis_service.set_task_progress(task_id, 50)
    progress = await redis_service.get_task_progress(task_id)
    assert progress == 50

    # Increment progress
    new_progress = await redis_service.increment_task_progress(task_id)
    assert new_progress == 51


@pytest.mark.asyncio
async def test_task_metadata_cache(redis_service):
    """Test task metadata caching"""
    task_id = uuid4()
    metadata = {
        "description": "Build authentication system",
        "user_id": str(uuid4()),
        "checkpoint_frequency": "medium",
    }

    # Cache metadata
    await redis_service.cache_task_metadata(task_id, metadata)

    # Get metadata
    cached = await redis_service.get_task_metadata(task_id)
    assert cached is not None
    assert cached["description"] == "Build authentication system"


@pytest.mark.asyncio
async def test_task_queue(redis_service):
    """Test task queue operations (FIFO)"""
    subtask_ids = [uuid4() for _ in range(5)]

    # Push subtasks to queue
    for subtask_id in subtask_ids:
        await redis_service.push_to_queue(subtask_id)

    # Check queue length
    length = await redis_service.get_queue_length()
    assert length == 5

    # Peek at first subtask
    first = await redis_service.peek_queue()
    assert first == str(subtask_ids[0])

    # Pop subtasks (FIFO)
    popped = []
    for _ in range(5):
        subtask = await redis_service.pop_from_queue()
        popped.append(subtask)

    # Verify FIFO order
    assert popped == [str(sid) for sid in subtask_ids]

    # Queue should be empty
    assert await redis_service.get_queue_length() == 0


@pytest.mark.asyncio
async def test_in_progress_tracking(redis_service):
    """Test in-progress subtask tracking"""
    subtask_id = uuid4()

    # Mark as in-progress
    await redis_service.mark_in_progress(subtask_id)

    # Check count
    count = await redis_service.get_in_progress_count()
    assert count == 1

    # Remove from in-progress
    await redis_service.remove_from_in_progress(subtask_id)
    count = await redis_service.get_in_progress_count()
    assert count == 0


@pytest.mark.asyncio
async def test_websocket_connections(redis_service):
    """Test WebSocket connection management"""
    client_id = "client-abc-123"

    # Add connection
    await redis_service.add_websocket_connection(client_id)

    # Check active connections
    connections = await redis_service.get_active_connections()
    assert client_id in connections

    # Remove connection
    await redis_service.remove_websocket_connection(client_id)
    connections = await redis_service.get_active_connections()
    assert client_id not in connections


@pytest.mark.asyncio
async def test_task_subscriptions(redis_service):
    """Test WebSocket task subscription tracking"""
    client_id = "client-abc"
    task_id = uuid4()

    # Subscribe to task
    await redis_service.subscribe_to_task(client_id, task_id)

    # Get task subscribers
    subscribers = await redis_service.get_task_subscribers(task_id)
    assert client_id in subscribers

    # Unsubscribe from task
    await redis_service.unsubscribe_from_task(client_id, task_id)
    subscribers = await redis_service.get_task_subscribers(task_id)
    assert client_id not in subscribers


@pytest.mark.asyncio
async def test_pubsub_events(redis_service):
    """Test Pub/Sub event broadcasting"""
    channel = "test_channel"
    message = {"type": "test_event", "data": "Hello, World!"}

    # Publish event
    num_subscribers = await redis_service.publish_event(channel, message)
    # No subscribers yet, should return 0
    assert num_subscribers == 0


@pytest.mark.asyncio
async def test_distributed_lock(redis_service):
    """Test distributed locking"""
    resource = "task-allocation"
    value = "worker-abc"

    # Acquire lock
    acquired = await redis_service.acquire_lock(resource, value, ttl=5)
    assert acquired is True

    # Try to acquire again (should fail)
    acquired_again = await redis_service.acquire_lock(resource, "worker-def", ttl=5)
    assert acquired_again is False

    # Release lock
    await redis_service.release_lock(resource)

    # Now should be able to acquire
    acquired_after = await redis_service.acquire_lock(resource, "worker-xyz", ttl=5)
    assert acquired_after is True


@pytest.mark.asyncio
async def test_rate_limiting(redis_service):
    """Test rate limiting"""
    user_id = uuid4()
    endpoint = "/api/tasks"
    limit = 5

    # Make requests up to limit
    for i in range(limit):
        within_limit = await redis_service.check_rate_limit(
            user_id, endpoint, limit=limit, window=60
        )
        assert within_limit is True

    # Next request should exceed limit
    exceeded = await redis_service.check_rate_limit(
        user_id, endpoint, limit=limit, window=60
    )
    assert exceeded is False

    # Check remaining
    remaining = await redis_service.get_rate_limit_remaining(user_id, endpoint, limit)
    assert remaining == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
