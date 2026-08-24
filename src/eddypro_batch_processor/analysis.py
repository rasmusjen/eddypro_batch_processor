"""
Bottleneck analysis for EddyPro performance metrics.

Digests the ``metrics.csv`` time series produced by
:mod:`eddypro_batch_processor.monitor` into summary statistics and a
traffic-light classification that answers the practical question: *was this run
limited by the CPU, by memory, or by the disk?*

Deliberately import-light -- stdlib ``csv`` and arithmetic only, no pandas -- so
that it can be used from the reporting path without pulling in heavy imports.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, TypedDict

logger = logging.getLogger(__name__)

Status = Literal["GREEN", "YELLOW", "RED", "UNKNOWN"]
Bottleneck = Literal["CPU", "MEMORY", "DISK_THROUGHPUT", "DISK_IOPS", "NONE", "UNKNOWN"]


class PerformanceThresholds(TypedDict, total=False):
    """Tunable limits used to classify a run. Override via ``config.yaml``."""

    cpu_high_percent: float
    cpu_moderate_percent: float
    cpu_idle_percent: float
    memory_high_percent: float
    memory_moderate_percent: float
    disk_high_mb_per_s: float
    disk_moderate_mb_per_s: float
    disk_high_iops: float


DEFAULT_THRESHOLDS: dict[str, float] = {
    "cpu_high_percent": 90.0,
    "cpu_moderate_percent": 70.0,
    # Below this, the CPU is considered idle enough that a high I/O rate is
    # evidence the run was waiting on the disk rather than computing.
    "cpu_idle_percent": 40.0,
    "memory_high_percent": 85.0,
    "memory_moderate_percent": 70.0,
    # Calibrated for a SATA SSD (~550 MB/s sequential), which is the common
    # case for the bulk storage EddyPro reads from. Adjust for other media:
    #   NVMe SSD  -> disk_high ~3000, moderate ~1500, iops ~200000
    #   Mechanical -> disk_high ~150,  moderate ~80,   iops ~150
    "disk_high_mb_per_s": 450.0,
    "disk_moderate_mb_per_s": 250.0,
    "disk_high_iops": 20000.0,
}


# Columns the process-tree monitor must emit. Their absence means the file was
# written by the pre-v2 monitor, whose figures were all 0.0 anyway (it sampled
# the shell wrapper rather than EddyPro). Reporting UNKNOWN is honest; reporting
# "no bottleneck, CPU 0.0%" from those files is not.
CANONICAL_COLUMNS = ("cpu_percent", "memory_mb", "read_mb", "write_mb")
LEGACY_COLUMNS = ("process_cpu_percent", "process_memory_rss", "process_io_read_bytes")


@dataclass
class MetricStats:
    """Summary statistics for one metric series."""

    mean: float = 0.0
    max: float = 0.0
    p95: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class ScenarioAnalysis:
    """Result of analysing one metrics time series."""

    scenario_name: str = "baseline"
    sample_count: int = 0
    duration_seconds: float = 0.0

    cpu: MetricStats = field(default_factory=MetricStats)
    memory_mb: MetricStats = field(default_factory=MetricStats)
    system_memory_percent: MetricStats = field(default_factory=MetricStats)
    read_mb_per_s: MetricStats = field(default_factory=MetricStats)
    write_mb_per_s: MetricStats = field(default_factory=MetricStats)
    read_iops: MetricStats = field(default_factory=MetricStats)
    write_iops: MetricStats = field(default_factory=MetricStats)

    total_read_mb: float = 0.0
    total_write_mb: float = 0.0
    peak_memory_mb: float = 0.0

    cpu_status: Status = "UNKNOWN"
    memory_status: Status = "UNKNOWN"
    disk_status: Status = "UNKNOWN"
    primary_bottleneck: Bottleneck = "UNKNOWN"
    explanation: str = "No metrics available."

    def to_dict(self) -> dict[str, Any]:
        """Serialise for inclusion in a manifest or report."""
        data = asdict(self)
        return data


def _to_float(value: Any) -> float | None:
    """Parse a CSV cell into a float, tolerating blanks and junk."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stats(values: list[float]) -> MetricStats:
    """Compute mean/max/p95 for a series."""
    if not values:
        return MetricStats()
    ordered = sorted(values)
    n = len(ordered)
    if n == 1:
        p95 = ordered[0]
    else:
        index = 0.95 * (n - 1)
        lower = int(index)
        upper = min(lower + 1, n - 1)
        weight = index - lower
        p95 = ordered[lower] * (1 - weight) + ordered[upper] * weight
    return MetricStats(
        mean=round(sum(ordered) / n, 3),
        max=round(ordered[-1], 3),
        p95=round(p95, 3),
    )


