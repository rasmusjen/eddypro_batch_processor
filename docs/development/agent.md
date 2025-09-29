# Agent Workflow & Development Instructions

## 1. Overview

This document provides comprehensive guidelines for automated agents, developers, and maintainers working on the EddyPro Batch Processor project. It establishes coding standards, operational procedures, and workflows to ensure consistent, high-quality development.

## 2. Agent Operational Guidelines

### 2.1 Primary Responsibilities
- **Code Quality Assurance**: Maintain type safety, proper error handling, and comprehensive documentation
- **Performance Monitoring**: Implement and validate performance optimization features
- **Testing Automation**: Ensure all code changes include appropriate tests
- **Configuration Management**: Validate configuration changes and maintain backward compatibility

### 2.2 Approval Workflows
- **Autonomous Actions**: Code formatting, dependency updates, minor bug fixes, documentation updates
- **Human-in-the-loop Required**: Architecture changes, new feature implementation, configuration schema changes, performance-critical modifications

### 2.3 Error Handling & Escalation
- **Level 1 - Automatic**: Retry failed builds, update dependencies, fix linting issues
- **Level 2 - Alert**: Test failures, configuration validation errors, performance regressions
- **Level 3 - Escalate**: Security vulnerabilities, data corruption risks, major functionality breaks

## 3. Development Standards

### 3.1 Code Quality Requirements
```python
# Required: Type hints for all functions
def process_year(args: Tuple[int, str, str, str, Path, bool, Path, Path]) -> int:
    """
    Process a single year for EddyPro batch processing.
    
    Args:
        args: Tuple containing all necessary parameters
        
    Returns:
        Number of raw files processed for the year
        
    Raises:
        FileNotFoundError: If required input files are missing
        ConfigurationError: If configuration is invalid
    """
    pass

# Required: Comprehensive error handling
try:
    result = risky_operation()
except SpecificException as e:
    logging.error(f"Operation failed: {e}")
    return error_code
```

### 3.2 Performance Standards
- **Memory Usage**: Functions should not exceed 1GB memory usage per process
- **CPU Efficiency**: Multiprocessing should scale linearly up to available cores
- **I/O Optimization**: Batch file operations where possible, avoid excessive small reads/writes
- **Resource Monitoring**: All long-running operations must include progress tracking

### 3.3 Testing Requirements
- **Unit Tests**: Minimum 80% code coverage for core functions
- **Integration Tests**: End-to-end workflow testing with sample data
- **Performance Tests**: Benchmark key operations (file processing, EddyPro execution)
- **Cross-platform Tests**: Windows and Linux compatibility verification

## 4. Multiprocessing & Parallelization Strategy

### 4.1 Current Architecture
- **Process Level**: Site-year combinations run in separate processes
- **Thread Safety**: EddyPro executable instances are process-isolated
- **Resource Management**: CPU core allocation managed via `max_processes` config

### 4.2 EddyPro Parallel Execution Investigation _(Development Priority)_

**Research Questions**:
1. Can multiple EddyPro instances run simultaneously on the same machine?
2. Are there shared resource conflicts (temp files, registry, memory)?
3. What's the optimal process-to-core ratio for EddyPro workloads?

**Testing Protocol**:
```python
def test_eddypro_parallel_execution():
    """
    Test plan for EddyPro parallel processing validation:
    
    1. Launch 2 EddyPro instances with different project files
    2. Monitor system resources (CPU, memory, I/O)
    3. Verify output file integrity
    4. Measure total processing time vs sequential
    5. Test with increasing parallel instances (2, 4, 8, 16)
    6. Identify optimal parallelization level
    """
    pass
```

**Implementation Strategy**:
- **Phase 1**: Validate EddyPro can run multiple instances
- **Phase 2**: Implement thread-based execution within site-year processing
- **Phase 3**: Optimize resource allocation based on testing results

### 4.3 Performance Monitoring Implementation

**Per-job Resource Tracking**:
```python
import psutil
import time
from dataclasses import dataclass

@dataclass
class ProcessMetrics:
    site_id: str
    year: int
    start_time: float
    end_time: float
    cpu_percent: float
    memory_mb: float
    io_read_mb: float
    io_write_mb: float
    files_processed: int

def monitor_process_performance(func):
    """Decorator to track resource usage for processing functions."""
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        start_metrics = process.as_dict(['cpu_percent', 'memory_info', 'io_counters'])
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        end_metrics = process.as_dict(['cpu_percent', 'memory_info', 'io_counters'])
        
        # Log performance metrics
        # Store in database/file for analysis
        
        return result
    return wrapper
```

