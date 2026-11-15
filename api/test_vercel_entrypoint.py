import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class VercelEntrypointTests(unittest.TestCase):
    def test_entrypoint_loads_when_service_root_is_flattened(self):
        source_root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as temp_dir:
            service_root = Path(temp_dir)
            for source in source_root.iterdir():
                if source.name in {".venv", "__pycache__"}:
                    continue
                destination = service_root / source.name
                if source.is_dir():
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)

            result = subprocess.run(
                [sys.executable, "-c", "import vercel_entrypoint; print(vercel_entrypoint.app.title)"],
                cwd=service_root,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TideAware API", result.stdout)


if __name__ == "__main__":
    unittest.main()
