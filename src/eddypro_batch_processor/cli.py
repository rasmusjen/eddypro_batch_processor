#!/usr/bin/env python3
"""
EddyPro Batch Processor CLI.

Command-line interface for automated EddyPro processing with scenario support
and performance monitoring.
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

from . import core, ecmd, ini_tools, report, scenarios, validation


def setup_logging(log_level: str = "INFO") -> None:
    """Set up console logging with the specified level."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="eddypro-batch",
        description="EddyPro Batch Processor - Automated EddyPro processing with "
        "scenario support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  eddypro-batch --config config/config.yaml run
  eddypro-batch scenarios --site GL-ZaF --years 2021 2022
  eddypro-batch --config config/config.yaml validate
  eddypro-batch status
        """,
    )

    # Global options
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to the configuration YAML file (default: config/config.yaml)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", metavar="COMMAND"
    )

    # Run command
    run_parser = subparsers.add_parser(
        "run", help="Process site/years according to config and/or overrides"
    )
    run_parser.add_argument("--site", type=str, help="Override site ID from config")
    run_parser.add_argument(
        "--years", nargs="+", type=int, help="Override years to process"
    )
    run_parser.add_argument(
        "--input-dir-pattern", type=str, help="Override input directory pattern"
    )
    run_parser.add_argument(
        "--output-dir-pattern", type=str, help="Override output directory pattern"
    )
    run_parser.add_argument(
        "--eddypro-exe", type=str, help="Override EddyPro executable path"
    )
    run_parser.add_argument(
        "--stream-output",
        action="store_true",
        help="Enable real-time output streaming",
    )
    run_parser.add_argument(
        "--no-stream-output",
        action="store_true",
        help="Disable real-time output streaming",
    )
    run_parser.add_argument("--mp", action="store_true", help="Enable multiprocessing")
    run_parser.add_argument(
        "--max-proc", type=int, help="Maximum number of processes for multiprocessing"
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate files without executing EddyPro",
    )
    run_parser.add_argument(
        "--metrics-interval",
        type=float,
        default=0.5,
        help="Performance monitoring sampling interval in seconds (default: 0.5)",
    )
    run_parser.add_argument(
        "--reports-dir",
        type=str,
        help="Custom reports directory (default: {output_dir}/reports)",
    )
    run_parser.add_argument(
        "--report-charts",
        choices=["plotly", "svg", "none"],
        default="plotly",
        help="Chart engine for reports (default: plotly)",
    )

    # INI parameter overrides for run command
    run_parser.add_argument(
        "--rot-meth",
        type=int,
        choices=[1, 3],
        help="Rotation method override (1=DR, 3=PF)",
    )
    run_parser.add_argument(
        "--tlag-meth",
        type=int,
        choices=[2, 4],
        help="Time lag method override (2=CMD, 4=AO)",
    )
    run_parser.add_argument(
        "--detrend-meth",
        type=int,
        choices=[0, 1],
        help="Detrend method override (0=BA, 1=LD)",
    )
    run_parser.add_argument(
        "--despike-vm",
        type=int,
        choices=[0, 1],
        help="Spike removal method override (0=VM97, 1=M13)",
    )

    # Scenarios command
    scenarios_parser = subparsers.add_parser(
        "scenarios", help="Run Cartesian product of supplied INI parameter values"
    )
    scenarios_parser.add_argument(
        "--rot-meth",
        nargs="+",
        type=int,
        choices=[1, 3],
        help="Rotation methods (1=DR, 3=PF)",
    )
    scenarios_parser.add_argument(
        "--tlag-meth",
        nargs="+",
        type=int,
        choices=[2, 4],
        help="Time lag methods (2=CMD, 4=AO)",
    )
    scenarios_parser.add_argument(
        "--detrend-meth",
        nargs="+",
        type=int,
        choices=[0, 1],
        help="Detrend methods (0=BA, 1=LD)",
    )
    scenarios_parser.add_argument(
        "--despike-vm",
        nargs="+",
        type=int,
        choices=[0, 1],
        help="Spike removal methods (0=VM97, 1=M13)",
    )
    scenarios_parser.add_argument(
        "--max-scenarios",
        type=int,
        default=32,
        help="Maximum number of scenarios (default: 32)",
    )
    scenarios_parser.add_argument("--site", type=str, help="Site ID to process")
    scenarios_parser.add_argument(
        "--years", nargs="+", type=int, help="Years to process"
    )
    scenarios_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate files without executing EddyPro",
    )
    scenarios_parser.add_argument(
        "--metrics-interval",
        type=float,
        default=0.5,
        help="Performance monitoring sampling interval in seconds (default: 0.5)",
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate config and environment"
    )
    validate_parser.add_argument(
        "--skip-paths", action="store_true", help="Skip path existence checks"
    )
    validate_parser.add_argument(
        "--skip-ecmd", action="store_true", help="Skip ECMD file validation"
    )

    # Status command
    status_parser = subparsers.add_parser(
        "status", help="Summarize last run results from provenance/manifest"
    )
    status_parser.add_argument(
        "--reports-dir", type=str, help="Override reports directory path"
    )

    return parser


def cmd_run(args: argparse.Namespace) -> int:  # noqa: PLR0912, PLR0915
    """Execute the run command.

    Orchestrates the full processing pipeline:
    1. Load and validate configuration
    2. Apply CLI overrides
    3. Generate project files with parameter overrides
    4. Execute EddyPro processing (or dry-run)
    5. Capture metrics and generate reports

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logging.info("Starting EddyPro batch processing run...")
    start_time = datetime.now()

    # Load configuration
    config_path = Path(args.config)
    processor = core.EddyProBatchProcessor(config_path)
    try:
        config = processor.load_config()
        processor.validate_config(config)
    except SystemExit:
        return 1

    # Collect INI parameter overrides
    ini_parameters = {}
    if args.rot_meth is not None:
        ini_parameters["rot_meth"] = args.rot_meth
    if args.tlag_meth is not None:
        ini_parameters["tlag_meth"] = args.tlag_meth
    if args.detrend_meth is not None:
        ini_parameters["detrend_meth"] = args.detrend_meth
    if args.despike_vm is not None:
        ini_parameters["despike_vm"] = args.despike_vm

    # Validate INI parameters if any provided
    if ini_parameters:
        try:
            validated_params = ini_tools.validate_parameters(ini_parameters)
            logging.info(f"INI parameter overrides: {validated_params}")
        except ini_tools.INIParameterError as e:
            logging.error(f"Invalid INI parameter: {e}")  # noqa: TRY400
            return 1

    # Apply CLI overrides to config
    if getattr(args, "site", None):
        config["site_id"] = args.site
    if getattr(args, "years", None):
        config["years_to_process"] = args.years
    if getattr(args, "input_dir_pattern", None):
        config["input_dir_pattern"] = args.input_dir_pattern
    if getattr(args, "output_dir_pattern", None):
        config["output_dir_pattern"] = args.output_dir_pattern
    if getattr(args, "eddypro_exe", None):
        config["eddypro_executable"] = args.eddypro_exe
    if getattr(args, "stream_output", False):
        config["stream_output"] = True
    if getattr(args, "no_stream_output", False):
        config["stream_output"] = False
    if getattr(args, "mp", False):
        config["multiprocessing"] = True
    if getattr(args, "max_proc", None):
        config["max_processes"] = args.max_proc
    if getattr(args, "metrics_interval", None):
        config["metrics_interval_seconds"] = args.metrics_interval
    if getattr(args, "reports_dir", None):
        config["reports_dir"] = args.reports_dir
    if getattr(args, "report_charts", None):
        config["report_charts"] = args.report_charts

    # Extract key settings
    site_id = config["site_id"]
    years = config["years_to_process"]
    eddypro_exe = Path(config["eddypro_executable"])
    stream_output = config.get("stream_output", True)
    metrics_interval = config.get("metrics_interval_seconds", 0.5)
    dry_run = args.dry_run
    config["dry_run"] = dry_run  # Store in config for manifest

    if dry_run:
        logging.info("Dry run mode enabled - EddyPro will not be executed")

    # Find project template
    default_template = "config/EddyProProject_template.ini"
    template_path = Path(config.get("project_template", default_template))
    if not template_path.exists():
        # Try alternate locations
        alternate_paths = [
            Path("config/EddyProProject_template.ini"),
            (
                Path(__file__).parent.parent.parent
                / "config"
                / "EddyProProject_template.ini"
            ),
        ]
        for alt_path in alternate_paths:
            if alt_path.exists():
                template_path = alt_path
                break

        if not template_path.exists():
            logging.error(f"Project template not found: {template_path}")
            return 1

    # Process each year
    overall_success = True
    years_processed = []

    for year in years:
        logging.info(f"Processing year {year} for site {site_id}")

        # Determine paths
        output_pattern = config["output_dir_pattern"]
        output_dir = Path(output_pattern.format(year=year, site_id=site_id))

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate project file with parameter overrides and patched paths
        project_file = output_dir / f"{site_id}_{year}.eddypro"
        try:
            ini_config = ini_tools.read_ini_template(template_path)
            if ini_parameters:
                validated_params = ini_tools.validate_parameters(ini_parameters)
                ini_tools.patch_ini_parameters(ini_config, validated_params)

            # Materialize metadata files early (idempotent)
            try:
                # Copy site-specific metadata template -> {site}.metadata
                metadata_template = Path("config") / f"{site_id}_metadata_template.ini"
                if not metadata_template.exists():
                    metadata_template = Path("config") / "metadata_template.ini"

                if metadata_template.exists():
                    shutil.copyfile(
                        metadata_template, output_dir / f"{site_id}.metadata"
                    )
                else:
                    logging.warning(
                        f"No metadata template found for site {site_id}, "
                        "skipping .metadata file generation"
                    )

                # Generate dynamic metadata from ECMD CSV (all years included)
                ecmd_file_pattern = config.get("ecmd_file", "")
                if "{site_id}" in ecmd_file_pattern:
                    ecmd_file = Path(ecmd_file_pattern.format(site_id=site_id))
                else:
                    ecmd_file = Path(ecmd_file_pattern)

                dyn_metadata_filename = f"{site_id}_dynamic_metadata.txt"
                if ecmd_file.exists():
                    ecmd.generate_dynamic_metadata(
                        ecmd_path=ecmd_file,
                        output_path=output_dir / dyn_metadata_filename,
                        site_id=site_id,
                    )
                else:
                    logging.warning(
                        f"ECMD file not found at {ecmd_file}, "
                        "skipping dynamic metadata generation"
                    )

            except Exception as meta_err:
                logging.warning(f"Failed to materialize metadata files: {meta_err}")

            # Patch path fields
            # Input path from configured pattern
            input_pattern = config.get("input_dir_pattern", "")
            data_path_value = input_pattern.format(year=year, site_id=site_id)
            ini_tools.patch_ini_paths(
                ini_config,
                proj_file=str(output_dir / f"{site_id}.metadata"),
                dyn_metadata_file=str(output_dir / f"{site_id}_dynamic_metadata.txt"),
                data_path=data_path_value,
                out_path=str(output_dir),
            )

            # Patch Project metadata fields (creation_date, project_title, etc.)
            ini_tools.patch_project_metadata(
                ini_config,
                site_id=site_id,
                year=year,
                scenario_suffix="",
            )

            ini_tools.write_ini_file(ini_config, project_file)

            logging.info(f"Created project file: {project_file}")

            # Preflight validation: check data_path and file availability
            if not dry_run:
                try:
                    ini_tools.validate_eddypro_inputs(ini_config)
                    ini_tools.validate_eddypro_metadata(ini_config)
                except ini_tools.INIParameterError:
                    logging.exception(f"Preflight validation failed for year {year}")
                    overall_success = False
                    continue

        except Exception:
            logging.exception("Failed to create project file")
            overall_success = False
            continue

        # Execute EddyPro (or skip in dry-run mode)
        if not dry_run:
            # Ensure we pass the project file to EddyPro executable
            # Use the same OS flag as core runner (-s win/linux) for consistency
            os_suffix = "win" if sys.platform.startswith("win") else "linux"
            command = f'"{eddypro_exe}" -s {os_suffix} "{project_file}"'
            exit_code = core.run_subprocess_with_monitoring(
                command=command,
                working_dir=output_dir,
                stream_output=stream_output,
                metrics_interval=metrics_interval,
                output_dir=output_dir,
                scenario_suffix="",
            )

            if exit_code != 0:
                logging.error(f"EddyPro processing failed for year {year}")
                overall_success = False
            else:
                msg = f"EddyPro processing completed successfully for year {year}"
                logging.info(msg)
                years_processed.append(year)
        else:
            logging.info(f"Dry run: skipped EddyPro execution for year {year}")
            years_processed.append(year)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Generate reports
    if years_processed:
        try:
            output_pattern = config["output_dir_pattern"]
            first_year_dir = output_pattern.format(year=years[0], site_id=site_id)
            output_base = Path(first_year_dir)
            core.generate_run_report(
                config=config,
                site_id=site_id,
                years_processed=years_processed,
                output_base_dir=output_base,
                start_time=start_time,
                end_time=end_time,
                overall_success=overall_success,
            )
            logging.info("Reports generated successfully")
        except Exception as e:
            logging.warning(f"Failed to generate reports: {e}")

    # Final summary
    logging.info(f"Processing completed in {duration:.1f}s")
    if overall_success and years_processed:
        logging.info(f"Successfully processed {len(years_processed)} year(s)")
        return 0
    else:
        logging.error("Processing completed with errors")
        return 1


