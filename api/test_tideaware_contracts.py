import unittest

from api.tideaware.contracts import TideAwareRunRequest, validate_thresholds


class TideAwareContractTests(unittest.TestCase):
    def test_request_defaults_match_notebook_thresholds(self):
        request = TideAwareRunRequest(aoi={"type": "Polygon", "coordinates": []})
        self.assertEqual(request.track, "both")
        self.assertEqual(request.bands, ["HHHH", "HVHV"])
        self.assertEqual(request.z_thr, -3.0)
        self.assertEqual(request.z_pos, 3.0)
        self.assertEqual(request.min_db_drop, 1.5)
        self.assertEqual(request.cusum_k, 0.5)
        self.assertEqual(request.cusum_h, 4.0)
        self.assertEqual(request.min_patch, 3)

    def test_threshold_validation_rejects_non_negative_drop(self):
        with self.assertRaises(ValueError):
            validate_thresholds(z_thr=-3, z_pos=3, min_db_drop=0, cusum_k=0.5, cusum_h=4, min_patch=3)

    def test_request_never_accepts_an_earthdata_token(self):
        request = TideAwareRunRequest(aoi={"type": "Polygon", "coordinates": []})
        self.assertNotIn("EARTHDATA_TOKEN", request.model_dump())


if __name__ == "__main__":
    unittest.main()
