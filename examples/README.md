# Examples Directory

This directory contains example configurations and sample data to help you get started with the EddyPro Batch Processor.

## Contents

- **`config.yaml`** - Basic configuration example
- **`sample_ecmd.csv`** - Example ECMD metadata file format
- **`basic_project.ini`** - Minimal EddyPro project configuration
- **`README.md`** - This file

## Quick Start

1. Copy `config.yaml` to your project's `config/` directory
2. Modify the paths and settings to match your environment
3. Ensure your ECMD file follows the format shown in `sample_ecmd.csv`
4. Run the processor with your configuration

## Configuration Examples

### Basic Setup

```bash
# Copy example config
cp examples/config.yaml config/config.yaml

# Edit paths for your system
# Update: eddypro_executable, input_dir_pattern, output_dir_pattern, ecmd_file

# Run processing
eddypro-batch run
```

### Testing with Sample Data

If you want to test with the provided sample data:

1. Place some CSV files in `data/raw/test-site/2023/`
2. Use the example config with `site_id: test-site` and `years_to_process: [2023]`
3. The sample ECMD format shows the required metadata structure

## File Descriptions

### config.yaml

Basic configuration showing:

- EddyPro executable path (update for your installation)
- Site and year selection
- Input/output directory patterns
- Processing options (multiprocessing, logging, etc.)

### sample_ecmd.csv

Example ECMD (Extended Continuous Measurement Data) file showing:

- Required column headers
- Sample metadata entries
- Proper formatting and data types

### basic_project.ini

Minimal EddyPro project file template showing essential settings.

## Getting Help

- See the main [README.md](../README.md) for installation and setup
- Check [docs/CONFIG.md](../docs/CONFIG.md) for detailed configuration options
- Review [docs/USAGE.md](../docs/USAGE.md) for complete CLI usage examples
- Visit [docs/](../docs/) for comprehensive documentation
