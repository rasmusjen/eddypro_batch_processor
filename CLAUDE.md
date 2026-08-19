# CLAUDE.md

Project brief for Claude Code sessions in this repo.

## What this is

`eddypro-batch-processor` batch-runs LI-COR EddyPro over multi-year
eddy-covariance flux data on Windows. It generates EddyPro `.eddypro`
project files from templates, runs `eddypro_rp`/`eddypro_fcc` as
subprocesses across years/sites/parameter scenarios, monitors process
performance, and produces manifests plus HTML/Plotly reports.

## Environment

- Windows, PowerShell primary shell.
- Virtualenv lives at **`.venv`**. A stale second `venv/` directory also
  exists in the repo — always use `.venv`, never `venv`.
- Activate: `.venv\Scripts\Activate.ps1`
- Install (editable, with dev deps): `pip install -e ".[dev]"`

## Commands

```powershell
.venv\Scripts\Activate.ps1
pytest
ruff check .
black .
mypy src/
pre-commit run --all-files
```

## Module map (`src/eddypro_batch_processor/`)

- `cli.py` — argparse CLI, entry point `eddypro-batch`; subcommands
  `run`, `scenarios`, `validate`, `status`.
- `core.py` — orchestration: config loading, subprocess execution of
  `eddypro_rp` / `eddypro_fcc`.
- `monitor.py` — psutil-based process-tree performance sampling during runs.
- `analysis.py` — bottleneck classification from monitoring samples.
- `report.py` — run manifests and HTML/Plotly report generation.
- `ini_tools.py` — EddyPro `.eddypro` INI templating and patching.
- `ecmd.py` — ECMD metadata CSV handling.
- `scenarios.py` — parameter Cartesian-product scenario generation.
- `validation.py` — config and ECMD validation.

## Domain rules — read before acting

- **EddyPro runs take hours.** Never launch a real run speculatively just
  to "check" something — use `--dry-run` instead.
- **Never write to or delete anything under** `data/`, `logs/`,
  `D:/L0_raw/`, or `D:/L1_processed/`. These hold irreplaceable raw and
  processed field data.
- `config/config.yaml` is the user's live working config with
  machine-specific paths. Don't commit changes to it.

## Code quality

Detailed code-quality, testing, and doc-maintenance rules live in
`.github/copilot-instructions.md` — treat that as the source of truth
rather than duplicating it here.

## Definition of Done

- [ ] Tests pass (`pytest`)
- [ ] Lint/format/type-check clean (`ruff check .`, `black .`, `mypy src/`)
- [ ] Relevant docs updated (README, `docs/*.md` as applicable)
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`
