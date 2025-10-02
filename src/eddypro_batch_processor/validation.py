"""
Validation module for configuration, paths, and ECMD files.

Provides comprehensive validation of configuration structure, path existence,
ECMD file schema, and sanity checks with actionable error messages.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_config_structure(config: Dict[str, Any]) -> List[str]:
    """
    Validate that all required configuration keys are present.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of error messages (empty if valid)

    Examples:
        >>> config = {"eddypro_executable": "path/to/exe"}
        >>> errors = validate_config_structure(config)
        >>> len(errors) > 0  # Missing required keys
        True
    """
    required_keys = [
        "eddypro_executable",
        "site_id",
        "years_to_process",
        "input_dir_pattern",
        "output_dir_pattern",
        "ecmd_file",
        "stream_output",
        "log_level",
        "multiprocessing",
        "max_processes",
        "metrics_interval_seconds",
        "reports_dir",
        "report_charts",
    ]

    errors = []
    missing_keys = [key for key in required_keys if key not in config]

    if missing_keys:
        errors.append(f"Missing required configuration keys: {', '.join(missing_keys)}")

    # Validate types for present keys
    if "site_id" in config and not isinstance(config["site_id"], str):
        errors.append(f"'site_id' must be a string, got {type(config['site_id'])}")

    if "years_to_process" in config and not isinstance(
        config["years_to_process"], list
    ):
        errors.append(
            f"'years_to_process' must be a list, got {type(config['years_to_process'])}"
        )

    if "multiprocessing" in config and not isinstance(config["multiprocessing"], bool):
        errors.append(
            f"'multiprocessing' must be a boolean, got "
            f"{type(config['multiprocessing'])}"
        )

    if "stream_output" in config and not isinstance(config["stream_output"], bool):
        errors.append(
            f"'stream_output' must be a boolean, got {type(config['stream_output'])}"
        )

    if "max_processes" in config and not isinstance(config["max_processes"], int):
        errors.append(
            f"'max_processes' must be an integer, got {type(config['max_processes'])}"
        )

    if "metrics_interval_seconds" in config and not isinstance(
        config["metrics_interval_seconds"], (int, float)
    ):
        errors.append(
            f"'metrics_interval_seconds' must be a number, got "
            f"{type(config['metrics_interval_seconds'])}"
        )

    if "report_charts" in config and config["report_charts"] not in [
        "plotly",
        "svg",
        "none",
    ]:
        errors.append(
            f"'report_charts' must be one of [plotly, svg, none], got "
            f"'{config['report_charts']}'"
        )

    if "log_level" in config and config["log_level"] not in [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]:
        errors.append(
            f"'log_level' must be one of [DEBUG, INFO, WARNING, ERROR, CRITICAL], "
            f"got '{config['log_level']}'"
        )

    return errors


def validate_paths(config: Dict[str, Any], skip_ecmd: bool = False) -> List[str]:
    """
    Validate that required paths exist in the filesystem.

    Args:
        config: Configuration dictionary
        skip_ecmd: If True, skip ECMD file validation

    Returns:
        List of error messages (empty if valid)

    Examples:
        >>> config = {"eddypro_executable": "/nonexistent/path"}
        >>> errors = validate_paths(config, skip_ecmd=True)
        >>> len(errors) > 0
        True
    """
    errors = []

    # Validate EddyPro executable
    eddypro_exe = Path(config.get("eddypro_executable", ""))
    if not eddypro_exe.exists():
        errors.append(
            f"EddyPro executable not found: {eddypro_exe}\n"
            f"  → Check 'eddypro_executable' path in config"
        )

    # Validate input/output directory patterns
    # Note: We can't validate the pattern itself, but we can check if it's
    # a reasonable string
    input_pattern = config.get("input_dir_pattern", "")
    if not input_pattern or "{site_id}" not in input_pattern:
        errors.append(
            "Invalid 'input_dir_pattern': must contain '{site_id}' placeholder"
        )
    if "{year}" not in input_pattern:
        errors.append("Invalid 'input_dir_pattern': must contain '{year}' placeholder")

    output_pattern = config.get("output_dir_pattern", "")
    if not output_pattern or "{site_id}" not in output_pattern:
        errors.append(
            "Invalid 'output_dir_pattern': must contain '{site_id}' placeholder"
        )
    if "{year}" not in output_pattern:
        errors.append("Invalid 'output_dir_pattern': must contain '{year}' placeholder")

    # Try to format patterns with actual values to check if directories exist
    # for first year
    site_id = config.get("site_id", "")
    years = config.get("years_to_process", [])

    if site_id and years:
        first_year = years[0]
        try:
            input_dir = Path(input_pattern.format(year=first_year, site_id=site_id))
            if not input_dir.exists():
                errors.append(
                    f"Input directory for year {first_year} not found: {input_dir}\n"
                    f"  → Check 'input_dir_pattern' and ensure raw data exists"
                )
        except (KeyError, ValueError) as e:
            errors.append(f"Error formatting input_dir_pattern: {e}")

    # Validate ECMD file if not skipped
    if not skip_ecmd:
        ecmd_file = config.get("ecmd_file", "")
        if ecmd_file:
            # ECMD file path may contain placeholders
            if "{site_id}" in ecmd_file:
                ecmd_path = Path(ecmd_file.format(site_id=site_id))
            else:
                ecmd_path = Path(ecmd_file)

            if not ecmd_path.exists():
                errors.append(
                    f"ECMD file not found: {ecmd_path}\n"
                    f"  → Check 'ecmd_file' path in config"
                )

    return errors


def validate_ecmd_schema(ecmd_path: Path) -> List[str]:
    """
    Validate that ECMD CSV file contains required columns.

    Args:
        ecmd_path: Path to ECMD CSV file

    Returns:
        List of error messages (empty if valid)

    Examples:
        >>> from pathlib import Path
        >>> # Assuming valid ECMD file exists
        >>> errors = validate_ecmd_schema(Path("data/GL-ZaF_ecmd.csv"))
        >>> errors  # Should be empty for valid file
        []
    """
    required_columns = [
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
    ]

    # Closed-path specific columns (conditional)
    closed_path_columns = ["GA_TUBE_LENGTH", "GA_TUBE_DIAMETER", "GA_FLOWRATE"]

    errors = []

    if not ecmd_path.exists():
        errors.append(f"ECMD file not found: {ecmd_path}")
        return errors

    try:
        with ecmd_path.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            # Get actual columns from file
            fieldnames = reader.fieldnames
            if not fieldnames:
                errors.append(f"ECMD file is empty or has no header: {ecmd_path}")
                return errors

            # Check required columns
            missing_cols = [col for col in required_columns if col not in fieldnames]
            if missing_cols:
                errors.append(
                    f"ECMD file missing required columns: {', '.join(missing_cols)}\n"
                    f"  → File: {ecmd_path}"
                )

            # Check for closed-path configuration
            if "GA_PATH" in fieldnames:
                # Read first data row to check GA_PATH value
                try:
                    first_row = next(reader)
                    if first_row.get("GA_PATH", "").lower() == "closed":
                        missing_closed = [
                            col for col in closed_path_columns if col not in fieldnames
                        ]
                        if missing_closed:
                            errors.append(
                                f"ECMD file has GA_PATH='closed' but missing columns: "
                                f"{', '.join(missing_closed)}\n"
                                f"  → Required for closed-path analyzers"
                            )
                except StopIteration:
                    # Empty file (no data rows)
                    errors.append(f"ECMD file has header but no data rows: {ecmd_path}")

    except Exception as e:
        errors.append(f"Error reading ECMD file {ecmd_path}: {e}")

    return errors


def validate_ecmd_sanity(ecmd_path: Path) -> List[str]:
    """
    Perform sanity checks on ECMD file data values.

    Args:
        ecmd_path: Path to ECMD CSV file

    Returns:
        List of error messages (empty if valid)

    Examples:
        >>> from pathlib import Path
        >>> errors = validate_ecmd_sanity(Path("data/GL-ZaF_ecmd.csv"))
        >>> # Should be empty for sane values
        >>> len(errors) == 0
        True
    """
    errors = []

    if not ecmd_path.exists():
        errors.append(f"ECMD file not found: {ecmd_path}")
        return errors

    try:
        with ecmd_path.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for i, row in enumerate(reader, start=2):  # Start at 2 (1=header)
                # Check ACQUISITION_FREQUENCY is positive
                try:
                    acq_freq = float(row.get("ACQUISITION_FREQUENCY", "0"))
                    if acq_freq <= 0:
                        errors.append(
                            f"Row {i}: ACQUISITION_FREQUENCY must be positive, "
                            f"got {acq_freq}"
                        )
                except ValueError:
                    errors.append(
                        f"Row {i}: ACQUISITION_FREQUENCY is not a valid number: "
                        f"'{row.get('ACQUISITION_FREQUENCY')}'"
                    )

                # Check FILE_DURATION is positive
                try:
                    file_dur = float(row.get("FILE_DURATION", "0"))
                    if file_dur <= 0:
                        errors.append(
                            f"Row {i}: FILE_DURATION must be positive, got {file_dur}"
                        )
                except ValueError:
                    errors.append(
                        f"Row {i}: FILE_DURATION is not a valid number: "
                        f"'{row.get('FILE_DURATION')}'"
                    )

                # Check CANOPY_HEIGHT is non-negative (can be 0)
                try:
                    canopy_height = float(row.get("CANOPY_HEIGHT", "0"))
                    if canopy_height < 0:
                        errors.append(
                            f"Row {i}: CANOPY_HEIGHT must be non-negative, "
                            f"got {canopy_height}"
                        )
                except ValueError:
                    errors.append(
                        f"Row {i}: CANOPY_HEIGHT is not a valid number: "
                        f"'{row.get('CANOPY_HEIGHT')}'"
                    )

                # Check SA_HEIGHT is positive
                try:
                    sa_height = float(row.get("SA_HEIGHT", "0"))
                    if sa_height <= 0:
                        errors.append(
                            f"Row {i}: SA_HEIGHT must be positive, got {sa_height}"
                        )
                except ValueError:
                    errors.append(
                        f"Row {i}: SA_HEIGHT is not a valid number: "
                        f"'{row.get('SA_HEIGHT')}'"
                    )

    except Exception as e:
        errors.append(f"Error reading ECMD file {ecmd_path}: {e}")

    return errors


def validate_config_sanity(config: Dict[str, Any]) -> List[str]:
    """
    Perform sanity checks on configuration values.

    Args:
        config: Configuration dictionary

    Returns:
        List of error messages (empty if valid)

    Examples:
        >>> config = {"years_to_process": [], "site_id": ""}
        >>> errors = validate_config_sanity(config)
        >>> len(errors) > 0
        True
    """
    errors = []

    # Check years_to_process is not empty
    years = config.get("years_to_process", [])
    if not years:
        errors.append("'years_to_process' cannot be empty")

    # Check site_id is not empty
    site_id = config.get("site_id", "")
    if not site_id or not site_id.strip():
        errors.append("'site_id' cannot be empty")

    # Check max_processes is positive when multiprocessing enabled
    if config.get("multiprocessing", False):
        max_proc = config.get("max_processes", 0)
        if max_proc <= 0:
            errors.append(
                f"'max_processes' must be positive when multiprocessing is "
                f"enabled, got {max_proc}"
            )

    # Check metrics_interval_seconds is positive
    metrics_interval = config.get("metrics_interval_seconds", 0)
    if metrics_interval <= 0:
        errors.append(
            f"'metrics_interval_seconds' must be positive, got {metrics_interval}"
        )

    return errors


def validate_all(
    config: Dict[str, Any],
    skip_paths: bool = False,
    skip_ecmd: bool = False,
) -> Dict[str, List[str]]:
    """
    Run all validations and return categorized errors.

    Args:
        config: Configuration dictionary
        skip_paths: If True, skip path existence checks
        skip_ecmd: If True, skip ECMD file validation

    Returns:
        Dictionary mapping validation category to list of errors

    Examples:
        >>> config = {"eddypro_executable": "/path/to/exe"}
        >>> result = validate_all(config, skip_paths=True, skip_ecmd=True)
        >>> "config_structure" in result
        True
    """
    results = {}

    # Config structure validation
    results["config_structure"] = validate_config_structure(config)

    # Config sanity validation
    results["config_sanity"] = validate_config_sanity(config)

    # Path validation (unless skipped)
    if not skip_paths:
        results["paths"] = validate_paths(config, skip_ecmd=skip_ecmd)
    else:
        results["paths"] = []

    # ECMD validation (unless skipped)
    if not skip_ecmd:
        ecmd_file = config.get("ecmd_file", "")
        site_id = config.get("site_id", "")

        if ecmd_file:
            # Format ECMD path if it contains placeholders
            if "{site_id}" in ecmd_file:
                ecmd_path = Path(ecmd_file.format(site_id=site_id))
            else:
                ecmd_path = Path(ecmd_file)

            if ecmd_path.exists():
                results["ecmd_schema"] = validate_ecmd_schema(ecmd_path)
                results["ecmd_sanity"] = validate_ecmd_sanity(ecmd_path)
            else:
                results["ecmd_schema"] = [f"ECMD file not found: {ecmd_path}"]
                results["ecmd_sanity"] = []
        else:
            results["ecmd_schema"] = ["ECMD file path not specified in config"]
            results["ecmd_sanity"] = []
    else:
        results["ecmd_schema"] = []
        results["ecmd_sanity"] = []

    return results


def format_validation_report(results: Dict[str, List[str]]) -> str:
    """
    Format validation results as a human-readable report.

    Args:
        results: Dictionary mapping validation category to errors

    Returns:
        Formatted validation report string

    Examples:
        >>> results = {"config_structure": ["Missing key: site_id"]}
        >>> report = format_validation_report(results)
        >>> "config_structure" in report
        True
    """
    lines = ["Validation Report", "=" * 60, ""]

    total_errors = sum(len(errors) for errors in results.values())

    for category, errors in results.items():
        category_name = category.replace("_", " ").title()
        if errors:
            lines.append(f"[FAIL] {category_name}: {len(errors)} error(s)")
            for error in errors:
                # Indent multi-line errors
                error_lines = error.split("\n")
                lines.append(f"   - {error_lines[0]}")
                for line in error_lines[1:]:
                    lines.append(f"     {line}")
            lines.append("")
        else:
            lines.append(f"[PASS] {category_name}: OK")

    lines.append("")
    lines.append("=" * 60)
    if total_errors == 0:
        lines.append("[PASS] All validations passed!")
    else:
        lines.append(f"[FAIL] Total errors: {total_errors}")

    return "\n".join(lines)
