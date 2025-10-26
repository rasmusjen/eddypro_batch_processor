#!/usr/bin/env python3
"""
Unit tests for INI tools module.

Tests parameter validation, INI file patching, and scenario suffix generation.
"""

import configparser
import shutil
import tempfile
import unittest
from pathlib import Path

from src.eddypro_batch_processor import ini_tools


class TestParameterValidation(unittest.TestCase):
    """Test parameter validation functionality."""

    def test_validate_parameter_valid_values(self):
        """Test validation with valid parameter values."""
        # Test all valid parameter combinations
        test_cases = [
            ("rot_meth", 1),
            ("rot_meth", 3),
            ("tlag_meth", 2),
            ("tlag_meth", 4),
            ("detrend_meth", 0),
            ("detrend_meth", 1),
            ("despike_vm", 0),
            ("despike_vm", 1),
        ]

        for param_name, value in test_cases:
            with self.subTest(param=param_name, value=value):
                result = ini_tools.validate_parameter(param_name, value)
                self.assertEqual(result, value)

    def test_validate_parameter_invalid_values(self):
        """Test validation with invalid parameter values."""
        test_cases = [
            ("rot_meth", 0),
            ("rot_meth", 2),
            ("rot_meth", 4),
            ("tlag_meth", 0),
            ("tlag_meth", 1),
            ("tlag_meth", 3),
            ("detrend_meth", -1),
            ("detrend_meth", 2),
            ("despike_vm", -1),
            ("despike_vm", 2),
        ]

        for param_name, value in test_cases:
            with self.subTest(param=param_name, value=value):  # noqa: SIM117
                with self.assertRaises(ini_tools.INIParameterError):
                    ini_tools.validate_parameter(param_name, value)

    def test_validate_parameter_unknown_parameter(self):
        """Test validation with unknown parameter name."""
        with self.assertRaises(ini_tools.INIParameterError) as cm:
            ini_tools.validate_parameter("unknown_param", 1)

        self.assertIn("Unknown parameter 'unknown_param'", str(cm.exception))
        self.assertIn("Available parameters:", str(cm.exception))

    def test_validate_parameter_non_integer_values(self):
        """Test validation with non-integer values."""
        # Valid conversions
        result = ini_tools.validate_parameter("rot_meth", "1")
        self.assertEqual(result, 1)

        result = ini_tools.validate_parameter("rot_meth", 1.0)
        self.assertEqual(result, 1)

        # Invalid conversions
        invalid_values = ["invalid", None, [1]]
        for value in invalid_values:
            with self.subTest(value=value):  # noqa: SIM117
                with self.assertRaises(ini_tools.INIParameterError):
                    ini_tools.validate_parameter("rot_meth", value)

    def test_validate_parameters_dict(self):
        """Test validation of parameter dictionaries."""
        # Valid parameters
        params = {"rot_meth": 1, "tlag_meth": 2, "detrend_meth": 0, "despike_vm": 1}
        result = ini_tools.validate_parameters(params)
        self.assertEqual(result, params)

        # Invalid parameter in dict
        invalid_params = {
            "rot_meth": 1,
            "tlag_meth": 5,  # Invalid value
        }
        with self.assertRaises(ini_tools.INIParameterError):
            ini_tools.validate_parameters(invalid_params)

    def test_get_parameter_info(self):
        """Test getting parameter information."""
        info = ini_tools.get_parameter_info()

        # Check that all expected parameters are present
        expected_params = {"rot_meth", "tlag_meth", "detrend_meth", "despike_vm"}
        self.assertEqual(set(info.keys()), expected_params)

        # Check structure of parameter info
        for _param_name, param_info in info.items():
            self.assertIn("section", param_info)
            self.assertIn("allowed_values", param_info)
            self.assertIn("description", param_info)
            self.assertIsInstance(param_info["section"], str)
            self.assertIsInstance(param_info["allowed_values"], set)
            self.assertIsInstance(param_info["description"], str)


class TestINIFileOperations(unittest.TestCase):
    """Test INI file reading, patching, and writing operations."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal test INI file
        self.test_ini_content = """[Project]
title=Test Project

[RawProcess_Settings]
rot_meth=1
detrend_meth=0
tlag_meth=2

