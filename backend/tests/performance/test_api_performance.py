"""
API Performance Tests

Test API endpoint response times to ensure they meet NFR requirements:
- Worker registration < 5 seconds
- Task submission < 2 seconds
- Task query < 1 second
- Worker list < 1 second
"""

import pytest
from uuid import uuid4
from tests.performance.conftest import PerformanceTimer


@pytest.mark.performance
@pytest.mark.asyncio
class TestWorkerAPIPerformance:
    """Test Worker API performance"""

    async def test_worker_registration_performance(
        self,
        test_client,
        perf_timer,
        assert_performance,
        performance_thresholds,
        sample_worker_data_factory
    ):
        """Test worker registration response time < 5 seconds"""
        worker_data = sample_worker_data_factory(1)

        with perf_timer("worker_registration") as timer:
            response = await test_client.post("/api/v1/workers/register", json=worker_data)

        assert response.status_code == 200
        assert_performance(
            timer.duration_ms,
            performance_thresholds["worker_registration_ms"],
            "Worker registration"
        )

    async def test_worker_registration_repeated_performance(
        self,
        test_client,
        perf_analyzer,
        performance_thresholds,
        sample_worker_data_factory
    ):
        """Test repeated worker registrations (measures average performance)"""
        num_registrations = 10

        for i in range(num_registrations):
            worker_data = sample_worker_data_factory(i)

            with PerformanceTimer(f"worker_registration_{i}") as timer:
                response = await test_client.post("/api/v1/workers/register", json=worker_data)

            assert response.status_code == 200
            perf_analyzer.add_metric(timer.get_metrics())

        # Generate and check report
        report = perf_analyzer.generate_report()
        print(f"\n=== Worker Registration Performance ({num_registrations} runs) ===")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")
        print(f"P99: {report.p99_duration_ms:.2f}ms")

        assert report.meets_requirement(performance_thresholds["worker_registration_ms"]), \
            f"P95 latency {report.p95_duration_ms:.2f}ms exceeds {performance_thresholds['worker_registration_ms']}ms"

    async def test_worker_heartbeat_performance(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_worker_data_factory
    ):
        """Test worker heartbeat response time"""
        # First register a worker
        worker_data = sample_worker_data_factory(1)
        response = await test_client.post("/api/v1/workers/register", json=worker_data)
        assert response.status_code == 200
        worker_id = response.json()["worker_id"]

        # Test heartbeat performance
        heartbeat_data = {
            "status": "online",
            "resources": {
                "cpu_percent": 45.5,
                "memory_percent": 60.0,
                "disk_percent": 70.0
            }
        }

        with perf_timer("worker_heartbeat") as timer:
            response = await test_client.post(
                f"/api/v1/workers/{worker_id}/heartbeat",
                json=heartbeat_data
            )

        assert response.status_code == 200
        # Heartbeat should be very fast (< 500ms)
        assert_performance(timer.duration_ms, 500, "Worker heartbeat")

    async def test_worker_list_performance(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_worker_data_factory
    ):
        """Test worker list API response time"""
        # Register a few workers first
        for i in range(5):
            worker_data = sample_worker_data_factory(i)
            await test_client.post("/api/v1/workers/register", json=worker_data)

        # Test list performance
        with perf_timer("worker_list") as timer:
            response = await test_client.get("/api/v1/workers")

        assert response.status_code == 200
        # List should be fast (< 1 second)
        assert_performance(timer.duration_ms, 1000, "Worker list")

    async def test_worker_get_performance(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_worker_data_factory
    ):
        """Test get single worker API response time"""
        # Register a worker
        worker_data = sample_worker_data_factory(1)
        response = await test_client.post("/api/v1/workers/register", json=worker_data)
        worker_id = response.json()["worker_id"]

        # Test get performance
        with perf_timer("worker_get") as timer:
            response = await test_client.get(f"/api/v1/workers/{worker_id}")

        assert response.status_code == 200
        # Get should be very fast (< 500ms)
        assert_performance(timer.duration_ms, 500, "Worker get")


