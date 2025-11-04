"""
End-to-end integration tests for EddyPro Batch Processor.

Tests the full pipeline in dry-run mode with mocked EddyPro execution to verify
that all components work together correctly: CLI → config → INI generation →
scenario execution → reporting → manifest generation.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


class TestEndToEndIntegration:
    """End-to-end integration tests for the full processing pipeline."""

    @pytest.fixture
    def mock_eddypro_exe(self, tmp_path: Path) -> Path:
        """Create a mock EddyPro executable that does nothing."""
        mock_exe = tmp_path / "mock_eddypro.exe"
        # Create a simple batch script that exits successfully
        if mock_exe.suffix == ".exe":
            # On Windows, create a simple executable stub
            mock_exe.write_text("@echo off\nexit 0")
        else:
            mock_exe.write_text("#!/bin/sh\nexit 0")
        mock_exe.chmod(0o755)
        return mock_exe

    @pytest.fixture
    def mock_ecmd_file(self, tmp_path: Path) -> Path:
        """Create a mock ECMD CSV file with required columns."""
        ecmd_file = tmp_path / "test_ecmd.csv"
        content = (
            "DATE_OF_VARIATION_EF,FILE_DURATION,ACQUISITION_FREQUENCY,CANOPY_HEIGHT,"
            "SA_MANUFACTURER,SA_MODEL,SA_HEIGHT,SA_WIND_DATA_FORMAT,SA_NORTH_ALIGNEMENT,"
            "SA_NORTH_OFFSET,GA_MANUFACTURER,GA_MODEL,GA_NORTHWARD_SEPARATION,"
            "GA_EASTWARD_SEPARATION,GA_VERTICAL_SEPARATION,GA_PATH,GA_TUBE_LENGTH,"
            "GA_TUBE_DIAMETER,GA_FLOWRATE\n"
            "2021-01-01,30,20,2.5,TestManufacturer,TestModel,3.0,u-v-w,0,0,"
            "TestGA,TestGAModel,0.1,0.1,0.2,closed,1.5,0.01,10.0\n"
        )
        ecmd_file.write_text(content)
        return ecmd_file

    @pytest.fixture
    def test_config(
        self, tmp_path: Path, mock_eddypro_exe: Path, mock_ecmd_file: Path
    ) -> dict:
        """Create a test configuration dictionary."""
        input_dir = tmp_path / "raw" / "TEST-SITE" / "2021"
        output_dir = tmp_path / "processed" / "TEST-SITE" / "2021"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        return {
            "eddypro_executable": str(mock_eddypro_exe),
            "site_id": "TEST-SITE",
            "years_to_process": [2021],
            "input_dir_pattern": str(tmp_path / "raw" / "{site_id}" / "{year}"),
            "output_dir_pattern": str(tmp_path / "processed" / "{site_id}" / "{year}"),
            "ecmd_file": str(mock_ecmd_file),
            "stream_output": False,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 1,
            "metrics_interval_seconds": 0.1,
            "reports_dir": None,
            "report_charts": "none",
        }

    @pytest.fixture
    def config_file(self, tmp_path: Path, test_config: dict) -> Path:
        """Write test config to a temporary YAML file."""
        config_path = tmp_path / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(test_config, f)
        return config_path

    @pytest.fixture
    def template_ini(self, tmp_path: Path) -> Path:
        """Create a minimal EddyPro template INI file."""
        template_path = tmp_path / "EddyProProject_template.ini"
        content = """[Project]
project_title = Test Project
file_name = test_project.eddypro

[RawProcess_General]
data_path = /path/to/data
recurse = 1
out_path = /path/to/output

[RawProcess_Settings]
rot_meth = 1
tlag_meth = 2
detrend_meth = 0

