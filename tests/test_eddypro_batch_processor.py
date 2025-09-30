import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add src to path so we can import the module directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eddypro_batch_processor import process_year  # noqa: E402
from eddypro_batch_processor.cli import main  # noqa: E402


class TestCLI(unittest.TestCase):
    def test_main_function(self):
        """Test that the CLI main function works and returns 0."""
        result = main()
        self.assertEqual(result, 0)

    def test_main_script_execution(self):
        """Test that the CLI can be executed as a script."""
        # Simply test that we can import and run the main function
        # The __main__ block is harder to test reliably without side effects
        result = main()
        self.assertEqual(result, 0)


class TestEddyProBatchProcessor(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.raw_data_dir = self.test_dir / "data" / "raw" / "GL-ZaF" / "2021"
        self.output_dir = (
            self.test_dir
            / "data"
            / "processed"
            / "GL-ZaF"
            / "2021"
            / "eddypro"
            / "processing"
        )
        self.config_dir = self.test_dir / "config"

        # Create directories
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal test files
        self.create_test_files()

    def create_test_files(self):
        """Create minimal test files for testing."""
        # Create test raw data files matching the expected pattern
        test_files = [
            "GL-ZaF_EC_202107011030_F10.csv",
            "GL-ZaF_EC_202107011100_F10.csv",
            "GL-ZaF_EC_202107011130_F10.csv",
        ]

        for filename in test_files:
            file_content = "timestamp,data\n2021-07-01 10:30:00,1.0\n"
            (self.raw_data_dir / filename).write_text(file_content)

        # Create template file with essential sections
        template_content = """[Project]
creation_date=
last_change_date=
file_name=
run_mode=0
project_title=
sw_version=7.0.9
project_id=
file_type=1
file_prototype=??????????yyyymmddHHMM????.csv
use_pfile=1
proj_file=
use_dyn_md_file=1
dyn_metadata_file=
out_path=

[RawProcess_General]
data_path=
recurse=1
use_geo_north=0
mag_dec=0

[RawProcess_Settings]
max_lack=10
u_offset=0
v_offset=0
w_offset=0
"""
        (self.config_dir / "EddyProProject_template.ini").write_text(template_content)

        # Create realistic ecmd file with proper columns and metadata
        header = (
            "DATE_OF_VARIATION_DB,DATE_OF_VARIATION_EF,SITEID,LATITUDE,LONGITUDE,"
            "ALTITUDE,CANOPY_HEIGHT,SA_MANUFACTURER,SA_MODEL,SA_SW_VERSION,"
            "SA_WIND_DATA_FORMAT,SA_NORTH_ALIGNEMENT,SA_HEIGHT,SA_NORTH_OFFSET,"
            "SA_NORTH_MAGDEC,SA_INVALID_WIND_SECTOR_c1,SA_INVALID_WIND_SECTOR_w1,"
            "SA_INVALID_WIND_SECTOR_c2,SA_INVALID_WIND_SECTOR_w2,"
            "SA_INVALID_WIND_SECTOR_c3,SA_INVALID_WIND_SECTOR_w3,GA_PATH,"
            "GA_MANUFACTURER,GA_MODEL,GA_SW_VERSION,GA_NORTHWARD_SEPARATION,"
            "GA_EASTWARD_SEPARATION,GA_VERTICAL_SEPARATION,GA_TUBE_DIAMETER,"
            "GA_FLOWRATE,GA_TUBE_LENGTH,FILE_DURATION,ACQUISITION_FREQUENCY,"
            "FILE_FORMAT,FILE_EXTENSION,LN,FN,EXTERNAL_TIMESTAMP,EOL,SEPARATOR,"
            "MISSING_DATA_STRING,NROW_HEADER,UVW_UNITS,T_SONIC_UNITS,"
            "T_CELL_UNITS,P_CELL_UNITS,CO2_measure_type,CO2_UNITS,"
            "H2O_measure_type,H2O_UNITS,SA_DIAG,GA_DIAG"
        )
        data_row = (
            "202107010000,202001010000,GL-ZaF,74.481522,-20.555773,38,0.1,"
            "gill,hs_50_1,3.01,uvw,spar,3.16,60,NA,105,20,247.5,55,NA,NA,"
            "closed,licor,li7200_1,8.8.28,-11,-18,0,5.3,12,71.1,30,10,"
            "ASCII,csv,1,10,END,crlf,comma,-9999,1,m_sec,celsius,celsius,"
            "kpa,mixing_ratio,ppm,mixing_ratio,ppt,dimensionless,dimensionless"
        )
        ecmd_content = f"{header}\n{data_row}"
        (self.test_dir / "data" / "GL-ZaF_ecmd.csv").write_text(ecmd_content)

    def test_process_year_with_files(self):
        """Test that process_year handles raw files processing correctly."""
        input_pattern = str(self.test_dir / "data" / "raw" / "{site_id}" / "{year}")
        output_pattern = str(
            self.test_dir
            / "data"
            / "processed"
            / "{site_id}"
            / "{year}"
            / "eddypro"
            / "processing"
        )
        ecmd_path = str(self.test_dir / "data" / "{site_id}_ecmd.csv")

        args = (
            2021,  # year
            "GL-ZaF",  # site_id
            input_pattern,  # input_dir_pattern
            output_pattern,  # output_dir_pattern
            None,  # eddypro_executable (mocked or None)
            False,  # stream_output
            self.config_dir / "EddyProProject_template.ini",  # template_file as Path
            ecmd_path,  # path_ecmd
        )

        # Mock the EddyPro execution since we don't have the actual executable
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = process_year(args)

        # Should return the number of raw files found (3 files)
        self.assertEqual(result, 3)

    def test_process_year_no_files(self):
        """Test that process_year handles case with no raw files."""
        # Create empty directory
        empty_dir = self.test_dir / "data" / "raw" / "empty-site" / "2021"
        empty_dir.mkdir(parents=True, exist_ok=True)

        input_pattern = str(self.test_dir / "data" / "raw" / "{site_id}" / "{year}")
        output_pattern = str(
            self.test_dir
            / "data"
            / "processed"
            / "{site_id}"
            / "{year}"
            / "eddypro"
            / "processing"
        )
        ecmd_path = str(self.test_dir / "data" / "{site_id}_ecmd.csv")

        args = (
            2021,  # year
            "empty-site",  # site_id
            input_pattern,  # input_dir_pattern
            output_pattern,  # output_dir_pattern
            None,  # eddypro_executable (mocked or None)
            False,  # stream_output
            self.config_dir / "EddyProProject_template.ini",  # template_file as Path
            ecmd_path,  # path_ecmd
        )

        # Create empty ecmd file for this site
        header = (
            "DATE_OF_VARIATION_DB,DATE_OF_VARIATION_EF,SITEID,LATITUDE,LONGITUDE,"
            "ALTITUDE,CANOPY_HEIGHT,SA_MANUFACTURER,SA_MODEL,SA_SW_VERSION,"
            "SA_WIND_DATA_FORMAT,SA_NORTH_ALIGNEMENT,SA_HEIGHT,SA_NORTH_OFFSET,"
            "SA_NORTH_MAGDEC,SA_INVALID_WIND_SECTOR_c1,SA_INVALID_WIND_SECTOR_w1,"
            "SA_INVALID_WIND_SECTOR_c2,SA_INVALID_WIND_SECTOR_w2,"
            "SA_INVALID_WIND_SECTOR_c3,SA_INVALID_WIND_SECTOR_w3,GA_PATH,"
            "GA_MANUFACTURER,GA_MODEL,GA_SW_VERSION,GA_NORTHWARD_SEPARATION,"
            "GA_EASTWARD_SEPARATION,GA_VERTICAL_SEPARATION,GA_TUBE_DIAMETER,"
            "GA_FLOWRATE,GA_TUBE_LENGTH,FILE_DURATION,ACQUISITION_FREQUENCY,"
            "FILE_FORMAT,FILE_EXTENSION,LN,FN,EXTERNAL_TIMESTAMP,EOL,SEPARATOR,"
            "MISSING_DATA_STRING,NROW_HEADER,UVW_UNITS,T_SONIC_UNITS,"
            "T_CELL_UNITS,P_CELL_UNITS,CO2_measure_type,CO2_UNITS,"
            "H2O_measure_type,H2O_UNITS,SA_DIAG,GA_DIAG"
        )
        data_row = (
            "202107010000,202001010000,empty-site,74.481522,-20.555773,38,0.1,"
            "gill,hs_50_1,3.01,uvw,spar,3.16,60,NA,105,20,247.5,55,NA,NA,"
            "closed,licor,li7200_1,8.8.28,-11,-18,0,5.3,12,71.1,30,10,"
            "ASCII,csv,1,10,END,crlf,comma,-9999,1,m_sec,celsius,celsius,"
            "kpa,mixing_ratio,ppm,mixing_ratio,ppt,dimensionless,dimensionless"
        )
        empty_ecmd = f"{header}\n{data_row}"
        (self.test_dir / "data" / "empty-site_ecmd.csv").write_text(empty_ecmd)

        result = process_year(args)
        # Should return 0 when no files are found
        self.assertEqual(result, 0)

    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.test_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
