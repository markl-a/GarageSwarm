"""Integration tests for Workers API endpoints"""

import pytest
from uuid import uuid4


@pytest.fixture
def unique_worker_data():
    """Sample worker registration data with unique machine_id"""
    return {
        "machine_id": f"test-machine-{uuid4()}",
        "machine_name": "Test Development Machine",
        "system_info": {
            "os": "Linux",
            "os_version": "Ubuntu 22.04",
            "cpu_count": 8,
            "memory_total": 16000000000,
            "python_version": "3.11.0"
        },
        "tools": ["claude_code", "gemini_cli"]
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_worker_success(test_client, unique_worker_data):
    """Test successful worker registration"""
    response = await test_client.post(
        "/api/v1/workers/register",
        json=unique_worker_data
    )

    assert response.status_code == 200
    data = response.json()

    assert "worker_id" in data
    assert "status" in data
    assert data["status"] in ["registered", "updated"]
    assert "message" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_worker_idempotency(test_client, unique_worker_data):
    """Test that registering same worker twice is idempotent"""
    # First registration
    response1 = await test_client.post(
        "/api/v1/workers/register",
        json=unique_worker_data
    )
    assert response1.status_code == 200
    worker_id_1 = response1.json()["worker_id"]

    # Second registration with same machine_id
    response2 = await test_client.post(
        "/api/v1/workers/register",
        json=unique_worker_data
    )
    assert response2.status_code == 200
    worker_id_2 = response2.json()["worker_id"]

    # Should return same worker_id
    assert worker_id_1 == worker_id_2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_worker_validation_error(test_client):
    """Test worker registration with invalid data"""
    # Missing required field: machine_id
    response = await test_client.post(
        "/api/v1/workers/register",
        json={
            "machine_name": "Test Machine",
            "system_info": {},
            "tools": []
        }
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_heartbeat_success(test_client, unique_worker_data):
    """Test sending worker heartbeat"""
    # First register worker
    register_response = await test_client.post(
        "/api/v1/workers/register",
        json=unique_worker_data
    )
    assert register_response.status_code == 200
    worker_id = register_response.json()["worker_id"]

    # Send heartbeat
    heartbeat_data = {
        "status": "idle",
        "resources": {
            "cpu_percent": 25.5,
            "memory_percent": 60.2,
            "disk_percent": 45.0
        }
    }

    response = await test_client.post(
        f"/api/v1/workers/{worker_id}/heartbeat",
        json=heartbeat_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_heartbeat_not_found(test_client):
    """Test heartbeat for non-existent worker"""
    fake_worker_id = str(uuid4())

    response = await test_client.post(
        f"/api/v1/workers/{fake_worker_id}/heartbeat",
        json={
            "status": "online",
            "resources": {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0
            }
        }
    )

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_workers(test_client, unique_worker_data):
    """Test listing workers"""
    # Register a worker first
    await test_client.post(
        "/api/v1/workers/register",
        json=unique_worker_data
    )

    # List workers
    response = await test_client.get("/api/v1/workers")

    assert response.status_code == 200
    data = response.json()

    assert "workers" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["workers"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_workers_with_filters(test_client):
    """Test listing workers with status filter"""
    response = await test_client.get(
        "/api/v1/workers",
        params={"status": "online", "limit": 10, "offset": 0}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["limit"] == 10
    assert data["offset"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_worker_detail(test_client, unique_worker_data):
    """Test getting worker details"""
    # Register worker
    register_response = await test_client.post(
        "/api/v1/workers/register",
        json=unique_worker_data
    )
    assert register_response.status_code == 200
    worker_id = register_response.json()["worker_id"]

    # Get worker details
    response = await test_client.get(f"/api/v1/workers/{worker_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["worker_id"] == worker_id
    assert data["machine_name"] == unique_worker_data["machine_name"]
    assert "system_info" in data
    assert "tools" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_worker_not_found(test_client):
    """Test getting non-existent worker"""
    fake_worker_id = str(uuid4())

    response = await test_client.get(f"/api/v1/workers/{fake_worker_id}")

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unregister_worker(test_client, unique_worker_data):
    """Test unregistering worker"""
    # Register worker
    register_response = await test_client.post(
        "/api/v1/workers/register",
        json=unique_worker_data
    )
    assert register_response.status_code == 200
    worker_id = register_response.json()["worker_id"]

    # Unregister worker
    response = await test_client.post(f"/api/v1/workers/{worker_id}/unregister")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "unregistered"
    assert data["worker_id"] == worker_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unregister_worker_not_found(test_client):
    """Test unregistering non-existent worker"""
    fake_worker_id = str(uuid4())

    response = await test_client.post(f"/api/v1/workers/{fake_worker_id}/unregister")

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_lifecycle(test_client):
    """Test complete worker lifecycle: register -> heartbeat -> unregister"""
    # 1. Register
    worker_data = {
        "machine_id": f"lifecycle-test-{uuid4()}",
        "machine_name": "Lifecycle Test Machine",
        "system_info": {"os": "Linux"},
        "tools": ["claude_code"]
    }

    register_response = await test_client.post(
        "/api/v1/workers/register",
        json=worker_data
    )
    assert register_response.status_code == 200
    worker_id = register_response.json()["worker_id"]

    # 2. Send heartbeat
    heartbeat_response = await test_client.post(
        f"/api/v1/workers/{worker_id}/heartbeat",
        json={
            "status": "idle",
            "resources": {
                "cpu_percent": 10.0,
                "memory_percent": 50.0,
                "disk_percent": 30.0
            }
        }
    )
    assert heartbeat_response.status_code == 200

    # 3. Get details
    detail_response = await test_client.get(f"/api/v1/workers/{worker_id}")
    assert detail_response.status_code == 200

    # 4. Unregister
    unregister_response = await test_client.post(
        f"/api/v1/workers/{worker_id}/unregister"
    )
    assert unregister_response.status_code == 200
