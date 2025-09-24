# Configuration Guide

This document explains how `eddypro_batch_processor` is configured, how runtime context is derived, and how to extend or override defaults safely.

## Overview

Configuration is layered (lowest precedence first):

1. Built‑in defaults (embedded in code for safety / deterministic behavior)
2. `config/config.yaml`
3. Dynamic metadata & template files in `config/`
4. Environment variables (prefixed `EDDYPRO_`)
5. CLI flags / explicit function parameters (highest precedence)

Result: an effective config object passed into the processing pipeline and (after this update) captured in provenance manifests.

## Files in `config/`

| File | Purpose |
|------|---------|
| `config.yaml` | Primary static configuration (site code, paths, enabled processing stages, logging detail). |
| `EddyProProject_template.ini` | Template for generating an EddyPro project file (.eddypro) parameterized per site/year run. |
| `metadata_template.ini` | Base static metadata template merged with site/year specifics. |
| `GL-ZaF_metadata_template.ini` | Site-specific override example (demonstrates specialization). |
| `GL-ZaF_dynamic_metadata.ini` | Dynamic subset (values that change per run or are computed). |

Additional runtime artifacts such as `*_dynamic_metadata.txt` or generated `.eddypro` project files are emitted into the processed run directory tree.

## Key Sections (proposed schema)

Below is a descriptive schema (not strict JSON Schema yet) of expected top-level keys in `config.yaml`.

```yaml
site:
  code: GL-ZaF              # Short site identifier
  description: Glacier XYZ  # Human-readable label
  timezone: Europe/Copenhagen
paths:
  raw_root: data/raw        # Root for incoming raw data years
  processed_root: data/processed
  temp_root: data/processed/tmp
processing:
  years: [2021, 2022, 2023] # Years to process (can be overridden by CLI)
  concurrency: 2            # Future: parallel runs
  stages:                   # Enable/disable pipeline components
    prepare: true
    generate_project: true
    run_eddypro: true
    postprocess: true
eddypro:
  mode: advanced            # or 'express'
  executable: eddypro_cli   # Name or path; resolved on PATH if bare
logging:
  level: INFO               # DEBUG/INFO/WARNING/ERROR
  file: logs/eddypro_processing.log
provenance:
  enabled: true
  include_environment: true # Capture Python + package versions
  redact:
    - secret_token
    - api_key
```

### Field Notes

- `paths.*` may be relative; they are resolved against repository root at runtime.
- `processing.years` may be dynamically discovered from folder names if omitted.
- `eddypro.mode` influences which INI template variables are substituted.
- `provenance.redact` lists keys (case-insensitive) removed from the captured flattened config before serialization.

## Environment Variable Overrides

Environment variables with prefix `EDDYPRO_` map to nested keys using double underscore (`__`) as a path separator.

Example:

```bash
EDDYPRO_PROCESSING__CONCURRENCY=4
EDDYPRO_LOGGING__LEVEL=DEBUG
```

These override `processing.concurrency` and `logging.level` respectively.

### Boolean & List Coercion Rules

- `true/false/1/0` (case-insensitive) become booleans.
- Comma-separated values become lists (e.g., `2021,2022,2023`).

## Dynamic Metadata Flow

1. Base metadata (`metadata_template.ini`) loaded.
2. Site overrides applied (e.g., `GL-ZaF_metadata_template.ini`).
3. Dynamic metadata file (e.g., `GL-ZaF_dynamic_metadata.ini`) parsed; placeholders substituted (timestamps, run id, operator, etc.).
4. Result written to run directory (`<site>/<year>/GL-ZaF.metadata`).

## Validation & Future Hardening

Short term validation: required keys asserted in code (fail-fast with clear error). Planned enhancements:

- JSON Schema (`schema/config.schema.json`) for automated validation.
- CI check to ensure example config matches schema.

## Extending the Configuration

Add new keys under relevant namespaces. Maintain backward compatibility by providing defaults in code. Update this document and (when introduced) the schema file.

## Provenance Integration (New)

When a run completes, an immutable `provenance.json` (or timestamped variant) will record:

- Effective config hash (SHA256 of canonical JSON)
- Subset of config (with `redact` keys removed)
- Git commit, branch, dirty flag
- Python & package versions
- Start/end timestamps & duration
- Input/output directories & year(s) processed

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|--------------|-----------|
| Missing year directories | `processing.years` not set and discovery found none | Create year folder under `raw_root` or list years explicitly. |
| Override ignored | Wrong env var path | Check double underscore segments align to YAML nesting. |
| Provenance missing | `provenance.enabled` false | Set to true or remove key (defaults to enabled). |

## Change Log

- v0.1.0 (2025-09-24): Initial draft config guide.

---

Feedback welcome; propose improvements via PR referencing Constitution governance rules.