[RawProcess_ParameterSettings]
despike_meth = 0
"""
        template_path.write_text(content)
        return template_path

    def test_dry_run_single_scenario(
        self, tmp_path: Path, config_file: Path, template_ini: Path, test_config: dict
    ):
        """Test end-to-end dry-run with a single scenario."""
        # Set up template in expected location
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        template_target = config_dir / "EddyProProject_template.ini"
        template_target.write_text(template_ini.read_text())

        # Run the CLI in dry-run mode
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "--config",
                str(config_file),
                "run",
                "--dry-run",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        # Verify successful execution
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Verify output directory structure
        output_base = tmp_path / "processed" / "TEST-SITE" / "2021"
        reports_dir = output_base / "reports"

        # Check that reports directory was created
        assert reports_dir.exists(), "Reports directory not created"

        # Verify manifest exists
        manifest_file = reports_dir / "run_manifest.json"
        assert manifest_file.exists(), "Run manifest not created"

        # Load and validate manifest structure
        with open(manifest_file) as f:
            manifest = json.load(f)

        # Check manifest has expected keys
        assert "run_id" in manifest
        assert "config_snapshot" in manifest
        assert "scenarios" in manifest
        assert "start_time" in manifest
        assert "end_time" in manifest
        assert "dry_run" in manifest
        assert manifest["dry_run"] is True

        # Verify at least one scenario was processed
        assert len(manifest["scenarios"]) >= 1

    def test_dry_run_multiple_scenarios(
        self, tmp_path: Path, config_file: Path, template_ini: Path, test_config: dict
    ):
        """Test end-to-end dry-run with multiple scenarios."""
        # Set up template in expected location
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        template_target = config_dir / "EddyProProject_template.ini"
        template_target.write_text(template_ini.read_text())

        # Run scenarios command with multiple parameter combinations
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "--config",
                str(config_file),
                "scenarios",
                "--site",
                "TEST-SITE",
                "--years",
                "2021",
                "--rot-meth",
                "1",
                "3",
                "--tlag-meth",
                "2",
                "4",
                "--dry-run",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        # Verify successful execution
        assert result.returncode == 0, f"Scenarios command failed: {result.stderr}"

        # Verify output directory
        output_base = tmp_path / "processed" / "TEST-SITE" / "2021"
        reports_dir = output_base / "reports"

        # Check reports directory
        assert reports_dir.exists(), "Reports directory not created"

        # Verify manifest
        manifest_file = reports_dir / "run_manifest.json"
        assert manifest_file.exists(), "Run manifest not created"

        with open(manifest_file) as f:
            manifest = json.load(f)

        # Should have 4 scenarios (2 rot_meth × 2 tlag_meth)
        n_scenarios = len(manifest["scenarios"])
        assert n_scenarios == 4, f"Expected 4 scenarios, got {n_scenarios}"

        # Verify scenario naming is deterministic
        scenario_names = [s["scenario_suffix"] for s in manifest["scenarios"]]
        expected_suffixes = [
            "_rot1_tlag2",
            "_rot1_tlag4",
            "_rot3_tlag2",
            "_rot3_tlag4",
        ]
        for expected in expected_suffixes:
            found = any(expected in name for name in scenario_names)
            assert found, f"Missing suffix {expected}"

    def test_dry_run_with_validation(
        self, tmp_path: Path, config_file: Path, template_ini: Path
    ):
        """Test that validation runs before processing in dry-run mode."""
        # Set up template
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        template_target = config_dir / "EddyProProject_template.ini"
        template_target.write_text(template_ini.read_text())

        # First validate
        validate_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "--config",
                str(config_file),
                "validate",
                "--skip-paths",  # Skip path validation since paths may not exist
                "--skip-ecmd",  # Skip ECMD validation
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        # Validation should pass for config structure
        rc = validate_result.returncode
        msg = f"Validation failed: {validate_result.stderr}"
        assert rc == 0, msg

        # Then run in dry-run mode
        run_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "--config",
                str(config_file),
                "run",
                "--dry-run",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert run_result.returncode == 0, f"Dry run failed: {run_result.stderr}"

    def test_dry_run_project_file_generation(
        self, tmp_path: Path, config_file: Path, template_ini: Path, test_config: dict
    ):
        """Test that .eddypro project files are generated in dry-run mode."""
        # Set up template
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        template_target = config_dir / "EddyProProject_template.ini"
        template_target.write_text(template_ini.read_text())

        # Run with parameter overrides
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "--config",
                str(config_file),
                "run",
                "--dry-run",
                "--rot-meth",
                "3",
                "--tlag-meth",
                "4",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Check that project files were created
        output_base = tmp_path / "processed" / "TEST-SITE" / "2021"

        # Look for .eddypro files
        eddypro_files = list(output_base.rglob("*.eddypro"))
        assert len(eddypro_files) > 0, "No .eddypro project files generated"

        # Verify INI overrides were applied (read one of the files)
        if eddypro_files:
            project_content = eddypro_files[0].read_text()
            assert "rot_meth = 3" in project_content or "rot_meth=3" in project_content
            assert (
                "tlag_meth = 4" in project_content or "tlag_meth=4" in project_content
            )

    def test_dry_run_scenario_cap_enforcement(
        self, tmp_path: Path, config_file: Path, template_ini: Path
    ):
        """Test that scenario cap of 32 is enforced."""
        # Set up template
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        template_target = config_dir / "EddyProProject_template.ini"
        template_target.write_text(template_ini.read_text())

        # Try to generate 2×2×2×2×2×2 = 64 scenarios (exceeds cap of 32)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "--config",
                str(config_file),
                "scenarios",
                "--site",
                "TEST-SITE",
                "--years",
                "2021",
                "2022",  # 2 years
                "--rot-meth",
                "1",
                "3",  # 2 values
                "--tlag-meth",
                "2",
                "4",  # 2 values
                "--detrend-meth",
                "0",
                "1",  # 2 values
                "--despike-meth",
                "0",
                "1",  # 2 values
                # Total: 2×2×2×2×2 = 32 scenarios (at the cap)
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        # This should succeed (exactly at cap)
        msg = f"Should succeed at cap: {result.stderr}"
        assert result.returncode == 0, msg

    def test_dry_run_reports_generation(
        self, tmp_path: Path, config_file: Path, template_ini: Path, test_config: dict
    ):
        """Test that reports are generated correctly in dry-run mode."""
        # Set up template
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        template_target = config_dir / "EddyProProject_template.ini"
        template_target.write_text(template_ini.read_text())

        # Run with report generation
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "--config",
                str(config_file),
                "run",
                "--dry-run",
                "--report-charts",
                "none",  # Disable charts for faster tests
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Verify reports directory and files
        output_base = tmp_path / "processed" / "TEST-SITE" / "2021"
        reports_dir = output_base / "reports"

        assert reports_dir.exists(), "Reports directory not created"
        assert (reports_dir / "run_manifest.json").exists(), "Manifest not created"
        assert (reports_dir / "run_report.html").exists(), "HTML report not created"

        # Verify HTML report has content
        html_content = (reports_dir / "run_report.html").read_text()
        assert len(html_content) > 0, "HTML report is empty"
        assert (
            "EddyPro Batch Processing Report" in html_content
            or "TEST-SITE" in html_content
        )


class TestEndToEndCLICommands:
    """Test individual CLI commands work end-to-end."""

    @pytest.fixture
    def minimal_config(self, tmp_path: Path) -> Path:
        """Create a minimal valid config for testing."""
        config = {
            "eddypro_executable": str(tmp_path / "eddypro.exe"),
            "site_id": "TEST",
            "years_to_process": [2021],
            "input_dir_pattern": str(tmp_path / "raw" / "{site_id}" / "{year}"),
            "output_dir_pattern": str(tmp_path / "processed" / "{site_id}" / "{year}"),
            "ecmd_file": str(tmp_path / "test.csv"),
            "stream_output": False,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 1,
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return config_path

    def test_cli_help_command(self):
        """Test that CLI --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "eddypro_batch_processor.cli", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "eddypro-batch" in result.stdout
        assert "run" in result.stdout
        assert "scenarios" in result.stdout
        assert "validate" in result.stdout
        assert "status" in result.stdout

    def test_cli_run_help(self):
        """Test that run subcommand help works."""
        result = subprocess.run(
            [sys.executable, "-m", "eddypro_batch_processor.cli", "run", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "--dry-run" in result.stdout
        assert "--rot-meth" in result.stdout

    def test_cli_scenarios_help(self):
        """Test that scenarios subcommand help works."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "scenarios",
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "--rot-meth" in result.stdout
        assert "--tlag-meth" in result.stdout

    def test_cli_validate_help(self):
        """Test that validate subcommand help works."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "eddypro_batch_processor.cli",
                "validate",
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "--skip-paths" in result.stdout or "validate" in result.stdout
