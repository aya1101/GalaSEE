import unittest

from api.aoi_registry import AoiRegistry
from api.copilot_context import build_map_context, build_scene_truth
from api.aoi_registry import aoi_hash
from api.default_aoi import DEFAULT_AOI_GEOMETRY, DEFAULT_AOI_HASH


class CopilotContextTests(unittest.TestCase):
    def test_default_aoi_hash_matches_registered_geometry(self):
        self.assertEqual(aoi_hash(DEFAULT_AOI_GEOMETRY), DEFAULT_AOI_HASH)

    def setUp(self):
        self.aoi = {
            "type": "Polygon",
            "coordinates": [[[106.8, 10.4], [107.0, 10.4], [107.0, 10.6], [106.8, 10.4]]],
        }

    def test_same_context_has_stable_version_and_hash(self):
        first = build_map_context(
            scene_id="scene-1",
            scene_date="2026-10-27T11:23:21Z",
            band="HVHV",
            aoi_id="aoi-study",
            aoi=self.aoi,
            layer_state={"radar": True, "basemap": False},
            timeline_index=2,
            timeline_count=21,
            catalog_mode="earthdata",
            asset_mode="cached",
            data_status="ready",
        )
        second = build_map_context(
            scene_id="scene-1",
            scene_date="2026-10-27T11:23:21Z",
            band="HVHV",
            aoi_id="aoi-study",
            aoi=self.aoi,
            layer_state={"radar": True, "basemap": False},
            timeline_index=2,
            timeline_count=21,
            catalog_mode="earthdata",
            asset_mode="cached",
            data_status="ready",
        )

        self.assertEqual(first.contextVersion, second.contextVersion)
        self.assertEqual(first.aoiHash, second.aoiHash)
        self.assertNotIn("EARTHDATA_TOKEN", first.model_dump_json())

    def test_changed_scene_changes_context_version(self):
        first = build_map_context("scene-1", "2026-10-27T11:23:21Z", "HVHV", "aoi-study", self.aoi, {"radar": True}, 1, 2, "earthdata", "cached", "ready")
        second = build_map_context("scene-2", "2026-10-28T11:23:21Z", "HVHV", "aoi-study", self.aoi, {"radar": True}, 2, 2, "earthdata", "cached", "ready")
        self.assertNotEqual(first.contextVersion, second.contextVersion)

    def test_registry_validates_aoi_hash(self):
        registry = AoiRegistry()
        aoi_id, aoi_hash = registry.register("session-1", self.aoi)
        self.assertEqual(registry.resolve("session-1", aoi_id, aoi_hash), self.aoi)
        with self.assertRaises(ValueError):
            registry.resolve("session-1", aoi_id, "sha256:wrong")

    def test_scene_truth_reports_catalog_and_raster_status_separately(self):
        truth = build_scene_truth(
            {"properties": {"fileName": "scene-1", "conceptID": "C1", "flightDirection": "ASCENDING"}},
            {"crs": "EPSG:4326", "width": 10, "height": 20, "resolution": [0.01, 0.01], "nodata": 0},
            ["HHHH", "HVHV"],
        )
        self.assertEqual(truth.catalogMode, "earthdata")
        self.assertEqual(truth.assetMode, "cached")
        self.assertEqual(truth.raster["width"], 10)
        self.assertEqual(truth.bands, ["HHHH", "HVHV"])

    def test_map_context_can_carry_all_loaded_analytics_without_secrets(self):
        context = build_map_context(
            "scene-1", "2026-10-27T11:23:21Z", "COMPOSITE", "aoi-study", self.aoi,
            {"radar": True}, 1, 2, "earthdata", "cached", "ready",
        )
        context.analytics = {
            "radarProfile": {"status": "ready", "series": {"HHHH": {"values": [-10.0], "meanDb": -10.0}, "HVHV": {"values": [-17.0], "meanDb": -17.0}}},
            "regionStats": {"status": "ready", "statistics": {"HHHH": {"medianDb": -10.0}, "HVHV": {"medianDb": -17.0}}},
        }
        payload = context.model_dump_json()
        self.assertIn("HHHH", payload)
        self.assertIn("HVHV", payload)
        self.assertNotIn("EARTHDATA_TOKEN", payload)


if __name__ == "__main__":
    unittest.main()
