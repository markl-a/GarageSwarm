"""Test Worker Agent connection to Backend"""

import asyncio
import httpx
import uuid


async def test_worker_connection():
    """Test basic worker operations"""
    backend_url = "http://localhost:8002"
    machine_id = f"test-machine-{uuid.uuid4().hex[:8]}"
    machine_name = "Test Worker Machine"

    async with httpx.AsyncClient(base_url=backend_url, timeout=30.0) as client:
        # Test 1: Health check
        print("=" * 50)
        print("Test 1: Health Check")
        print("=" * 50)
        response = await client.get("/api/v1/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        # Test 2: Register worker
        print("\n" + "=" * 50)
        print("Test 2: Register Worker")
        print("=" * 50)
        register_data = {
            "machine_id": machine_id,
            "machine_name": machine_name,
            "tools": ["claude_code", "gemini_cli"],
            "system_info": {
                "platform": "Windows",
                "python_version": "3.11",
                "cpu_count": 8,
                "memory_total_gb": 16
            }
        }
        response = await client.post("/api/v1/workers/register", json=register_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 201:
            worker_data = response.json()
            worker_id = worker_data["worker_id"]
            print(f"\n[OK] Worker registered with ID: {worker_id}")

            # Test 3: Send heartbeat
            print("\n" + "=" * 50)
            print("Test 3: Send Heartbeat")
            print("=" * 50)
            heartbeat_data = {
                "status": "idle",
                "cpu_percent": 25.5,
                "memory_percent": 45.2,
                "disk_percent": 60.0
            }
            response = await client.post(
                f"/api/v1/workers/{worker_id}/heartbeat",
                json=heartbeat_data
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")

            if response.status_code == 200:
                print("\n[OK] Heartbeat sent successfully")
            else:
                print("\n[FAIL] Heartbeat failed")

            # Test 4: Pull task (should return None since no tasks)
            print("\n" + "=" * 50)
            print("Test 4: Pull Task")
            print("=" * 50)
            response = await client.get(f"/api/v1/workers/{worker_id}/pull-task")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                task = response.json()
                if task:
                    print(f"Task found: {task}")
                else:
                    print("No pending tasks (expected)")
                    print("\n[OK] Pull task working correctly")
            else:
                print(f"Response: {response.text}")

            # Test 5: Send offline heartbeat
            print("\n" + "=" * 50)
            print("Test 5: Send Offline Heartbeat")
            print("=" * 50)
            heartbeat_data = {
                "status": "offline",
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0
            }
            response = await client.post(
                f"/api/v1/workers/{worker_id}/heartbeat",
                json=heartbeat_data
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("\n[OK] Worker marked as offline")
            else:
                print(f"Response: {response.text}")

        else:
            print(f"\n[FAIL] Worker registration failed")

    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_worker_connection())
