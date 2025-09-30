"""
EddyPro Batch Processor Core Module.

Contains the core business logic refactored from the original eddypro_batch_processor.py
while preserving existing behavior and outputs.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


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

        logging.info("Configuration validation passed.")


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
