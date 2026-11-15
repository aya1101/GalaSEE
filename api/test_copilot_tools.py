import unittest

from api.copilot_context import build_map_context
from api.copilot_tools import ToolContext, ToolRegistry


class CopilotToolTests(unittest.TestCase):
    def setUp(self):
        aoi = {"type": "Polygon", "coordinates": [[[106.8, 10.4], [107.0, 10.4], [107.0, 10.6], [106.8, 10.4]]]}
        self.context = build_map_context("scene-1", "2026-10-27T11:23:21Z", "HVHV", "aoi-study", aoi, {"radar": True}, 1, 2, "earthdata", "cached", "ready")
        self.registry = ToolRegistry()

    def test_current_context_tool_returns_versioned_truth(self):
        result = self.registry.call("get_current_map_context", {}, ToolContext(self.context, "session-1"))
        self.assertEqual(result.status, "KNOWN")
        self.assertEqual(result.contextVersion, self.context.contextVersion)
        self.assertEqual(result.data["band"], "HVHV")

    def test_explain_layer_returns_approved_policy(self):
        result = self.registry.call("explain_layer", {"layer": "radar"}, ToolContext(self.context, "session-1"))
        self.assertEqual(result.status, "KNOWN")
        self.assertIn("radar", result.data["label"].lower())

    def test_scene_metadata_exposes_live_availability_from_map_context(self):
        result = self.registry.call("get_scene_metadata", {}, ToolContext(self.context, "session-1"))
        self.assertEqual(result.status, "KNOWN")
        self.assertTrue(result.data["hasRasterData"])
        self.assertEqual(result.data["dataStatus"], "ready")

    def test_unknown_comparison_tool_is_blocked(self):
        with self.assertRaises(ValueError):
            self.registry.call("get_comparison_status", {}, ToolContext(self.context, "session-1"))

    def test_stale_context_is_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.call("get_current_map_context", {"contextVersion": self.context.contextVersion + 1}, ToolContext(self.context, "session-1"))


if __name__ == "__main__":
    unittest.main()
