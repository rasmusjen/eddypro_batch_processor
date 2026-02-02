"""Tests for ECMD utilities."""

from pathlib import Path

import pytest

from eddypro_batch_processor import ecmd


def _write_ecmd_file(path: Path, rows: list[dict[str, str]]) -> None:
    header = [
        "DATE_OF_VARIATION_EF",
        "SITEID",
        "ALTITUDE",
        "CANOPY_HEIGHT",
        "LATITUDE",
        "LONGITUDE",
        "ACQUISITION_FREQUENCY",
        "FILE_DURATION",
        "SA_HEIGHT",
        "SA_WIND_DATA_FORMAT",
        "SA_NORTH_ALIGNEMENT",
        "SA_NORTH_OFFSET",
        "GA_TUBE_LENGTH",
        "GA_TUBE_DIAMETER",
        "GA_FLOWRATE",
        "GA_NORTHWARD_SEPARATION",
        "GA_EASTWARD_SEPARATION",
        "GA_VERTICAL_SEPARATION",
    ]
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(row.get(col, "") for col in header))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_select_ecmd_row_for_year_exact_and_nearest(tmp_path: Path) -> None:
    ecmd_path = tmp_path / "ecmd.csv"
    rows = [
        {
            "DATE_OF_VARIATION_EF": "202001010000",
            "SITEID": "SITE",
            "ALTITUDE": "10",
            "CANOPY_HEIGHT": "0.5",
            "LATITUDE": "1.0",
            "LONGITUDE": "2.0",
            "ACQUISITION_FREQUENCY": "10",
            "FILE_DURATION": "30",
            "SA_HEIGHT": "3.1",
            "SA_WIND_DATA_FORMAT": "uvw",
            "SA_NORTH_ALIGNEMENT": "spar",
            "SA_NORTH_OFFSET": "60",
            "GA_TUBE_LENGTH": "71.1",
            "GA_TUBE_DIAMETER": "5.3",
            "GA_FLOWRATE": "12",
            "GA_NORTHWARD_SEPARATION": "-11",
            "GA_EASTWARD_SEPARATION": "-18",
            "GA_VERTICAL_SEPARATION": "0",
        },
        {
            "DATE_OF_VARIATION_EF": "202101010000",
            "SITEID": "SITE",
            "ALTITUDE": "20",
            "CANOPY_HEIGHT": "0.8",
            "LATITUDE": "1.1",
            "LONGITUDE": "2.1",
            "ACQUISITION_FREQUENCY": "20",
            "FILE_DURATION": "60",
            "SA_HEIGHT": "3.2",
            "SA_WIND_DATA_FORMAT": "uvw",
            "SA_NORTH_ALIGNEMENT": "spar",
            "SA_NORTH_OFFSET": "61",
            "GA_TUBE_LENGTH": "72.1",
            "GA_TUBE_DIAMETER": "5.4",
            "GA_FLOWRATE": "13",
            "GA_NORTHWARD_SEPARATION": "-10",
            "GA_EASTWARD_SEPARATION": "-17",
            "GA_VERTICAL_SEPARATION": "1",
        },
    ]
    _write_ecmd_file(ecmd_path, rows)

    selected_2021 = ecmd.select_ecmd_row_for_year(ecmd_path, "SITE", 2021)
    assert selected_2021["ALTITUDE"] == "20"
    assert selected_2021["FILE_DURATION"] == "60"

    selected_2020 = ecmd.select_ecmd_row_for_year(ecmd_path, "SITE", 2020)
    assert selected_2020["ALTITUDE"] == "10"
    assert selected_2020["FILE_DURATION"] == "30"


def test_select_ecmd_row_for_year_earliest_after_target_raises(
    tmp_path: Path,
) -> None:
    ecmd_path = tmp_path / "ecmd.csv"
    rows = [
        {
            "DATE_OF_VARIATION_EF": "202201010000",
            "SITEID": "SITE",
            "ALTITUDE": "10",
            "CANOPY_HEIGHT": "0.5",
            "LATITUDE": "1.0",
            "LONGITUDE": "2.0",
            "ACQUISITION_FREQUENCY": "10",
            "FILE_DURATION": "30",
            "SA_HEIGHT": "3.1",
            "SA_WIND_DATA_FORMAT": "uvw",
            "SA_NORTH_ALIGNEMENT": "spar",
            "SA_NORTH_OFFSET": "60",
            "GA_TUBE_LENGTH": "71.1",
            "GA_TUBE_DIAMETER": "5.3",
            "GA_FLOWRATE": "12",
            "GA_NORTHWARD_SEPARATION": "-11",
            "GA_EASTWARD_SEPARATION": "-18",
            "GA_VERTICAL_SEPARATION": "0",
        }
    ]
    _write_ecmd_file(ecmd_path, rows)

    with pytest.raises(ecmd.ECMDError):
        ecmd.select_ecmd_row_for_year(ecmd_path, "SITE", 2021)


