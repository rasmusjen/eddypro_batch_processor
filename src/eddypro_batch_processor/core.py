"""
EddyPro Batch Processor Core Module.

Contains the core business logic refactored from the original eddypro_batch_processor.py
while preserving existing behavior and outputs.
"""

import logging
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .monitor import MonitoredOperation


class EddyProBatchProcessor:
    """Main class for EddyPro batch processing operations."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the processor with optional config path."""
        self.config_path = config_path or Path("config/config.yaml")
        self.config: Dict[str, Any] = {}

    def load_config(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
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
                config: Dict[str, Any] = yaml.safe_load(file)
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

    def validate_config(self, config: Optional[Dict[str, Any]] = None) -> None:
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
        if not isinstance(metrics_interval, (int, float)) or metrics_interval <= 0:
            logging.error(
                "Invalid 'metrics_interval_seconds' value. "
                "It must be a positive number."
            )
            sys.exit(1)

        logging.info("Configuration validation passed.")


def run_subprocess_with_monitoring(
    command: str,
    working_dir: Path,
    stream_output: bool = True,
    metrics_interval: float = 0.5,
    output_dir: Optional[Path] = None,
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


# TODO: Add remaining functions from eddypro_batch_processor.py
# This is a stub implementation for Milestone 2
# Full refactoring will happen in future milestones
