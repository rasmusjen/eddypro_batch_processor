# CLI Usage Guide

This document provides detailed usage information for the `eddypro-batch` command-line tool.

## Table of Contents

- [Overview](#overview)
- [Global Options](#global-options)
- [Commands](#commands)
  - [run](#run-command)
  - [scenarios](#scenarios-command)
  - [validate](#validate-command)
  - [status](#status-command)
- [Examples](#examples)

## Overview

The `eddypro-batch` CLI provides automated EddyPro processing with scenario support, performance monitoring, and reporting capabilities. All commands operate on a YAML configuration file and support various overrides via command-line arguments.

```bash
eddypro-batch [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

## Global Options

These options can be used with any command:

- `--config PATH`: Path to the configuration YAML file (default: `config/config.yaml`)
- `--log-level LEVEL`: Set the logging level (choices: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; default: `INFO`)
- `--help`, `-h`: Show help message and exit

## Commands

### run Command

Process site/years according to configuration and/or overrides.

**Usage:**
```bash
eddypro-batch run [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--site SITE_ID` | str | Override site ID from config |
| `--years YEAR [YEAR ...]` | int | Override years to process |
| `--input-dir-pattern PATTERN` | str | Override input directory pattern |
| `--output-dir-pattern PATTERN` | str | Override output directory pattern |
| `--eddypro-exe PATH` | str | Override EddyPro executable path |
| `--stream-output` | flag | Enable real-time output streaming |
| `--no-stream-output` | flag | Disable real-time output streaming |
| `--mp` | flag | Enable multiprocessing |
| `--max-proc N` | int | Maximum number of processes for multiprocessing |
| `--dry-run` | flag | Generate files without executing EddyPro |
| `--metrics-interval SECONDS` | float | Performance monitoring sampling interval (default: 0.5) |
| `--reports-dir PATH` | str | Custom reports directory (default: `{output_dir}/reports`) |
| `--report-charts ENGINE` | str | Chart engine for reports (choices: `plotly`, `svg`, `none`; default: `plotly`) |

**INI Parameter Overrides:**

| Option | Choices | Description |
|--------|---------|-------------|
| `--rot-meth` | 1, 3 | Rotation method (1=DR double rotation, 3=PF planar fit) |
| `--tlag-meth` | 2, 4 | Time lag method (2=CMD constant minimum delay, 4=AO automatic optimization) |
| `--detrend-meth` | 0, 1 | Detrend method (0=BA block averaging, 1=LD linear detrending) |
| `--despike-meth` | 0, 1 | Spike removal method (0=VM97 Vickers & Mahrt 1997, 1=M13 Mauder et al. 2013) |
| `--hf-meth` | 1, 4 | High-frequency spectral correction (1=Moncrieff et al. 1997 analytic, 4=Fratini et al. 2012 in situ/analytic) |

**Examples:**

```bash
# Basic run with default config
eddypro-batch run

# Run with specific site and years
eddypro-batch run --site GL-ZaF --years 2021 2022

# Dry run to generate project files without execution
eddypro-batch run --dry-run

# Run with INI parameter overrides
eddypro-batch run --rot-meth 3 --tlag-meth 4 --detrend-meth 1

# Run with multiprocessing
eddypro-batch run --mp --max-proc 8

# Run with custom reports directory and SVG charts
eddypro-batch run --reports-dir /custom/reports --report-charts svg

# Debug run with verbose output
eddypro-batch --log-level DEBUG run --stream-output
```

---

### scenarios Command

Run a Cartesian product of supplied INI parameter values to test multiple configurations.

**Usage:**
```bash
eddypro-batch scenarios [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--rot-meth N [N ...]` | int | Rotation methods to test (choices: 1, 3) |
| `--tlag-meth N [N ...]` | int | Time lag methods to test (choices: 2, 4) |
| `--detrend-meth N [N ...]` | int | Detrend methods to test (choices: 0, 1) |
| `--despike-meth N [N ...]` | int | Spike removal methods to test (choices: 0, 1) |
| `--hf-meth N [N ...]` | int | High-frequency correction methods to test (choices: 1, 4) |
| `--max-scenarios N` | int | Maximum number of scenarios allowed (default: 32) |
| `--site SITE_ID` | str | Site ID to process |
| `--years YEAR [YEAR ...]` | int | Years to process |
| `--metrics-interval SECONDS` | float | Performance monitoring sampling interval (default: 0.5) |

**Examples:**

```bash
# Test two rotation methods for a single year
eddypro-batch scenarios --rot-meth 1 3 --site GL-ZaF --years 2021

# Test combination of rotation and time lag methods
eddypro-batch scenarios --rot-meth 1 3 --tlag-meth 2 4 --years 2021

# Test all four parameters (16 combinations)
eddypro-batch scenarios \
  --rot-meth 1 3 \
  --tlag-meth 2 4 \
  --detrend-meth 0 1 \
  --despike-meth 0 1 \
  --years 2021

# Test all five parameters (32 combinations - maximum by default)
eddypro-batch scenarios \
  --rot-meth 1 3 \
  --tlag-meth 2 4 \
  --detrend-meth 0 1 \
  --despike-meth 0 1 \
  --hf-meth 1 4 \
  --years 2021

# Test with custom max scenarios limit
eddypro-batch scenarios --rot-meth 1 3 --max-scenarios 10 --years 2021
```

**Scenario Limits:**

The `scenarios` command enforces a hard cap of 32 combinations by default to prevent runaway resource usage. If the Cartesian product exceeds this limit, the command will error with an actionable message instructing you to narrow the parameters.

You can adjust this limit with `--max-scenarios`, but be mindful of system resources and processing time.

---

### validate Command

Validate configuration and environment before running EddyPro processing.

**Usage:**
```bash
eddypro-batch validate [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--skip-paths` | flag | Skip path existence checks |
| `--skip-ecmd` | flag | Skip ECMD file validation |

**What Gets Validated:**

By default, the `validate` command checks:

1. **Config Structure**: All required keys present with correct types
2. **Config Sanity**: Non-empty site_id and years, positive values, etc.
3. **Paths**: EddyPro executable exists, directory patterns valid, input directories exist
4. **ECMD Schema**: Required columns present, closed-path columns if applicable
5. **ECMD Sanity**: Positive acquisition frequency and file duration, non-negative canopy height, etc.

**Exit Behavior:**

- Exit code `0`: All validations passed
- Exit code `1`: One or more validations failed

**Examples:**

```bash
# Full validation
eddypro-batch validate

# Validate config only (skip path checks)
eddypro-batch validate --skip-paths

# Validate without checking ECMD file
eddypro-batch validate --skip-ecmd

# Validate with custom config file
eddypro-batch --config /path/to/config.yaml validate

# Quiet validation (only show errors)
eddypro-batch --log-level WARNING validate
```

**Sample Output:**

```
Validation Report
============================================================

✓ Config Structure: OK
✓ Config Sanity: OK
❌ Paths: 1 error(s)
   • EddyPro executable not found: /path/to/eddypro_rp.exe
     → Check 'eddypro_executable' path in config
✓ Ecmd Schema: OK
✓ Ecmd Sanity: OK

============================================================
❌ Total errors: 1
```

---

### status Command

Summarize results from the last run using provenance and manifest files.

**Usage:**
```bash
eddypro-batch status [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--reports-dir PATH` | str | Override reports directory path |

**Examples:**

```bash
# Check status of last run
eddypro-batch status

# Check status in custom reports directory
eddypro-batch status --reports-dir /custom/reports
```

**Note:** This command is currently a stub implementation and will be fully implemented in a future milestone.

---

## Examples

### Typical Workflow

1. **Validate your setup first:**
   ```bash
   eddypro-batch validate
   ```

2. **Run a single configuration:**
   ```bash
   eddypro-batch run --site GL-ZaF --years 2021
   ```

3. **Test different parameter combinations:**
   ```bash
   eddypro-batch scenarios --rot-meth 1 3 --tlag-meth 2 4 --years 2021
   ```

4. **Check the results:**
   ```bash
   eddypro-batch status
   ```

### Advanced Usage

**Process multiple years with multiprocessing:**
```bash
eddypro-batch run --site GL-ZaF --years 2020 2021 2022 2023 --mp --max-proc 4
```

**Test scenario matrix for specific site and year:**
```bash
eddypro-batch scenarios \
  --site GL-ZaF \
  --years 2021 \
  --rot-meth 1 3 \
  --tlag-meth 2 4 \
  --max-scenarios 16
```

**Dry run to preview what will be generated:**
```bash
eddypro-batch run --dry-run --site GL-ZaF --years 2021
```

**Debug a validation failure:**
```bash
eddypro-batch --log-level DEBUG validate
```

---

## Configuration File

All commands read from a YAML configuration file (default: `config/config.yaml`). See [CONFIG.md](CONFIG.md) for details on all available options.

## Scenario Processing

For detailed information about how scenarios work, naming conventions, and output structure, see [SCENARIOS.md](SCENARIOS.md).

## Reports

For information about report structure, location, and interpretation, see [REPORTING.md](REPORTING.md).

## Development

For contributing guidelines, testing, and code standards, see [DEVELOPMENT.md](DEVELOPMENT.md).
