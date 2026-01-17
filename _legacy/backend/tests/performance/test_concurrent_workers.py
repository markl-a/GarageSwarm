"""
Concurrent Workers Performance Tests

Test system performance with multiple workers:
- 10 workers simultaneous registration
- 10 workers simultaneous heartbeats
- High concurrency scenarios
"""

import pytest
import asyncio


@pytest.mark.performance
@pytest.mark.asyncio
class TestConcurrentWorkerRegistration:
    """Test concurrent worker registration performance"""

    async def test_10_workers_concurrent_registration(
        self,
        test_client,
        run_concurrent_timed,
        performance_thresholds,
        sample_worker_data_factory
    ):
        """Test 10 workers registering simultaneously (NFR requirement)"""
        num_workers = performance_thresholds["max_concurrent_workers"]

        # Prepare worker registration coroutines
        async def register_worker(worker_data):
            response = await test_client.post("/api/v1/workers/register", json=worker_data)
            return response

        # Generate worker data for all workers
        args_list = [(sample_worker_data_factory(i),) for i in range(num_workers)]

        # Run concurrent registrations
        results, report = await run_concurrent_timed(
            register_worker,
            args_list,
            operation="concurrent_worker_registration"
        )

        # Verify all workers registered successfully
        successful_registrations = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 200
        )

        print(f"\n=== Concurrent Worker Registration ({num_workers} workers) ===")
        print(f"Successful: {successful_registrations}/{num_workers}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")
        print(f"Max: {report.max_duration_ms:.2f}ms")

        assert successful_registrations == num_workers, \
            f"Only {successful_registrations}/{num_workers} workers registered successfully"

        # Each worker registration should complete within threshold
        assert report.p95_duration_ms <= performance_thresholds["worker_registration_ms"], \
            f"P95 registration time {report.p95_duration_ms:.2f}ms exceeds {performance_thresholds['worker_registration_ms']}ms"

    async def test_20_workers_concurrent_registration(
        self,
        test_client,
        run_concurrent_timed,
        performance_thresholds,
        sample_worker_data_factory
    ):
        """Test 20 workers registering simultaneously (stress test)"""
        num_workers = 20

        async def register_worker(worker_data):
            response = await test_client.post("/api/v1/workers/register", json=worker_data)
            return response

        args_list = [(sample_worker_data_factory(i),) for i in range(num_workers)]

        results, report = await run_concurrent_timed(
            register_worker,
            args_list,
            operation="concurrent_worker_registration_stress"
        )

        successful_registrations = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 200
        )

        print(f"\n=== Stress Test: Concurrent Worker Registration ({num_workers} workers) ===")
        print(f"Successful: {successful_registrations}/{num_workers}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")
        print(f"P99: {report.p99_duration_ms:.2f}ms")

        # Should still handle 20 workers gracefully
        assert successful_registrations >= num_workers * 0.95, \
            f"Less than 95% success rate: {successful_registrations}/{num_workers}"


@pytest.mark.performance
@pytest.mark.asyncio
class TestConcurrentWorkerHeartbeat:
    """Test concurrent worker heartbeat performance"""

    async def test_10_workers_concurrent_heartbeat(
        self,
        test_client,
        run_concurrent_timed,
        performance_thresholds,
        sample_worker_data_factory
    ):
        """Test 10 workers sending heartbeats simultaneously"""
        num_workers = performance_thresholds["max_concurrent_workers"]

        # First, register all workers
        worker_ids = []
        for i in range(num_workers):
            worker_data = sample_worker_data_factory(i)
            response = await test_client.post("/api/v1/workers/register", json=worker_data)
            assert response.status_code == 200
            worker_ids.append(response.json()["worker_id"])

        # Prepare heartbeat coroutines
        async def send_heartbeat(worker_id):
            heartbeat_data = {
                "status": "online",
                "resources": {
                    "cpu_percent": 45.5,
                    "memory_percent": 60.0,
                    "disk_percent": 70.0
                }
            }
            response = await test_client.post(
                f"/api/v1/workers/{worker_id}/heartbeat",
                json=heartbeat_data
            )
            return response

        # Run concurrent heartbeats
        args_list = [(worker_id,) for worker_id in worker_ids]
        results, report = await run_concurrent_timed(
            send_heartbeat,
            args_list,
            operation="concurrent_worker_heartbeat"
        )

        successful_heartbeats = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 200
        )

        print(f"\n=== Concurrent Worker Heartbeat ({num_workers} workers) ===")
        print(f"Successful: {successful_heartbeats}/{num_workers}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")

        assert successful_heartbeats == num_workers, \
            f"Only {successful_heartbeats}/{num_workers} heartbeats succeeded"

        # Heartbeats should be very fast
        assert report.p95_duration_ms <= 1000, \
            f"P95 heartbeat time {report.p95_duration_ms:.2f}ms is too slow"

    async def test_sustained_heartbeat_load(
        self,
        test_client,
        perf_analyzer,
        performance_thresholds,
        sample_worker_data_factory
    ):
        """Test sustained heartbeat load (10 workers, 5 heartbeats each)"""
        num_workers = performance_thresholds["max_concurrent_workers"]
        heartbeats_per_worker = 5

        # Register workers
        worker_ids = []
        for i in range(num_workers):
            worker_data = sample_worker_data_factory(i)
            response = await test_client.post("/api/v1/workers/register", json=worker_data)
            worker_ids.append(response.json()["worker_id"])

        # Send sustained heartbeats
        async def worker_heartbeat_sequence(worker_id, worker_idx):
            """Send multiple heartbeats from one worker"""
            for heartbeat_num in range(heartbeats_per_worker):
                heartbeat_data = {
                    "status": "online",
                    "resources": {
                        "cpu_percent": 45.5 + heartbeat_num,
                        "memory_percent": 60.0,
                        "disk_percent": 70.0
                    }
                }

                from tests.performance.conftest import PerformanceTimer
                with PerformanceTimer(f"heartbeat_w{worker_idx}_h{heartbeat_num}") as timer:
                    response = await test_client.post(
                        f"/api/v1/workers/{worker_id}/heartbeat",
                        json=heartbeat_data
                    )

                perf_analyzer.add_metric(timer.get_metrics())
                assert response.status_code == 200

                # Small delay between heartbeats
                await asyncio.sleep(0.1)

        # Run all workers concurrently
        tasks = [
            worker_heartbeat_sequence(worker_id, idx)
            for idx, worker_id in enumerate(worker_ids)
        ]
        await asyncio.gather(*tasks)

        # Analyze performance
        report = perf_analyzer.generate_report()
        total_heartbeats = num_workers * heartbeats_per_worker

        print(f"\n=== Sustained Heartbeat Load ({total_heartbeats} heartbeats) ===")
        print(f"Workers: {num_workers}")
        print(f"Heartbeats per worker: {heartbeats_per_worker}")
        print(f"Average: {report.avg_duration_ms:.2f}ms")
        print(f"P95: {report.p95_duration_ms:.2f}ms")
        print(f"P99: {report.p99_duration_ms:.2f}ms")

        # Performance should remain stable under sustained load
        assert report.p95_duration_ms <= 1000, \
            f"P95 {report.p95_duration_ms:.2f}ms exceeds 1000ms under sustained load"


