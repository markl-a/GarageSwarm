"""
Concurrent Tasks Performance Tests

Test system performance with multiple tasks:
- 20 tasks simultaneous submission
- Parallel task execution performance
- Task queue performance under load
"""

import pytest
import asyncio


@pytest.mark.performance
@pytest.mark.asyncio
class TestConcurrentTaskSubmission:
    """Test concurrent task submission performance"""

    async def test_20_tasks_concurrent_submission(
        self,
        test_client,
        run_concurrent_timed,
        performance_thresholds,
        sample_task_data_factory
    ):
        """Test 20 tasks being submitted simultaneously (NFR requirement)"""
        num_tasks = performance_thresholds["max_concurrent_tasks"]

        # Prepare task submission coroutines
        async def submit_task(task_data):
            response = await test_client.post("/api/v1/tasks", json=task_data)
            return response

        # Generate task data for all tasks
        args_list = [(sample_task_data_factory(i),) for i in range(num_tasks)]

        # Run concurrent submissions
        results, report = await run_concurrent_timed(
            submit_task,
            args_list,
            operation="concurrent_task_submission"
        )

        # Verify all tasks submitted successfully
        successful_submissions = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 201
        )

        print(f"\n=== Concurrent Task Submission ({num_tasks} tasks) ===")
        print(f"Successful: {successful_submissions}/{num_tasks}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")
        print(f"Max: {report.max_duration_ms:.2f}ms")

        assert successful_submissions == num_tasks, \
            f"Only {successful_submissions}/{num_tasks} tasks submitted successfully"

        # Each task submission should complete within threshold
        assert report.p95_duration_ms <= performance_thresholds["task_submission_ms"], \
            f"P95 submission time {report.p95_duration_ms:.2f}ms exceeds {performance_thresholds['task_submission_ms']}ms"

    async def test_50_tasks_concurrent_submission(
        self,
        test_client,
        run_concurrent_timed,
        sample_task_data_factory
    ):
        """Test 50 tasks being submitted simultaneously (stress test)"""
        num_tasks = 50

        async def submit_task(task_data):
            response = await test_client.post("/api/v1/tasks", json=task_data)
            return response

        args_list = [(sample_task_data_factory(i),) for i in range(num_tasks)]

        results, report = await run_concurrent_timed(
            submit_task,
            args_list,
            operation="concurrent_task_submission_stress"
        )

        successful_submissions = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 201
        )

        print(f"\n=== Stress Test: Concurrent Task Submission ({num_tasks} tasks) ===")
        print(f"Successful: {successful_submissions}/{num_tasks}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")
        print(f"P99: {report.p99_duration_ms:.2f}ms")

        # Should still handle 50 tasks gracefully
        assert successful_submissions >= num_tasks * 0.95, \
            f"Less than 95% success rate: {successful_submissions}/{num_tasks}"


@pytest.mark.performance
@pytest.mark.asyncio
class TestConcurrentTaskQueries:
    """Test concurrent task query performance"""

    async def test_20_tasks_concurrent_queries(
        self,
        test_client,
        run_concurrent_timed,
        performance_thresholds,
        sample_task_data_factory
    ):
        """Test querying 20 tasks simultaneously"""
        num_tasks = performance_thresholds["max_concurrent_tasks"]

        # First, create all tasks
        task_ids = []
        for i in range(num_tasks):
            task_data = sample_task_data_factory(i)
            response = await test_client.post("/api/v1/tasks", json=task_data)
            assert response.status_code == 201
            task_ids.append(response.json()["task_id"])

        # Prepare query coroutines
        async def query_task(task_id):
            response = await test_client.get(f"/api/v1/tasks/{task_id}")
            return response

        # Run concurrent queries
        args_list = [(task_id,) for task_id in task_ids]
        results, report = await run_concurrent_timed(
            query_task,
            args_list,
            operation="concurrent_task_query"
        )

        successful_queries = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 200
        )

        print(f"\n=== Concurrent Task Queries ({num_tasks} tasks) ===")
        print(f"Successful: {successful_queries}/{num_tasks}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")

        assert successful_queries == num_tasks, \
            f"Only {successful_queries}/{num_tasks} queries succeeded"

        # Queries should be fast
        assert report.p95_duration_ms <= 1500, \
            f"P95 query time {report.p95_duration_ms:.2f}ms is too slow"

    async def test_concurrent_progress_queries(
        self,
        test_client,
        run_concurrent_timed,
        performance_thresholds,
        sample_task_data_factory
    ):
        """Test concurrent task progress queries (Redis-backed)"""
        num_tasks = performance_thresholds["max_concurrent_tasks"]

        # Create tasks
        task_ids = []
        for i in range(num_tasks):
            task_data = sample_task_data_factory(i)
            response = await test_client.post("/api/v1/tasks", json=task_data)
            task_ids.append(response.json()["task_id"])

        # Query progress concurrently
        async def query_progress(task_id):
            response = await test_client.get(f"/api/v1/tasks/{task_id}/progress")
            return response

        args_list = [(task_id,) for task_id in task_ids]
        results, report = await run_concurrent_timed(
            query_progress,
            args_list,
            operation="concurrent_progress_query"
        )

        successful_queries = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 200
        )

        print(f"\n=== Concurrent Progress Queries ({num_tasks} tasks) ===")
        print(f"Successful: {successful_queries}/{num_tasks}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")

        assert successful_queries == num_tasks
        # Progress queries should be very fast (Redis-backed)
        assert report.p95_duration_ms <= 500, \
            f"P95 progress query time {report.p95_duration_ms:.2f}ms is too slow"


