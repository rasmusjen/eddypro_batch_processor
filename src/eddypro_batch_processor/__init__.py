"""EddyPro Batch Processor.

A robust Python tool to automate and manage EddyPro processing tasks
across multiple years and sites with scenario support and performance monitoring.
"""

import sys
from pathlib import Path

__version__ = "0.1.0"

# Import the main function from the module file
try:
    # Add the src directory to path to import the main module
    src_dir = Path(__file__).parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Import from the module file (not package)
    import importlib.util

    module_path = src_dir / "eddypro_batch_processor.py"
    spec = importlib.util.spec_from_file_location(
        "eddypro_batch_processor_module", module_path
    )
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Export the process_year function
        process_year = module.process_year

except Exception as import_error:
    # Capture error message for use in fallback function
    error_msg = str(import_error)

    # Fallback - define a stub function that provides an error message
    def process_year(*args, **kwargs):
        raise ImportError(f"Could not import process_year function: {error_msg}")


__all__ = ["process_year"]
