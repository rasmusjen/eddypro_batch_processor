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

- Python 3.12 or higher
- [EddyPro](https://www.licor.com/env/products/eddy_covariance/eddypro.html) installed
- Python packages: `pyyaml`, `psutil`, `plotly` (optional for charts)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd eddypro_batch_processor
   ```

2. Create virtual environment and install:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   pip install -e .
   ```

3. Configure the application:
   - Copy and edit `config/config.yaml` with your paths and settings
   - Ensure your ECMD metadata file is accessible

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
