"""
Performance monitoring module for EddyPro batch processing.

This module provides performance monitoring capabilities using psutil to track
CPU, memory, and I/O metrics during EddyPro subprocess execution.
"""

import csv
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Monitor system and process performance metrics during operations.

    Tracks CPU utilization, memory usage (RSS/peak), disk I/O, and wall-clock time
    with configurable sampling intervals. Produces both time series (CSV) and
    summary (JSON) outputs.
    """

    def __init__(
        self,
        interval_seconds: float = 0.5,
        output_dir: str | Path | None = None,
        scenario_suffix: str = "",
    ):
        """
        Initialize the performance monitor.

        Args:
            interval_seconds: Sampling interval in seconds (default: 0.5)
            output_dir: Directory to write metrics files (default: current directory)
            scenario_suffix: Suffix to append to output filenames for scenario runs

        Raises:
            ImportError: If psutil is not available
        """
        if not PSUTIL_AVAILABLE:
            raise ImportError(
                "psutil is required for performance monitoring. "
                "Install with: pip install psutil"
            )

        self.interval_seconds = max(0.1, interval_seconds)  # Minimum 0.1s
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.scenario_suffix = scenario_suffix

        # Monitoring state
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._start_time: float | None = None
        self._end_time: float | None = None

        # Data storage
        self._samples: list[dict[str, Any]] = []
        self._process: psutil.Process | None = None

        # Output file paths
        self._metrics_csv_path = self._get_output_path("metrics.csv")
        self._summary_json_path = self._get_output_path("metrics_summary.json")

    def _get_output_path(self, filename: str) -> Path:
        """Get output file path with optional scenario suffix."""
        if self.scenario_suffix:
            name, ext = filename.rsplit(".", 1)
            filename = f"{name}_{self.scenario_suffix}.{ext}"
        return self.output_dir / filename

    def start_monitoring(self, process_pid: int | None = None) -> None:
        """
        Start performance monitoring.

        Args:
            process_pid: PID of specific process to monitor. If None, monitors system.
        """
        if self._monitoring:
            logger.warning("Monitoring already active")
            return

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping performance monitoring")
            return

        self._monitoring = True
        self._start_time = time.time()
        self._samples.clear()

        # Set up process monitoring if PID provided
        if process_pid:
            try:
                self._process = psutil.Process(process_pid)
            except Exception:
                logger.warning(
                    f"Process {process_pid} not found, monitoring system instead"
                )
                self._process = None

        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="PerformanceMonitor"
        )
        self._monitor_thread.start()

        logger.info(
            f"Started performance monitoring (interval: {self.interval_seconds}s, "
            f"process: {process_pid or 'system'})"
        )

    def stop_monitoring(self) -> dict[str, Any]:
        """
        Stop performance monitoring and return summary.

        Returns:
            Dictionary containing monitoring summary and metrics
        """
        if not self._monitoring:
            logger.warning("Monitoring not active")
            return {}

        self._monitoring = False
        self._end_time = time.time()

        # Wait for monitor thread to finish
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)

        # Generate summary
        summary = self._generate_summary()

        # Write outputs
        self._write_metrics_csv()
        self._write_summary_json(summary)

        logger.info(
            f"Stopped performance monitoring. "
            f"Duration: {summary.get('duration_seconds', 0):.2f}s, "
            f"Samples: {len(self._samples)}"
        )

        return summary

    def _monitor_loop(self) -> None:
        """Main monitoring loop running in background thread."""
        while self._monitoring:
            try:
                sample = self._collect_sample()
                if sample:
                    self._samples.append(sample)
            except Exception as e:
                logger.warning(f"Error collecting performance sample: {e}")

            time.sleep(self.interval_seconds)

    def _collect_sample(self) -> dict[str, Any] | None:
        """
        Collect a single performance sample.

        Returns:
            Dictionary with timestamp and performance metrics, or None on error
        """
        try:
            timestamp = time.time()
            sample = {
                "timestamp": timestamp,
                "relative_time": timestamp - (self._start_time or timestamp),
            }

            # System-wide metrics
            sample.update(self._collect_system_metrics())

            # Process-specific metrics if available
            if self._process:
                process_metrics = self._collect_process_metrics()
                if process_metrics:
                    sample.update(process_metrics)

        except Exception as e:
            logger.debug(f"Failed to collect sample: {e}")
            return None
        else:
            return sample

    def _collect_system_metrics(self) -> dict[str, Any]:
        """Collect system-wide performance metrics."""
        metrics = {}

        try:
            # CPU utilization
            cpu_percent = psutil.cpu_percent(interval=0)
            metrics["system_cpu_percent"] = cpu_percent

            # Memory usage
            memory = psutil.virtual_memory()
            metrics["system_memory_total"] = memory.total
            metrics["system_memory_available"] = memory.available
            metrics["system_memory_percent"] = memory.percent

            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                metrics["system_disk_read_bytes"] = disk_io.read_bytes
                metrics["system_disk_write_bytes"] = disk_io.write_bytes
                metrics["system_disk_read_count"] = disk_io.read_count
                metrics["system_disk_write_count"] = disk_io.write_count

            # Network I/O (optional)
            try:
                network_io = psutil.net_io_counters()
                if network_io:
                    metrics["system_network_bytes_sent"] = network_io.bytes_sent
                    metrics["system_network_bytes_recv"] = network_io.bytes_recv
            except AttributeError:
                pass  # Network counters not available on all systems

        except Exception as e:
            logger.debug(f"Error collecting system metrics: {e}")

        return metrics

    def _collect_process_metrics(self) -> dict[str, Any] | None:
        """Collect process-specific performance metrics."""
        if not self._process:
            return None

        try:
            # Check if process still exists
            if not self._process.is_running():
                logger.debug("Monitored process no longer running")
                self._process = None
                return None

            metrics = {}

            # CPU usage
            try:
                cpu_percent = self._process.cpu_percent()
                metrics["process_cpu_percent"] = cpu_percent
            except Exception:  # nosec B110
                pass

            # Memory usage
            try:
                memory_info = self._process.memory_info()
                metrics["process_memory_rss"] = memory_info.rss
                metrics["process_memory_vms"] = memory_info.vms

                # Memory percent
                memory_percent = self._process.memory_percent()
                metrics["process_memory_percent"] = memory_percent
            except Exception:  # nosec B110
                pass

            # I/O counters
            try:
                io_counters = self._process.io_counters()
                metrics["process_io_read_bytes"] = io_counters.read_bytes
                metrics["process_io_write_bytes"] = io_counters.write_bytes
                metrics["process_io_read_count"] = io_counters.read_count
                metrics["process_io_write_count"] = io_counters.write_count
            except Exception:  # nosec B110
                pass  # I/O counters not available on all platforms

        except Exception:
            logger.debug("Error collecting process metrics")
            self._process = None
            return None
        else:
            return metrics

    def _generate_summary(self) -> dict[str, Any]:
        """Generate summary statistics from collected samples."""
        if not self._samples:
            return {"error": "No samples collected"}

        summary = {
            "monitoring_config": {
                "interval_seconds": self.interval_seconds,
                "scenario_suffix": self.scenario_suffix,
                "output_dir": str(self.output_dir),
            },
            "timing": {
                "start_time": self._start_time,
                "end_time": self._end_time,
                "duration_seconds": (self._end_time or 0) - (self._start_time or 0),
            },
            "samples": {
                "count": len(self._samples),
                "first_timestamp": self._samples[0]["timestamp"],
                "last_timestamp": self._samples[-1]["timestamp"],
            },
            "metrics": {},
        }

        # Calculate statistics for each numeric metric
        numeric_fields = self._get_numeric_fields()
        metrics_dict: dict[str, dict[str, float]] = {}
        for field in numeric_fields:
            values = [
                s[field] for s in self._samples if field in s and s[field] is not None
            ]
            if values:
                metrics_dict[field] = self._calculate_stats(values)
        summary["metrics"] = metrics_dict

        return summary

    def _get_numeric_fields(self) -> list[str]:
        """Get list of numeric field names from samples."""
        if not self._samples:
            return []

        numeric_fields = []
        for key, value in self._samples[0].items():
            if key in ["timestamp", "relative_time"]:
                continue
            if isinstance(value, int | float):
                numeric_fields.append(key)

        return numeric_fields

    def _calculate_stats(self, values: list[int | float]) -> dict[str, float]:
        """Calculate min, max, mean, and percentiles for a list of values."""
        if not values:
            return {}

        values = sorted(values)
        n = len(values)

        stats = {
            "min": float(min(values)),
            "max": float(max(values)),
            "mean": sum(values) / n,
            "count": n,
        }

        # Percentiles
        if n >= 2:
            stats["p50"] = self._percentile(values, 0.5)
            stats["p90"] = self._percentile(values, 0.9)
            stats["p95"] = self._percentile(values, 0.95)

        return stats

    def _percentile(self, values: list[int | float], p: float) -> float:
        """Calculate percentile from sorted values."""
        if not values:
            return 0.0

        index = p * (len(values) - 1)
        if index.is_integer():
            return float(values[int(index)])
        else:
            lower = int(index)
            upper = lower + 1
            weight = index - lower
            return float(values[lower] * (1 - weight) + values[upper] * weight)

    def _write_metrics_csv(self) -> None:
        """Write time series metrics to CSV file."""
        if not self._samples:
            logger.warning("No samples to write to CSV")
            return

        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Get all possible field names
            all_fields: set[str] = set()
            for sample in self._samples:
                all_fields.update(sample.keys())

            # Sort fields for consistent output
            fieldnames = sorted(all_fields)

            with open(
                self._metrics_csv_path, "w", newline="", encoding="utf-8"
            ) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self._samples)

            logger.info(
                f"Wrote {len(self._samples)} samples to {self._metrics_csv_path}"
            )

        except Exception:
            logger.exception("Failed to write metrics CSV")

    def _write_summary_json(self, summary: dict[str, Any]) -> None:
        """Write summary statistics to JSON file."""
        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            with open(self._summary_json_path, "w", encoding="utf-8") as jsonfile:
                json.dump(summary, jsonfile, indent=2, default=str)

            logger.info(f"Wrote summary to {self._summary_json_path}")

        except Exception:
            logger.exception("Failed to write summary JSON")

    @property
    def metrics_csv_path(self) -> Path:
        """Path to the metrics CSV file."""
        return self._metrics_csv_path

    @property
    def summary_json_path(self) -> Path:
        """Path to the summary JSON file."""
        return self._summary_json_path

    @property
    def is_monitoring(self) -> bool:
        """Whether monitoring is currently active."""
        return self._monitoring

    @property
    def sample_count(self) -> int:
        """Number of samples collected so far."""
        return len(self._samples)


def create_monitor(
    interval_seconds: float = 0.5,
    output_dir: str | Path | None = None,
    scenario_suffix: str = "",
) -> PerformanceMonitor | None:
    """
    Create a performance monitor instance with error handling.

    Args:
        interval_seconds: Sampling interval in seconds (default: 0.5)
        output_dir: Directory to write metrics files
        scenario_suffix: Suffix for scenario-specific output files

    Returns:
        PerformanceMonitor instance, or None if psutil is not available
    """
    if not PSUTIL_AVAILABLE:
        logger.warning(
            "psutil not available, performance monitoring disabled. "
            "Install with: pip install psutil"
        )
        return None

    try:
        return PerformanceMonitor(
            interval_seconds=interval_seconds,
            output_dir=output_dir,
            scenario_suffix=scenario_suffix,
        )
    except ImportError as e:
        logger.warning(f"Failed to create performance monitor: {e}")
        return None


# Context manager for convenient monitoring
class MonitoredOperation:
    """
    Context manager for monitoring operations.

    Example:
        with MonitoredOperation(output_dir="./metrics") as monitor:
            # ... run expensive operation ...
            pass
        # Metrics are automatically saved
    """

    def __init__(
        self,
        interval_seconds: float = 0.5,
        output_dir: str | Path | None = None,
        scenario_suffix: str = "",
        process_pid: int | None = None,
    ):
        """Initialize monitored operation context."""
        self.monitor = create_monitor(interval_seconds, output_dir, scenario_suffix)
        self.process_pid = process_pid
        self.summary: dict[str, Any] = {}

    def __enter__(self) -> PerformanceMonitor | None:
        """Enter monitoring context."""
        if self.monitor:
            self.monitor.start_monitoring(self.process_pid)
        return self.monitor

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit monitoring context and save results."""
        if self.monitor:
            self.summary = self.monitor.stop_monitoring()
