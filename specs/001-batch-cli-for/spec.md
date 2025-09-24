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

### Functional Requirements

- **FR-001**: CLI MUST provide subcommands: `run-year`, `run-range`, `run-scenarios` with documented options (`--config`, `--input`, `--output`, `--dry-run`, `--log-level`, `--max-workers`, `--retry`, `--profile`, `--storage-tag`).
- **FR-002**: System MUST treat raw inputs as read-only (no rename, move, or modification).
- **FR-003**: System MUST validate presence and pairing of `.ghg` `.data` and `.metadata` files; missing partner triggers a blocking error listing missing paths.
- **FR-004**: System MUST compute deterministic `scenario_id` from canonicalized scenario settings (sorted keys, stable serialization).
- **FR-005**: Each scenario run MUST produce: `provenance.json`, `summary.md`, `run_summary.csv` (per scenario), `report.html`.
- **FR-006**: Year-level (non-scenario) run MUST produce baseline artifacts under `<output>/<site>/<year>/` mirroring EddyPro structure.
- **FR-007**: `--dry-run` MUST perform validation and planning without creating output artifacts or modifying filesystem (aside from logs if unavoidable). Logs MUST clearly state DRY-RUN MODE.
- **FR-008**: `--profile` MUST result in `perf_profile.json` (time series) and `perf_summary.csv` (per-phase aggregates) with CPU%, RSS memory, disk bytes read/written, wall times.
- **FR-009**: System MUST log structured fields (timestamp, level, site, year, run-id, optional scenario_id) in both console and file logs.
- **FR-010**: Provenance MUST include: invoked command, normalized args, config digest (hash), list of input files with checksums, start/end timestamps, duration seconds, OS/platform info, tool versions (EddyPro, Python), storage tag, scenario settings (if applicable).
- **FR-011**: System MUST generate `scenarios_index.csv` summarizing scenario metrics: `scenario_id,rotation,detrending,qc_preset,n_ok,n_warn,n_err,duration_s,throughput_mb_s`.
- **FR-012**: HTML report MUST be a single file, embedding required JS/CSS/assets (no CDN) and including interactive visualizations.
- **FR-013**: Directory layout MUST be consistent cross-platform; no absolute host-specific prefixes appear in stored artifacts.
- **FR-014**: `run-range` MUST return non-zero exit code if any single year fails; partial successes MUST be reflected in logs.
- **FR-015**: System MUST support configurable retry count (`--retry`) for transient failures (e.g., intermittent file access) with exponential backoff [NEEDS CLARIFICATION: Are target transient error classes predefined?].
- **FR-016**: All timestamps MUST be stored in explicit timezone or UTC (recommended UTC) and clearly labeled.
- **FR-017**: Summary CSV / Markdown MUST surface error counts and highlight warnings distinctly.
- **FR-018**: Scenario execution MUST isolate temp directories per scenario to avoid cross-contamination.
- **FR-019**: System MUST produce deterministic artifact names from identical inputs & parameters.
- **FR-020**: CLI help (`--help`) MUST enumerate options with concise explanations.
- **FR-021**: Scenario executions MUST run sequentially within a given year run (no concurrent scenario processing in initial release); only year-level commands may leverage external concurrency (future enhancement may revisit).
- **FR-022**: Provenance checksum algorithm MUST be configurable via `--hash-alg` (allowed: `blake3`, `sha256`); default = `blake3`. All listed input files MUST include the selected algorithm name and hex digest. Switching algorithm with identical inputs MUST only change the checksum-related fields.
- **FR-023**: Profiling subsystem MUST target ≤2% added wall-clock overhead and MUST dynamically throttle sampling (e.g., extend interval) to ensure measured overhead never exceeds 5%. Actual measured overhead percentage MUST be recorded in `perf_summary.csv` and provenance.
- **FR-024**: Tooling MUST require Python ≥3.11; CI MUST test against 3.11 (required) and MAY additionally test 3.12. Features relying on 3.11-specific improvements (e.g., exception groups, pattern matching refinements) are permitted; code MUST remain compatible with 3.11.
- **FR-025**: Scenario-level failures MUST NOT be auto-retried; a failed scenario terminates with an error status recorded in `scenarios_index.csv`. Only lower-level transient file operations may use the generic `--retry` mechanism.

*Ambiguities to clarify (retain until resolved):*

- **FR-A01**: Supported rotation modes complete list? Provided examples; confirm if additional modes exist.
- **FR-A02**: QC preset taxonomy (`VM97`, `MF`) completeness; need other presets?
- **FR-A03**: Should `--force` be included in initial release for re-run overrides?
- **FR-A04**: Threshold for snapshot interval (1s vs 2s) fixed or configurable?
- **FR-A05**: Maximum matrix size guardrails (e.g., limit combinations or require confirmation) required?

