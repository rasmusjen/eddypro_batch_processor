# EddyPro Batch Processor – Improvement Plan

This plan proposes concrete, staged improvements to evolve the current script into a robust, testable CLI tool with scenario runs, performance monitoring, and reporting. It is written to be immediately actionable in this repository.

## Objectives

- Provide a first-class CLI with arguments and subcommands.
- Parameterize and programmatically control key EddyPro INI settings and support scenario matrices.
- Add a performance monitor module (CPU, memory, disk/network IO) to analyze bottlenecks.
- Produce run reports in both HTML and machine-readable formats.
- Improve repo hygiene, testing, CI, and documentation.
- Suggest additional enhancements that add value with low risk.


## Guardrails

- The following template/config files are read-only and MUST NOT be modified without explicit user approval:
  - `config/EddyProProject_template.ini`
  - `config/GL-ZaF_metadata_template.ini`
  - `config/GL-ZaF_dynamic_metadata.ini`

- Current working baseline: `src/eddypro_batch_processor.py` is functioning well and serves as the starting point. All refactors must preserve existing behavior/output unless explicitly agreed.

---

## 1) CLI Design

Introduce a dedicated CLI entry point with subcommands. Keep `src/eddypro_batch_processor.py` as library functions and add a thin CLI wrapper.

- Package layout
  - `src/eddypro_batch_processor/__init__.py`
  - `src/eddypro_batch_processor/cli.py` – arg parsing + orchestration
  - `src/eddypro_batch_processor/core.py` – refactor reusable logic from current script
  - `src/eddypro_batch_processor/ini_tools.py` – INI templating and parameter patching
  - `src/eddypro_batch_processor/monitor.py` – performance metrics
  - `src/eddypro_batch_processor/report.py` – HTML + JSON reporting

- Commands (examples)
  - `run` – process site/years according to config and/or overrides
    - Options: `--config`, `--site`, `--years 2021 2022`, `--input-dir-pattern`, `--output-dir-pattern`,
      `--eddypro-exe`, `--stream-output`, `--mp`, `--max-proc`, `--dry-run`, `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`
    - Scenario overrides: `--rot-meth`, `--tlag-meth`, `--detrend-meth`, `--despike-meth`
  - `scenarios` – enumerate and run Cartesian product of supplied INI parameter values
    - Options: `--rot-meth 1 3`, `--tlag-meth 2 4`, `--detrend-meth 0 1`, `--despike-meth 0 1`, `--year 2021`, `--site GL-ZaF`
  - `validate` – validate config and environment (required keys, path existence, ECMD CSV schema + minimal sanity checks)
  - `status` – summarize last run results from provenance/manifest

- Distribution
  - Local-only: use `pyproject.toml` for packaging and expose `eddypro-batch` console script.
  - Installation for developers via editable mode: `pip install -e .`.
  - No publishing to public or private registries is planned.

Acceptance criteria

- `eddypro-batch run --config config/config.yaml` runs current flow (backward compatible).
- Overrides on the CLI persist to the generated `.eddypro` project files.

Multiprocessing defaults and behavior

- No automatic default process count. When `--mp` (or `multiprocessing: true`) is enabled, the user must explicitly set `--max-proc` (CLI) or `max_processes` (config). If omitted, the run errors with guidance to set a value.

Validation scope (default)

- Config: structure and required keys present
- Environment: path existence for EddyPro executable, input/output directories, and ECMD file
- ECMD schema: required columns present, including (at minimum):
  - DATE_OF_VARIATION_EF, FILE_DURATION, ACQUISITION_FREQUENCY, CANOPY_HEIGHT
  - SA_MANUFACTURER, SA_MODEL, SA_HEIGHT, SA_WIND_DATA_FORMAT, SA_NORTH_ALIGNEMENT, SA_NORTH_OFFSET
  - GA_MANUFACTURER, GA_MODEL, GA_NORTHWARD_SEPARATION, GA_EASTWARD_SEPARATION, GA_VERTICAL_SEPARATION (if available)
  - If `GA_PATH` == "closed": GA_TUBE_LENGTH, GA_TUBE_DIAMETER, GA_FLOWRATE
- Minimal sanity checks: non-empty `years_to_process`, non-empty `site_id`, positive `ACQUISITION_FREQUENCY`, and positive `FILE_DURATION`
- Exit behavior: non-zero exit code on failure with actionable messages