def test_select_ecmd_row_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    with pytest.raises(ecmd.ECMDError):
        ecmd.select_ecmd_row_for_year(missing, "SITE", 2021)


def test_select_ecmd_row_missing_required_columns_raises(tmp_path: Path) -> None:
    ecmd_path = tmp_path / "ecmd.csv"
    ecmd_path.write_text("DATE_OF_VARIATION_EF,SITEID\n", encoding="utf-8")

    with pytest.raises(ecmd.ECMDError) as exc:
        ecmd.select_ecmd_row_for_year(ecmd_path, "SITE", 2021)
    assert "missing required columns" in str(exc.value).lower()


def test_select_ecmd_row_missing_date_value_raises(tmp_path: Path) -> None:
    ecmd_path = tmp_path / "ecmd.csv"
    rows = [
        {
            "DATE_OF_VARIATION_EF": "",
            "SITEID": "SITE",
            "ALTITUDE": "10",
            "CANOPY_HEIGHT": "0.5",
            "LATITUDE": "1.0",
            "LONGITUDE": "2.0",
            "ACQUISITION_FREQUENCY": "10",
            "FILE_DURATION": "30",
            "SA_HEIGHT": "3.1",
            "SA_WIND_DATA_FORMAT": "uvw",
            "SA_NORTH_ALIGNEMENT": "spar",
            "SA_NORTH_OFFSET": "60",
            "GA_TUBE_LENGTH": "71.1",
            "GA_TUBE_DIAMETER": "5.3",
            "GA_FLOWRATE": "12",
            "GA_NORTHWARD_SEPARATION": "-11",
            "GA_EASTWARD_SEPARATION": "-18",
            "GA_VERTICAL_SEPARATION": "0",
        }
    ]
    _write_ecmd_file(ecmd_path, rows)

    with pytest.raises(ecmd.ECMDError):
        ecmd.select_ecmd_row_for_year(ecmd_path, "SITE", 2021)


def test_select_ecmd_row_invalid_date_raises(tmp_path: Path) -> None:
    ecmd_path = tmp_path / "ecmd.csv"
    rows = [
        {
            "DATE_OF_VARIATION_EF": "not-a-date",
            "SITEID": "SITE",
            "ALTITUDE": "10",
            "CANOPY_HEIGHT": "0.5",
            "LATITUDE": "1.0",
            "LONGITUDE": "2.0",
            "ACQUISITION_FREQUENCY": "10",
            "FILE_DURATION": "30",
            "SA_HEIGHT": "3.1",
            "SA_WIND_DATA_FORMAT": "uvw",
            "SA_NORTH_ALIGNEMENT": "spar",
            "SA_NORTH_OFFSET": "60",
            "GA_TUBE_LENGTH": "71.1",
            "GA_TUBE_DIAMETER": "5.3",
            "GA_FLOWRATE": "12",
            "GA_NORTHWARD_SEPARATION": "-11",
            "GA_EASTWARD_SEPARATION": "-18",
            "GA_VERTICAL_SEPARATION": "0",
        }
    ]
    _write_ecmd_file(ecmd_path, rows)

    with pytest.raises(ecmd.ECMDError):
        ecmd.select_ecmd_row_for_year(ecmd_path, "SITE", 2021)


def test_select_ecmd_row_no_site_rows_raises(tmp_path: Path) -> None:
    ecmd_path = tmp_path / "ecmd.csv"
    rows = [
        {
            "DATE_OF_VARIATION_EF": "202001010000",
            "SITEID": "OTHER",
            "ALTITUDE": "10",
            "CANOPY_HEIGHT": "0.5",
            "LATITUDE": "1.0",
            "LONGITUDE": "2.0",
            "ACQUISITION_FREQUENCY": "10",
            "FILE_DURATION": "30",
            "SA_HEIGHT": "3.1",
            "SA_WIND_DATA_FORMAT": "uvw",
            "SA_NORTH_ALIGNEMENT": "spar",
            "SA_NORTH_OFFSET": "60",
            "GA_TUBE_LENGTH": "71.1",
            "GA_TUBE_DIAMETER": "5.3",
            "GA_FLOWRATE": "12",
            "GA_NORTHWARD_SEPARATION": "-11",
            "GA_EASTWARD_SEPARATION": "-18",
            "GA_VERTICAL_SEPARATION": "0",
        }
    ]
    _write_ecmd_file(ecmd_path, rows)

    with pytest.raises(ecmd.ECMDError):
        ecmd.select_ecmd_row_for_year(ecmd_path, "SITE", 2021)
