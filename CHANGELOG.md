# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Milestone 7: Validation Command and Documentation** - Complete validation system and comprehensive user documentation
  - New `validation.py` module with comprehensive validation functions:
    - `validate_config_structure()` - checks required keys and types
    - `validate_config_sanity()` - performs sanity checks on values
    - `validate_paths()` - verifies path existence and pattern validity
    - `validate_ecmd_schema()` - validates ECMD CSV columns and structure
    - `validate_ecmd_sanity()` - checks ECMD data values (positive frequencies, non-negative heights, etc.)
    - `validate_all()` - aggregates all validations with categorized results
    - `format_validation_report()` - generates human-readable validation reports
  - Functional `cmd_validate` CLI command with exit codes (0=pass, 1=fail)
  - Options to skip path validation (`--skip-paths`) or ECMD validation (`--skip-ecmd`)
  - Comprehensive test suite with 25 tests achieving 73% coverage on validation module
  - Complete user documentation:
    - **USAGE.md** - CLI usage guide with examples for all commands
    - **CONFIG.md** - Configuration reference with all YAML options and ECMD format
    - **SCENARIOS.md** - Scenario matrix documentation with naming conventions and limits
    - **REPORTING.md** - Report structure, metrics interpretation, and provenance
    - **DEVELOPMENT.md** - Contributing guidelines, testing, code standards, pre-commit workflow
  - Updated README.md with concise overview, quickstart, and links to detailed docs

### Changed

- CLI `validate` command now fully functional with comprehensive checks
- README slimmed down to focus on overview and quickstart
- Documentation reorganized into dedicated topic-specific files

### Technical

- All validation functions have proper type hints and docstrings
- All code passes black, ruff formatting checks
- Tests are deterministic with mocked file I/O and temp files
- Validation errors provide actionable guidance with clear messages
- Exit codes properly signal validation success/failure

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

## [0.1.0] - 2024-10-01

### Features

- Initial project structure
- Configuration management (YAML)
- CLI skeleton with subcommands (run, scenarios, validate, status)
- INI tools for EddyPro parameter patching
- Performance monitoring with psutil
- HTML and JSON reporting with Plotly charts
- Pre-commit hooks and CI workflow
