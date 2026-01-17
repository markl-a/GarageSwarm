#!/usr/bin/env python3
"""
Docker Worker 快速測試腳本

使用方式:
    python test_docker_worker.py

測試項目:
    1. Backend 連線
    2. Worker 註冊狀態
    3. 建立測試任務
    4. 等待執行完成
    5. 驗證結果
"""

import asyncio
import httpx
import time
import subprocess


BACKEND_URL = "http://localhost:8002"
TEST_USER = {"username": "demo", "password": "Demo123!"}


def print_step(step: int, msg: str):
    print(f"\n[Step {step}] {msg}")


def print_ok(msg: str):
    print(f"  [OK] {msg}")


def print_fail(msg: str):
    print(f"  [FAIL] {msg}")


def print_info(msg: str):
    print(f"  [INFO] {msg}")


async def main():
    print("=" * 60)
    print("Docker Worker Test")
    print("=" * 60)

    # Step 1: Check Docker container
    print_step(1, "Check Docker container status")
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=multi-agent-worker", "--format", "{{.Status}}"],
        capture_output=True, text=True
    )
    if "Up" in result.stdout and "healthy" in result.stdout:
        print_ok(f"Container running: {result.stdout.strip()}")
    else:
        print_fail("Container not running or unhealthy")
        print_info("Run: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d")
        return

    # Step 2: Check Backend
    print_step(2, "Check Backend connection")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{BACKEND_URL}/api/v1/health")
            if resp.status_code == 200:
                print_ok(f"Backend OK: {resp.json().get('status')}")
            else:
                print_fail(f"Backend error: {resp.status_code}")
                return
        except Exception as e:
            print_fail(f"Cannot connect to Backend: {e}")
            return

        # Step 3: Login
        print_step(3, "Login to get Token")
        try:
            resp = await client.post(
                f"{BACKEND_URL}/api/v1/auth/login",
                json=TEST_USER
            )
            if resp.status_code == 200:
                token = resp.json().get("access_token")
                print_ok("Login successful")
            else:
                print_fail(f"Login failed: {resp.text}")
                return
        except Exception as e:
            print_fail(f"Login error: {e}")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # Step 4: Check workers
        print_step(4, "Check registered Workers")
        try:
            resp = await client.get(f"{BACKEND_URL}/api/v1/workers", headers=headers)
            workers = resp.json().get("workers", [])
            print_info(f"Registered Workers: {len(workers)}")
            for w in workers:
                status = "[ON]" if w.get("status") == "online" else "[OFF]"
                print_info(f"  {status} {w.get('machine_name')} - {w.get('tools', [])}")
        except Exception as e:
            print_info(f"Cannot get workers list: {e}")

        # Step 5: Create test task
        print_step(5, "Create test task")
        task_data = {
            "title": "Docker Worker Test",
            "description": "Answer: What is 1+1? Reply with number only.",
            "subtasks": [{
                "name": "Simple Math",
                "description": "Answer: What is 1+1? Reply with number only.",
                "recommended_tool": "claude_code"
            }]
        }

        try:
            resp = await client.post(
                f"{BACKEND_URL}/api/v1/tasks",
                json=task_data,
                headers=headers
            )
            if resp.status_code in (200, 201):
                task = resp.json()
                task_id = task.get("task_id")
                print_ok(f"Task created: {task_id}")
            else:
                print_fail(f"Task creation failed: {resp.text}")
                return
        except Exception as e:
            print_fail(f"Task creation error: {e}")
            return

        # Step 6: Wait for completion
        print_step(6, "Wait for task completion")
        max_wait = 60
        start = time.time()

        while time.time() - start < max_wait:
            await asyncio.sleep(5)
            elapsed = int(time.time() - start)

            try:
                resp = await client.get(
                    f"{BACKEND_URL}/api/v1/tasks/{task_id}",
                    headers=headers
                )
                task = resp.json()
                status = task.get("status", "unknown")
                progress = task.get("progress", 0)

                print_info(f"[{elapsed}s] Status: {status}, Progress: {progress}%")

                if status == "completed":
                    print_ok("Task completed successfully!")

                    # Get result
                    subtasks = task.get("subtasks", [])
                    if subtasks:
                        output = subtasks[0].get("output", {})
                        if output:
                            result_text = str(output.get("output", ""))[:200]
                            print_info(f"Result: {result_text}...")
                    return

                elif status == "failed":
                    print_fail("Task execution failed!")
                    subtasks = task.get("subtasks", [])
                    if subtasks:
                        error = subtasks[0].get("error", "Unknown error")
                        print_info(f"Error: {error[:200]}")
                    return

            except Exception as e:
                print_info(f"Query error: {e}")

        print_fail(f"Timeout ({max_wait}s), task not completed")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
