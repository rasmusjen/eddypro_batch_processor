"""Tests for core module functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from eddypro_batch_processor.core import (
    EddyProBatchProcessor,
    load_config,
    run_eddypro_with_monitoring,
    validate_config,
)


class TestEddyProBatchProcessor:
    """Test the main EddyProBatchProcessor class."""

    def test_init_default_config_path(self):
        """Test initialization with default config path."""
        processor = EddyProBatchProcessor()
        assert processor.config_path == Path("config/config.yaml")
        assert processor.config == {}

    def test_init_custom_config_path(self):
        """Test initialization with custom config path."""
        custom_path = Path("custom/config.yaml")
        processor = EddyProBatchProcessor(custom_path)
        assert processor.config_path == custom_path
        assert processor.config == {}

    def test_load_config_success(self):
        """Test successful config loading."""
        test_config = {
            "eddypro_executable": "/path/to/eddypro",
            "site_id": "TEST-SITE",
            "years_to_process": [2021, 2022],
            "input_dir_pattern": "data/raw/{site_id}/{year}",
            "output_dir_pattern": "data/processed/{site_id}/{year}",
            "ecmd_file": "data/test_ecmd.csv",
            "stream_output": True,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 1,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            config_path = Path(f.name)

        try:
            processor = EddyProBatchProcessor()
            loaded_config = processor.load_config(config_path)

            assert loaded_config == test_config
            assert processor.config == test_config
            assert processor.config_path == config_path
        finally:
            config_path.unlink()

    def test_load_config_file_not_found(self):
        """Test config loading with non-existent file."""
        processor = EddyProBatchProcessor()
        non_existent_path = Path("non_existent_config.yaml")

        with pytest.raises(SystemExit):
            processor.load_config(non_existent_path)

    def test_load_config_invalid_yaml(self):
        """Test config loading with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [\n")  # Invalid YAML
            config_path = Path(f.name)

        try:
            processor = EddyProBatchProcessor()
            with pytest.raises(SystemExit):
                processor.load_config(config_path)
        finally:
            config_path.unlink()

    def test_validate_config_success(self):
        """Test successful config validation."""
        valid_config = {
            "eddypro_executable": "/path/to/eddypro",
            "site_id": "TEST-SITE",
            "years_to_process": [2021],
            "input_dir_pattern": "data/raw/{site_id}/{year}",
            "output_dir_pattern": "data/processed/{site_id}/{year}",
            "ecmd_file": "data/test_ecmd.csv",
            "stream_output": True,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 2,
            "metrics_interval_seconds": 0.5,
            "reports_dir": None,
            "report_charts": "plotly",
        }

        processor = EddyProBatchProcessor()
        # Should not raise an exception
        processor.validate_config(valid_config)

    def test_validate_config_missing_keys(self):
        """Test config validation with missing required keys."""
        incomplete_config = {
            "eddypro_executable": "/path/to/eddypro",
            "site_id": "TEST-SITE",
            # Missing required keys
        }

        processor = EddyProBatchProcessor()
        with pytest.raises(SystemExit):
            processor.validate_config(incomplete_config)

    def test_validate_config_invalid_max_processes(self):
        """Test config validation with invalid max_processes."""
        invalid_config = {
            "eddypro_executable": "/path/to/eddypro",
            "site_id": "TEST-SITE",
            "years_to_process": [2021],
            "input_dir_pattern": "data/raw/{site_id}/{year}",
            "output_dir_pattern": "data/processed/{site_id}/{year}",
            "ecmd_file": "data/test_ecmd.csv",
            "stream_output": True,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 0,  # Invalid value
        }

        processor = EddyProBatchProcessor()
        with pytest.raises(SystemExit):
            processor.validate_config(invalid_config)

    def test_validate_config_use_instance_config(self):
        """Test config validation using instance config when none provided."""
        valid_config = {
            "eddypro_executable": "/path/to/eddypro",
            "site_id": "TEST-SITE",
            "years_to_process": [2021],
            "input_dir_pattern": "data/raw/{site_id}/{year}",
            "output_dir_pattern": "data/processed/{site_id}/{year}",
            "ecmd_file": "data/test_ecmd.csv",
            "stream_output": True,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 1,
            "metrics_interval_seconds": 0.5,
            "reports_dir": None,
            "report_charts": "plotly",
        }

        processor = EddyProBatchProcessor()
        processor.config = valid_config
        # Should not raise an exception
        processor.validate_config()


class TestLegacyFunctions:
    """Test the legacy function wrappers."""

    def test_load_config_legacy_wrapper(self):
        """Test the legacy load_config function wrapper."""
        test_config = {
            "eddypro_executable": "/path/to/eddypro",
            "site_id": "LEGACY-TEST",
            "years_to_process": [2021],
            "input_dir_pattern": "data/raw/{site_id}/{year}",
            "output_dir_pattern": "data/processed/{site_id}/{year}",
            "ecmd_file": "data/test_ecmd.csv",
            "stream_output": False,
            "log_level": "DEBUG",
            "multiprocessing": True,
            "max_processes": 4,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            config_path = Path(f.name)

        try:
            loaded_config = load_config(config_path)
            assert loaded_config == test_config
        finally:
            config_path.unlink()

    def test_validate_config_legacy_wrapper(self):
        """Test the legacy validate_config function wrapper."""
        valid_config = {
            "eddypro_executable": "/path/to/eddypro",
            "site_id": "LEGACY-TEST",
            "years_to_process": [2021],
            "input_dir_pattern": "data/raw/{site_id}/{year}",
            "output_dir_pattern": "data/processed/{site_id}/{year}",
            "ecmd_file": "data/test_ecmd.csv",
            "stream_output": False,
            "log_level": "DEBUG",
            "multiprocessing": True,
            "max_processes": 4,
            "metrics_interval_seconds": 0.5,
            "reports_dir": None,
            "report_charts": "plotly",
        }

        # Should not raise an exception
        validate_config(valid_config)


class TestRunEddyProWithMonitoring:
    """Tests for the rp/fcc execution flow."""

    def test_runs_rp_then_fcc_on_success(self, tmp_path: Path):
        """Ensure eddypro_rp and eddypro_fcc run in order on success."""
        project_dir = tmp_path / "site" / "2021"
        project_dir.mkdir(parents=True)
        project_file = project_dir / "TEST.eddypro"
        project_file.write_text("project", encoding="utf-8")

        eddypro_bin = tmp_path / "eddypro_bin"
        eddypro_bin.mkdir()
        eddypro_exe = eddypro_bin / "eddypro_rp.exe"
        eddypro_exe.write_text("", encoding="utf-8")

        def _mock_copytree(src: Path, dst: Path, dirs_exist_ok: bool = True) -> Path:
            dst_path = Path(dst)
            dst_path.mkdir(parents=True, exist_ok=True)
            (dst_path / "eddypro_rp.exe").write_text("", encoding="utf-8")
            (dst_path / "eddypro_fcc.exe").write_text("", encoding="utf-8")
            return dst_path

        with (
            patch(
                "eddypro_batch_processor.core.platform.system",
                return_value="Windows",
            ),
            patch(
                "eddypro_batch_processor.core.shutil.copytree",
                side_effect=_mock_copytree,
            ),
            patch(
                "eddypro_batch_processor.core.run_subprocess_with_monitoring",
                side_effect=[0, 0],
            ) as mock_run,
        ):
            success = run_eddypro_with_monitoring(
                project_file=project_file,
                eddypro_executable=eddypro_exe,
                stream_output=False,
                metrics_interval=0.5,
                scenario_suffix="",
            )

        assert success is True
        assert mock_run.call_count == 2

        rp_call = mock_run.call_args_list[0].kwargs
        fcc_call = mock_run.call_args_list[1].kwargs

        assert "eddypro_rp.exe" in rp_call["command"]
        assert "eddypro_fcc.exe" in fcc_call["command"]
        assert rp_call["working_dir"] == project_dir.parent
        assert fcc_call["working_dir"] == project_dir.parent
        assert rp_call["scenario_suffix"] == "rp"
        assert fcc_call["scenario_suffix"] == "fcc"

    def test_skips_fcc_when_rp_fails(self, tmp_path: Path):
        """Ensure eddypro_fcc is skipped when eddypro_rp fails."""
        project_dir = tmp_path / "site" / "2021"
        project_dir.mkdir(parents=True)
        project_file = project_dir / "TEST.eddypro"
        project_file.write_text("project", encoding="utf-8")

        eddypro_bin = tmp_path / "eddypro_bin"
        eddypro_bin.mkdir()
        eddypro_exe = eddypro_bin / "eddypro_rp.exe"
        eddypro_exe.write_text("", encoding="utf-8")

        def _mock_copytree(src: Path, dst: Path, dirs_exist_ok: bool = True) -> Path:
            dst_path = Path(dst)
            dst_path.mkdir(parents=True, exist_ok=True)
            (dst_path / "eddypro_rp.exe").write_text("", encoding="utf-8")
            (dst_path / "eddypro_fcc.exe").write_text("", encoding="utf-8")
            return dst_path

        with (
            patch(
                "eddypro_batch_processor.core.platform.system",
                return_value="Windows",
            ),
            patch(
                "eddypro_batch_processor.core.shutil.copytree",
                side_effect=_mock_copytree,
            ),
            patch(
                "eddypro_batch_processor.core.run_subprocess_with_monitoring",
                side_effect=[1],
            ) as mock_run,
        ):
            success = run_eddypro_with_monitoring(
                project_file=project_file,
                eddypro_executable=eddypro_exe,
                stream_output=False,
                metrics_interval=0.5,
                scenario_suffix="",
            )

        assert success is False
        assert mock_run.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__])
