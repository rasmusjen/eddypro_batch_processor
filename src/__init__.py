# src/__init__.py

"""
EddyPro Batch Processor Package

This package provides functionality to automate and manage EddyPro processing tasks.
"""

from .eddypro_batch_processor import (
    load_config,
    validate_config,
    setup_logging,
    get_raw_files,
    build_project_file,
    run_subprocess,
    run_eddypro,
    process_year,
    main
)

__all__ = [
    "load_config",
    "validate_config",
    "setup_logging",
    "get_raw_files",
    "build_project_file",
    "run_subprocess",
    "run_eddypro",
    "process_year",
    "main"
]