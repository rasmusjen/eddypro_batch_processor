# Copilot Rules — Python, private, offline, batch

## Scope
- **No network**: never fetch data/packages or call remote APIs.
- **Large batch data**: prefer generators/chunked I/O; avoid full-dataset loads.

## Protected Files (Read-only)
- Do NOT edit these without explicit user permission (treat as inputs/templates):
	- `config/EddyProProject_template.ini`
	- `config/GL-ZaF_metadata_template.ini`
	- `config/GL-ZaF_dynamic_metadata.ini`

## Code Quality
- Enforce **black (88)**, **ruff** (E,F,W,I,N,UP,B,SIM,TRY,PL), strict type hints; keep **mypy/pyright clean**.
- Public APIs get NumPy/Google-style docstrings (Args/Returns/Raises/Examples).

## Testing
- Every change adds/updates **pytest** tests; target **≥90% core coverage** (start at 70% floor, improve over time; document allowed gaps).
- Use **Hypothesis** where parsing/transform correctness benefits; keep **golden files** tiny in `tests/data/expected`.
- Tests must be **deterministic** (seed RNG; no wall-clock or machine-path coupling).

## Reliability & Safety
- Validate inputs early (**schemas, dtypes, ranges, units**). Fail with actionable messages.
- Core transforms are **pure** (no I/O). Orchestrators do I/O.
- **Idempotent writes**: write to temp, then atomic move. Support `--retries`/`--timeout`.
- On bad records: **log + quarantine** to a sidecar file; never drop silently.

## Performance & Observability
- Single-pass where possible; minimize re-reads; batch writes.
- Parallelism: **process-based** for CPU-bound; **do not over-subscribe**; workers are configurable.
- Emit **structured logs** (run_id, step, file, chunk_idx, rows, duration_ms). One log per run.
- Provide **progress** (tqdm) and optional **light profiling** (CPU/IO/peak RAM).
- Each run writes a **manifest** (config hash, git SHA, start/end, metrics, outputs).
- **Dependencies**: psutil (monitoring), plotly (charts, with fallbacks), optional jinja2 (templates).

## Config & CLI
- Single source of truth: **`config/config.yaml`**; CLI overrides are explicit.
- CLI tool: **`eddypro-batch`** with subcommands (run, scenarios, validate, status).
- No hard-coded paths. Keep unit conversions at edges; internal units are canonical.

## Git & CI
- Branches: `feat/<slug>`, `fix/<slug>`; Conventional Commits.
- PR must describe **Problem | Approach | Tests | Risks | Rollback**; green CI required.
- **Pre-commit**: ruff, black, mypy, and fast tests on staged files.
- CI (offline): ruff → black --check → mypy → pytest (tiny fixtures). Upload **coverage + run manifest** artifacts. Cache env.

## Definition of Done (return this checked list with each change)
- [ ] Lint/format/typecheck clean
- [ ] Tests updated; coverage maintained; deterministic
- [ ] Schema/unit validations in place
- [ ] Chunked I/O & parallelism reviewed (no over-subscribe)
- [ ] Logs + manifest written; profiling optional
- [ ] CLI/config/docstrings/CHANGELOG updated
- [ ] Feature branch pushed; PR opened with summary & risks
