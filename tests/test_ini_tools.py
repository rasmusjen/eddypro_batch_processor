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
            ("despike_meth", 0),
            ("despike_meth", 1),
            ("hf_meth", 1),
            ("hf_meth", 4),
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
            ("despike_meth", -1),
            ("despike_meth", 2),
            ("hf_meth", 0),
            ("hf_meth", 2),
            ("hf_meth", 3),
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
        params = {"rot_meth": 1, "tlag_meth": 2, "detrend_meth": 0, "despike_meth": 1}
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
        expected_params = {
            "rot_meth",
            "tlag_meth",
            "detrend_meth",
            "despike_meth",
            "hf_meth",
        }
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
despike_meth=0
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

        parameters = {
            "rot_meth": 3,
            "tlag_meth": 4,
            "detrend_meth": 1,
            "despike_meth": 1,
        }

        ini_tools.patch_ini_parameters(config, parameters)

        # Verify parameters were updated
        self.assertEqual(config.get("RawProcess_Settings", "rot_meth"), "3")
        self.assertEqual(config.get("RawProcess_Settings", "tlag_meth"), "4")
        self.assertEqual(config.get("RawProcess_Settings", "detrend_meth"), "1")
        # despike_meth maps to despike_vm in the INI file
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

        # Ensure no trailing empty line
        lines = output_path.read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines)
        self.assertTrue(lines[-1].strip())

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
        parameters = {"rot_meth": 3, "despike_meth": 1}

        ini_tools.create_patched_ini(self.template_path, output_path, parameters)

        # Verify output file exists and has correct values
        self.assertTrue(output_path.exists())

        config = configparser.ConfigParser()
        config.read(output_path, encoding="utf-8")
        self.assertEqual(config.get("RawProcess_Settings", "rot_meth"), "3")
        # despike_meth maps to despike_vm in the INI file
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

        proj_file = "SITE.metadata"
        dyn_md = "SITE_dynamic_metadata.txt"
        data_path = "/abs/input/path"
        out_path = "/abs/output/path/scenario_rot1"

        # Ensure required sections exist in our minimal test INI by adding them
        if not config.has_section("Project"):
            config.add_section("Project")
        if not config.has_section("FluxCorrection_SpectralAnalysis_General"):
            config.add_section("FluxCorrection_SpectralAnalysis_General")
        if not config.has_section("RawProcess_General"):
            config.add_section("RawProcess_General")

        ini_tools.patch_ini_paths(
            config,
            site_id="SITE",
            proj_file=proj_file,
            dyn_metadata_file=dyn_md,
            data_path=data_path,
            out_path=out_path,
        )

        expected_metadata_path = f"{out_path}/SITE.metadata"
        self.assertEqual(config.get("Project", "file_name"), f"{out_path}/SITE.eddypro")
        self.assertEqual(config.get("Project", "proj_file"), expected_metadata_path)
        self.assertEqual(config.get("Project", "dyn_metadata_file"), dyn_md)
        self.assertEqual(config.get("Project", "out_path"), out_path)
        self.assertEqual(config.get("RawProcess_General", "data_path"), data_path)
        self.assertEqual(
            config.get("FluxCorrection_SpectralAnalysis_General", "sa_bin_spectra"),
            f"{out_path}/eddypro_binned_cospectra",
        )
        self.assertEqual(
            config.get("FluxCorrection_SpectralAnalysis_General", "sa_full_spectra"),
            f"{out_path}/eddypro_full_cospectra",
        )

    def test_patch_project_metadata_sets_site_id_fields(self):
        """Project title and ID should be set to site_id."""
        config = configparser.ConfigParser()
        config.add_section("Project")
        config.set("Project", "creation_date", "")

        ini_tools.patch_project_metadata(
            config,
            site_id="GL-ZaF",
            year=2021,
            scenario_suffix="_rot1",
        )

        self.assertEqual(config.get("Project", "project_title"), "GL-ZaF")
        self.assertEqual(config.get("Project", "project_id"), "GL-ZaF")
        self.assertTrue(config.get("Project", "creation_date").strip())
        self.assertTrue(config.get("Project", "last_change_date").strip())

    def test_validate_eddypro_metadata(self):
        """Ensure metadata validation passes for a valid template file."""
        config = configparser.ConfigParser()
        config.add_section("Project")

        # Copy a real metadata template to a temp file
        repo_meta = Path("config") / "GL-ZaF_metadata_template.ini"
        self.assertTrue(
            repo_meta.exists(),
            msg="Expected repository metadata template to exist for the test",
        )
        tmp_meta = self.temp_dir / "SITE.metadata"
        shutil.copyfile(repo_meta, tmp_meta)

        config.set("Project", "proj_file", str(tmp_meta))

        # Should not raise
        ini_tools.validate_eddypro_metadata(config)

    def test_validate_eddypro_metadata_missing_file(self):
        """Validator should raise for missing metadata file."""
        config = configparser.ConfigParser()
        config.add_section("Project")
        config.set("Project", "proj_file", str(self.temp_dir / "missing.metadata"))

        with self.assertRaises(ini_tools.INIParameterError):
            ini_tools.validate_eddypro_metadata(config)

    def test_populate_metadata_file_sets_expected_fields(self):
        """Populate metadata from ECMD and verify key fields."""
        repo_meta = Path("config") / "metadata_template.ini"
        self.assertTrue(repo_meta.exists())

        metadata_path = self.temp_dir / "SITE.metadata"
        shutil.copyfile(repo_meta, metadata_path)

        ecmd_row = {
            "ALTITUDE": "38",
            "CANOPY_HEIGHT": "0.1",
            "LATITUDE": "74.48",
            "LONGITUDE": "-20.55",
            "ACQUISITION_FREQUENCY": "10",
            "FILE_DURATION": "30",
            "SA_HEIGHT": "3.16",
            "SA_WIND_DATA_FORMAT": "uvw",
            "SA_NORTH_ALIGNEMENT": "spar",
            "SA_NORTH_OFFSET": "60",
            "GA_TUBE_LENGTH": "71.1",
            "GA_TUBE_DIAMETER": "5.3",
            "GA_FLOWRATE": "12",
            "GA_NORTHWARD_SEPARATION": "-11",
            "GA_EASTWARD_SEPARATION": "-18",
            "GA_VERTICAL_SEPARATION": "0",
        }

        output_dir = self.temp_dir / "out"
        ini_tools.populate_metadata_file(
            metadata_path,
            site_id="SITE",
            output_dir=output_dir,
            ecmd_row=ecmd_row,
        )

        config = configparser.ConfigParser()
        config.read(metadata_path, encoding="utf-8")

        self.assertEqual(
            config.get("Project", "file_name"),
            (output_dir / "SITE.metadata").as_posix(),
        )
        self.assertEqual(config.get("Site", "site_id"), "SITE")
        self.assertEqual(config.get("Station", "station_id"), "SITE")
        self.assertEqual(config.get("Station", "station_name"), "SITE")
        self.assertEqual(config.get("Site", "altitude"), "38")
        self.assertEqual(config.get("Timing", "file_duration"), "30")
        self.assertEqual(config.get("Instruments", "instr_1_height"), "3.16")

    def test_populate_metadata_file_missing_ecmd_values_raises(self):
        """Missing ECMD values should raise validation errors."""
        repo_meta = Path("config") / "metadata_template.ini"
        metadata_path = self.temp_dir / "SITE.metadata"
        shutil.copyfile(repo_meta, metadata_path)

        ecmd_row = {
            "ALTITUDE": "",
            "CANOPY_HEIGHT": "0.1",
            "LATITUDE": "74.48",
            "LONGITUDE": "-20.55",
            "ACQUISITION_FREQUENCY": "10",
            "FILE_DURATION": "30",
            "SA_HEIGHT": "3.16",
            "SA_WIND_DATA_FORMAT": "uvw",
            "SA_NORTH_ALIGNEMENT": "spar",
            "SA_NORTH_OFFSET": "60",
            "GA_TUBE_LENGTH": "71.1",
            "GA_TUBE_DIAMETER": "5.3",
            "GA_FLOWRATE": "12",
            "GA_NORTHWARD_SEPARATION": "-11",
            "GA_EASTWARD_SEPARATION": "-18",
            "GA_VERTICAL_SEPARATION": "0",
        }

        with self.assertRaises(ini_tools.INIParameterError):
            ini_tools.populate_metadata_file(
                metadata_path,
                site_id="SITE",
                output_dir=self.temp_dir,
                ecmd_row=ecmd_row,
            )

    def test_populate_metadata_file_missing_section_raises(self):
        """Missing required sections should raise an error."""
        metadata_path = self.temp_dir / "SITE.metadata"
        metadata_path.write_text("[Project]\nfile_name=\n", encoding="utf-8")

        with self.assertRaises(ini_tools.INIParameterError):
            ini_tools.populate_metadata_file(
                metadata_path,
                site_id="SITE",
                output_dir=self.temp_dir,
                ecmd_row={"ALTITUDE": "10"},
            )

    def test_write_metadata_file_writes_header(self):
        """Metadata writer should include the GHG header and no trailing blanks."""
        config = configparser.ConfigParser()
        config.add_section("Project")
        config.set("Project", "file_name", "SITE.metadata")

        output_path = self.temp_dir / "out.metadata"
        ini_tools.write_metadata_file(config, output_path)

        text = output_path.read_text(encoding="utf-8")
        assert text.startswith(";GHG_METADATA\n")
        assert text.splitlines()[-1].strip()

    def test_write_project_file_with_metadata(self):
        """Project writer should populate metadata after writing .eddypro."""
        project_config = configparser.ConfigParser()
        project_config.add_section("Project")
        project_config.set("Project", "file_name", "SITE.eddypro")

        metadata_path = self.temp_dir / "SITE.metadata"
        metadata_path.write_text(
            "[Project]\nfile_name=\n"
            "[Site]\nsite_id=\n"
            "[Station]\nstation_id=\nstation_name=\n"
            "[Timing]\nacquisition_frequency=\nfile_duration=\n"
            "[Instruments]\ninstr_1_height=\n",
            encoding="utf-8",
        )

        ecmd_row = {
            "ALTITUDE": "38",
            "CANOPY_HEIGHT": "0.1",
            "LATITUDE": "74.48",
            "LONGITUDE": "-20.55",
            "ACQUISITION_FREQUENCY": "10",
            "FILE_DURATION": "30",
            "SA_HEIGHT": "3.16",
            "SA_WIND_DATA_FORMAT": "uvw",
            "SA_NORTH_ALIGNEMENT": "spar",
            "SA_NORTH_OFFSET": "60",
            "GA_TUBE_LENGTH": "71.1",
            "GA_TUBE_DIAMETER": "5.3",
            "GA_FLOWRATE": "12",
            "GA_NORTHWARD_SEPARATION": "-11",
            "GA_EASTWARD_SEPARATION": "-18",
            "GA_VERTICAL_SEPARATION": "0",
        }

        project_path = self.temp_dir / "SITE.eddypro"
        ini_tools.write_project_file_with_metadata(
            project_config,
            project_path,
            metadata_path=metadata_path,
            site_id="SITE",
            output_dir=self.temp_dir,
            ecmd_row=ecmd_row,
        )

        assert project_path.exists()
        parser = configparser.ConfigParser()
        parser.read(metadata_path, encoding="utf-8")
        assert parser.get("Site", "site_id") == "SITE"


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
        parameters = {
            "rot_meth": 3,
            "tlag_meth": 4,
            "detrend_meth": 1,
            "despike_meth": 0,
        }
        result = ini_tools.generate_scenario_suffix(parameters)

        # Should be sorted by parameter name alphabetically
        # despike_meth, detrend_meth, rot_meth, tlag_meth
        expected = "_spk0_det1_rot3_tlag4"
        self.assertEqual(result, expected)

    def test_generate_scenario_suffix_with_hf_meth(self):
        """Suffix should include hf when hf_meth provided (alphabetical order)."""
        parameters = {
            "rot_meth": 1,
            "hf_meth": 4,
            "tlag_meth": 2,
        }
        result = ini_tools.generate_scenario_suffix(parameters)
        # Alphabetical order of keys: hf_meth, rot_meth, tlag_meth -> hf, rot, tlag
        self.assertEqual(result, "_hf4_rot1_tlag2")

    def test_generate_scenario_suffix_deterministic(self):
        """Test that suffix generation is deterministic."""
        parameters = {"despike_meth": 1, "rot_meth": 1, "tlag_meth": 2}

        # Generate suffix multiple times
        results = [ini_tools.generate_scenario_suffix(parameters) for _ in range(5)]

        # All results should be identical
        self.assertTrue(all(r == results[0] for r in results))
        # Should be sorted alphabetically: despike_meth, rot_meth, tlag_meth
        self.assertEqual(results[0], "_spk1_rot1_tlag2")

    def test_generate_scenario_suffix_unknown_parameter(self):
        """Test suffix generation with unknown parameter name."""
        parameters = {"unknown_param": 1}
        result = ini_tools.generate_scenario_suffix(parameters)

        # Should fallback to original parameter name
        self.assertEqual(result, "_unknown_param1")


