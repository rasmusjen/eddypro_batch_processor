# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Milestone 6: Scenario Runner** - Comprehensive scenario generation and execution system
  - New `scenarios.py` module with Cartesian product generation
  - Deterministic scenario naming with suffixes (e.g., `_rot1_tlag2_det0_spk1`)
  - Hard cap of 32 scenarios with clear error messaging when exceeded
  - `Scenario` dataclass for immutable scenario representation
  - `cmd_scenarios` CLI command for running parameter matrices
  - Scenario execution functions in `core.py` (`run_single_scenario`, `run_scenario_batch`)
  - Per-scenario manifest generation with execution metadata
  - Comprehensive test suite with 25 tests achieving 100% coverage on scenarios module
  - Support for CLI parameter specification: `--rot-meth`, `--tlag-meth`, `--detrend-meth`, `--despike-vm`
  - Scenario summary formatting for user feedback

### Changed

- CLI `scenarios` subcommand now fully functional with scenario generation and execution
- Report module updated to support consolidated scenario manifests
- Core execution functions now support scenario-specific output directories and file naming

### Technical

- All code passes black, ruff, and type checking
- Deterministic scenario generation ensures reproducible results
- Frozen dataclasses enforce immutability for scenario parameters
- Comprehensive input validation with actionable error messages

## [0.1.0] - 2024-10-01

### Features

- Initial project structure
- Configuration management (YAML)
- CLI skeleton with subcommands (run, scenarios, validate, status)
- INI tools for EddyPro parameter patching
- Performance monitoring with psutil
- HTML and JSON reporting with Plotly charts
- Pre-commit hooks and CI workflow
