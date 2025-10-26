#!/usr/bin/env python3
"""
INI Tools for EddyPro Batch Processor.

Utilities for parameterizing and validating EddyPro INI configuration files.
Supports patching specific parameters while preserving the rest of the template.
"""

import configparser
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Parameter validation rules
PARAMETER_VALIDATION: dict[str, dict[str, Any]] = {
    "rot_meth": {
        "section": "RawProcess_Settings",
        "allowed_values": {1, 3},
        "description": "Rotation method (1=DR double rotation, 3=PF planar fit)",
    },
    "tlag_meth": {
        "section": "RawProcess_Settings",
        "allowed_values": {2, 4},
        "description": "Time lag method (2=CMD, 4=AO)",
    },
    "detrend_meth": {
        "section": "RawProcess_Settings",
        "allowed_values": {0, 1},
        "description": "Detrend method (0=BA, 1=LD)",
    },
    "despike_vm": {
        "section": "RawProcess_ParameterSettings",
        "allowed_values": {0, 1},
        "description": "Spike removal method (0=VM97, 1=M13)",
    },
}


class INIParameterError(Exception):
    """Exception raised for invalid INI parameter values."""

    pass


def validate_parameter(param_name: str, value: Any) -> int:
    """
    Validate a parameter value against allowed values.

    Args:
        param_name: Name of the parameter to validate
        value: Value to validate

    Returns:
        The validated integer value

    Raises:
        INIParameterError: If parameter name is unknown or value is invalid
    """
    if param_name not in PARAMETER_VALIDATION:
        available_params = list(PARAMETER_VALIDATION.keys())
        raise INIParameterError(
            f"Unknown parameter '{param_name}'. "
            f"Available parameters: {available_params}"
        )

    # Convert to int if possible
    try:
        int_value = int(value)
    except (ValueError, TypeError) as e:
        raise INIParameterError(
            f"Parameter '{param_name}' must be an integer, got: {value}"
        ) from e

    # Check if value is in allowed set
    validation_info = PARAMETER_VALIDATION[param_name]
    allowed_values: set[int] = validation_info["allowed_values"]
    if int_value not in allowed_values:
        allowed = sorted(allowed_values)
        description = validation_info["description"]
        raise INIParameterError(
            f"Parameter '{param_name}' value {int_value} is not allowed. "
            f"Allowed values: {allowed}. {description}"
        )

    return int_value


def validate_parameters(parameters: dict[str, Any]) -> dict[str, int]:
    """
    Validate a dictionary of parameters.

    Args:
        parameters: Dictionary of parameter name -> value pairs

    Returns:
        Dictionary of validated parameter name -> int value pairs

    Raises:
        INIParameterError: If any parameter is invalid
    """
    validated = {}
    for param_name, value in parameters.items():
        validated[param_name] = validate_parameter(param_name, value)

    logger.debug(f"Validated parameters: {validated}")
    return validated


def read_ini_template(template_path: Path) -> configparser.ConfigParser:
    """
    Read an INI template file.

    Args:
        template_path: Path to the INI template file

    Returns:
        ConfigParser object with the template contents

    Raises:
        FileNotFoundError: If template file doesn't exist
        configparser.Error: If INI file is malformed
    """
    if not template_path.exists():
        raise FileNotFoundError(f"INI template not found: {template_path}")

    config = configparser.ConfigParser()
    try:
        config.read(template_path, encoding="utf-8")
    except configparser.Error as e:
        raise configparser.Error(
            f"Failed to parse INI template {template_path}: {e}"
        ) from e
    else:
        logger.debug(f"Read INI template from {template_path}")
        return config


def patch_ini_parameters(
    config: configparser.ConfigParser, parameters: dict[str, int]
) -> None:
    """
    Patch INI configuration with validated parameters.

    Args:
        config: ConfigParser object to modify in-place
        parameters: Dictionary of validated parameter name -> value pairs

    Raises:
        INIParameterError: If required section is missing
    """
    for param_name, value in parameters.items():
        validation_info = PARAMETER_VALIDATION[param_name]
        section_name: str = validation_info["section"]

        # Ensure section exists
        if not config.has_section(section_name):
            raise INIParameterError(
                f"Required section '{section_name}' missing from INI template "
                f"for parameter '{param_name}'"
            )

        # Set the parameter value
        config.set(section_name, param_name, str(value))
        logger.debug(f"Set {section_name}.{param_name} = {value}")


