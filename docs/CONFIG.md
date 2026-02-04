# Configuration Guide

This document describes all configuration options available in the `config/config.yaml` file.

## Configuration File Location

Default location: `config/config.yaml`

Override with: `--config /path/to/config.yaml`

## Configuration Schema

### Complete Example

```yaml
# EddyPro executable path
eddypro_executable: "C:/Program Files/LI-COR/EddyPro-7.0.9/bin/eddypro_rp.exe"

# Site identification
site_id: GL-ZaF

# Years to process
years_to_process:
  - 2021
  - 2022
  - 2023

# Input directory pattern (use {year} and {site_id} placeholders)
input_dir_pattern: "D:/L0_raw/{site_id}/{year}/ec/rflux_csv"

# Output directory pattern (use {year} and {site_id} placeholders)
output_dir_pattern: "D:/L1_processed/{site_id}/{year}/ec_rflux"

# ECMD (Extended Configuration Metadata) file path
ecmd_file: "D:/L1_processed/{site_id}/ecmd/{site_id}_ecmd.csv"

# Multiprocessing settings
multiprocessing: False
max_processes: 16

# Output streaming (EddyPro subprocess outputs)
stream_output: True

# Logging level
log_level: INFO

# Optional log file path (null disables file logging)
log_file: "logs/eddypro_processing.log"

# Performance monitoring
metrics_interval_seconds: 0.5

# Reporting
reports_dir: null  # null = use default ({output_dir}/reports)
report_charts: plotly  # Options: plotly, svg, none

# Optional: project template override
project_template: null  # null = use config/EddyProProject_template.ini
```

## Required Configuration Keys

The following keys **must** be present in your configuration file:

| Key | Type | Description |
|-----|------|-------------|
| `eddypro_executable` | str | Path to EddyPro executable |
| `site_id` | str | Site identifier (e.g., "GL-ZaF") |
| `years_to_process` | list[int] | Years to process |
| `input_dir_pattern` | str | Input directory pattern with placeholders |
| `output_dir_pattern` | str | Output directory pattern with placeholders |
| `ecmd_file` | str | Path to ECMD CSV file |
| `stream_output` | bool | Enable/disable real-time output |
| `log_level` | str | Logging level |
| `log_file` | str or null | Optional log file path (null disables file logging) |
| `multiprocessing` | bool | Enable/disable multiprocessing |
| `max_processes` | int | Maximum number of processes |
| `metrics_interval_seconds` | float | Performance monitoring interval |
| `reports_dir` | str or null | Custom reports directory |
| `report_charts` | str | Chart engine for reports |

## Optional Configuration Keys

| Key | Type | Description |
|-----|------|-------------|
| `project_template` | str or null | Optional path to EddyPro project template |

## Configuration Details

### eddypro_executable

**Type:** String (file path)

**Description:** Full path to the EddyPro raw processing executable (`eddypro_rp.exe` on Windows).

**Example:**
```yaml
eddypro_executable: "C:/Program Files/LI-COR/EddyPro-7.0.9/bin/eddypro_rp.exe"
```

**Validation:**
- File must exist
- Must be an executable file

**Notes:**
- Use forward slashes (`/`) even on Windows for cross-platform compatibility
- Wrap paths with spaces in quotes
- Scenario runs invoke both `eddypro_rp` and `eddypro_fcc`; ensure
  `eddypro_fcc` is present in the same directory as `eddypro_executable`.

---

### site_id

**Type:** String

**Description:** Unique identifier for the measurement site.

**Example:**
```yaml
site_id: GL-ZaF
```

**Validation:**
- Cannot be empty
- Used in path placeholders (`{site_id}`)

---

### years_to_process

**Type:** List of integers

**Description:** Years to process in the batch run.

**Example:**
```yaml
years_to_process:
  - 2021
  - 2022
  - 2023
```

**Validation:**
- List cannot be empty
- Each item must be a valid integer (typically 4-digit year)

**Notes:**
- Years are processed sequentially (or in parallel if multiprocessing is enabled)
- Used in path placeholders (`{year}`)

---

### input_dir_pattern

**Type:** String (path pattern)

**Description:** Pattern for locating raw input data directories.

**Placeholders:**
- `{site_id}` – replaced with the site ID
- `{year}` – replaced with each year from `years_to_process`

**Example:**
```yaml
input_dir_pattern: "D:/L0_raw/{site_id}/{year}/ec/rflux_csv"
```

**Validation:**
- Must contain both `{site_id}` and `{year}` placeholders
- For the first year, the resolved directory must exist

**Resolved Example:**
```
D:/L0_raw/GL-ZaF/2021/ec/rflux_csv
```

---

### output_dir_pattern

**Type:** String (path pattern)

**Description:** Pattern for writing processed output data.

**Placeholders:**
- `{site_id}` – replaced with the site ID
- `{year}` – replaced with each year from `years_to_process`

**Example:**
```yaml
output_dir_pattern: "D:/L1_processed/{site_id}/{year}/ec_rflux"
```

