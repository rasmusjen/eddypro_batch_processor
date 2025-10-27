"""Tests for the report module."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from eddypro_batch_processor import report


def test_compute_file_checksum(tmp_path):
    """Test file checksum computation."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    checksum = report.compute_file_checksum(test_file)
    assert isinstance(checksum, str)
    assert len(checksum) == 64  # SHA256 produces 64-character hex string

    # Test with non-existent file
    with pytest.raises(FileNotFoundError):
        report.compute_file_checksum(tmp_path / "nonexistent.txt")


def test_collect_eddypro_output_files(tmp_path):
    """Test EddyPro output file collection."""
    site_id = "GL-ZaF"

    # Create sample EddyPro output files
    files_to_create = [
        f"eddypro_{site_id}_fluxnet_2024-11-18T185928_adv.csv",
        f"eddypro_{site_id}_full_output_2024-11-18T185928_adv.csv",
        f"eddypro_{site_id}_metadata_2024-11-18T185928_adv.csv",
        f"eddypro_{site_id}_qc_details_2024-11-18T165300_adv.csv",
        # Extra files that should not be collected
        f"{site_id}_cleanset.csv",
        f"{site_id}_WorkSet.csv",
        "other_file.txt",
    ]

    for filename in files_to_create:
        (tmp_path / filename).write_text("test data")

    # Collect files
    collected = report.collect_eddypro_output_files(tmp_path, site_id)

    # Verify structure
    assert "fluxnet_files" in collected
    assert "full_output_files" in collected
    assert "metadata_files" in collected
    assert "qc_details_files" in collected

    # Verify counts
    assert len(collected["fluxnet_files"]) == 1
    assert len(collected["full_output_files"]) == 1
    assert len(collected["metadata_files"]) == 1
    assert len(collected["qc_details_files"]) == 1

    # Verify absolute paths
    for file_list in collected.values():
        for file_path in file_list:
            assert Path(file_path).is_absolute()
            assert Path(file_path).exists()

    # Verify correct file matching
    assert "fluxnet" in collected["fluxnet_files"][0]
    assert "full_output" in collected["full_output_files"][0]
    assert "metadata" in collected["metadata_files"][0]
    assert "qc_details" in collected["qc_details_files"][0]


def test_collect_eddypro_output_files_empty_directory(tmp_path):
    """Test collection when no matching files exist."""
    collected = report.collect_eddypro_output_files(tmp_path, "GL-ZaF")

    # Should return empty lists for all file types
    assert collected["fluxnet_files"] == []
    assert collected["full_output_files"] == []
    assert collected["metadata_files"] == []
    assert collected["qc_details_files"] == []


def test_get_python_environment_info():
    """Test Python environment info capture."""
    env_info = report.get_python_environment_info()

    assert "python_version" in env_info
    assert "platform" in env_info
    assert "package_versions" in env_info

    pkg_versions = env_info["package_versions"]
    assert "PyYAML" in pkg_versions
    assert "psutil" in pkg_versions
    assert "plotly" in pkg_versions


def test_generate_scenario_manifest():
    """Test scenario manifest generation."""
    start_time = datetime(2025, 10, 1, 10, 0, 0)
    end_time = datetime(2025, 10, 1, 10, 30, 0)

    manifest = report.generate_scenario_manifest(
        scenario_name="test_scenario",
        scenario_params={"rot_meth": 1, "tlag_meth": 2},
        project_file=Path("/path/to/project.eddypro"),
        output_dir=Path("/path/to/output"),
        start_time=start_time,
        end_time=end_time,
        success=True,
        metrics_summary={"cpu_avg": 45.2, "memory_max_mb": 1024},
    )

    assert manifest["scenario_name"] == "test_scenario"
    assert manifest["scenario_params"]["rot_meth"] == 1
    assert manifest["duration_seconds"] == 1800.0  # 30 minutes
    assert manifest["success"] is True
    assert "metrics_summary" in manifest


def test_write_scenario_manifest(tmp_path):
    """Test writing scenario manifest to file."""
    manifest = {
        "scenario_name": "test",
        "success": True,
        "duration_seconds": 100.0,
    }
    output_path = tmp_path / "manifest.json"

    report.write_scenario_manifest(manifest, output_path)

    assert output_path.exists()
    with output_path.open("r") as f:
        loaded = json.load(f)
    assert loaded["scenario_name"] == "test"


def test_generate_run_manifest():
    """Test run-level manifest generation."""
    start_time = datetime(2025, 10, 1, 10, 0, 0)
    end_time = datetime(2025, 10, 1, 12, 0, 0)

    scenarios = [
        {"scenario_name": "baseline", "success": True},
        {"scenario_name": "scenario1", "success": True},
    ]

    manifest = report.generate_run_manifest(
        run_id="test_run_001",
        config={"site_id": "GL-ZaF"},
        config_checksum="abc123",
        site_id="GL-ZaF",
        years_processed=[2021, 2022],
        scenarios=scenarios,
        start_time=start_time,
        end_time=end_time,
        overall_success=True,
        output_dirs=[Path("/out/2021"), Path("/out/2022")],
    )

    assert manifest["run_id"] == "test_run_001"
    assert manifest["site_id"] == "GL-ZaF"
    assert len(manifest["scenarios"]) == 2
    assert manifest["duration_seconds"] == 7200.0  # 2 hours
    assert "environment" in manifest
    assert "output_files" in manifest  # New: verify output files included


