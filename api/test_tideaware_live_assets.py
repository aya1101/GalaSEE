import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from api.tideaware.live_assets import AssetCompatibilityError, SceneAsset, ensure_live_scene_assets, read_common_stack, validate_asset_set


class LiveAssetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.transform = from_origin(500000, 1200000, 100, 100)

    def tearDown(self):
        self.directory.cleanup()

    def write(self, name: str, value: float, transform=None) -> Path:
        path = self.root / name
        with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=1, dtype="float32", crs="EPSG:32648", transform=transform or self.transform, nodata=np.nan) as target:
            target.write(np.full((2, 2), value, dtype="float32"), 1)
        return path

    def test_live_resolver_can_build_scene_assets_without_exposing_h5(self):
        path = self.write("scene.tif", 1.0)

        def resolver(scene_id: str, band: str):
            return path, {"unit": "power"}

        assets = ensure_live_scene_assets(["scene-1"], ["HHHH"], resolver)
        self.assertEqual(assets[0].unit, "power")
        self.assertNotIn("h5", str(assets[0].path).lower())

    def test_power_is_converted_to_db_once(self):
        path = self.write("scene.tif", 10.0)
        assets = [SceneAsset(scene_id="scene-1", band="HHHH", path=path, unit="power")]
        stack = read_common_stack(assets)
        self.assertAlmostEqual(float(stack["HHHH"][0, 0, 0]), 10.0, places=4)

    def test_grid_mismatch_is_blocked(self):
        first = self.write("first.tif", 1.0)
        second = self.write("second.tif", 1.0, from_origin(500100, 1200000, 100, 100))
        assets = [
            SceneAsset(scene_id="scene-1", band="HHHH", path=first, unit="power"),
            SceneAsset(scene_id="scene-2", band="HHHH", path=second, unit="power"),
        ]
        with self.assertRaises(AssetCompatibilityError):
            validate_asset_set(assets)


if __name__ == "__main__":
    unittest.main()
