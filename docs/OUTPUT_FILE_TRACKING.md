# Output File Tracking in Run Manifests

## Overview

Run manifests now include comprehensive tracking of all EddyPro output CSV files with absolute paths. This enables automated post-processing, validation workflows, and audit trails.

## Manifest Structure

The `output_files` field in the run manifest contains a dictionary mapping each scenario output directory to its collected EddyPro output files:

```json
{
  "output_files": {
    "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot1": {
      "fluxnet_files": [
        "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot1\\eddypro_GL-ZaF_fluxnet_2024-11-18T185928_adv.csv"
      ],
      "full_output_files": [
        "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot1\\eddypro_GL-ZaF_full_output_2024-11-18T185928_adv.csv"
      ],
      "metadata_files": [
        "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot1\\eddypro_GL-ZaF_metadata_2024-11-18T185928_adv.csv"
      ],
      "qc_details_files": [
        "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot1\\eddypro_GL-ZaF_qc_details_2024-11-18T165300_adv.csv"
      ]
    },
    "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot3": {
      "fluxnet_files": [
        "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot3\\eddypro_GL-ZaF_fluxnet_2024-11-18T190000_adv.csv"
      ],
      "full_output_files": [
        "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot3\\eddypro_GL-ZaF_full_output_2024-11-18T190000_adv.csv"
      ],
      "metadata_files": [
        "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot3\\eddypro_GL-ZaF_metadata_2024-11-18T190000_adv.csv"
      ],
      "qc_details_files": [
        "D:\\L1_processed\\GL-ZaF\\2021\\ec_rflux\\test\\scenario_rot3\\eddypro_GL-ZaF_qc_details_2024-11-18T170000_adv.csv"
      ]
    }
  }
}
```

## File Type Patterns

The following EddyPro output file patterns are tracked:

1. **Fluxnet files**: `eddypro_{site_ID}_fluxnet_*.csv`
   - FLUXNET-format flux and meteorological data

2. **Full output files**: `eddypro_{site_ID}_full_output_*.csv`
   - Complete output dataset with all computed variables

3. **Metadata files**: `eddypro_{site_ID}_metadata_*.csv`
   - Processing metadata and configuration details

4. **QC details files**: `eddypro_{site_ID}_qc_details*.csv`
   - Quality control flags and diagnostic information

## Usage Examples

### Automated Post-Processing

```python
import json
from pathlib import Path

# Load manifest
with open("run_manifest.json") as f:
    manifest = json.load(f)

# Iterate over all scenario outputs
for output_dir, files in manifest["output_files"].items():
    print(f"Processing outputs from: {output_dir}")

    # Process fluxnet files
    for fluxnet_file in files["fluxnet_files"]:
        process_fluxnet_data(Path(fluxnet_file))

    # Validate QC details
    for qc_file in files["qc_details_files"]:
        validate_quality_control(Path(qc_file))
```

### File Inventory Report

```python
# Count total files across all scenarios
total_files = 0
for output_dir, files in manifest["output_files"].items():
    scenario_total = sum(len(files[ft]) for ft in files)
    total_files += scenario_total
    print(f"{output_dir}: {scenario_total} files")

print(f"Total EddyPro outputs: {total_files}")
```

### Data Comparison Across Scenarios

```python
# Compare fluxnet outputs from different rotation methods
fluxnet_by_scenario = {}
for output_dir, files in manifest["output_files"].items():
    scenario_name = Path(output_dir).name  # e.g., "scenario_rot1"
    fluxnet_by_scenario[scenario_name] = files["fluxnet_files"]

# Now compare rot1 vs rot3
compare_flux_data(
    fluxnet_by_scenario["scenario_rot1"][0],
    fluxnet_by_scenario["scenario_rot3"][0]
)
```

## Implementation Details

### Collection Function

The `collect_eddypro_output_files()` function in `report.py` scans each scenario output directory using glob patterns:

```python
def collect_eddypro_output_files(
    output_dir: Path, site_id: str
) -> dict[str, list[str]]:
    """
    Collect all EddyPro output CSV files matching standard patterns.

    Returns absolute paths grouped by file type.
    """
    patterns = {
        "fluxnet_files": f"eddypro_{site_id}_fluxnet_*.csv",
        "full_output_files": f"eddypro_{site_id}_full_output_*.csv",
        "metadata_files": f"eddypro_{site_id}_metadata_*.csv",
        "qc_details_files": f"eddypro_{site_id}_qc_details*.csv",
    }

    collected = {}
    for file_type, pattern in patterns.items():
        matching_files = sorted(output_dir.glob(pattern))
        collected[file_type] = [str(f.resolve()) for f in matching_files]

    return collected
```

### Integration

The collection is integrated into `generate_run_manifest()`:

```python
# Collect EddyPro output files from all output directories
output_files = {}
for output_dir in output_dirs:
    if output_dir.exists():
        collected = collect_eddypro_output_files(output_dir, site_id)
        output_files[str(output_dir)] = collected

manifest["output_files"] = output_files
```

## Benefits

1. **Traceability**: Complete audit trail of all generated files
2. **Automation**: Enables scripted post-processing without manual file discovery
3. **Validation**: Verify expected outputs were created
4. **Comparison**: Easy identification of scenario-specific outputs
5. **Archival**: Documentation of processed datasets for long-term storage

## Notes

- File paths are absolute and platform-specific (Windows backslashes shown in examples)
- Files are sorted alphabetically within each type
- Empty lists indicate no matching files (e.g., during dry runs)
- All four file types are always present in the manifest, even if empty
