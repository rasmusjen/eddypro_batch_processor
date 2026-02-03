
# Investigation: EddyPro execution path (run vs scenarios)

Date: 2026-02-03

## Scope
Analyze how external EddyPro executables are invoked in the current codebase versus the rollback commit `rollback/0e9514e`, focusing on:
- Whether `eddypro_rp` and `eddypro_fcc` are called
- The pipeline setup (binary copy, temp dirs, working dir)
- The divergence between `run` and `scenarios`

## Sources reviewed
- Current code:
	- [src/eddypro_batch_processor/cli.py](../../src/eddypro_batch_processor/cli.py)
	- [src/eddypro_batch_processor/core.py](../../src/eddypro_batch_processor/core.py)
- Rollback code:
	- https://github.com/rasmusjen/eddypro_batch_processor/blob/rollback/0e9514e/src/eddypro_batch_processor.py
- Known issues:
	- [docs/KNOWN_ISSUES_AND_TODO.md](../KNOWN_ISSUES_AND_TODO.md)

## Findings (current main branch)

### `run` command
- Executes only the configured `eddypro_executable` (typically `eddypro_rp.exe`).
- No `eddypro_fcc` call in the `run` path.
- No binary copy to a local `bin/` folder in `run`.

Reference: [src/eddypro_batch_processor/cli.py](../../src/eddypro_batch_processor/cli.py)

### `scenarios` command
- Uses `run_eddypro_with_monitoring()`.
- Copies the EddyPro bin directory to a local `bin/` directory under the output base.
- Executes **both** `eddypro_rp` and `eddypro_fcc` sequentially.
- Cleans up `bin/` and `tmp/` afterward.

Reference: [src/eddypro_batch_processor/core.py](../../src/eddypro_batch_processor/core.py)

## Findings (rollback/0e9514e)

The legacy `run_eddypro()` in `rollback/0e9514e`:
- Creates `tmp/` and `bin/` under the output base path
- Copies the EddyPro binaries into `bin/`
- Executes **both** `eddypro_rp` and `eddypro_fcc` sequentially
- Cleans up `bin/` and `tmp/`

Reference: https://github.com/rasmusjen/eddypro_batch_processor/blob/rollback/0e9514e/src/eddypro_batch_processor.py

## Delta summary

| Area | Rollback behavior | Current behavior |
|---|---|---|
| `run` command | `rp` + `fcc` via local bin copy | **Only** `rp` (direct executable call) |
| `scenarios` command | `rp` + `fcc` via local bin copy | `rp` + `fcc` via local bin copy |
| Binary copy | Always in run | Only in scenarios |

## Implication
The current `run` path omits `eddypro_fcc`, which matches the observed behavior. The scenario path still runs `eddypro_fcc` as expected.

## Resolved requirements
- `run` must execute `eddypro_fcc` after `eddypro_rp` (no conditional gating).
- `run` must use the same local `bin/` copy and working-directory strategy as `scenarios`.
- If `eddypro_rp` fails (non-zero), skip `eddypro_fcc` and report failure.
- No known environments require skipping `eddypro_fcc`.

## Underspecifications and gaps

### Behavioral intent (product spec)
- No explicit statement of intended behavior for `run` vs `scenarios` (should `run` mirror `scenarios` or remain `rp`-only?).
- No documented criteria for when `eddypro_fcc` should be mandatory, optional, or skipped.

### Execution contract details
- Working directory expectations for `eddypro_rp`/`eddypro_fcc` are not documented.
- Binary copy strategy lacks specification: when to copy, what to copy, and cleanup guarantees.
- No stated requirement about preserving or removing `bin/` and `tmp/` on failures.

### Observability and failure handling
- No explicit success criteria or artifact checks to decide whether `eddypro_fcc` should run.
- No documented error-handling contract (e.g., whether `fcc` should run after `rp` non-zero exit).
- No explicit logging expectations for both executables (stdout/stderr capture, log locations).

### Configuration and UX
- No CLI/config option stated for toggling `eddypro_fcc` in `run`.
- No documented default value for a hypothetical `run-fcc` behavior if added.
- No explicit compatibility notes for different EddyPro versions (paths, binary names).

