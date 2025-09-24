# Documentation Index

## Overview

This directory contains comprehensive documentation for the EddyPro Batch Processor project, organized into development and user documentation.

## Directory Structure

```
docs/
├── README.md                          # This index file
├── development/                       # Development and maintenance docs
│   ├── specs.md                      # Technical specifications
│   ├── agent.md                      # Agent workflow & dev standards
│   ├── plan.md                       # Development roadmap
│   └── RUNBOOK.md                    # Operations runbook
└── user/                             # End-user documentation
    ├── (future) getting-started.md   # Quick start guide
    ├── (future) configuration.md     # Configuration reference
    ├── (future) troubleshooting.md   # User troubleshooting
    └── (future) api-reference.md     # API documentation
```

## Development Documentation

### [specs.md](development/specs.md)
**Purpose**: Technical specifications and architecture documentation  
**Audience**: Developers, architects, technical stakeholders  
**Content**: System requirements, architecture design, performance specifications, extensibility roadmap

### [agent.md](development/agent.md)  
**Purpose**: Agent workflow instructions and development standards  
**Audience**: Automated agents, developers, code reviewers  
**Content**: Coding standards, testing requirements, operational procedures, multiprocessing strategy

### [plan.md](development/plan.md)
**Purpose**: Development roadmap and project planning  
**Audience**: Project managers, development team, stakeholders  
**Content**: Development phases, timelines, resource requirements, success metrics

### [RUNBOOK.md](development/RUNBOOK.md)
**Purpose**: Operational procedures and maintenance guide  
**Audience**: System administrators, DevOps engineers, on-call personnel  
**Content**: Deployment procedures, monitoring, troubleshooting, emergency procedures

## User Documentation (Future)

The `user/` directory is reserved for end-user documentation that will be developed as the project matures and additional interfaces are added.

### Planned User Documentation:
- **getting-started.md**: Quick start guide for new users
- **configuration.md**: Comprehensive configuration reference
- **troubleshooting.md**: Common issues and solutions for end users
- **api-reference.md**: API documentation (when REST API is implemented)

## Document Relationships

```
┌─────────────┐    informs    ┌─────────────┐
│   specs.md  │ ────────────▶ │   plan.md   │
└─────────────┘               └─────────────┘
       │                             │
       │ guides                      │ schedules
       ▼                             ▼
┌─────────────┐               ┌─────────────┐
│  agent.md   │               │ RUNBOOK.md  │
└─────────────┘               └─────────────┘
       │                             │
       └──────────── supports ───────┘
              operations
```

### How Documents Work Together:

1. **specs.md** defines WHAT needs to be built (requirements, architecture)
2. **plan.md** defines WHEN and WHO will build it (timeline, resources)  
3. **agent.md** defines HOW to build it (standards, procedures)
4. **RUNBOOK.md** defines HOW to operate it (deployment, monitoring)

## Maintenance Schedule

| Document | Review Frequency | Update Triggers |
|----------|------------------|-----------------|
| specs.md | Quarterly | Major feature changes, architecture updates |
| agent.md | Monthly | Development process changes, new standards |
| plan.md | Monthly | Milestone completion, scope changes |
| RUNBOOK.md | Quarterly | Operational process changes, new procedures |

## Document Standards

- **Format**: Markdown (.md) with consistent heading structure
- **Version Control**: All documents tracked in Git with the main codebase
- **Review Process**: Changes require pull request review
- **Status Tracking**: Each document includes version and last updated information

## Contributing to Documentation

1. **For Development Docs**: Follow the guidelines in `agent.md`
2. **For User Docs**: Focus on clarity and practical examples
3. **Review Process**: All documentation changes require peer review
4. **Style Guide**: Use clear headings, code examples, and practical instructions

---

## Quick Links

- [Project Repository](https://github.com/rasmusjen/eddypro_batch_processor)
- [Main README](../README.md)
- [Development Specifications](development/specs.md)
- [Development Plan](development/plan.md)
- [Operations Runbook](development/RUNBOOK.md)

## Document Status
- **Created**: September 23, 2025
- **Last Updated**: September 23, 2025
- **Next Review**: December 31, 2025