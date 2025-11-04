# Scenario Matrix Runs

This document explains how to use the `scenarios` command to test multiple parameter combinations efficiently.

## Overview

The `scenarios` command allows you to run a Cartesian product of EddyPro processing parameters, enabling systematic testing of different configurations. This is useful for:

- Sensitivity analysis of processing methods
- Determining optimal parameter combinations for your site
- Comparing different flux calculation approaches
- Quality assurance and method validation

## Supported Parameters

The following EddyPro INI parameters can be varied in scenario runs:

| Parameter | INI Section | INI Key | Valid Values | Description |
|-----------|-------------|---------|--------------|-------------|
| Rotation Method | `[RawProcess_Settings]` | `rot_meth` | 1, 3 | 1=DR (double rotation), 3=PF (planar fit) |
| Time Lag Method | `[RawProcess_Settings]` | `tlag_meth` | 2, 4 | 2=CMD (constant minimum delay), 4=AO (automatic optimization) |
| Detrend Method | `[RawProcess_Settings]` | `detrend_meth` | 0, 1 | 0=BA (block averaging), 1=LD (linear detrending) |
| Spike Removal | `[RawProcess_ParameterSettings]` | `despike_meth` | 0, 1 | 0=VM97 (Vickers & Mahrt 1997), 1=M13 (Mauder et al. 2013) |
| High-Frequency Correction | `[Project]` | `hf_meth` | 1, 4 | 1=Moncrieff et al. (1997) analytic, 4=Fratini et al. (2012) in situ/analytic |

## Usage

Basic syntax:

```bash
eddypro-batch scenarios [PARAMETER_OPTIONS] --site SITE_ID --years YEAR [YEAR ...]
```

You must specify at least one parameter with **multiple values** to create a scenario matrix.

## Examples

### Simple Scenarios

**Test two rotation methods:**

```bash
eddypro-batch scenarios --rot-meth 1 3 --site GL-ZaF --years 2021
```

This creates 2 scenarios:
- Scenario 1: `rot_meth=1`
- Scenario 2: `rot_meth=3`

### Cartesian Products

**Test rotation × time lag (4 scenarios):**

```bash
eddypro-batch scenarios --rot-meth 1 3 --tlag-meth 2 4 --site GL-ZaF --years 2021
```

This creates 4 scenarios:
- `rot1_tlag2`: `rot_meth=1`, `tlag_meth=2`
- `rot1_tlag4`: `rot_meth=1`, `tlag_meth=4`
- `rot3_tlag2`: `rot_meth=3`, `tlag_meth=2`
- `rot3_tlag4`: `rot_meth=3`, `tlag_meth=4`

**Test all four parameters (16 scenarios):**

```bash
eddypro-batch scenarios \
  --rot-meth 1 3 \
  --tlag-meth 2 4 \
  --detrend-meth 0 1 \
  --despike-meth 0 1 \
  --site GL-ZaF \
  --years 2021
```

This creates 2 × 2 × 2 × 2 = 16 scenarios with all possible combinations.

**Test all five parameters (32 scenarios - maximum):**

```bash
eddypro-batch scenarios \
  --rot-meth 1 3 \
  --tlag-meth 2 4 \
  --detrend-meth 0 1 \
  --despike-meth 0 1 \
  --hf-meth 1 4 \
  --site GL-ZaF \
  --years 2021
```

This creates 2 × 2 × 2 × 2 × 2 = 32 scenarios with all possible combinations (reaches the default limit).

## Naming Conventions

### Scenario Suffixes

Each scenario receives a unique suffix based on its parameter values:

```
_rot{R}_tlag{T}_det{D}_spk{S}_hf{H}
```

Where:
- `R` = rotation method value
- `T` = time lag method value
- `D` = detrend method value
- `S` = despike method value
- `H` = high-frequency correction method value

Only parameters that vary across scenarios are included in the suffix.

**Examples:**

- If only `rot_meth` varies: `_rot1`, `_rot3`
- If `rot_meth` and `tlag_meth` vary: `_rot1_tlag2`, `_rot1_tlag4`, `_rot3_tlag2`, `_rot3_tlag4`
- All four vary: `_rot1_tlag2_det0_spk0`, `_rot1_tlag2_det0_spk1`, etc.

### Project Files

Each scenario generates a unique EddyPro project file:

```
{site_id}_{year}{suffix}.eddypro
```

Example:
```
GL-ZaF_2021_rot1_tlag2.eddypro
GL-ZaF_2021_rot3_tlag4.eddypro
```

### Output Directories

Scenario outputs are written to subdirectories:

```
{output_dir_pattern}/{site_id}/{year}/{suffix}/
```

Example structure:
```
data/processed/GL-ZaF/2021/
├── _rot1_tlag2/
│   ├── eddypro_full_output_2021.csv
│   └── ...
├── _rot3_tlag2/
│   ├── eddypro_full_output_2021.csv
│   └── ...
└── reports/
    ├── run_manifest.json
    ├── run_report.html
    └── ...
```

## Scenario Limits

### Hard Cap

**Default limit: 32 scenarios**

The `scenarios` command enforces a hard cap to prevent resource exhaustion. If the Cartesian product exceeds the limit, the run aborts with an error:

