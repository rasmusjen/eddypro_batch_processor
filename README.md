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
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
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
```
Error: EddyPro executable not found at: <path>
```
**Solution:** Check the `eddypro_executable` path in `config.yaml`. Common locations:
- Windows: `C:\Program Files\LI-COR\EddyPro-7.0.9\bin\eddypro_rp.exe`
- Linux: `/opt/eddypro/bin/eddypro_rp`
- macOS: `/Applications/EddyPro.app/Contents/MacOS/eddypro_rp`

**Missing Plotly (charts disabled):**
```
Warning: Plotly not available, charts disabled
```
**Solution:** Install optional dependencies:
```bash
pip install plotly
```

**ECMD file validation errors:**
```
Error: Missing required columns in ECMD file
```
**Solution:** See [CONFIG.md](docs/CONFIG.md) for ECMD format requirements. Ensure your CSV has required columns: `filename`, `date`, `time`, `DOY`, etc.

**Permission errors on Windows:**
```
PermissionError: [Errno 13] Permission denied
```
**Solution:** Run terminal as Administrator, or ensure EddyPro installation directory is accessible.

#### Getting Help

- **Configuration issues**: See [CONFIG.md](docs/CONFIG.md)
- **Usage examples**: See [USAGE.md](docs/USAGE.md)
- **Development setup**: See [DEVELOPMENT.md](docs/DEVELOPMENT.md)

### Basic Usage

1. **Validate your configuration:**
   ```bash
   eddypro-batch validate
   ```

2. **Run processing for one or more years:**
   ```bash
   eddypro-batch run --site GL-ZaF --years 2021 2022
   ```

3. **Test parameter scenarios:**
   ```bash
   eddypro-batch scenarios --rot-meth 1 3 --tlag-meth 2 4 --years 2021
   ```

4. **Check results:**
   ```bash
   eddypro-batch status
   ```

## Documentation

For detailed information, see the `docs/` directory:

- **[USAGE.md](docs/USAGE.md)** – Complete CLI usage guide with examples
- **[CONFIG.md](docs/CONFIG.md)** – Configuration file reference and ECMD format
- **[SCENARIOS.md](docs/SCENARIOS.md)** – Scenario matrix runs and parameter testing
- **[REPORTING.md](docs/REPORTING.md)** – Understanding reports and performance metrics
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** – Contributing guidelines and development setup
- **[IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md)** – Project roadmap and milestones

## Key Capabilities

### Configuration Validation

Catch configuration errors before processing:

```bash
eddypro-batch validate
```

Validates:
- Required config keys and types
- Path existence (EddyPro executable, input directories, ECMD file)
- ECMD schema (required columns, data types)
- Sanity checks (positive values, non-empty fields)

### Scenario Matrix Testing

Test multiple parameter combinations systematically:

```bash
eddypro-batch scenarios \
  --rot-meth 1 3 \
  --tlag-meth 2 4 \
  --site GL-ZaF \
  --years 2021
```

Creates 4 scenarios with all combinations of rotation methods (DR, PF) and time lag methods (CMD, AO).

### Performance Monitoring

Track resource usage during processing:
- CPU utilization (process and system)
- Memory usage (RSS, peak)
- Disk I/O (read/write MB, IOPS)
- Processing duration

Metrics are saved per scenario and aggregated in reports.

### Comprehensive Reporting

Generates:
- **HTML reports** with interactive Plotly charts
- **JSON manifests** for programmatic analysis
- **Per-scenario metrics** (CSV time series)
- **Provenance capture** (config hash, git SHA, software versions)

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