---

## 2) INI Parameterization & Scenario Runner

Implement a focused INI manipulation module to programmatically set specific parameters in `EddyProProject_template.ini` before creating the per-year project file.

- Parameters to expose
  - Rotation: `rot_meth` in `[RawProcess_Settings]` → 1=DR (double rotation), 3=PF (planar fit)
  - Time lag compensation: `tlag_meth` in `[RawProcess_Settings]` → 2=CMD, 4=AO
  - Detrend: `detrend_meth` in `[RawProcess_Settings]` → 0=BA, 1=LD
  - Spike removal: `despike_meth` in `[RawProcess_ParameterSettings]` → 0=VM97, 1=M13
  - High-frequency correction: `hf_meth` in `[Project]` → 1=Moncrieff et al. (1997) analytic, 4=Fratini et al. (2012) in situ/analytic

- Design
  - Read template via `configparser`, then patch only the keys that were provided (leave others intact).
  - Ensure type-safety and validation with friendly messages.
  - Validation policy
    - Allowed values: `rot_meth` ∈ {1, 3}; `tlag_meth` ∈ {2, 4}; `detrend_meth` ∈ {0, 1}; `despike_meth` ∈ {0, 1}; `hf_meth` ∈ {1, 4}.
    - If a CLI override is outside the allowed set, error and abort the run (non-zero exit). No coercion or skipping.

- Scenario engine
  - Input: mappings of parameter → list of values.
  - Build Cartesian product of combinations (small cap to avoid explosion e.g., `--max-scenarios`).
  - For each scenario: write a unique project file name suffix (e.g., `_rot1_tlag2_det0_spk0_hf4`) and run.
  - Store scenario metadata (params + run metadata + result paths + metrics) in a manifest JSON.
  - Limits: Hard cap of 32 combinations; if exceeded, the run errors out and instructs the user to narrow parameters.

Acceptance criteria

- User can run one year with all requested combinations and find outputs in deterministically named folders/files.
- Manifest provides machine-readable linkage between scenario → outputs.

---

## 3) Performance Monitoring Module

Add a small module built on `psutil` (cross-platform) to track:

- CPU utilization (process and system), memory (RSS/peak), and wall-clock.
- Disk I/O and per-disk throughput; optionally network I/O if input/output are remote shares.
- Periodic sampling during EddyPro subprocesses and aggregation after run.

Implementation notes

- Start a background thread/process before launching `eddypro_rp`/`eddypro_fcc`.
- Default sampling interval: 0.5s; configurable via CLI flag `--metrics-interval` and config key `metrics_interval_seconds`.
- Capture `read_bytes`, `write_bytes`, CPU%, mem at each sample.
- On completion, compute min/avg/max, percentiles, and totals.
- Emit both time series (CSV) and summary (JSON) per run/scenario.

Acceptance criteria

- Metrics are captured for each scenario and included in the final report.

Dependencies

- Add `psutil` to `requirements.txt` (and guard imports where not installed).

Defaults and options

- `metrics_interval_seconds`: default 0.5
- CLI: `--metrics-interval <float>` to override per run

---

## 4) Reporting (HTML + JSON)

Create a reporting module that produces human-friendly and machine-readable outputs and stores them in a consistent location.

### Artifacts generated

- `run_manifest.json` – run-level summary including scenarios, timings, metrics, output links, exit codes
- `run_report.html` – HTML report with tables and charts summarizing runs and scenarios
- Per-scenario artifacts within the reports directory:
  - `manifest.json` – scenario parameters, project file path, output folder, timestamps, success/failure, metrics summary
  - `metrics.csv` – sampled performance time series
  - Optional: small PNG/HTML plots (CPU, IO over time)

### Report contents (default)

- Summary with run status and aggregated timings
- Scenario matrix/table with per-scenario timings
- Performance charts (CPU, memory, IO) and per-scenario metrics table
- Environment and provenance: Python version, package versions, EddyPro version, config snapshot, and checksums of key inputs/templates

### Output locations

- Default: inside the year’s output directory, under `reports/`
  - Base path: `{output_dir_pattern}/reports` (e.g., `.../{site_id}/{year}/.../reports`)
  - Files: `run_manifest.json`, `run_report.html`, and per-scenario artifacts (e.g., suffix `_rot1_tlag2_det0_spk0`)
  - Overrides: `--reports-dir` CLI flag or `reports_dir` config key

