import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from .gcov_analytics import AnalyticsError, compare_rasters, power_to_db, region_statistics, sample_pixel


class GcovAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.transform = from_origin(106.7, 10.7, 0.01, 0.01)
        self.crs = "EPSG:4326"

    def tearDown(self):
        self.directory.cleanup()

    def write_raster(self, name: str, values: np.ndarray) -> Path:
        path = self.root / name
        with rasterio.open(path, "w", driver="GTiff", height=values.shape[0], width=values.shape[1], count=1, dtype="float32", crs=self.crs, transform=self.transform, nodata=0) as target:
            target.write(values.astype("float32"), 1)
        return path

    def test_power_to_db_uses_ten_log10_and_invalid_is_nan(self):
        output = power_to_db(np.array([1.0, 0.1, 0.0, -1.0], dtype="float32"))
        self.assertAlmostEqual(float(output[0]), 0.0, places=5)
        self.assertAlmostEqual(float(output[1]), -10.0, places=5)
        self.assertTrue(np.isnan(output[2]))
        self.assertTrue(np.isnan(output[3]))

    def test_region_statistics_and_pixel_nodata(self):
        values = np.array([[1, 2, 0], [4, 8, 16], [0, 32, 64]], dtype="float32")
        path = self.write_raster("scene.tif", values)
        stats = region_statistics(path)
        self.assertEqual(stats["validPixelCount"], 7)
        self.assertAlmostEqual(stats["validCoveragePercent"], 7 / 9 * 100, places=4)
        self.assertAlmostEqual(stats["medianDb"], 10 * np.log10(8), places=4)
        inside = sample_pixel(path, 106.705, 10.695)
        self.assertTrue(inside["valid"])
        outside = sample_pixel(path, 106.8, 10.8)
        self.assertFalse(outside["valid"])

    def test_compare_rasters_creates_three_db_candidate_and_delta(self):
        left = self.write_raster("t1.tif", np.ones((5, 5), dtype="float32"))
        right_values = np.ones((5, 5), dtype="float32")
        right_values[1:4, 1:4] = 10 ** 0.4
        right = self.write_raster("t2.tif", right_values)
        output = self.root / "delta.tif"
        result = compare_rasters(left, right, threshold_db=3, min_pixels=9, output_path=output)
        self.assertTrue(output.is_file())
        self.assertEqual(result["candidate"]["type"], "FeatureCollection")
        self.assertGreaterEqual(len(result["candidate"]["features"]), 1)
        self.assertGreater(result["candidate"]["features"][0]["properties"]["areaHa"], 0)
        self.assertAlmostEqual(result["statistics"]["meanDb"], 1.44, places=2)

    def test_compare_rasters_blocks_grid_mismatch(self):
        left = self.write_raster("left.tif", np.ones((3, 3), dtype="float32"))
        path = self.root / "right.tif"
        with rasterio.open(path, "w", driver="GTiff", height=3, width=3, count=1, dtype="float32", crs=self.crs, transform=from_origin(106.71, 10.7, 0.01, 0.01), nodata=0) as target:
            target.write(np.ones((3, 3), dtype="float32"), 1)
        with self.assertRaises(AnalyticsError):
            compare_rasters(left, path)


if __name__ == "__main__":
    unittest.main()
