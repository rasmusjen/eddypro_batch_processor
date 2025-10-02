# Milestone 6: Scenario Runner - Cartesian Product Generation

## Summary

Implements comprehensive scenario generation and execution system with Cartesian product logic, enabling users to run multiple EddyPro parameter combinations efficiently. This milestone delivers a fully functional scenario runner that generates deterministic combinations and tracks execution results.

## Problem

Users need to test multiple EddyPro parameter combinations (rotation methods, time lag methods, detrend methods, spike removal) systematically to find optimal processing configurations. Manual execution of multiple parameter combinations is error-prone, time-consuming, and lacks systematic tracking.

## Approach

### New Components

- **`scenarios.py` module**: Cartesian product generation with validation
  - `generate_scenarios()`: Creates all parameter combinations with hard cap enforcement
  - `generate_scenario_suffix()`: Deterministic naming (e.g., `_rot1_tlag2_det0_spk1`)
  - `Scenario` dataclass: Immutable scenario representation
  - `validate_scenario_parameters()`: Parameter validation before generation

- **Core execution functions**: Scenario batch processing
  - `run_single_scenario()`: Executes individual scenarios with patched INI files
  - `run_scenario_batch()`: Orchestrates multiple scenarios sequentially
  - Per-scenario output directories and manifest generation

- **CLI integration**: Full `scenarios` subcommand
  - Accepts parameter lists: `--rot-meth 1 3`, `--tlag-meth 2 4`, etc.
  - `--max-scenarios` override (default: 32)
  - Integration with existing config system

### Key Features

1. **Deterministic generation**: Same inputs → same scenarios, same order
2. **Hard cap enforcement**: Maximum 32 scenarios with actionable error messages
3. **Immutable scenarios**: Frozen dataclasses prevent accidental mutations
4. **Per-scenario tracking**: Individual manifests with timing and success status
5. **Consistent naming**: Canonical parameter ordering in suffixes

## Tests

- **25 new tests** in `test_scenarios.py` with **100% coverage** on scenarios module
- All existing tests updated and passing (**118/118 tests pass**)
- Tests validate:
  - Cartesian product generation
  - Scenario cap enforcement
  - Deterministic naming and ordering
  - Parameter validation
  - Dataclass immutability
  - Error handling

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Large scenario matrices overwhelm system | Hard cap of 32 scenarios; clear error when exceeded |
| Scenario naming conflicts | Deterministic suffix with canonical ordering |
| Parameter validation gaps | Comprehensive validation at multiple stages |
| Non-deterministic behavior | Tests verify deterministic generation; seeded where needed |

## Rollback Plan

If issues arise:

1. Revert commit `f44c4e5`
2. Use single-parameter runs from Milestone 5
3. No data loss as scenarios are isolated

## Usage Examples

### Basic scenario matrix

```bash
# Test 2 rotation methods × 2 time lag methods = 4 scenarios
eddypro-batch scenarios --rot-meth 1 3 --tlag-meth 2 4 --site GL-ZaF --years 2021
```

Output structure:

```text
output/GL-ZaF/2021/
├── scenario_rot1_tlag2/
│   ├── EddyProProject_rot1_tlag2.eddypro
│   ├── scenario_manifest_rot1_tlag2.json
│   └── metrics_rot1_tlag2_rp.csv
├── scenario_rot1_tlag4/
├── scenario_rot3_tlag2/
└── scenario_rot3_tlag4/
```

### Full parameter matrix

```bash
# 2×2×2×2 = 16 scenarios
eddypro-batch scenarios \
  --rot-meth 1 3 \
  --tlag-meth 2 4 \
  --detrend-meth 0 1 \
  --despike-vm 0 1 \
  --site GL-ZaF \
  --years 2021 2022
```

### Scenario summary output

```text
Generated 4 scenario(s):

  Scenario 1: rot_meth=1, tlag_meth=2
    Suffix: _rot1_tlag2
  Scenario 2: rot_meth=1, tlag_meth=4
    Suffix: _rot1_tlag4
  Scenario 3: rot_meth=3, tlag_meth=2
    Suffix: _rot3_tlag2
  Scenario 4: rot_meth=3, tlag_meth=4
    Suffix: _rot3_tlag4
```

## Code Quality Metrics

- **Overall coverage**: 74.56% (up from baseline)
- **New module coverage**: 100% on `scenarios.py`
- **Linting**: All code passes ruff, black, mypy
- **Security**: Bandit checks pass
- **Type safety**: Strict type hints throughout

## Documentation

- ✅ CHANGELOG.md updated with detailed changes
- ✅ Comprehensive docstrings (NumPy/Google style)
- ✅ Usage examples in PR description
- ✅ Inline code comments for complex logic

## Definition of Done

- [x] Lint/format/typecheck clean
- [x] Tests updated; coverage ≥70% maintained (74.56%)
- [x] Schema/unit validations in place
- [x] Chunked I/O & parallelism reviewed (N/A for this milestone)
- [x] Logs + manifest written; profiling optional
- [x] CLI/config/docstrings/CHANGELOG updated
- [x] Feature branch pushed; PR opened with summary & risks

## Related Issues

Part of `docs/IMPROVEMENT_PLAN.md` Milestone 6

## Checklist

- [x] Code follows project coding standards
- [x] Tests added/updated and passing
- [x] Documentation updated
- [x] CHANGELOG.md updated
- [x] No breaking changes to existing functionality
- [x] Pre-commit hooks pass
