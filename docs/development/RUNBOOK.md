# EddyPro Batch Processor - Operations Runbook

## 1. Overview

This runbook provides operational procedures for deploying, monitoring, and maintaining the EddyPro Batch Processor in production environments. It serves as a reference for system administrators, DevOps engineers, and on-call personnel.

## 2. System Architecture Overview

### 2.1 Components
- **Main Application**: `eddypro_batch_processor.py`
- **Configuration**: YAML-based configuration files
- **Data Storage**: Local or network file systems
- **Logging**: Rotating log files in `logs/` directory
- **External Dependency**: EddyPro software suite

### 2.2 File Structure
```
eddypro_batch_processor/
├── src/eddypro_batch_processor.py     # Main application
├── config/
│   ├── config.yaml                    # Runtime configuration
│   ├── EddyProProject_template.ini    # EddyPro project template
│   └── metadata_template.ini          # Metadata template
├── data/
│   ├── raw/{site_id}/{year}/          # Input data
│   └── processed/{site_id}/{year}/    # Output data
└── logs/                              # Application logs
```

## 3. Deployment Procedures

### 3.1 Initial Deployment

#### Prerequisites
- Python 3.6+ installed
- EddyPro software installed and licensed
- Sufficient disk space for data processing
- Network access to data sources (if applicable)

#### Deployment Steps
```bash
# 1. Clone repository
git clone https://github.com/rasmusjen/eddypro_batch_processor.git
cd eddypro_batch_processor

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure application
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with site-specific settings

# 5. Verify installation
python src/eddypro_batch_processor.py --help

# 6. Test with sample data
python src/eddypro_batch_processor.py --config config/config.yaml
```

#### Configuration Validation
```bash
# Validate configuration file
python -c "
from src.eddypro_batch_processor import load_config, validate_config
config = load_config('config/config.yaml')
validate_config(config)
print('Configuration valid')
"
```

### 3.2 Production Deployment Checklist

- [ ] **Environment Setup**
  - [ ] Python environment configured
  - [ ] All dependencies installed
  - [ ] EddyPro executable accessible
  - [ ] Data directories mounted/accessible

- [ ] **Configuration**
  - [ ] config.yaml customized for environment
  - [ ] Input/output paths verified
  - [ ] Logging configuration set
  - [ ] Performance parameters tuned

- [ ] **Testing**
  - [ ] Test run with sample data completed successfully
  - [ ] Log files generated and readable
  - [ ] Output data validates correctly
  - [ ] Performance within expected range

- [ ] **Security**
  - [ ] File permissions set correctly
  - [ ] Network access configured
  - [ ] Log file access restricted

## 4. Operational Procedures

### 4.1 Starting the Application

#### Manual Execution
```bash
# Activate virtual environment
source venv/bin/activate

# Run with default configuration
python src/eddypro_batch_processor.py

# Run with custom configuration
python src/eddypro_batch_processor.py --config /path/to/custom/config.yaml

# Run with specific log level
python src/eddypro_batch_processor.py --config config/config.yaml 2>&1 | tee runtime.log
```

#### Scheduled Execution (Cron)
```bash
# Add to crontab for daily execution at 2 AM
0 2 * * * /path/to/eddypro_batch_processor/venv/bin/python /path/to/eddypro_batch_processor/src/eddypro_batch_processor.py --config /path/to/config.yaml >> /path/to/logs/cron.log 2>&1
```

#### Windows Task Scheduler
```powershell
# Create scheduled task for daily execution
schtasks /create /tn "EddyPro Batch Processing" /tr "C:\path\to\venv\Scripts\python.exe C:\path\to\src\eddypro_batch_processor.py --config C:\path\to\config.yaml" /sc daily /st 02:00
```

### 4.2 Monitoring Procedures

#### Real-time Monitoring
```bash
# Monitor active processing
tail -f logs/eddypro_processing.log

# Monitor system resources during processing
htop
iostat -x 1
```

