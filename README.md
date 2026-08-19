# EddyPro Batch Processor

A Python CLI tool for automated EddyPro processing with scenario support, performance monitoring, and comprehensive reporting.

## Features

- **Automated batch processing** of eddy covariance data across multiple years
- **Scenario matrix support** for testing parameter combinations (rotation, time lag, detrending, spike removal, high-frequency correction)
- **Performance monitoring** with CPU, memory, and I/O metrics
- **Comprehensive reporting** with interactive charts and machine-readable manifests
- **Multiprocessing** for parallel year processing
- **Configuration validation** to catch errors before processing
- **Flexible configuration** via YAML with CLI overrides

## Quick Start

### Requirements

- Python 3.10 or higher (Python 3.12+ recommended for development)
- [EddyPro](https://www.licor.com/env/products/eddy_covariance/eddypro.html) installed and accessible
- Python packages: `pyyaml`, `psutil`, `plotly` (optional for charts)

### Installation

#### 1. Install EddyPro (Prerequisite)

Download and install EddyPro from [LI-COR's website](https://www.licor.com/env/products/eddy_covariance/eddypro.html):

- **Windows**: Install to default location (`C:\Program Files\LI-COR\EddyPro-X.X.X\`)
- **Linux/macOS**: Install according to LI-COR instructions
- **Note the installation path** - you'll need it for configuration

#### 2. Clone and Setup Python Environment

```bash
git clone <repository-url>
cd eddypro_batch_processor
```

Create virtual environment and install:

**On Windows (PowerShell):**
```powershell
python -m venv venv
   .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

**On Linux/macOS (Bash):**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

#### 3. Configure the Application

```bash
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your paths and settings
```

**Key configuration items:**

- Set `eddypro_executable` to your EddyPro installation path
- Update `input_dir_pattern` and `output_dir_pattern` for your data structure
- Specify `ecmd_file` path for your site metadata
- Ensure your ECMD metadata file is accessible
- Optional: set `log_file` (and rotation settings) to write logs to a file
   and keep EddyPro output (see CONFIG.md)

#### 4. Verify Installation

Test that everything is working:

```bash
# Check CLI is installed
eddypro-batch --help

# Verify version
eddypro-batch --version

# Validate your configuration
eddypro-batch validate --config config/config.yaml
```

### Troubleshooting

#### Common Issues

**EddyPro executable not found:**

```text
Error: EddyPro executable not found at: <path>
```

**Solution:** Check the `eddypro_executable` path in `config.yaml`. Common locations:

- Windows: `C:\Program Files\LI-COR\EddyPro-7.0.9\bin\eddypro_rp.exe`
- Linux: `/opt/eddypro/bin/eddypro_rp`
- macOS: `/Applications/EddyPro.app/Contents/MacOS/eddypro_rp`

**Missing Plotly (charts disabled):**

```text
Warning: Plotly not available, charts disabled
```

**Solution:** Install optional dependencies:

```bash
pip install plotly
```

**ECMD file validation errors:**

```text
Error: Missing required columns in ECMD file
```

**Solution:** See [CONFIG.md](docs/CONFIG.md) for ECMD format requirements. Ensure your CSV has required columns such as `DATE_OF_VARIATION_EF`, `SITEID`, and the sensor metadata fields.

**Permission errors on Windows:**

```text
PermissionError: [Errno 13] Permission denied
```

**Solution:** Run terminal as Administrator, or ensure EddyPro installation directory is accessible.

#### Getting Help

- **Configuration issues**: See [CONFIG.md](docs/CONFIG.md)
- **Usage examples**: See [USAGE.md](docs/USAGE.md)
- **Development setup**: See [DEVELOPMENT.md](docs/DEVELOPMENT.md)

### Basic Usage

**First, activate your virtual environment:**

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Linux/macOS (Bash):**
```bash
source venv/bin/activate
```

---

**Then run commands:**

1. **Validate your configuration:**

   ```bash
   eddypro-batch --config config/config.yaml validate
   ```

2. **Run processing for one or more years:**

   ```bash
   eddypro-batch --config config/config.yaml run --site GL-ZaF --years 2021 2022
   ```

   **Note:** `run` executes `eddypro_rp` followed by `eddypro_fcc` using the same
   local `bin/` copy strategy as `scenarios`. If `eddypro_rp` fails, `eddypro_fcc`
   is skipped.

3. **Process several years with the same settings (multi-year run):**

   ```bash
   eddypro-batch --config config/config.yaml run --site GL-Dsk --years 2020 2021 2022 2023 2024 2025 --mp --max-proc 6
   ```

   See [MULTI_YEAR_RUNS.md](docs/MULTI_YEAR_RUNS.md) for a complete worked
   example (config file and pure-CLI forms, choosing `max_processes`,
   reading the performance bottleneck report).

4. **Test combinations of processing parameters (scenario matrix):**

   ```bash
   eddypro-batch --config config/config.yaml scenarios --site GL-ZaF --years 2021 --rot-meth 1 3 --tlag-meth 2 4 --detrend-meth 0 1 --despike-meth 0 1
   ```

   This tests all 16 combinations (2×2×2×2) of rotation, time lag, detrend,
   and spike-removal methods; add `--hf-meth 1 4` for up to 32. Each
   scenario runs independently and produces its own output directory and
   HTML report. See [SCENARIOS.md](docs/SCENARIOS.md) for the full parameter
   table, naming conventions, and more examples — note that a *scenario*
   run (many parameter combinations, one year) is different from a
   *multi-year* run (one set of parameters, many years) shown above.

5. **Dry-run mode (generate files without executing EddyPro):**

   ```bash
   eddypro-batch --config config/config.yaml run --site GL-ZaF --years 2021 --dry-run
   ```

6. **Check results from last run:**

   ```bash
   eddypro-batch status
   ```

## Documentation

For detailed information, see the `docs/` directory:

- **[MULTI_YEAR_RUNS.md](docs/MULTI_YEAR_RUNS.md)** – Worked multi-year run example (same settings, many years) — start here if that's your use case
- **[USAGE.md](docs/USAGE.md)** – Complete CLI usage guide with all command examples and options
- **[CONFIG.md](docs/CONFIG.md)** – Configuration file reference, YAML structure, and ECMD format specifications
- **[SCENARIOS.md](docs/SCENARIOS.md)** – Scenario matrix runs (parameter combinations), naming conventions
- **[REPORTING.md](docs/REPORTING.md)** – Understanding reports, performance metrics, and manifest structure
- **[OUTPUT_FILE_TRACKING.md](docs/OUTPUT_FILE_TRACKING.md)** – Machine-readable output file tracking in manifests
- **[KNOWN_ISSUES_AND_TODO.md](docs/KNOWN_ISSUES_AND_TODO.md)** – Known issues, gaps, and roadmap items
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** – Contributing guidelines, development setup, and testing
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** – System design and module organization
- **[plan/implemented/IMPROVEMENT_PLAN.md](docs/plan/implemented/IMPROVEMENT_PLAN.md)** – Project roadmap and completed milestones

## Key Capabilities

- **Configuration validation** (`eddypro-batch validate`) — required keys/types, path existence, ECMD schema and sanity checks
- **Multi-year runs** — process several years with identical settings, optionally in parallel (`--mp --max-proc N`); see [MULTI_YEAR_RUNS.md](docs/MULTI_YEAR_RUNS.md)
- **Scenario matrix testing** (`eddypro-batch scenarios`) — Cartesian product of up to 32 parameter combinations by default (`--max-scenarios`); see [SCENARIOS.md](docs/SCENARIOS.md)
- **Performance monitoring** — CPU, memory, and disk I/O sampled from the whole EddyPro process tree, with a CPU/MEMORY/DISK_THROUGHPUT/DISK_IOPS bottleneck classification; toggle with `monitoring_enabled` / `--monitor` / `--no-monitor`
- **Reporting** — HTML reports (for both `run` and `scenarios`, plus an aggregate comparison report for `scenarios`) and JSON `run_manifest.json` with provenance (git SHA, config checksum, EddyPro executable checksum, `sys.argv`)

See [CONFIG.md](docs/CONFIG.md) and [REPORTING.md](docs/REPORTING.md) for full details.

## Configuration Example

```yaml
eddypro_executable: "C:/Program Files/LI-COR/EddyPro-7.0.9/bin/eddypro_rp.exe"
site_id: GL-ZaF
years_to_process: [2021, 2022, 2023]
input_dir_pattern: "D:/L0_raw/{site_id}/{year}/ec/rflux_csv"
output_dir_pattern: "D:/L1_processed/{site_id}/{year}/ec_rflux"
ecmd_file: "D:/L1_processed/{site_id}/ecmd/{site_id}_ecmd.csv"
multiprocessing: False
monitoring_enabled: true
report_charts: plotly
```

This is a short excerpt. The full, authoritative example with every key and
comments is [`config/config.yaml.example`](config/config.yaml.example); see
[CONFIG.md](docs/CONFIG.md) for the key-by-key reference and
[MULTI_YEAR_RUNS.md](docs/MULTI_YEAR_RUNS.md) /
[`examples/multi_year_config.yaml`](examples/multi_year_config.yaml) for a
complete real-world example.

## Contributing

Contributions are welcome! Please see [DEVELOPMENT.md](docs/DEVELOPMENT.md) for:

- Development setup
- Code standards (Black, Ruff, Mypy)
- Testing guidelines (pytest, coverage)
- Git workflow and PR process

## License

[Specify license here]

## Acknowledgments

Built for offline, high-volume eddy covariance data processing with a focus on reproducibility, performance, and maintainability.