@pytest.mark.performance
@pytest.mark.asyncio
class TestTaskAPIPerformance:
    """Test Task API performance"""

    async def test_task_submission_performance(
        self,
        test_client,
        perf_timer,
        assert_performance,
        performance_thresholds,
        sample_task_data_factory
    ):
        """Test task submission response time < 2 seconds"""
        task_data = sample_task_data_factory(1)

        with perf_timer("task_submission") as timer:
            response = await test_client.post("/api/v1/tasks", json=task_data)

        assert response.status_code == 201
        assert_performance(
            timer.duration_ms,
            performance_thresholds["task_submission_ms"],
            "Task submission"
        )

    async def test_task_submission_repeated_performance(
        self,
        test_client,
        perf_analyzer,
        performance_thresholds,
        sample_task_data_factory
    ):
        """Test repeated task submissions (measures average performance)"""
        num_tasks = 10

        for i in range(num_tasks):
            task_data = sample_task_data_factory(i)

            with PerformanceTimer(f"task_submission_{i}") as timer:
                response = await test_client.post("/api/v1/tasks", json=task_data)

            assert response.status_code == 201
            perf_analyzer.add_metric(timer.get_metrics())

        # Generate and check report
        report = perf_analyzer.generate_report()
        print(f"\n=== Task Submission Performance ({num_tasks} runs) ===")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")
        print(f"P99: {report.p99_duration_ms:.2f}ms")

        assert report.meets_requirement(performance_thresholds["task_submission_ms"]), \
            f"P95 latency {report.p95_duration_ms:.2f}ms exceeds {performance_thresholds['task_submission_ms']}ms"

    async def test_task_query_performance(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_task_data_factory
    ):
        """Test task query response time"""
        # Create a task first
        task_data = sample_task_data_factory(1)
        response = await test_client.post("/api/v1/tasks", json=task_data)
        task_id = response.json()["task_id"]

        # Test query performance
        with perf_timer("task_query") as timer:
            response = await test_client.get(f"/api/v1/tasks/{task_id}")

        assert response.status_code == 200
        # Query should be fast (< 1 second)
        assert_performance(timer.duration_ms, 1000, "Task query")

    async def test_task_list_performance(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_task_data_factory
    ):
        """Test task list API response time"""
        # Create a few tasks first
        for i in range(5):
            task_data = sample_task_data_factory(i)
            await test_client.post("/api/v1/tasks", json=task_data)

        # Test list performance
        with perf_timer("task_list") as timer:
            response = await test_client.get("/api/v1/tasks")

        assert response.status_code == 200
        # List should be fast (< 1 second)
        assert_performance(timer.duration_ms, 1000, "Task list")

    async def test_task_progress_performance(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_task_data_factory
    ):
        """Test task progress query response time"""
        # Create a task first
        task_data = sample_task_data_factory(1)
        response = await test_client.post("/api/v1/tasks", json=task_data)
        task_id = response.json()["task_id"]

        # Test progress query performance
        with perf_timer("task_progress") as timer:
            response = await test_client.get(f"/api/v1/tasks/{task_id}/progress")

        assert response.status_code == 200
        # Progress query should be very fast (< 200ms) as it's from Redis
        assert_performance(timer.duration_ms, 200, "Task progress query")

    async def test_task_decompose_performance(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_task_data_factory
    ):
        """Test task decomposition performance"""
        # Create a task first
        task_data = sample_task_data_factory(1)
        response = await test_client.post("/api/v1/tasks", json=task_data)
        task_id = response.json()["task_id"]

        # Test decompose performance
        with perf_timer("task_decompose") as timer:
            response = await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

        assert response.status_code == 200
        # Decompose should complete in reasonable time (< 2 seconds)
        assert_performance(timer.duration_ms, 2000, "Task decomposition")


@pytest.mark.performance
@pytest.mark.asyncio
class TestHealthAPIPerformance:
    """Test Health API performance"""

    async def test_health_check_performance(
        self,
        test_client,
        perf_timer,
        assert_performance
    ):
        """Test health check endpoint response time"""
        with perf_timer("health_check") as timer:
            response = await test_client.get("/api/v1/health")

        assert response.status_code == 200
        # Health check should be very fast (< 100ms)
        assert_performance(timer.duration_ms, 100, "Health check")

    async def test_health_check_consistency(
        self,
        test_client,
        perf_analyzer
    ):
        """Test health check consistency across multiple calls"""
        num_checks = 50

        for i in range(num_checks):
            with PerformanceTimer(f"health_check_{i}") as timer:
                response = await test_client.get("/api/v1/health")

            assert response.status_code == 200
            perf_analyzer.add_metric(timer.get_metrics())

        report = perf_analyzer.generate_report()
        print(f"\n=== Health Check Performance ({num_checks} runs) ===")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"Min: {report.min_duration_ms:.2f}ms")
        print(f"Max: {report.max_duration_ms:.2f}ms")
        print(f"Std Dev: {report.std_deviation_ms:.2f}ms")

        # Health check should be consistently fast
        assert report.p99_duration_ms < 200, \
            f"P99 latency {report.p99_duration_ms:.2f}ms is too high for health check"
