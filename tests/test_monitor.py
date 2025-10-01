"""
Unit tests for the performance monitoring module.

Tests the PerformanceMonitor class and related functionality with mocked
dependencies to ensure deterministic behavior.
"""

import itertools
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    import psutil as psutil_module
except ImportError:
    psutil_module = None

from eddypro_batch_processor.monitor import (
    MonitoredOperation,
    PerformanceMonitor,
    create_monitor,
)


class TestPerformanceMonitor:
    """Test cases for the PerformanceMonitor class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_psutil(self):
        """Mock psutil module for testing."""
        with patch("eddypro_batch_processor.monitor.psutil") as mock_psutil, patch(
            "eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", True
        ):
            # Mock system metrics
            mock_psutil.cpu_percent.return_value = 50.0
            mock_memory = MagicMock()
            mock_memory.total = 8 * 1024**3  # 8GB
            mock_memory.available = 4 * 1024**3  # 4GB
            mock_memory.percent = 50.0
            mock_psutil.virtual_memory.return_value = mock_memory

            mock_disk_io = MagicMock()
            mock_disk_io.read_bytes = 1000000
            mock_disk_io.write_bytes = 500000
            mock_disk_io.read_count = 100
            mock_disk_io.write_count = 50
            mock_psutil.disk_io_counters.return_value = mock_disk_io

            mock_network_io = MagicMock()
            mock_network_io.bytes_sent = 10000
            mock_network_io.bytes_recv = 20000
            mock_psutil.net_io_counters.return_value = mock_network_io

            # Mock process
            mock_process = MagicMock()
            mock_process.is_running.return_value = True
            mock_process.cpu_percent.return_value = 25.0
            mock_process.memory_percent.return_value = 10.0
            mock_memory_info = MagicMock()
            mock_memory_info.rss = 100 * 1024**2  # 100MB
            mock_memory_info.vms = 200 * 1024**2  # 200MB
            mock_process.memory_info.return_value = mock_memory_info

            mock_io_counters = MagicMock()
            mock_io_counters.read_bytes = 50000
            mock_io_counters.write_bytes = 25000
            mock_io_counters.read_count = 10
            mock_io_counters.write_count = 5
            mock_process.io_counters.return_value = mock_io_counters

            mock_psutil.Process.return_value = mock_process

            yield mock_psutil

    def test_monitor_initialization(self, temp_dir):
        """Test monitor initialization with default and custom parameters."""
        # Test default initialization
        monitor = PerformanceMonitor(output_dir=temp_dir)
        assert monitor.interval_seconds == 0.5
        assert monitor.output_dir == temp_dir
        assert monitor.scenario_suffix == ""
        assert not monitor.is_monitoring
        assert monitor.sample_count == 0

        # Test custom initialization
        monitor = PerformanceMonitor(
            interval_seconds=1.0, output_dir=temp_dir, scenario_suffix="test"
        )
        assert monitor.interval_seconds == 1.0
        assert monitor.scenario_suffix == "test"

        # Test minimum interval enforcement
        monitor = PerformanceMonitor(interval_seconds=0.05, output_dir=temp_dir)
        assert monitor.interval_seconds == 0.1  # Should be clamped to minimum

    def test_monitor_without_psutil(self, temp_dir):
        """Test monitor behavior when psutil is not available."""
        with patch(
            "eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", False
        ), pytest.raises(ImportError, match="psutil is required"):
            PerformanceMonitor(output_dir=temp_dir)

    def test_create_monitor_without_psutil(self, temp_dir):
        """Test create_monitor function when psutil is not available."""
        with patch("eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", False):
            monitor = create_monitor(output_dir=temp_dir)
            assert monitor is None

    def test_output_path_generation(self, temp_dir):
        """Test output file path generation with and without scenario suffix."""
        # Without suffix
        monitor = PerformanceMonitor(output_dir=temp_dir)
        assert monitor.metrics_csv_path == temp_dir / "metrics.csv"
        assert monitor.summary_json_path == temp_dir / "metrics_summary.json"

        # With suffix
        monitor = PerformanceMonitor(output_dir=temp_dir, scenario_suffix="rot1_tlag2")
        assert monitor.metrics_csv_path == temp_dir / "metrics_rot1_tlag2.csv"
        assert monitor.summary_json_path == temp_dir / "metrics_summary_rot1_tlag2.json"

    @patch("time.time")
    def test_sample_collection(self, mock_time, temp_dir, mock_psutil):
        """Test performance sample collection."""
        # Set up predictable timestamps - provide enough values for multiple calls
        mock_time.side_effect = [1000.0, 1000.5, 1001.0, 1001.5, 1002.0]

        monitor = PerformanceMonitor(output_dir=temp_dir)
        monitor._start_time = 1000.0

        # Test system metrics collection
        sample = monitor._collect_sample()
        assert sample is not None
        # First call to time.time() in _collect_sample
        assert sample["timestamp"] == 1000.0
        assert sample["relative_time"] == 0.0
        assert sample["system_cpu_percent"] == 50.0
        assert sample["system_memory_percent"] == 50.0
        assert sample["system_disk_read_bytes"] == 1000000

    @patch("time.time")
    def test_process_monitoring(self, mock_time, temp_dir, mock_psutil):
        """Test process-specific monitoring."""
        mock_time.side_effect = [1000.0, 1000.5, 1001.0, 1001.5]

        monitor = PerformanceMonitor(output_dir=temp_dir)

        # Set up process monitoring (without starting full monitoring)
        try:
            monitor._process = mock_psutil.Process.return_value
            monitor._start_time = 1000.0
        except Exception:
            # If mocking fails, manually set up the process object
            monitor._process = mock_psutil.Process(1234)
            monitor._start_time = 1000.0

        # Collect sample with process metrics
        sample = monitor._collect_sample()
        assert sample is not None
        assert "process_cpu_percent" in sample
        assert "process_memory_rss" in sample
        assert sample["process_cpu_percent"] == 25.0

    def test_process_not_found(self, temp_dir, mock_psutil):
        """Test handling of non-existent process."""
        # Mock NoSuchProcess exception
        if psutil_module:
            mock_psutil.Process.side_effect = psutil_module.NoSuchProcess(9999)
        else:
            # Create a mock exception for testing
            class MockNoSuchProcessError(Exception):
                def __init__(self, pid):
                    self.pid = pid

            mock_psutil.Process.side_effect = MockNoSuchProcessError(9999)

        monitor = PerformanceMonitor(output_dir=temp_dir)
        monitor.start_monitoring(process_pid=9999)

        # Should fall back to system monitoring
        assert monitor._process is None

    @patch("time.sleep")
    @patch("time.time")
    def test_monitoring_lifecycle(self, mock_time, mock_sleep, temp_dir, mock_psutil):
        """Test complete monitoring lifecycle."""
        # Mock timestamps - use itertools.cycle for unlimited values
        timestamps = [1000.0, 1000.5, 1001.0, 1001.5, 1002.0, 1002.5, 1003.0, 1003.5]
        mock_time.side_effect = itertools.cycle(timestamps)

        monitor = PerformanceMonitor(interval_seconds=0.1, output_dir=temp_dir)

        # Start monitoring
        monitor.start_monitoring()
        assert monitor.is_monitoring
        assert monitor._monitor_thread is not None

        # Let the monitoring run briefly (mock sleep to prevent actual delay)
        mock_sleep.return_value = None

        # Stop monitoring quickly to avoid too many mock calls
        summary = monitor.stop_monitoring()
        assert not monitor.is_monitoring
        assert "timing" in summary
        assert "duration_seconds" in summary["timing"]
        assert "samples" in summary

        # Check that files are created
        assert monitor.metrics_csv_path.exists()
        assert monitor.summary_json_path.exists()

    def test_statistics_calculation(self, temp_dir, mock_psutil):
        """Test statistics calculation from samples."""
        monitor = PerformanceMonitor(output_dir=temp_dir)

        # Test percentile calculation
        values = [1, 2, 3, 4, 5]
        p50 = monitor._percentile(values, 0.5)
        assert p50 == 3.0

        p90 = monitor._percentile(values, 0.9)
        assert p90 == 4.6  # Interpolated value

        # Test stats calculation
        stats = monitor._calculate_stats(values)
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["mean"] == 3.0
        assert stats["count"] == 5
        assert "p50" in stats
        assert "p90" in stats

    def test_empty_samples_handling(self, temp_dir, mock_psutil):
        """Test handling of empty samples."""
        monitor = PerformanceMonitor(output_dir=temp_dir)

        # No samples collected
        summary = monitor._generate_summary()
        assert "error" in summary

        # Empty values
        stats = monitor._calculate_stats([])
        assert stats == {}

        percentile = monitor._percentile([], 0.5)
        assert percentile == 0.0

    @patch("time.time")
    def test_csv_output_format(self, mock_time, temp_dir, mock_psutil):
        """Test CSV output format and content."""
        mock_time.side_effect = [1000.0, 1000.5, 1001.0]

        monitor = PerformanceMonitor(output_dir=temp_dir)
        monitor._start_time = 1000.0

        # Collect some samples
        sample1 = monitor._collect_sample()
        sample2 = monitor._collect_sample()
        monitor._samples = [sample1, sample2]

        # Write CSV
        monitor._write_metrics_csv()

        # Check CSV content
        assert monitor.metrics_csv_path.exists()
        with open(monitor.metrics_csv_path) as f:
            content = f.read()
            assert "timestamp" in content
            assert "system_cpu_percent" in content

    def test_json_output_format(self, temp_dir, mock_psutil):
        """Test JSON summary output format."""
        monitor = PerformanceMonitor(output_dir=temp_dir)

        summary = {
            "monitoring_config": {"interval_seconds": 0.5},
            "timing": {"duration_seconds": 2.0},
            "samples": {"count": 4},
            "metrics": {"system_cpu_percent": {"min": 10.0, "max": 90.0}},
        }

        monitor._write_summary_json(summary)

        # Check JSON content
        assert monitor.summary_json_path.exists()
        with open(monitor.summary_json_path) as f:
            loaded = json.load(f)
            assert loaded["timing"]["duration_seconds"] == 2.0
            assert loaded["samples"]["count"] == 4


class TestMonitoredOperation:
    """Test cases for the MonitoredOperation context manager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @patch("eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", True)
    @patch("eddypro_batch_processor.monitor.psutil")
    def test_context_manager(self, mock_psutil, temp_dir):
        """Test MonitoredOperation as context manager."""
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 50.0
        mock_memory = MagicMock()
        mock_memory.total = 8 * 1024**3
        mock_memory.available = 4 * 1024**3
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_io_counters.return_value = None
        mock_psutil.net_io_counters.return_value = None

        with MonitoredOperation(interval_seconds=0.1, output_dir=temp_dir) as monitor:
            assert monitor is not None
            assert monitor.is_monitoring
            # Simulate some work
            time.sleep(0.1)

        # After context exit, monitoring should be stopped
        assert not monitor.is_monitoring
        assert monitor.metrics_csv_path.exists()

    @patch("eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", False)
    def test_context_manager_without_psutil(self, temp_dir):
        """Test MonitoredOperation when psutil is unavailable."""
        with MonitoredOperation(output_dir=temp_dir) as monitor:
            assert monitor is None


