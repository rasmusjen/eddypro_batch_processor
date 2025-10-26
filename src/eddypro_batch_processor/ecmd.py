#!/usr/bin/env python3
"""
ECMD utilities for dynamic metadata generation.

Reads ECMD CSV files and generates EddyPro-compatible dynamic metadata files
with time-varying instrument configurations.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import NoReturn

logger = logging.getLogger(__name__)


class ECMDError(Exception):
    """Exception raised for ECMD processing errors."""

    pass


def parse_ecmd_date(date_str: str) -> datetime:
    """
    Parse ECMD date string in format YYYYMMDDHHMM.

    Args:
        date_str: Date string in YYYYMMDDHHMM format

    Returns:
        Parsed datetime object

    Raises:
        ECMDError: If date format is invalid
    """

    def _raise_parse_error(date_str: str, e: ValueError) -> NoReturn:
        raise ECMDError(f"Invalid ECMD date format '{date_str}': {e}") from e

    try:
        return datetime.strptime(date_str, "%Y%m%d%H%M")
    except ValueError as e:
        _raise_parse_error(date_str, e)


def generate_dynamic_metadata(
    ecmd_path: Path,
    output_path: Path,
    site_id: str,
) -> None:
    """
    Generate EddyPro dynamic metadata file from ECMD CSV.

    The dynamic metadata file contains time-varying instrument configurations
    with columns matching EddyPro's expected format. All ECMD rows for the site
    are included (all years) to allow EddyPro to find the correct configuration
    for any data file timestamp.

    Args:
        ecmd_path: Path to ECMD CSV file
        output_path: Path where dynamic metadata file will be written
        site_id: Site identifier to filter ECMD rows

    Raises:
        ECMDError: If ECMD file cannot be read or required columns are missing
        OSError: If output file cannot be written
    """
    if not ecmd_path.exists():
        raise ECMDError(f"ECMD file not found: {ecmd_path}")

    # EddyPro dynamic metadata columns (header row)
    output_columns = [
        "date",
        "time",
        "file_length",
        "acquisition_frequency",
        "canopy_height",
        "master_sonic_manufacturer",
        "master_sonic_model",
        "master_sonic_height",
        "master_sonic_wformat",
        "master_sonic_wref",
        "master_sonic_north_offset",
        "co2_irga_manufacturer",
        "co2_irga_model",
        "co2_irga_northward_separation",
        "co2_irga_eastward_separation",
        "co2_irga_tube_length",
        "co2_irga_tube_diameter",
        "co2_irga_flowrate",
        "h2o_irga_manufacturer",
        "h2o_irga_model",
        "h2o_irga_northward_separation",
        "h2o_irga_eastward_separation",
        "h2o_irga_tube_length",
        "h2o_irga_tube_diameter",
        "h2o_irga_flowrate",
    ]

    # Mapping from ECMD columns to dynamic metadata columns
    ecmd_to_dyn_md = {
        "FILE_DURATION": "file_length",
        "ACQUISITION_FREQUENCY": "acquisition_frequency",
        "CANOPY_HEIGHT": "canopy_height",
        "SA_MANUFACTURER": "master_sonic_manufacturer",
        "SA_MODEL": "master_sonic_model",
        "SA_HEIGHT": "master_sonic_height",
        "SA_WIND_DATA_FORMAT": "master_sonic_wformat",
        "SA_NORTH_ALIGNEMENT": "master_sonic_wref",
        "SA_NORTH_OFFSET": "master_sonic_north_offset",
        "GA_MANUFACTURER": "co2_irga_manufacturer",
        "GA_MODEL": "co2_irga_model",
        "GA_NORTHWARD_SEPARATION": "co2_irga_northward_separation",
        "GA_EASTWARD_SEPARATION": "co2_irga_eastward_separation",
        "GA_TUBE_LENGTH": "co2_irga_tube_length",
        "GA_TUBE_DIAMETER": "co2_irga_tube_diameter",
        "GA_FLOWRATE": "co2_irga_flowrate",
    }

    def _validate_ecmd_header(reader: csv.DictReader, ecmd_path: Path) -> None:
        """Validate ECMD CSV header has required columns."""
        if not reader.fieldnames:
            raise ECMDError(f"ECMD file has no header: {ecmd_path}")

        # Check required columns exist
        missing_cols = []
        for ecmd_col in ecmd_to_dyn_md:
            if ecmd_col not in reader.fieldnames and ecmd_col not in [
                "GA_TUBE_LENGTH",
                "GA_TUBE_DIAMETER",
                "GA_FLOWRATE",
            ]:
                # Tube fields are optional for open-path
                missing_cols.append(ecmd_col)

        if missing_cols:
            msg = f"ECMD file missing required columns: {', '.join(missing_cols)}"
            raise ECMDError(msg)

    filtered_rows = []

    try:
        with ecmd_path.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            _validate_ecmd_header(reader, ecmd_path)

            for row in reader:
                # Filter by site_id
                if row.get("SITEID", "").strip() != site_id:
                    continue

                # Parse effective date
                date_str = row.get("DATE_OF_VARIATION_EF", "")
                if not date_str:
                    logger.warning("Skipping ECMD row with no DATE_OF_VARIATION_EF")
                    continue

                try:
                    eff_date = parse_ecmd_date(date_str)
                except ECMDError as e:
                    logger.warning(f"Skipping ECMD row: {e}")
                    continue

                # Build output row (all years included for EddyPro to match timestamps)
                output_row = {}
                output_row["date"] = eff_date.strftime("%Y-%m-%d")
                output_row["time"] = eff_date.strftime("%H:%M")

                # Map ECMD columns to dynamic metadata columns
                for ecmd_col, dyn_md_col in ecmd_to_dyn_md.items():
                    value = row.get(ecmd_col, "").strip()
                    output_row[dyn_md_col] = value

                # H2O IRGA typically same as CO2 IRGA (shared analyzer)
                output_row["h2o_irga_manufacturer"] = output_row[
                    "co2_irga_manufacturer"
                ]
                output_row["h2o_irga_model"] = output_row["co2_irga_model"]
                output_row["h2o_irga_northward_separation"] = output_row[
                    "co2_irga_northward_separation"
                ]
                output_row["h2o_irga_eastward_separation"] = output_row[
                    "co2_irga_eastward_separation"
                ]
                output_row["h2o_irga_tube_length"] = output_row["co2_irga_tube_length"]
                output_row["h2o_irga_tube_diameter"] = output_row[
                    "co2_irga_tube_diameter"
                ]
                output_row["h2o_irga_flowrate"] = output_row["co2_irga_flowrate"]

                filtered_rows.append(output_row)

    except csv.Error as e:
        raise ECMDError(f"Error reading ECMD CSV {ecmd_path}: {e}") from e
    except Exception as e:
        raise ECMDError(f"Unexpected error processing ECMD {ecmd_path}: {e}") from e

    if not filtered_rows:
        logger.warning(f"No ECMD rows found for site {site_id}")

    # Write dynamic metadata file
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=output_columns)
            writer.writeheader()
            writer.writerows(filtered_rows)

        logger.info(
            f"Generated dynamic metadata: {output_path} "
            f"({len(filtered_rows)} configuration(s))"
        )

    except OSError as e:
        raise OSError(f"Failed to write dynamic metadata {output_path}: {e}") from e
