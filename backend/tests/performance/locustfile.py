"""
Locust Load Testing Configuration

Run with:
    locust -f locustfile.py --host=http://localhost:8000

Or run with web UI:
    locust -f locustfile.py --host=http://localhost:8000 --web-host=0.0.0.0

Test scenarios:
1. Worker lifecycle: register -> heartbeat -> unregister
2. Task lifecycle: create -> query -> decompose
3. Mixed workload: workers + tasks + queries
"""

from locust import HttpUser, task, between, SequentialTaskSet
import random
import json


class WorkerBehavior(SequentialTaskSet):
    """Sequential task set for worker lifecycle"""

    def on_start(self):
        """Initialize worker data"""
        self.worker_id = None
        self.machine_id = f"locust-worker-{random.randint(1000, 9999)}"

    @task
    def register_worker(self):
        """Register a worker"""
        worker_data = {
            "machine_id": self.machine_id,
            "machine_name": f"Locust Worker {self.machine_id}",
            "system_info": {
                "os": "Linux",
                "cpu_count": 8,
                "memory_total": 16000000000
            },
            "tools": ["claude_code", "gemini_cli"]
        }

        with self.client.post(
            "/api/v1/workers/register",
            json=worker_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                self.worker_id = response.json()["worker_id"]
                response.success()
            else:
                response.failure(f"Registration failed: {response.status_code}")

    @task
    def send_heartbeat(self):
        """Send heartbeat (repeat 5 times)"""
        if not self.worker_id:
            return

        for _ in range(5):
            heartbeat_data = {
                "status": "online",
                "resources": {
                    "cpu_percent": random.uniform(20, 80),
                    "memory_percent": random.uniform(40, 70),
                    "disk_percent": random.uniform(30, 60)
                }
            }

            with self.client.post(
                f"/api/v1/workers/{self.worker_id}/heartbeat",
                json=heartbeat_data,
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Heartbeat failed: {response.status_code}")

            self.wait()  # Wait between heartbeats

    @task
    def unregister_worker(self):
        """Unregister worker"""
        if not self.worker_id:
            return

        with self.client.post(
            f"/api/v1/workers/{self.worker_id}/unregister",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unregister failed: {response.status_code}")


class TaskBehavior(SequentialTaskSet):
    """Sequential task set for task lifecycle"""

    def on_start(self):
        """Initialize task data"""
        self.task_id = None

    @task
    def create_task(self):
        """Create a task"""
        task_data = {
            "description": f"Locust test task {random.randint(1000, 9999)}: Implement feature X",
            "task_type": random.choice(["develop_feature", "bug_fix", "refactor", "code_review"]),
            "requirements": {
                "complexity": random.choice(["low", "medium", "high"]),
                "estimated_time": "30m"
            },
            "checkpoint_frequency": "medium",
            "privacy_level": "normal",
            "tool_preferences": ["claude_code"]
        }

        with self.client.post(
            "/api/v1/tasks",
            json=task_data,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                self.task_id = response.json()["task_id"]
                response.success()
            else:
                response.failure(f"Task creation failed: {response.status_code}")

    @task
    def query_task(self):
        """Query task details (repeat 3 times)"""
        if not self.task_id:
            return

        for _ in range(3):
            with self.client.get(
                f"/api/v1/tasks/{self.task_id}",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Task query failed: {response.status_code}")

            self.wait()

    @task
    def query_progress(self):
        """Query task progress"""
        if not self.task_id:
            return

        with self.client.get(
            f"/api/v1/tasks/{self.task_id}/progress",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Progress query failed: {response.status_code}")

    @task
    def decompose_task(self):
        """Decompose task"""
        if not self.task_id:
            return

        with self.client.post(
            f"/api/v1/tasks/{self.task_id}/decompose",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Task decomposition failed: {response.status_code}")


class WorkerUser(HttpUser):
    """Simulates a worker agent"""
    tasks = [WorkerBehavior]
    wait_time = between(1, 3)  # Wait 1-3 seconds between task sets

    def on_start(self):
        """Called when a simulated user starts"""
        pass


class TaskUser(HttpUser):
    """Simulates a task submitter"""
    tasks = [TaskBehavior]
    wait_time = between(2, 5)  # Wait 2-5 seconds between task sets

    def on_start(self):
        """Called when a simulated user starts"""
        pass


class MixedUser(HttpUser):
    """Simulates mixed workload - both worker and task operations"""
    wait_time = between(1, 4)

    @task(3)
    def list_workers(self):
        """List workers (high frequency)"""
        with self.client.get("/api/v1/workers", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List workers failed: {response.status_code}")

    @task(3)
    def list_tasks(self):
        """List tasks (high frequency)"""
        with self.client.get("/api/v1/tasks", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List tasks failed: {response.status_code}")

    @task(2)
    def health_check(self):
        """Health check (medium frequency)"""
        with self.client.get("/api/v1/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def create_worker(self):
        """Create a worker (low frequency)"""
        machine_id = f"locust-mixed-{random.randint(1000, 9999)}"
        worker_data = {
            "machine_id": machine_id,
            "machine_name": f"Mixed Locust Worker {machine_id}",
            "system_info": {
                "os": "Linux",
                "cpu_count": 8,
                "memory_total": 16000000000
            },
            "tools": ["claude_code"]
        }

        with self.client.post("/api/v1/workers/register", json=worker_data, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Worker creation failed: {response.status_code}")

    @task(1)
    def create_task(self):
        """Create a task (low frequency)"""
        task_data = {
            "description": f"Mixed load task {random.randint(1000, 9999)}",
            "task_type": "develop_feature",
            "checkpoint_frequency": "medium",
            "privacy_level": "normal"
        }

        with self.client.post("/api/v1/tasks", json=task_data, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Task creation failed: {response.status_code}")


# Recommended test scenarios:

# 1. Worker load test:
#    locust -f locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=60s --only-summary WorkerUser

# 2. Task load test:
#    locust -f locustfile.py --host=http://localhost:8000 --users=20 --spawn-rate=4 --run-time=60s --only-summary TaskUser

# 3. Mixed load test:
#    locust -f locustfile.py --host=http://localhost:8000 --users=30 --spawn-rate=5 --run-time=120s --only-summary MixedUser

# 4. Full load test with web UI:
#    locust -f locustfile.py --host=http://localhost:8000
#    Then open http://localhost:8089 in browser
