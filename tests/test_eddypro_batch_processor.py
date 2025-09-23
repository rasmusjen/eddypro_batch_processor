import unittest
from src.eddypro_batch_processor import process_year

class TestEddyProBatchProcessor(unittest.TestCase):
    
    def test_process_year_no_files(self):
        # Example test case where no files are present
        args = (
            2021,               # year
            "GL-ZaF",           # site_id
            "data/raw/{site_id}/{year}",  # input_dir_pattern
            "data/processed/{site_id}/{year}/eddypro/processing",  # output_dir_pattern
            None,               # eddypro_executable (mocked or None)
            False,              # stream_output
            None,               # template_file (mocked or None)
            None                # path_ecmd (mocked or None)
        )
        result = process_year(args)
        self.assertEqual(result, 0)

    # Add more test cases as needed

if __name__ == '__main__':
    unittest.main()