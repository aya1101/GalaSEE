import tempfile
import unittest
from pathlib import Path

from .tideaware.jobs import read_run_state, run_state_path, write_run_state


class TideAwareJobStateTests(unittest.TestCase):
    def test_job_state_is_atomic_and_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = run_state_path(root, "abc12345")
            write_run_state(path, {"id": "abc12345", "status": "queued"})
            self.assertEqual(read_run_state(path)["status"], "queued")
            with self.assertRaises(ValueError):
                run_state_path(root, "../outside")


if __name__ == "__main__":
    unittest.main()
