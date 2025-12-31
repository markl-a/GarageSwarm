"""Resource monitoring for worker agents"""

import platform
from typing import Dict, Any
import psutil
import structlog

logger = structlog.get_logger()


class ResourceMonitor:
    """Monitor system resources (CPU, Memory, Disk)"""

    def __init__(self):
        """Initialize resource monitor"""
        self.is_windows = platform.system() == "Windows"
        # Determine the root path for disk monitoring
        if self.is_windows:
            # On Windows, use C: drive by default
            self.disk_path = "C:\\"
        else:
            # On Unix-like systems, use root
            self.disk_path = '/'

        logger.debug(
            "ResourceMonitor initialized",
            platform=platform.system(),
            disk_path=self.disk_path
        )

    def get_resources(self) -> Dict[str, float]:
        """Get current resource usage

        Returns:
            Dictionary with cpu_percent, memory_percent, disk_percent
        """
        try:
            # Get CPU usage (cross-platform)
            cpu_percent = psutil.cpu_percent(interval=1)

            # Get memory usage (cross-platform)
            memory_percent = psutil.virtual_memory().percent

            # Get disk usage (platform-aware)
            try:
                disk_percent = psutil.disk_usage(self.disk_path).percent
            except (OSError, PermissionError) as e:
                logger.warning(
                    "Failed to get disk usage, using fallback",
                    path=self.disk_path,
                    error=str(e)
                )
                # Fallback: try to get any available disk
                disk_percent = self._get_fallback_disk_usage()

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent
            }
        except Exception as e:
            logger.error("Failed to get resource usage", error=str(e))
            # Return default values on error
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "disk_percent": 0.0
            }

    def _get_fallback_disk_usage(self) -> float:
        """Get disk usage from first available partition

        Returns:
            Disk usage percentage or 0.0 if unavailable
        """
        try:
            partitions = psutil.disk_partitions()
            if partitions:
                # Use the first available partition
                first_partition = partitions[0].mountpoint
                return psutil.disk_usage(first_partition).percent
        except Exception as e:
            logger.debug("Failed to get fallback disk usage", error=str(e))

        return 0.0

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information

        Returns:
            Dictionary with OS, CPU, memory, Python version info
        """
        try:
            memory = psutil.virtual_memory()

            # Get disk info with platform-aware path
            try:
                disk = psutil.disk_usage(self.disk_path)
            except (OSError, PermissionError):
                # Fallback to first available partition
                partitions = psutil.disk_partitions()
                if partitions:
                    disk = psutil.disk_usage(partitions[0].mountpoint)
                else:
                    # Create dummy disk info if no partitions available
                    disk = type('obj', (object,), {'total': 0, 'used': 0, 'free': 0})()

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
                "disk_total_gb": round(disk.total / (1024 ** 3), 2) if disk.total > 0 else 0.0,
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "is_windows": self.is_windows,
                "disk_path": self.disk_path
            }
        except Exception as e:
            logger.error("Failed to get system info", error=str(e))
            # Return minimal system info on error
            return {
                "os": platform.system(),
                "os_version": "unknown",
                "os_release": "unknown",
                "machine": platform.machine(),
                "cpu_count": 0,
                "cpu_count_physical": 0,
                "memory_total": 0,
                "memory_total_gb": 0.0,
                "disk_total": 0,
                "disk_total_gb": 0.0,
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "is_windows": self.is_windows,
                "disk_path": self.disk_path
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
        try:
            resources = self.get_resources()
            memory = psutil.virtual_memory()

            # Get disk info with platform-aware path
            try:
                disk = psutil.disk_usage(self.disk_path)
            except (OSError, PermissionError):
                # Fallback to first available partition
                partitions = psutil.disk_partitions()
                if partitions:
                    disk = psutil.disk_usage(partitions[0].mountpoint)
                else:
                    # Create dummy disk info
                    disk = type('obj', (object,), {
                        'total': 0, 'used': 0, 'free': 0, 'percent': 0.0
                    })()

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
                    "path": self.disk_path,
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "cpu": {
                    "percent": resources["cpu_percent"],
                    "count": psutil.cpu_count(),
                    "count_physical": psutil.cpu_count(logical=False)
                },
                "platform": {
                    "system": platform.system(),
                    "is_windows": self.is_windows
                }
            }
        except Exception as e:
            logger.error("Failed to get detailed status", error=str(e))
            # Return minimal status on error
            return {
                "resources": {"cpu_percent": 0.0, "memory_percent": 0.0, "disk_percent": 0.0},
                "memory": {"total": 0, "available": 0, "used": 0, "free": 0, "percent": 0.0},
                "disk": {"path": self.disk_path, "total": 0, "used": 0, "free": 0, "percent": 0.0},
                "cpu": {"percent": 0.0, "count": 0, "count_physical": 0},
                "platform": {"system": platform.system(), "is_windows": self.is_windows}
            }