### Key Entities

- **Run**: A single site-year (optionally scenario) execution with parameters, timing, outputs, provenance.
- **Scenario**: A named parameter combination overlaying a base run; generates distinct output namespace.
- **Provenance Record**: Structured immutable JSON capturing configuration, inputs, environment, results summary.
- **Performance Snapshot**: Time-stamped measurements of system resource usage and phase markers.
- **HTML Report**: Offline bundling of metadata, summaries, charts, and QA indicators.
- **Scenario Index**: Aggregated CSV of all scenario outcomes for a site-year.

---

## Review & Acceptance Checklist

GATE: To be satisfied before implementation plan approval.

### Content Quality

- [ ] No implementation details (libraries, frameworks) leaked in this spec
- [ ] Focused on user value and repeatability
- [ ] Written accessibly for mixed technical/non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness

- [ ] All [NEEDS CLARIFICATION] items resolved or explicitly deferred
- [ ] Requirements testable & unambiguous
- [ ] Success metrics measurable (artifact presence, exit codes, report generation)
- [ ] Scope boundaries defined (no algorithmic changes inside EddyPro)
- [ ] Dependencies & assumptions enumerated (EddyPro installed, read-only raw data location)

---

## Execution Status

Initialized for specify step; will be updated in later workflow phases.

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed (pending clarifications)

---

## Assumptions & Constraints (Derived)

- EddyPro CLI/tooling available and version stable across runs.
- Profiling subsystem enforces adaptive budget: aim 2% overhead, hard cap 5% (FR-023); if prediction exceeds cap, sampling interval increases or high-frequency metrics skipped.
- Python baseline is 3.11 (FR-024); optional 3.12 testing permitted but not required for readiness.
- No scenario-level retry policy (FR-025); operators re-run explicitly if needed.
- Default checksum algorithm is BLAKE3 (performance + cryptographic strength) with optional SHA256 for strict compliance use cases (FR-022); provenance records MUST record algorithm used.
- Scenario matrix provided via JSON or YAML file; format includes top-level keys mapping to lists of allowed values.
- Maximum concurrency limited by I/O saturation; user-tunable via `--max-workers`.
- Scenario-level execution is deliberately sequential (FR-021) to simplify resource profiling accuracy and avoid I/O contention; future versions may add parallel scenarios behind a flag.

## Non-Goals (Explicit)

- Altering EddyPro’s internal scientific computations.
- Providing a multi-user web dashboard or persistent database.
- Real-time streaming visualizations beyond logs.
- Cloud deployment orchestration.

## Success Metrics

- 100% of acceptance criteria A1–A8 demonstrably pass with automated or semi-automated tests.
- Report file opens offline (no network requests in dev tools) for sample run.
- Re-running identical command yields byte-identical provenance except for timestamp fields.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Large scenario matrices cause long runtime | Delays | Provide early matrix size summary & optional confirm flag. |
| Profiling overhead skews performance data | Misinterpretation | Lightweight sampling interval; allow disable; document overhead. |
| Platform path inconsistencies | Non-reproducible layouts | Normalize internal path handling & prefer relative paths in artifacts. |
| Missing `.ghg` metadata formats variations | False negatives | Implement flexible validation rules & targeted error messaging. |
| User confusion over scenario_id derivation | Difficulty reproducing | Document canonicalization process and include settings echo in provenance. |

## Open Questions

1. Scenario execution parallelism decision: RESOLVED → Sequential (FR-021), no built-in parallel scenario scheduling initial release.
2. Are there storage I/O metrics beyond bytes read/written (latency, queue depth) required? [NEEDS CLARIFICATION]
3. Checksum algorithm mandate: RESOLVED → Configurable (`blake3` default, optional `sha256`) (FR-022).
4. Profiling overhead threshold: RESOLVED → Adaptive target 2%, cap 5% (FR-023).

## High-Level Validation Matrix (Mapping FR → Acceptance Criteria)

| FR | Acceptance Link |
|----|-----------------|
| FR-001 | A1, A3 |
| FR-003 | A5 |
| FR-004 | A6 |
| FR-005 | A2, A6, A7 |
| FR-008 | A4 |
| FR-010 | A1, A6, A7 |
| FR-011 | A6 |
| FR-012 | A7 |
| FR-014 | A3 |

---

## Definition of Ready (for Planning Phase)

- Ambiguities enumerated; pending clarifications do not block initial architecture outline.
- Functional scope bounded (no algorithmic internals of EddyPro).
- Core artifact list stabilized (provenance, perf, report, summaries, scenario index).
- Cross-platform and determinism commitments stated.

---

End of specification.
