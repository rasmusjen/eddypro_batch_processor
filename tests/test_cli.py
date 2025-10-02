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
    """Test that scenarios command accepts parameter options."""
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
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Generated 2 scenario(s):" in result.stdout
    assert "Parameter options for scenarios:" in result.stdout


def test_cli_run_dry_run_stub():
    """Test that run command accepts dry-run option."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "eddypro_batch_processor.cli",
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
    assert "Run command - stub implementation" in result.stdout
    assert "Dry run mode enabled" in result.stdout


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