#### Health Checks
```bash
# Check if application is running
ps aux | grep eddypro_batch_processor

# Check log file for errors
grep -i error logs/eddypro_processing.log | tail -20

# Check disk space usage
df -h /path/to/data/directories

# Verify recent processing activity
ls -la data/processed/*/$(date +%Y)/ | head -10
```

### 4.3 Performance Monitoring

#### Key Performance Indicators
- **Processing Throughput**: Files processed per hour
- **Resource Utilization**: CPU, memory, disk I/O
- **Error Rates**: Failed processing runs per day
- **Data Quality**: Output file validation success rate

#### Performance Commands
```bash
# Monitor CPU usage during processing
top -p $(pgrep -f eddypro_batch_processor)

# Monitor memory usage
ps -o pid,vsz,rss,comm -p $(pgrep -f eddypro_batch_processor)

# Monitor disk I/O
iotop -p $(pgrep -f eddypro_batch_processor)

# Check processing statistics from logs
grep "Processed.*files" logs/eddypro_processing.log | tail -10
```

## 5. Troubleshooting Guide

### 5.1 Common Issues

#### Issue: Application fails to start
**Symptoms**: ImportError, configuration errors, or immediate exit
```bash
# Diagnosis
python src/eddypro_batch_processor.py --config config/config.yaml

# Solutions
1. Verify Python environment: python --version
2. Check dependencies: pip list
3. Validate configuration: python -c "import yaml; print(yaml.safe_load(open('config/config.yaml')))"
4. Check file permissions: ls -la config/config.yaml
```

#### Issue: EddyPro executable not found
**Symptoms**: "EddyPro executable not found" error message
```bash
# Diagnosis
ls -la "$(grep eddypro_executable config/config.yaml | cut -d: -f2 | tr -d ' \"')"

# Solutions
1. Verify EddyPro installation path
2. Update config.yaml with correct path
3. Check executable permissions
4. Verify EddyPro license validity
```

#### Issue: Processing runs but produces no output
**Symptoms**: Process completes but no files in output directory
```bash
# Diagnosis
grep -i "No raw files found\|Skipping.*no valid" logs/eddypro_processing.log

# Solutions
1. Verify input data path and file patterns
2. Check data file naming conventions
3. Validate file permissions on input data
4. Review site_id and year configuration
```

#### Issue: High memory usage or out-of-memory errors
**Symptoms**: System becomes unresponsive, killed processes
```bash
# Diagnosis
dmesg | grep -i "killed process\|out of memory"
grep "memory\|Memory" logs/eddypro_processing.log

# Solutions
1. Reduce max_processes in configuration
2. Process fewer years simultaneously
3. Monitor and increase system memory
4. Check for memory leaks in processing
```

### 5.2 Error Code Reference

| Exit Code | Description | Action Required |
|-----------|-------------|-----------------|
| 0 | Success | None |
| 1 | Configuration error | Check config.yaml syntax and required parameters |
| 2 | EddyPro executable error | Verify EddyPro installation and licensing |
| 3 | Input data error | Check data paths and file accessibility |
| 4 | Output directory error | Verify write permissions and disk space |
| 5 | Processing error | Review EddyPro logs and data quality |

### 5.3 Log Analysis

#### Key Log Patterns
```bash
# Successful processing completion
grep "Processed .* files. Elapsed time:" logs/eddypro_processing.log

# Configuration loading
grep "Configuration loaded successfully" logs/eddypro_processing.log

# Error patterns
grep -E "(ERROR|CRITICAL|Failed|Exception)" logs/eddypro_processing.log

# Performance metrics
grep -E "(Starting|Finished).*eddypro" logs/eddypro_processing.log
```

## 6. Maintenance Procedures

### 6.1 Regular Maintenance

#### Daily Tasks
- [ ] Check processing logs for errors
- [ ] Verify disk space availability
- [ ] Monitor processing completion status

#### Weekly Tasks
- [ ] Rotate log files if needed
- [ ] Clean up temporary processing files
- [ ] Review performance metrics
- [ ] Backup configuration files

#### Monthly Tasks
- [ ] Update dependencies (pip list --outdated)
- [ ] Review and archive old log files
- [ ] Performance analysis and optimization
- [ ] Documentation updates

