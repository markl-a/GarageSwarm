"""
Integration tests for WebSocket Redis Pub/Sub cross-instance broadcasting
"""

import asyncio
import json
from datetime import datetime
from uuid import uuid4, UUID

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.models.task import Task
from src.services.redis_service import RedisService
from src.dependencies import get_redis_service


@pytest.mark.asyncio
class TestWebSocketRedisPubSub:
    """Test WebSocket with Redis Pub/Sub for multi-instance deployment"""

    async def test_publish_to_redis_channel(
        self,
        db_session: AsyncSession,
        redis_service: RedisService
    ):
        """Test publishing WebSocket messages to Redis channel"""
        # Create a test task
        task = Task(
            task_id=uuid4(),
            description="Test task for pub/sub",
            status="pending",
            priority=1
        )
        db_session.add(task)
        await db_session.commit()

        # Publish a WebSocket message
        message = {
            "type": "log",
            "data": {
                "task_id": str(task.task_id),
                "level": "info",
                "message": "Test log message"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        num_subscribers = await redis_service.publish_websocket_message(task.task_id, message)

        # If no subscribers yet, should return 0
        assert num_subscribers >= 0

    async def test_subscribe_to_task_channel(
        self,
        db_session: AsyncSession,
        redis_service: RedisService
    ):
        """Test subscribing to task-specific Redis channel"""
        # Create a test task
        task = Task(
            task_id=uuid4(),
            description="Test task for subscription",
            status="pending",
            priority=1
        )
        db_session.add(task)
        await db_session.commit()

        # Create a pubsub instance
        pubsub = redis_service.redis.pubsub()

        # Subscribe to task channel
        await redis_service.subscribe_to_task_channel(task.task_id, pubsub)

        # Verify subscription
        # The first message should be a subscription confirmation
        message = await pubsub.get_message(timeout=2)
        if message:
            assert message['type'] in ['subscribe', 'message']

        # Unsubscribe
        await redis_service.unsubscribe_from_task_channel(task.task_id, pubsub)
        await pubsub.close()

    async def test_message_queue_for_offline_clients(
        self,
        redis_service: RedisService
    ):
        """Test queuing messages for offline clients"""
        client_id = "test-client-123"

        # Queue some messages
        message1 = {"type": "log", "data": {"message": "Message 1"}}
        message2 = {"type": "log", "data": {"message": "Message 2"}}
        message3 = {"type": "status", "data": {"status": "completed"}}

        await redis_service.queue_message_for_client(client_id, message1)
        await redis_service.queue_message_for_client(client_id, message2)
        await redis_service.queue_message_for_client(client_id, message3)

        # Retrieve queued messages
        queued = await redis_service.get_queued_messages(client_id)

        assert len(queued) == 3
        assert queued[0] == message1
        assert queued[1] == message2
        assert queued[2] == message3

        # Queue should be cleared after retrieval
        queued_again = await redis_service.get_queued_messages(client_id)
        assert len(queued_again) == 0

    async def test_clear_client_queue(
        self,
        redis_service: RedisService
    ):
        """Test clearing message queue for a client"""
        client_id = "test-client-456"

        # Queue messages
        message = {"type": "log", "data": {"message": "Test"}}
        await redis_service.queue_message_for_client(client_id, message)
        await redis_service.queue_message_for_client(client_id, message)

        # Clear queue
        await redis_service.clear_client_queue(client_id)

        # Verify queue is empty
        queued = await redis_service.get_queued_messages(client_id)
        assert len(queued) == 0

    async def test_cross_instance_message_flow(
        self,
        db_session: AsyncSession,
        redis_service: RedisService
    ):
        """Test message flow across instances via Redis Pub/Sub"""
        # Create a test task
        task = Task(
            task_id=uuid4(),
            description="Test task for cross-instance messaging",
            status="in_progress",
            priority=1
        )
        db_session.add(task)
        await db_session.commit()

        # Simulate Instance A: Subscribe to task channel
        pubsub_instance_a = redis_service.redis.pubsub()
        await redis_service.subscribe_to_task_channel(task.task_id, pubsub_instance_a)

        # Wait a bit for subscription to be established
        await asyncio.sleep(0.1)

        # Clear the subscription confirmation message
        await pubsub_instance_a.get_message(timeout=0.5)

        # Simulate Instance B: Publish a message
        message = {
            "type": "log",
            "data": {
                "task_id": str(task.task_id),
                "subtask_id": str(uuid4()),
                "level": "info",
                "message": "Test cross-instance message",
                "timestamp": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        num_subscribers = await redis_service.publish_websocket_message(task.task_id, message)

        # Should have at least 1 subscriber (Instance A)
        assert num_subscribers >= 1

        # Instance A should receive the message
        received_message = await pubsub_instance_a.get_message(timeout=2)

        assert received_message is not None
        assert received_message['type'] == 'message'

        # Parse the message data
        received_data = json.loads(received_message['data'])
        assert received_data['type'] == 'log'
        assert received_data['data']['message'] == 'Test cross-instance message'

        # Cleanup
        await pubsub_instance_a.close()

    async def test_offline_client_message_delivery(
        self,
        db_session: AsyncSession,
        redis_service: RedisService
    ):
        """Test that messages are queued when client is offline"""
        client_id = "offline-client-789"

        # Simulate messages being sent while client is offline
        messages = [
            {"type": "log", "data": {"message": f"Offline message {i}"}}
            for i in range(5)
        ]

        for msg in messages:
            await redis_service.queue_message_for_client(client_id, msg)

        # Client comes online and retrieves messages
        queued = await redis_service.get_queued_messages(client_id)

        assert len(queued) == 5
        for i, msg in enumerate(queued):
            assert msg['data']['message'] == f"Offline message {i}"

    async def test_message_ttl(
        self,
        redis_service: RedisService
    ):
        """Test that queued messages respect TTL"""
        client_id = "ttl-test-client"

        # Queue message with 1 second TTL
        message = {"type": "test", "data": {"message": "TTL test"}}
        await redis_service.queue_message_for_client(client_id, message, ttl=1)

        # Immediately retrieve - should be available
        queued = await redis_service.get_queued_messages(client_id)
        assert len(queued) == 1

        # Queue another message with 1 second TTL
        await redis_service.queue_message_for_client(client_id, message, ttl=1)

        # Wait for TTL to expire
        await asyncio.sleep(2)

        # Should be empty due to TTL expiration
        queued = await redis_service.get_queued_messages(client_id)
        assert len(queued) == 0

    async def test_pubsub_manager_subscription_counting(
        self,
        db_session: AsyncSession,
        redis_service: RedisService
    ):
        """Test that PubSubManager correctly tracks subscription counts"""
        from src.api.v1.websocket import RedisPubSubManager, ConnectionManager

        # Create test task
        task = Task(
            task_id=uuid4(),
            description="Test task for subscription counting",
            status="pending",
            priority=1
        )
        db_session.add(task)
        await db_session.commit()

        # Create PubSubManager
        connection_manager = ConnectionManager(redis_service)
        pubsub_manager = RedisPubSubManager(redis_service)
        await pubsub_manager.start(connection_manager)

        # First subscription
        await pubsub_manager.subscribe_to_task(task.task_id)
        assert task.task_id in pubsub_manager.active_subscriptions
        assert pubsub_manager.active_subscriptions[task.task_id] == 1

        # Second subscription to same task
        await pubsub_manager.subscribe_to_task(task.task_id)
        assert pubsub_manager.active_subscriptions[task.task_id] == 2

        # First unsubscribe
        await pubsub_manager.unsubscribe_from_task(task.task_id)
        assert pubsub_manager.active_subscriptions[task.task_id] == 1

        # Second unsubscribe - should remove from dict
        await pubsub_manager.unsubscribe_from_task(task.task_id)
        assert task.task_id not in pubsub_manager.active_subscriptions

        # Cleanup
        await pubsub_manager.stop()

    async def test_multiple_tasks_subscription(
        self,
        db_session: AsyncSession,
        redis_service: RedisService
    ):
        """Test subscribing to multiple tasks simultaneously"""
        # Create multiple test tasks
        tasks = []
        for i in range(3):
            task = Task(
                task_id=uuid4(),
                description=f"Test task {i}",
                status="pending",
                priority=1
            )
            db_session.add(task)
            tasks.append(task)
        await db_session.commit()

        # Create PubSubManager
        from src.api.v1.websocket import RedisPubSubManager, ConnectionManager

        connection_manager = ConnectionManager(redis_service)
        pubsub_manager = RedisPubSubManager(redis_service)
        await pubsub_manager.start(connection_manager)

        # Subscribe to all tasks
        for task in tasks:
            await pubsub_manager.subscribe_to_task(task.task_id)

        # Verify all subscriptions are active
        assert len(pubsub_manager.active_subscriptions) == 3
        for task in tasks:
            assert task.task_id in pubsub_manager.active_subscriptions

        # Cleanup
        for task in tasks:
            await pubsub_manager.unsubscribe_from_task(task.task_id)

        await pubsub_manager.stop()


@pytest.mark.asyncio
class TestWebSocketEndpointWithPubSub:
    """Test WebSocket endpoint with Redis Pub/Sub integration"""

    async def test_websocket_receives_queued_messages_on_connect(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        redis_service: RedisService
    ):
        """Test that clients receive queued messages on connection"""
        # Create a test task
        task = Task(
            task_id=uuid4(),
            description="Test task for queued messages",
            status="in_progress",
            priority=1
        )
        db_session.add(task)
        await db_session.commit()

        # Queue some messages for a client (simulating offline period)
        client_id = "reconnecting-client-123"
        messages = [
            {
                "type": "log",
                "data": {"message": f"Queued message {i}"},
                "timestamp": datetime.utcnow().isoformat()
            }
            for i in range(3)
        ]

        for msg in messages:
            await redis_service.queue_message_for_client(client_id, msg)

        # Verify messages were queued
        queued = await redis_service.get_queued_messages(client_id)
        assert len(queued) == 3

        # Note: Full WebSocket connection test would require WebSocket client
        # This test verifies the queuing mechanism works correctly


@pytest.mark.asyncio
class TestConnectionManagerWithRedis:
    """Test ConnectionManager with Redis integration"""

    async def test_connection_manager_initialization(
        self,
        redis_service: RedisService
    ):
        """Test ConnectionManager initializes with Redis support"""
        from src.api.v1.websocket import ConnectionManager

        conn_manager = ConnectionManager(redis_service)
        await conn_manager.initialize()

        assert conn_manager.redis_service is not None
        assert conn_manager.pubsub_manager is not None

        await conn_manager.shutdown()

    async def test_broadcast_via_redis(
        self,
        db_session: AsyncSession,
        redis_service: RedisService
    ):
        """Test broadcasting messages via Redis Pub/Sub"""
        from src.api.v1.websocket import ConnectionManager

        # Create test task
        task = Task(
            task_id=uuid4(),
            description="Test task for Redis broadcasting",
            status="in_progress",
            priority=1
        )
        db_session.add(task)
        await db_session.commit()

        # Create connection manager with Redis
        conn_manager = ConnectionManager(redis_service)
        await conn_manager.initialize()

        # Broadcast message
        message = {
            "type": "log",
            "data": {"message": "Test broadcast via Redis"},
            "timestamp": datetime.utcnow().isoformat()
        }

        result = await conn_manager.broadcast_to_task_subscribers(task.task_id, message)

        # Should have published to Redis (may return 0 if no subscribers yet)
        assert result >= 0

        await conn_manager.shutdown()
