# Configuration Guide

This document describes all configuration options available in the `config/config.yaml` file.

## Configuration File Location

Default location: `config/config.yaml`

Override with: `--config /path/to/config.yaml`

`config/config.yaml` is **not tracked in git** — it holds machine-specific
absolute paths that differ per install. It is covered by `.gitignore`, so a
fresh clone has no `config/config.yaml` until you create one:

```powershell
cp config/config.yaml.example config/config.yaml
```

Only `config/config.yaml.example` is version-controlled.

## Configuration Schema

### Complete Example

The full, authoritative example config lives at
[`config/config.yaml.example`](../config/config.yaml.example) — copy it to
`config/config.yaml` and edit it. A short excerpt:

```yaml
eddypro_executable: "C:/Program Files/LI-COR/EddyPro-7.0.9/bin/eddypro_rp.exe"
site_id: GL-NuF
years_to_process:
  - 2024
input_dir_pattern: "D:/L0_raw/{site_id}/{year}/ec/rflux_csv"
output_dir_pattern: "D:/L1_processed/{site_id}/{year}/ec_rflux"
ecmd_file: "D:/L1_processed/{site_id}/ecmd/{site_id}_ecmd.csv"
multiprocessing: False
max_processes: 16
monitoring_enabled: true
metrics_interval_seconds: 0.5
reports_dir: null
report_charts: plotly
```

For a fully worked multi-year example (same settings applied across several
years), see [MULTI_YEAR_RUNS.md](MULTI_YEAR_RUNS.md) and
[`examples/multi_year_config.yaml`](../examples/multi_year_config.yaml).

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
| `multiprocessing` | bool | Enable/disable multiprocessing across years |
| `max_processes` | int | Maximum number of parallel worker processes |
| `metrics_interval_seconds` | float | Performance monitoring interval |
| `reports_dir` | str or null | Custom reports directory |
| `report_charts` | str | Chart engine for reports |

## Optional Configuration Keys

| Key | Type | Description |
|-----|------|-------------|
| `project_template` | str or null | Optional path to EddyPro project template |
| `log_file` | str or null | Optional log file path (null disables file logging) |
| `log_max_bytes` | int or null | Max log file size in bytes before rotation (0 disables rotation) |
| `log_backup_count` | int or null | Number of rotated log files to keep |
| `log_eddypro_output` | bool | Write EddyPro stdout/stderr to logs |
| `monitoring_enabled` | bool | Enable/disable performance monitoring (default: `true`) |
| `cpu_affinity` | str, list[int], or null | Pin the run to specific logical CPUs (default: `null`, no pinning) |

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
- Years are processed in parallel (one worker per year, up to `max_processes`)
  when `multiprocessing: true`; otherwise sequentially. See
  [MULTI_YEAR_RUNS.md](MULTI_YEAR_RUNS.md) for a worked example.
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
- When `True`, the `run` command processes years in parallel across up to
  `max_processes` worker processes (one worker per year). `scenarios`
  processes years sequentially, running the full scenario batch for each
  year before moving to the next.
- Enable via CLI with `--mp` (and `--max-proc N`); see
  [MULTI_YEAR_RUNS.md](MULTI_YEAR_RUNS.md).

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

### log_max_bytes

**Type:** Integer (bytes) or null

**Description:** Maximum size of the log file before rotation. Set to 0 or null
to disable rotation.

**Example:**
```yaml
log_max_bytes: 10485760  # 10 MB
```

---

### log_backup_count

**Type:** Integer or null

**Description:** Number of rotated log files to keep. Rotation uses numbered
suffixes like `eddypro_processing.log.1` up to `.N`. Set to 0 or null to
disable rotation.

**Example:**
```yaml
log_backup_count: 5
```

---

### log_eddypro_output

**Type:** Boolean

**Description:** When true, EddyPro stdout/stderr lines are written to the log
handlers (console and file). If false, only pipeline logs are written.

**Example:**
```yaml
log_eddypro_output: true
```

---

### monitoring_enabled

**Type:** Boolean

**Default:** `true`

**Description:** Enable or disable performance monitoring (CPU, memory, and
disk sampling of the EddyPro process tree) during processing.

**Example:**
```yaml
monitoring_enabled: false
```

**Interaction with `metrics_interval_seconds`:**
- When `true` (default), the monitor samples at `metrics_interval_seconds`
  and writes `metrics_*.csv` files per year/scenario.
- When `false`, no metrics files are written and `metrics_interval_seconds`
  is ignored entirely — validation does not require it to be positive.

**CLI Override:** `--monitor` / `--no-monitor` (available on both `run` and
`scenarios`).

---

### cpu_affinity

**Type:** String, list of integers, or null

**Default:** `null` (leave scheduling to the OS)

**Description:** Restricts the run -- and every process it launches, since child
processes inherit affinity -- to a set of logical CPUs.

**Values:**

