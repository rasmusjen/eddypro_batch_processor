"""
EddyPro Batch Processor CLI.

Command-line interface for automated EddyPro processing with scenario support
and performance monitoring.
"""

import argparse
import json
import logging
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, NoReturn

from . import (
    __version__,
    analysis,
    core,
    ecmd,
    ini_tools,
    report,
    scenarios,
    validation,
)


def setup_logging(
    log_level: str = "INFO",
    log_file: str | None = None,
    log_max_bytes: int | None = None,
    log_backup_count: int | None = None,
) -> None:
    """Set up console and optional file logging with the specified level."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        max_bytes = 0 if log_max_bytes is None else max(log_max_bytes, 0)
        backup_count = 0 if log_backup_count is None else max(log_backup_count, 0)
        if max_bytes > 0 and backup_count > 0:
            handlers.append(
                RotatingFileHandler(
                    log_path,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding="utf-8",
                )
            )
        else:
            handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
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
        "--version",
        action="version",
        version=f"eddypro-batch {__version__}",
        help="Show the installed package version and exit",
    )
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
        default=None,
        help="Performance monitoring sampling interval in seconds "
        "(default: metrics_interval_seconds from config, or 0.5)",
    )
    run_parser.add_argument(
        "--monitor",
        dest="monitor",
        action="store_true",
        default=None,
        help="Enable performance monitoring (overrides monitoring_enabled in config)",
    )
    run_parser.add_argument(
        "--no-monitor",
        dest="monitor",
        action="store_false",
        help="Disable performance monitoring; no metrics files are written",
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
        "--despike-meth",
        type=int,
        choices=[0, 1],
        help="Spike removal method override (0=VM97, 1=M13)",
    )
    run_parser.add_argument(
        "--hf-meth",
        type=int,
        choices=[1, 4],
        help=(
            "High-frequency spectral correction method override "
            "(1=Moncrieff 1997 analytic, 4=Fratini 2012 in situ/analytic)"
        ),
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
        "--despike-meth",
        nargs="+",
        type=int,
        choices=[0, 1],
        help="Spike removal methods (0=VM97, 1=M13)",
    )
    scenarios_parser.add_argument(
        "--hf-meth",
        nargs="+",
        type=int,
        choices=[1, 4],
        help=(
            "High-frequency spectral correction methods "
            "(1=Moncrieff 1997 analytic, 4=Fratini 2012 in situ/analytic)"
        ),
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
        default=None,
        help="Performance monitoring sampling interval in seconds "
        "(default: metrics_interval_seconds from config, or 0.5)",
    )
    scenarios_parser.add_argument(
        "--monitor",
        dest="monitor",
        action="store_true",
        default=None,
        help="Enable performance monitoring (overrides monitoring_enabled in config)",
    )
    scenarios_parser.add_argument(
        "--no-monitor",
        dest="monitor",
        action="store_false",
        help="Disable performance monitoring; no metrics files are written",
    )
    scenarios_parser.add_argument(
        "--reports-dir",
        type=str,
        help="Custom reports directory (default: {output_dir}/reports)",
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


def _raise_missing_ecmd(site: str, path: Path | None) -> NoReturn:
    raise ecmd.ECMDError(f"ECMD file not found for site {site}: {path}")


def _prepare_year_project(
    *,
    year: int,
    site_id: str,
    config: dict[str, Any],
    template_path: Path,
    ini_parameters: dict[str, int],
    dry_run: bool,
) -> Path:
    """
    Build the EddyPro project file for one year.

    Returns:
        Path to the generated ``.eddypro`` project file.

    Raises:
        Exception: Any failure to assemble the project, metadata, or inputs.
    """
    output_pattern = config["output_dir_pattern"]
    output_dir = Path(output_pattern.format(year=year, site_id=site_id))
    output_dir.mkdir(parents=True, exist_ok=True)

    project_file = output_dir / f"{site_id}.eddypro"

    ini_config = ini_tools.read_ini_template(template_path)
    if ini_parameters:
        validated_params = ini_tools.validate_parameters(ini_parameters)
        ini_tools.patch_ini_parameters(ini_config, validated_params)

    ecmd_file_pattern = config.get("ecmd_file", "")
    if "{site_id}" in ecmd_file_pattern:
        ecmd_file = Path(ecmd_file_pattern.format(site_id=site_id))
    else:
        ecmd_file = Path(ecmd_file_pattern)

    # Materialize metadata files early (idempotent)
    try:
        # Copy generic metadata template -> {site}.metadata
        # All sites use the same template; ECMD values populate it.
        metadata_template = Path("config") / "metadata_template.ini"

        if metadata_template.exists():
            shutil.copyfile(metadata_template, output_dir / f"{site_id}.metadata")
        else:
            logging.warning(
                f"No metadata template found for site {site_id}, "
                "skipping .metadata file generation"
            )

        # Generate dynamic metadata from ECMD CSV (all years included)
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

    if not ecmd_file.exists():
        _raise_missing_ecmd(site_id, ecmd_file)

    ecmd_row = ecmd.select_ecmd_row_for_year(
        ecmd_path=ecmd_file,
        site_id=site_id,
        year=year,
    )

    # Patch path fields; input path comes from the configured pattern
    input_pattern = config.get("input_dir_pattern", "")
    data_path_value = input_pattern.format(year=year, site_id=site_id)
    ini_tools.patch_ini_paths(
        ini_config,
        site_id=site_id,
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

    ini_tools.write_project_file_with_metadata(
        ini_config,
        project_file,
        metadata_path=output_dir / f"{site_id}.metadata",
        site_id=site_id,
        output_dir=output_dir,
        ecmd_row=ecmd_row,
    )

    logging.info(f"Created project file: {project_file}")

    # Preflight validation: check data_path and file availability
    if not dry_run:
        ini_tools.validate_eddypro_inputs(ini_config)
        ini_tools.validate_eddypro_metadata(ini_config)

    return project_file


def process_year(job: dict[str, Any]) -> dict[str, Any]:
    """
    Process a single year end to end.

    Defined at module level and taking a plain dict so that it can be dispatched
    to a :class:`~concurrent.futures.ProcessPoolExecutor` worker. Never raises:
    every failure is captured into the returned record so that one bad year does
    not abort the whole run and, crucially, remains visible in the run manifest.

    Returns:
        ``{year, status, duration_seconds, error, output_dir}`` where status is
        one of ``"success"``, ``"failed"``, or ``"dry_run"``.
    """
    year = job["year"]
    site_id = job["site_id"]
    config = job["config"]
    dry_run = job["dry_run"]

    # Worker processes start with a bare logging config; re-establish it so that
    # parallel years still write to the configured log file.
    if job.get("configure_logging"):
        setup_logging(
            job.get("log_level", "INFO"),
            config.get("log_file"),
            config.get("log_max_bytes"),
            config.get("log_backup_count"),
        )

    output_dir = Path(config["output_dir_pattern"].format(year=year, site_id=site_id))
    started = datetime.now(timezone.utc)
    record: dict[str, Any] = {
        "year": year,
        "status": "failed",
        "duration_seconds": 0.0,
        "error": None,
        "output_dir": str(output_dir),
    }

    logging.info(f"Processing year {year} for site {site_id}")

    try:
        project_file = _prepare_year_project(
            year=year,
            site_id=site_id,
            config=config,
            template_path=Path(job["template_path"]),
            ini_parameters=job["ini_parameters"],
            dry_run=dry_run,
        )
    except Exception as exc:
        logging.exception(f"Failed to prepare project file for year {year}")
        record["error"] = str(exc)
        record["duration_seconds"] = (
            datetime.now(timezone.utc) - started
        ).total_seconds()
        return record

    if dry_run:
        logging.info(f"Dry run: skipped EddyPro execution for year {year}")
        record["status"] = "dry_run"
        record["duration_seconds"] = (
            datetime.now(timezone.utc) - started
        ).total_seconds()
        return record

    try:
        success = core.run_eddypro_with_monitoring(
            project_file=project_file,
            eddypro_executable=Path(config["eddypro_executable"]),
            stream_output=job["stream_output"],
            metrics_interval=job["metrics_interval"],
            scenario_suffix="",
            log_output=job["log_eddypro_output"],
            monitoring_enabled=job["monitoring_enabled"],
        )
    except Exception as exc:
        logging.exception(f"EddyPro execution raised for year {year}")
        record["error"] = str(exc)
    else:
        if success:
            record["status"] = "success"
            logging.info(f"EddyPro processing completed successfully for year {year}")
        else:
            record["error"] = "EddyPro returned a non-zero exit status"
            logging.error(f"EddyPro processing failed for year {year}")

    record["duration_seconds"] = (datetime.now(timezone.utc) - started).total_seconds()
    return record


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
    start_time = datetime.now(timezone.utc)

    # Load configuration
    config_path = Path(args.config)
    processor = core.EddyProBatchProcessor(config_path)
    try:
        config = processor.load_config()
        processor.validate_config(config)
    except SystemExit:
        return 1

    setup_logging(
        getattr(args, "log_level", "INFO"),
        config.get("log_file"),
        config.get("log_max_bytes"),
        config.get("log_backup_count"),
    )

    # Collect INI parameter overrides
    ini_parameters = {}
    if args.rot_meth is not None:
        ini_parameters["rot_meth"] = args.rot_meth
    if args.tlag_meth is not None:
        ini_parameters["tlag_meth"] = args.tlag_meth
    if args.detrend_meth is not None:
        ini_parameters["detrend_meth"] = args.detrend_meth
    if args.despike_meth is not None:
        ini_parameters["despike_meth"] = args.despike_meth
    if getattr(args, "hf_meth", None) is not None:
        ini_parameters["hf_meth"] = args.hf_meth

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
    # `is not None` matters: the parser default used to be 0.5, which is truthy,
    # so metrics_interval_seconds from config.yaml was always silently overwritten.
    if getattr(args, "metrics_interval", None) is not None:
        config["metrics_interval_seconds"] = args.metrics_interval
    if getattr(args, "monitor", None) is not None:
        config["monitoring_enabled"] = args.monitor
    if getattr(args, "reports_dir", None):
        config["reports_dir"] = args.reports_dir
    if getattr(args, "report_charts", None):
        config["report_charts"] = args.report_charts

    # Extract key settings
    site_id = config["site_id"]
    years = config["years_to_process"]
    # The executable is read from config inside process_year so that the job dict
    # stays picklable for the ProcessPoolExecutor workers.
    stream_output = config.get("stream_output", True)
    log_eddypro_output = config.get("log_eddypro_output", True)
    metrics_interval = config.get("metrics_interval_seconds", 0.5)
    monitoring_enabled = config.get("monitoring_enabled", True)
    dry_run = args.dry_run
    config["dry_run"] = dry_run  # Store in config for manifest

    if not monitoring_enabled:
        logging.info(
            "Performance monitoring disabled; no metrics files will be written"
        )

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
    use_mp = bool(config.get("multiprocessing", False))
    max_processes = int(config.get("max_processes", 1) or 1)
    # Never spin up more workers than there is work, or than the machine has cores.
    worker_count = max(1, min(max_processes, len(years), os.cpu_count() or 1))
    parallel = use_mp and worker_count > 1 and len(years) > 1

    if use_mp and not parallel:
        logging.info(
            "Multiprocessing requested but only one worker is useful "
            f"({len(years)} year(s), max_processes={max_processes}); "
            "running sequentially"
        )

    # Interleaved stdout from several concurrent EddyPro processes is unreadable,
    # so streaming is suppressed when running in parallel. Output still reaches
    # the log file when log_eddypro_output is enabled.
    effective_stream_output = stream_output and not parallel
    if parallel and stream_output:
        logging.info(
            "Output streaming disabled while running years in parallel; "
            "EddyPro output is still captured in the log"
        )

    jobs = [
        {
            "year": year,
            "site_id": site_id,
            "config": config,
            "template_path": str(template_path),
            "ini_parameters": ini_parameters,
            "dry_run": dry_run,
            "stream_output": effective_stream_output,
            "metrics_interval": metrics_interval,
            "log_eddypro_output": log_eddypro_output,
            "monitoring_enabled": monitoring_enabled,
            "configure_logging": parallel,
            "log_level": getattr(args, "log_level", "INFO"),
        }
        for year in years
    ]

    year_records: list[dict[str, Any]] = []

    if parallel:
        logging.info(
            f"Processing {len(years)} years with {worker_count} parallel workers"
        )
        results_by_year: dict[int, dict[str, Any]] = {}
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = {executor.submit(process_year, job): job["year"] for job in jobs}
            for future in as_completed(futures):
                year = futures[future]
                try:
                    results_by_year[year] = future.result()
                except Exception as exc:
                    logging.exception(f"Worker for year {year} crashed")
                    results_by_year[year] = {
                        "year": year,
                        "status": "failed",
                        "duration_seconds": 0.0,
                        "error": f"worker crashed: {exc}",
                        "output_dir": str(
                            Path(
                                config["output_dir_pattern"].format(
                                    year=year, site_id=site_id
                                )
                            )
                        ),
                    }
        # Restore the requested order; completion order is nondeterministic.
        year_records = [results_by_year[year] for year in years]
    else:
        year_records = [process_year(job) for job in jobs]

    years_processed = [
        r["year"] for r in year_records if r["status"] in ("success", "dry_run")
    ]
    run_errors = [f"{r['year']}: {r['error']}" for r in year_records if r.get("error")]
    overall_success = all(r["status"] in ("success", "dry_run") for r in year_records)
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Generate reports. This runs unconditionally: a run in which every year
    # failed is exactly the run whose manifest matters most, and the old
    # `if years_processed:` guard meant no record was written at all.
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
            year_records=year_records,
            errors=run_errors,
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
    if args.despike_meth:
        parameter_options["despike_meth"] = args.despike_meth
    if args.hf_meth:
        parameter_options["hf_meth"] = args.hf_meth

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

    setup_logging(
        getattr(args, "log_level", "INFO"),
        config.get("log_file"),
        config.get("log_max_bytes"),
        config.get("log_backup_count"),
    )

    # Apply CLI overrides
    site_id = args.site if args.site else config.get("site_id")
    years = args.years if args.years else config.get("years_to_process", [])
    eddypro_exe = Path(config["eddypro_executable"])
    stream_output = config.get("stream_output", True)
    log_eddypro_output = config.get("log_eddypro_output", True)
    # Honour config.yaml; the CLI flag only wins when explicitly supplied.
    metrics_interval = (
        args.metrics_interval
        if args.metrics_interval is not None
        else config.get("metrics_interval_seconds", 0.5)
    )
    monitoring_enabled = (
        args.monitor
        if getattr(args, "monitor", None) is not None
        else config.get("monitoring_enabled", True)
    )
    if not monitoring_enabled:
        logging.info(
            "Performance monitoring disabled; no metrics files will be written"
        )

    if not site_id:
        logging.error("Site ID not provided via CLI or config")
        return 1

    if not years:
        logging.error("Years to process not provided via CLI or config")
        return 1

    # Process each year with all scenarios
    start_time = datetime.now(timezone.utc)
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
            log_output=log_eddypro_output,
            monitoring_enabled=monitoring_enabled,
        )

        # Collect results for reporting
        all_scenario_results.extend(scenario_results)

        # Log results
        successful = sum(1 for r in scenario_results if r["success"])
        failed = len(scenario_results) - successful
        logging.info(f"Year {year}: {successful} scenarios successful, {failed} failed")

    end_time = datetime.now(timezone.utc)
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

            # Stable SHA256; str(hash(...)) changed on every process.
            config_checksum = report.compute_config_checksum(config)

            # Build scenario list for manifest. "scenario_name" is included so
            # that `status` renders a name rather than "unknown".
            manifest_scenarios = []
            for result in all_scenario_results:
                suffix = result.get("scenario_suffix", "")
                manifest_scenarios.append(
                    {
                        "scenario_name": result.get(
                            "scenario_name", f"scenario{suffix}"
                        ),
                        "year": result.get("year"),
                        "scenario_index": result.get("scenario_index", 0),
                        "scenario_suffix": suffix,
                        "scenario_params": result.get("scenario_params", {}),
                        "start_time": result.get("start_time", start_time.isoformat()),
                        "end_time": result.get("end_time", end_time.isoformat()),
                        "duration_seconds": result.get("duration_seconds", 0),
                        "success": result.get("success", False),
                        "error": result.get("error"),
                        "output_dir": result.get("output_dir"),
                    }
                )

            # Analyse each scenario's metrics and emit a per-scenario HTML report.
            analyzer = analysis.BottleneckAnalyzer(config.get("performance_thresholds"))
            analyses = []
            scenario_metrics: dict[str, list[dict[str, Any]]] = {}
            for result in all_scenario_results:
                out_dir = result.get("output_dir")
                if not out_dir:
                    continue
                out_path = Path(out_dir)
                name = f"scenario{result.get('scenario_suffix', '')}"
                metrics_files = sorted(
                    out_path.glob("metrics_*.csv"),
                    key=lambda f: f.stat().st_mtime,
                )
                if not metrics_files:
                    continue
                scenario_analyses = [
                    analyzer.analyze(mf, scenario_name=f"{name}_{mf.stem}")
                    for mf in metrics_files
                ]
                analyses.extend(scenario_analyses)
                for mf in metrics_files:
                    scenario_metrics[f"{name}_{mf.stem}"] = (
                        report.load_metrics_from_csv(mf)
                    )

                # Per-scenario report, promised by docs but never generated
                # before: {output_dir}/reports/run_report.html
                try:
                    sc_reports_dir = out_path / "reports"
                    sc_reports_dir.mkdir(parents=True, exist_ok=True)
                    sc_manifest = dict(result)
                    sc_manifest.update(
                        {
                            "run_id": f"{run_id}_{name}",
                            "site_id": site_id,
                            "scenarios": [
                                s
                                for s in manifest_scenarios
                                if s["scenario_suffix"]
                                == result.get("scenario_suffix", "")
                            ],
                            "metrics_summary": {
                                "schema_version": 2,
                                "scenarios": [a.to_dict() for a in scenario_analyses],
                                "primary_bottleneck": (
                                    scenario_analyses[0].primary_bottleneck
                                    if scenario_analyses
                                    else "UNKNOWN"
                                ),
                            },
                        }
                    )
                    report.generate_html_report(
                        run_manifest=sc_manifest,
                        scenario_metrics={
                            f"{name}_{mf.stem}": scenario_metrics[f"{name}_{mf.stem}"]
                            for mf in metrics_files
                        },
                        chart_engine=config.get("report_charts", "plotly"),
                        output_path=sc_reports_dir / "run_report.html",
                    )
                except Exception as sc_err:
                    logging.warning(f"Failed to generate report for {name}: {sc_err}")

            metrics_summary = (
                {
                    "schema_version": 2,
                    "scenarios": [a.to_dict() for a in analyses],
                    "primary_bottleneck": analysis.dominant_bottleneck(analyses),
                }
                if analyses
                else None
            )

            overall_success = all(r["success"] for r in all_scenario_results)

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
                overall_success=overall_success,
                output_dirs=output_dirs,
                provenance=report.get_provenance(config),
                errors=[
                    f"{s['scenario_name']}: {s['error']}"
                    for s in manifest_scenarios
                    if s.get("error")
                ],
                status="completed" if overall_success else "failed",
                metrics_summary=metrics_summary,
            )

            # Write manifest
            manifest_path = reports_dir / "run_manifest.json"
            report.write_run_manifest(manifest, manifest_path)

            # Aggregate comparison report across all scenarios
            try:
                report.generate_html_report(
                    run_manifest=manifest,
                    scenario_metrics=scenario_metrics or None,
                    chart_engine=config.get("report_charts", "plotly"),
                    output_path=reports_dir / "run_report.html",
                )
            except Exception as agg_err:
                logging.warning(f"Failed to generate aggregate report: {agg_err}")

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

    setup_logging(
        getattr(args, "log_level", "INFO"),
        config.get("log_file"),
        config.get("log_max_bytes"),
        config.get("log_backup_count"),
    )

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
            setup_logging(
                getattr(args, "log_level", "INFO"),
                config.get("log_file"),
                config.get("log_max_bytes"),
                config.get("log_backup_count"),
            )
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
    print(f"Status: {manifest.get('status', 'unknown')}")

    # Per-year outcome, including years that failed. `years_processed` lists only
    # successes, so a failed year would otherwise be invisible in this output.
    year_records = manifest.get("years", [])
    if year_records:
        print("\n" + "-" * 70)
        print(f"{'Year':<8} {'Status':<12} {'Duration (s)':<15} {'Error'}")
        print("-" * 70)
        for rec in year_records:
            err = rec.get("error") or ""
            if len(err) > 30:
                err = err[:27] + "..."
            print(
                f"{rec.get('year', '?'):<8} {rec.get('status', '?'):<12} "
                f"{rec.get('duration_seconds', 0):<15.1f} {err}"
            )

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

    # Performance summary and bottleneck verdict
    metrics_summary = manifest.get("metrics_summary") or {}
    if metrics_summary:
        print("\n" + "-" * 70)
        print("Performance")
        print("-" * 70)
        print(f"Primary bottleneck: {metrics_summary.get('primary_bottleneck')}")
        for entry in metrics_summary.get("scenarios", []):
            cpu = entry.get("cpu", {})
            print(
                f"  {entry.get('scenario_name', '?'):<18} "
                f"{entry.get('primary_bottleneck', '?'):<18} "
                f"CPU p95 {cpu.get('p95', 0):>6.1f}%  "
                f"peak RAM {entry.get('peak_memory_mb', 0):>7.0f} MB  "
                f"read {entry.get('total_read_mb', 0):>7.0f} MB  "
                f"write {entry.get('total_write_mb', 0):>7.0f} MB"
            )
            if entry.get("explanation"):
                print(f"      {entry['explanation']}")

    # Output paths. The manifest key is "output_dirs"; reading "outputs" meant
    # this section never rendered.
    outputs = manifest.get("output_dirs", [])
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

    # With no subcommand there is nothing to configure, so help must print
    # rather than a config error. On a fresh clone config/config.yaml does not
    # exist yet, and a bare `eddypro-batch` is the first thing anyone runs.
    if not args.command:
        parser.print_help()
        return 1

    # Validate config file exists if provided
    if hasattr(args, "config") and args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            logging.error(f"Configuration file not found: {config_path}")
            return 1

    # Route to appropriate command handler. argparse restricts args.command to
    # these choices and the empty case returned above, so there is no fallback.
    handlers = {
        "run": cmd_run,
        "scenarios": cmd_scenarios,
        "validate": cmd_validate,
        "status": cmd_status,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
