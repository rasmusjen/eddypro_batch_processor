"""
Tests for the bottleneck analysis module.

Includes an intentionally un-mocked integration test that runs a real subprocess
under the real monitor. Every other monitor test mocks psutil wholesale, which is
precisely why the original "monitor reports 0.0 for everything" bug survived in
CI for so long.
"""

import csv
import sys
import textwrap
from pathlib import Path

import pytest

from eddypro_batch_processor import core
from eddypro_batch_processor.analysis import (
    DEFAULT_THRESHOLDS,
    BottleneckAnalyzer,
    dominant_bottleneck,
)

FIELDNAMES = [
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
    "system_cpu_percent",
    "system_memory_percent",
    "system_memory_used_mb",
    "system_read_mb_per_s",
    "system_write_mb_per_s",
]


def write_metrics(path: Path, rows: list[dict]) -> Path:
    """Write a metrics CSV in the canonical schema."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for i, row in enumerate(rows):
            full = dict.fromkeys(FIELDNAMES, 0.0)
            full["timestamp"] = 1000.0 + i
            full["relative_time"] = float(i)
            full.update(row)
            writer.writerow(full)
    return path


def make_series(path: Path, count: int = 20, **values) -> Path:
    """Write `count` identical samples with the given metric values."""
    return write_metrics(path, [dict(values) for _ in range(count)])


class TestBottleneckClassification:
    """The analyzer must name the right limiting resource."""

    def test_cpu_bound(self, tmp_path):
        csv_path = make_series(
            tmp_path / "metrics.csv",
            cpu_percent=95.0,
            memory_mb=500.0,
            system_memory_percent=40.0,
            read_mb_per_s=2.0,
            write_mb_per_s=1.0,
        )
        result = BottleneckAnalyzer().analyze(csv_path)
        assert result.primary_bottleneck == "CPU"
        assert result.cpu_status == "RED"
        assert result.disk_status == "GREEN"
        assert "saturated" in result.explanation.lower()

    def test_disk_throughput_bound(self, tmp_path):
        # Idle CPU paired with heavy sustained I/O is the disk-bound signature.
        csv_path = make_series(
            tmp_path / "metrics.csv",
            cpu_percent=8.0,
            memory_mb=300.0,
            system_memory_percent=35.0,
            read_mb_per_s=180.0,
            write_mb_per_s=20.0,
        )
        result = BottleneckAnalyzer().analyze(csv_path)
        assert result.primary_bottleneck == "DISK_THROUGHPUT"
        assert result.disk_status == "RED"
        assert result.cpu_status == "GREEN"

    def test_disk_iops_bound(self, tmp_path):
        # Low throughput but very high operation count: many small files.
        csv_path = make_series(
            tmp_path / "metrics.csv",
            cpu_percent=10.0,
            memory_mb=200.0,
            system_memory_percent=30.0,
            read_mb_per_s=5.0,
            write_mb_per_s=2.0,
            read_iops=3000.0,
            write_iops=500.0,
        )
        result = BottleneckAnalyzer().analyze(csv_path)
        assert result.primary_bottleneck == "DISK_IOPS"

    def test_memory_bound(self, tmp_path):
        csv_path = make_series(
            tmp_path / "metrics.csv",
            cpu_percent=30.0,
            memory_mb=24000.0,
            system_memory_percent=93.0,
            read_mb_per_s=5.0,
            write_mb_per_s=5.0,
        )
        result = BottleneckAnalyzer().analyze(csv_path)
        assert result.primary_bottleneck == "MEMORY"
        assert result.memory_status == "RED"

    def test_no_bottleneck(self, tmp_path):
        csv_path = make_series(
            tmp_path / "metrics.csv",
            cpu_percent=15.0,
            memory_mb=250.0,
            system_memory_percent=30.0,
            read_mb_per_s=3.0,
            write_mb_per_s=2.0,
        )
        result = BottleneckAnalyzer().analyze(csv_path)
        assert result.primary_bottleneck == "NONE"
        assert result.cpu_status == "GREEN"
        assert "headroom" in result.explanation.lower()

    def test_cpu_takes_priority_over_disk(self, tmp_path):
        # A saturated CPU outranks a busy disk: the CPU is the binding limit.
        csv_path = make_series(
            tmp_path / "metrics.csv",
            cpu_percent=96.0,
            system_memory_percent=40.0,
            read_mb_per_s=200.0,
            write_mb_per_s=200.0,
        )
        assert BottleneckAnalyzer().analyze(csv_path).primary_bottleneck == "CPU"


class TestThresholdOverrides:
    """Thresholds must be tunable for different hardware."""

    def test_custom_disk_threshold_changes_verdict(self, tmp_path):
        csv_path = make_series(
            tmp_path / "metrics.csv",
            cpu_percent=8.0,
            system_memory_percent=30.0,
            read_mb_per_s=180.0,
        )
        assert BottleneckAnalyzer().analyze(csv_path).primary_bottleneck == (
            "DISK_THROUGHPUT"
        )
        # On an NVMe drive 180 MB/s is unremarkable, so raise the ceiling.
        relaxed = BottleneckAnalyzer(
            {"disk_high_mb_per_s": 2000.0, "disk_moderate_mb_per_s": 1000.0}
        )
        assert relaxed.analyze(csv_path).primary_bottleneck == "NONE"

    def test_defaults_are_not_mutated(self, tmp_path):
        original = dict(DEFAULT_THRESHOLDS)
        BottleneckAnalyzer({"cpu_high_percent": 10.0})
        assert dict(DEFAULT_THRESHOLDS) == original


class TestRobustness:
    """Bad input must degrade, not raise."""

    def test_missing_file(self, tmp_path):
        result = BottleneckAnalyzer().analyze(tmp_path / "nope.csv")
        assert result.primary_bottleneck == "UNKNOWN"
        assert result.sample_count == 0

    def test_empty_file(self, tmp_path):
        path = write_metrics(tmp_path / "metrics.csv", [])
        assert BottleneckAnalyzer().analyze(path).primary_bottleneck == "UNKNOWN"

    def test_blank_and_malformed_cells(self, tmp_path):
        path = tmp_path / "metrics.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for i in range(5):
                row = dict.fromkeys(FIELDNAMES, "")
                row["relative_time"] = i
                row["cpu_percent"] = "" if i % 2 else 95.0
                row["system_memory_percent"] = "n/a"
                writer.writerow(row)
        result = BottleneckAnalyzer().analyze(path)
        # Parses what it can rather than raising on the junk cells.
        assert result.sample_count == 5
        assert result.cpu.max == 95.0


class TestDominantBottleneck:
    """Aggregation across several analyses."""

    def test_empty(self):
        assert dominant_bottleneck([]) == "UNKNOWN"

    def test_real_bottleneck_outranks_none(self, tmp_path):
        cpu = make_series(
            tmp_path / "a.csv", cpu_percent=95.0, system_memory_percent=30.0
        )
        idle = make_series(
            tmp_path / "b.csv", cpu_percent=5.0, system_memory_percent=30.0
        )
        analyzer = BottleneckAnalyzer()
        analyses = [
            analyzer.analyze(idle),
            analyzer.analyze(idle),
            analyzer.analyze(cpu),
        ]
        # NONE is more common, but the saturated run is the actionable finding.
        assert dominant_bottleneck(analyses) == "CPU"


@pytest.mark.slow
@pytest.mark.integration
class TestRealWorkloadMonitoring:
    """
    End-to-end regression guard for the original defect.

    The monitor used to be pointed at the `cmd.exe` wrapper created by
    `shell=True` rather than at the real workload, so every CPU and disk figure
    was 0.0. These tests use no mocks at all: if that regression returns, they
    fail.
    """

    @pytest.fixture
    def burner_script(self, tmp_path):
        script = tmp_path / "burner.py"
        script.write_text(
            textwrap.dedent("""
                import os, sys, tempfile, time
                end = time.time() + 3.0
                d = tempfile.mkdtemp()
                payload = b"x" * (1024 * 1024)
                i = 0
                while time.time() < end:
                    total = 0
                    for j in range(150000):
                        total += j * j
                    path = os.path.join(d, "chunk%d.bin" % (i % 4))
                    with open(path, "wb") as fh:
                        fh.write(payload * 4)
                        fh.flush()
                        os.fsync(fh.fileno())
                    with open(path, "rb") as fh:
                        fh.read()
                    i += 1
                """),
            encoding="utf-8",
        )
        return script

    def test_monitor_captures_real_numbers(self, tmp_path, burner_script):
        out_dir = tmp_path / "metrics"
        rc = core.run_subprocess_with_monitoring(
            command=[sys.executable, str(burner_script)],
            working_dir=tmp_path,
            stream_output=False,
            metrics_interval=0.25,
            output_dir=out_dir,
            scenario_suffix="real",
            log_output=False,
        )
        assert rc == 0

        csv_path = out_dir / "metrics_real.csv"
        assert csv_path.exists(), "monitor wrote no metrics file"
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        assert len(rows) >= 3, f"expected several samples, got {len(rows)}"

        def col(name):
            return [float(r[name]) for r in rows if r.get(name) not in ("", None)]

        # The load is single-threaded, so normalised CPU is small on a many-core
        # box; cpu_percent_of_core is the column that must show real work.
        assert max(col("cpu_percent_of_core")) > 20.0, (
            "process-tree CPU never rose above 20% of a core -- the monitor is "
            "measuring the wrong process again"
        )
        assert max(col("memory_mb")) > 1.0, "process memory looks like a shell"

        # Assert on combined I/O rather than reads specifically. On Linux
        # io_counters().read_bytes counts only what was actually fetched from
        # the storage layer, so reading back a file that is still in the page
        # cache correctly reports zero reads. Writes are fsync'd, so the
        # combined total is non-zero on every platform.
        total_io = max(col("read_mb")) + max(col("write_mb"))
        assert total_io > 0.0, "no disk I/O recorded at all"
        total_rate = max(col("read_mb_per_s")) + max(col("write_mb_per_s"))
        assert total_rate > 0.0, "no I/O rate derived from the counter deltas"
        assert max(col("num_processes")) >= 1

        # Cumulative counters must never decrease.
        reads = col("read_mb")
        assert reads == sorted(reads), "cumulative read_mb went backwards"

    def test_analysis_of_real_run_is_not_unknown(self, tmp_path, burner_script):
        out_dir = tmp_path / "metrics"
        core.run_subprocess_with_monitoring(
            command=[sys.executable, str(burner_script)],
            working_dir=tmp_path,
            stream_output=False,
            metrics_interval=0.25,
            output_dir=out_dir,
            scenario_suffix="real",
            log_output=False,
        )
        result = BottleneckAnalyzer().analyze(out_dir / "metrics_real.csv")
        assert result.primary_bottleneck != "UNKNOWN"
        assert result.sample_count > 0
        assert result.total_read_mb + result.total_write_mb > 0

    def test_monitoring_disabled_writes_nothing(self, tmp_path, burner_script):
        out_dir = tmp_path / "metrics"
        rc = core.run_subprocess_with_monitoring(
            command=[sys.executable, "-c", "print('quick')"],
            working_dir=tmp_path,
            stream_output=False,
            metrics_interval=0.25,
            output_dir=out_dir,
            scenario_suffix="off",
            log_output=False,
            monitoring_enabled=False,
        )
        assert rc == 0
        assert not (out_dir / "metrics_off.csv").exists()
        assert not (out_dir / "metrics_summary_off.json").exists()