def write_ini_file(config: configparser.ConfigParser, output_path: Path) -> None:
    """
    Write INI configuration to file.

    Args:
        config: ConfigParser object to write
        output_path: Path where to write the INI file

    Raises:
        OSError: If file cannot be written
    """
    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            config.write(f)

        logger.debug(f"Wrote INI file to {output_path}")
    except OSError as e:
        raise OSError(f"Failed to write INI file {output_path}: {e}") from e


def patch_ini_paths(
    config: configparser.ConfigParser,
    *,
    proj_file: str,
    dyn_metadata_file: str,
    data_path: str,
    out_path: str,
) -> None:
    """Patch essential path fields inside an EddyPro INI/eddypro project file.

    Args:
        config: Parsed INI configuration to modify in-place
        proj_file: Project filename (typically the .eddypro file name)
        dyn_metadata_file: Dynamic metadata filename (.txt) expected by EddyPro
        data_path: Absolute path to input raw data
        out_path: Absolute path to output directory for this run/scenario

    Raises:
        INIParameterError: If required sections are missing
    """
    # Validate sections
    if not config.has_section("Project"):
        raise INIParameterError("Required section 'Project' missing from template")
    if not config.has_section("RawProcess_General"):
        raise INIParameterError(
            "Required section 'RawProcess_General' missing from template"
        )

    # Project-level paths
    config.set("Project", "proj_file", proj_file)
    config.set("Project", "dyn_metadata_file", dyn_metadata_file)
    config.set("Project", "out_path", out_path)

    # Input data path
    config.set("RawProcess_General", "data_path", data_path)

    logger.debug(
        "Patched paths: Project.proj_file=%s, Project.dyn_metadata_file=%s, "
        "Project.out_path=%s, RawProcess_General.data_path=%s",
        proj_file,
        dyn_metadata_file,
        out_path,
        data_path,
    )


def create_patched_ini(
    template_path: Path, output_path: Path, parameters: dict[str, Any] | None = None
) -> None:
    """
    Create a patched INI file from template with parameter overrides.

    Args:
        template_path: Path to the INI template file
        output_path: Path where to write the patched INI file
        parameters: Dictionary of parameter name -> value pairs to override

    Raises:
        FileNotFoundError: If template file doesn't exist
        INIParameterError: If any parameter is invalid
        configparser.Error: If INI file is malformed
        OSError: If output file cannot be written
    """
    # Read template
    config = read_ini_template(template_path)

    # Apply parameter overrides if provided
    if parameters:
        validated_params = validate_parameters(parameters)
        patch_ini_parameters(config, validated_params)
        logger.info(f"Applied parameter overrides: {validated_params}")
    else:
        logger.info("No parameter overrides provided, using template as-is")

    # Write patched file
    write_ini_file(config, output_path)
    logger.info(f"Created patched INI file: {output_path}")


def get_parameter_info() -> dict[str, dict[str, Any]]:
    """
    Get information about all supported parameters.

    Returns:
        Dictionary with parameter information
    """
    return PARAMETER_VALIDATION.copy()


def generate_scenario_suffix(parameters: dict[str, int]) -> str:
    """
    Generate a deterministic suffix for scenario identification.

    Args:
        parameters: Dictionary of parameter name -> value pairs

    Returns:
        String suffix like "_rot1_tlag2_det0_spk0"
    """
    if not parameters:
        return ""

    # Create suffix in consistent order
    suffix_parts = []
    for param_name in sorted(parameters.keys()):
        value = parameters[param_name]
        # Use short names for suffix
        short_names = {
            "rot_meth": "rot",
            "tlag_meth": "tlag",
            "detrend_meth": "det",
            "despike_vm": "spk",
        }
        short_name = short_names.get(param_name, param_name)
        suffix_parts.append(f"{short_name}{value}")

    return "_" + "_".join(suffix_parts)
