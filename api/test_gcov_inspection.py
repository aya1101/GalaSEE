import unittest

from api.main import build_gcov_inspection, resolve_gcov_variable


class GcovInspectionTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "collections": [
                {
                    "id": "C3622241360-ASF/V1",
                    "title": "/science/LSAR/GCOV/grids/frequencyA/HHHH NISAR_L2_GCOV_V1 v1",
                    "description": "Frequency A HHHH",
                    "extent": {"spatial": {"crs": "CRS84"}},
                    "links": [{"title": "Perform rangeset request for /science/LSAR/GCOV/grids/frequencyA/HHHH"}],
                },
                {
                    "id": "C3622241360-ASF/V2",
                    "title": "/science/LSAR/GCOV/grids/frequencyB/HVHV NISAR_L2_GCOV_V1 v1",
                    "description": "Frequency B HVHV",
                    "links": [{"title": "Perform rangeset request for /science/LSAR/GCOV/grids/frequencyB/HVHV"}],
                },
                {
                    "id": "C3622241360-ASF/V3",
                    "title": "/science/LSAR/GCOV/grids/frequencyB/mask NISAR_L2_GCOV_V1 v1",
                    "links": [{"title": "Perform rangeset request for /science/LSAR/GCOV/grids/frequencyB/mask"}],
                },
            ]
        }

    def test_manifest_groups_discovered_paths_without_assuming_frequency_a(self):
        manifest = build_gcov_inspection("C3622241360-ASF", self.payload, None)

        self.assertEqual(manifest["frequencies"]["frequencyA"]["bands"], ["HHHH"])
        self.assertEqual(manifest["frequencies"]["frequencyB"]["bands"], ["HVHV"])
        self.assertEqual(manifest["metadata"]["extentCrs"], "CRS84")

    def test_plain_band_uses_deterministic_order_only_after_discovery(self):
        manifest = build_gcov_inspection("C3622241360-ASF", self.payload, None)

        self.assertEqual(resolve_gcov_variable(manifest, "HHHH")["path"], "/science/LSAR/GCOV/grids/frequencyA/HHHH")
        self.assertEqual(resolve_gcov_variable(manifest, "HVHV", "frequencyB")["path"], "/science/LSAR/GCOV/grids/frequencyB/HVHV")
        self.assertIsNone(resolve_gcov_variable(manifest, "HHHH", "frequencyB"))


if __name__ == "__main__":
    unittest.main()
