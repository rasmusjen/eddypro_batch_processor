# Copilot Rules — EddyPro Batch Processor (Python, offline, batch)

## Project Context
- **Purpose**: Automated EddyPro processing with scenario support, performance monitoring, and comprehensive reporting
- **Tech stack**: Python 3.10+, pytest, black, ruff, mypy
- **Data scale**: Large batch processing, offline operation
- **Package manager**: pip + venv (no network during processing)

## Scope
- **No network**: never fetch data/packages or call remote APIs during processing
- **Large batch data**: prefer generators/chunked I/O; avoid full-dataset loads
- **Windows primary**: Development on Windows, but keep Linux/macOS compatible

## Virtual Environment (CRITICAL)

**ALWAYS use the project's venv:**

```powershell
# Windows (PowerShell) - ACTIVATE FIRST
.\venv\Scripts\Activate.ps1

# Linux/macOS (Bash)
source venv/bin/activate
```

**When running commands:**
- ✅ Always activate venv before running `pytest`, `ruff`, `black`, `mypy`, `eddypro-batch`
- ✅ Use `python -m <tool>` to ensure venv's packages are used
- ❌ Never assume global Python installation
- ❌ Never run commands without showing activation step first

**Installing dependencies:**
```powershell
# After activating venv
pip install -e .              # Install package in editable mode
pip install -e ".[dev]"       # Install with dev dependencies (pytest, ruff, etc.)
```

## Test Setup & Execution

**Test framework:** pytest with coverage tracking

**Location:** `tests/` directory (165 tests as of Nov 2024)

**Run tests:**
```powershell
# Activate venv first!
.\venv\Scripts\Activate.ps1

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_cli.py -v

# Run specific test
pytest tests/test_cli.py::test_cli_help_command -v

# Fast run (no coverage)
pytest tests/ -q
```

**Test requirements:**
- Coverage: ≥70% floor (target ≥90% for core modules)
- All tests must be **deterministic** (no random data, timestamps, or machine paths)
- New features require tests (unit + integration where applicable)
- E2E tests use fixtures in `tests/test_e2e_integration.py`

**VS Code integration:**
- Testing panel should auto-discover tests (uses `.vscode/settings.json`)
- Python interpreter must point to `.\venv\Scripts\python.exe`

## Protected Files (Read-only)

Do NOT edit these without explicit user permission (treat as inputs/templates):
- `config/EddyProProject_template.ini`
- `config/GL-ZaF_metadata_template.ini`
- `config/GL-ZaF_dynamic_metadata.ini`

## Code Quality

**Linting & formatting (run in order):**
```powershell
# 1. Format code
black src/ tests/

# 2. Lint (auto-fix)
ruff check --fix src/ tests/

# 3. Type checking
mypy src/

# 4. Run tests
pytest tests/ -v
```

**Standards:**
- **black (88 chars)**: No exceptions
- **ruff**: Rules: E,F,W,I,N,UP,B,SIM,TRY,PL
- **Type hints**: Strict; all public APIs fully typed
- **Docstrings**: Google-style for public APIs (Args/Returns/Raises/Examples)
- **mypy**: Keep clean; no `# type: ignore` without justification

## Documentation Maintenance (CRITICAL)

**After ANY code change, check if these need updates:**

1. **[`README.md`](../README.md)** - Main project documentation
   - Update if: CLI commands change, features added, installation steps modified
   - Sections: Features, Quick Start, Usage examples

2. **[`docs/USAGE.md`](../docs/USAGE.md)** - Complete CLI reference
   - Update if: New CLI arguments, changed defaults, new subcommands

3. **[`docs/SCENARIOS.md`](../docs/SCENARIOS.md)** - Scenario matrix documentation
   - Update if: New parameters added, scenario limits changed, suffix naming modified

4. **[`docs/CONFIG.md`](../docs/CONFIG.md)** - Configuration reference
   - Update if: New config keys, changed validation, YAML structure modified

