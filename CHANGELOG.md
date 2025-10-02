# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### ⚠️ BREAKING CHANGES

- **Minimum Python version increased to 3.10**
  - Python 3.8 and 3.9 are no longer supported (Python 3.8 reached EOL in October 2024)
  - Added Python 3.13 support
  - CI now tests on Python 3.10, 3.11, 3.12, and 3.13

### Changed

- Updated minimum Python requirement from 3.8 to 3.10
- Updated all tool configurations (black, ruff, mypy) to target Python 3.10
- Updated documentation to reflect Python 3.10+ requirement

### Migration Guide

Users on Python 3.8 or 3.9 should:

1. **Upgrade Python** to 3.10 or higher:
   ```bash
   # Using conda/mamba
   conda install python=3.10  # or 3.11, 3.12, 3.13

   # Or download from python.org
   # https://www.python.org/downloads/
   ```

2. **Reinstall package**:
   ```bash
   pip install --upgrade eddypro-batch-processor
   ```

3. **Test your workflows**:
   ```bash
   eddypro-batch --version
   eddypro-batch validate --config config/config.yaml
   ```

**Note**: Version 0.2.x will continue to support Python 3.8+ for critical security fixes only.

## [0.2.0] - 2025-10-02

### Added

- **Milestone 9: CLI Implementation** - Complete CLI pipeline functionality
  - Implemented full `cmd_run()` function for end-to-end processing pipeline
    - Configuration loading and validation with CLI overrides
    - INI parameter validation and project file generation
    - Dry-run mode support for testing without EddyPro execution
    - Comprehensive error handling and logging at each stage
    - Report and manifest generation after processing
  - Implemented full `cmd_scenarios()` function for Cartesian product scenario execution
    - Multi-parameter scenario generation (rot_meth × tlag_meth × detrend_meth × despike_vm)
    - Scenario cap enforcement (32 combinations limit)
    - Custom manifest generation with actual scenario results
    - Individual scenario tracking with success/failure status
    - Parallel batch processing with configurable workers
  - Implemented full `cmd_status()` function for run status reporting
    - Manifest reading from reports directory
    - Formatted output with run summary and scenario table
    - Support for custom reports directory override
  - Enhanced `generate_run_manifest()` in report.py
    - Added start_time, end_time, config_snapshot, dry_run fields
    - Support for both single runs and scenario matrices
  - All CLI functions use defensive attribute access with getattr() for robustness
  - Integration tests now passing without xfail markers (10/10 tests pass)
  - Unit tests updated to provide complete config fixtures and manifest files
  - Coverage maintained at 71.79% (above 70% minimum floor)

- **Milestone 8: End-to-End Integration Tests** - Comprehensive dry-run integration testing
  - New `test_e2e_integration.py` module with full pipeline integration tests
  - End-to-end tests for dry-run mode verifying:
    - Single and multiple scenario execution
    - Project file (.eddypro) generation with parameter overrides
    - Reports directory creation and manifest generation
    - Scenario cap enforcement (32 combinations limit)
    - HTML report generation with proper content
    - CLI command help and validation workflows
  - Integration tests exercise full pipeline: CLI → config → INI → scenarios → reporting
  - All tests use mocked EddyPro executables and temporary directories for isolation
  - Tests validate manifest structure, scenario naming, and output artifacts
  - 13 comprehensive integration tests covering all major user workflows
  - All tests deterministic with no external dependencies or network calls

### Changed

- Integration tests use subprocess.run with check=False for proper error handling
- Test fixtures provide complete mock environment (config, ECMD, templates, executables)

### Technical

- All integration tests pass black, ruff, mypy checks
- Tests verify CLI exit codes and error messages
- Proper cleanup with pytest fixtures and temporary paths
- Tests document expected behavior for dry-run mode
- Full coverage of CLI subcommands: run, scenarios, validate, status

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
