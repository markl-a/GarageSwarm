"""
E2E Tests: Worker Lifecycle

Tests for the complete worker lifecycle including:
- Worker registration
- Heartbeat mechanism
- Resource monitoring
- Offline detection
- Graceful shutdown
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_worker_registration_flow(test_client):
    """Test complete worker registration flow"""
    # Prepare unique worker data
    machine_id = f"test-machine-{uuid4()}"
    worker_data = {
        "machine_id": machine_id,
        "machine_name": "Test Worker Registration",
        "system_info": {
            "os": "Linux",
            "os_version": "Ubuntu 22.04",
            "cpu_count": 8,
            "memory_total": 16000000000,
            "python_version": "3.11.0"
        },
        "tools": ["claude_code", "gemini_cli"]
    }

    # Register worker
    response = await test_client.post(
        "/api/v1/workers/register",
        json=worker_data
    )

    assert response.status_code == 200
    data = response.json()
    assert "worker_id" in data
    assert data["status"] in ["registered", "updated"]
    worker_id = data["worker_id"]

    # Verify worker was created
    response = await test_client.get(f"/api/v1/workers/{worker_id}")
    assert response.status_code == 200

    worker_details = response.json()
    assert worker_details["machine_id"] == machine_id
    assert worker_details["machine_name"] == "Test Worker Registration"
    assert worker_details["status"] in ["online", "offline", "idle"]
    assert "claude_code" in worker_details["tools"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_worker_registration_idempotency(test_client):
    """Test that worker registration is idempotent"""
    machine_id = f"test-machine-{uuid4()}"
    worker_data = {
        "machine_id": machine_id,
        "machine_name": "Idempotency Test Worker",
        "system_info": {
            "os": "Windows",
            "os_version": "Windows 11",
            "cpu_count": 16,
            "memory_total": 32000000000,
            "python_version": "3.11.0"
        },
        "tools": ["claude_code"]
    }

    # First registration
    response1 = await test_client.post(
        "/api/v1/workers/register",
        json=worker_data
    )
    assert response1.status_code == 200
    worker_id_1 = response1.json()["worker_id"]

    # Second registration with same machine_id
    response2 = await test_client.post(
        "/api/v1/workers/register",
        json=worker_data
    )
    assert response2.status_code == 200
    worker_id_2 = response2.json()["worker_id"]

    # Should return same worker_id
    assert worker_id_1 == worker_id_2

    # Verify worker details are updated
    response = await test_client.get(f"/api/v1/workers/{worker_id_1}")
    assert response.status_code == 200
    assert response.json()["machine_name"] == "Idempotency Test Worker"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_worker_heartbeat_mechanism(test_client):
    """Test worker heartbeat updates status and resources"""
    # Register worker
    machine_id = f"test-machine-{uuid4()}"
    worker_data = {
        "machine_id": machine_id,
        "machine_name": "Heartbeat Test Worker",
        "system_info": {
            "os": "Linux",
            "cpu_count": 4,
            "memory_total": 8000000000
        },
        "tools": ["claude_code"]
    }

    register_response = await test_client.post(
        "/api/v1/workers/register",
        json=worker_data
    )
    assert register_response.status_code == 200
    worker_id = register_response.json()["worker_id"]

    # Send first heartbeat
    heartbeat_data = {
        "status": "idle",
        "resources": {
            "cpu_percent": 15.5,
            "memory_percent": 45.2,
            "disk_percent": 60.0
        }
    }

    response = await test_client.post(
        f"/api/v1/workers/{worker_id}/heartbeat",
        json=heartbeat_data
    )
    assert response.status_code == 200
    assert response.json()["acknowledged"] is True

    # Verify heartbeat updated worker status
    worker_response = await test_client.get(f"/api/v1/workers/{worker_id}")
    assert worker_response.status_code == 200
    worker_details = worker_response.json()
    assert worker_details["status"] == "idle"
    assert worker_details["cpu_percent"] == 15.5
    assert worker_details["memory_percent"] == 45.2
    assert worker_details["disk_percent"] == 60.0

    # Send second heartbeat with different status
    heartbeat_data["status"] = "busy"
    heartbeat_data["resources"]["cpu_percent"] = 85.0

    response = await test_client.post(
        f"/api/v1/workers/{worker_id}/heartbeat",
        json=heartbeat_data
    )
    assert response.status_code == 200

    # Verify status changed
    worker_response = await test_client.get(f"/api/v1/workers/{worker_id}")
    assert worker_response.status_code == 200
    worker_details = worker_response.json()
    assert worker_details["status"] == "busy"
    assert worker_details["cpu_percent"] == 85.0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_worker_resource_monitoring(test_client):
    """Test worker resource usage tracking over time"""
    # Register worker
    machine_id = f"test-machine-{uuid4()}"
    worker_data = {
        "machine_id": machine_id,
        "machine_name": "Resource Monitor Worker",
        "system_info": {
            "os": "Linux",
            "cpu_count": 8,
            "memory_total": 16000000000
        },
        "tools": ["claude_code", "gemini_cli"]
    }

    register_response = await test_client.post(
        "/api/v1/workers/register",
        json=worker_data
    )
    worker_id = register_response.json()["worker_id"]

    # Simulate resource usage changes over time
    resource_updates = [
        {"cpu_percent": 20.0, "memory_percent": 40.0, "disk_percent": 50.0},
        {"cpu_percent": 45.0, "memory_percent": 55.0, "disk_percent": 52.0},
        {"cpu_percent": 75.0, "memory_percent": 70.0, "disk_percent": 55.0},
        {"cpu_percent": 30.0, "memory_percent": 45.0, "disk_percent": 55.0},
    ]

    for resources in resource_updates:
        response = await test_client.post(
            f"/api/v1/workers/{worker_id}/heartbeat",
            json={
                "status": "busy" if resources["cpu_percent"] > 50 else "idle",
                "resources": resources
            }
        )
        assert response.status_code == 200

        # Verify resources were updated
        worker_response = await test_client.get(f"/api/v1/workers/{worker_id}")
        worker_details = worker_response.json()
        assert worker_details["cpu_percent"] == resources["cpu_percent"]
        assert worker_details["memory_percent"] == resources["memory_percent"]

        # Small delay between updates
        await asyncio.sleep(0.1)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_worker_with_current_task(test_client):
    """Test worker heartbeat with current task information"""
    # Register worker
    machine_id = f"test-machine-{uuid4()}"
    worker_data = {
        "machine_id": machine_id,
        "machine_name": "Task Worker",
        "system_info": {"os": "Linux", "cpu_count": 4, "memory_total": 8000000000},
        "tools": ["claude_code"]
    }

    register_response = await test_client.post(
        "/api/v1/workers/register",
        json=worker_data
    )
    worker_id = register_response.json()["worker_id"]

    # Send heartbeat with current task
    current_task_id = str(uuid4())
    heartbeat_data = {
        "status": "busy",
        "resources": {
            "cpu_percent": 60.0,
            "memory_percent": 55.0,
            "disk_percent": 50.0
        },
        "current_task": current_task_id
    }

    response = await test_client.post(
        f"/api/v1/workers/{worker_id}/heartbeat",
        json=heartbeat_data
    )
    assert response.status_code == 200
    assert response.json()["acknowledged"] is True

    # Send heartbeat without task (task completed)
    heartbeat_data["status"] = "idle"
    heartbeat_data["current_task"] = None
    heartbeat_data["resources"]["cpu_percent"] = 20.0

    response = await test_client.post(
        f"/api/v1/workers/{worker_id}/heartbeat",
        json=heartbeat_data
    )
    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_worker_graceful_shutdown(test_client):
    """Test worker graceful unregistration"""
    # Register worker
    machine_id = f"test-machine-{uuid4()}"
    worker_data = {
        "machine_id": machine_id,
        "machine_name": "Shutdown Test Worker",
        "system_info": {"os": "Linux", "cpu_count": 4, "memory_total": 8000000000},
        "tools": ["claude_code"]
    }

    register_response = await test_client.post(
        "/api/v1/workers/register",
        json=worker_data
    )
    worker_id = register_response.json()["worker_id"]

    # Send heartbeat to ensure worker is online
    await test_client.post(
        f"/api/v1/workers/{worker_id}/heartbeat",
        json={
            "status": "idle",
            "resources": {
                "cpu_percent": 10.0,
                "memory_percent": 30.0,
                "disk_percent": 40.0
            }
        }
    )

    # Gracefully unregister worker
    response = await test_client.post(
        f"/api/v1/workers/{worker_id}/unregister"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unregistered"
    assert data["worker_id"] == worker_id

    # Verify worker status is offline
    worker_response = await test_client.get(f"/api/v1/workers/{worker_id}")
    assert worker_response.status_code == 200
    worker_details = worker_response.json()
    assert worker_details["status"] == "offline"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_list_workers_filtering(test_client):
    """Test listing workers with status filtering"""
    # Create multiple workers with different statuses
    workers = []

    for i in range(3):
        machine_id = f"test-machine-{uuid4()}"
        worker_data = {
            "machine_id": machine_id,
            "machine_name": f"Test Worker {i}",
            "system_info": {"os": "Linux", "cpu_count": 4, "memory_total": 8000000000},
            "tools": ["claude_code"]
        }

        register_response = await test_client.post(
            "/api/v1/workers/register",
            json=worker_data
        )
        worker_id = register_response.json()["worker_id"]

        # Set different statuses
        status = ["idle", "busy", "idle"][i]
        await test_client.post(
            f"/api/v1/workers/{worker_id}/heartbeat",
            json={
                "status": status,
                "resources": {
                    "cpu_percent": 20.0,
                    "memory_percent": 40.0,
                    "disk_percent": 50.0
                }
            }
        )

        workers.append({"worker_id": worker_id, "status": status})

    # List all workers
    response = await test_client.get("/api/v1/workers")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3

    # Filter by status: idle
    response = await test_client.get("/api/v1/workers?status=idle")
    assert response.status_code == 200
    data = response.json()
    assert all(w["status"] == "idle" for w in data["workers"])

    # Filter by status: busy
    response = await test_client.get("/api/v1/workers?status=busy")
    assert response.status_code == 200
    data = response.json()
    assert all(w["status"] == "busy" for w in data["workers"])


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_worker_heartbeat_nonexistent(test_client):
    """Test sending heartbeat for non-existent worker"""
    fake_worker_id = uuid4()

    response = await test_client.post(
        f"/api/v1/workers/{fake_worker_id}/heartbeat",
        json={
            "status": "idle",
            "resources": {
                "cpu_percent": 20.0,
                "memory_percent": 40.0,
                "disk_percent": 50.0
            }
        }
    )

    # Should return 404 or handle gracefully
    assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_worker_multiple_tools(test_client):
    """Test worker with multiple AI tools"""
    machine_id = f"test-machine-{uuid4()}"
    worker_data = {
        "machine_id": machine_id,
        "machine_name": "Multi-Tool Worker",
        "system_info": {"os": "Linux", "cpu_count": 16, "memory_total": 32000000000},
        "tools": ["claude_code", "gemini_cli", "ollama"]
    }

    response = await test_client.post(
        "/api/v1/workers/register",
        json=worker_data
    )
    assert response.status_code == 200
    worker_id = response.json()["worker_id"]

    # Verify all tools are registered
    worker_response = await test_client.get(f"/api/v1/workers/{worker_id}")
    worker_details = worker_response.json()
    assert len(worker_details["tools"]) == 3
    assert "claude_code" in worker_details["tools"]
    assert "gemini_cli" in worker_details["tools"]
    assert "ollama" in worker_details["tools"]