[RawProcess_ParameterSettings]
despike_vm=0
"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.template_path = self.temp_dir / "template.ini"
        with open(self.template_path, "w", encoding="utf-8") as f:
            f.write(self.test_ini_content)

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        shutil.rmtree(self.temp_dir)

    def test_read_ini_template_success(self):
        """Test successful reading of INI template."""
        config = ini_tools.read_ini_template(self.template_path)

        self.assertIsInstance(config, configparser.ConfigParser)
        self.assertTrue(config.has_section("RawProcess_Settings"))
        self.assertTrue(config.has_section("RawProcess_ParameterSettings"))
        self.assertEqual(config.get("RawProcess_Settings", "rot_meth"), "1")

    def test_read_ini_template_not_found(self):
        """Test reading non-existent INI template."""
        nonexistent_path = self.temp_dir / "nonexistent.ini"

        with self.assertRaises(FileNotFoundError):
            ini_tools.read_ini_template(nonexistent_path)

    def test_read_ini_template_malformed(self):
        """Test reading malformed INI template."""
        malformed_path = self.temp_dir / "malformed.ini"
        with open(malformed_path, "w", encoding="utf-8") as f:
            f.write("[Section\ninvalid ini content")

        with self.assertRaises(configparser.Error):
            ini_tools.read_ini_template(malformed_path)

    def test_patch_ini_parameters(self):
        """Test patching INI configuration with parameters."""
        config = ini_tools.read_ini_template(self.template_path)

        parameters = {"rot_meth": 3, "tlag_meth": 4, "detrend_meth": 1, "despike_vm": 1}

        ini_tools.patch_ini_parameters(config, parameters)

        # Verify parameters were updated
        self.assertEqual(config.get("RawProcess_Settings", "rot_meth"), "3")
        self.assertEqual(config.get("RawProcess_Settings", "tlag_meth"), "4")
        self.assertEqual(config.get("RawProcess_Settings", "detrend_meth"), "1")
        self.assertEqual(config.get("RawProcess_ParameterSettings", "despike_vm"), "1")

    def test_patch_ini_parameters_missing_section(self):
        """Test patching INI with missing required section."""
        # Create config without required section
        minimal_ini = "[Project]\ntitle=Test"
        minimal_path = self.temp_dir / "minimal.ini"
        with open(minimal_path, "w", encoding="utf-8") as f:
            f.write(minimal_ini)

        config = ini_tools.read_ini_template(minimal_path)
        parameters = {"rot_meth": 3}

        with self.assertRaises(ini_tools.INIParameterError) as cm:
            ini_tools.patch_ini_parameters(config, parameters)

        self.assertIn(
            "Required section 'RawProcess_Settings' missing", str(cm.exception)
        )

    def test_write_ini_file(self):
        """Test writing INI configuration to file."""
        config = ini_tools.read_ini_template(self.template_path)
        output_path = self.temp_dir / "output.ini"

        ini_tools.write_ini_file(config, output_path)

        # Verify file was written
        self.assertTrue(output_path.exists())

        # Verify content can be read back
        new_config = configparser.ConfigParser()
        new_config.read(output_path, encoding="utf-8")
        self.assertEqual(
            new_config.get("RawProcess_Settings", "rot_meth"),
            config.get("RawProcess_Settings", "rot_meth"),
        )

    def test_write_ini_file_creates_directories(self):
        """Test that write_ini_file creates output directories."""
        config = ini_tools.read_ini_template(self.template_path)
        nested_path = self.temp_dir / "subdir" / "nested" / "output.ini"

        ini_tools.write_ini_file(config, nested_path)

        self.assertTrue(nested_path.exists())
        self.assertTrue(nested_path.parent.exists())

    def test_create_patched_ini_with_parameters(self):
        """Test complete INI patching workflow with parameters."""
        output_path = self.temp_dir / "patched.ini"
        parameters = {"rot_meth": 3, "despike_vm": 1}

        ini_tools.create_patched_ini(self.template_path, output_path, parameters)

        # Verify output file exists and has correct values
        self.assertTrue(output_path.exists())

        config = configparser.ConfigParser()
        config.read(output_path, encoding="utf-8")
        self.assertEqual(config.get("RawProcess_Settings", "rot_meth"), "3")
        self.assertEqual(config.get("RawProcess_ParameterSettings", "despike_vm"), "1")
        # Unchanged parameters should remain the same
        self.assertEqual(config.get("RawProcess_Settings", "tlag_meth"), "2")

    def test_create_patched_ini_without_parameters(self):
        """Test INI patching workflow without parameters."""
        output_path = self.temp_dir / "patched.ini"

        ini_tools.create_patched_ini(self.template_path, output_path)

        # Verify output file exists and is identical to template
        self.assertTrue(output_path.exists())

        config = configparser.ConfigParser()
        config.read(output_path, encoding="utf-8")
        self.assertEqual(config.get("RawProcess_Settings", "rot_meth"), "1")
        self.assertEqual(config.get("RawProcess_Settings", "tlag_meth"), "2")

    def test_create_patched_ini_invalid_parameters(self):
        """Test INI patching with invalid parameters."""
        output_path = self.temp_dir / "patched.ini"
        invalid_parameters = {"rot_meth": 5}  # Invalid value

        with self.assertRaises(ini_tools.INIParameterError):
            ini_tools.create_patched_ini(
                self.template_path, output_path, invalid_parameters
            )

        # Verify output file was not created
        self.assertFalse(output_path.exists())

    def test_patch_ini_paths_updates_expected_fields(self):
        """Test that patch_ini_paths updates key Project and data path fields."""
        config = ini_tools.read_ini_template(self.template_path)

        proj_file = "SITE_2021_rot1.eddypro"
        dyn_md = "SITE_dynamic_metadata.txt"
        data_path = "/abs/input/path"
        out_path = "/abs/output/path/scenario_rot1"

        # Ensure required sections exist in our minimal test INI by adding them
        if not config.has_section("Project"):
            config.add_section("Project")
        if not config.has_section("RawProcess_General"):
            config.add_section("RawProcess_General")

        ini_tools.patch_ini_paths(
            config,
            proj_file=proj_file,
            dyn_metadata_file=dyn_md,
            data_path=data_path,
            out_path=out_path,
        )

        self.assertEqual(config.get("Project", "proj_file"), proj_file)
        self.assertEqual(config.get("Project", "dyn_metadata_file"), dyn_md)
        self.assertEqual(config.get("Project", "out_path"), out_path)
        self.assertEqual(config.get("RawProcess_General", "data_path"), data_path)


