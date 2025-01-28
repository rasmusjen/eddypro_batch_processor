# EddyPro Batch Processor

## Description

A robust Python script to automate and manage EddyPro processing tasks across multiple years and sites, leveraging multiprocessing for enhanced performance.

## Features

- **Configurable multiprocessing** with adjustable CPU core usage.
- **Dynamic logging** with adjustable verbosity.
- **Flexible configuration** via YAML files.
- **Automated project file modifications** and processing.
- **Real-time progress tracking** with estimated time remaining.
- Supports both **sequential and parallel processing** modes.

## Requirements

- **Python** 3.6 or higher
- [EddyPro](https://www.licor.com/env/products/eddy_covariance/eddypro.html) installed and accessible at the specified path in `config/config.yaml`
- **PyYAML** library (`pip install pyyaml`)

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/eddypro_batch_processor.git
    ```

2. **Navigate to the project directory:**

    ```bash
    cd eddypro_batch_processor
    ```

3. **Install the required Python packages:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure the application:**
    - Rename `config/config.example.yaml` to `config/config.yaml`
    - Update the settings in `config.yaml` as per your environment.

## Configuration

### `config.yaml`

The `config.yaml` file is the primary configuration file for the EddyPro Batch Processor. It allows you to customize various aspects of the batch processing, including:

- **EddyPro Path:**

    ```yaml
    eddypro_path: "C:/Program Files/EddyPro/EddyPro.exe"
    ```

    Path to the EddyPro executable.

- **Processing Settings:**

    ```yaml
    processing_mode: "parallel"  # Options: "sequential", "parallel"
    cpu_cores: 4
    ```

    Configure the processing mode and the number of CPU cores to utilize for multiprocessing.

- **Logging:**

    ```yaml
    logging:
      level: "INFO"  # Options: "DEBUG", "INFO", "WARNING", "ERROR"
      log_file: "logs/eddypro_processor.log"
    ```

    Set the logging verbosity and specify the log file location.

- **Directories:**

    ```yaml
    directories:
      projects: "projects/"
      results: "results/"
    ```

    Define paths for project files and output results.

### `_ecmd.csv`

The `_ecmd.csv` file is a critical component used by EddyPro Batch Processor to manage and track processing tasks. It contains metadata and configuration for each EddyPro project, including:

- **Project ID:** Unique identifier for each EddyPro project.
- **Site Information:** Details about the site location and relevant parameters.
- **Data Paths:** Paths to input data files required for processing.
- **Processing Parameters:** Specific settings and parameters to be applied during EddyPro execution.

**Example Structure:**

```csv
project_id,site,input_data,parameters
001,SiteA,data/siteA/data1.csv,--param1 value1
002,SiteB,data/siteB/data2.csv,--param2 value2
```

This CSV file allows the batch processor to iterate through each project, apply the necessary configurations, and execute EddyPro accordingly.

## Usage

1. **Prepare the `_ecmd.csv` file** with all your project details.
2. **Run the batch processor:**

    ```bash
    python eddypro_batch_processor.py
    ```

3. **Monitor the logs** in the specified log file for real-time updates and progress tracking.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.
