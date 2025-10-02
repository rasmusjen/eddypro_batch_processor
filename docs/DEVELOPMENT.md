# Development Guide

This document provides guidelines for contributing to the EddyPro Batch Processor project, including setup, testing, code standards, and workflow.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Pre-commit Hooks](#pre-commit-hooks)
- [CI/CD](#cicd)
- [Git Workflow](#git-workflow)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Definition of Done](#definition-of-done)

## Development Setup

### Prerequisites

- Python 3.10 or higher (Python 3.12+ recommended for development)
- Git
- Virtual environment (recommended)

### Initial Setup

1. **Clone the repository:**

```bash
git clone <repository-url>
cd eddypro_batch_processor
```

2. **Create and activate virtual environment:**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
pip install -e .  # Editable install for development
```

4. **Install development tools:**

```bash
pip install black ruff mypy pytest pytest-cov pre-commit
```

5. **Set up pre-commit hooks:**

```bash
pre-commit install
```

6. **Verify setup:**

```bash
eddypro-batch --help
pytest tests/
```

---

## Code Standards

### Formatting

**Black (line length: 88)**

Automatic code formatting:

```bash
black src/ tests/
```

Configuration in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py312']
```

### Linting

**Ruff (fast Python linter)**

Enforced rules: E, F, W, I, N, UP, B, SIM, TRY, PL

Run linter:

```bash
ruff check src/ tests/
```

Auto-fix issues:

```bash
ruff check --fix src/ tests/
```

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "TRY", "PL"]
ignore = []
line-length = 88
```

### Type Checking

**Mypy (static type checker)**

Run type checks:

```bash
mypy src/
```

Configuration in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

**Type hint guidelines:**

- All public functions must have type hints for parameters and return values
- Use `typing` module types: `Dict`, `List`, `Optional`, `Any`, etc.
- Gradual typing: add types to new code first, then backfill legacy code

**Example:**

```python
from pathlib import Path
from typing import Dict, List

def process_files(input_dir: Path, years: List[int]) -> Dict[str, Any]:
    """Process files for given years."""
    results = {}
    for year in years:
        results[str(year)] = process_year(input_dir, year)
    return results
```

---

## Testing

### Test Framework

**Pytest with pytest-cov**

### Running Tests

**All tests:**

```bash
pytest
```

**With coverage:**

```bash
pytest --cov=src/eddypro_batch_processor --cov-report=html --cov-report=term
```

**Specific test file:**

```bash
pytest tests/test_validation.py
```

**Specific test:**

```bash
pytest tests/test_validation.py::TestValidateConfigStructure::test_valid_config_passes
```

**Verbose output:**

```bash
pytest -v
```

**Stop on first failure:**

```bash
pytest -x
```

### Coverage Goals

- **Core modules (validation, ini_tools, scenarios)**: ≥ 90%
- **Overall project**: ≥ 70% (baseline), improving to 90%

**View coverage report:**

```bash
# Generate HTML report
pytest --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html  # Mac/Linux
start htmlcov\index.html  # Windows
```

### Test Organization

```
tests/
├── __init__.py
├── test_cli.py               # CLI command tests
├── test_core.py              # Core processing logic tests
├── test_ini_tools.py         # INI manipulation tests
├── test_validation.py        # Validation module tests
├── test_scenarios.py         # Scenario generation tests
├── test_monitor.py           # Performance monitoring tests
└── test_report.py            # Reporting module tests
```

### Writing Tests

**Test class structure:**

```python
import pytest
from src.eddypro_batch_processor import validation

class TestValidateConfigStructure:
    """Test configuration structure validation."""

    def test_valid_config_passes(self):
        """Test that a valid configuration passes validation."""
        config = {
            "eddypro_executable": "/path/to/exe",
            "site_id": "GL-ZaF",
            # ... other required keys
        }
        errors = validation.validate_config_structure(config)
        assert errors == []

    def test_missing_required_keys(self):
        """Test that missing required keys are detected."""
        config = {"site_id": "GL-ZaF"}  # Missing other keys
        errors = validation.validate_config_structure(config)
        assert len(errors) > 0
        assert "Missing required configuration keys" in errors[0]
```

**Using fixtures:**

```python
@pytest.fixture
def valid_config():
    """Provide a valid configuration for tests."""
    return {
        "eddypro_executable": "/path/to/exe",
        "site_id": "GL-ZaF",
        "years_to_process": [2021],
        # ... other required keys
    }

def test_with_fixture(valid_config):
    """Test using fixture."""
    errors = validation.validate_config_structure(valid_config)
    assert errors == []
```

**Temporary files:**

```python
import tempfile
from pathlib import Path

def test_with_temp_file():
    """Test with temporary file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test data")
        temp_path = Path(f.name)

    try:
        # Test code using temp_path
        result = process_file(temp_path)
        assert result is not None
    finally:
        temp_path.unlink()  # Clean up
```

### Test Determinism

**Rules:**

- **No wall-clock dependencies**: Use fixed timestamps or mocking
- **No machine-path coupling**: Use relative paths or fixtures
- **Seed RNG**: Use `random.seed()` or `numpy.random.seed()` for reproducibility
- **Mock external dependencies**: Mock EddyPro binaries, file I/O, network calls

**Example:**

```python
from unittest.mock import patch, Mock

@patch('subprocess.run')
def test_eddypro_execution(mock_run):
    """Test EddyPro execution with mocked subprocess."""
    mock_run.return_value = Mock(returncode=0, stdout="success")

    result = run_eddypro("/path/to/project.eddypro")

    assert result.success is True
    mock_run.assert_called_once()
```

---

## Pre-commit Hooks

### Setup

Install pre-commit hooks:

```bash
pre-commit install
```

### Configuration

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML]
```

### Running Hooks

**Automatically on commit:**

Pre-commit hooks run automatically when you `git commit`.

**Manually on all files:**

```bash
pre-commit run --all-files
```

**Skip hooks (not recommended):**

```bash
git commit --no-verify
```

---

## CI/CD

### GitHub Actions Workflow

`.github/workflows/ci.yml`:

```yaml
name: CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install black ruff mypy
      - name: Run black
        run: black --check src/ tests/
      - name: Run ruff
        run: ruff check src/ tests/
      - name: Run mypy
        run: mypy src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### CI Checks

CI enforces:

1. **Formatting**: `black --check`
2. **Linting**: `ruff check`
3. **Type checking**: `mypy`
4. **Tests**: `pytest` with coverage

**All checks must pass** before merging a PR.

---

## Git Workflow

### Branch Naming

Use conventional branch names:

- `feat/<slug>` – new features
- `fix/<slug>` – bug fixes
- `refactor/<slug>` – code refactoring
- `docs/<slug>` – documentation updates
- `test/<slug>` – test additions/updates

**Examples:**

```bash
git checkout -b feat/milestone-7-validate-docs
git checkout -b fix/ecmd-schema-validation
git checkout -b refactor/ini-tools-cleanup
```

### Commit Messages

Follow **Conventional Commits**:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- `feat`: new feature
- `fix`: bug fix
- `refactor`: code refactoring
- `docs`: documentation changes
- `test`: test additions/updates
- `chore`: maintenance tasks

**Examples:**

```
feat(validation): add ECMD schema and sanity checks

- Implement validate_ecmd_schema() function
- Implement validate_ecmd_sanity() function
- Add tests for ECMD validation

Closes #42
```

```
fix(cli): correct exit code on validation failure

Previously returned 0 even on failure. Now returns 1
to properly signal error state to calling scripts.
```

---

## Pull Request Guidelines

### Before Opening a PR

1. **Ensure all tests pass:**

```bash
pytest
```

2. **Run linters and formatters:**

```bash
black src/ tests/
ruff check --fix src/ tests/
mypy src/
```

3. **Update documentation:**
   - Update relevant `.md` files
   - Add docstrings to new functions
   - Update CHANGELOG.md

4. **Commit changes:**

```bash
git add .
git commit -m "feat: implement feature X"
```

5. **Push to remote:**

```bash
git push origin feat/feature-x
```

### PR Description Template

```markdown
## Problem

Briefly describe the problem or feature request.

## Approach

Explain your solution and key design decisions.

## Tests

Describe test coverage:
- New tests added
- Existing tests updated
- Coverage maintained/improved

## Risks

Any potential risks or breaking changes?

## Rollback

How to revert if this causes issues?

## Checklist

- [ ] Lint/format/typecheck clean
- [ ] Tests updated; coverage maintained
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] CI passing
```

### Review Process

1. **Automated checks**: CI must pass
2. **Code review**: At least one approval required
3. **Testing**: Reviewer tests changes locally if needed
4. **Merge**: Squash and merge to keep history clean

---

## Definition of Done

Before marking a task as complete, ensure:

- [ ] **Lint/format/typecheck clean**: Black, Ruff, Mypy all pass
- [ ] **Tests updated**: New tests added; existing tests updated; coverage maintained (≥70%)
- [ ] **Tests deterministic**: No wall-clock or machine-path coupling; RNG seeded
- [ ] **Schema/unit validations in place**: Input validation with actionable errors
- [ ] **Chunked I/O & parallelism reviewed**: No over-subscription; respect resource limits
- [ ] **Logs + manifest written**: Structured logs; provenance captured
- [ ] **Profiling optional**: Performance monitoring available
- [ ] **CLI/config/docstrings/CHANGELOG updated**: User-facing changes documented
- [ ] **Feature branch pushed**: Branch available for review
- [ ] **PR opened**: PR includes Problem, Approach, Tests, Risks, Rollback

---

## Troubleshooting

### Pre-commit Hooks Failing

**Issue:** Pre-commit hooks fail on commit

**Solutions:**

```bash
# Run hooks manually to see details
pre-commit run --all-files

# Fix formatting issues
black src/ tests/

# Fix linting issues
ruff check --fix src/ tests/

# Skip hooks if absolutely necessary (not recommended)
git commit --no-verify
```

### Type Checking Errors

**Issue:** Mypy reports type errors

**Solutions:**

```bash
# Run mypy to see all errors
mypy src/

# Add type hints to fix errors
# Or add type: ignore comments for complex cases
result = complex_function()  # type: ignore

# Update mypy configuration for gradual typing
# In pyproject.toml:
# disallow_untyped_defs = false
```

### Test Failures

**Issue:** Tests fail locally or in CI

**Solutions:**

```bash
# Run tests with verbose output
pytest -v

# Run specific failing test
pytest tests/test_module.py::test_function -v

# Check test logs
pytest --log-cli-level=DEBUG

# Ensure fixtures and mocks are correct
# Check for non-deterministic behavior
```

---

## Additional Resources

- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [Black Code Style](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Pre-commit Hooks](https://pre-commit.com/)

---

## See Also

- [USAGE.md](USAGE.md) – CLI usage
- [CONFIG.md](CONFIG.md) – Configuration options
- [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) – Project roadmap