class TestFakeWorkload:
    """Test monitoring with artificial workloads to verify behavior."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def cpu_intensive_task(self, duration: float = 0.1):
        """Simulate CPU-intensive work."""
        start = time.time()
        # Simple CPU-bound loop
        while time.time() - start < duration:
            _ = sum(i**2 for i in range(1000))

    @patch("eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", True)
    @patch("eddypro_batch_processor.monitor.psutil")
    def test_monitoring_fake_workload(self, mock_psutil, temp_dir):
        """Test monitoring with a fake CPU workload."""
        # Mock varying CPU usage over time
        cpu_values = [10.0, 30.0, 60.0, 40.0, 20.0]
        mock_psutil.cpu_percent.side_effect = cpu_values

        mock_memory = MagicMock()
        mock_memory.total = 8 * 1024**3
        mock_memory.available = 4 * 1024**3
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_psutil.disk_io_counters.return_value = None
        mock_psutil.net_io_counters.return_value = None

        monitor = PerformanceMonitor(interval_seconds=0.05, output_dir=temp_dir)

        # Run monitoring during fake workload
        monitor.start_monitoring()
        self.cpu_intensive_task(0.2)  # Run for 200ms
        summary = monitor.stop_monitoring()

        # Verify monitoring captured data
        assert summary["samples"]["count"] > 0
        assert "system_cpu_percent" in summary["metrics"]

        # Verify files were created
        assert monitor.metrics_csv_path.exists()
        assert monitor.summary_json_path.exists()

    def test_deterministic_sample_generation(self, temp_dir):
        """Test that monitoring produces deterministic results with fixed inputs."""
        with patch("eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", True), patch(
            "eddypro_batch_processor.monitor.psutil"
        ) as mock_psutil:
            # Set fixed return values for deterministic testing
            mock_psutil.cpu_percent.return_value = 42.0
            mock_memory = MagicMock()
            mock_memory.total = 8589934592  # Exact bytes
            mock_memory.available = 4294967296
            mock_memory.percent = 50.0
            mock_psutil.virtual_memory.return_value = mock_memory

            mock_disk_io = MagicMock()
            mock_disk_io.read_bytes = 1048576
            mock_disk_io.write_bytes = 524288
            mock_disk_io.read_count = 100
            mock_disk_io.write_count = 50
            mock_psutil.disk_io_counters.return_value = mock_disk_io
            mock_psutil.net_io_counters.return_value = None

            monitor = PerformanceMonitor(output_dir=temp_dir)

            # Collect exactly one sample
            with patch("time.time", return_value=1000.0):
                monitor._start_time = 1000.0
                sample = monitor._collect_sample()

            # Verify deterministic values
            assert sample["system_cpu_percent"] == 42.0
            assert sample["system_memory_total"] == 8589934592
            assert sample["system_disk_read_bytes"] == 1048576


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @patch("eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", True)
    @patch("eddypro_batch_processor.monitor.psutil")
    def test_file_write_errors(self, mock_psutil, temp_dir):
        """Test handling of file write errors."""
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 50.0
        mock_memory = MagicMock()
        mock_memory.total = 8 * 1024**3
        mock_memory.available = 4 * 1024**3
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_io_counters.return_value = None

        monitor = PerformanceMonitor(output_dir=temp_dir)

        # Add a sample
        sample = {"timestamp": 1000.0, "system_cpu_percent": 50.0}
        monitor._samples = [sample]

        # Make directory read-only to cause write errors
        temp_dir.chmod(0o444)

        try:
            # These should not raise exceptions, just log errors
            monitor._write_metrics_csv()
            monitor._write_summary_json({"test": "data"})
        finally:
            # Restore permissions for cleanup
            temp_dir.chmod(0o755)

    @patch("eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", True)
    @patch("eddypro_batch_processor.monitor.psutil")
    def test_psutil_exceptions(self, mock_psutil, temp_dir):
        """Test handling of psutil exceptions during monitoring."""
        # Mock psutil to raise exceptions
        if psutil_module:
            mock_psutil.cpu_percent.side_effect = psutil_module.AccessDenied()
            mock_psutil.virtual_memory.side_effect = psutil_module.AccessDenied()
            mock_psutil.disk_io_counters.side_effect = psutil_module.AccessDenied()
        else:
            # Create mock exceptions for testing
            class MockAccessDeniedError(Exception):
                pass

            mock_psutil.cpu_percent.side_effect = MockAccessDeniedError()
            mock_psutil.virtual_memory.side_effect = MockAccessDeniedError()
            mock_psutil.disk_io_counters.side_effect = MockAccessDeniedError()

        monitor = PerformanceMonitor(output_dir=temp_dir)

        # Should handle exceptions gracefully
        sample = monitor._collect_sample()
        assert sample is not None
        assert "timestamp" in sample
        # System metrics should be missing due to exceptions
        assert "system_cpu_percent" not in sample

    def test_thread_safety(self, temp_dir):
        """Test thread safety of monitoring operations."""
        with patch("eddypro_batch_processor.monitor.PSUTIL_AVAILABLE", True), patch(
            "eddypro_batch_processor.monitor.psutil"
        ) as mock_psutil:
            # Mock psutil
            mock_psutil.cpu_percent.return_value = 50.0
            mock_memory = MagicMock()
            mock_memory.total = 8 * 1024**3
            mock_memory.available = 4 * 1024**3
            mock_memory.percent = 50.0
            mock_psutil.virtual_memory.return_value = mock_memory
            mock_psutil.disk_io_counters.return_value = None

            monitor = PerformanceMonitor(interval_seconds=0.01, output_dir=temp_dir)

            # Start monitoring
            monitor.start_monitoring()

            # Multiple threads trying to access sample count
            results = []

            def check_samples():
                results.append(monitor.sample_count)

            threads = [threading.Thread(target=check_samples) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            monitor.stop_monitoring()

            # All threads should have gotten valid results
            assert len(results) == 10
            assert all(isinstance(count, int) for count in results)