### Tests and acceptance criteria
- Missing explicit acceptance criteria for tests (what exact calls/paths must be observed).
- No mention of specific mock expectations or fixtures needed for `run` vs `scenarios`.

## Guardrails (do not modify inputs/templates)
The following input/config artifacts are **read-only** for this investigation and any fix branch unless explicit permission is given:

- [config/config.yaml](../../config/config.yaml)
- [config/metadata_template.ini](../../config/metadata_template.ini)
- Any existing EddyPro project files (e.g., `GL-Dsk_2025.eddypro`) in working directories

Rationale: These represent user inputs or canonical templates and must not be mutated by analysis or code changes.

## Inappropriate features discovered
None observed in this investigation.

## Draft debugging plan (no execution)

### Phase 1 — Confirm invocation path
1. Verify the pipeline failure is triggered via `run` vs `scenarios`.
2. Confirm `run` does not call `run_eddypro_with_monitoring()`.
3. Confirm `eddypro_executable` points to `eddypro_rp.exe`.

### Phase 2 — Reconcile code paths
1. Compare `cmd_run()` and `run_eddypro_with_monitoring()` for execution differences.
2. Document the intended behavior: `run` must call `rp` then `fcc`, using the same local `bin/` copy and working directory strategy as `scenarios`.
3. Define failure handling: if `rp` exits non-zero, skip `fcc` and report failure.

### Phase 3 — Correction options (design only)
- **Option A (selected)**: Make `run` call `run_eddypro_with_monitoring()` (rp + fcc, bin copy).

### Phase 4 — Acceptance criteria (implementation-ready)
The change is complete when all criteria below pass:

1. `run` executes both `eddypro_rp` then `eddypro_fcc` using the same local bin copy and working directory strategy as `scenarios`.
	 - Same bin copy location and temp directory strategy as in `run_eddypro_with_monitoring()`.
2. If `eddypro_rp` exits non-zero, `eddypro_fcc` is **not** invoked, and the failure is surfaced in the run result/manifest.
3. If `eddypro_rp` exits zero and `eddypro_fcc` exits zero, the run is marked successful.
4. On success, `bin/` and `tmp/` are cleaned up (consistent with `scenarios` behavior).
5. On failure, cleanup behavior is consistent with `scenarios` (do not introduce new retention behavior).
6. Coverage remains ≥70% and all tests pass.

### Phase 5 — Test plan (no execution)
Target tests are limited and deterministic to protect coverage and speed. Use mocks for subprocess and filesystem.

**Unit tests (core execution path):**
- Add tests in [tests/test_core.py](../../tests/test_core.py) for `run_eddypro_with_monitoring()` or its call site in `cmd_run()`.
- Mock subprocess to capture ordered calls:
	- Case A: `eddypro_rp` returns 0 → `eddypro_fcc` invoked exactly once after `eddypro_rp`.
	- Case B: `eddypro_rp` returns non-zero → `eddypro_fcc` not invoked.
- Assert working directory and executable path are sourced from the local `bin/` copy (same as `scenarios`).

**CLI tests (command wiring):**
- Update or add tests in [tests/test_cli_functions.py](../../tests/test_cli_functions.py) to ensure `cmd_run()` routes through `run_eddypro_with_monitoring()`.
- Mock to verify call count and arguments without running external binaries.

**Integration tests (dry-run if possible):**
- Update or add a minimal integration test in [tests/test_e2e_integration.py](../../tests/test_e2e_integration.py) using mocks to confirm rp→fcc ordering under `run`.
- Use temporary directories and fixed paths; avoid wall-clock coupling.

**Coverage safeguard:**
- Keep new tests minimal and focused; reuse fixtures where possible to avoid coverage regression.

### Phase 6 — Documentation and changelog updates
- Update [CHANGELOG.md](../../CHANGELOG.md) under Unreleased → Changed: `run` now mirrors `scenarios` execution path and includes `eddypro_fcc`.
- Update [docs/USAGE.md](../../docs/USAGE.md) and [README.md](../../README.md) if behavior is user-visible (run now runs both executables).