| Value | Meaning |
|-------|---------|
| `null` | No pinning |
| `performance` | Auto-detect the performance cores and pin to them |
| `[0, 1, 2, ...]` | Pin to these logical CPU indices |

**Why:** Intel hybrid CPUs (12th generation and later) mix performance cores
with efficiency cores, and the OS will park a long-running background job on the
efficiency ones. `eddypro_rp` is single-threaded, so this costs roughly a factor
of two. Measured on an i7-12700K, one year of 10 Hz data:

| | Wall time | CPU % of one core |
|---|---|---|
| Pinned to performance cores | 241 s, 241 s | 102.6% |
| Unpinned | 474 s, 501 s | 96.5-97.8% |

Note the second column: **CPU utilisation is identical**. A demoted run looks
healthy in the bottleneck report. Pinning also removes the variance -- the
pinned runs agreed exactly, the unpinned pair differed by 5.7%.

**Auto-detection:** `performance` derives the split from the core counts.
Performance cores carry two hardware threads and efficiency cores carry one, so
`p_cores = logical - physical`, occupying logical indices `0 .. 2*p_cores-1`.
Where that cannot be determined -- no SMT, or no efficiency cores -- affinity is
left unchanged and a message is logged. On a CPU without efficiency cores there
is nothing to gain, so this is the correct outcome rather than a failure.

**Never fatal:** an unrecognised value is logged and ignored. A failed
optimisation must not stop a multi-hour run.

**CLI Override:** none -- config only.

---

### performance_thresholds

**Type:** Mapping (optional)

**Default:** see table below

**Description:** Tunes how the bottleneck analyser classifies a run. The
defaults assume a **SATA SSD** (~550 MB/s sequential), which is the common case
for the bulk storage EddyPro reads from. The disk limits must match the drive
the input data actually lives on: leave NVMe limits at the SATA default and
ordinary runs are reported as disk-bound; leave mechanical-disk limits at the
SATA default and a genuinely saturated disk is never flagged at all.

| Key | Default | Meaning |
|-----|---------|---------|
| `cpu_high_percent` | 90 | At or above this sustained (p95) **machine-wide** CPU, status is RED |
| `cpu_moderate_percent` | 70 | At or above this, status is YELLOW |
| `cpu_idle_percent` | 40 | Below this, a busy disk is read as the limiting factor |
| `single_core_bound_percent` | 95 | Applied to `cpu_percent_of_core`, where 100 = one core fully busy. At or above this, the run is reported `CPU_SINGLE_CORE` |
| `memory_high_percent` | 85 | System memory use that counts as RED |
| `memory_moderate_percent` | 70 | System memory use that counts as YELLOW |
| `disk_high_mb_per_s` | 450 | Combined read+write throughput counting as RED |
| `disk_moderate_mb_per_s` | 250 | Throughput counting as YELLOW |
| `disk_high_iops` | 20000 | Combined IOPS above which latency is the suspect |

The CPU verdict is judged on `system_cpu_percent` (machine-wide). Each parallel
worker runs its own monitor and sees only its own process tree, so per-process
CPU can never reveal that the machine as a whole is full. Files written by a
monitor that did not record the system column fall back to the normalised
process figure.

Unknown keys are ignored, so a config written for a newer version still loads.

Suggested disk limits by medium:

| Medium | `disk_high_mb_per_s` | `disk_moderate_mb_per_s` | `disk_high_iops` |
|--------|---------------------|--------------------------|------------------|
| NVMe SSD | 3000 | 1500 | 200000 |
| SATA SSD (default) | 450 | 250 | 20000 |
| Mechanical / USB HDD | 150 | 80 | 150 |

On Windows, check which you have with:

```powershell
Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType
Get-Partition | Where-Object DriveLetter | Select-Object DriveLetter, DiskNumber
```

**Example (NVMe):**
```yaml
performance_thresholds:
  disk_high_mb_per_s: 3000
  disk_moderate_mb_per_s: 1500
  disk_high_iops: 200000
```

**CLI Override:** none — config only.

**Notes:**
- Disable for maximum throughput on large batches where the small sampling
  overhead matters, or when you no longer need per-run performance data. See
  [MULTI_YEAR_RUNS.md](MULTI_YEAR_RUNS.md).

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
- If `plotly` is selected but the `plotly` package is not installed, the
  report is still generated: chart sections show a
  "Plotly not installed" note instead of a chart, and a debug-level log
  message records the import failure. There is no automatic switch to `svg`.
  Set `report_charts: svg` (or pass `--report-charts svg`) explicitly if you
  don't have `plotly` installed.

**Scope:** Used for HTML reports generated by both `run` and `scenarios`
(per-scenario reports plus one aggregate comparison report).

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
- [MULTI_YEAR_RUNS.md](MULTI_YEAR_RUNS.md) – Worked multi-year run example
- [SCENARIOS.md](SCENARIOS.md) – Scenario matrix runs
- [REPORTING.md](REPORTING.md) – Understanding reports