### Chart engine defaults and fallbacks

- Default chart engine: Plotly (interactive). Select via `--report-charts {plotly,svg,none}` (default: `plotly`).
- If Plotly is not installed, automatically fall back to `svg` (or `none` if SVG generation is unavailable) with a warning.

---

## 5) Repository Hygiene & Best Practices

- Packaging
  - Adopt `pyproject.toml` with project metadata and console script entry point. Local-only distribution; no registry publishing.
  - Package name: `eddypro-batch-processor` (or keep current).
- Dependencies
  - Maintain `requirements.txt`; pin minimal versions; include `psutil` and `plotly` as defaults.
  - Optional: `jinja2` for templated HTML; if omitted, produce HTML with minimal inline templates.
  - Document fallbacks: if Plotly missing, report generation downgrades charts to SVG or none with a warning.
- Code quality
  - Add `ruff` or `flake8` + `black` config; ensure consistent formatting and linting.
  - Type hints where practical; enable `mypy` (optional, gradual).
- Testing
  - Expand `tests/` with unit tests for: INI patching, scenario cartesian product, manifest writer, and monitor sampling.
  - Add a small, fake run harness that skips actual EddyPro binaries (mock subprocess) to validate flow.
- CI
  - GitHub Actions workflow: lint + tests on push/PR.
- Logging
  - Keep rotating logs; add per-run log file in the output folder alongside manifest.
  - Console default level: INFO. Override via CLI `--log-level` or config key `log_level`.
- Structure
  - Move top-level script logic into `src/eddypro_batch_processor/core.py` and call from CLI.

---

## 6) Documentation

- Keep README concise, focusing on overview, quickstart, and configuration pointers.
- Create user docs in `docs/`:
  - `USAGE.md` – CLI usage with examples.
  - `SCENARIOS.md` – parameter matrix runs, naming conventions, output structure.
  - `CONFIG.md` – all YAML options and environment validation.
  - `REPORTING.md` – where to find reports and how to interpret them.
  - `DEVELOPMENT.md` – contributing, testing, coding standards.

---

## 7) Suggested Enhancements

- Provenance capture: keep inputs checksum and software versions (EddyPro version, script version, Python) in manifest.
- Retry/Resume: mark completed years/scenarios and resume skipped ones safely.
- Dry-run mode: generate all per-scenario `.eddypro` files and planned commands without executing.
- Caching: if a scenario’s inputs and parameters haven’t changed, allow skipping.
- Parallelism control per scenario vs per year; scheduling that respects IO bottlenecks.
- Pluggable exporters: export a compact CSV summary across all scenarios for downstream analysis.
- Telemetry toggle: metric collection can be disabled to minimize overhead.

---

## 8) Professional Linting, Style, Testing, and Guardrails

Establish consistent code quality practices, enforceable locally and in CI, to keep the project reliable and maintainable.

- Linters and Formatters
  - `ruff` for fast linting (aggregates many Flake8 plugins). Baseline rules: E, F, W, I, N, UP, B, SIM, TRY.
  - `black` for opinionated formatting; target Python 3.12 (align with your environment).
  - `isort` (optional) for import sorting; or rely on Ruff’s import rules.
  - `.editorconfig` to unify whitespace, line endings, and indent across editors.

- Type Checking
  - `mypy` in incremental mode for new/critical modules (`ini_tools.py`, `monitor.py`, `report.py`).
  - Gradual typing in legacy modules with explicit `# type: ignore` where needed.

- Testing
  - `pytest` as the runner; `pytest-cov` for coverage. Start with a 70% floor and improve over time.
  - Mock external dependencies (EddyPro binaries, filesystem/network) to keep tests fast and deterministic.
  - CLI smoke tests for `run`, `scenarios`, `validate` using tmp dirs and `capsys`.
  - Optional: `hypothesis` for property-based tests of INI patching and scenario generation.

- Security/Guardrails
  - `bandit` to scan for common Python security issues.
  - Validate and sanitize CLI inputs (paths exist, allowed ranges, bounded combinations).
  - Prefer `subprocess.run([...], shell=False)` where possible; sanitize/quote when `shell=True` is necessary.
  - Resource ceilings (`--max-scenarios`, `--max-proc`) to prevent runaway loads.

