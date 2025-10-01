"""Tests for core module functionality."""

import tempfile
from pathlib import Path

import pytest
import yaml

from eddypro_batch_processor.core import (
    EddyProBatchProcessor,
    load_config,
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
        }

        # Should not raise an exception
        validate_config(valid_config)


if __name__ == "__main__":
    pytest.main([__file__])
