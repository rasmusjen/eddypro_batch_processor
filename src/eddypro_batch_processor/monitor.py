"""
Performance monitoring module for EddyPro batch processing.

This module provides performance monitoring capabilities using psutil to track
CPU, memory, and I/O metrics during EddyPro subprocess execution.

Design notes
------------
The monitored unit is a **process tree**, not a single process. EddyPro is launched
as a child process and may itself spawn workers, so every sample walks
``root.children(recursive=True)`` and aggregates across the whole tree. Sampling a
single PID was the historical cause of all-zero metrics.

Disk I/O is exposed two ways: cumulative totals since monitoring started
(``read_mb`` / ``write_mb``) and instantaneous rates derived from the delta between
consecutive samples divided by the *actual* elapsed wall time (``read_mb_per_s`` /
``write_mb_per_s``). Raw psutil counters are monotonic since boot and are never
reported directly, because aggregate statistics over them are meaningless.
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

#: Bumped whenever the CSV column set or summary JSON structure changes.
METRICS_SCHEMA_VERSION = 2

#: Canonical column order for ``metrics.csv``. The first six columns are the
#: contract consumed by :mod:`eddypro_batch_processor.report`.
METRICS_FIELDNAMES = [
    "timestamp",
    "relative_time",
    "cpu_percent",
    "cpu_percent_of_core",
    "memory_mb",
    "read_mb",
    "write_mb",
    "read_mb_per_s",
    "write_mb_per_s",
    "read_iops",
    "write_iops",
    "num_processes",
    "work_items",
    "work_items_per_s",
    "system_cpu_percent",
    "system_memory_percent",
    "system_memory_used_mb",
    "system_read_mb_per_s",
    "system_write_mb_per_s",
]

_BYTES_PER_MB = 1024.0 * 1024.0


class PerformanceMonitor:
    """
    Monitor system and process-tree performance metrics during operations.

    Tracks CPU utilization, memory usage, and disk I/O (both cumulative and as
    rates) with a configurable sampling interval. Produces a time series (CSV) and
    a summary (JSON).
    """

    def __init__(
        self,
        interval_seconds: float = 0.5,
        output_dir: str | Path | None = None,
        scenario_suffix: str = "",
        progress_dir: str | Path | None = None,
        progress_glob: str = "*",
    ):
        """
        Initialize the performance monitor.

        Args:
            interval_seconds: Sampling interval in seconds (default: 0.5)
            output_dir: Directory to write metrics files (default: current directory)
            scenario_suffix: Suffix to append to output filenames for scenario runs
            progress_dir: Optional directory whose file count is a proxy for work
                completed. CPU alone cannot tell a saturated fast core from a
                saturated slow one -- on a hybrid P-core/E-core CPU a demoted run
                reports the same ~100% of a core while delivering roughly half the
                throughput. Counting finished work makes that visible.
            progress_glob: Pattern selecting the files to count in progress_dir

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
        self.progress_dir = Path(progress_dir) if progress_dir else None
        self.progress_glob = progress_glob

        # Number of logical CPUs, used to normalise process CPU onto a 0-100 scale
        # so it is directly comparable with psutil.cpu_percent().
        self._cpu_count = psutil.cpu_count() or 1

        # Monitoring state
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._start_time: float | None = None
        self._end_time: float | None = None

        # Data storage. _samples is touched by both the sampler thread and the
        # writer on the main thread, so it is guarded by _lock.
        self._samples: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._process: psutil.Process | None = None

        # Per-PID cumulative I/O counters, retained after a child exits so the
        # tree total never goes backwards when a worker finishes.
        self._io_by_pid: dict[int, tuple[float, float, float, float]] = {}
        self._io_baseline: tuple[float, float, float, float] | None = None
        self._primed_pids: set[int] = set()

        # psutil records the CPU-times baseline on the Process *instance*, so a
        # freshly constructed object always reports 0.0. children() builds new
        # objects on every call, so the instances must be cached by PID or every
        # descendant reads as idle for the whole run.
        self._proc_cache: dict[int, psutil.Process] = {}

        # Previous sample state, for delta-based rate computation
        self._prev_time: float | None = None
        self._prev_io: tuple[float, float, float, float] | None = None
        self._prev_system_io: tuple[float, float] | None = None
        self._prev_work_items: int | None = None

        # Output file paths
        self._metrics_csv_path = self._get_output_path("metrics.csv")
        self._summary_json_path = self._get_output_path("metrics_summary.json")

    def _get_output_path(self, filename: str) -> Path:
        """Get output file path with optional scenario suffix."""
        if self.scenario_suffix:
            name, ext = filename.rsplit(".", 1)
            filename = f"{name}_{self.scenario_suffix}.{ext}"
        return self.output_dir / filename

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_monitoring(self, process_pid: int | None = None) -> None:
        """
        Start performance monitoring.

        Args:
            process_pid: PID of the root process to monitor, including all of its
                descendants. If None, only system-wide metrics are recorded until
                :meth:`attach_process` is called.
        """
        if self._monitoring:
            logger.warning("Monitoring already active")
            return

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping performance monitoring")
            return

        self._monitoring = True
        self._start_time = time.time()
        with self._lock:
            self._samples.clear()
        self._io_by_pid.clear()
        self._io_baseline = None
        self._primed_pids.clear()
        self._prev_time = None
        self._prev_io = None
        self._prev_system_io = None
        self._prev_work_items = None

        # Prime the system-wide CPU counter. The first call after import always
        # returns 0.0 because there is no previous measurement to diff against.
        psutil.cpu_percent(interval=None)

        if process_pid:
            self.attach_process(process_pid)

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="PerformanceMonitor"
        )
        self._monitor_thread.start()

        logger.info(
            f"Started performance monitoring (interval: {self.interval_seconds}s, "
            f"process: {process_pid or 'system'})"
        )

    def attach_process(self, process_pid: int) -> bool:
        """
        Attach to a process tree after monitoring has already started.

        This lets the caller spawn the subprocess first and then point the running
        monitor at it, without the stop/restart cycle that used to truncate the
        metrics files.

        Args:
            process_pid: PID of the root process to monitor.

        Returns:
            True if the process was found and attached.
        """
        try:
            self._process = psutil.Process(process_pid)
        except Exception:
            logger.warning(
                f"Process {process_pid} not found, monitoring system-wide only"
            )
            self._process = None
            return False

        # Prime per-process CPU so the first real sample is not 0.0.
        for proc in self._iter_tracked():
            try:
                proc.cpu_percent(None)
                self._primed_pids.add(proc.pid)
            # nosec B112 - a process that vanishes or denies access between the
            # tree walk and this call must be skipped, not allowed to abort
            # priming for the rest of the tree.
            except Exception:  # noqa: PERF203  # nosec B112
                continue

        logger.debug(f"Attached performance monitor to PID {process_pid}")
        return True

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

        # Wait for the sampler thread. The timeout must exceed one full sampling
        # period or a slow interval would race the CSV writer.
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=max(5.0, self.interval_seconds * 2))

        summary = self._generate_summary()

        self._write_metrics_csv()
        self._write_summary_json(summary)

        duration = summary.get("timing", {}).get("duration_seconds", 0.0)
        logger.info(
            f"Stopped performance monitoring. "
            f"Duration: {duration:.2f}s, Samples: {len(self._samples)}"
        )

        return summary

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def _monitor_loop(self) -> None:
        """Main monitoring loop running in background thread."""
        while self._monitoring:
            try:
                sample = self._collect_sample()
                if sample:
                    with self._lock:
                        self._samples.append(sample)
            except Exception as e:
                logger.warning(f"Error collecting performance sample: {e}")

            time.sleep(self.interval_seconds)

    def _iter_tracked(self) -> list[Any]:
        """
        Return the root process plus every living descendant.

        Re-walked on every sample so workers spawned mid-run are picked up. A
        vanished root yields an empty list but never clears ``self._process`` --
        transient errors must not permanently disable process monitoring.
        """
        if not self._process:
            return []
        try:
            children = self._process.children(recursive=True)
        except Exception:
            return []

        tracked: list[Any] = [self._process]
        live_pids = {self._process.pid}
        for child in children:
            # setdefault keeps the first instance seen for this PID so its CPU
            # baseline survives; the newly built object is discarded.
            tracked.append(self._proc_cache.setdefault(child.pid, child))
            live_pids.add(child.pid)

        # Drop instances for processes that have exited. Their cumulative I/O is
        # already retained separately in _io_by_pid, so nothing is lost.
        for pid in self._proc_cache.keys() - live_pids:
            del self._proc_cache[pid]
            self._primed_pids.discard(pid)

        return tracked

    def _collect_sample(self) -> dict[str, Any] | None:
        """
        Collect a single performance sample.

        Returns:
            Dictionary of canonical metrics, or None on error.
        """
        try:
            timestamp = time.time()
            elapsed = (
                timestamp - self._prev_time if self._prev_time is not None else None
            )

            sample: dict[str, Any] = {
                "timestamp": timestamp,
                "relative_time": timestamp - (self._start_time or timestamp),
            }
            sample.update(self._collect_system_metrics(elapsed))
            sample.update(self._collect_process_metrics(elapsed))
            sample.update(self._collect_progress_metrics(elapsed))

            self._prev_time = timestamp
        except Exception as e:
            logger.debug(f"Failed to collect sample: {e}")
            return None
        else:
            return sample

    def _collect_progress_metrics(self, elapsed: float | None) -> dict[str, Any]:
        """Count completed work items and derive a rate.

        Throughput is the only signal that distinguishes a saturated fast core
        from a saturated slow one. CPU utilisation reads ~100% of a core either
        way, so without this a run demoted onto an efficiency core looks
        perfectly healthy while taking twice as long.
        """
        metrics: dict[str, Any] = {"work_items": 0, "work_items_per_s": 0.0}
        if self.progress_dir is None:
            return metrics

        try:
            # The directory is created by the workload, so it legitimately does
            # not exist for the first samples of a run.
            count = (
                sum(1 for _ in self.progress_dir.glob(self.progress_glob))
                if self.progress_dir.is_dir()
                else 0
            )
        except OSError as e:
            logger.debug(f"Failed to count progress items: {e}")
            return metrics

        metrics["work_items"] = count
        if self._prev_work_items is not None and elapsed and elapsed > 0:
            metrics["work_items_per_s"] = round(
                max(0, count - self._prev_work_items) / elapsed, 4
            )
        self._prev_work_items = count
        return metrics

    def _collect_system_metrics(self, elapsed: float | None) -> dict[str, Any]:
        """Collect system-wide metrics, converting disk counters into rates."""
        metrics: dict[str, Any] = {
            "system_cpu_percent": 0.0,
            "system_memory_percent": 0.0,
            "system_memory_used_mb": 0.0,
            "system_read_mb_per_s": 0.0,
            "system_write_mb_per_s": 0.0,
        }

        try:
            metrics["system_cpu_percent"] = psutil.cpu_percent(interval=None)

            memory = psutil.virtual_memory()
            metrics["system_memory_percent"] = memory.percent
            metrics["system_memory_used_mb"] = (
                memory.total - memory.available
            ) / _BYTES_PER_MB

            disk_io = psutil.disk_io_counters()
            if disk_io:
                current = (float(disk_io.read_bytes), float(disk_io.write_bytes))
                if self._prev_system_io is not None and elapsed and elapsed > 0:
                    metrics["system_read_mb_per_s"] = max(
                        0.0, (current[0] - self._prev_system_io[0])
                    ) / (_BYTES_PER_MB * elapsed)
                    metrics["system_write_mb_per_s"] = max(
                        0.0, (current[1] - self._prev_system_io[1])
                    ) / (_BYTES_PER_MB * elapsed)
                self._prev_system_io = current

        except Exception as e:
            logger.debug(f"Error collecting system metrics: {e}")

        return metrics

    def _collect_process_metrics(self, elapsed: float | None) -> dict[str, Any]:
        """
        Aggregate CPU, memory, and I/O across the monitored process tree.

        Every psutil call is guarded per-process: a child that exits between the
        tree walk and the read is skipped, and an ``AccessDenied`` on one process
        never aborts the sample or disables monitoring.
        """
        metrics: dict[str, Any] = {
            "cpu_percent": 0.0,
            "cpu_percent_of_core": 0.0,
            "memory_mb": 0.0,
            "read_mb": 0.0,
            "write_mb": 0.0,
            "read_mb_per_s": 0.0,
            "write_mb_per_s": 0.0,
            "read_iops": 0.0,
            "write_iops": 0.0,
            "num_processes": 0,
        }

        tracked = self._iter_tracked()
        if not tracked:
            # The tree has exited. Cumulative totals must hold their final value
            # rather than snapping back to zero -- read_mb/write_mb are
            # monotonic by contract, and consumers chart them as such.
            self._fill_cumulative_io(metrics)
            return metrics

        total_cpu = 0.0
        total_rss = 0.0
        alive = 0

        for proc in tracked:
            try:
                with proc.oneshot():
                    # A process seen for the first time must be primed; its first
                    # cpu_percent() reading is meaningless and is discarded.
                    if proc.pid not in self._primed_pids:
                        proc.cpu_percent(None)
                        self._primed_pids.add(proc.pid)
                    else:
                        total_cpu += proc.cpu_percent(None)

                    total_rss += float(proc.memory_info().rss)
                    alive += 1

                    try:
                        io = proc.io_counters()
                    except Exception:
                        io = None

                if io is not None:
                    # Retain the last known counters per PID so a finished child
                    # keeps contributing to the tree total.
                    self._io_by_pid[proc.pid] = (
                        float(io.read_bytes),
                        float(io.write_bytes),
                        float(io.read_count),
                        float(io.write_count),
                    )
            # nosec B112 - NoSuchProcess / AccessDenied / ZombieProcess: skip
            # this process only. self._process is deliberately left intact,
            # because nulling it on the first transient error is what used to
            # silently disable process monitoring for the rest of the run.
            except Exception:  # noqa: PERF203  # nosec B112
                continue

        metrics["num_processes"] = alive
        # Normalise onto 0-100 so this column is comparable with system_cpu_percent.
        metrics["cpu_percent"] = round(total_cpu / self._cpu_count, 3)
        # Un-normalised: 100 means "one core fully busy", 200 means two, and so on.
        # EddyPro is largely single-threaded, so this is the column that reveals a
        # saturated single core on a many-core machine.
        metrics["cpu_percent_of_core"] = round(total_cpu, 3)
        metrics["memory_mb"] = round(total_rss / _BYTES_PER_MB, 3)

        totals = self._fill_cumulative_io(metrics)
        if totals is not None:
            if self._prev_io is not None and elapsed and elapsed > 0:
                metrics["read_mb_per_s"] = round(
                    max(0.0, totals[0] - self._prev_io[0]) / (_BYTES_PER_MB * elapsed),
                    3,
                )
                metrics["write_mb_per_s"] = round(
                    max(0.0, totals[1] - self._prev_io[1]) / (_BYTES_PER_MB * elapsed),
                    3,
                )
                metrics["read_iops"] = round(
                    max(0.0, totals[2] - self._prev_io[2]) / elapsed, 2
                )
                metrics["write_iops"] = round(
                    max(0.0, totals[3] - self._prev_io[3]) / elapsed, 2
                )
            self._prev_io = totals

        return metrics

    def _fill_cumulative_io(
        self, metrics: dict[str, Any]
    ) -> tuple[float, float, float, float] | None:
        """
        Set read_mb/write_mb from retained per-PID counters.

        Returns the raw aggregate totals so the caller can derive rates, or None
        if no I/O counters have ever been observed.
        """
        totals = self._aggregate_io()
        if totals is None:
            return None
        if self._io_baseline is None:
            self._io_baseline = totals
        base = self._io_baseline
        metrics["read_mb"] = round(max(0.0, totals[0] - base[0]) / _BYTES_PER_MB, 3)
        metrics["write_mb"] = round(max(0.0, totals[1] - base[1]) / _BYTES_PER_MB, 3)
        return totals

    def _aggregate_io(self) -> tuple[float, float, float, float] | None:
        """Sum retained per-PID I/O counters across the whole tree."""
        if not self._io_by_pid:
            return None
        read = write = rcount = wcount = 0.0
        for r, w, rc, wc in self._io_by_pid.values():
            read += r
            write += w
            rcount += rc
            wcount += wc
        return (read, write, rcount, wcount)

    # ------------------------------------------------------------------
    # Summary and output
    # ------------------------------------------------------------------

    def _generate_summary(self) -> dict[str, Any]:
        """Generate summary statistics from collected samples."""
        with self._lock:
            samples = list(self._samples)

        duration = (self._end_time or 0) - (self._start_time or 0)

        if not samples:
            return {
                "schema_version": METRICS_SCHEMA_VERSION,
                "error": "No samples collected",
                "timing": {
                    "start_time": self._start_time,
                    "end_time": self._end_time,
                    "duration_seconds": duration,
                },
            }

        summary: dict[str, Any] = {
            "schema_version": METRICS_SCHEMA_VERSION,
            "monitoring_config": {
                "interval_seconds": self.interval_seconds,
                "scenario_suffix": self.scenario_suffix,
                "output_dir": str(self.output_dir),
                "cpu_count": self._cpu_count,
            },
            "timing": {
                "start_time": self._start_time,
                "end_time": self._end_time,
                "duration_seconds": duration,
            },
            "samples": {
                "count": len(samples),
                "first_timestamp": samples[0]["timestamp"],
                "last_timestamp": samples[-1]["timestamp"],
            },
            "metrics": {},
        }

        metrics_dict: dict[str, dict[str, float]] = {}
        for field in self._get_numeric_fields(samples):
            values = [s[field] for s in samples if field in s and s[field] is not None]
            if values:
                metrics_dict[field] = self._calculate_stats(values)
        summary["metrics"] = metrics_dict

        # Totals are the tail of the cumulative series, not an average.
        summary["totals"] = {
            "read_mb": samples[-1].get("read_mb", 0.0),
            "write_mb": samples[-1].get("write_mb", 0.0),
            "peak_memory_mb": max(s.get("memory_mb", 0.0) for s in samples),
        }

        return summary

    def _get_numeric_fields(self, samples: list[dict[str, Any]]) -> list[str]:
        """Get list of numeric field names from samples."""
        if not samples:
            return []

        return [
            key
            for key, value in samples[0].items()
            if key not in ("timestamp", "relative_time")
            and isinstance(value, int | float)
        ]

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
        lower = int(index)
        upper = lower + 1
        weight = index - lower
        return float(values[lower] * (1 - weight) + values[upper] * weight)

    def _write_metrics_csv(self) -> None:
        """Write time series metrics to CSV using the canonical column order."""
        with self._lock:
            samples = list(self._samples)

        if not samples:
            logger.warning("No samples to write to CSV")
            return

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)

            with open(
                self._metrics_csv_path, "w", newline="", encoding="utf-8"
            ) as csvfile:
                writer = csv.DictWriter(
                    csvfile, fieldnames=METRICS_FIELDNAMES, extrasaction="ignore"
                )
                writer.writeheader()
                for sample in samples:
                    writer.writerow({k: sample.get(k, 0) for k in METRICS_FIELDNAMES})

            logger.info(f"Wrote {len(samples)} samples to {self._metrics_csv_path}")

        except Exception:
            logger.exception("Failed to write metrics CSV")

    def _write_summary_json(self, summary: dict[str, Any]) -> None:
        """Write summary statistics to JSON file."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)

            with open(self._summary_json_path, "w", encoding="utf-8") as jsonfile:
                json.dump(summary, jsonfile, indent=2, default=str)

            logger.info(f"Wrote summary to {self._summary_json_path}")

        except Exception:
            logger.exception("Failed to write summary JSON")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

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
        with self._lock:
            return len(self._samples)


def create_monitor(
    interval_seconds: float = 0.5,
    output_dir: str | Path | None = None,
    scenario_suffix: str = "",
    progress_dir: str | Path | None = None,
    progress_glob: str = "*",
) -> PerformanceMonitor | None:
    """
    Create a performance monitor instance with error handling.

    Args:
        interval_seconds: Sampling interval in seconds (default: 0.5)
        output_dir: Directory to write metrics files
        scenario_suffix: Suffix for scenario-specific output files
        progress_dir: Optional directory whose file count proxies work completed
        progress_glob: Pattern selecting the files to count in progress_dir

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
            progress_dir=progress_dir,
            progress_glob=progress_glob,
        )
    except ImportError as e:
        logger.warning(f"Failed to create performance monitor: {e}")
        return None


class MonitoredOperation:
    """
    Context manager for monitoring operations.

    When ``enabled`` is False the context manager is inert: no monitor is created
    and no metrics files are written.

    Example:
        with MonitoredOperation(output_dir="./metrics") as monitor:
            proc = subprocess.Popen(...)
            monitor.attach_process(proc.pid)
            proc.wait()
        # Metrics are automatically saved
    """

    def __init__(
        self,
        interval_seconds: float = 0.5,
        output_dir: str | Path | None = None,
        scenario_suffix: str = "",
        process_pid: int | None = None,
        enabled: bool = True,
        progress_dir: str | Path | None = None,
        progress_glob: str = "*",
    ):
        """Initialize monitored operation context."""
        self.enabled = enabled
        self.monitor = (
            create_monitor(
                interval_seconds,
                output_dir,
                scenario_suffix,
                progress_dir,
                progress_glob,
            )
            if enabled
            else None
        )
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
