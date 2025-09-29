# EddyPro Batch Processor: Project Specification

## 1. Overview

**EddyPro Batch Processor** is a robust Python application designed to automate and manage EddyPro processing tasks across multiple years and sites. This production-grade tool serves scientists and data engineers working with eddy covariance data who require scalable, reliable, and efficient batch or near-real-time processing capabilities.

The system leverages multiprocessing for enhanced performance and provides comprehensive metadata management, making it suitable for large-scale, multi-site, multi-year environmental studies.

## 2. Business Goals & Context

- **Primary Goal**: Automate the setup and execution of EddyPro projects, eliminating manual configuration overhead for large datasets
- **Secondary Goals**: 
  - Standardize data processing workflows across research teams
  - Provide performance monitoring and bottleneck identification
  - Enable scalable processing from single-site studies to multi-site networks
  - Support both retrospective batch processing and (future) near-real-time workflows

## 3. Target Users

- **Primary**: Environmental scientists working with eddy covariance flux tower data
- **Secondary**: Data engineers managing environmental data pipelines
- **Tertiary**: Research teams coordinating long-term, multi-site field campaigns

## 4. Core Features & Capabilities

### 4.1 Data Processing
- **Batch Processing**: High-throughput processing of multiple years/sites simultaneously
- **Configurable Multiprocessing**: Adjustable CPU core usage (1-16+ cores) with intelligent core detection
- **Sequential/Parallel Modes**: Flexible execution strategies based on system resources
- **Progress Tracking**: Real-time progress monitoring with estimated time remaining

### 4.2 Configuration Management
- **YAML-based Configuration**: Human-readable, version-controllable configuration files
- **Template-driven Project Setup**: Automated EddyPro project file generation from templates
- **Metadata Management**: Dynamic metadata file generation from CSV inputs (`_ecmd.csv`)
- **Path Pattern Support**: Flexible directory structure with `{year}` and `{site_id}` placeholders

### 4.3 EddyPro Integration
- **Automated Executable Detection**: Cross-platform support (Windows/Linux)
- **Two-stage Processing**: Orchestrates both `eddypro_rp` and `eddypro_fcc` executables
- **Stream Output Control**: Optional real-time output streaming or quiet operation
- **Error Handling**: Comprehensive error detection and logging for failed processes

### 4.4 Monitoring & Logging
- **Dynamic Logging**: Adjustable verbosity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Rotating Log Files**: Persistent logging with automatic file rotation
- **Performance Metrics**: Processing time tracking per project and overall runtime
- **Resource Monitoring**: _(Planned)_ CPU, memory, and I/O bottleneck identification

## 5. System Architecture

### 5.1 Modular Design
```
src/
├── eddypro_batch_processor.py  # Main orchestration logic
├── __init__.py                 # Package exports
└── [future modules]            # Performance monitoring, cloud integration

config/
├── config.yaml                 # Runtime configuration
├── EddyProProject_template.ini # EddyPro project template
└── metadata_template.ini       # Metadata template

data/
├── raw/{site_id}/{year}/       # Input data structure
└── processed/{site_id}/{year}/ # Output data structure
```

### 5.2 Core Components
1. **Configuration Manager** (`load_config`, `validate_config`)
2. **Data Discovery** (`get_raw_files`) 
3. **Project Builder** (`build_project_file`, `build_metadata_file`)
4. **Process Orchestrator** (`run_eddypro`, `run_subprocess`)
5. **Multiprocessing Controller** (`process_year`, main workflow)
6. **Logging System** (`setup_logging`)

### 5.3 Data Flow
```
1. Load YAML config + CSV metadata
2. Discover raw data files per site/year
3. Generate EddyPro project files from templates
4. Execute EddyPro processing (rp → fcc)
5. Monitor progress and log results
```

## 6. Performance Requirements

### 6.1 Processing Performance
- **Throughput**: Must efficiently process multiple years of data (typically 5-20 years per site)
- **Scalability**: Linear performance scaling with available CPU cores
- **Memory Efficiency**: Should handle large datasets without memory overflow
- **I/O Optimization**: Efficient handling of both local and network storage