## 5. Configuration Management

### 5.1 Schema Validation
```python
from pydantic import BaseModel, validator
from typing import List, Optional

class EddyProConfig(BaseModel):
    eddypro_executable: str
    site_id: str
    years_to_process: List[int]
    input_dir_pattern: str
    output_dir_pattern: str
    ecmd_file: str
    multiprocessing: bool = False
    max_processes: int = 1
    stream_output: bool = True
    log_level: str = "INFO"
    
    @validator('eddypro_executable')
    def executable_exists(cls, v):
        if not Path(v).exists():
            raise ValueError(f'EddyPro executable not found: {v}')
        return v
    
    @validator('max_processes')
    def valid_process_count(cls, v):
        if v < 1 or v > multiprocessing.cpu_count():
            raise ValueError(f'max_processes must be between 1 and {multiprocessing.cpu_count()}')
        return v
```

### 5.2 Configuration Evolution
- **Backward Compatibility**: Support legacy configuration formats for 2 major versions
- **Migration Scripts**: Automated migration tools for configuration updates
- **Validation**: Comprehensive validation with helpful error messages

## 6. Scheduled Processing Implementation

### 6.1 Daily Processing Architecture
```python
import schedule
import time
from datetime import datetime, timedelta

class ScheduledProcessor:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        self.last_processed = self._load_checkpoint()
    
    def daily_processing_job(self):
        """
        Daily processing workflow:
        1. Scan for new data files since last run
        2. Identify incomplete processing runs
        3. Process new data with retry mechanisms
        4. Update processing checkpoint
        5. Generate daily summary report
        """
        pass
    
    def setup_schedule(self):
        """Configure daily processing schedule."""
        schedule.every().day.at("02:00").do(self.daily_processing_job)
        schedule.every().day.at("14:00").do(self._health_check)
        
    def run_scheduler(self):
        """Main scheduler loop."""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
```

### 6.2 Retry Mechanism Design
```python
from functools import wraps
import time
import random

def retry_on_failure(max_attempts=3, backoff_factor=2, exceptions=(Exception,)):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        exceptions: Tuple of exceptions that trigger retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    wait_time = (backoff_factor ** attempt) + random.uniform(0, 1)
                    logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.2f}s...")
                    time.sleep(wait_time)
            
        return wrapper
    return decorator

@retry_on_failure(max_attempts=3, exceptions=(subprocess.CalledProcessError, FileNotFoundError))
def run_eddypro_with_retry(project_file, eddypro_executable, stream_output):
    """EddyPro execution with automatic retry capability."""
    return run_eddypro(project_file, eddypro_executable, stream_output)
```

## 7. Operational Procedures

### 7.1 Deployment Checklist
- [ ] Validate all configuration files
- [ ] Verify EddyPro executable accessibility
- [ ] Test with sample dataset
- [ ] Configure logging and monitoring
- [ ] Set up scheduled processing (if applicable)
- [ ] Verify backup and recovery procedures

### 7.2 Monitoring & Alerting
- **Health Checks**: Daily processing status, disk space, error rates
- **Performance Metrics**: Processing throughput, resource utilization
- **Alert Conditions**: Failed processing runs, configuration errors, resource exhaustion

### 7.3 Maintenance Procedures
- **Weekly**: Log file rotation, temporary file cleanup
- **Monthly**: Performance trend analysis, dependency updates
- **Quarterly**: Full system health review, capacity planning

## 8. Development Workflow

### 8.1 Feature Development Process
1. **Requirements Analysis**: Review specs.md and plan.md
2. **Design Review**: Architecture impact assessment
3. **Implementation**: Follow coding standards and testing requirements
4. **Performance Testing**: Validate performance impact
5. **Documentation Update**: Update relevant documentation
6. **Code Review**: Peer review before merge

### 8.2 Git Workflow
- **Feature Branches**: `feature/performance-monitoring`, `feature/scheduled-processing`
- **Commit Messages**: Follow conventional commit format
- **Pull Requests**: Include test results and performance metrics
- **Code Review**: Required for all changes to main branch

### 8.3 Release Management
- **Semantic Versioning**: MAJOR.MINOR.PATCH format
- **Changelog**: Detailed change documentation
- **Backward Compatibility**: Maintain for configuration and API
- **Migration Guides**: For breaking changes

---

## Document Status
- **Version**: 1.0
- **Last Updated**: September 23, 2025
- **Next Review**: When implementing new features outlined in plan.md
