import os
import unittest
from pathlib import Path
from unittest.mock import patch

from . import main


class MainCacheTests(unittest.TestCase):
    def test_vercel_defaults_to_writable_tmp_cache(self):
        with patch.dict(os.environ, {"VERCEL": "1", "GCOV_CACHE_DIR": ""}, clear=False):
            self.assertEqual(main.default_gcov_cache_dir(), Path(os.getenv("TMPDIR", "/tmp")) / "tideaware" / "gcov")

    def test_local_defaults_to_repository_cache(self):
        with patch.dict(os.environ, {"VERCEL": "", "GCOV_CACHE_DIR": ""}, clear=False):
            self.assertEqual(main.default_gcov_cache_dir(), main.REPOSITORY_ROOT / ".cache" / "gcov")


if __name__ == "__main__":
    unittest.main()
