# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Investigation doc on EddyPro execution path differences between `run` and `scenarios`.

- **Static .metadata population from ECMD**
  - Selects the ECMD row closest to but not later than the processing year
  - Populates site, timing, and instrument fields plus station identifiers
  - Validates missing ECMD values and fails with actionable errors

- **High-frequency spectral correction method parameter (`--hf-meth`)**
  - New CLI parameter for controlling EddyPro's high-frequency spectral correction method
  - Valid values: 1 (Moncrieff et al. 1997 analytic) or 4 (Fratini et al. 2012 in situ/analytic, default in template)
  - Available in both `run` and `scenarios` commands
  - Extends scenario matrix from 16 to 32 possible combinations (2×2×2×2×2)
  - Parameter written to `[Project]` section as `hf_meth` in generated INI files
  - Full test coverage and documentation updates

- **Conditional date/time range population for EddyPro project files**
  - Automatically populates date/time ranges when using Planar Fit (rot_meth=3) or time-lag optimization (tlag_meth=4)
  - When `rot_meth=3` (Planar Fit): sets `pf_start_date`, `pf_end_date`, `pf_start_time`, `pf_end_time` to full-year ranges
  - When `tlag_meth=4` (Covariance maximization with time-lag optimization): sets `to_start_date`, `to_end_date`, `to_start_time`, `to_end_time` to full-year ranges

### Changed

- **Project file naming uses site ID only**
  - `.eddypro` files are now named `{site_id}.eddypro` (no year or scenario suffix)
  - The `Project.file_name` field is aligned to the same `{site_id}.eddypro` pattern

- **Run execution now mirrors scenarios (rp → fcc via local bin copy)**
  - `run` uses the same local `bin/` copy and working-directory strategy as `scenarios`
  - `eddypro_fcc` runs only after `eddypro_rp` succeeds

- **BREAKING: Renamed CLI parameter from `--despike-vm` to `--despike-meth`**
  - Renamed for consistency with other parameter naming (rot_meth, tlag_meth, detrend_meth)
  - Python parameter name changed from `despike_vm` to `despike_meth` throughout codebase
  - INI file key remains `despike_vm` for compatibility with EddyPro
  - CLI usage: `eddypro-batch run --despike-meth 0` (previously `--despike-vm 0`)
  - Scenarios: `eddypro-batch scenarios --despike-meth 0 1` (previously `--despike-vm 0 1`)
  - Date ranges are automatically set to January 1 - December 31 for the processing year
  - Ensures EddyPro has sufficient data for planar fit calculations and time-lag optimization
  - New function `patch_conditional_date_ranges` in `ini_tools.py` with comprehensive test coverage

- **Known issues and TODO tracking document**
  - Added [docs/KNOWN_ISSUES_AND_TODO.md](docs/KNOWN_ISSUES_AND_TODO.md)
  - Documents current pipeline limitations and planned work

- **Machine-readable output file tracking in run manifests**
  - Run manifests now include `output_files` field with absolute paths to all EddyPro output CSV files
  - Tracks four file types: fluxnet, full_output, metadata, and qc_details
  - Enables automated post-processing and validation workflows
  - Files grouped by output directory with sorted absolute paths

- **EddyPro project file population adjustments**
  - `file_name` now points to `{output_dir}/{site_id}.eddypro`
  - `proj_file` now points to `{output_dir}/{site_id}.metadata`
  - `project_title` and `project_id` now set to `site_id` only
  - `sa_bin_spectra` and `sa_full_spectra` now point to
    `{output_dir}/eddypro_binned_cospectra` and `{output_dir}/eddypro_full_cospectra`
  - INI writer now trims trailing empty lines

- **Documentation alignment**
  - Updated README and core docs to match current CLI behavior, outputs, and schemas

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
    - Multi-parameter scenario generation (rot_meth × tlag_meth × detrend_meth × despike_meth)
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
  - Support for CLI parameter specification: `--rot-meth`, `--tlag-meth`, `--detrend-meth`, `--despike-meth`
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
