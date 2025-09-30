"""EddyPro Batch Processor - Automated EddyPro processing with scenario support."""

__version__ = "0.1.0"
__author__ = "Rasmus Jensen"
__email__ = "raje@ecos.au.dk"

from .core import EddyProBatchProcessor, load_config, validate_config

__all__ = ["EddyProBatchProcessor", "load_config", "validate_config"]
