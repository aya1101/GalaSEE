import unittest

import numpy as np
from rasterio.transform import from_origin

from api.tideaware.polygonize import candidate_feature_collection


class PolygonizeTests(unittest.TestCase):
    def test_filters_small_components_and_reports_area(self):
        mask = np.array([[True, True, False], [False, False, True], [False, False, True]])
        result = candidate_feature_collection(mask, from_origin(500000, 1200000, 100, 100), "EPSG:32648", min_pixels=2)
        self.assertEqual(result["type"], "FeatureCollection")
        self.assertEqual(len(result["features"]), 2)
        self.assertTrue(all(feature["properties"]["pixelCount"] >= 2 for feature in result["features"]))
        self.assertAlmostEqual(result["properties"]["candidateAreaHa"], 4.0)


if __name__ == "__main__":
    unittest.main()