5. **[`docs/REPORTING.md`](../docs/REPORTING.md)** - Report format documentation
   - Update if: New metrics, report structure changed, manifest schema modified

6. **[`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)** - System design
   - Update if: New modules, major refactoring, data flow changes

7. **[`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md)** - Developer guide
   - Update if: Setup process changed, new tools added, testing approach modified

**CHANGELOG maintenance:**
- **MUST update [`CHANGELOG.md`](../CHANGELOG.md) for EVERY user-facing change**
- Add entry to `## [Unreleased]` section following Keep a Changelog format
- Categories: Added, Changed, Deprecated, Removed, Fixed, Security
- Before commit/push/PR: **verify CHANGELOG is updated**

**Documentation checklist (run before PR):**
```powershell
# 1. Check if docs need updates
git diff --name-only origin/main | grep -E "(src/|tests/)" > /dev/null && echo "Code changed - review docs"

# 2. Verify README examples still work
eddypro-batch --help
eddypro-batch validate --config config/config.yaml

# 3. Check CHANGELOG has unreleased section
grep -A 5 "## \[Unreleased\]" CHANGELOG.md

# 4. Lint documentation
# (if using markdownlint)
markdownlint README.md docs/*.md
```

## Testing Requirements

- Every change adds/updates **pytest** tests
- Target: **≥90% core coverage** (start at 70% floor, improve over time)
- Use **Hypothesis** for property-based testing where applicable
- Keep **golden files** tiny in `tests/data/expected`
- Tests must be **deterministic** (seed RNG; no wall-clock or machine-path coupling)

**Test file naming:**
- `test_*.py` for unit tests
- `test_e2e_*.py` for end-to-end integration tests
- `test_*_integration.py` for integration tests

## Reliability & Safety

- Validate inputs early (**schemas, dtypes, ranges, units**). Fail with actionable messages.
- Core transforms are **pure** (no I/O). Orchestrators do I/O.
- **Idempotent writes**: write to temp, then atomic move. Support `--retries`/`--timeout`.
- On bad records: **log + quarantine** to a sidecar file; never drop silently.

## Performance & Observability

- Single-pass where possible; minimize re-reads; batch writes
- Parallelism: **process-based** for CPU-bound; **do not over-subscribe**; workers are configurable
- Emit **structured logs** (run_id, step, file, chunk_idx, rows, duration_ms). One log per run.
- Provide **progress** (tqdm) and optional **light profiling** (CPU/IO/peak RAM)
- Each run writes a **manifest** (config hash, git SHA, start/end, metrics, outputs)
- **Dependencies**: psutil (monitoring), plotly (charts, with fallbacks), optional jinja2 (templates)

## Config & CLI

- Single source of truth: **`config/config.yaml`**; CLI overrides are explicit
- CLI tool: **`eddypro-batch`** with subcommands (run, scenarios, validate, status)
- No hard-coded paths. Keep unit conversions at edges; internal units are canonical
- CLI entry point: `src/eddypro_batch_processor/cli.py`

## Git & CI

- Branches: `feat/<slug>`, `fix/<slug>`; Conventional Commits
- PR must describe **Problem | Approach | Tests | Risks | Rollback**; green CI required
- **Pre-commit**: ruff, black, mypy, and fast tests on staged files
- CI (offline): ruff → black --check → mypy → pytest (tiny fixtures). Upload **coverage + run manifest** artifacts. Cache env.

## Working Style (for AI agents)

**When making changes:**

1. **Ask before assuming**: If requirements are ambiguous, ask clarifying questions
2. **Incremental progress**: If a task is large, break into steps and show progress
3. **Show your work**: Display commands you're running and their output
4. **Handle errors gracefully**: If stuck, explain what went wrong and suggest alternatives
5. **Use timeouts**: Add timeouts to subprocess calls (e.g., `timeout=30`) to prevent hangs

