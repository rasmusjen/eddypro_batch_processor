#!/usr/bin/env python3
"""
EddyPro Batch Processor CLI.

Command-line interface for automated EddyPro processing with scenario support
and performance monitoring.
"""

import argparse
import logging
import sys
from pathlib import Path

from . import ini_tools


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
  eddypro-batch run --config config/config.yaml
  eddypro-batch scenarios --site GL-ZaF --years 2021 2022
  eddypro-batch validate --config config/config.yaml
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


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the run command."""
    logging.info("Starting EddyPro batch processing run...")

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
            # Use error instead of exception to avoid stack trace for user input errors
            logging.error(f"Invalid INI parameter: {e}")  # noqa: TRY400
            return 1

    # TODO: Implement run logic using EddyProBatchProcessor
    logging.info("Run command - stub implementation")
    logging.info(f"Config: {args.config}")
    if args.site:
        logging.info(f"Site override: {args.site}")
    if args.years:
        logging.info(f"Years override: {args.years}")
    if args.dry_run:
        logging.info("Dry run mode enabled")

    return 0


def cmd_scenarios(args: argparse.Namespace) -> int:
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

    # Validate each parameter value in the options
    if parameter_options:
        try:
            for param_name, values in parameter_options.items():
                for value in values:
                    ini_tools.validate_parameter(param_name, value)
            logging.info(f"Parameter options for scenarios: {parameter_options}")
        except ini_tools.INIParameterError as e:
            # Use error instead of exception to avoid stack trace for user input errors
            logging.error(f"Invalid scenario parameter: {e}")  # noqa: TRY400
            return 1

    # TODO: Calculate Cartesian product and check scenario limit
    # TODO: Implement scenario logic
    logging.info("Scenarios command - stub implementation")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute the validate command."""
    logging.info("Validating configuration and environment...")

    # TODO: Implement validation logic
    logging.info("Validate command - stub implementation")
    logging.info(f"Config: {args.config}")
    if args.skip_paths:
        logging.info("Skipping path existence checks")
    if args.skip_ecmd:
        logging.info("Skipping ECMD file validation")

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Execute the status command."""
    logging.info("Checking last run status...")

    # TODO: Implement status logic
    logging.info("Status command - stub implementation")
    if args.reports_dir:
        logging.info(f"Reports directory: {args.reports_dir}")

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