@pytest.mark.performance
@pytest.mark.asyncio
class TestWorkerListPerformanceUnderLoad:
    """Test worker listing performance under various loads"""

    async def test_list_workers_with_10_registered(
        self,
        test_client,
        perf_timer,
        assert_performance,
        performance_thresholds,
        sample_worker_data_factory
    ):
        """Test listing workers with 10 workers registered"""
        num_workers = performance_thresholds["max_concurrent_workers"]

        # Register workers
        for i in range(num_workers):
            worker_data = sample_worker_data_factory(i)
            await test_client.post("/api/v1/workers/register", json=worker_data)

        # Test list performance
        with perf_timer("list_workers_10") as timer:
            response = await test_client.get("/api/v1/workers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == num_workers

        print(f"\n=== List Workers ({num_workers} workers) ===")
        print(f"Duration: {timer.duration_ms:.2f}ms")

        assert_performance(timer.duration_ms, 1000, "List workers")

    async def test_list_workers_with_50_registered(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_worker_data_factory
    ):
        """Test listing workers with 50 workers registered"""
        num_workers = 50

        # Register workers
        for i in range(num_workers):
            worker_data = sample_worker_data_factory(i)
            await test_client.post("/api/v1/workers/register", json=worker_data)

        # Test list performance with default limit
        with perf_timer("list_workers_50") as timer:
            response = await test_client.get("/api/v1/workers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == num_workers

        print(f"\n=== List Workers ({num_workers} workers) ===")
        print(f"Duration: {timer.duration_ms:.2f}ms")
        print(f"Results in response: {len(data['workers'])}")

        assert_performance(timer.duration_ms, 2000, "List workers with 50 registered")

    async def test_list_workers_with_filters(
        self,
        test_client,
        perf_timer,
        assert_performance,
        sample_worker_data_factory
    ):
        """Test listing workers with status filter"""
        num_workers = 20

        # Register workers
        worker_ids = []
        for i in range(num_workers):
            worker_data = sample_worker_data_factory(i)
            response = await test_client.post("/api/v1/workers/register", json=worker_data)
            worker_ids.append(response.json()["worker_id"])

        # Send heartbeat to some workers to make them "online"
        for i in range(10):
            heartbeat_data = {
                "status": "online",
                "resources": {
                    "cpu_percent": 45.5,
                    "memory_percent": 60.0,
                    "disk_percent": 70.0
                }
            }
            await test_client.post(
                f"/api/v1/workers/{worker_ids[i]}/heartbeat",
                json=heartbeat_data
            )

        # Test filtered list performance
        with perf_timer("list_workers_filtered") as timer:
            response = await test_client.get("/api/v1/workers?status=online")

        assert response.status_code == 200
        data = response.json()

        print(f"\n=== List Workers (filtered: status=online) ===")
        print(f"Duration: {timer.duration_ms:.2f}ms")
        print(f"Online workers: {data['total']}")

        assert_performance(timer.duration_ms, 1000, "List workers with filter")
