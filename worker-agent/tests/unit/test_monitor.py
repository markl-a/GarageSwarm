"""Unit tests for ResourceMonitor"""

import pytest
from src.agent.monitor import ResourceMonitor


@pytest.mark.unit
def test_resource_monitor_initialization():
    """Test ResourceMonitor can be initialized"""
    monitor = ResourceMonitor()
    assert monitor is not None


@pytest.mark.unit
def test_get_resources():
    """Test getting current resource usage"""
    monitor = ResourceMonitor()
    resources = monitor.get_resources()

    assert "cpu_percent" in resources
    assert "memory_percent" in resources
    assert "disk_percent" in resources

    # Verify values are reasonable
    assert 0 <= resources["cpu_percent"] <= 100
    assert 0 <= resources["memory_percent"] <= 100
    assert 0 <= resources["disk_percent"] <= 100


@pytest.mark.unit
def test_get_system_info():
    """Test getting system information"""
    monitor = ResourceMonitor()
    system_info = monitor.get_system_info()

    required_keys = [
        "os", "os_version", "cpu_count",
        "memory_total", "memory_total_gb",
        "python_version"
    ]

    for key in required_keys:
        assert key in system_info, f"Missing key: {key}"

    # Verify data types
    assert isinstance(system_info["cpu_count"], int)
    assert system_info["cpu_count"] > 0
    assert isinstance(system_info["memory_total"], int)
    assert system_info["memory_total"] > 0


@pytest.mark.unit
def test_check_resource_thresholds():
    """Test checking resource thresholds"""
    monitor = ResourceMonitor()
    result = monitor.check_resource_thresholds(
        cpu_threshold=90,
        memory_threshold=85,
        disk_threshold=90
    )

    assert "cpu_exceeded" in result
    assert "memory_exceeded" in result
    assert "disk_exceeded" in result
    assert "any_exceeded" in result

    assert isinstance(result["cpu_exceeded"], bool)
    assert isinstance(result["memory_exceeded"], bool)
    assert isinstance(result["disk_exceeded"], bool)


@pytest.mark.unit
def test_get_detailed_status():
    """Test getting detailed system status"""
    monitor = ResourceMonitor()
    status = monitor.get_detailed_status()

    assert "resources" in status
    assert "memory" in status
    assert "disk" in status
    assert "cpu" in status

    # Verify memory details
    memory = status["memory"]
    assert "total" in memory
    assert "available" in memory
    assert "percent" in memory