def cmd_scenarios(args: argparse.Namespace) -> int:  # noqa: PLR0911
    """Execute the scenarios command."""
    logging.info("Starting scenario matrix processing...")

    # Collect parameter options for Cartesian product
    parameter_options = {}
    if args.rot_meth:
        parameter_options["rot_meth"] = args.rot_meth
    if args.tlag_meth:
        parameter_options["tlag_meth"] = args.tlag_meth
    if args.detrend_meth:
        parameter_options["detrend_meth"] = args.detrend_meth
    if args.despike_vm:
        parameter_options["despike_vm"] = args.despike_vm

    if not parameter_options:
        logging.error(
            "No parameter options provided. Specify at least one parameter "
            "with multiple values (e.g., --rot-meth 1 3)"
        )
        return 1

    # Validate each parameter value in the options
    try:
        for param_name, values in parameter_options.items():
            for value in values:
                ini_tools.validate_parameter(param_name, value)
        logging.info(f"Parameter options for scenarios: {parameter_options}")
    except ini_tools.INIParameterError as e:
        logging.error(f"Invalid scenario parameter: {e}")  # noqa: TRY400
        return 1

    # Generate scenarios with Cartesian product
    try:
        scenario_list = scenarios.generate_scenarios(
            parameter_options=parameter_options,
            max_scenarios=args.max_scenarios,
        )
    except scenarios.ScenarioLimitExceededError as e:
        logging.error(str(e))  # noqa: TRY400
        return 1
    except ValueError as e:
        logging.error(f"Scenario generation error: {e}")  # noqa: TRY400
        return 1

    # Display scenario summary
    summary = scenarios.format_scenario_summary(scenario_list)
    logging.info("\n" + summary)

    # Load configuration
    config_path = Path(args.config)
    processor = core.EddyProBatchProcessor(config_path)
    try:
        config = processor.load_config()
        processor.validate_config(config)
    except SystemExit:
        return 1

    # Apply CLI overrides
    site_id = args.site if args.site else config.get("site_id")
    years = args.years if args.years else config.get("years_to_process", [])
    eddypro_exe = Path(config["eddypro_executable"])
    stream_output = config.get("stream_output", True)
    metrics_interval = args.metrics_interval

    if not site_id:
        logging.error("Site ID not provided via CLI or config")
        return 1

    if not years:
        logging.error("Years to process not provided via CLI or config")
        return 1

    # Process each year with all scenarios
    start_time = datetime.now()
    all_scenario_results = []

    for year in years:
        logging.info(f"Processing year {year} with {len(scenario_list)} scenarios")

        # Determine paths
        input_pattern = config.get("input_dir_pattern", "")
        output_pattern = config.get("output_dir_pattern", "")

        input_dir = Path(input_pattern.format(year=year, site_id=site_id))
        output_base_dir = Path(output_pattern.format(year=year, site_id=site_id))

        if not input_dir.exists():
            logging.warning(f"Input directory not found: {input_dir}, skipping year")
            continue

        # Template project file path (from config or default)
        default_template = "config/EddyProProject_template.ini"
        template_path = Path(config.get("project_template", default_template))
        if not template_path.exists():
            # Try alternate locations
            alternate_paths = [
                Path("config/EddyProProject_template.ini"),
                (
                    Path(__file__).parent.parent.parent
                    / "config"
                    / "EddyProProject_template.ini"
                ),
            ]
            for alt_path in alternate_paths:
                if alt_path.exists():
                    template_path = alt_path
                    break

            if not template_path.exists():
                logging.error(f"Project template not found: {template_path}")
                return 1

        # Determine ECMD file path
        ecmd_file_pattern = config.get("ecmd_file", "")
        if ecmd_file_pattern:
            if "{site_id}" in ecmd_file_pattern:
                ecmd_file_path = Path(ecmd_file_pattern.format(site_id=site_id))
            else:
                ecmd_file_path = Path(ecmd_file_pattern)
        else:
            ecmd_file_path = None

        # Run scenario batch
        scenario_results = core.run_scenario_batch(
            scenario_list=scenario_list,
            template_path=template_path,
            output_base_dir=output_base_dir,
            eddypro_executable=eddypro_exe,
            stream_output=stream_output,
            metrics_interval=metrics_interval,
            site_id=site_id,
            year=year,
            input_dir=input_dir,
            ecmd_file=ecmd_file_path,
            dry_run=hasattr(args, "dry_run") and args.dry_run,
        )

        # Collect results for reporting
        all_scenario_results.extend(scenario_results)

        # Log results
        successful = sum(1 for r in scenario_results if r["success"])
        failed = len(scenario_results) - successful
        logging.info(f"Year {year}: {successful} scenarios successful, {failed} failed")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logging.info(f"Scenario processing completed in {duration:.1f}s")

    # Generate reports with actual scenario information
    if years and all_scenario_results:
        try:
            output_pattern = config.get("output_dir_pattern", "")
            first_year_dir = output_pattern.format(year=years[0], site_id=site_id)
            output_base = Path(first_year_dir)

            # Create reports directory
            reports_dir_config = config.get("reports_dir")
            if reports_dir_config:
                reports_dir = Path(reports_dir_config)
            else:
                reports_dir = output_base / "reports"
            reports_dir = report.create_reports_directory(
                reports_dir.parent, reports_dir.name
            )

            # Generate run ID
            run_id = f"{site_id}_{start_time.strftime('%Y%m%d_%H%M%S')}"

            # Collect output directories from scenario results
            output_dirs = []
            for result in all_scenario_results:
                output_dir = result.get("output_dir")
                if output_dir:
                    output_dir_path = Path(output_dir)
                    if output_dir_path.exists():
                        output_dirs.append(output_dir_path)

            # Compute config checksum
            config_checksum = str(hash(json.dumps(config, sort_keys=True)))

            # Build scenario list for manifest
            manifest_scenarios = []
            for result in all_scenario_results:
                manifest_scenarios.append(
                    {
                        "scenario_index": result.get("scenario_index", 0),
                        "scenario_suffix": result.get("scenario_suffix", ""),
                        "scenario_params": result.get("scenario_params", {}),
                        "start_time": result.get("start_time", start_time.isoformat()),
                        "end_time": result.get("end_time", end_time.isoformat()),
                        "duration_seconds": result.get("duration_seconds", 0),
                        "success": result.get("success", False),
                    }
                )

            # Generate and write manifest
            manifest = report.generate_run_manifest(
                run_id=run_id,
                config=config,
                config_checksum=config_checksum,
                site_id=site_id,
                years_processed=years,
                scenarios=manifest_scenarios,
                start_time=start_time,
                end_time=end_time,
                overall_success=all(r["success"] for r in all_scenario_results),
                output_dirs=output_dirs,
            )

            # Add dry_run flag to config for manifest
            manifest["dry_run"] = hasattr(args, "dry_run") and args.dry_run

            # Write manifest
            manifest_path = reports_dir / "run_manifest.json"
            report.write_run_manifest(manifest, manifest_path)

            logging.info("Reports generated successfully")
        except Exception:
            logging.exception("Failed to generate reports")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute the validate command."""
    logging.info("Validating configuration and environment...")
    logging.info(f"Config file: {args.config}")

    # Load configuration
    config_path = Path(args.config)
    processor = core.EddyProBatchProcessor(config_path)

    try:
        config = processor.load_config()
    except SystemExit:
        # SystemExit already logged by load_config
        return 1

    # Run all validations
    results = validation.validate_all(
        config=config, skip_paths=args.skip_paths, skip_ecmd=args.skip_ecmd
    )

    # Format and display report
    validation_report = validation.format_validation_report(results)
    print("\n" + validation_report)

    # Count total errors
    total_errors = sum(len(errors) for errors in results.values())

    if total_errors == 0:
        logging.info("[PASS] Validation passed successfully")
        return 0
    else:
        logging.error(f"[FAIL] Validation failed with {total_errors} error(s)")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Execute the status command.

    Read and display the last run manifest with formatted output showing:
    - Run summary (ID, duration, success status)
    - Scenario table with results
    - Key metrics if available

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure/manifest not found)
    """
    logging.info("Checking last run status...")

    # Determine reports directory
    if args.reports_dir:
        reports_dir = Path(args.reports_dir)
    else:
        # Try to find manifest in common locations
        config_path = Path(args.config)
        try:
            processor = core.EddyProBatchProcessor(config_path)
            config = processor.load_config()
            reports_dir_config = config.get("reports_dir")
            if reports_dir_config:
                reports_dir = Path(reports_dir_config)
            else:
                # Use default pattern
                site_id = config.get("site_id", "")
                years = config.get("years_to_process", [])
                if site_id and years:
                    output_pattern = config.get("output_dir_pattern", "")
                    first_year_dir = output_pattern.format(
                        year=years[0], site_id=site_id
                    )
                    reports_dir = Path(first_year_dir) / "reports"
                else:
                    logging.error("Cannot determine reports directory from config")
                    return 1
        except Exception:
            logging.exception("Failed to load config for status check")
            return 1

    # Look for manifest file
    manifest_path = reports_dir / "run_manifest.json"
    if not manifest_path.exists():
        logging.error(f"No manifest found at: {manifest_path}")
        logging.info(
            "Tip: Run processing first or specify --reports-dir if using "
            "a custom location"
        )
        return 1

    # Load and parse manifest
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError:
        logging.exception(f"Corrupt manifest file: {manifest_path}")
        return 1
    except Exception:
        logging.exception(f"Failed to read manifest: {manifest_path}")
        return 1

    # Display formatted status
    print("\n" + "=" * 70)
    print("EddyPro Batch Processing Status")
    print("=" * 70)

    # Run summary
    run_id = manifest.get("run_id", "unknown")
    start_time_str = manifest.get("start_time", "")
    end_time_str = manifest.get("end_time", "")
    duration = manifest.get("duration_seconds", 0)
    dry_run = manifest.get("dry_run", False)

    print(f"\nRun ID: {run_id}")
    print(f"Start Time: {start_time_str}")
    print(f"End Time: {end_time_str}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Mode: {'Dry Run' if dry_run else 'Production'}")

    # Scenarios summary
    scenarios_data = manifest.get("scenarios", [])
    if scenarios_data:
        print(f"\nScenarios Processed: {len(scenarios_data)}")
        print("\n" + "-" * 70)
        print(f"{'Scenario':<25} {'Duration (s)':<15} {'Status':<10}")
        print("-" * 70)

        for scenario in scenarios_data:
            scenario_name = scenario.get("scenario_name", "unknown")
            scenario_duration = scenario.get("duration_seconds", 0)
            scenario_success = scenario.get("success", False)
            status = "SUCCESS" if scenario_success else "FAILED"

            print(f"{scenario_name:<25} {scenario_duration:<15.1f} {status:<10}")

    # Metrics summary
    metrics_summary = manifest.get("metrics_summary", {})
    if metrics_summary:
        print("\n" + "-" * 70)
        print("Performance Metrics")
        print("-" * 70)
        for key, value in metrics_summary.items():
            if isinstance(value, int | float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")

    # Output paths
    outputs = manifest.get("outputs", [])
    if outputs:
        print("\n" + "-" * 70)
        print("Output Directories")
        print("-" * 70)
        for output_path in outputs:
            print(f"  {output_path}")

    print("\n" + "=" * 70)
    print(f"Manifest location: {manifest_path}")
    print("=" * 70 + "\n")

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Set up logging early
    setup_logging(args.log_level)

    # Validate config file exists if provided
    if hasattr(args, "config") and args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            logging.error(f"Configuration file not found: {config_path}")
            return 1

    # Route to appropriate command handler
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "scenarios":
        return cmd_scenarios(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "status":
        return cmd_status(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