def test_generate_run_manifest_with_output_files(tmp_path):
    """Test run manifest includes collected EddyPro output files."""
    site_id = "GL-ZaF"

    # Create output directory with sample files
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    (output_dir / f"eddypro_{site_id}_fluxnet_2024-11-18T185928_adv.csv").write_text(
        "data"
    )
    (
        output_dir / f"eddypro_{site_id}_full_output_2024-11-18T185928_adv.csv"
    ).write_text("data")

    start_time = datetime(2025, 10, 1, 10, 0, 0)
    end_time = datetime(2025, 10, 1, 10, 30, 0)

    manifest = report.generate_run_manifest(
        run_id="test_run_002",
        config={"site_id": site_id},
        config_checksum="xyz789",
        site_id=site_id,
        years_processed=[2024],
        scenarios=[{"scenario_name": "baseline", "success": True}],
        start_time=start_time,
        end_time=end_time,
        overall_success=True,
        output_dirs=[output_dir],
    )

    # Verify output_files structure
    assert "output_files" in manifest
    assert str(output_dir) in manifest["output_files"]

    collected = manifest["output_files"][str(output_dir)]
    assert "fluxnet_files" in collected
    assert "full_output_files" in collected
    assert len(collected["fluxnet_files"]) == 1
    assert len(collected["full_output_files"]) == 1


def test_write_run_manifest(tmp_path):
    """Test writing run manifest to file."""
    manifest = {
        "run_id": "test_run",
        "site_id": "GL-ZaF",
        "overall_success": True,
    }
    output_path = tmp_path / "subdir" / "run_manifest.json"

    report.write_run_manifest(manifest, output_path)

    assert output_path.exists()
    with output_path.open("r") as f:
        loaded = json.load(f)
    assert loaded["run_id"] == "test_run"


def test_load_metrics_from_csv(tmp_path):
    """Test loading metrics from CSV file."""
    metrics_csv = tmp_path / "metrics.csv"
    metrics_csv.write_text(
        "timestamp,cpu_percent,memory_mb,read_mb,write_mb\n"
        "2025-10-01T10:00:00,25.5,512.3,10.2,5.1\n"
        "2025-10-01T10:00:01,30.2,518.7,12.5,6.3\n"
    )

    metrics = report.load_metrics_from_csv(metrics_csv)

    assert len(metrics) == 2
    assert metrics[0]["cpu_percent"] == 25.5
    assert metrics[1]["memory_mb"] == 518.7


def test_generate_html_report():
    """Test HTML report generation."""
    run_manifest = {
        "run_id": "test_run",
        "timestamp": "2025-10-01T10:00:00",
        "duration_seconds": 3600.0,
        "site_id": "GL-ZaF",
        "years_processed": [2021],
        "overall_success": True,
        "scenarios": [
            {
                "scenario_name": "baseline",
                "scenario_params": {},
                "duration_seconds": 1800.0,
                "success": True,
            }
        ],
        "environment": {
            "python_version": "3.10.0",
            "platform": "Windows",
            "package_versions": {"PyYAML": "6.0"},
        },
    }

    html = report.generate_html_report(run_manifest, chart_engine="none")

    assert "EddyPro Batch Processing Report" in html
    assert "test_run" in html
    assert "GL-ZaF" in html
    assert "baseline" in html
    assert "<!DOCTYPE html>" in html


def test_generate_html_report_with_file_output(tmp_path):
    """Test HTML report generation with file output."""
    run_manifest = {
        "run_id": "test_run",
        "timestamp": "2025-10-01T10:00:00",
        "duration_seconds": 100.0,
        "site_id": "GL-ZaF",
        "years_processed": [2021],
        "overall_success": True,
        "scenarios": [],
        "environment": {"python_version": "3.10.0"},
    }

    output_path = tmp_path / "reports" / "report.html"
    html = report.generate_html_report(
        run_manifest, chart_engine="none", output_path=output_path
    )

    assert output_path.exists()
    assert "test_run" in html


def test_create_reports_directory(tmp_path):
    """Test reports directory creation."""
    base_dir = tmp_path / "output" / "GL-ZaF" / "2021"
    base_dir.mkdir(parents=True)

    reports_dir = report.create_reports_directory(base_dir)

    assert reports_dir.exists()
    assert reports_dir.name == "reports"
    assert reports_dir.parent == base_dir


def test_generate_plotly_charts():
    """Test Plotly chart generation."""
    metrics = [
        {
            "timestamp": 0,
            "cpu_percent": 25.0,
            "memory_mb": 512.0,
            "read_mb": 10.0,
            "write_mb": 5.0,
        },
        {
            "timestamp": 1,
            "cpu_percent": 30.0,
            "memory_mb": 520.0,
            "read_mb": 12.0,
            "write_mb": 6.0,
        },
    ]

    # Test with plotly available (if installed)
    result = report.generate_plotly_charts(metrics, scenario_name="test")
    if report.PLOTLY_AVAILABLE:
        assert result is not None
        assert "plotly" in result.lower() or "div" in result.lower()
    else:
        assert result is None

    # Test with empty metrics
    result = report.generate_plotly_charts([], scenario_name="test")
    assert result is None
