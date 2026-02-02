# Metadata Population Plan (.metadata)

## Results (current behavior)

- The .metadata file is currently created by copying a site-specific or generic template during scenario setup in [src/eddypro_batch_processor/core.py](src/eddypro_batch_processor/core.py).
- The .eddypro file is written via the INI utilities in [src/eddypro_batch_processor/ini_tools.py](src/eddypro_batch_processor/ini_tools.py).
- Dynamic metadata (.txt) is generated from the ECMD CSV in [src/eddypro_batch_processor/ecmd.py](src/eddypro_batch_processor/ecmd.py).
- There is no current logic that populates .metadata values from ECMD.

## Required behavior (per request)

### Static .metadata fields

Populate these fields in the .metadata file after writing the .eddypro file:

- `file_name = {output_dir}/{site_id}.metadata`
- `site_id = {site_id}`

### ECMD-driven fields

Populate the following .metadata values based on ECMD input (column names on the right):

| .metadata key | ECMD column |
|---|---|
| `altitude` | `ALTITUDE` |
| `canopy_height` | `CANOPY_HEIGHT` |
| `latitude` | `LATITUDE` |
| `longitude` | `LONGITUDE` |
| `acquisition_frequency` | `ACQUISITION_FREQUENCY` |
| `file_duration` | `FILE_DURATION` |
| `instr_1_height` | `SA_HEIGHT` |
| `instr_1_wformat` | `SA_WIND_DATA_FORMAT` |
| `instr_1_wref` | `SA_NORTH_ALIGNEMENT` |
| `instr_1_north_offset` | `SA_NORTH_OFFSET` |
| `instr_2_tube_length` | `GA_TUBE_LENGTH` |
| `instr_2_tube_diameter` | `GA_TUBE_DIAMETER` |
| `instr_2_tube_flowrate` | `GA_FLOWRATE` |
| `instr_2_northward_separation` | `GA_NORTHWARD_SEPARATION` |
| `instr_2_eastward_separation` | `GA_EASTWARD_SEPARATION` |
| `instr_2_vertical_separation` | `GA_VERTICAL_SEPARATION` |

### ECMD selection rule

- If multiple ECMD rows exist, select the row where `DATE_OF_VARIATION_EF` (format `YYYYMMDDHHMM`) is **closest to but not later than** the start of the processing year.
- For `--year 2025`, use the row at `202501010000` if available.
- If the earliest ECMD row is **after** the processing year start, raise an error.

## Implementation plan

### 1. Add ECMD row selector utility

Create a new function in [src/eddypro_batch_processor/ecmd.py](src/eddypro_batch_processor/ecmd.py) to load and select the ECMD row for a given site and year.

**Proposed behavior:**

- Read ECMD CSV.
- Filter by `SITEID == site_id`.
- Parse `DATE_OF_VARIATION_EF` using the existing `parse_ecmd_date()`.
- Determine the target timestamp for the processing year: `YYYY-01-01 00:00`.
- Select the row with the latest `DATE_OF_VARIATION_EF` that is `<= target`.
- If no such row exists and the earliest row is after target, raise `ECMDError` with an actionable message.

**Return value:**

- A mapping of ECMD column name → value (strings preserved for INI compatibility).

### 2. Add metadata patcher in ini_tools.py

Add a function in [src/eddypro_batch_processor/ini_tools.py](src/eddypro_batch_processor/ini_tools.py) that:

- Reads the .metadata template (already copied into the scenario output dir).
- Applies the static updates (`file_name`, `site_id`).
- Applies ECMD-derived fields into the correct sections:
  - `file_name` → `[Project]`
  - `site_id` → `[Site]`
  - `altitude`, `canopy_height`, `latitude`, `longitude` → `[Site]`
  - `acquisition_frequency`, `file_duration` → `[Timing]`
  - `instr_1_*` → `[Instruments]`
  - `instr_2_*` → `[Instruments]`
- Writes the updated .metadata file in-place using the same formatting rules as `write_ini_file()` (no spaces around `=`, LF line endings).

### 3. Wire the call immediately after .eddypro write

Update the flow so that .metadata population is invoked **after** the .eddypro file is written. The cleanest option is to add a new helper in ini_tools.py that:

1. Writes the .eddypro file (existing `write_ini_file()` logic).
2. Populates the .metadata file using the ECMD selector and patcher.

This keeps the sequencing requirement (“inside ini_tools.py just after writing the .eddypro file”) while minimizing changes in the core orchestration in [src/eddypro_batch_processor/core.py](src/eddypro_batch_processor/core.py).

### 4. Tests

Add unit tests for:

- ECMD selection logic (exact match, nearest earlier, error when all rows are later).
- Metadata patching (section/key correctness, required fields set).
- End-to-end scenario run in dry-run mode to ensure .metadata is populated.

Likely locations:
- [tests/test_ecmd.py](tests/test_ecmd.py) (new or existing)
- [tests/test_ini_tools.py](tests/test_ini_tools.py)
- [tests/test_e2e_integration.py](tests/test_e2e_integration.py)

### 5. Documentation and changelog

- Update [docs/CONFIG.md](docs/CONFIG.md) or [docs/SCENARIOS.md](docs/SCENARIOS.md) only if user-facing behavior needs to be documented.
- Add an entry under **[Unreleased]** in [CHANGELOG.md](CHANGELOG.md).

## Open questions (for confirmation)

1. Should `file_name` in .metadata be stored with forward slashes (EddyPro style) even on Windows?
2. If an ECMD value is missing (empty string), should we leave the .metadata field blank, or raise a validation error?
3. Should `station_id` or `station_name` in [Station] also be populated with `site_id`, or left untouched?