### 6.2 Performance Monitoring _(Current & Planned)_
- **Current**: Basic timing metrics (elapsed time, estimated remaining time)
- **Planned**: Detailed diagnostics to identify bottlenecks:
  - CPU utilization per process
  - Memory usage patterns
  - Disk I/O wait times
  - Network latency (for remote storage)
  - Bottleneck classification (CPU-bound vs I/O-bound vs memory-bound)

### 6.3 Storage Support
- **Local Drives**: Full support for local SSD/HDD storage
- **Network Drives**: Tested with mapped network drives and UNC paths
- **Cloud Storage**: _(Future)_ Planned support for S3, Azure Blob, Google Cloud Storage

## 7. Technical Requirements

### 7.1 System Requirements
- **Python**: 3.6+ (actively tested on 3.12+)
- **Operating Systems**: Windows 10/11, Linux (Ubuntu 18.04+)
- **Memory**: 4GB minimum, 16GB+ recommended for large datasets
- **Storage**: Variable (depends on dataset size), requires ~2x raw data size for processing

### 7.2 Dependencies
- **Core**: PyYAML, pandas, configparser, multiprocessing
- **Development**: types-PyYAML, pandas-stubs, pytest
- **External**: EddyPro software suite (LI-COR)

### 7.3 Configuration Schema
```yaml
# Required parameters
eddypro_executable: str          # Path to EddyPro binary
site_id: str                     # Site identifier
years_to_process: list[int]      # Years to process
input_dir_pattern: str           # Input path template
output_dir_pattern: str          # Output path template
ecmd_file: str                   # Metadata CSV file path

# Optional parameters
multiprocessing: bool            # Enable parallel processing
max_processes: int               # CPU core limit
stream_output: bool              # Real-time output display
log_level: str                   # Logging verbosity
```

## 8. Extensibility & Future Roadmap

### 8.1 Near-term Enhancements
- **Performance Profiling**: Detailed system resource monitoring
- **Advanced Error Recovery**: Automatic retry mechanisms for failed processes
- **Configuration Validation**: Enhanced YAML schema validation
- **Unit Testing**: Comprehensive test coverage

### 8.2 Future Capabilities
- **Near-real-time Processing**: Streaming data ingestion and processing
- **Cloud Integration**: Native support for cloud storage and compute
- **Web Interface**: Optional web dashboard for monitoring and control
- **API Layer**: RESTful API for programmatic control
- **Distributed Processing**: Multi-node processing for very large datasets

## 9. Non-Functional Requirements

### 9.1 Reliability
- **Error Handling**: Graceful degradation with comprehensive error logging
- **Data Integrity**: Checksums and validation for processed outputs
- **Process Recovery**: Ability to resume interrupted processing runs

### 9.2 Maintainability
- **Code Quality**: Type hints, docstrings, and consistent formatting
- **Modular Architecture**: Clear separation of concerns for easy testing/extension
- **Documentation**: Comprehensive inline and external documentation

### 9.3 Usability
- **Configuration**: Simple YAML-based setup with sensible defaults
- **Logging**: Clear, actionable error messages and progress indicators
- **Cross-platform**: Consistent behavior across Windows and Linux

### 9.4 Security _(Future)_
- **Access Control**: Authentication for web interface
- **Data Privacy**: Encryption for sensitive environmental data
- **Audit Trail**: Comprehensive logging of all processing activities

## 10. Testing Strategy

### 10.1 Current Testing
- **Manual Testing**: Ad-hoc testing with sample datasets
- **Import Testing**: Verification that modules can be imported successfully

### 10.2 Planned Testing
- **Unit Tests**: Test individual functions and modules
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Benchmarking and regression testing
- **Cross-platform Tests**: Windows and Linux compatibility verification

---

## Document Status
- **Version**: 1.0
- **Last Updated**: September 23, 2025
- **Status**: Production system with planned enhancements
- **Next Review**: Quarterly or upon major feature additions