class BottleneckAnalyzer:
    """Classify a metrics time series into a primary bottleneck."""

    def __init__(self, thresholds: Mapping[str, Any] | None = None):
        merged: dict[str, float] = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            # Unknown keys are ignored rather than rejected, so a config written
            # for a newer version does not break an older install.
            merged.update(
                {k: float(v) for k, v in thresholds.items() if k in DEFAULT_THRESHOLDS}
            )
        self.thresholds: dict[str, float] = merged

    # ------------------------------------------------------------------

    def analyze(
        self, metrics_csv_path: str | Path, scenario_name: str = "baseline"
    ) -> ScenarioAnalysis:
        """
        Analyse a metrics CSV file.

        Args:
            metrics_csv_path: Path to a ``metrics*.csv`` written by the monitor.
            scenario_name: Label carried through to the report.

        Returns:
            A :class:`ScenarioAnalysis`. Always returns an object -- a missing or
            unreadable file yields an ``UNKNOWN`` classification rather than raising.
        """
        path = Path(metrics_csv_path)
        rows = self._read_rows(path)
        if not rows:
            return ScenarioAnalysis(
                scenario_name=scenario_name,
                explanation=f"No usable samples found in {path.name}.",
            )
        return self.analyze_rows(rows, scenario_name=scenario_name)

    def analyze_rows(
        self, rows: list[dict[str, Any]], scenario_name: str = "baseline"
    ) -> ScenarioAnalysis:
        """Analyse already-parsed metric rows."""
        if rows and not any(c in rows[0] for c in CANONICAL_COLUMNS):
            legacy = any(c in rows[0] for c in LEGACY_COLUMNS)
            detail = (
                "written by a pre-v2 monitor, whose process metrics were all 0.0"
                if legacy
                else "missing every process-tree column"
            )
            logger.warning(
                f"Metrics for {scenario_name} are {detail}; cannot classify."
            )
            return ScenarioAnalysis(
                scenario_name=scenario_name,
                sample_count=len(rows),
                explanation=(
                    f"Unrecognised metrics schema ({detail}). Re-run with the "
                    f"current version to get a bottleneck verdict."
                ),
            )

        def series(key: str) -> list[float]:
            return [v for v in (_to_float(r.get(key)) for r in rows) if v is not None]

        cpu = series("cpu_percent")
        memory = series("memory_mb")
        sys_mem = series("system_memory_percent")
        read_rate = series("read_mb_per_s")
        write_rate = series("write_mb_per_s")
        read_iops = series("read_iops")
        write_iops = series("write_iops")
        read_total = series("read_mb")
        write_total = series("write_mb")
        rel_time = series("relative_time")

        analysis = ScenarioAnalysis(
            scenario_name=scenario_name,
            sample_count=len(rows),
            duration_seconds=round(rel_time[-1], 2) if rel_time else 0.0,
            cpu=_stats(cpu),
            memory_mb=_stats(memory),
            system_memory_percent=_stats(sys_mem),
            read_mb_per_s=_stats(read_rate),
            write_mb_per_s=_stats(write_rate),
            read_iops=_stats(read_iops),
            write_iops=_stats(write_iops),
            total_read_mb=round(read_total[-1], 3) if read_total else 0.0,
            total_write_mb=round(write_total[-1], 3) if write_total else 0.0,
            peak_memory_mb=round(max(memory), 3) if memory else 0.0,
        )

        self._classify(analysis)
        return analysis

    # ------------------------------------------------------------------

    def _read_rows(self, path: Path) -> list[dict[str, Any]]:
        """Read a metrics CSV, returning [] on any failure."""
        if not path.exists():
            logger.debug(f"Metrics file not found: {path}")
            return []
        try:
            with path.open("r", encoding="utf-8", newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            logger.exception(f"Failed to read metrics from {path}")
            return []

    def _classify(self, a: ScenarioAnalysis) -> None:
        """Assign per-resource statuses and the primary bottleneck."""
        t = self.thresholds

        # CPU: judged on sustained load, so p95 rather than the peak.
        a.cpu_status = self._level(
            a.cpu.p95, t["cpu_moderate_percent"], t["cpu_high_percent"]
        )

        # Memory: system-wide pressure matters more than the process footprint,
        # but fall back to the process if system memory was not recorded.
        mem_metric = (
            a.system_memory_percent.p95 if a.system_memory_percent.max > 0 else 0.0
        )
        a.memory_status = self._level(
            mem_metric, t["memory_moderate_percent"], t["memory_high_percent"]
        )

        # Disk: combined read+write throughput at p95.
        disk_rate = a.read_mb_per_s.p95 + a.write_mb_per_s.p95
        total_iops = a.read_iops.p95 + a.write_iops.p95
        disk_by_rate = self._level(
            disk_rate, t["disk_moderate_mb_per_s"], t["disk_high_mb_per_s"]
        )
        disk_by_iops = "RED" if total_iops > t["disk_high_iops"] else "GREEN"
        a.disk_status = "RED" if "RED" in (disk_by_rate, disk_by_iops) else disk_by_rate

        cpu_idle = a.cpu.p95 < t["cpu_idle_percent"]

        # Priority: saturated CPU is the clearest signal. Otherwise a busy disk
        # paired with an idle CPU means the run was waiting on I/O.
        if a.cpu_status == "RED":
            a.primary_bottleneck = "CPU"
            a.explanation = (
                f"CPU saturated: sustained (p95) utilisation {a.cpu.p95:.1f}%. "
                f"Processing is compute-bound; more parallel years will not help "
                f"unless spare cores are available."
            )
        elif a.memory_status == "RED":
            a.primary_bottleneck = "MEMORY"
            a.explanation = (
                f"Memory pressure: system memory reached {mem_metric:.1f}% (p95), "
                f"peak process-tree RSS {a.peak_memory_mb:.0f} MB. Reduce "
                f"max_processes to avoid swapping."
            )
        elif cpu_idle and disk_by_rate == "RED":
            a.primary_bottleneck = "DISK_THROUGHPUT"
            a.explanation = (
                f"Disk-bound: {disk_rate:.1f} MB/s sustained while the CPU sat at "
                f"{a.cpu.p95:.1f}%. The run is waiting on storage -- move the data "
                f"to a faster disk before adding parallelism."
            )
        elif cpu_idle and disk_by_iops == "RED":
            a.primary_bottleneck = "DISK_IOPS"
            a.explanation = (
                f"Disk-bound on latency: {total_iops:.0f} IOPS (p95) with the CPU at "
                f"{a.cpu.p95:.1f}%. Many small reads -- typical of raw files split "
                f"into short intervals."
            )
        elif a.cpu_status == "YELLOW":
            a.primary_bottleneck = "CPU"
            a.explanation = (
                f"Moderately CPU-bound: sustained utilisation {a.cpu.p95:.1f}%. "
                f"Some headroom remains."
            )
        else:
            a.primary_bottleneck = "NONE"
            a.explanation = (
                f"No clear bottleneck: CPU {a.cpu.p95:.1f}% (p95), disk "
                f"{disk_rate:.1f} MB/s, peak memory {a.peak_memory_mb:.0f} MB. "
                f"There is headroom to increase max_processes."
            )

    @staticmethod
    def _level(value: float, moderate: float, high: float) -> Status:
        """Map a value onto a traffic light."""
        if value >= high:
            return "RED"
        if value >= moderate:
            return "YELLOW"
        return "GREEN"


def analyze_metrics_files(
    metrics_paths: dict[str, Path],
    thresholds: Mapping[str, Any] | None = None,
) -> list[ScenarioAnalysis]:
    """
    Analyse several metrics files at once.

    Args:
        metrics_paths: Mapping of scenario name -> metrics CSV path.
        thresholds: Optional threshold overrides.

    Returns:
        One :class:`ScenarioAnalysis` per input, in insertion order.
    """
    analyzer = BottleneckAnalyzer(thresholds)
    return [
        analyzer.analyze(path, scenario_name=name)
        for name, path in metrics_paths.items()
    ]


def dominant_bottleneck(analyses: list[ScenarioAnalysis]) -> str:
    """
    Pick the most frequently observed limiting resource across analyses.

    A real bottleneck outranks ``NONE`` even when ``NONE`` is more common: one
    saturated year is the actionable finding, not the quiet ones.
    """
    if not analyses:
        return "UNKNOWN"
    counts: dict[str, int] = {}
    for a in analyses:
        counts[a.primary_bottleneck] = counts.get(a.primary_bottleneck, 0) + 1
    ranked = sorted(
        counts.items(), key=lambda kv: (kv[0] in ("NONE", "UNKNOWN"), -kv[1])
    )
    return ranked[0][0]
