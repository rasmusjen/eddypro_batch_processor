"""Tests for CLI functionality."""

import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_help_command():
    """Test that eddypro-batch --help returns zero and prints usage."""
    result = subprocess.run(
        [sys.executable, "-m", "eddypro_batch_processor.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "eddypro-batch" in result.stdout
    assert "Available commands" in result.stdout
    assert "run" in result.stdout
    assert "scenarios" in result.stdout
    assert "validate" in result.stdout
    assert "status" in result.stdout


def test_cli_subcommands_help():
    """Test that all subcommands have help text."""
    subcommands = ["run", "scenarios", "validate", "status"]

    for subcommand in subcommands:
        result = subprocess.run(
            [sys.executable, "-m", "eddypro_batch_processor.cli", subcommand, "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Subcommand '{subcommand}' help failed"
        assert "usage:" in result.stdout, f"Subcommand '{subcommand}' missing usage"


def test_cli_validate_stub():
    """Test that validate command runs successfully with skip options."""
    # Create a minimal config for testing
    config_content = """
eddypro_executable: "dummy_path"
site_id: "test_site"
years_to_process: [2021]
input_dir_pattern: "dummy_input"
output_dir_pattern: "dummy_output"
ecmd_file: "dummy_ecmd.csv"
stream_output: false
log_level: "INFO"
multiprocessing: false
max_processes: 1
metrics_interval_seconds: 60
reports_dir: "dummy_reports"
report_charts: "none"
"""

    # Write temporary config
    test_config = Path("test_config.yaml")
    try:
        test_config.write_text(config_content)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "--config",
                str(test_config),
                "validate",
                "--skip-paths",
                "--skip-ecmd",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "[PASS] All validations passed!" in result.stdout

    finally:
        # Clean up
        if test_config.exists():
            test_config.unlink()


def test_cli_scenarios_stub():
    """Test that scenarios command accepts parameter options and generates matrix."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "eddypro_batch_processor.cli",
            "scenarios",
            "--rot-meth",
            "1",
            "3",
            "--site",
            "GL-ZaF",
            "--years",
            "2021",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,  # Add timeout to prevent hanging
    )

    # The command may fail due to missing paths, but should still
    # generate scenarios and show parameter options
    assert "Generated 2 scenario(s):" in result.stdout
    assert "Parameter options for scenarios:" in result.stdout


def test_cli_run_dry_run_stub(tmp_path):
    """Test that run command accepts dry-run option and executes."""
    ecmd_file = tmp_path / "ecmd.csv"
    ecmd_file.write_text(
        "DATE_OF_VARIATION_EF,SITEID,ALTITUDE,CANOPY_HEIGHT,LATITUDE,LONGITUDE,"
        "ACQUISITION_FREQUENCY,FILE_DURATION,SA_HEIGHT,SA_WIND_DATA_FORMAT,"
        "SA_NORTH_ALIGNEMENT,SA_NORTH_OFFSET,GA_TUBE_LENGTH,GA_TUBE_DIAMETER,"
        "GA_FLOWRATE,GA_NORTHWARD_SEPARATION,GA_EASTWARD_SEPARATION,"
        "GA_VERTICAL_SEPARATION\n"
        "202001010000,test-site,10,0.5,1.0,2.0,10,30,3.1,uvw,spar,"
        "60,71.1,5.3,12,-11,-18,0\n",
        encoding="utf-8",
    )

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        f"""
site_id: test-site
years_to_process: [2025]
eddypro_executable: /fake/eddypro.exe
input_dir_pattern: {tmp_path}/input/{{site_id}}/{{year}}
output_dir_pattern: {tmp_path}/output/{{site_id}}/{{year}}
ecmd_file: {ecmd_file}
max_processes: 1
multiprocessing: false
stream_output: false
log_level: INFO
metrics_interval_seconds: 0.5
reports_dir: null
report_charts: none
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "eddypro_batch_processor.cli",
            "--config",
            str(config_file),
            "run",
            "--dry-run",
            "--site",
            "test-site",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    # Check for actual implementation outputs, not stub message
    assert "Dry run mode enabled" in result.stdout
    assert "Starting EddyPro batch processing" in result.stdout


def test_cli_no_subcommand_shows_help():
    """Test that running without subcommand shows help."""
    result = subprocess.run(
        [sys.executable, "-m", "eddypro_batch_processor.cli"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "usage:" in result.stdout


def test_cli_nonexistent_config_error():
    """Test that non-existent config file produces error."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "eddypro_batch_processor.cli",
            "--config",
            "nonexistent_config.yaml",
            "validate",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    # Error message goes to stdout due to logging configuration
    assert "Configuration file not found" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])
