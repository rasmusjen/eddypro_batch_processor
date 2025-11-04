#!/usr/bin/env python3
"""
INI Tools for EddyPro Batch Processor.

Utilities for parameterizing and validating EddyPro INI configuration files.
Supports patching specific parameters while preserving the rest of the template.
"""

import configparser
import logging
from datetime import datetime
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
    "despike_meth": {
        "section": "RawProcess_ParameterSettings",
        "allowed_values": {0, 1},
        "description": "Spike removal method (0=VM97, 1=M13)",
        "ini_key": "despike_vm",  # INI file uses legacy key name
    },
}

# Mapping from Python parameter names to INI key names
# (only needed when they differ)
PARAMETER_INI_KEY_MAP: dict[str, str] = {
    "despike_meth": "despike_vm",
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

        # Get INI key name (may differ from Python parameter name)
        ini_key = PARAMETER_INI_KEY_MAP.get(param_name, param_name)

        # Set the parameter value
        config.set(section_name, ini_key, str(value))
        logger.debug(f"Set {section_name}.{ini_key} = {value}")


def write_ini_file(config: configparser.ConfigParser, output_path: Path) -> None:
    """
    Write INI configuration to file.

    Writes with no spaces around delimiters and LF line endings to match
    EddyPro native format expectations.

    Args:
        config: ConfigParser object to write
        output_path: Path where to write the INI file

    Raises:
        OSError: If file cannot be written
    """
    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with no spaces around '=' and LF endings (EddyPro native format)
        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            config.write(f, space_around_delimiters=False)

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

    All paths are normalized to forward slashes for EddyPro compatibility.

    Args:
        config: Parsed INI configuration to modify in-place
        proj_file: Path to the static metadata file (.metadata)
        dyn_metadata_file: Path to the dynamic metadata file (.txt)
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

    # Normalize all paths to forward slashes (EddyPro standard)
    proj_file_normalized = Path(proj_file).as_posix()
    dyn_metadata_file_normalized = Path(dyn_metadata_file).as_posix()
    data_path_normalized = Path(data_path).as_posix()
    out_path_normalized = Path(out_path).as_posix()

    # Project-level paths
    config.set("Project", "proj_file", proj_file_normalized)
    config.set("Project", "dyn_metadata_file", dyn_metadata_file_normalized)
    config.set("Project", "out_path", out_path_normalized)

    # Ensure use flags are enabled (template should already set these to 1)
    # but we enforce to avoid surprises when templates vary.
    try:
        config.set("Project", "use_pfile", "1")
        config.set("Project", "use_dyn_md_file", "1")
    except Exception:  # pragma: no cover - defensive only
        logger.debug("Project section missing use flags; leaving as-is")

    # Input data path
    config.set("RawProcess_General", "data_path", data_path_normalized)

    logger.debug(
        "Patched paths: Project.proj_file=%s, Project.dyn_metadata_file=%s, "
        "Project.out_path=%s, RawProcess_General.data_path=%s",
        proj_file_normalized,
        dyn_metadata_file_normalized,
        out_path_normalized,
        data_path_normalized,
    )


def patch_conditional_date_ranges(
    config: configparser.ConfigParser,
    *,
    year: int,
) -> None:
    """Conditionally populate date/time ranges based on processing methods.

    When rot_meth=3 (Planar Fit), populates pf_start_date/pf_end_date/
    pf_start_time/pf_end_time with full-year ranges in
    [RawProcess_TiltCorrection_Settings].

    When tlag_meth=4 (Covariance maximization with time-lag optimization),
    populates to_start_date/to_end_date/to_start_time/to_end_time with
    full-year ranges in [RawProcess_TimelagOptimization_Settings].

    Args:
        config: Parsed INI configuration to modify in-place
        year: Processing year to use for date range (YYYY-01-01 to YYYY-12-31)

    Raises:
        INIParameterError: If required sections are missing when conditions
            are met
    """
    # Check rot_meth for Planar Fit (value 3)
    if config.has_section("RawProcess_Settings"):
        rot_meth = config.getint("RawProcess_Settings", "rot_meth", fallback=None)
        if rot_meth == 3:
            if not config.has_section("RawProcess_TiltCorrection_Settings"):
                raise INIParameterError(
                    "rot_meth=3 (Planar Fit) requires section "
                    "'RawProcess_TiltCorrection_Settings' in template"
                )

            # Populate planar fit date/time range for the full year
            config.set(
                "RawProcess_TiltCorrection_Settings",
                "pf_start_date",
                f"{year}-01-01",
            )
            config.set(
                "RawProcess_TiltCorrection_Settings",
                "pf_end_date",
                f"{year}-12-31",
            )
            config.set("RawProcess_TiltCorrection_Settings", "pf_start_time", "00:00")
            config.set("RawProcess_TiltCorrection_Settings", "pf_end_time", "23:59")

            logger.debug(
                "rot_meth=3: Populated planar fit date range for year %d "
                "(pf_start_date=%s-%02d-%02d, pf_end_date=%s-%02d-%02d)",
                year,
                year,
                1,
                1,
                year,
                12,
                31,
            )

    # Check tlag_meth for time-lag optimization (value 4)
    if config.has_section("RawProcess_Settings"):
        tlag_meth = config.getint("RawProcess_Settings", "tlag_meth", fallback=None)
        if tlag_meth == 4:
            if not config.has_section("RawProcess_TimelagOptimization_Settings"):
                raise INIParameterError(
                    "tlag_meth=4 (time-lag optimization) requires section "
                    "'RawProcess_TimelagOptimization_Settings' in template"
                )

            # Populate time-lag optimization date/time range for the full year
            config.set(
                "RawProcess_TimelagOptimization_Settings",
                "to_start_date",
                f"{year}-01-01",
            )
            config.set(
                "RawProcess_TimelagOptimization_Settings",
                "to_end_date",
                f"{year}-12-31",
            )
            config.set(
                "RawProcess_TimelagOptimization_Settings",
                "to_start_time",
                "00:00",
            )
            config.set(
                "RawProcess_TimelagOptimization_Settings", "to_end_time", "23:59"
            )

            logger.debug(
                "tlag_meth=4: Populated time-lag optimization date range "
                "for year %d (to_start_date=%s-%02d-%02d, "
                "to_end_date=%s-%02d-%02d)",
                year,
                year,
                1,
                1,
                year,
                12,
                31,
            )


def patch_project_metadata(
    config: configparser.ConfigParser,
    *,
    site_id: str,
    year: int,
    scenario_suffix: str = "",
) -> None:
    """Patch Project metadata fields to match EddyPro native format.

    Populates creation_date, last_change_date, project_title, and project_id
    to align with legacy EddyPro project file standards.

    Args:
        config: Parsed INI configuration to modify in-place
        site_id: Site identifier (e.g., 'GL-ZaF')
        year: Processing year
        scenario_suffix: Optional scenario suffix (e.g., '_rot1_tlag2')

    Raises:
        INIParameterError: If required Project section is missing
    """
    if not config.has_section("Project"):
        raise INIParameterError("Required section 'Project' missing from template")

    # Get current timestamp in EddyPro format: YYYY-MM-DDTHH:MM:SS
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Set creation_date only if empty (preserve original creation time)
    if not config.get("Project", "creation_date", fallback="").strip():
        config.set("Project", "creation_date", now)

    # Always update last_change_date to current time
    config.set("Project", "last_change_date", now)

    # Set project_title: "<site_id> <year>" or with scenario suffix
    if scenario_suffix:
        project_title = f"{site_id} {year}{scenario_suffix}"
    else:
        project_title = f"{site_id} {year}"
    config.set("Project", "project_title", project_title)

    # Set project_id: "<site_id>_<year>"
    project_id = f"{site_id}_{year}"
    config.set("Project", "project_id", project_id)

    logger.debug(
        "Patched Project metadata: creation_date=%s, last_change_date=%s, "
        "project_title=%s, project_id=%s",
        config.get("Project", "creation_date"),
        now,
        project_title,
        project_id,
    )


def validate_eddypro_inputs(config: configparser.ConfigParser) -> None:
    """Validate that EddyPro inputs are accessible before execution.

    Checks that data_path exists and contains at least one matching file,
    preventing Fatal error(86) from EddyPro.

    Args:
        config: Parsed EddyPro project configuration

    Raises:
        INIParameterError: If data_path is invalid or no files found
    """
    # Get data_path
    data_path_str = config.get("RawProcess_General", "data_path", fallback="")
    if not data_path_str:
        raise INIParameterError(
            "RawProcess_General.data_path is empty. "
            "Cannot proceed without input data directory."
        )

    data_path = Path(data_path_str)
    if not data_path.exists():
        raise INIParameterError(
            f"RawProcess_General.data_path does not exist: {data_path}"
        )

    if not data_path.is_dir():
        raise INIParameterError(
            f"RawProcess_General.data_path is not a directory: {data_path}"
        )

    # Check for CSV files (basic check; prototype matching is EddyPro's job)
    csv_files = list(data_path.glob("*.csv"))
    if not csv_files:
        raise INIParameterError(
            f"No CSV files found in data_path: {data_path}. "
            "EddyPro will fail with Fatal error(86)."
        )

    # Get file_prototype for informational logging
    file_prototype = config.get("Project", "file_prototype", fallback="(not set)")

    logger.info(
        f"Preflight check passed: {len(csv_files)} CSV file(s) found in {data_path}"
    )
    logger.debug(f"File prototype: {file_prototype}")

    # Optional: warn if prototype looks suspicious (e.g., still has placeholder '?')
    # but don't fail, as EddyPro will handle the actual matching
    if file_prototype and "?" in file_prototype:
        # Sample a few filenames for the log
        sample_files = [f.name for f in csv_files[:3]]
        logger.debug(
            f"Sample files in directory: {sample_files}. "
            f"Ensure prototype '{file_prototype}' matches."
        )


def validate_eddypro_metadata(config: configparser.ConfigParser) -> None:
    """Validate that the static metadata file referenced by the project exists
    and declares the mandatory variables.

    This prevents EddyPro Fatal error(23) due to missing u/v/w/ts definitions or
    accidental mis-pointing to the .eddypro file itself.

    Args:
        config: Parsed EddyPro project configuration

    Raises:
        INIParameterError: If metadata file is missing or invalid
    """
    proj_file_path = config.get("Project", "proj_file", fallback="").strip()
    if not proj_file_path:
        raise INIParameterError(
            "Project.proj_file is empty. It must point to the static .metadata file."
        )

    meta_path = Path(proj_file_path)
    if not meta_path.exists() or not meta_path.is_file():
        raise INIParameterError(f"Static metadata file not found: {meta_path}")

    # Parse metadata and check variables in [FileDescription]
    parser = configparser.ConfigParser()
    try:
        parser.read(meta_path, encoding="utf-8")
    except configparser.Error as e:  # pragma: no cover
        raise INIParameterError(
            f"Failed to parse metadata file {meta_path}: {e}"
        ) from e

    if not parser.has_section("FileDescription"):
        raise INIParameterError(
            f"Metadata file {meta_path} missing [FileDescription] section"
        )

    # Collect declared variables
    variables: set[str] = set()
    for key, value in parser.items("FileDescription"):
        if key.endswith("_variable"):
            variables.add(value.strip())

    required = {"u", "v", "w", "ts"}
    missing = sorted(required - variables)
    if missing:
        raise INIParameterError(
            "Metadata is missing required variables: " + ", ".join(missing)
        )

    logger.info(
        "Metadata validation passed for %s (vars present: %s)",
        meta_path.name,
        sorted(variables),
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
            "despike_meth": "spk",
        }
        short_name = short_names.get(param_name, param_name)
        suffix_parts.append(f"{short_name}{value}")

    return "_" + "_".join(suffix_parts)