@pytest.mark.performance
@pytest.mark.asyncio
class TestTaskDecompositionPerformance:
    """Test task decomposition performance"""

    async def test_concurrent_task_decomposition(
        self,
        test_client,
        run_concurrent_timed,
        sample_task_data_factory
    ):
        """Test decomposing multiple tasks concurrently"""
        num_tasks = 10

        # Create tasks
        task_ids = []
        for i in range(num_tasks):
            task_data = sample_task_data_factory(i)
            response = await test_client.post("/api/v1/tasks", json=task_data)
            task_ids.append(response.json()["task_id"])

        # Decompose concurrently
        async def decompose_task(task_id):
            response = await test_client.post(f"/api/v1/tasks/{task_id}/decompose")
            return response

        args_list = [(task_id,) for task_id in task_ids]
        results, report = await run_concurrent_timed(
            decompose_task,
            args_list,
            operation="concurrent_task_decomposition"
        )

        successful_decompositions = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 200
        )

        print(f"\n=== Concurrent Task Decomposition ({num_tasks} tasks) ===")
        print(f"Successful: {successful_decompositions}/{num_tasks}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")

        assert successful_decompositions == num_tasks
        # Decomposition should be reasonably fast
        assert report.p95_duration_ms <= 3000, \
            f"P95 decomposition time {report.p95_duration_ms:.2f}ms is too slow"

    async def test_sequential_decomposition_performance(
        self,
        test_client,
        perf_analyzer,
        sample_task_data_factory
    ):
        """Test sequential task decomposition to measure individual performance"""
        num_tasks = 5

        for i in range(num_tasks):
            # Create task
            task_data = sample_task_data_factory(i)
            response = await test_client.post("/api/v1/tasks", json=task_data)
            task_id = response.json()["task_id"]

            # Decompose with timing
            from tests.performance.conftest import PerformanceTimer
            with PerformanceTimer(f"decompose_task_{i}") as timer:
                response = await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

            assert response.status_code == 200
            perf_analyzer.add_metric(timer.get_metrics())

        report = perf_analyzer.generate_report()
        print(f"\n=== Sequential Task Decomposition ({num_tasks} tasks) ===")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"Min: {report.min_duration_ms:.2f}ms")
        print(f"Max: {report.max_duration_ms:.2f}ms")

        # Each decomposition should be fast
        assert report.avg_duration_ms <= 2000, \
            f"Average decomposition time {report.avg_duration_ms:.2f}ms is too slow"


