# Feature Specification: Batch CLI for EddyPro with Provenance, Profiling, Scenario Matrix & Offline Reports

**Feature Branch**: `001-batch-cli-for`  
**Created**: 2025-09-24  
**Status**: Draft  
**Input**: User description: "Batch CLI for EddyPro with provenance, profiling, LI-COR .ghg input, scenario matrix, and self-contained HTML reports ... (full text in request)"

## Execution Flow (main)

```text
1. Parse CLI subcommand & options
2. Validate config & raw input availability (and pairing for .ghg)
3. If dry-run → emit plan (years, scenarios, expected outputs) then EXIT success
4. For each year (range or single):
   a. Discover raw inputs & classify types (existing vs .ghg)
   b. If scenarios: expand matrix → ordered list of scenario specs
   c. For each run (baseline + scenarios):
      i.   Initialize logging & run-id
      ii.  Capture start timestamp (UTC)
      iii. (Optional) start profiler sampling loop
      iv.  Prepare temp workspace (isolated)
      v.   Invoke EddyPro with selected settings
      vi.  Post-process: summaries, QA counts
      vii. Stop profiler, assemble performance artifacts
      viii.Compute input file checksums & config digest
      ix.  Write provenance, summary.md, CSV artifacts, report.html
      x.   Cleanup temp space
5. Aggregate scenario_index & run_summary CSVs
6. Return consolidated exit code (non-zero if any failure)
```

---

## ⚡ Quick Guidelines

- ✅ Focus on WHAT users need (repeatable batch processing, profiling, comparability)
- ❌ Avoid HOW (specific libraries / implementation internals omitted)
- 👥 Audience includes data engineers, scientists, reviewers

### Section Requirements

- Mandatory sections completed below; optional ones included when relevant.

---

## Clarifications

### Session 2025-09-24

- Q: How should scenario executions be parallelized (scheduling architecture impact)? → A: Sequential (one after another, no concurrent scenario runs in initial release).
- Q: What is the acceptable profiling overhead budget? → A: Adaptive (target 2% overhead, never exceed 5%).
- Q: What is the minimum supported Python version? → A: 3.11 baseline (test 3.12 allowed).
- Q: Should failed scenarios be retried automatically? → A: No scenario-level retries (fail fast; rely on underlying transient file retry only).

Applied Changes:
 
- Added **FR-021** defining sequential scenario execution model.
- Removed related open question about scenario parallelism.
- Added assumption noting potential future enhancement to introduce controlled concurrency if needed.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

As a research data engineer, I need to batch process one or more years of eddy covariance raw data for a site (including LI-COR native `.ghg` datasets) using consistent, auditable parameters so that outputs, quality control metrics, and performance characteristics are reproducible, comparable, and reviewable offline.

### Secondary Stories

1. As a performance analyst, I want to profile CPU, RAM, and I/O phases under different storage backends (e.g., local SSD vs network share) to select optimal infrastructure.
2. As a flux scientist, I want to explore processing sensitivity using multiple scenario combinations (axis rotation, detrending, QC presets) for the same site-year without manual duplication.
3. As a reviewer/auditor, I want a concise `summary.md`, CSV summaries, and a single self-contained `report.html` per run/scenario to evaluate data quality offline.
4. As an operator, I want a dry-run that validates inputs and shows the execution plan with zero side effects before committing resources.

### Acceptance Scenarios

1. **Given** valid config & raw inputs for year 2021, **When** I run `run-year --year 2021 --site GL-ZaF`, **Then** output directories, provenance, summaries, logs, and report artifacts are produced under the expected structure.
2. **Given** same invocation with `--dry-run`, **When** executed, **Then** no output directories or files are created (except console/log validation) and exit code is success.
3. **Given** a range `2020–2021`, **When** I use `run-range --start-year 2020 --end-year 2021 --site GL-ZaF`, **Then** two independent year runs complete and a non-zero exit is returned if any year fails.
4. **Given** a scenario matrix file specifying rotations {double, planar-fit}, detrending {block, linear}, QC {VM97, MF}, **When** I run `run-scenarios`, **Then** each unique combination has its own scenario directory with metadata aggregated into `scenarios_index.csv`.
5. **Given** `.ghg` paired files with missing `.metadata`, **When** validation runs, **Then** the command fails fast with actionable error text including missing file names.
6. **Given** `--profile` and `--storage-tag local-ssd`, **When** a run completes, **Then** performance artifacts show time series snapshots and per-phase throughput; a later run with `--storage-tag network-share` yields different metrics for comparison.
7. **Given** a completed run/scenario, **When** I open `report.html` offline, **Then** I can interact with charts (phase timings, variable time series, QA flags) without network access.
8. **Given** identical inputs on Windows vs WSL/Linux, **When** I run the same command, **Then** directory layout and artifact naming match (aside from path separators) and contain no user-specific absolute paths.

### Edge Cases

- Zero discoverable raw inputs for selected year → fail fast with explicit guidance to check path/pattern.
- Duplicate scenario definitions (semantic collision) → deduplicate; warn unless forced.
- Prior partial run artifacts exist → skip identical work unless `--force` (future flag) [NEEDS CLARIFICATION: Is `--force` required in initial scope?].
- Extremely long nested paths on Windows → detect near limit and warn with suggestion to shorten base output path.
- Corrupt `.ghg` metadata file → fail with reference to offending line/field.

---

## Requirements *(mandatory)*

[...unchanged from original spec in feature branch...]