### 6.2 Log File Management

#### Log Rotation Configuration
```python
# Automatic log rotation is configured in the application
# Default: 5 rotating files, 10MB each
# Location: logs/eddypro_processing.log

# Manual log rotation if needed
import logging.handlers
handler = logging.handlers.RotatingFileHandler(
    'logs/eddypro_processing.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

#### Log Cleanup
```bash
# Remove logs older than 30 days
find logs/ -name "*.log.*" -mtime +30 -delete

# Compress old log files
gzip logs/eddypro_processing.log.[2-9]
```

### 6.3 Data Management

#### Input Data Validation
```bash
# Check for new data files
find data/raw/ -name "*.csv" -mtime -1 | wc -l

# Validate file formats
python -c "
import pandas as pd
import sys
try:
    df = pd.read_csv(sys.argv[1])
    print(f'Valid CSV: {len(df)} rows, {len(df.columns)} columns')
except Exception as e:
    print(f'Invalid CSV: {e}')
" data/raw/SITE/YEAR/file.csv
```

#### Output Data Validation
```bash
# Check output file completeness
find data/processed/ -name "*.csv" -mtime -1 -exec wc -l {} +

# Validate output file formats
ls data/processed/*/$(date +%Y)/ | grep -E "\.(csv|eddypro)$"
```

## 7. Backup and Recovery

### 7.1 Backup Procedures

#### Configuration Backup
```bash
# Backup configuration files
tar -czf backup/config_$(date +%Y%m%d_%H%M%S).tar.gz config/

# Automated daily backup
0 1 * * * tar -czf /backup/eddypro_config_$(date +\%Y\%m\%d).tar.gz /path/to/config/
```

#### Data Backup
```bash
# Backup processed data
rsync -av data/processed/ /backup/processed/

# Incremental backup
rsync -av --link-dest=/backup/processed_previous data/processed/ /backup/processed_$(date +%Y%m%d)/
```

### 7.2 Recovery Procedures

#### Configuration Recovery
```bash
# Restore configuration from backup
tar -xzf backup/config_YYYYMMDD_HHMMSS.tar.gz

# Verify restored configuration
python -c "from src.eddypro_batch_processor import load_config, validate_config; config = load_config('config/config.yaml'); validate_config(config)"
```

#### Processing Recovery
```bash
# Resume interrupted processing
# 1. Check logs for last processed site/year
grep "Starting.*year" logs/eddypro_processing.log | tail -5

# 2. Update configuration to skip completed years
# 3. Restart processing
python src/eddypro_batch_processor.py --config config/config.yaml
```

## 8. Emergency Procedures

### 8.1 System Overload
```bash
# Immediate actions
1. Stop current processing: pkill -f eddypro_batch_processor
2. Check system resources: free -h && df -h
3. Reduce process count in config.yaml
4. Restart with limited resources
```

### 8.2 Data Corruption
```bash
# Detection
1. Validate output files: python scripts/validate_output.py
2. Check file integrity: find data/processed -name "*.csv" -exec file {} \;
3. Compare with known good outputs

# Recovery
1. Stop processing
2. Remove corrupted output files
3. Restore from backup if available
4. Reprocess affected data
```

### 8.3 License Issues
```bash
# EddyPro license expiration
1. Check EddyPro license status
2. Contact LI-COR for license renewal
3. Temporarily halt processing
4. Document affected processing periods
```

## 9. Contact Information

### 9.1 Support Escalation
- **Level 1**: System Administrator (operational issues)
- **Level 2**: Development Team (application issues)
- **Level 3**: EddyPro Support (software-specific issues)

### 9.2 Emergency Contacts
- **Primary On-call**: [Contact information]
- **Secondary On-call**: [Contact information]
- **Development Team Lead**: [Contact information]
- **System Administrator**: [Contact information]

---

## Document Status
- **Version**: 1.0
- **Last Updated**: September 23, 2025
- **Next Review**: December 31, 2025
- **Maintained by**: DevOps Team