```
ERROR: Scenario count exceeds maximum limit.
  Requested: 64 scenarios
  Limit: 32
  → Narrow your parameter choices or increase --max-scenarios
```

### Adjusting the Limit

You can raise the limit with `--max-scenarios`:

```bash
eddypro-batch scenarios --rot-meth 1 3 --max-scenarios 64 --years 2021
```

⚠️ **Warning:** Large scenario counts can:
- Consume significant disk space
- Take hours or days to process
- Overwhelm system resources

Always consider:
- Available CPU cores and memory
- Disk space for outputs
- Total processing time (scenarios × year processing time)

## Output Structure

Each scenario run produces:

### Per-Scenario Artifacts

Located in `{output_dir}/{suffix}/`:

- EddyPro output files (CSV, metadata, QC flags)
- Processing logs
- `manifest.json` – scenario metadata and metrics
- `metrics.csv` – performance time series (CPU, memory, I/O)

### Aggregated Reports

Located in `{output_dir}/reports/`:

- `run_manifest.json` – Summary of all scenarios
- `run_report.html` – Interactive report with charts
- Scenario comparison tables and visualizations

See [REPORTING.md](REPORTING.md) for details on report structure and interpretation.

## Manifest Schema

Each scenario's `manifest.json` contains:

```json
{
  "scenario_id": "rot1_tlag2_det0_spk0",
  "parameters": {
    "rot_meth": 1,
    "tlag_meth": 2,
    "detrend_meth": 0,
    "despike_meth": 0
  },
  "project_file": "/path/to/GL-ZaF_2021_rot1_tlag2_det0_spk0.eddypro",
  "output_dir": "/path/to/output/_rot1_tlag2_det0_spk0",
  "timestamps": {
    "start": "2025-10-02T10:00:00",
    "end": "2025-10-02T10:15:32"
  },
  "success": true,
  "exit_code": 0,
  "metrics": {
    "duration_seconds": 932.1,
    "cpu_percent_avg": 45.2,
    "memory_rss_peak_mb": 1024.5,
    "disk_read_mb": 512.3,
    "disk_write_mb": 128.7
  }
}
```

## Best Practices

### Start Small

Begin with a limited set of scenarios to verify the workflow:

```bash
# Test with just 2 scenarios first
eddypro-batch scenarios --rot-meth 1 3 --years 2021
```

### Use Dry Run

Preview what will be generated without executing:

```bash
eddypro-batch scenarios --rot-meth 1 3 --tlag-meth 2 4 --dry-run --years 2021
```

### Monitor Resources

Track CPU, memory, and disk usage during scenario runs:

- Check `metrics.csv` for per-scenario resource usage
- Use system monitoring tools (Task Manager, `htop`, `psutil`)
- Ensure adequate disk space before starting

### Validate First

Always validate your config before running scenarios:

```bash
eddypro-batch validate
```

### One Year at a Time

For large scenario matrices, process one year at a time:

```bash
eddypro-batch scenarios --rot-meth 1 3 --tlag-meth 2 4 --years 2021
eddypro-batch scenarios --rot-meth 1 3 --tlag-meth 2 4 --years 2022
```

### Naming Clarity

Use descriptive parameter combinations that align with your research questions:

```bash
# Compare rotation methods only
eddypro-batch scenarios --rot-meth 1 3 --years 2021

# Compare detrending approaches
eddypro-batch scenarios --detrend-meth 0 1 --years 2021
```

## Troubleshooting

### Scenario Limit Exceeded

**Error:**
```
ERROR: Scenario count exceeds maximum limit (64 > 32)
```

**Solution:**
- Reduce parameter combinations
- Increase limit with `--max-scenarios 64`
- Split into multiple runs (e.g., by year)

### Invalid Parameter Values

**Error:**
```
ERROR: Invalid scenario parameter: rot_meth=2
```

**Solution:**
- Check allowed values in the table above
- Only use documented parameter values

### Disk Space Exhausted

**Symptom:** Scenario runs fail partway through

**Solution:**
- Check available disk space before starting
- Reduce number of scenarios
- Increase storage allocation
- Clean up old outputs

### Memory Issues

**Symptom:** System becomes unresponsive or scenarios fail with memory errors

**Solution:**
- Reduce `--max-proc` if using multiprocessing
- Monitor memory with `metrics.csv`
- Process fewer scenarios at a time
- Increase system RAM

## Advanced Usage

### Combine with Custom Reports Directory

```bash
eddypro-batch scenarios \
  --rot-meth 1 3 \
  --tlag-meth 2 4 \
  --reports-dir /custom/reports/scenario-comparison \
  --years 2021
```

### Adjust Performance Monitoring

```bash
eddypro-batch scenarios \
  --rot-meth 1 3 \
  --metrics-interval 1.0 \
  --years 2021
```

### Process Multiple Years

```bash
eddypro-batch scenarios \
  --rot-meth 1 3 \
  --tlag-meth 2 4 \
  --years 2020 2021 2022
```

This processes each year with all scenario combinations.

## See Also

- [USAGE.md](USAGE.md) – General CLI usage
- [CONFIG.md](CONFIG.md) – Configuration options
- [REPORTING.md](REPORTING.md) – Understanding reports and manifests
