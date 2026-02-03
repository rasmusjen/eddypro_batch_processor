
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

## Draft debugging plan (no execution)

### Phase 1 — Confirm invocation path
1. Verify the pipeline failure is triggered via `run` vs `scenarios`.
2. Confirm `run` does not call `run_eddypro_with_monitoring()`.
3. Confirm `eddypro_executable` points to `eddypro_rp.exe`.

### Phase 2 — Reconcile code paths
1. Compare `cmd_run()` and `run_eddypro_with_monitoring()` for execution differences.
2. Document the intended behavior: should `run` call `fcc` or not?

### Phase 3 — Correction options (design only)
- **Option A**: Make `run` call `run_eddypro_with_monitoring()` (rp + fcc, bin copy).
- **Option B**: Add a flag (e.g., `--run-fcc`) to enable fcc in `run`.
- **Option C**: Detect output artifacts from rp and conditionally call fcc.

### Phase 4 — Test plan (no execution)
- Unit tests for `cmd_run` to assert which executables are invoked.
- Integration tests mocking subprocess to verify rp → fcc call order.

## Open questions
- Is `run` intended to be rp-only or to mirror the scenario runner?
- Are there environments where `eddypro_fcc` should be optional even in `run`?
