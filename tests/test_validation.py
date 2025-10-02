"""
Tests for the validation module.

Covers configuration validation, path checks, ECMD schema and sanity checks.
"""

import csv
import tempfile
from pathlib import Path

import pytest

from src.eddypro_batch_processor import validation


class TestValidationError:
    """Test ValidationError exception class."""

    def test_validation_error_can_be_raised(self):
        """Test that ValidationError can be instantiated and raised."""
        with pytest.raises(validation.ValidationError, match="test error"):
            raise validation.ValidationError("test error")


class TestValidateConfigStructure:
    """Test configuration structure validation."""

    def test_valid_config_passes(self):
        """Test that a valid configuration passes validation."""
        config = {
            "eddypro_executable": "/path/to/exe",
            "site_id": "GL-ZaF",
            "years_to_process": [2021, 2022],
            "input_dir_pattern": "/input/{site_id}/{year}",
            "output_dir_pattern": "/output/{site_id}/{year}",
            "ecmd_file": "/path/to/ecmd.csv",
            "stream_output": True,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 4,
            "metrics_interval_seconds": 0.5,
            "reports_dir": None,
            "report_charts": "plotly",
        }
        errors = validation.validate_config_structure(config)
        assert errors == []

    def test_missing_required_keys(self):
        """Test that missing required keys are detected."""
        config = {"site_id": "GL-ZaF"}
        errors = validation.validate_config_structure(config)
        assert len(errors) > 0
        assert "Missing required configuration keys" in errors[0]

    def test_invalid_site_id_type(self):
        """Test that non-string site_id is rejected."""
        config = {
            "eddypro_executable": "/path/to/exe",
            "site_id": 123,  # Should be string
            "years_to_process": [2021],
            "input_dir_pattern": "/input/{site_id}/{year}",
            "output_dir_pattern": "/output/{site_id}/{year}",
            "ecmd_file": "/path/to/ecmd.csv",
            "stream_output": True,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 4,
            "metrics_interval_seconds": 0.5,
            "reports_dir": None,
            "report_charts": "plotly",
        }
        errors = validation.validate_config_structure(config)
        assert any("'site_id' must be a string" in err for err in errors)

    def test_invalid_years_type(self):
        """Test that non-list years_to_process is rejected."""
        config = {
            "eddypro_executable": "/path/to/exe",
            "site_id": "GL-ZaF",
            "years_to_process": 2021,  # Should be list
            "input_dir_pattern": "/input/{site_id}/{year}",
            "output_dir_pattern": "/output/{site_id}/{year}",
            "ecmd_file": "/path/to/ecmd.csv",
            "stream_output": True,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 4,
            "metrics_interval_seconds": 0.5,
            "reports_dir": None,
            "report_charts": "plotly",
        }
        errors = validation.validate_config_structure(config)
        assert any("'years_to_process' must be a list" in err for err in errors)

    def test_invalid_report_charts_value(self):
        """Test that invalid report_charts value is rejected."""
        config = {
            "eddypro_executable": "/path/to/exe",
            "site_id": "GL-ZaF",
            "years_to_process": [2021],
            "input_dir_pattern": "/input/{site_id}/{year}",
            "output_dir_pattern": "/output/{site_id}/{year}",
            "ecmd_file": "/path/to/ecmd.csv",
            "stream_output": True,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 4,
            "metrics_interval_seconds": 0.5,
            "reports_dir": None,
            "report_charts": "invalid",  # Must be plotly, svg, or none
        }
        errors = validation.validate_config_structure(config)
        assert any(
            "'report_charts' must be one of [plotly, svg, none]" in err
            for err in errors
        )

    def test_invalid_log_level(self):
        """Test that invalid log_level value is rejected."""
        config = {
            "eddypro_executable": "/path/to/exe",
            "site_id": "GL-ZaF",
            "years_to_process": [2021],
            "input_dir_pattern": "/input/{site_id}/{year}",
            "output_dir_pattern": "/output/{site_id}/{year}",
            "ecmd_file": "/path/to/ecmd.csv",
            "stream_output": True,
            "log_level": "INVALID",  # Invalid log level
            "multiprocessing": False,
            "max_processes": 4,
            "metrics_interval_seconds": 0.5,
            "reports_dir": None,
            "report_charts": "plotly",
        }
        errors = validation.validate_config_structure(config)
        assert any("'log_level' must be one of" in err for err in errors)


