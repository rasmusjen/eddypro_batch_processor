"""Tests for core module functionality."""

import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from eddypro_batch_processor import core
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

        # The command must be an argv list, not a shell string: with shell=True
        # the monitored PID would be cmd.exe rather than EddyPro.
        assert isinstance(rp_call["command"], list)
        assert isinstance(fcc_call["command"], list)
        assert "eddypro_rp.exe" in rp_call["command"][0]
        assert "eddypro_fcc.exe" in fcc_call["command"][0]
        assert str(project_file) in rp_call["command"]
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


class TestSubprocessOutputEchoing:
    """EddyPro output must reach the console exactly once.

    `setup_logging` always attaches a stdout StreamHandler, so when `log_output`
    is on the logger already puts each line on the console. Printing as well
    emitted everything twice, doubling log-file size and halving the interval
    between rotations on multi-hour runs.

    These assert on `print` rather than on captured log records: the logger is
    called exactly once either way, so a caplog-based test passes against the
    bug it is meant to catch.
    """

    MARKER = "EDDYPRO_MARKER_LINE"

    def _run(self, tmp_path, *, log_output):
        return core.run_subprocess_with_monitoring(
            command=[sys.executable, "-c", f"print('{self.MARKER}')"],
            working_dir=tmp_path,
            stream_output=True,
            log_output=log_output,
            monitoring_enabled=False,
            output_dir=tmp_path,
        )

    def test_no_direct_echo_when_the_logger_mirrors_output(self, tmp_path, caplog):
        """With log_output on, the logger is the single emitter."""
        with (
            patch("builtins.print") as mock_print,
            caplog.at_level(logging.INFO, logger="eddypro_batch_processor.eddypro"),
        ):
            assert self._run(tmp_path, log_output=True) == 0

        assert not any(
            self.MARKER in str(call) for call in mock_print.call_args_list
        ), "output was printed as well as logged, so each line appears twice"
        logged = [r for r in caplog.records if self.MARKER in r.getMessage()]
        assert len(logged) == 1, "the line must still reach the log exactly once"

    def test_direct_echo_survives_when_the_logger_is_silent(self, tmp_path):
        """With log_output off, printing is the only route to the console."""
        with patch("builtins.print") as mock_print:
            assert self._run(tmp_path, log_output=False) == 0

        assert any(
            self.MARKER in str(call) for call in mock_print.call_args_list
        ), "live progress was dropped entirely"


class TestCpuAffinity:
    """Pinning is an optimisation, so a bad value must never stop a run."""

    def test_performance_cores_derived_from_core_counts(self):
        """8 P-cores (2 threads each) + 4 E-cores = 20 logical / 12 physical."""
        with (patch("eddypro_batch_processor.core.psutil.cpu_count") as cpu_count,):
            cpu_count.side_effect = lambda logical=True: 20 if logical else 12
            assert core.resolve_performance_cores() == list(range(16))

    def test_no_hybrid_split_returns_none(self):
        """A uniform SMT CPU (8 cores / 16 threads) has no E-cores to avoid."""
        with patch("eddypro_batch_processor.core.psutil.cpu_count") as cpu_count:
            cpu_count.side_effect = lambda logical=True: 16 if logical else 8
            assert core.resolve_performance_cores() is None

    def test_no_smt_returns_none(self):
        """Without SMT the thread-count trick cannot identify core types."""
        with patch("eddypro_batch_processor.core.psutil.cpu_count") as cpu_count:
            cpu_count.side_effect = lambda logical=True: 8
            assert core.resolve_performance_cores() is None

    def test_absent_setting_leaves_affinity_untouched(self):
        with patch("eddypro_batch_processor.core.psutil.Process") as proc:
            core.apply_cpu_affinity({})
            proc.assert_not_called()

    def test_explicit_list_is_applied(self):
        with patch("eddypro_batch_processor.core.psutil.Process") as proc:
            core.apply_cpu_affinity({"cpu_affinity": [0, 1, 2, 3]})
            proc.return_value.cpu_affinity.assert_called_once_with([0, 1, 2, 3])

    def test_performance_keyword_uses_detection(self):
        with (
            patch("eddypro_batch_processor.core.psutil.Process") as proc,
            patch(
                "eddypro_batch_processor.core.resolve_performance_cores",
                return_value=[0, 1],
            ),
        ):
            core.apply_cpu_affinity({"cpu_affinity": "performance"})
            proc.return_value.cpu_affinity.assert_called_once_with([0, 1])

    def test_performance_keyword_no_split_is_a_no_op(self):
        with (
            patch("eddypro_batch_processor.core.psutil.Process") as proc,
            patch(
                "eddypro_batch_processor.core.resolve_performance_cores",
                return_value=None,
            ),
        ):
            core.apply_cpu_affinity({"cpu_affinity": "performance"})
            proc.return_value.cpu_affinity.assert_not_called()

    def test_garbage_value_is_ignored_not_raised(self):
        with patch("eddypro_batch_processor.core.psutil.Process") as proc:
            core.apply_cpu_affinity({"cpu_affinity": "wibble"})
            core.apply_cpu_affinity({"cpu_affinity": {"a": 1}})
            proc.return_value.cpu_affinity.assert_not_called()

    def test_failure_to_pin_does_not_abort_the_run(self):
        """A multi-hour run must not die because affinity could not be set."""
        with patch("eddypro_batch_processor.core.psutil.Process") as proc:
            proc.return_value.cpu_affinity.side_effect = OSError("denied")
            core.apply_cpu_affinity({"cpu_affinity": [0, 1]})  # must not raise
