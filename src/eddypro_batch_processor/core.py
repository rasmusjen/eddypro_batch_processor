"""
EddyPro Batch Processor Core Module.

Contains the core business logic refactored from the original eddypro_batch_processor.py
while preserving existing behavior and outputs.
"""

import json
import logging
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import yaml

from . import ecmd, ini_tools, report
from .monitor import MonitoredOperation
from .scenarios import Scenario


def _raise_missing_ecmd(site_id: str, path: Path | None) -> NoReturn:
    raise ecmd.ECMDError(  # noqa: TRY301 - centralized error helper
        f"ECMD file not found for site {site_id}: {path}"
    )


class EddyProBatchProcessor:
    """Main class for EddyPro batch processing operations."""

    def __init__(self, config_path: Path | None = None):
        """Initialize the processor with optional config path."""
        self.config_path = config_path or Path("config/config.yaml")
        self.config: dict[str, Any] = {}

    def load_config(self, config_path: Path | None = None) -> dict[str, Any]:
        """Load the YAML configuration file.

        This function attempts to read and parse a YAML configuration file
        from the specified path. It handles scenarios where the file is missing
        or contains invalid YAML syntax by logging appropriate error messages
        and exiting the script.

        Args:
            config_path: The file system path to the YAML configuration file.

        Returns:
            A dictionary containing configuration parameters loaded from the
            YAML file.

        Raises:
            SystemExit: If the configuration file is not found or contains
                invalid YAML.
        """
        if config_path:
            self.config_path = config_path

        try:
            with self.config_path.open("r") as file:
                config: dict[str, Any] = yaml.safe_load(file)
                logging.info(
                    f"Configuration loaded successfully from {self.config_path}"
                )
                self.config = config
                return config
        except FileNotFoundError:
            logging.exception(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError:
            logging.exception("Error parsing the configuration file")
            sys.exit(1)

    def validate_config(self, config: dict[str, Any] | None = None) -> None:
        """
        Validate the essential configuration parameters.

        Args:
            config: The configuration dictionary loaded from the YAML file.

        Raises:
            SystemExit: If any required configuration parameter is missing or invalid.
        """
        if config is None:
            config = self.config

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
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            logging.error(
                f"Missing configuration parameters: {', '.join(missing_keys)}"
            )
            sys.exit(1)

        # Validate max_processes
        max_processes = config.get("max_processes")
        if not isinstance(max_processes, int) or max_processes < 1:
            logging.error(
                "Invalid 'max_processes' value. It must be a positive integer."
            )
            sys.exit(1)

        # Validate metrics_interval_seconds
        metrics_interval = config.get("metrics_interval_seconds")
        if not isinstance(metrics_interval, int | float) or metrics_interval <= 0:
            logging.error(
                "Invalid 'metrics_interval_seconds' value. "
                "It must be a positive number."
            )
            sys.exit(1)

        # Validate report_charts
        report_charts = config.get("report_charts", "plotly")
        if report_charts not in ["plotly", "svg", "none"]:
            logging.error(
                "Invalid 'report_charts' value. Must be one of: plotly, svg, none."
            )
            sys.exit(1)

        logging.info("Configuration validation passed.")


def run_subprocess_with_monitoring(
    command: str,
    working_dir: Path,
    stream_output: bool = True,
    metrics_interval: float = 0.5,
    output_dir: Path | None = None,
    scenario_suffix: str = "",
) -> int:
    """
    Execute a subprocess command with performance monitoring.

    This function runs the given command in a subprocess, optionally streams output,
    and monitors performance metrics during execution.

    Args:
        command: The command line string to execute
        working_dir: Directory to execute the command in
        stream_output: Whether to stream output in real-time
        metrics_interval: Sampling interval for performance monitoring
        output_dir: Directory to write metrics files (defaults to working_dir)
        scenario_suffix: Suffix for metrics files in scenario runs

    Returns:
        Subprocess return code, or -1 if an exception occurs
    """
    metrics_output_dir = output_dir or working_dir

    try:
        with MonitoredOperation(
            interval_seconds=metrics_interval,
            output_dir=metrics_output_dir,
            scenario_suffix=scenario_suffix,
        ) as monitor:
            # Start the subprocess
            process = subprocess.Popen(  # nosec B602
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=working_dir,
            )

            # Start monitoring the specific process if monitor is available
            if monitor and process.pid:
                # Stop current monitoring and restart with process PID
                monitor.stop_monitoring()
                monitor.start_monitoring(process_pid=process.pid)

            # Handle output streaming
            if stream_output and process.stdout:
                for line in process.stdout:
                    print(line, end="")
            else:
                # Just wait for completion without streaming
                process.wait()

            return_code = process.returncode
            logging.debug(f"Subprocess finished with return code {return_code}")
            return return_code

    except Exception:
        logging.exception(f"Failed to execute command '{command}'")
        return -1


def run_eddypro_with_monitoring(
    project_file: Path,
    eddypro_executable: Path,
    stream_output: bool = True,
    metrics_interval: float = 0.5,
    scenario_suffix: str = "",
) -> bool:
    """
    Run EddyPro processing with performance monitoring.

    Args:
        project_file: Path to the EddyPro project file
        eddypro_executable: Path to the EddyPro executable
        stream_output: Whether to stream subprocess output
        metrics_interval: Performance monitoring sampling interval
        scenario_suffix: Suffix for scenario-specific metrics files

    Returns:
        True if both eddypro_rp and eddypro_fcc succeed, False otherwise
    """
    output_dir = project_file.parent
    eddypro_path = output_dir.parent
    tmp_dir = eddypro_path / "tmp"
    bin_dir = eddypro_path / "bin"

    # Create temporary directories
    tmp_dir.mkdir(exist_ok=True)
    bin_dir.mkdir(exist_ok=True)
    logging.debug(f"Created temporary directories: {tmp_dir}, {bin_dir}")

    # Copy EddyPro binaries
    try:
        shutil.copytree(eddypro_executable.parent, bin_dir, dirs_exist_ok=True)
        logging.info(f"Copied EddyPro binaries to {bin_dir}")
    except Exception:
        logging.exception("Failed to copy EddyPro binaries")
        return False

    # Determine OS-specific executable names
    rp_executable = bin_dir / (
        "eddypro_rp.exe" if platform.system() == "Windows" else "eddypro_rp"
    )
    fcc_executable = bin_dir / (
        "eddypro_fcc.exe" if platform.system() == "Windows" else "eddypro_fcc"
    )

    # Verify executables exist
    if not rp_executable.exists():
        logging.error(f"EddyPro rp executable not found: {rp_executable}")
        return False
    if not fcc_executable.exists():
        logging.error(f"EddyPro fcc executable not found: {fcc_executable}")
        return False

    # Construct commands
    os_suffix = "win" if platform.system() == "Windows" else "linux"
    command_sys = f" -s {os_suffix} "
    rp_command = f'"{rp_executable}"{command_sys}"{project_file}"'
    fcc_command = f'"{fcc_executable}"{command_sys}"{project_file}"'

    success = True

    # Run eddypro_rp with monitoring
    logging.info("Starting eddypro_rp with performance monitoring...")
    rp_return_code = run_subprocess_with_monitoring(
        command=rp_command,
        working_dir=eddypro_path,
        stream_output=stream_output,
        metrics_interval=metrics_interval,
        output_dir=output_dir,
        scenario_suffix=f"{scenario_suffix}_rp" if scenario_suffix else "rp",
    )
    if rp_return_code != 0:
        logging.error(f"eddypro_rp failed with return code {rp_return_code}")
        success = False

    # Run eddypro_fcc with monitoring
    logging.info("Starting eddypro_fcc with performance monitoring...")
    fcc_return_code = run_subprocess_with_monitoring(
        command=fcc_command,
        working_dir=eddypro_path,
        stream_output=stream_output,
        metrics_interval=metrics_interval,
        output_dir=output_dir,
        scenario_suffix=f"{scenario_suffix}_fcc" if scenario_suffix else "fcc",
    )
    if fcc_return_code != 0:
        logging.error(f"eddypro_fcc failed with return code {fcc_return_code}")
        success = False

    # Clean up temporary directories
    try:
        shutil.rmtree(bin_dir)
        shutil.rmtree(tmp_dir)
        logging.debug("Cleaned up temporary directories")
    except Exception as e:
        logging.warning(f"Failed to clean up temporary directories: {e}")

    if success:
        logging.info(
            f"EddyPro processing completed successfully. Results in {output_dir}"
        )
    else:
        logging.error("EddyPro processing failed")

    return success


# Legacy function imports - to be used by the CLI while preserving existing behavior
def load_config(config_path: Path) -> dict:
    """Legacy function wrapper for backwards compatibility."""
    processor = EddyProBatchProcessor(config_path)
    return processor.load_config()


def validate_config(config: dict) -> None:
    """Legacy function wrapper for backwards compatibility."""
    processor = EddyProBatchProcessor()
    processor.validate_config(config)


def generate_run_report(
    config: dict[str, Any],
    site_id: str,
    years_processed: list,
    output_base_dir: Path,
    start_time: datetime,
    end_time: datetime,
    overall_success: bool = True,
) -> None:
    """
    Generate run manifest and HTML report after processing completes.

    Args:
        config: Configuration dictionary
        site_id: Site identifier
        years_processed: List of years that were processed
        output_base_dir: Base output directory (parent of year-specific dirs)
        start_time: Processing start time (datetime)
        end_time: Processing end time (datetime)
        overall_success: Whether all processing succeeded
    """
    # Determine reports directory
    reports_dir_config = config.get("reports_dir")
    if reports_dir_config:
        reports_dir = Path(reports_dir_config)
    else:
        # Default: put reports in the output_base_dir/reports
        reports_dir = output_base_dir / "reports"

    reports_dir = report.create_reports_directory(reports_dir.parent, reports_dir.name)

    # Generate run ID
    run_id = f"{site_id}_{start_time.strftime('%Y%m%d_%H%M%S')}"

    # Collect output directories
    output_dirs = []
    for year in years_processed:
        year_dir = Path(
            config.get("output_dir_pattern", "").format(year=year, site_id=site_id)
        )
        if year_dir.exists():
            output_dirs.append(year_dir)

    # Compute config checksum (simple hash of sorted config JSON)
    config_checksum = str(hash(json.dumps(config, sort_keys=True)))

    # Collect scenarios (single baseline scenario for now)
    scenario_list = [
        {
            "scenario_name": "baseline",
            "scenario_params": {},
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "success": overall_success,
        }
    ]

    # Load metrics if available
    scenario_metrics = {}
    for year in years_processed:
        year_dir = Path(
            config.get("output_dir_pattern", "").format(year=year, site_id=site_id)
        )
        metrics_files = list(year_dir.glob("metrics_*.csv"))
        if metrics_files:
            # Load the most recent metrics file
            metrics_file = sorted(metrics_files)[-1]
            metrics = report.load_metrics_from_csv(metrics_file)
            scenario_metrics[f"{year}_baseline"] = metrics

    # Generate run manifest
    run_manifest = report.generate_run_manifest(
        run_id=run_id,
        config=config,
        config_checksum=config_checksum,
        site_id=site_id,
        years_processed=years_processed,
        scenarios=scenario_list,
        start_time=start_time,
        end_time=end_time,
        overall_success=overall_success,
        output_dirs=output_dirs,
    )

    # Write run manifest
    manifest_path = reports_dir / "run_manifest.json"
    report.write_run_manifest(run_manifest, manifest_path)

    # Generate HTML report
    chart_engine = config.get("report_charts", "plotly")
    html_path = reports_dir / "run_report.html"
    report.generate_html_report(
        run_manifest=run_manifest,
        scenario_metrics=scenario_metrics if scenario_metrics else None,
        chart_engine=chart_engine,
        output_path=html_path,
    )

    logging.info(f"Run report generated: {html_path}")
    logging.info(f"Run manifest generated: {manifest_path}")


def run_single_scenario(
    scenario: Scenario,
    template_path: Path,
    output_base_dir: Path,
    eddypro_executable: Path,
    stream_output: bool,
    metrics_interval: float,
    *,
    site_id: str,
    year: int,
    input_dir: Path,
    ecmd_file: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Execute a single scenario with patched parameters.

    Args:
        scenario: Scenario object with parameters and suffix
        template_path: Path to EddyPro project template
        output_base_dir: Base directory for scenario outputs
        eddypro_executable: Path to EddyPro executable
        stream_output: Whether to stream subprocess output
        metrics_interval: Performance monitoring sampling interval
        dry_run: If True, only create files without running EddyPro

    Returns:
        Dictionary containing scenario execution metadata
    """
    start_time = datetime.now()

    # Create scenario-specific output directory
    scenario_output_dir = output_base_dir / f"scenario{scenario.suffix}"
    scenario_output_dir.mkdir(parents=True, exist_ok=True)

    # Project filename must be {site_id}_{year}_{scenario_id}.eddypro
    project_filename = f"{site_id}_{year}_{scenario.suffix.lstrip('_')}.eddypro"
    scenario_project_file = scenario_output_dir / project_filename

    # Metadata filenames (shared across years, not year-specific)
    metadata_filename = f"{site_id}.metadata"
    dyn_metadata_filename = f"{site_id}_dynamic_metadata.txt"

    logging.info(
        f"Scenario {scenario.index}: Creating project file with parameters "
        f"{scenario.parameters}"
    )

    try:
        # Create patched INI file to a temporary path, then patch paths and write final
        ini_config = ini_tools.read_ini_template(template_path)
        if scenario.parameters:
            validated_params = ini_tools.validate_parameters(scenario.parameters)
            ini_tools.patch_ini_parameters(ini_config, validated_params)

        # Ensure input and output paths
        # The input path is not directly available here; infer from template if
        # set, else use conservative default. We avoid guessing a raw path from
        # output structure to prevent mis-processing. If template had empty
        # data_path, we keep it empty (user's template should carry the right
        # value), and still set out_path for outputs.
        data_path_value = ini_config.get("RawProcess_General", "data_path", fallback="")
        if not data_path_value:
            # Use provided input_dir when template is empty
            data_path_value = str(input_dir)

        success = True
        return_code = 0

        # Materialize metadata files beside project file (idempotent overwrite)
        try:
            # Copy site-specific metadata template -> {site}.metadata
            # (shared across years)
            metadata_template = Path("config") / f"{site_id}_metadata_template.ini"
            if not metadata_template.exists():
                # Fallback to generic template
                metadata_template = Path("config") / "metadata_template.ini"

            if metadata_template.exists():
                shutil.copyfile(
                    metadata_template,
                    scenario_output_dir / metadata_filename,
                )
            else:
                logging.warning(
                    f"No metadata template found for site {site_id}, "
                    "skipping .metadata file generation"
                )

            # Generate dynamic metadata from ECMD CSV (all years included)
            if ecmd_file and ecmd_file.exists():
                ecmd.generate_dynamic_metadata(
                    ecmd_path=ecmd_file,
                    output_path=scenario_output_dir / dyn_metadata_filename,
                    site_id=site_id,
                )
            else:
                logging.warning(
                    f"ECMD file not found or not provided for site {site_id}, "
                    f"skipping dynamic metadata generation"
                )

        except Exception as meta_err:
            logging.warning(f"Failed to materialize metadata files: {meta_err}")

        ecmd_path = ecmd_file
        if ecmd_path is None or not ecmd_path.exists():
            _raise_missing_ecmd(site_id, ecmd_path)

        ecmd_row = ecmd.select_ecmd_row_for_year(
            ecmd_path=ecmd_path,
            site_id=site_id,
            year=year,
        )

        # Patch all path fields (normalized to forward slashes)
        ini_tools.patch_ini_paths(
            ini_config,
            site_id=site_id,
            proj_file=str(scenario_output_dir / metadata_filename),
            dyn_metadata_file=str(scenario_output_dir / dyn_metadata_filename),
            data_path=data_path_value,
            out_path=str(scenario_output_dir),
        )

        # Patch Project metadata fields (creation_date, last_change_date, etc.)
        ini_tools.patch_project_metadata(
            ini_config,
            site_id=site_id,
            year=year,
            scenario_suffix=scenario.suffix,
        )

        # Conditionally patch date/time ranges based on rot_meth and tlag_meth
        ini_tools.patch_conditional_date_ranges(ini_config, year=year)

        # Write final project file, then populate .metadata from ECMD
        ini_tools.write_project_file_with_metadata(
            ini_config,
            scenario_project_file,
            metadata_path=scenario_output_dir / metadata_filename,
            site_id=site_id,
            output_dir=scenario_output_dir,
            ecmd_row=ecmd_row,
        )

        # Preflight validation: ensure inputs and metadata are sane
        try:
            ini_tools.validate_eddypro_inputs(ini_config)
            ini_tools.validate_eddypro_metadata(ini_config)
        except ini_tools.INIParameterError:
            logging.exception(
                f"Preflight validation failed for scenario {scenario.index}"
            )
            raise

        if not dry_run:
            # Run EddyPro with monitoring
            logging.info(f"Scenario {scenario.index}: Running EddyPro...")
            success = run_eddypro_with_monitoring(
                project_file=scenario_project_file,
                eddypro_executable=eddypro_executable,
                stream_output=stream_output,
                metrics_interval=metrics_interval,
                scenario_suffix=scenario.suffix,
            )
            return_code = 0 if success else 1
        else:
            logging.info(
                f"Scenario {scenario.index}: Dry run mode - skipping execution"
            )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Build scenario metadata
        metadata = {
            "scenario_index": scenario.index,
            "scenario_suffix": scenario.suffix,
            "scenario_params": scenario.parameters,
            "project_file": str(scenario_project_file),
            "output_dir": str(scenario_output_dir),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "success": success,
            "return_code": return_code,
            "dry_run": dry_run,
        }

        # Write scenario manifest
        manifest_path = scenario_output_dir / f"scenario_manifest{scenario.suffix}.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logging.info(
            f"Scenario {scenario.index} {'completed' if success else 'failed'} "
            f"in {duration:.1f}s"
        )

    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logging.exception(f"Scenario {scenario.index} failed with exception")

        metadata = {
            "scenario_index": scenario.index,
            "scenario_suffix": scenario.suffix,
            "scenario_params": scenario.parameters,
            "project_file": (
                str(scenario_project_file) if scenario_project_file else None
            ),
            "output_dir": str(scenario_output_dir),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "success": False,
            "return_code": -1,
            "error": str(e),
            "dry_run": dry_run,
        }

    return metadata


def run_scenario_batch(
    scenario_list: list[Scenario],
    template_path: Path,
    output_base_dir: Path,
    eddypro_executable: Path,
    stream_output: bool,
    metrics_interval: float,
    *,
    site_id: str,
    year: int,
    input_dir: Path,
    ecmd_file: Path | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """
    Execute a batch of scenarios sequentially.

    Args:
        scenario_list: List of Scenario objects to execute
        template_path: Path to EddyPro project template
        output_base_dir: Base directory for all scenario outputs
        eddypro_executable: Path to EddyPro executable
        stream_output: Whether to stream subprocess output
        metrics_interval: Performance monitoring sampling interval
        dry_run: If True, only create files without running EddyPro

    Returns:
        List of scenario metadata dictionaries
    """
    logging.info(f"Starting batch execution of {len(scenario_list)} scenarios")

    scenario_results = []
    for scenario in scenario_list:
        result = run_single_scenario(
            scenario=scenario,
            template_path=template_path,
            output_base_dir=output_base_dir,
            eddypro_executable=eddypro_executable,
            stream_output=stream_output,
            metrics_interval=metrics_interval,
            site_id=site_id,
            year=year,
            input_dir=input_dir,
            ecmd_file=ecmd_file,
            dry_run=dry_run,
        )
        scenario_results.append(result)

    # Summary
    successful = sum(1 for r in scenario_results if r["success"])
    failed = len(scenario_results) - successful

    logging.info(f"Scenario batch completed: {successful} successful, {failed} failed")

    return scenario_results


# TODO: Add remaining functions from eddypro_batch_processor.py
# This is a stub implementation for Milestone 2
# Full refactoring will happen in future milestones
