#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
eddypro_batch_processor.py

Automates the batch processing of EddyPro projects based on raw data files and templates.

This script performs the following tasks:
1. Loads configuration settings from a YAML file.
2. Sets up logging for both console and file outputs.
3. Scans raw data directories for EddyPro-compatible CSV files.
4. Modifies EddyPro project files based on raw data and predefined templates.
5. Executes EddyPro subprocesses (`eddypro_rp` and `eddypro_fcc`) with optional real-time output streaming.
6. Tracks and logs the processing progress, including elapsed and estimated remaining time.

Usage:
    python eddypro_batch_processor.py

Configuration:
    The script relies on a `config.yaml` file located in the `config/` subdirectory. This file specifies paths,
    site identifiers, years to process, and other relevant settings.

Author:
    Rasmus Jensen [raje at ecos.au.dk]

License:
    GNU GPLv3

Requirements:
    - Python 3.6+
    - PyYAML library (`pip install pyyaml`)
    - EddyPro installed and accessible at the specified path in `config.yaml`

Example `config.yaml`:
    # Configuration for EddyPro processing job
    
    # Specify the path to the EddyPro executable
    eddypro_executable: "C:/Program Files/LI-COR/EddyPro-7.0.9/bin/eddypro_rp.exe"
    
    # Specify the site ID you want to process
    site_id: GL-ZaF
    
    # List of years you want to process for this site
    years_to_process:
      - 2021
      - 2022
      - 2023
    
    # Input directory pattern for each year and site
    # Use `{year}` and `{site_id}` as placeholders
    input_dir_pattern: "C:/Users/au710242/Code/Python/eddypro_batch_processor/data/raw/{site_id}/{year}"
    
    # Output directory pattern for each year and site
    # Use `{year}` and `{site_id}` as placeholders
    output_dir_pattern: "C:/Users/au710242/Code/Python/eddypro_batch_processor/data/processed/{site_id}/{year}/eddypro/processing"
    
    # Enable or disable multiprocessing
    multiprocessing: False
    
    # Control output streaming
    stream_output: True  # Set to False to keep the output quiet
