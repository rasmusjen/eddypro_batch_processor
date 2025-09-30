import sys
import unittest
from pathlib import Path

# Add src to path so we can import the module directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eddypro_batch_processor import process_year  # noqa: E402


class TestEddyProBatchProcessor(unittest.TestCase):
    def test_process_year_no_files(self):
        # Example test case where no files are present
        args = (
            2021,  # year
            "GL-ZaF",  # site_id
            "data/raw/{site_id}/{year}",  # input_dir_pattern
            "data/processed/{site_id}/{year}/eddypro/processing",  # output_dir_pattern
            None,  # eddypro_executable (mocked or None)
            False,  # stream_output
            None,  # template_file (mocked or None)
        )
        result = process_year(args)
        self.assertEqual(result, 0)

    # Add more test cases as needed


if __name__ == "__main__":
    unittest.main()
