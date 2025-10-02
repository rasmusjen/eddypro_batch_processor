#!/usr/bin/env python3
"""
Scenario Generation for EddyPro Batch Processor.

Utilities for generating Cartesian products of INI parameter combinations
and creating deterministic scenario identifiers.
"""

import itertools
import logging
from dataclasses import dataclass

from . import ini_tools

logger = logging.getLogger(__name__)

# Hard cap on scenario combinations
MAX_SCENARIOS = 32


class ScenarioLimitExceededError(Exception):
    """Exception raised when scenario count exceeds maximum allowed."""

    pass


@dataclass(frozen=True)
class Scenario:
    """
    Represents a single scenario with parameter values.

    Attributes:
        parameters: Dictionary of parameter name -> value pairs
        suffix: Deterministic suffix for naming files/directories
        index: Scenario number (1-based)
    """

    parameters: dict[str, int]
    suffix: str
    index: int

    def __post_init__(self) -> None:
        """Validate scenario after initialization."""
        if not self.parameters:
            raise ValueError("Scenario must have at least one parameter")
        if not self.suffix:
            raise ValueError("Scenario suffix cannot be empty")
        if self.index < 1:
            raise ValueError("Scenario index must be positive")


def generate_scenario_suffix(parameters: dict[str, int]) -> str:
    """
    Generate a deterministic suffix for a scenario based on its parameters.

    The suffix format is: _rot{X}_tlag{Y}_det{Z}_spk{W}
    Only parameters present in the dictionary are included.

    Args:
        parameters: Dictionary of parameter name -> value pairs

    Returns:
        A deterministic suffix string (e.g., "_rot1_tlag2_det0_spk1")

    Examples:
        >>> generate_scenario_suffix({"rot_meth": 1, "tlag_meth": 2})
        '_rot1_tlag2'
        >>> generate_scenario_suffix({"rot_meth": 3, "despike_vm": 0})
        '_rot3_spk0'
    """
    if not parameters:
        return ""

    # Define canonical ordering and abbreviations
    param_order = ["rot_meth", "tlag_meth", "detrend_meth", "despike_vm"]
    param_abbrev = {
        "rot_meth": "rot",
        "tlag_meth": "tlag",
        "detrend_meth": "det",
        "despike_vm": "spk",
    }

    suffix_parts = []
    for param_name in param_order:
        if param_name in parameters:
            abbrev = param_abbrev[param_name]
            value = parameters[param_name]
            suffix_parts.append(f"{abbrev}{value}")

    suffix = "_" + "_".join(suffix_parts) if suffix_parts else ""
    logger.debug(f"Generated suffix '{suffix}' for parameters {parameters}")
    return suffix


def generate_scenarios(
    parameter_options: dict[str, list[int]],
    max_scenarios: int = MAX_SCENARIOS,
) -> list[Scenario]:
    """
    Generate all scenario combinations from parameter options.

    Creates a Cartesian product of all parameter value lists and validates
    that the total count does not exceed the maximum.

    Args:
        parameter_options: Dictionary mapping parameter names to lists of values
        max_scenarios: Maximum number of scenarios allowed (default: 32)

    Returns:
        List of Scenario objects with deterministic suffixes and indices

    Raises:
        ScenarioLimitExceededError: If the number of combinations exceeds max_scenarios
        ValueError: If parameter_options is empty or contains empty lists

    Examples:
        >>> opts = {"rot_meth": [1, 3], "tlag_meth": [2]}
        >>> scenarios = generate_scenarios(opts)
        >>> len(scenarios)
        2
        >>> scenarios[0].suffix
        '_rot1_tlag2'
    """
    if not parameter_options:
        raise ValueError("Parameter options cannot be empty")

    # Validate that all options lists are non-empty
    for param_name, values in parameter_options.items():
        if not values:
            raise ValueError(
                f"Parameter '{param_name}' has no values. "
                "Remove it or provide at least one value."
            )

    # Calculate total combinations
    param_names = sorted(parameter_options.keys())  # Consistent ordering
    param_value_lists = [parameter_options[name] for name in param_names]
    total_combinations = 1
    for values in param_value_lists:
        total_combinations *= len(values)

    logger.info(
        f"Generating scenarios: {total_combinations} combinations from "
        f"{len(parameter_options)} parameters"
    )

    # Check against cap
    if total_combinations > max_scenarios:
        param_counts = {
            name: len(parameter_options[name]) for name in parameter_options
        }
        raise ScenarioLimitExceededError(
            f"Scenario count ({total_combinations}) exceeds maximum ({max_scenarios}). "
            f"Current parameter value counts: {param_counts}. "
            f"Please reduce the number of values for some parameters."
        )

    # Generate Cartesian product
    scenarios = []
    for index, combination in enumerate(itertools.product(*param_value_lists), start=1):
        # Build parameter dictionary for this combination
        parameters = dict(zip(param_names, combination, strict=False))

        # Generate deterministic suffix
        suffix = generate_scenario_suffix(parameters)

        # Create scenario object
        scenario = Scenario(
            parameters=parameters,
            suffix=suffix,
            index=index,
        )
        scenarios.append(scenario)

        logger.debug(f"Scenario {index}/{total_combinations}: {parameters} -> {suffix}")

    logger.info(f"Generated {len(scenarios)} scenarios successfully")
    return scenarios


def format_scenario_summary(scenarios: list[Scenario]) -> str:
    """
    Format a human-readable summary of scenarios.

    Args:
        scenarios: List of Scenario objects

    Returns:
        Formatted string summarizing all scenarios

    Examples:
        >>> scenarios = generate_scenarios({"rot_meth": [1, 3]})
        >>> summary = format_scenario_summary(scenarios)
        >>> "Scenario 1" in summary
        True
    """
    if not scenarios:
        return "No scenarios generated."

    lines = [f"Generated {len(scenarios)} scenario(s):"]
    lines.append("")

    for scenario in scenarios:
        param_str = ", ".join(
            f"{k}={v}" for k, v in sorted(scenario.parameters.items())
        )
        lines.append(f"  Scenario {scenario.index}: {param_str}")
        lines.append(f"    Suffix: {scenario.suffix}")

    return "\n".join(lines)


def validate_scenario_parameters(
    parameter_options: dict[str, list[int]],
) -> dict[str, list[int]]:
    """
    Validate parameter options before scenario generation.

    Ensures all parameter names are recognized and all values are valid.
    This should be called after individual parameter validation.

    Args:
        parameter_options: Dictionary mapping parameter names to lists of values

    Returns:
        The validated parameter options (unchanged if valid)

    Raises:
        ValueError: If any parameter name is unrecognized

    Note:
        Individual parameter values should be validated using
        ini_tools.validate_parameter() before calling this function.
    """
    recognized_params = set(ini_tools.PARAMETER_VALIDATION.keys())

    for param_name in parameter_options:
        if param_name not in recognized_params:
            raise ValueError(
                f"Unrecognized parameter '{param_name}'. "
                f"Valid parameters: {sorted(recognized_params)}"
            )

    logger.debug(f"Validated scenario parameter options: {parameter_options}")
    return parameter_options
