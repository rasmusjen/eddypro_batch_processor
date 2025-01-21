# EddyPro Batch Processor

## Description

A robust Python script to automate and manage EddyPro processing tasks across multiple years and sites, leveraging multiprocessing for enhanced performance.

## Features

- Configurable multiprocessing with adjustable CPU core usage.
- Dynamic logging with adjustable verbosity.
- Flexible configuration via YAML files.
- Automated project file modifications and processing.
- Real-time progress tracking with estimated time remaining.
- Supports both sequential and parallel processing modes.

## Requirements

- Python 3.6 or higher
- [EddyPro](https://www.licor.com/env/products/eddy_covariance/eddypro.html) installed and accessible at the specified path in `config/config.yaml`
- PyYAML library (`pip install pyyaml`)

## Installation

1. **Clone the repository:**

    