"""
Example: WebSocket with Redis Pub/Sub Cross-Instance Broadcasting

This example demonstrates:
1. Publishing messages to Redis Pub/Sub
2. Receiving messages across multiple instances
3. Message queuing for offline clients
"""

import asyncio
import json
from datetime import datetime
from uuid import uuid4, UUID

# Simulated imports - adjust paths as needed
from src.services.redis_service import RedisService
from src.redis_client import RedisClient


async def example_1_publish_message():
    """Example 1: Publish a WebSocket message to Redis"""
    print("\n=== Example 1: Publishing WebSocket Message ===\n")

    # Initialize Redis
    redis_client = RedisClient("redis://localhost:6379/0")
    await redis_client.connect()
    redis_service = RedisService(redis_client.client)

    # Create a test task ID
    task_id = uuid4()
    print(f"Task ID: {task_id}")

    # Create a WebSocket message
    message = {
        "type": "log",
        "data": {
            "task_id": str(task_id),
            "subtask_id": str(uuid4()),
            "level": "info",
            "message": "Processing request with Claude Code",
            "worker_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    # Publish to Redis
    num_subscribers = await redis_service.publish_websocket_message(task_id, message)
    print(f"Published to {num_subscribers} backend instance(s)")
    print(f"Message: {json.dumps(message, indent=2)}")

    await redis_client.close()


async def example_2_subscribe_and_receive():
    """Example 2: Subscribe to task channel and receive messages"""
    print("\n=== Example 2: Subscribing to Task Channel ===\n")

    # Initialize Redis
    redis_client = RedisClient("redis://localhost:6379/0")
    await redis_client.connect()
    redis_service = RedisService(redis_client.client)

    # Create a test task ID
    task_id = uuid4()
    print(f"Task ID: {task_id}")

    # Create PubSub instance
    pubsub = redis_service.redis.pubsub()

    # Subscribe to task channel
    await redis_service.subscribe_to_task_channel(task_id, pubsub)
    print(f"Subscribed to channel: websocket:task:{task_id}")

    # Wait for subscription confirmation
    await asyncio.sleep(0.1)
    confirmation = await pubsub.get_message(timeout=0.5)
    if confirmation:
        print(f"Subscription confirmed: {confirmation['type']}")

    # Simulate another instance publishing a message
    print("\nPublishing a message from another instance...")
    message = {
        "type": "log",
        "data": {
            "message": "Hello from another instance!",
            "timestamp": datetime.utcnow().isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    await redis_service.publish_websocket_message(task_id, message)

    # Receive the message
    print("Waiting for message...")
    received = await pubsub.get_message(timeout=2.0)

    if received and received['type'] == 'message':
        data = json.loads(received['data'])
        print(f"\nReceived message:")
        print(json.dumps(data, indent=2))
    else:
        print("No message received within timeout")

    # Cleanup
    await pubsub.close()
    await redis_client.close()


async def example_3_message_queue():
    """Example 3: Queue messages for offline clients"""
    print("\n=== Example 3: Message Queue for Offline Clients ===\n")

    # Initialize Redis
    redis_client = RedisClient("redis://localhost:6379/0")
    await redis_client.connect()
    redis_service = RedisService(redis_client.client)

    client_id = "test-client-123"
    print(f"Client ID: {client_id}")

    # Simulate client being offline - queue messages
    print("\nQueueing messages for offline client...")
    messages = [
        {
            "type": "log",
            "data": {"message": "Task started", "level": "info"},
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "type": "log",
            "data": {"message": "Processing data...", "level": "info"},
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "type": "status",
            "data": {"status": "in_progress", "progress": 50},
            "timestamp": datetime.utcnow().isoformat()
        }
    ]

    for msg in messages:
        await redis_service.queue_message_for_client(client_id, msg, ttl=3600)
        print(f"  Queued: {msg['type']} - {msg.get('data', {}).get('message', 'status update')}")

    # Simulate client coming back online
    print(f"\nClient {client_id} reconnecting...")
    queued_messages = await redis_service.get_queued_messages(client_id)

    print(f"Delivering {len(queued_messages)} queued messages:")
    for i, msg in enumerate(queued_messages, 1):
        print(f"\n  Message {i}:")
        print(f"    Type: {msg['type']}")
        print(f"    Data: {json.dumps(msg['data'], indent=6)}")

    # Verify queue is empty after retrieval
    remaining = await redis_service.get_queued_messages(client_id)
    print(f"\nRemaining messages in queue: {len(remaining)}")

    await redis_client.close()


async def example_4_cross_instance_simulation():
    """Example 4: Simulate cross-instance message flow"""
    print("\n=== Example 4: Cross-Instance Message Flow ===\n")

    # Initialize Redis (shared by all instances)
    redis_client = RedisClient("redis://localhost:6379/0")
    await redis_client.connect()
    redis_service = RedisService(redis_client.client)

    task_id = uuid4()
    print(f"Task ID: {task_id}")

    # Simulate Instance A - Subscribe to task
    print("\n[Instance A] Subscribing to task channel...")
    pubsub_a = redis_service.redis.pubsub()
    await redis_service.subscribe_to_task_channel(task_id, pubsub_a)
    await asyncio.sleep(0.1)
    await pubsub_a.get_message(timeout=0.5)  # Clear subscription message
    print("[Instance A] Ready to receive messages")

    # Simulate Instance B - Subscribe to task
    print("\n[Instance B] Subscribing to task channel...")
    pubsub_b = redis_service.redis.pubsub()
    await redis_service.subscribe_to_task_channel(task_id, pubsub_b)
    await asyncio.sleep(0.1)
    await pubsub_b.get_message(timeout=0.5)  # Clear subscription message
    print("[Instance B] Ready to receive messages")

    # Simulate Instance C - Publish a message
    print("\n[Instance C] Publishing a log message...")
    message = {
        "type": "log",
        "data": {
            "task_id": str(task_id),
            "level": "info",
            "message": "Task completed successfully!",
            "timestamp": datetime.utcnow().isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    num_subscribers = await redis_service.publish_websocket_message(task_id, message)
    print(f"[Instance C] Published to {num_subscribers} subscriber(s)")

    # Instance A receives the message
    print("\n[Instance A] Receiving message...")
    msg_a = await pubsub_a.get_message(timeout=2.0)
    if msg_a and msg_a['type'] == 'message':
        data_a = json.loads(msg_a['data'])
        print(f"[Instance A] Received: {data_a['data']['message']}")

    # Instance B receives the message
    print("\n[Instance B] Receiving message...")
    msg_b = await pubsub_b.get_message(timeout=2.0)
    if msg_b and msg_b['type'] == 'message':
        data_b = json.loads(msg_b['data'])
        print(f"[Instance B] Received: {data_b['data']['message']}")

    print("\n✓ Both instances received the same message via Redis Pub/Sub!")

    # Cleanup
    await pubsub_a.close()
    await pubsub_b.close()
    await redis_client.close()


async def example_5_pubsub_manager():
    """Example 5: Using RedisPubSubManager"""
    print("\n=== Example 5: RedisPubSubManager Usage ===\n")

    # Initialize Redis
    redis_client = RedisClient("redis://localhost:6379/0")
    await redis_client.connect()
    redis_service = RedisService(redis_client.client)

    # Import the managers
    from src.api.v1.websocket import RedisPubSubManager, ConnectionManager

    # Create managers
    connection_manager = ConnectionManager(redis_service)
    pubsub_manager = RedisPubSubManager(redis_service)
    await pubsub_manager.start(connection_manager)

    # Create test tasks
    task_1 = uuid4()
    task_2 = uuid4()

    print(f"Task 1 ID: {task_1}")
    print(f"Task 2 ID: {task_2}")

    # Subscribe to tasks
    print("\nSubscribing to tasks...")
    await pubsub_manager.subscribe_to_task(task_1)
    await pubsub_manager.subscribe_to_task(task_2)

    # Multiple subscriptions to same task
    await pubsub_manager.subscribe_to_task(task_1)

    print(f"\nActive subscriptions: {len(pubsub_manager.active_subscriptions)}")
    print(f"  Task 1: {pubsub_manager.active_subscriptions.get(task_1, 0)} subscriber(s)")
    print(f"  Task 2: {pubsub_manager.active_subscriptions.get(task_2, 0)} subscriber(s)")

    # Unsubscribe
    print("\nUnsubscribing from task 1 (first time)...")
    await pubsub_manager.unsubscribe_from_task(task_1)
    print(f"  Task 1: {pubsub_manager.active_subscriptions.get(task_1, 0)} subscriber(s)")

    print("\nUnsubscribing from task 1 (second time)...")
    await pubsub_manager.unsubscribe_from_task(task_1)
    print(f"  Task 1 still in subscriptions: {task_1 in pubsub_manager.active_subscriptions}")

    # Cleanup
    await pubsub_manager.stop()
    await redis_client.close()


async def main():
    """Run all examples"""
    print("=" * 70)
    print("WebSocket Redis Pub/Sub Examples")
    print("=" * 70)

    try:
        await example_1_publish_message()
        await asyncio.sleep(1)

        await example_2_subscribe_and_receive()
        await asyncio.sleep(1)

        await example_3_message_queue()
        await asyncio.sleep(1)

        await example_4_cross_instance_simulation()
        await asyncio.sleep(1)

        await example_5_pubsub_manager()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