class TestValidatePaths:
    """Test path validation."""

    def test_missing_eddypro_executable(self):
        """Test that missing EddyPro executable is detected."""
        config = {
            "eddypro_executable": "/nonexistent/path/to/exe",
            "site_id": "GL-ZaF",
            "years_to_process": [2021],
            "input_dir_pattern": "/input/{site_id}/{year}",
            "output_dir_pattern": "/output/{site_id}/{year}",
            "ecmd_file": "/path/to/ecmd.csv",
        }
        errors = validation.validate_paths(config, skip_ecmd=True)
        assert any("EddyPro executable not found" in err for err in errors)

    def test_invalid_input_pattern_missing_placeholders(self):
        """Test that input_dir_pattern without placeholders is rejected."""
        config = {
            "eddypro_executable": __file__,  # Use this file as placeholder
            "site_id": "GL-ZaF",
            "years_to_process": [2021],
            "input_dir_pattern": "/input/data",  # Missing {site_id} and {year}
            "output_dir_pattern": "/output/{site_id}/{year}",
            "ecmd_file": "/path/to/ecmd.csv",
        }
        errors = validation.validate_paths(config, skip_ecmd=True)
        assert any("'{site_id}' placeholder" in err for err in errors)
        assert any("'{year}' placeholder" in err for err in errors)

    def test_skip_ecmd_validation(self):
        """Test that ECMD validation can be skipped."""
        config = {
            "eddypro_executable": __file__,
            "site_id": "GL-ZaF",
            "years_to_process": [2021],
            "input_dir_pattern": "/input/{site_id}/{year}",
            "output_dir_pattern": "/output/{site_id}/{year}",
            "ecmd_file": "/nonexistent/ecmd.csv",
        }
        errors = validation.validate_paths(config, skip_ecmd=True)
        # Should not complain about ECMD file when skip_ecmd=True
        assert not any("ECMD file not found" in err for err in errors)


