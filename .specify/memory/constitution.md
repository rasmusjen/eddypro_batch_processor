# eddypro_batch_processor Constitution
<!--
Sync Impact Report
Version change: 1.0.0 → 1.1.0
Modified principles: Added new Principle 5 (Incremental Evolution & Safe Refactoring); previous Principles 5-7 renumbered
Added sections: Incremental Evolution & Safe Refactoring
Removed sections: None
Templates requiring updates:
  - .specify/templates/plan-template.md (needs bottom reference bump to v1.1.0)
  - .specify/templates/spec-template.md (no direct version string – no change)
  - .specify/templates/tasks-template.md (no direct version string – no change)
Follow-up TODOs: Add docs/refactoring.md with characterization workflow (future minor)
-->

## Core Principles

### 1. Scientific Integrity & Mission Focus

All functionality MUST support the mission: reproducible batch processing of
EddyPro outputs (CO₂/CH₄/H₂O) across years and sites. Code MUST NOT change
scientific result semantics unless an accepted specification explicitly
requests it AND tests demonstrate equivalence or justified improvement. Raw
eddy-covariance data are immutable inputs: treat as read-only. Any
transformation MUST be fully reconstructible from committed code + versioned
configuration.

### 2. Reproducibility & Data Handling Discipline

Processing MUST be deterministic given (code version, config, input set,
EddyPro version). Never edit raw files in place; write derived artifacts to
dedicated output directories. Timezone usage MUST be explicit—no silent
timestamp shifts; store and log timezone context with outputs. File paths MUST
remain portable: no user-specific absolute paths, drive letters, or OS‑specific
separators hard‑coded; use pathlib abstractions. Every run MUST capture
provenance (input file list + hashes, EddyPro version, config revision) in
machine-readable metadata co-located with outputs.

### 3. Interface, CLI & Observability

Expose functionality via a Python 3.11+ CLI (Typer preferred; argparse
acceptable if justified) with clear subcommands (run-year, run-range, validate,
summarize, etc.). Every subcommand MUST support: --dry-run, --config, --input
(or --site / --year as applicable), --output, --log-level, and --debug (enables
stack traces). Default logging: structured human-readable lines to console AND
a rotating file under logs/[YEAR]/ with timestamps + level. No stack traces
unless --debug. All external process calls (EddyPro invocations) MUST log
command, duration, exit code. Prefer JSON or CSV outputs that downstream
tooling can parse deterministically.

### 4. Quality Gates: Types, Style, Tests

Type hints REQUIRED (no unqualified Any unless a code comment justifies). Lint
with Ruff; format with Black; enforce Ruff import ordering. Docstrings follow
NumPy style for public functions, classes, and modules. All new code MUST have
pytest coverage; overall line coverage MUST remain ≥ 80%. Each bug fix MUST add
a regression test reproducing the failure first. Test isolation: use temporary
directories; no network access in unit or integration tests. Fixture data that
impacts logic SHOULD be checksum pinned to detect accidental drift. CI MUST
block merge on lint, format, type check (mypy or pyright acceptable), tests,
and minimum coverage threshold.

### 5. Incremental Evolution & Safe Refactoring

Change MUST be delivered as the smallest coherent, reviewable unit that leaves
the system in a healthy, shippable state. Large "rewrite" or "big bang"
refactors are PROHIBITED unless explicitly specified and approved in a feature
spec with measurable risk mitigation.

Refactoring Safety Rules:

1. Characterize BEFORE altering behavior: capture baseline via existing tests
   plus (when touching performance‑sensitive paths) a lightweight timing sample
   over representative data. Commit characterization notes (or link) in PR
   description.
2. Tests FIRST for any behavior you intend to rely on but which is untested.
   Write characterization tests that would fail if semantics drift.
3. Single‑axis change: each PR SHOULD focus on one concern (naming cleanup,
   module extraction, interface tightening, performance micro‑opt, etc.).
4. Preserve public CLI and file/metadata contract stability unless the spec
   mandates a versioned change AND migration notes exist.
5. Feature flags (simple Boolean or env guard) MAY be used for incremental
   delivery of complex behavior shifts; flags MUST default to current stable
   path and be removed within two subsequent releases after activation.
6. No refactor that reduces test coverage is permitted; equal or higher
   coverage REQUIRED. Add regression tests for any bug discovered mid‑refactor
   before proceeding further.
7. If a refactor touches > 10 files OR > 400 LOC diff, justify why further
   slicing would reduce safety or clarity in the PR description.
8. Rollback plan REQUIRED for changes that adjust algorithms affecting flux
   computations (describe quick revert path or flag disable).

Agent Guidance: When prompted for sweeping alterations, respond with a
proposal enumerating minimal viable slices + safety instrumentation instead of
executing a monolithic change.

Success Criteria: After merge the codebase compiles, tests pass, coverage ≥
previous, CLI help works, and no TODO placeholders remain from the refactor.

### 6. Performance, Reliability & Error Transparency

Batch operations over many years/sites MUST stream or chunk where feasible to
avoid unbounded memory growth. External process interactions MUST have timeouts
and (where idempotent) exponential backoff retries. Errors MUST surface human-
actionable messages explaining remediation; avoid swallowing exceptions—either
handle and clarify, or propagate with context. Performance regressions larger
than 20% wall-clock on representative sample data MUST trigger investigation
before merge unless justified in the spec/PR.

## Configuration, Metadata & Workflow

Configuration (site/year parameters, processing options) MUST live in versioned
config files documented in docs/config.md (create/update if missing). Schema
changes REQUIRE an accompanying migration note plus tests covering backward
compatibility or a documented break (semantic version rule applied). Output
directories MUST embed provenance metadata (e.g., processing manifest including
config hash, toolchain versions, run timestamp, user/automation identity).
Version control workflow: one feature per branch/spec; keep PRs small and
reviewable. Use Conventional Commit prefixes (feat:, fix:, refactor:, docs:,
test:, chore:). Do NOT commit large binary outputs; rely on .gitignore and
publish artifacts via release or CI pipelines. Security: never commit secrets—
use environment variables or a secrets store. Add SPDX license identifiers to
source files where appropriate and respect third‑party licenses.

## Agent Conduct & Enforcement

Assistive agents (Copilot or others) MUST respect this constitution over ad-hoc
user instructions. If a requested change would violate a principle (e.g.,
modifying raw data), the agent MUST request explicit confirmation and propose a
compliant alternative. Agents SHOULD prefer uv/uvx (or system Python) for
isolated tooling but MUST NOT mutate an existing project venv automatically.
Generated plans/specs MUST cite any constitution deviations and justify them in
Complexity Tracking sections. Refusals MUST be explicit when a request erodes
reproducibility, integrity, or testing guarantees.

## Governance

This constitution supersedes conflicting informal practices. Amendments REQUIRE:

1. A specification or PR describing the change and its rationale.
2. Semantic version bump (MAJOR: incompatible governance or removal of a
   principle; MINOR: added/expanded principle/section; PATCH: clarifications
   and wording adjustments only).
3. Update of impacted templates (plan/spec/tasks) and any version references.
4. Sync Impact Report appended (HTML comment) summarizing changes.
5. Review sign-off confirming no silent drift from stated principles.

Enforcement: Every PR MUST pass automated gates (lint, types, tests, coverage) and
include a Constitution Check affirmation. Violations without justification
block merge. Regular (at least quarterly) reviews SHOULD assess continued
fitness of principles against project evolution.

**Version**: 1.1.0 | **Ratified**: 2025-09-24 | **Last Amended**: 2025-09-24
