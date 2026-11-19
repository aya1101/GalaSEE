import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from . import main


class MainCacheTests(unittest.TestCase):
    def test_vercel_entrypoint_imports_without_native_geospatial_modules(self):
        script = """
import builtins

real_import = builtins.__import__
blocked = {\"numpy\", \"rasterio\", \"scipy\", \"pyproj\", \"shapely\", \"PIL\"}

def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split(\".\", 1)[0] in blocked:
        raise ImportError(f\"blocked native module: {name}\")
    return real_import(name, globals, locals, fromlist, level)

builtins.__import__ = guarded_import
import vercel_entrypoint
assert vercel_entrypoint.app.title == \"TideAware API\"
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_vercel_defaults_to_writable_tmp_cache(self):
        with patch.dict(os.environ, {"VERCEL": "1", "GCOV_CACHE_DIR": ""}, clear=False):
            self.assertEqual(main.default_gcov_cache_dir(), main.runtime_temp_root() / "tideaware" / "gcov")

    def test_vercel_ignores_relative_local_cache_override(self):
        with patch.dict(os.environ, {"VERCEL": "1", "GCOV_CACHE_DIR": ".cache/gcov"}, clear=False):
            self.assertEqual(main.default_gcov_cache_dir(), main.runtime_temp_root() / "tideaware" / "gcov")

    def test_local_defaults_to_repository_cache(self):
        with patch.dict(os.environ, {"VERCEL": "", "GCOV_CACHE_DIR": ""}, clear=False):
            self.assertEqual(main.default_gcov_cache_dir(), main.REPOSITORY_ROOT / ".cache" / "gcov")


if __name__ == "__main__":
    unittest.main()
