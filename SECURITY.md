# Security Policy

## Supported Versions

We provide security updates for the following versions of EddyPro Batch Processor:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 0.2.x   | :white_check_mark: | Current stable release |
| 0.1.x   | :x:                | End of life |

## Security Considerations

### Data Security

- **Local Processing**: All data processing occurs locally; no data is transmitted over networks
- **File Permissions**: Ensure appropriate file system permissions for data directories
- **Configuration Files**: Keep `config.yaml` secure as it may contain file paths and system information

### System Security

- **EddyPro Executable**: Verify EddyPro installation integrity from official LI-COR sources
- **Python Environment**: Use virtual environments to isolate dependencies
- **File System Access**: The application requires read/write access to configured data directories

### Dependencies

- **Core Dependencies**: Minimal external dependencies (PyYAML only for core functionality)
- **Optional Dependencies**: psutil and plotly are optional and can be omitted in security-sensitive environments
- **Supply Chain**: All dependencies are from established Python packages with good security track records

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in EddyPro Batch Processor, please follow these steps:

### How to Report

**Email**: [raje@ecos.au.dk](mailto:raje@ecos.au.dk)

**Subject Line**: `[SECURITY] EddyPro Batch Processor - <Brief Description>`

### What to Include

Please include the following information in your report:

1. **Description**: Clear description of the vulnerability
2. **Steps to Reproduce**: Detailed steps to reproduce the issue
3. **Impact**: Potential impact and affected components
4. **Environment**: Operating system, Python version, and application version
5. **Proof of Concept**: If applicable, provide a minimal example (without exploiting)

### Response Timeline

- **Initial Response**: Within 48 hours of report receipt
- **Investigation**: We will investigate and assess the vulnerability within 5 business days
- **Resolution**: Security fixes will be prioritized and released as quickly as possible
- **Disclosure**: We will coordinate with you on responsible disclosure timing

### What NOT to Do

- **Do NOT** open public issues for security vulnerabilities
- **Do NOT** post vulnerabilities on social media or public forums
- **Do NOT** attempt to exploit vulnerabilities beyond proof of concept
- **Do NOT** access data that does not belong to you

## Security Best Practices

### For Users

1. **Keep Software Updated**: Always use the latest supported version
2. **Secure Configuration**:
   - Store `config.yaml` with appropriate file permissions (600 or 640)
   - Use absolute paths to prevent path traversal issues
   - Validate input file paths before processing
3. **Environment Isolation**: Use virtual environments for Python dependencies
4. **Data Protection**: Ensure data directories have appropriate access controls
5. **Log Security**: Review log files for unusual activity

### For Developers

1. **Input Validation**: All user inputs are validated before processing
2. **Path Safety**: Use `pathlib` for safe path operations
3. **Subprocess Security**: EddyPro execution uses safe subprocess practices
4. **Error Handling**: No sensitive information in error messages
5. **Testing**: Security considerations included in test suite

## Known Security Considerations

### File System Access

- The application requires read access to input data directories
- Write access is required for output directories and reports
- Configuration files may contain sensitive path information

### External Process Execution

- The application executes EddyPro as an external process
- EddyPro executable path is user-configurable
- Process execution is monitored but not sandboxed

### Temporary Files

- Temporary INI files are created during processing
- Temporary files are cleaned up after processing
- File permissions inherit from system defaults

## Security Updates

Security updates will be:

1. **Released Promptly**: Critical security fixes will be released as patch versions
2. **Clearly Documented**: Security fixes will be clearly marked in CHANGELOG.md
3. **Backwards Compatible**: Security fixes will maintain backwards compatibility when possible
4. **Communicated**: Users will be notified of security updates through release notes

## Contact Information

For security-related questions or concerns:

- **Security Contact**: [raje@ecos.au.dk](mailto:raje@ecos.au.dk)
- **General Issues**: Use GitHub Issues for non-security related bugs
- **Project Repository**: [https://github.com/rasmusjen/eddypro_batch_processor](https://github.com/rasmusjen/eddypro_batch_processor)

---

**Last Updated**: October 2, 2025
**Next Review**: April 2026