class TestValidateECMDSchema:
    """Test ECMD file schema validation."""

    def test_nonexistent_file(self):
        """Test that nonexistent ECMD file is detected."""
        errors = validation.validate_ecmd_schema(Path("/nonexistent/file.csv"))
        assert any("ECMD file not found" in err for err in errors)

    def test_valid_ecmd_file(self):
        """Test that a valid ECMD file passes validation."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "DATE_OF_VARIATION_EF",
                    "FILE_DURATION",
                    "ACQUISITION_FREQUENCY",
                    "CANOPY_HEIGHT",
                    "SA_MANUFACTURER",
                    "SA_MODEL",
                    "SA_HEIGHT",
                    "SA_WIND_DATA_FORMAT",
                    "SA_NORTH_ALIGNEMENT",
                    "SA_NORTH_OFFSET",
                    "GA_MANUFACTURER",
                    "GA_MODEL",
                    "GA_NORTHWARD_SEPARATION",
                    "GA_EASTWARD_SEPARATION",
                    "GA_VERTICAL_SEPARATION",
                    "GA_PATH",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "DATE_OF_VARIATION_EF": "202001010000",
                    "FILE_DURATION": "30",
                    "ACQUISITION_FREQUENCY": "10",
                    "CANOPY_HEIGHT": "0.1",
                    "SA_MANUFACTURER": "gill",
                    "SA_MODEL": "hs_50",
                    "SA_HEIGHT": "3.0",
                    "SA_WIND_DATA_FORMAT": "uvw",
                    "SA_NORTH_ALIGNEMENT": "spar",
                    "SA_NORTH_OFFSET": "60",
                    "GA_MANUFACTURER": "licor",
                    "GA_MODEL": "li7200",
                    "GA_NORTHWARD_SEPARATION": "-11",
                    "GA_EASTWARD_SEPARATION": "-18",
                    "GA_VERTICAL_SEPARATION": "0",
                    "GA_PATH": "open",
                }
            )
            temp_path = Path(f.name)

        try:
            errors = validation.validate_ecmd_schema(temp_path)
            assert errors == []
        finally:
            temp_path.unlink()

    def test_missing_required_columns(self):
        """Test that missing required columns are detected."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(
                f, fieldnames=["DATE_OF_VARIATION_EF", "FILE_DURATION"]
            )
            writer.writeheader()
            writer.writerow(
                {"DATE_OF_VARIATION_EF": "202001010000", "FILE_DURATION": "30"}
            )
            temp_path = Path(f.name)

        try:
            errors = validation.validate_ecmd_schema(temp_path)
            assert any("missing required columns" in err for err in errors)
        finally:
            temp_path.unlink()

    def test_closed_path_missing_columns(self):
        """Test that closed-path analyzer requires specific columns."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "DATE_OF_VARIATION_EF",
                    "FILE_DURATION",
                    "ACQUISITION_FREQUENCY",
                    "CANOPY_HEIGHT",
                    "SA_MANUFACTURER",
                    "SA_MODEL",
                    "SA_HEIGHT",
                    "SA_WIND_DATA_FORMAT",
                    "SA_NORTH_ALIGNEMENT",
                    "SA_NORTH_OFFSET",
                    "GA_MANUFACTURER",
                    "GA_MODEL",
                    "GA_NORTHWARD_SEPARATION",
                    "GA_EASTWARD_SEPARATION",
                    "GA_VERTICAL_SEPARATION",
                    "GA_PATH",
                    # Missing: GA_TUBE_LENGTH, GA_TUBE_DIAMETER, GA_FLOWRATE
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "DATE_OF_VARIATION_EF": "202001010000",
                    "FILE_DURATION": "30",
                    "ACQUISITION_FREQUENCY": "10",
                    "CANOPY_HEIGHT": "0.1",
                    "SA_MANUFACTURER": "gill",
                    "SA_MODEL": "hs_50",
                    "SA_HEIGHT": "3.0",
                    "SA_WIND_DATA_FORMAT": "uvw",
                    "SA_NORTH_ALIGNEMENT": "spar",
                    "SA_NORTH_OFFSET": "60",
                    "GA_MANUFACTURER": "licor",
                    "GA_MODEL": "li7200",
                    "GA_NORTHWARD_SEPARATION": "-11",
                    "GA_EASTWARD_SEPARATION": "-18",
                    "GA_VERTICAL_SEPARATION": "0",
                    "GA_PATH": "closed",
                }
            )
            temp_path = Path(f.name)

        try:
            errors = validation.validate_ecmd_schema(temp_path)
            assert any("GA_PATH='closed'" in err for err in errors)
        finally:
            temp_path.unlink()


class TestValidateECMDSanity:
    """Test ECMD file sanity checks."""

    def test_positive_acquisition_frequency(self):
        """Test that ACQUISITION_FREQUENCY must be positive."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "DATE_OF_VARIATION_EF",
                    "FILE_DURATION",
                    "ACQUISITION_FREQUENCY",
                    "CANOPY_HEIGHT",
                    "SA_HEIGHT",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "DATE_OF_VARIATION_EF": "202001010000",
                    "FILE_DURATION": "30",
                    "ACQUISITION_FREQUENCY": "-10",  # Invalid: negative
                    "CANOPY_HEIGHT": "0.1",
                    "SA_HEIGHT": "3.0",
                }
            )
            temp_path = Path(f.name)

        try:
            errors = validation.validate_ecmd_sanity(temp_path)
            assert any(
                "ACQUISITION_FREQUENCY must be positive" in err for err in errors
            )
        finally:
            temp_path.unlink()

    def test_positive_file_duration(self):
        """Test that FILE_DURATION must be positive."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "DATE_OF_VARIATION_EF",
                    "FILE_DURATION",
                    "ACQUISITION_FREQUENCY",
                    "CANOPY_HEIGHT",
                    "SA_HEIGHT",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "DATE_OF_VARIATION_EF": "202001010000",
                    "FILE_DURATION": "0",  # Invalid: must be positive
                    "ACQUISITION_FREQUENCY": "10",
                    "CANOPY_HEIGHT": "0.1",
                    "SA_HEIGHT": "3.0",
                }
            )
            temp_path = Path(f.name)

        try:
            errors = validation.validate_ecmd_sanity(temp_path)
            assert any("FILE_DURATION must be positive" in err for err in errors)
        finally:
            temp_path.unlink()

    def test_nonnegative_canopy_height(self):
        """Test that CANOPY_HEIGHT can be zero but not negative."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "DATE_OF_VARIATION_EF",
                    "FILE_DURATION",
                    "ACQUISITION_FREQUENCY",
                    "CANOPY_HEIGHT",
                    "SA_HEIGHT",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "DATE_OF_VARIATION_EF": "202001010000",
                    "FILE_DURATION": "30",
                    "ACQUISITION_FREQUENCY": "10",
                    "CANOPY_HEIGHT": "-1",  # Invalid: negative
                    "SA_HEIGHT": "3.0",
                }
            )
            temp_path = Path(f.name)

        try:
            errors = validation.validate_ecmd_sanity(temp_path)
            assert any("CANOPY_HEIGHT must be non-negative" in err for err in errors)
        finally:
            temp_path.unlink()

    def test_positive_sa_height(self):
        """Test that SA_HEIGHT must be positive."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "DATE_OF_VARIATION_EF",
                    "FILE_DURATION",
                    "ACQUISITION_FREQUENCY",
                    "CANOPY_HEIGHT",
                    "SA_HEIGHT",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "DATE_OF_VARIATION_EF": "202001010000",
                    "FILE_DURATION": "30",
                    "ACQUISITION_FREQUENCY": "10",
                    "CANOPY_HEIGHT": "0.1",
                    "SA_HEIGHT": "0",  # Invalid: must be positive
                }
            )
            temp_path = Path(f.name)

        try:
            errors = validation.validate_ecmd_sanity(temp_path)
            assert any("SA_HEIGHT must be positive" in err for err in errors)
        finally:
            temp_path.unlink()


class TestValidateConfigSanity:
    """Test configuration sanity checks."""

    def test_empty_years_to_process(self):
        """Test that years_to_process cannot be empty."""
        config = {
            "site_id": "GL-ZaF",
            "years_to_process": [],  # Invalid: empty
            "multiprocessing": False,
            "max_processes": 4,
            "metrics_interval_seconds": 0.5,
        }
        errors = validation.validate_config_sanity(config)
        assert any("'years_to_process' cannot be empty" in err for err in errors)

    def test_empty_site_id(self):
        """Test that site_id cannot be empty."""
        config = {
            "site_id": "",  # Invalid: empty
            "years_to_process": [2021],
            "multiprocessing": False,
            "max_processes": 4,
            "metrics_interval_seconds": 0.5,
        }
        errors = validation.validate_config_sanity(config)
        assert any("'site_id' cannot be empty" in err for err in errors)

    def test_multiprocessing_requires_positive_max_processes(self):
        """Test that max_processes must be positive when multiprocessing enabled."""
        config = {
            "site_id": "GL-ZaF",
            "years_to_process": [2021],
            "multiprocessing": True,
            "max_processes": 0,  # Invalid: must be positive
            "metrics_interval_seconds": 0.5,
        }
        errors = validation.validate_config_sanity(config)
        assert any(
            "'max_processes' must be positive when multiprocessing is enabled" in err
            for err in errors
        )

    def test_positive_metrics_interval(self):
        """Test that metrics_interval_seconds must be positive."""
        config = {
            "site_id": "GL-ZaF",
            "years_to_process": [2021],
            "multiprocessing": False,
            "max_processes": 4,
            "metrics_interval_seconds": 0,  # Invalid: must be positive
        }
        errors = validation.validate_config_sanity(config)
        assert any(
            "'metrics_interval_seconds' must be positive" in err for err in errors
        )


class TestValidateAll:
    """Test the complete validation workflow."""

    def test_validate_all_returns_categories(self):
        """Test that validate_all returns categorized results."""
        config = {
            "eddypro_executable": __file__,
            "site_id": "GL-ZaF",
            "years_to_process": [2021],
            "input_dir_pattern": "/input/{site_id}/{year}",
            "output_dir_pattern": "/output/{site_id}/{year}",
            "ecmd_file": "/path/to/ecmd.csv",
            "stream_output": True,
            "log_level": "INFO",
            "multiprocessing": False,
            "max_processes": 4,
            "metrics_interval_seconds": 0.5,
            "reports_dir": None,
            "report_charts": "plotly",
        }
        results = validation.validate_all(config, skip_paths=True, skip_ecmd=True)
        assert "config_structure" in results
        assert "config_sanity" in results
        assert "paths" in results
        assert "ecmd_schema" in results
        assert "ecmd_sanity" in results


class TestFormatValidationReport:
    """Test validation report formatting."""

    def test_format_report_with_no_errors(self):
        """Test report formatting with no errors."""
        results = {
            "config_structure": [],
            "config_sanity": [],
            "paths": [],
            "ecmd_schema": [],
            "ecmd_sanity": [],
        }
        report = validation.format_validation_report(results)
        assert "All validations passed" in report
        assert "✓" in report

    def test_format_report_with_errors(self):
        """Test report formatting with errors."""
        results = {
            "config_structure": ["Missing key: site_id"],
            "config_sanity": [],
            "paths": ["EddyPro executable not found"],
            "ecmd_schema": [],
            "ecmd_sanity": [],
        }
        report = validation.format_validation_report(results)
        assert "Total errors: 2" in report
        assert "❌" in report
        assert "Missing key: site_id" in report
        assert "EddyPro executable not found" in report
