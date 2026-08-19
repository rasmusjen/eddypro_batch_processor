# Known Issues, Gaps, and TODOs

This document captures current limitations, ambiguities, and roadmap items.
It is intended to keep docs aligned with the actual behavior in the codebase.

## Current Known Issues

### 1) Scenario (and run) execution depends on `eddypro_fcc`

- **What happens:** Both `run` and `scenarios` use
  `run_eddypro_with_monitoring()`, which copies the EddyPro binaries and runs
  both `eddypro_rp` and `eddypro_fcc`.
- **Failure mode:** If `eddypro_fcc` is missing from the same directory as
  `eddypro_executable`, or if `eddypro_fcc` cannot run on the host, processing
  fails for that year/scenario.
- **Impact:** Runs can error even when only the raw-processing step
  (`eddypro_rp`) would have succeeded.

### 2) Execution path parity (`run` vs `scenarios`)

- **`run`:** Copies EddyPro binaries to a local `bin/` folder and runs
  `eddypro_rp` then `eddypro_fcc` (same strategy as `scenarios`).
- **`scenarios`:** Runs `eddypro_rp` then `eddypro_fcc` from a copied `bin/`
  folder, once per scenario.
- **Status:** The two commands now use the same execution strategy, so this
  is no longer a source of divergent outputs/error modes. It remains listed
  here because the two commands still differ in other ways worth knowing:
  `run` parallelizes across years when `multiprocessing: true`; `scenarios`
  processes years sequentially and parallelizes scenarios within a year not
  at all (scenarios run one after another).

### 3) ~~Metrics schema mismatch with report chart loader~~ — FIXED

Performance monitoring now samples the whole EddyPro process tree (not the
`cmd.exe`/shell wrapper), and the report chart loader's expected fields
(`cpu_percent`, `memory_mb`, `read_mb`, `write_mb`) match what the monitor
writes. CPU, memory, and disk figures in `run_report.html` reflect actual
EddyPro resource usage, including derived disk rates and a
CPU/MEMORY/DISK_THROUGHPUT/DISK_IOPS bottleneck classification.

### 4) ~~Scenario reports are not generated~~ — FIXED

`scenarios` now generates a per-scenario HTML report at
`{output_dir}/{scenario_suffix}/reports/run_report.html`, plus one aggregate
comparison report and `run_manifest.json` under `reports_dir`.

### 5) ~~`status` output and scenario manifest schema mismatch~~ — FIXED

The run manifest's scenario entries and the `status` command's reader are now
aligned, so scenario names/suffixes display correctly instead of showing
"unknown".

### 6) ~~Multiprocessing flags are not wired~~ — FIXED

`multiprocessing` and `max_processes` are wired into `run`: years are
processed in parallel, one worker per year, up to `max_processes` concurrent
workers. Enable via config (`multiprocessing: true`) or CLI (`--mp
--max-proc N`). See [MULTI_YEAR_RUNS.md](MULTI_YEAR_RUNS.md).

### 7) CLI flag ambiguity

- The CLI accepts `--years` only (no `--year`).
- Using `--year` is invalid and should be corrected in any scripts or docs.

## Investigations / Suspected Root Causes

- **`eddypro_fcc` availability:** Both `run` and `scenarios` explicitly
  require it. If installations provide only `eddypro_rp`, processing will
  fail (see Issue 1).
- **Execution environment:** Both commands copy binaries to a local `bin/`
  folder; missing dependencies or licensing checks can fail after copy.

## TODO Checklist (High Priority)

- [ ] Decide how to handle `eddypro_fcc` missing on `run`/`scenarios` (fail
      fast vs. fallback to `eddypro_rp` only).
- [ ] Consider parallelizing `scenarios` across scenarios/years the same way
      `run` now parallelizes across years.

## See Also

- [MULTI_YEAR_RUNS.md](MULTI_YEAR_RUNS.md) – multi-year run behavior and caveats
- [SCENARIOS.md](SCENARIOS.md) – scenario run behavior and caveats
- [REPORTING.md](REPORTING.md) – manifest and report schema
