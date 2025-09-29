# Quickstart

## Install

- Python 3.11+
- Create venv and install deps (`pip install -r requirements.txt`)

## Run (dry run)

- Single year: `eddypro-batch run-year --year 2021 --site GL-ZaF --dry-run`
- Range: `eddypro-batch run-range --start-year 2021 --end-year 2022 --site GL-ZaF --dry-run`
- Scenarios: `eddypro-batch run-scenarios --year 2021 --site GL-ZaF --matrix configs/scenarios.yaml --dry-run`

## Real run

- Provide `--input` and `--output` base directories or use config file.
- Optional profiling: `--profile --storage-tag local-ssd`

## Outputs

- `<output>/<site>/<year>/...` including provenance.json, summary.md, run_summary.csv, report.html