**Communication:**
- ✅ Explain what you're about to do before doing it
- ✅ Show activation commands explicitly: `.\venv\Scripts\Activate.ps1`
- ✅ Provide complete commands (not "run tests" but actual `pytest` command)
- ✅ Mention which files you're modifying
- ❌ Don't assume paths or configurations
- ❌ Don't skip verification steps

**Error handling:**
- If tests fail: Show full error output and suggest fixes
- If linting fails: Show violations and fix them
- If stuck: Provide alternative approaches or ask for guidance
- Use `--dry-run` flags when testing large operations

## Project File Locations

**Source code:** `src/eddypro_batch_processor/`
- `cli.py` - CLI entry point (argparse, subcommands)
- `core.py` - Core processing logic (ConfigManager, run_eddypro)
- `ini_tools.py` - INI file handling (patching, validation)
- `scenarios.py` - Scenario matrix generation
- `monitor.py` - Performance monitoring
- `report.py` - Report generation
- `validation.py` - Configuration validation

**Configuration:** `config/`
- `config.yaml` - User configuration (NOT in git, use `config.yaml.example`)
- `EddyProProject_template.ini` - EddyPro project template (PROTECTED)
- `GL-ZaF_metadata_template.ini` - Site metadata template (PROTECTED)

**Tests:** `tests/`
- `test_cli.py` - CLI command tests
- `test_e2e_integration.py` - End-to-end integration tests
- `test_ini_tools.py` - INI handling tests
- `test_scenarios.py` - Scenario generation tests
- (etc.)

**Documentation:** `docs/`
- See "Documentation Maintenance" section above for file purposes

## Definition of Done (return this checked list with each change)

**Before committing:**
- [ ] Virtual environment activated (show command: `.\venv\Scripts\Activate.ps1`)
- [ ] Lint/format/typecheck clean (black, ruff, mypy)
- [ ] Tests updated; coverage maintained (≥70%); deterministic
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Schema/unit validations in place (if applicable)
- [ ] Chunked I/O & parallelism reviewed (no over-subscribe)
- [ ] Logs + manifest written; profiling optional (if applicable)
- [ ] **Documentation updated** (README, USAGE, CONFIG, SCENARIOS, etc. as needed)
- [ ] **CHANGELOG.md updated** with entry in `[Unreleased]` section
- [ ] CLI/config/docstrings updated (if public API changed)

**Before PR:**
- [ ] Feature branch created (`feat/<slug>` or `fix/<slug>`)
- [ ] All commits follow Conventional Commits format
- [ ] PR description includes: Problem | Approach | Tests | Risks | Rollback
- [ ] Pre-commit hooks pass
- [ ] CI pipeline green (if configured)
- [ ] Documentation review complete (all affected docs updated)
- [ ] CHANGELOG entry reviewed and accurate

## Common Commands Reference

```powershell
# Activate venv (Windows)
.\venv\Scripts\Activate.ps1

# Install/update dependencies
pip install -e ".[dev]"

# Run all quality checks (in order)
black src/ tests/
ruff check --fix src/ tests/
mypy src/
pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test
pytest tests/test_cli.py::test_cli_help_command -v

# Test CLI commands
eddypro-batch --help
eddypro-batch validate --config config/config.yaml
eddypro-batch run --help

# Check coverage
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html

# Pre-commit all files
pre-commit run --all-files
```

## Quick Troubleshooting

**Tests fail with "module not found":**
→ Check venv is activated and `pip install -e ".[dev]"` was run

**Linters not found:**
→ Install dev dependencies: `pip install -e ".[dev]"`

**CLI command not found:**
→ Install package in editable mode: `pip install -e .`

**Tests hang:**
→ Add `timeout=30` to subprocess calls; check for infinite loops

**Coverage dropped:**
→ Review what code was added; write tests for new functions

**Documentation out of sync:**
→ Review Definition of Done checklist; update affected docs
