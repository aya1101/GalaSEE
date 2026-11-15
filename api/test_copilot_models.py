import unittest

from api.copilot_models import (
    AssetMode,
    CatalogMode,
    DataStatus,
    EarthdataTruthResponse,
)


class CopilotModelTests(unittest.TestCase):
    def test_catalog_and_asset_truth_are_independent(self):
        payload = EarthdataTruthResponse(
            catalogMode=CatalogMode.earthdata,
            assetMode=AssetMode.cached,
            dataStatus=DataStatus.ready,
            source="cached-geotiff",
            payload={"scene": "scene-1"},
        )

        self.assertEqual(payload.catalogMode, "earthdata")
        self.assertEqual(payload.assetMode, "cached")
        self.assertEqual(payload.dataStatus, "ready")

    def test_error_does_not_look_like_demo(self):
        payload = EarthdataTruthResponse(
            catalogMode=CatalogMode.error,
            assetMode=AssetMode.unavailable,
            dataStatus=DataStatus.error,
            source="asf-search-api",
            errorCode="UPSTREAM_TIMEOUT",
            payload={},
        )

        self.assertNotEqual(payload.catalogMode, "demo")
        self.assertEqual(payload.dataStatus, "error")


if __name__ == "__main__":
    unittest.main()