**Validation:**
- Must contain both `{site_id}` and `{year}` placeholders

**Resolved Example:**
```
D:/L1_processed/GL-ZaF/2021/ec_rflux
```

**Notes:**
- Output directories are created automatically if they don't exist
- Scenario runs add subdirectories (e.g., `_rot1_tlag2/`)

---

### ecmd_file

**Type:** String (file path or path pattern)

**Description:** Path to the ECMD (Extended Configuration Metadata) CSV file containing instrument and site metadata.

**Placeholders:**
- `{site_id}` – replaced with the site ID (optional)

**Examples:**
```yaml
# With placeholder
ecmd_file: "D:/L1_processed/{site_id}/ecmd/{site_id}_ecmd.csv"

# Without placeholder
ecmd_file: "C:/Users/me/data/GL-ZaF_ecmd.csv"
```

**Validation:**
- File must exist
- Must be a valid CSV file with required columns (see ECMD section below)

**Resolved Example:**
```
D:/L1_processed/GL-ZaF/ecmd/GL-ZaF_ecmd.csv
```

---

### multiprocessing

**Type:** Boolean

**Description:** Enable or disable multiprocessing for parallel year processing.

**Values:**
- `True` – process years in parallel
- `False` – process years sequentially

**Example:**
```yaml
multiprocessing: True
```

**Validation:**
- When enabled, `max_processes` must be positive

**Notes:**
- Multiprocessing settings are validated but not yet wired into execution.
  The `run` and `scenarios` commands currently execute sequentially.

---

### max_processes

**Type:** Integer

**Description:** Maximum number of parallel processes when `multiprocessing: True`.

**Example:**
```yaml
max_processes: 8
```

**Validation:**
- Must be a positive integer when `multiprocessing: True`
- Should not exceed the number of CPU cores

**Recommendations:**
- For CPU-bound tasks: `max_processes = CPU cores - 1`
- For I/O-bound tasks: `max_processes = CPU cores * 2`
- Monitor system resources and adjust as needed

---

### stream_output

**Type:** Boolean

**Description:** Control whether EddyPro subprocess outputs are streamed to the console in real-time.

**Values:**
- `True` – stream subprocess output to console
- `False` – suppress subprocess output

**Example:**
```yaml
stream_output: False
```

**Notes:**
- Useful for debugging when `True`
- Keep `False` for cleaner logs in production

---

### log_level

**Type:** String (enum)

**Description:** Logging verbosity level.

**Valid Values:**
- `DEBUG` – detailed diagnostic messages
- `INFO` – general informational messages (default)
- `WARNING` – warnings only
- `ERROR` – errors only
- `CRITICAL` – critical errors only

**Example:**
```yaml
log_level: INFO
```

**CLI Override:**
```bash
eddypro-batch --log-level DEBUG run
```

---

### log_file

**Type:** String (path) or null

**Description:** Optional log file path. When set, logs are written to both the
terminal and this file. When null, only console logging is used.

**Example:**
```yaml
log_file: "logs/eddypro_processing.log"
```

**Notes:**
- The parent directory is created automatically if missing.
- Useful for long runs where terminal output is truncated.

---

### metrics_interval_seconds

**Type:** Float

**Description:** Sampling interval (in seconds) for performance monitoring (CPU, memory, disk I/O).

**Example:**
```yaml
metrics_interval_seconds: 0.5
```

**Validation:**
- Must be positive

**Recommendations:**
- `0.5` – high-resolution monitoring (default)
- `1.0` – lower overhead for long runs
- `0.1` – very high resolution (may impact performance)

---

### reports_dir

**Type:** String (path) or null

**Description:** Custom directory for storing reports and manifests.

**Values:**
- `null` – use default location (`{output_dir}/reports`)
- Path string – use custom directory

**Examples:**
```yaml
# Use default
reports_dir: null

# Custom location
reports_dir: "D:/reports/eddypro_runs"
```

**CLI Override:**
```bash
eddypro-batch run --reports-dir /custom/reports
```

---

### report_charts

**Type:** String (enum)

**Description:** Chart engine for generating visualizations in HTML reports.

**Valid Values:**
- `plotly` – interactive Plotly charts (default, requires `plotly` package)
- `svg` – static SVG charts
- `none` – no charts (text/tables only)

**Example:**
```yaml
report_charts: plotly
```

**Fallback Behavior:**
- If `plotly` is selected but not installed, automatically falls back to `svg` with a warning

**Scope:** Currently used for HTML reports generated by the `run` command.

**CLI Override:**
```bash
eddypro-batch run --report-charts svg
```

---

### project_template

**Type:** String (path) or null

**Description:** Optional path to an EddyPro project template INI. If unset
or null, the default `config/EddyProProject_template.ini` is used.

**Example:**
```yaml
project_template: "D:/templates/EddyProProject_template.ini"
```

---

## ECMD File Format