class TestConditionalDateRanges(unittest.TestCase):
    """Test conditional date/time range population."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_year = 2021
        self.config = configparser.ConfigParser()

        # Create required sections
        self.config.add_section("RawProcess_Settings")
        self.config.add_section("RawProcess_TiltCorrection_Settings")
        self.config.add_section("RawProcess_TimelagOptimization_Settings")

        # Initialize empty date/time fields
        self.config.set("RawProcess_TiltCorrection_Settings", "pf_start_date", "")
        self.config.set("RawProcess_TiltCorrection_Settings", "pf_end_date", "")
        self.config.set("RawProcess_TiltCorrection_Settings", "pf_start_time", "")
        self.config.set("RawProcess_TiltCorrection_Settings", "pf_end_time", "")

        self.config.set("RawProcess_TimelagOptimization_Settings", "to_start_date", "")
        self.config.set("RawProcess_TimelagOptimization_Settings", "to_end_date", "")
        self.config.set("RawProcess_TimelagOptimization_Settings", "to_start_time", "")
        self.config.set("RawProcess_TimelagOptimization_Settings", "to_end_time", "")

    def test_patch_date_ranges_rot_meth_3_planar_fit(self):
        """Test date/time population when rot_meth=3 (Planar Fit)."""
        # Set rot_meth to 3 (Planar Fit)
        self.config.set("RawProcess_Settings", "rot_meth", "3")
        self.config.set("RawProcess_Settings", "tlag_meth", "2")

        # Apply conditional patching
        ini_tools.patch_conditional_date_ranges(self.config, year=self.test_year)

        # Verify planar fit date/time fields are populated
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_start_date"),
            "2021-01-01",
        )
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_end_date"),
            "2021-12-31",
        )
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_start_time"),
            "00:00",
        )
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_end_time"),
            "23:59",
        )

        # Verify time-lag optimization fields remain empty
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_start_date"),
            "",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_end_date"),
            "",
        )

    def test_patch_date_ranges_tlag_meth_4_optimization(self):
        """Test date/time population when tlag_meth=4 (optimization)."""
        # Set tlag_meth to 4 (time-lag optimization)
        self.config.set("RawProcess_Settings", "rot_meth", "1")
        self.config.set("RawProcess_Settings", "tlag_meth", "4")

        # Apply conditional patching
        ini_tools.patch_conditional_date_ranges(self.config, year=self.test_year)

        # Verify time-lag optimization date/time fields are populated
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_start_date"),
            "2021-01-01",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_end_date"),
            "2021-12-31",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_start_time"),
            "00:00",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_end_time"),
            "23:59",
        )

        # Verify planar fit fields remain empty
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_start_date"),
            "",
        )
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_end_date"), ""
        )

    def test_patch_date_ranges_both_conditions(self):
        """Test date/time population when both rot_meth=3 and tlag_meth=4."""
        # Set both conditions
        self.config.set("RawProcess_Settings", "rot_meth", "3")
        self.config.set("RawProcess_Settings", "tlag_meth", "4")

        # Apply conditional patching
        ini_tools.patch_conditional_date_ranges(self.config, year=self.test_year)

        # Verify both sets of date/time fields are populated
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_start_date"),
            "2021-01-01",
        )
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_end_date"),
            "2021-12-31",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_start_date"),
            "2021-01-01",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_end_date"),
            "2021-12-31",
        )

    def test_patch_date_ranges_neither_condition(self):
        """Test no population when neither condition is met."""
        # Set rot_meth=1 and tlag_meth=2 (neither triggers population)
        self.config.set("RawProcess_Settings", "rot_meth", "1")
        self.config.set("RawProcess_Settings", "tlag_meth", "2")

        # Apply conditional patching
        ini_tools.patch_conditional_date_ranges(self.config, year=self.test_year)

        # Verify all date/time fields remain empty
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_start_date"),
            "",
        )
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_end_date"), ""
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_start_date"),
            "",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_end_date"),
            "",
        )

    def test_patch_date_ranges_different_year(self):
        """Test date/time population with a different year."""
        self.config.set("RawProcess_Settings", "rot_meth", "3")
        self.config.set("RawProcess_Settings", "tlag_meth", "4")

        # Apply with year 2023
        ini_tools.patch_conditional_date_ranges(self.config, year=2023)

        # Verify correct year is used
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_start_date"),
            "2023-01-01",
        )
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_end_date"),
            "2023-12-31",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_start_date"),
            "2023-01-01",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_end_date"),
            "2023-12-31",
        )

    def test_patch_date_ranges_missing_section_rot_meth_3(self):
        """Test error when rot_meth=3 but TiltCorrection section is missing."""
        # Remove the required section
        self.config.remove_section("RawProcess_TiltCorrection_Settings")
        self.config.set("RawProcess_Settings", "rot_meth", "3")

        # Should raise error
        with self.assertRaises(ini_tools.INIParameterError) as cm:
            ini_tools.patch_conditional_date_ranges(self.config, year=self.test_year)

        self.assertIn("RawProcess_TiltCorrection_Settings", str(cm.exception))
        self.assertIn("rot_meth=3", str(cm.exception))

    def test_patch_date_ranges_missing_section_tlag_meth_4(self):
        """Test error when tlag_meth=4 but TimelagOptimization section missing."""
        # Remove the required section
        self.config.remove_section("RawProcess_TimelagOptimization_Settings")
        self.config.set("RawProcess_Settings", "tlag_meth", "4")

        # Should raise error
        with self.assertRaises(ini_tools.INIParameterError) as cm:
            ini_tools.patch_conditional_date_ranges(self.config, year=self.test_year)

        self.assertIn("RawProcess_TimelagOptimization_Settings", str(cm.exception))
        self.assertIn("tlag_meth=4", str(cm.exception))

    def test_patch_date_ranges_no_rawprocess_settings_section(self):
        """Test graceful handling when RawProcess_Settings section is missing."""
        # Remove RawProcess_Settings section entirely
        self.config.remove_section("RawProcess_Settings")

        # Should not raise error, just do nothing
        try:
            ini_tools.patch_conditional_date_ranges(self.config, year=self.test_year)
        except Exception as e:
            self.fail(f"Should not raise exception: {e}")

        # Verify fields remain empty
        self.assertEqual(
            self.config.get("RawProcess_TiltCorrection_Settings", "pf_start_date"),
            "",
        )
        self.assertEqual(
            self.config.get("RawProcess_TimelagOptimization_Settings", "to_start_date"),
            "",
        )


if __name__ == "__main__":
    unittest.main()