- Pre-commit Hooks
  - Use `pre-commit` to run ruff, black, isort, mypy (fast), bandit, and whitespace fixes on commit.
  - Provide setup instructions and enforce in CI for consistency.

- CI Integration (GitHub Actions)
  - Jobs: lint, type-check, test (with cache for pip) on PRs and main.
  - Upload coverage artifact; optional badge for README.

- Configuration Files to Add
  - `pyproject.toml` – tool configs (black, ruff, mypy, isort) + packaging/entry points.
  - `.pre-commit-config.yaml` – hooks and versions.
  - `.editorconfig` – whitespace and encoding norms.
  - `.github/workflows/ci.yml` – lint + test workflow.

Acceptance criteria

- Local `pre-commit` passes on staged changes.
- CI enforces lint, type-check, and unit tests on PRs and main.
- Subprocess and input handling pass basic security checks (Bandit baseline clean).

---

## Milestones – Execution Plan (Actionable & Testable)

Milestone 1: Repo scaffolding and quality guardrails

- Tasks
  - [x] Add `pyproject.toml` with package metadata and console entry `eddypro-batch`
  - [x] Add `.editorconfig`, `ruff` + `black` config (via pyproject), `.pre-commit-config.yaml`
  - [x] Add CI workflow `.github/workflows/ci.yml` (lint, type-check, tests)
- Deliverables
  - [x] Files above committed; pre-commit enabled; CI workflow present
- Definition of Done
  - [x] Local pre-commit runs pass on a sample change
  - [x] CI pipeline passes on a branch with no code changes

Milestone 2: CLI skeleton and package structure

- Tasks
  - [x] Create package layout: `src/eddypro_batch_processor/{__init__.py,cli.py,core.py}`
  - [x] Implement `cli.py` with subcommands: `run`, `scenarios`, `validate`, `status` (stubs acceptable)
  - [x] Wire `--log-level`, `--config` and ensure help/usage is clear
- Deliverables
  - [x] `eddypro-batch --help` shows subcommands and options
- Definition of Done
  - [x] Unit test: invoking CLI with `--help` returns zero and prints usage

Milestone 3: INI parameterization utilities

- Tasks
  - [x] Implement `ini_tools.py` to patch: `rot_meth`, `tlag_meth`, `detrend_meth`, `despike_meth`
  - [x] Enforce validation policy (allowed sets; abort on invalid)
  - [x] Integrate overrides into `run` command flow
- Deliverables
  - [x] Unit tests covering valid/invalid overrides and correct INI patching
- Definition of Done
  - [x] Tests pass; patched `.eddypro` files contain expected values

Milestone 4: Performance monitoring module

- Tasks
  - [x] Implement `monitor.py` sampling every 0.5s (configurable) using `psutil`
  - [x] Record CPU%, RSS, IO read/write bytes; write `metrics.csv` and a summary JSON
  - [x] Start/stop monitor around EddyPro subprocess execution
- Deliverables
  - [x] Unit tests with a fake workload verify sampling and output files
- Definition of Done
  - [x] Metrics artifacts created and hold plausible values in a local test

Milestone 5: Reporting (manifest + HTML)

- Tasks
  - [x] Generate `run_manifest.json` capturing run/scenario metadata, metrics summary, outputs
  - [x] Generate `run_report.html` with Plotly charts by default; add `--report-charts` flag and fallbacks
  - [x] Store in `{output_dir_pattern}/reports` by default; support overrides
- Deliverables
  - [x] Unit tests assert presence and minimal schema of manifest; smoke test HTML generation
- Definition of Done
  - [x] Report renders locally; manifest links scenarios to outputs

Milestone 6: Scenario runner

- Tasks
  - [x] Implement Cartesian product executor with deterministic suffixes and a hard cap of 32
  - [x] Add `--max-scenarios` guard and clear error if exceeded
  - [x] Update manifest and reports to include all scenarios
- Deliverables
  - [x] Unit tests: naming, cap enforcement, per-scenario artifact creation (mocked runs)
- Definition of Done
  - [x] Scenario runs produce isolated outputs and consolidated report/manifest

Milestone 7: Validate command and documentation