@pytest.mark.performance
@pytest.mark.asyncio
class TestTaskListPerformanceUnderLoad:
    """Test task listing performance under various loads"""

    async def test_list_tasks_with_20_created(
        self,
        test_client,
        perf_timer,
        assert_performance,
        performance_thresholds,
        sample_task_data_factory
    ):
        """Test listing tasks with 20 tasks created"""
        num_tasks = performance_thresholds["max_concurrent_tasks"]

        # Create tasks
        for i in range(num_tasks):
            task_data = sample_task_data_factory(i)
            await test_client.post("/api/v1/tasks", json=task_data)

        # Test list performance
        with perf_timer("list_tasks_20") as timer:
            response = await test_client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == num_tasks

        print(f"\n=== List Tasks ({num_tasks} tasks) ===")
        print(f"Duration: {timer.duration_ms:.2f}ms")

        assert_performance(timer.duration_ms, 1000, "List tasks")

    async def test_list_tasks_with_100_created(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_task_data_factory
    ):
        """Test listing tasks with 100 tasks created"""
        num_tasks = 100

        # Create tasks (in batches for faster setup)
        for i in range(num_tasks):
            task_data = sample_task_data_factory(i)
            await test_client.post("/api/v1/tasks", json=task_data)

        # Test list performance with default limit (50)
        with perf_timer("list_tasks_100") as timer:
            response = await test_client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == num_tasks

        print(f"\n=== List Tasks ({num_tasks} tasks) ===")
        print(f"Duration: {timer.duration_ms:.2f}ms")
        print(f"Results in response: {len(data['tasks'])}")

        assert_performance(timer.duration_ms, 2000, "List tasks with 100 created")

    async def test_list_tasks_with_pagination(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_task_data_factory
    ):
        """Test task listing with pagination"""
        num_tasks = 50

        # Create tasks
        for i in range(num_tasks):
            task_data = sample_task_data_factory(i)
            await test_client.post("/api/v1/tasks", json=task_data)

        # Test paginated list performance
        with perf_timer("list_tasks_paginated") as timer:
            response = await test_client.get("/api/v1/tasks?limit=10&offset=20")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == num_tasks
        assert len(data["tasks"]) == 10

        print(f"\n=== List Tasks (paginated: 10 results) ===")
        print(f"Duration: {timer.duration_ms:.2f}ms")

        assert_performance(timer.duration_ms, 1000, "List tasks with pagination")

    async def test_list_tasks_with_filters(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_task_data_factory
    ):
        """Test listing tasks with status filter"""
        num_tasks = 30

        # Create tasks
        for i in range(num_tasks):
            task_data = sample_task_data_factory(i)
            await test_client.post("/api/v1/tasks", json=task_data)

        # Test filtered list performance
        with perf_timer("list_tasks_filtered") as timer:
            response = await test_client.get("/api/v1/tasks?status=pending")

        assert response.status_code == 200
        data = response.json()

        print(f"\n=== List Tasks (filtered: status=pending) ===")
        print(f"Duration: {timer.duration_ms:.2f}ms")
        print(f"Pending tasks: {data['total']}")

        assert_performance(timer.duration_ms, 1000, "List tasks with filter")


@pytest.mark.performance
@pytest.mark.asyncio
class TestMixedWorkloadPerformance:
    """Test performance under mixed workload (workers + tasks)"""

    async def test_mixed_worker_and_task_operations(
        self,
        test_client,
        perf_analyzer,
        sample_worker_data_factory,
        sample_task_data_factory
    ):
        """Test system performance with mixed worker and task operations"""
        num_workers = 5
        num_tasks = 10

        # Create workers and tasks concurrently
        async def create_worker(idx):
            from tests.performance.conftest import PerformanceTimer
            with PerformanceTimer(f"create_worker_{idx}") as timer:
                worker_data = sample_worker_data_factory(idx)
                response = await test_client.post("/api/v1/workers/register", json=worker_data)

            perf_analyzer.add_metric(timer.get_metrics())
            return response

        async def create_task(idx):
            from tests.performance.conftest import PerformanceTimer
            with PerformanceTimer(f"create_task_{idx}") as timer:
                task_data = sample_task_data_factory(idx)
                response = await test_client.post("/api/v1/tasks", json=task_data)

            perf_analyzer.add_metric(timer.get_metrics())
            return response

        # Run mixed workload
        worker_tasks = [create_worker(i) for i in range(num_workers)]
        task_tasks = [create_task(i) for i in range(num_tasks)]
        all_tasks = worker_tasks + task_tasks

        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Check results
        successful = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code in [200, 201]
        )

        report = perf_analyzer.generate_report()
        print(f"\n=== Mixed Workload ({num_workers} workers + {num_tasks} tasks) ===")
        print(f"Successful operations: {successful}/{num_workers + num_tasks}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")

        assert successful == num_workers + num_tasks, \
            f"Only {successful}/{num_workers + num_tasks} operations succeeded"