"""

import os
import yaml
import subprocess
import logging
import re
from datetime import datetime, timedelta
import shutil
import platform
from pathlib import Path
import sys
import time
import argparse
import multiprocessing
from multiprocessing import Pool
from logging.handlers import RotatingFileHandler

def load_config(config_path: Path) -> dict:
    """
    Load the YAML configuration file.

    This function attempts to read and parse a YAML configuration file from the specified path.
    It handles scenarios where the file is missing or contains invalid YAML syntax by logging 
    appropriate error messages and exiting the script.

    Args:
        config_path (Path): 
            The file system path to the YAML configuration file.

    Returns:
        dict: 
            A dictionary containing configuration parameters loaded from the YAML file.

    Raises:
        SystemExit: 
            If the configuration file is not found or contains invalid YAML.
    """
    try:
        with config_path.open("r") as file:
            config = yaml.safe_load(file)
            logging.info(f"Configuration loaded successfully from {config_path}")
            return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing the configuration file: {e}")
        sys.exit(1)

def validate_config(config: dict) -> None:
    """
    Validate the essential configuration parameters.

    Args:
        config (dict): The configuration dictionary loaded from the YAML file.

    Returns:
        None

    Raises:
        SystemExit: If any required configuration parameter is missing or invalid.
    """
    required_keys = [
        "eddypro_executable",
        "site_id",
        "years_to_process",
        "input_dir_pattern",
        "output_dir_pattern",
        "stream_output",
        "log_level",
        "multiprocessing",
        "max_processes"
    ]
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        logging.error(f"Missing configuration parameters: {', '.join(missing_keys)}")
        sys.exit(1)

    # Validate max_processes
    max_processes = config.get("max_processes")
    if not isinstance(max_processes, int) or max_processes < 1:
        logging.error("Invalid 'max_processes' value. It must be a positive integer.")
        sys.exit(1)

def setup_logging(log_level: str) -> None:
    """
    Configure logging with handlers for both file and console outputs.

    Args:
        log_level (str): 
            The logging level for console output (e.g., DEBUG, INFO).
    
    Returns:
        None
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Capture all levels of logs

    # Ensure the logs directory exists
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Rotating File handler for detailed logs
    file_handler = RotatingFileHandler(logs_dir / "eddypro_processing.log", maxBytes=5*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Console handler for specified log level
    console_handler = logging.StreamHandler()
    try:
        # Convert string log_level to logging constant
        console_level = getattr(logging, log_level.upper())
    except AttributeError:
        console_level = logging.INFO  # Default to INFO if invalid level
        logging.warning(f"Invalid log level '{log_level}' specified. Falling back to INFO.")
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(
        "%(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # Clear existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def get_raw_files(raw_data_dir: Path, site_id: str) -> list:
    """
    Retrieve a list of raw data files matching the specific naming pattern.

    This function scans the specified raw data directory and returns a list of files
    that match the naming convention: {site_id}_EC_YYYYMMDDHHMM_F10.csv. It ensures that
    only files (not directories) are included in the returned list.

    Args:
        raw_data_dir (Path): 
            The directory containing raw data files to be processed.
        site_id (str): 
            The identifier for the site, used to construct the filename pattern.

    Returns:
        list: 
            A list of Path objects representing the raw data files that match the pattern.
    """
    # Compile regex pattern for efficiency
    pattern = re.compile(rf"{re.escape(site_id)}_EC_\d{{12}}_F10\.csv")
    # List comprehension to filter files matching the pattern
    matching_files = [
        file for file in raw_data_dir.iterdir()
        if file.is_file() and pattern.match(file.name)
    ]
    logging.debug(f"Found {len(matching_files)} raw files in {raw_data_dir}")
    return matching_files

def modify_project_file(
    template_file: Path,
    project_file: Path,
    raw_data_dir: Path,
    output_dir: Path,
    site_id: str,
    year: int
) -> int:
    """
    Modify the EddyPro project file based on raw data and template.

    This function reads a project template file, updates various parameters such as file paths
    and data periods based on the available raw data, and writes the modified project file to
    the specified output directory. It also copies necessary metadata files to the output location.

    Args:
        template_file (Path): 
            The path to the EddyPro project template file.
        project_file (Path): 
            The path where the modified EddyPro project file will be saved.
        raw_data_dir (Path): 
            The directory containing raw data files used to determine data period coverage.
        output_dir (Path): 
            The directory where processed data and metadata files will be stored.
        site_id (str): 
            The identifier for the site, used in constructing file names.
        year (int): 
            The year corresponding to the data being processed, used in file naming.

    Returns:
        int: 
            The number of raw data files processed. Returns 0 if no files were found or if an error occurred.
    """
    raw_files = get_raw_files(raw_data_dir, site_id)
    if not raw_files:
        logging.warning(f"No raw data files found in {raw_data_dir}")
        return 0  # No files processed

    # Extract timestamps from filenames using regex
    timestamps = []
    for file in raw_files:
        match = re.search(rf"{re.escape(site_id)}_EC_(\d{{12}})_F10\.csv", file.name)
        if match:
            timestamp_str = match.group(1)
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M")
                timestamps.append(timestamp)
            except ValueError:
                logging.error(f"Invalid timestamp format in file: {file.name}")
                continue  # Skip files with invalid timestamps

    if not timestamps:
        logging.warning(f"No valid timestamps found in {raw_data_dir}")
        return 0

    start_time, end_time = min(timestamps), max(timestamps)

    # Read the template file content
    try:
        with template_file.open("r") as file:
            project_data = file.read()
    except FileNotFoundError:
        logging.error(f"Template file not found: {template_file}")
        return 0

    # Convert paths to POSIX format to avoid regex escape issues on Windows
    proj_file_path = (output_dir / f"{site_id}_{year}.metadata").as_posix()
    dyn_metadata_path = (output_dir / f"{site_id}_{year}_dynamic_metadata.txt").as_posix()
    out_path = output_dir.as_posix()
    data_path = raw_data_dir.as_posix()

    # Define patterns and their replacements
    replacements = {
        r'proj_file\s*=.*': f'proj_file={proj_file_path}',
        r'dyn_metadata_file\s*=.*': f'dyn_metadata_file={dyn_metadata_path}',
        r'out_path\s*=.*': f'out_path={out_path}',
        r'data_path\s*=.*': f'data_path={data_path}',
        r'last_change_date\s*=.*': f'last_change_date={datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}',
        r'project_id\s*=.*': f'project_id={site_id}',
        r'project_title\s*=.*$': f'project_title={site_id}'
    }

    # Apply all replacements to the project data
    for pattern, replacement in replacements.items():
        project_data = re.sub(pattern, replacement, project_data, flags=re.MULTILINE)

    # Ensure the output directory exists
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logging.debug(f"Ensured output directory exists: {output_dir}")
    except Exception as e:
        logging.error(f"Failed to create output directory {output_dir}: {e}")
        return 0

    # Write the modified project data to the project file
    try:
        with project_file.open("w") as file:
            file.write(project_data)
        logging.info(f"Modified project file written: {project_file}")
    except IOError as e:
        logging.error(f"Failed to write to project file {project_file}: {e}")
        return 0

    # Paths to dynamic metadata and metadata template files
    dynamic_metadata_src = template_file.parent / f"{site_id}_dynamic_metadata.ini"
    metadata_template_src = template_file.parent / f"{site_id}_metadata_template.ini"

    # Copy dynamic metadata file
    try:
        shutil.copyfile(dynamic_metadata_src, dyn_metadata_path)
        logging.info(f"Copied dynamic metadata from {dynamic_metadata_src} to {dyn_metadata_path}")
    except FileNotFoundError:
        logging.error(f"Dynamic metadata file not found: {dynamic_metadata_src}")
        return 0
    except IOError as e:
        logging.error(f"Failed to copy dynamic metadata file: {e}")
        return 0

    # Copy metadata template file
    try:
        shutil.copyfile(metadata_template_src, proj_file_path)
        logging.info(f"Copied metadata template from {metadata_template_src} to {proj_file_path}")
    except FileNotFoundError:
        logging.error(f"Metadata template file not found: {metadata_template_src}")
        return 0
    except IOError as e:
        logging.error(f"Failed to copy metadata template file: {e}")
        return 0

    logging.info(
        f"Modified project file {project_file} with data period {start_time} to {end_time}"
    )
    return len(raw_files)

def run_subprocess(command: str, working_dir: Path) -> int:
    """
    Execute a subprocess command and stream its output in real-time.

    This function runs the given command in a subprocess, streams the output to the terminal
    as it is generated, and returns the subprocess's exit code. It handles exceptions by
    logging errors and returning a non-zero code.

    Args:
        command (str): 
            The command line string to be executed in the subprocess.
        working_dir (Path): 
            The directory in which to execute the subprocess command.

    Returns:
        int: 
            The return code of the subprocess. Returns -1 if an exception occurs.
    """
    try:
        # Initialize the subprocess with appropriate parameters
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=working_dir
        )
        # Stream the output line by line as it becomes available
        for line in process.stdout:
            print(line, end='')  # Print to terminal without adding extra newline
        process.wait()  # Wait for the subprocess to finish
        logging.debug(f"Subprocess finished with return code {process.returncode}")
        return process.returncode
    except Exception as e:
        logging.error(f"Failed to execute command '{command}': {e}")
        return -1

def run_eddypro(
    project_file: Path,
    eddypro_executable: Path,
    stream_output: bool
) -> None:
    """
    Run EddyPro processing using the specified project file.
    """
    output_dir = project_file.parent
    eddypro_path = output_dir.parent
    tmp_dir = eddypro_path / "tmp"
    bin_dir = eddypro_path / "bin"

    # Create temporary directories for processing
    tmp_dir.mkdir(exist_ok=True)
    bin_dir.mkdir(exist_ok=True)
    logging.debug(f"Created temporary directories: {tmp_dir}, {bin_dir}")

    # Copy EddyPro binaries to the bin directory
    try:
        shutil.copytree(
            eddypro_executable.parent, bin_dir, dirs_exist_ok=True
        )
        logging.info(f"Copied EddyPro binaries from {eddypro_executable.parent} to {bin_dir}")
    except Exception as e:
        logging.error(f"Failed to copy EddyPro binaries: {e}")
        return

    # Determine the operating system suffix
    os_suffix = "win" if platform.system() == "Windows" else "linux"

    # Define paths to the EddyPro executables
    rp_executable = bin_dir / (
        "eddypro_rp.exe" if platform.system() == "Windows" else "eddypro_rp"
    )
    fcc_executable = bin_dir / (
        "eddypro_fcc.exe" if platform.system() == "Windows" else "eddypro_fcc"
    )

    # Verify that the executables exist
    if not rp_executable.exists():
        logging.error(f"EddyPro rp executable not found: {rp_executable}")
        return
    if not fcc_executable.exists():
        logging.error(f"EddyPro fcc executable not found: {fcc_executable}")
        return

    # Construct command-line arguments
    command_sys = f" -s {os_suffix} "
    rp_command = f'"{rp_executable}"{command_sys}"{project_file}"'
    fcc_command = f'"{fcc_executable}"{command_sys}"{project_file}"'

    # Execute eddypro_rp
    logging.info("Starting eddypro_rp...")
    if stream_output:
        # Stream output in real-time
        return_code = run_subprocess(rp_command, eddypro_path)
        if return_code != 0:
            logging.error("Error running eddypro_rp")
    else:
        # Run quietly and capture outputs
        try:
            rp_result = subprocess.run(
                rp_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=eddypro_path
            )
            if rp_result.returncode != 0:
                logging.error(f"Error running eddypro_rp:\n{rp_result.stderr}")
            else:
                logging.debug(rp_result.stdout)
        except Exception as e:
            logging.error(f"Failed to run eddypro_rp: {e}")

    # Execute eddypro_fcc
    logging.info("Starting eddypro_fcc...")
    if stream_output:
        # Stream output in real-time
        return_code = run_subprocess(fcc_command, eddypro_path)
        if return_code != 0:
            logging.error("Error running eddypro_fcc")
    else:
        # Run quietly and capture outputs
        try:
            fcc_result = subprocess.run(
                fcc_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=eddypro_path
            )
            if fcc_result.returncode != 0:
                logging.error(f"Error running eddypro_fcc:\n{fcc_result.stderr}")
            else:
                logging.debug(fcc_result.stdout)
        except Exception as e:
            logging.error(f"Failed to run eddypro_fcc: {e}")

    # Clean up temporary directories
    try:
        shutil.rmtree(bin_dir)
        shutil.rmtree(tmp_dir)
        logging.debug(f"Cleaned up temporary directories: {bin_dir}, {tmp_dir}")
    except Exception as e:
        logging.warning(f"Failed to clean up temporary directories: {e}")

    logging.info(f"The results of EddyPro run are stored in {output_dir}")

def process_year(args):
    """
    Process a single year for EddyPro batch processing.

    Args:
        args (tuple): A tuple containing all necessary parameters:
            - year (int)
            - site_id (str)
            - input_dir_pattern (str)
            - output_dir_pattern (str)
            - eddypro_executable (Path)
            - stream_output (bool)
            - template_file (Path)

    Returns:
        int: Number of raw files processed for the year.
    """
    (
        year,
        site_id,
        input_dir_pattern,
        output_dir_pattern,
        eddypro_executable,
        stream_output,
        template_file
    ) = args

    raw_data_dir = Path(input_dir_pattern.format(year=year, site_id=site_id))
    output_dir = Path(output_dir_pattern.format(year=year, site_id=site_id))
    project_file = output_dir / f"{site_id}_{year}.eddypro"

    # Modify the project file based on raw data and template
    num_processed = modify_project_file(
        template_file=template_file,
        project_file=project_file,
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        site_id=site_id,
        year=year
    )

    if num_processed == 0:
        logging.info(f"Skipping EddyPro run for year {year} due to no valid raw files.")
        return 0  # No files processed

    # Run EddyPro processing
    run_eddypro(
        project_file=project_file,
        eddypro_executable=eddypro_executable,
        stream_output=stream_output
    )

    return num_processed

def main():
    """
    Main function to orchestrate the EddyPro batch processing workflow.
    """
    # Parse command-line arguments (e.g., specify a custom config file)
    parser = argparse.ArgumentParser(description="EddyPro Batch Processor")
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to the configuration YAML file."
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()

    # Load configuration
    config = load_config(config_path)

    # Validate configuration
    validate_config(config)

    # Extract configuration parameters
    eddypro_executable = Path(config.get("eddypro_executable"))
    site_id = config.get("site_id")
    years = config.get("years_to_process", [])
    input_dir_pattern = config.get("input_dir_pattern")
    output_dir_pattern = config.get("output_dir_pattern")
    stream_output = config.get("stream_output", False)
    log_level = config.get("log_level", "INFO")  # Default to INFO if not specified
    use_multiprocessing = config.get("multiprocessing", False)  # New parameter
    max_processes = config.get("max_processes", multiprocessing.cpu_count())  # New parameter

    # Ensure max_processes does not exceed available CPU cores
    available_cpus = multiprocessing.cpu_count()
    if max_processes > available_cpus:
        logging.warning(
            f"Requested max_processes ({max_processes}) exceeds available CPU cores ({available_cpus}). "
            f"Setting max_processes to {available_cpus}."
        )
        max_processes = available_cpus
    elif max_processes < 1:
        logging.warning(
            f"Invalid max_processes ({max_processes}) specified. "
            f"Setting max_processes to 1."
        )
        max_processes = 1

    # Setup logging with the specified log_level
    setup_logging(log_level)

    # Validate essential configurations
    if not eddypro_executable.exists():
        logging.error(f"EddyPro executable not found: {eddypro_executable}")
        sys.exit(1)

    if not years:
        logging.error("No years specified for processing.")
        sys.exit(1)

    total_raw_files = 0
    raw_files_count = {}

    # Pre-calculate the number of raw files for each year
    for year in years:
        raw_data_dir = Path(input_dir_pattern.format(year=year, site_id=site_id))
        if raw_data_dir.exists():
            raw_files = get_raw_files(raw_data_dir, site_id)
            raw_files_count[year] = len(raw_files)
            total_raw_files += len(raw_files)
        else:
            raw_files_count[year] = 0
            logging.warning(f"Raw data directory does not exist: {raw_data_dir}")

    if total_raw_files == 0:
        logging.error("No raw files found for processing.")
        sys.exit(1)

    processed_raw_files = 0
    start_time = time.time()

    # Prepare arguments for each year
    template_file = Path(__file__).resolve().parent.parent / "config" / "EddyProProject_template.ini"
    args_list = [
        (
            year,
            site_id,
            input_dir_pattern,
            output_dir_pattern,
            eddypro_executable,
            stream_output,
            template_file
        )
        for year in years
    ]

    if use_multiprocessing:
        # Determine the number of processes (use min between max_processes and CPU count)
        num_processes = min(max_processes, multiprocessing.cpu_count())
        logging.info(f"Starting multiprocessing with {num_processes} processes.")

        with Pool(processes=num_processes) as pool:
            results = pool.map(process_year, args_list)
    else:
        # Sequential processing
        results = []
        for args in args_list:
            result = process_year(args)
            results.append(result)

    processed_raw_files = sum(results)

    # Calculate total elapsed time
    elapsed_time = time.time() - start_time

    # Estimate remaining time (if applicable)
    progress = processed_raw_files / total_raw_files
    estimated_total_time = elapsed_time / progress if progress > 0 else 0
    estimated_remaining_time = estimated_total_time - elapsed_time

    # Format time durations as HH:MM:SS
    elapsed_str = str(timedelta(seconds=int(elapsed_time)))
    remaining_str = (
        str(timedelta(seconds=int(estimated_remaining_time)))
        if estimated_remaining_time > 0 else "00:00:00"
    )

    # Log the final progress of processing
    logging.info(
        f"Processed {processed_raw_files}/{total_raw_files} files. "
        f"Elapsed time: {elapsed_str}. Estimated time remaining: {remaining_str}."
    )

if __name__ == "__main__":
    main()