- Tasks
  - [x] Implement `validate` scope: config keys, paths, ECMD schema and sanity checks; non-zero exit on failure
  - [x] Create docs skeleton: `USAGE.md`, `SCENARIOS.md`, `CONFIG.md`, `REPORTING.md`, `DEVELOPMENT.md`
  - [x] Slim README; link to docs
- Deliverables
  - [x] Unit tests for `validate` with good/bad fixtures; docs committed
- Definition of Done
  - [x] `eddypro-batch validate --config ...` returns zero on valid, non-zero on invalid

Milestone 8: End-to-end dry-run (integration)

- Tasks
  - [x] Add an integration test that runs `run` in dry-run mode (mock EddyPro) to exercise full pipeline
  - [x] Verify outputs: reports directory, manifest, and (mock) scenario files
- Deliverables
  - [x] Integration test script/pytest; mock fixtures for EddyPro and file system
- Definition of Done
  - [x] Integration test passes locally and in CI

Milestone 9: CLI Implementation – Complete Full Pipeline

- Tasks
  - [x] Implement `cmd_run()` in `cli.py` to orchestrate the full processing pipeline
    - [x] Parse CLI arguments and merge with config file settings
    - [x] Initialize logging and monitoring (if enabled)
    - [x] Generate project files using `ini_tools.py` with parameter overrides
    - [x] Execute EddyPro processing (respect `--dry-run` flag)
    - [x] Capture metrics and write manifest/reports
    - [x] Handle errors gracefully with proper exit codes
  - [x] Implement `cmd_scenarios()` in `cli.py` for scenario matrix execution
    - [x] Generate Cartesian product of parameter combinations
    - [x] Validate scenario cap (≤32 combinations)
    - [x] Execute each scenario with deterministic naming (suffixes)
    - [x] Aggregate results into consolidated manifest and report
  - [x] Implement `cmd_status()` in `cli.py` to read and display last run manifest
    - [x] Parse and pretty-print manifest JSON
    - [x] Show run summary, scenario table, and key metrics
    - [x] Handle missing/corrupt manifest files gracefully
  - [x] Remove `@pytest.mark.xfail` decorators from integration tests
  - [x] Update integration tests to verify actual outputs (not just CLI invocation)
  - [x] Add error handling tests for edge cases (missing files, invalid params, etc.)
- Deliverables
  - [x] Fully implemented `cmd_run()`, `cmd_scenarios()`, and `cmd_status()` functions
  - [x] All 10 integration tests pass without xfail markers
  - [x] Error scenarios tested (invalid config, missing files, exceeded cap)
  - [x] Updated documentation with real-world usage examples
- Definition of Done
  - [x] `eddypro-batch run --config ... --dry-run` executes full pipeline and generates reports
  - [x] `eddypro-batch scenarios --rot-meth 1 3 --tlag-meth 2 4 --dry-run` creates 4 scenarios with proper naming
  - [x] `eddypro-batch status` displays last run summary from manifest
  - [x] All integration tests pass (153 passed, 0 xfailed, coverage ≥70%)
  - [x] CI pipeline passes on all Python versions (3.8-3.12)
  - [x] Code quality checks pass (ruff, black, mypy, bandit)

Note: Milestone order is optimized for testability and incremental value; each milestone should leave the repo in a usable state.

---

## Acceptance Checklist

- [ ] CLI command `eddypro-batch run --config ...` works end-to-end
- [ ] The four INI settings can be overridden via CLI and scenario matrices
- [ ] Metrics exist per run and aggregate into the manifest and HTML report
- [ ] README remains concise; extended docs under `docs/` are published
- [ ] Lint/tests/CI pass locally and in GitHub Actions

---

## Conventions and Defaults (Quick Reference)

- Charts: default Plotly; `--report-charts {plotly,svg,none}`
- Scenario cap: 32 combinations (hard error if exceeded)
- Metrics interval: 0.5s default; `--metrics-interval <float>`
- Packaging: local-only via `pyproject.toml`; `pip install -e .`
- INI overrides: invalid values error and abort
- Reports location: `{output_dir_pattern}/reports`; override with `--reports-dir`/`reports_dir`
- Multiprocessing: must set `--max-proc`/`max_processes` when enabled; no auto default
- Validate: keys + paths + ECMD schema/sanity by default
- Console log level: INFO by default; `--log-level` to override
