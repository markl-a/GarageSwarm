"""Resource monitoring for worker agents"""

import platform
from typing import Dict, Any
import psutil


class ResourceMonitor:
    """Monitor system resources (CPU, Memory, Disk)"""

    def __init__(self):
        """Initialize resource monitor"""
        pass

    def get_resources(self) -> Dict[str, float]:
        """Get current resource usage

        Returns:
            Dictionary with cpu_percent, memory_percent, disk_percent
        """
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information

        Returns:
            Dictionary with OS, CPU, memory, Python version info
        """
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "cpu_count": psutil.cpu_count(),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "memory_total": memory.total,
            "memory_total_gb": round(memory.total / (1024 ** 3), 2),
            "disk_total": disk.total,
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation()
        }

    def check_resource_thresholds(
        self,
        cpu_threshold: float = 90.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0
    ) -> Dict[str, Any]:
        """Check if resource usage exceeds thresholds

        Args:
            cpu_threshold: CPU usage threshold percentage (default 90%)
            memory_threshold: Memory usage threshold percentage (default 85%)
            disk_threshold: Disk usage threshold percentage (default 90%)

        Returns:
            Dictionary with exceeded flags and current values
        """
        resources = self.get_resources()

        return {
            "cpu_exceeded": resources["cpu_percent"] > cpu_threshold,
            "memory_exceeded": resources["memory_percent"] > memory_threshold,
            "disk_exceeded": resources["disk_percent"] > disk_threshold,
            "cpu_percent": resources["cpu_percent"],
            "memory_percent": resources["memory_percent"],
            "disk_percent": resources["disk_percent"],
            "any_exceeded": (
                resources["cpu_percent"] > cpu_threshold or
                resources["memory_percent"] > memory_threshold or
                resources["disk_percent"] > disk_threshold
            )
        }

    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed system status

        Returns:
            Comprehensive system status including resources and info
        """
        resources = self.get_resources()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "resources": resources,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "free": memory.free,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "cpu": {
                "percent": resources["cpu_percent"],
                "count": psutil.cpu_count(),
                "count_physical": psutil.cpu_count(logical=False)
            }
        }
