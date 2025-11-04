# EddyPro Batch Processor

A Python CLI tool for automated EddyPro processing with scenario support, performance monitoring, and comprehensive reporting.

## Features

- **Automated batch processing** of eddy covariance data across multiple years
- **Scenario matrix support** for testing parameter combinations (rotation, time lag, detrending, spike removal)
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
```

**Key configuration items:**

- Set `eddypro_executable` to your EddyPro installation path
- Update `input_dir_pattern` and `output_dir_pattern` for your data structure
- Specify `ecmd_file` path for your site metadata
- Ensure your ECMD metadata file is accessible

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

**Solution:** See [CONFIG.md](docs/CONFIG.md) for ECMD format requirements. Ensure your CSV has required columns: `filename`, `date`, `time`, `DOY`, etc.

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

3. **Run a single scenario with specific parameters:**

   ```bash
   eddypro-batch --config config/config.yaml run --site GL-ZaF --years 2021 --rot-meth 1 --tlag-meth 2 --detrend-meth 0 --despike-meth 1
   ```

4. **Test all combinations of parameter scenarios (Cartesian product):**

   This example tests all 16 combinations (2×2×2×2):

   ```bash
   eddypro-batch --config config/config.yaml scenarios --site GL-ZaF --years 2021 --rot-meth 1 3 --tlag-meth 2 4 --detrend-meth 0 1 --despike-meth 0 1
   ```

   **Parameter meanings:**

   - `--rot-meth 1 3` → Rotation methods: 1=Double Rotation (DR), 3=Planar Fit (PF)
   - `--tlag-meth 2 4` → Time lag methods: 2=Constant (CMD), 4=Automatic Optimization (AO)
   - `--detrend-meth 0 1` → Detrending: 0=Block Average (BA), 1=Linear Detrending (LD)
   - `--despike-meth 0 1` → Spike removal: 0=Vickers & Mahrt (1997), 1=Mauder et al. (2013)

   Each scenario runs independently and produces separate output files with unique names (e.g., `scenario_rot1_tlag2_det0_spk1`).

   See [SCENARIOS.md](docs/SCENARIOS.md) for detailed documentation on scenario runs.

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

- **[USAGE.md](docs/USAGE.md)** – Complete CLI usage guide with all command examples and options
- **[CONFIG.md](docs/CONFIG.md)** – Configuration file reference, YAML structure, and ECMD format specifications
- **[SCENARIOS.md](docs/SCENARIOS.md)** – Scenario matrix runs, parameter testing, and naming conventions
- **[REPORTING.md](docs/REPORTING.md)** – Understanding reports, performance metrics, and manifest structure
- **[OUTPUT_FILE_TRACKING.md](docs/OUTPUT_FILE_TRACKING.md)** – Machine-readable output file tracking in manifests
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** – Contributing guidelines, development setup, and testing
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** – System design and module organization
- **[IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md)** – Project roadmap and completed milestones

## Key Capabilities

### Configuration Validation

Catch configuration errors before processing:

```bash
eddypro-batch --config config/config.yaml validate
```

Validates:

- Required config keys and types
- Path existence (EddyPro executable, input directories, ECMD file)
- ECMD schema (required columns, data types)
- Sanity checks (positive values, non-empty fields)

### Scenario Matrix Testing

Test multiple parameter combinations systematically. The `scenarios` command creates a Cartesian product of all parameter values:

```bash
eddypro-batch --config config/config.yaml scenarios --site GL-ZaF --years 2021 --rot-meth 1 3 --tlag-meth 2 4 --detrend-meth 0 1 --despike-meth 0 1
```

This creates 16 scenarios (2×2×2×2) with all combinations:

- Rotation: Double Rotation (1) and Planar Fit (3)
- Time lag: Constant (2) and Automatic Optimization (4)
- Detrending: Block Average (0) and Linear Detrending (1)
- Spike removal: Vickers & Mahrt (0) and Mauder et al. (1)

Each scenario is named uniquely (e.g., `scenario_rot1_tlag2_det0_spk1`) and processed independently. Results are tracked in the run manifest for comparison.

**Note:** Maximum 32 scenarios allowed (configurable via `--max-scenarios`). See [SCENARIOS.md](docs/SCENARIOS.md) for details.

### Performance Monitoring

Track resource usage during processing:

- CPU utilization (process and system)
- Memory usage (RSS, peak)
- Disk I/O (read/write MB, IOPS)
- Processing duration

Metrics are saved per scenario and aggregated in reports.

### Comprehensive Reporting

Generates detailed reports after each run:

- **HTML reports** with interactive Plotly charts (CPU, memory, I/O over time)
- **JSON manifests** (`run_manifest.json`) for programmatic analysis
  - Complete scenario results with success/failure status
  - Machine-readable output file tracking (all EddyPro CSV outputs)
  - Duration, metrics summary, and configuration snapshot
- **Per-scenario metrics** (CSV time series of resource usage)
- **Provenance capture** (config checksum, git SHA, Python environment, package versions)

Reports are saved to `{output_dir}/reports/` by default. See [REPORTING.md](docs/REPORTING.md) and [OUTPUT_FILE_TRACKING.md](docs/OUTPUT_FILE_TRACKING.md) for details.

## Configuration Example

```yaml
eddypro_executable: "C:/Program Files/LI-COR/EddyPro-7.0.9/bin/eddypro_rp.exe"
site_id: GL-ZaF
years_to_process: [2021, 2022, 2023]
input_dir_pattern: "D:/L0_raw/{site_id}/{year}/ec/rflux_csv"
output_dir_pattern: "D:/L1_processed/{site_id}/{year}/ec_rflux"
ecmd_file: "D:/L1_processed/{site_id}/ecmd/{site_id}_ecmd.csv"

multiprocessing: False
max_processes: 16
stream_output: True
log_level: INFO

metrics_interval_seconds: 0.5
report_charts: plotly  # Options: plotly, svg, none
```

See [CONFIG.md](docs/CONFIG.md) for all options and details.

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
