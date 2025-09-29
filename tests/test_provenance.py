import json
import time
from pathlib import Path
import unittest

from src.provenance import RunContext, generate_provenance


class TestProvenance(unittest.TestCase):
    def test_generate_provenance_basic(self):
        run_dir = Path("data/processed/test-site")
        if run_dir.exists():
            # Clean previous
            for f in run_dir.glob("provenance.json*"):
                f.unlink()
        start = time.time()
        ctx = RunContext(
            site_id="TEST",
            years=[2024],
            total_raw_files=10,
            processed_raw_files=10,
            input_root=Path("data/raw/TEST"),
            processed_root=Path("data/processed/TEST"),
            config={"a": 1, "secret_token": "xyz"},
            redact_keys=["secret_token"],
            include_environment=False,
            start_time=start,
            end_time=start + 1.234,
        )
        manifest_path = generate_provenance(run_dir, ctx)
        self.assertTrue(manifest_path.exists())
        data = json.loads(manifest_path.read_text())
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["run"]["site_id"], "TEST")
        self.assertEqual(data["run"]["processed_raw_files"], 10)
        self.assertIn("config", data)
        self.assertEqual(data["config"]["excerpt"]["secret_token"], "***REDACTED***")
        self.assertAlmostEqual(data["duration_seconds"], 1.234, places=2)


if __name__ == "__main__":
    unittest.main()
