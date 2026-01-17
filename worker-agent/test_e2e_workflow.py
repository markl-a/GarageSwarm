"""End-to-end test for workflow execution with Worker Agent"""

import asyncio
import httpx


async def test_workflow_execution():
    """Test complete workflow execution flow"""
    backend_url = "http://localhost:8002"

    async with httpx.AsyncClient(base_url=backend_url, timeout=60.0) as client:
        print("=" * 60)
        print("End-to-End Workflow Execution Test")
        print("=" * 60)

        # Step 1: Login to get auth token
        print("\n[Step 1] Logging in...")
        login_response = await client.post("/api/v1/auth/login", json={
            "username": "demo",
            "password": "Demo123!"
        })
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.text}")
            # Try registering
            print("Attempting to register demo user...")
            register_response = await client.post("/api/v1/auth/register", json={
                "username": "demo",
                "email": "demo@example.com",
                "password": "Demo123!"
            })
            if register_response.status_code not in [200, 201]:
                print(f"Registration failed: {register_response.text}")
                return
            login_response = await client.post("/api/v1/auth/login", json={
                "username": "demo",
                "password": "Demo123!"
            })

        auth_data = login_response.json()
        token = auth_data.get("access_token")
        client.headers["Authorization"] = f"Bearer {token}"
        print(f"[OK] Logged in successfully")

        # Step 2: Check workers
        print("\n[Step 2] Checking available workers...")
        workers_response = await client.get("/api/v1/workers")
        workers_data = workers_response.json()
        print(f"Total workers: {workers_data.get('total', 0)}")
        if workers_data.get("workers"):
            for w in workers_data["workers"][:3]:
                print(f"  - {w['machine_name']} ({w['status']}) - Tools: {w.get('tools', [])}")

        # Step 3: Create a simple task (not workflow) for worker to pick up
        print("\n[Step 3] Creating a test task for Claude Code...")
        task_response = await client.post("/api/v1/tasks", json={
            "description": "Write a Python function that returns the factorial of a number. Save it to factorial.py",
            "tool_preference": "claude_code",
            "priority": 10
        })
        if task_response.status_code not in [200, 201]:
            print(f"Task creation failed: {task_response.text}")
            return

        task_data = task_response.json()
        task_id = task_data.get("task_id")
        print(f"[OK] Task created: {task_id}")
        print(f"    Description: {task_data.get('description', '')[:50]}...")

        # Step 4: Wait for worker to pick up and complete the task
        print("\n[Step 4] Waiting for worker to complete task...")
        max_wait = 120  # 2 minutes
        poll_interval = 5
        waited = 0

        while waited < max_wait:
            await asyncio.sleep(poll_interval)
            waited += poll_interval

            # Check task status
            status_response = await client.get(f"/api/v1/tasks/{task_id}")
            if status_response.status_code != 200:
                print(f"    Error checking task: {status_response.text}")
                continue

            status_data = status_response.json()
            task_status = status_data.get("status")
            progress = status_data.get("progress", 0)

            print(f"    [{waited}s] Status: {task_status}, Progress: {progress}%")

            if task_status == "completed":
                print(f"\n[OK] Task completed successfully!")
                result = status_data.get("result")
                if result:
                    print(f"    Result output: {str(result)[:200]}...")
                break
            elif task_status == "failed":
                print(f"\n[FAIL] Task failed!")
                error = status_data.get("error")
                if error:
                    print(f"    Error: {error}")
                break
        else:
            print(f"\n[TIMEOUT] Task did not complete within {max_wait} seconds")

        # Step 5: Create and execute a workflow
        print("\n[Step 5] Creating a sequential workflow...")
        workflow_response = await client.post("/api/v1/workflows", json={
            "name": "E2E Test Workflow",
            "description": "End-to-end test workflow",
            "workflow_type": "sequential"
        })
        if workflow_response.status_code not in [200, 201]:
            print(f"Workflow creation failed: {workflow_response.text}")
            return

        workflow_data = workflow_response.json()
        workflow_id = workflow_data.get("workflow_id")
        print(f"[OK] Workflow created: {workflow_id}")

        # Step 6: Check workflow status
        print("\n[Step 6] Checking workflow status...")
        workflow_status_response = await client.get(f"/api/v1/workflows/{workflow_id}")
        if workflow_status_response.status_code == 200:
            workflow_status = workflow_status_response.json()
            print(f"    Name: {workflow_status.get('name')}")
            print(f"    Status: {workflow_status.get('status')}")
            print(f"    Type: {workflow_status.get('workflow_type')}")

        print("\n" + "=" * 60)
        print("End-to-End Test Complete!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_workflow_execution())