The ECMD (Extended Configuration Metadata) file is a CSV containing instrument and site metadata that varies over time.

### Required Columns

**Temporal:**
- `DATE_OF_VARIATION_EF` – timestamp when metadata became effective (format: `YYYYMMDDHHmm`)

**Data File Metadata:**
- `FILE_DURATION` – duration of each raw data file in minutes (e.g., `30`)
- `ACQUISITION_FREQUENCY` – sampling frequency in Hz (e.g., `10`)

**Site Metadata:**
- `CANOPY_HEIGHT` – canopy height in meters (can be `0` for non-vegetated sites)

**Sonic Anemometer (SA):**
- `SA_MANUFACTURER` – manufacturer name (e.g., `gill`, `campbell`)
- `SA_MODEL` – model name (e.g., `hs_50`, `csat3`)
- `SA_HEIGHT` – measurement height in meters
- `SA_WIND_DATA_FORMAT` – wind data format (`uvw`, `polar`)
- `SA_NORTH_ALIGNEMENT` – north alignment method (`axis`, `spar`)
- `SA_NORTH_OFFSET` – north offset angle in degrees

**Gas Analyzer (GA):**
- `GA_MANUFACTURER` – manufacturer name (e.g., `licor`, `campbell`)
- `GA_MODEL` – model name (e.g., `li7200`, `li7500`)
- `GA_NORTHWARD_SEPARATION` – northward separation from SA in cm
- `GA_EASTWARD_SEPARATION` – eastward separation from SA in cm
- `GA_VERTICAL_SEPARATION` – vertical separation from SA in cm

**Closed-Path Specific (required if `GA_PATH = "closed"`):**
- `GA_TUBE_LENGTH` – intake tube length in cm
- `GA_TUBE_DIAMETER` – intake tube diameter in mm
- `GA_FLOWRATE` – flow rate in L/min

### Sanity Checks

The validation performs the following sanity checks on ECMD data:

- `ACQUISITION_FREQUENCY` must be positive
- `FILE_DURATION` must be positive
- `CANOPY_HEIGHT` must be non-negative (can be zero)
- `SA_HEIGHT` must be positive

### Example ECMD File

```csv
DATE_OF_VARIATION_EF,FILE_DURATION,ACQUISITION_FREQUENCY,CANOPY_HEIGHT,SA_MANUFACTURER,SA_MODEL,SA_HEIGHT,SA_WIND_DATA_FORMAT,SA_NORTH_ALIGNEMENT,SA_NORTH_OFFSET,GA_MANUFACTURER,GA_MODEL,GA_NORTHWARD_SEPARATION,GA_EASTWARD_SEPARATION,GA_VERTICAL_SEPARATION,GA_PATH,GA_TUBE_LENGTH,GA_TUBE_DIAMETER,GA_FLOWRATE
202001010000,30,10,0.1,gill,hs_50,3.16,uvw,spar,60,licor,li7200,-11,-18,0,closed,71.1,5.3,12
202106120130,30,10,0.1,gill,hs_50,3.16,uvw,spar,60,licor,li7200,-11,-18,0,closed,71.1,5.3,12
```

---

## Validation

Run validation to check your configuration:

```bash
eddypro-batch validate
```

This checks:
- All required keys present
- Correct types for all values
- Path existence (EddyPro executable, input directories, ECMD file)
- ECMD schema and sanity checks

### Validation Flags

Skip specific checks:

```bash
# Skip path existence checks
eddypro-batch validate --skip-paths

# Skip ECMD file validation
eddypro-batch validate --skip-ecmd
```

---

## CLI Overrides

Many configuration options can be overridden via CLI arguments:

```bash
eddypro-batch run \
  --site GL-ZaH \
  --years 2021 2022 \
  --mp \
  --max-proc 4 \
  --log-level DEBUG \
  --reports-dir /custom/reports \
  --report-charts svg
```

CLI arguments take precedence over config file values.

---

## Best Practices

### Use Absolute Paths

Prefer absolute paths to avoid ambiguity:

```yaml
# Good
input_dir_pattern: "D:/L0_raw/{site_id}/{year}/ec/rflux_csv"

# Avoid (relative paths can be fragile)
input_dir_pattern: "../data/raw/{site_id}/{year}"
```

### Separate Configs by Site

Create separate config files for different sites:

```
config/
├── config_GL-ZaF.yaml
├── config_GL-NuF.yaml
└── config_GL-Dsk.yaml
```

Run with:
```bash
eddypro-batch --config config/config_GL-ZaF.yaml run
```

### Version Control

- Keep config files under version control (Git)
- Document changes in CHANGELOG.md
- Use comments to explain site-specific settings

### Validate Early

Always validate before running:

```bash
eddypro-batch validate && eddypro-batch run
```

---

## See Also

- [USAGE.md](USAGE.md) – CLI usage and examples
- [SCENARIOS.md](SCENARIOS.md) – Scenario matrix runs
- [REPORTING.md](REPORTING.md) – Understanding reports
