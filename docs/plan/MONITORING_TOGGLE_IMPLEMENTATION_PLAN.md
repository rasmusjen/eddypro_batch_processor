# Monitoring Toggle Implementation Plan

## Goal
Add a way to disable performance monitoring via CLI and config while keeping current defaults unchanged.

## Summary of Proposed Behavior
- **Config**: Add `monitoring_enabled: true|false` (default `true`).
- **CLI**: Add `--monitor` and `--no-monitor` flags to `run` and `scenarios`.
- **Metrics interval**: If monitoring is disabled, skip creation of monitors and metrics files even if `metrics_interval_seconds` is set.
- **Validation**: Only enforce positive `metrics_interval_seconds` when monitoring is enabled.

## Scope of Changes

### 1) CLI wiring
Update argument parsing and overrides in:
- [src/eddypro_batch_processor/cli.py](src/eddypro_batch_processor/cli.py)

Tasks:
- Add `--monitor` / `--no-monitor` flags to `run` command.
- Add `--monitor` / `--no-monitor` flags to `scenarios` command.
- Apply flags to config overrides (e.g., `config["monitoring_enabled"] = True/False`).
- Pass `monitoring_enabled` into calls that run monitoring.

### 2) Config schema and validation
Update validation rules in:
- [src/eddypro_batch_processor/validation.py](src/eddypro_batch_processor/validation.py)

Tasks:
- Include `monitoring_enabled` in required keys (or treat as optional with default).
- Enforce `metrics_interval_seconds > 0` **only if** monitoring is enabled.
- Add validation for `monitoring_enabled` type (bool).

### 3) Core execution path
Update monitoring entry points in:
- [src/eddypro_batch_processor/core.py](src/eddypro_batch_processor/core.py)
- [src/eddypro_batch_processor/monitor.py](src/eddypro_batch_processor/monitor.py)

Tasks:
- Add `monitoring_enabled: bool` parameter to `run_subprocess_with_monitoring()`.
- If disabled, bypass `MonitoredOperation` and run subprocess without monitoring.
- Ensure metrics files are not created in disabled mode.
- Propagate `monitoring_enabled` to any other monitoring usages (e.g., in scenario runs).

### 4) Tests
Update or add tests in:
- [tests/test_cli.py](tests/test_cli.py)
- [tests/test_cli_functions.py](tests/test_cli_functions.py)
- [tests/test_e2e_integration.py](tests/test_e2e_integration.py)
- [tests/test_validation.py](tests/test_validation.py)
- [tests/test_monitor.py](tests/test_monitor.py)

Test cases:
- CLI flags set/clear `monitoring_enabled`.
- Validation allows `metrics_interval_seconds <= 0` when monitoring disabled.
- Monitoring disabled produces **no metrics files** in dry-run and scenario runs.
- Monitoring enabled behavior unchanged.

### 5) Documentation updates
Update:
- [README.md](README.md)
- [docs/USAGE.md](docs/USAGE.md)
- [docs/CONFIG.md](docs/CONFIG.md)
- [docs/REPORTING.md](docs/REPORTING.md)
- [CHANGELOG.md](CHANGELOG.md)

Docs tasks:
- Add config option `monitoring_enabled` with default and description.
- Add CLI flags to usage tables and examples.
- Note that disabling monitoring stops metrics CSV/JSON and report performance charts.

## Detailed Implementation Steps

1) **Add config key**
- In [docs/CONFIG.md](docs/CONFIG.md), document:
  - `monitoring_enabled: true` (default).
  - If `false`, no metrics collected; `metrics_interval_seconds` ignored.

2) **CLI additions**
- In [src/eddypro_batch_processor/cli.py](src/eddypro_batch_processor/cli.py):
  - Add flags:
    - `--monitor` (enable monitoring)
    - `--no-monitor` (disable monitoring)
  - In config overrides, set `config["monitoring_enabled"]` accordingly.

3) **Validation rules**
- In [src/eddypro_batch_processor/validation.py](src/eddypro_batch_processor/validation.py):
  - Validate `monitoring_enabled` is bool.
  - If `monitoring_enabled` is `False`, skip positive check for `metrics_interval_seconds`.

4) **Core runtime logic**
- In [src/eddypro_batch_processor/core.py](src/eddypro_batch_processor/core.py):
  - Add parameter `monitoring_enabled: bool` to `run_subprocess_with_monitoring`.
  - If disabled, run subprocess without `MonitoredOperation`.
  - Ensure no metrics files emitted.
- Ensure calls from `cmd_run()` and `cmd_scenarios()` pass the correct flag.

5) **Tests**
- Add test cases for CLI and validation.
- Add integration tests that ensure no metrics files are created when monitoring is disabled.

6) **Docs + changelog**
- Update CLI usage examples with `--no-monitor`.
- Mention effect on reports/metrics in [docs/REPORTING.md](docs/REPORTING.md).
- Add entry to [CHANGELOG.md](CHANGELOG.md) under `[Unreleased]`.

## Acceptance Criteria
- `eddypro-batch run --no-monitor` runs without creating metrics files.
- `eddypro-batch scenarios --no-monitor` runs without metrics files.
- Validation passes with `monitoring_enabled: false` and `metrics_interval_seconds: 0`.
- Default behavior unchanged (monitoring enabled, metrics collected).
- Docs reflect new config and CLI options.
- Tests updated and passing.

## Risks / Notes
- Ensure backward compatibility for configs that don’t include `monitoring_enabled`.
- Avoid changing metrics filenames or report output when monitoring is enabled.