class TestScenarioSuffixGeneration(unittest.TestCase):
    """Test scenario suffix generation functionality."""

    def test_generate_scenario_suffix_empty(self):
        """Test suffix generation with empty parameters."""
        result = ini_tools.generate_scenario_suffix({})
        self.assertEqual(result, "")

    def test_generate_scenario_suffix_single_parameter(self):
        """Test suffix generation with single parameter."""
        parameters = {"rot_meth": 1}
        result = ini_tools.generate_scenario_suffix(parameters)
        self.assertEqual(result, "_rot1")

    def test_generate_scenario_suffix_multiple_parameters(self):
        """Test suffix generation with multiple parameters."""
        parameters = {"rot_meth": 3, "tlag_meth": 4, "detrend_meth": 1, "despike_vm": 0}
        result = ini_tools.generate_scenario_suffix(parameters)

        # Should be sorted by parameter name alphabetically
        # despike_vm, detrend_meth, rot_meth, tlag_meth
        expected = "_spk0_det1_rot3_tlag4"
        self.assertEqual(result, expected)

    def test_generate_scenario_suffix_deterministic(self):
        """Test that suffix generation is deterministic."""
        parameters = {"despike_vm": 1, "rot_meth": 1, "tlag_meth": 2}

        # Generate suffix multiple times
        results = [ini_tools.generate_scenario_suffix(parameters) for _ in range(5)]

        # All results should be identical
        self.assertTrue(all(r == results[0] for r in results))
        # Should be sorted alphabetically: despike_vm, rot_meth, tlag_meth
        self.assertEqual(results[0], "_spk1_rot1_tlag2")

    def test_generate_scenario_suffix_unknown_parameter(self):
        """Test suffix generation with unknown parameter name."""
        parameters = {"unknown_param": 1}
        result = ini_tools.generate_scenario_suffix(parameters)

        # Should fallback to original parameter name
        self.assertEqual(result, "_unknown_param1")


if __name__ == "__main__":
    unittest.main()
