# Known Issues, Gaps, and TODOs

This document captures current limitations, ambiguities, and roadmap items.
It is intended to keep docs aligned with the actual behavior in the codebase.

## Current Known Issues

### 1) Scenario runs depend on `eddypro_fcc`

- **What happens:** Scenario execution uses `run_eddypro_with_monitoring()` which
  copies the EddyPro binaries and runs both `eddypro_rp` and `eddypro_fcc`.
- **Failure mode:** If `eddypro_fcc` is missing from the same directory as
  `eddypro_executable`, or if `eddypro_fcc` cannot run on the host, scenarios fail.
- **Impact:** Scenario runs can error even when a regular `run` succeeds.
- **Notes:** This is likely the source of the “pipeline still cannot run everything
  without errors” observation. It is consistent with failures seen when
  `eddypro_fcc` is absent or not executable.

### 2) Execution path mismatch (`run` vs `scenarios`)

- **`run`:** Executes the configured `eddypro_executable` directly.
- **`scenarios`:** Runs `eddypro_rp` then `eddypro_fcc` from a copied `bin/` folder.
- **Impact:** Outputs and error modes can diverge between `run` and `scenarios`.
  This is a deliberate design today but should be documented as a limitation.

### 3) Metrics schema mismatch with report chart loader

- **Observed:** The monitor writes raw metrics with fields like
  `system_cpu_percent` and `process_memory_rss`.
- **Report loader expects:** `cpu_percent`, `memory_mb`, `read_mb`, `write_mb`.
- **Impact:** HTML charts can be empty or missing lines even when metrics exist.

### 4) Scenario reports are not generated

- **Current behavior:** `scenarios` writes only `run_manifest.json`.
- **Expected by docs:** Per-scenario HTML reports and an aggregate report.
- **Impact:** Users do not get HTML reports for scenario runs today.

### 5) `status` output and scenario manifest schema mismatch

- **`status` prints:** `scenario_name` from the run manifest.
- **`scenarios` manifest entries:** `scenario_index` + `scenario_suffix` without
  `scenario_name`.
- **Impact:** Status output can show “unknown” for scenario name entries.

### 6) Multiprocessing flags are not wired

- `multiprocessing` and `max_processes` are validated but not applied in execution.
- Runs are currently sequential regardless of these settings.

### 7) CLI flag ambiguity

- The CLI accepts `--years` only (no `--year`).
- Using `--year` is invalid and should be corrected in any scripts or docs.

## Investigations / Suspected Root Causes

- **`eddypro_fcc` availability:** Scenario runner explicitly requires it. If
  installations provide only `eddypro_rp`, scenario runs will fail.
- **Execution environment:** Scenario runs copy binaries to a local `bin/` folder;
  missing dependencies or licensing checks can fail after copy.

## Roadmap Items (Planned, Not Implemented Yet)

### Monitoring Toggle

See [MONITORING_TOGGLE_IMPLEMENTATION_PLAN.md](plan/MONITORING_TOGGLE_IMPLEMENTATION_PLAN.md).

Planned:
- Config `monitoring_enabled: true|false` (default `true`).
- CLI flags `--monitor` / `--no-monitor` for `run` and `scenarios`.
- Skip metrics files and monitor creation when disabled.
- Validation: only enforce positive `metrics_interval_seconds` if enabled.

### Performance Analysis & Reporting Enhancements

See [PERFORMANCE_ANALYSIS_DESIGN.md](plan/PERFORMANCE_ANALYSIS_DESIGN.md).

Planned:
- New `analysis.py` with `BottleneckAnalyzer` and `ScenarioAnalysis` models.
- Traffic-light executive summary (CPU/RAM/Disk bottleneck classification).
- Plotly subplots for CPU, memory, and disk I/O with thresholds.
- Per-scenario HTML reports and aggregated comparison matrix.
- Unified baseline scenario model for `run` so analysis is consistent.

## TODO Checklist (High Priority)

- [ ] Decide how to handle `eddypro_fcc` missing on scenario runs (fail fast vs.
      fallback to `eddypro_rp` only).
- [ ] Align metrics schema between monitor outputs and report chart loader.
- [ ] Add HTML report generation for `scenarios` or document as intentionally
      unsupported.
- [ ] Wire `multiprocessing` and `max_processes` or mark as deprecated.
- [ ] Add `monitoring_enabled` config + CLI flags as per plan.
- [ ] Implement performance analysis module and integrate with reporting.
