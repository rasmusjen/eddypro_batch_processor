"""EddyPro Batch Processor - Automated EddyPro processing with scenario support."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("eddypro-batch-processor")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0+unknown"

__author__ = "Rasmus Jensen"
__email__ = "raje@ecos.au.dk"

from .core import EddyProBatchProcessor, load_config, validate_config

__all__ = ["EddyProBatchProcessor", "__version__", "load_config", "validate_config"]
