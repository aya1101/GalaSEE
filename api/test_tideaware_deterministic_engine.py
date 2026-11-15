import unittest

import numpy as np

from api.tideaware.deterministic_engine import (
    cusum_decrease,
    pixelwise_ols,
    robust_z_labels,
    run_track_analysis,
)


class DeterministicEngineTests(unittest.TestCase):
    def test_pixelwise_ols_recovers_tide_slope_and_loo_baseline(self):
        tide = np.array([0.0, 1.0, 2.0, 3.0])
        reference = np.stack([10.0 + 2.0 * tide[index] for index in range(4)])[:, None, None]
        result = pixelwise_ols(reference, tide)
        self.assertAlmostEqual(float(result.intercept[0, 0]), 10.0, places=5)
        self.assertAlmostEqual(float(result.slope[0, 0]), 2.0, places=5)
        self.assertGreater(float(result.r2[0, 0]), 0.99)
        self.assertLess(result.loo_rmse_tide, result.loo_rmse_baseline)

    def test_robust_z_labels_a_large_negative_change(self):
        reference = np.array([[[10.0]], [[10.2]], [[9.8]], [[10.1]]])
        monitoring = np.array([[[9.5]]])
        result = robust_z_labels(
            reference,
            monitoring,
            vegetation_mask=np.ones((1, 1), dtype=bool),
            z_thr=-3.0,
            z_pos=3.0,
            min_db_drop=0.5,
        )
        self.assertEqual(int(result.labels[0, 0, 0]), 1)
        self.assertLess(float(result.z_maps[0, 0, 0]), -3.0)

    def test_cusum_flags_repeated_negative_z(self):
        z_maps = [np.array([[-4.0]]), np.array([[-4.0]])]
        result = cusum_decrease(z_maps, k=0.5, h=4.0)
        self.assertFalse(bool(result.flags[0][0, 0]))
        self.assertTrue(bool(result.flags[1][0, 0]))
        self.assertGreater(float(result.score[0, 0]), 4.0)

    def test_track_analysis_keeps_original_when_monitoring_tide_is_missing(self):
        roles = ["Reference_1", "Reference_2", "Reference_3", "Reference_4", "Monitoring_1", "Monitoring_2"]
        tide = np.array([0.0, 1.0, 2.0, 3.0, np.nan, np.nan])
        stack = np.array([[[10.0]], [[10.1]], [[9.9]], [[10.0]], [[9.0]], [[8.5]]])
        result = run_track_analysis(
            track="047",
            roles=roles,
            stacks={"HHHH": stack, "HVHV": stack - 2.0},
            tide_levels=tide,
            vegetation_mask=np.ones((1, 1), dtype=bool),
            min_patch=1,
        )
        self.assertFalse(result["corrected_available"])
        self.assertIn("Missing Monitoring tide", result["warnings"])
        self.assertEqual(result["bands"]["HHHH"]["original"].labels.shape[0], 2)


if __name__ == "__main__":
    unittest.main()
