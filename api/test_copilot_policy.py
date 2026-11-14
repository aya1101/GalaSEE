import unittest

from api.copilot_policy import ALLOWED_UI_ACTIONS, validate_action, validate_tool_name


class CopilotPolicyTests(unittest.TestCase):
    def test_comparison_is_not_an_mvp_action(self):
        self.assertNotIn("open_comparison", ALLOWED_UI_ACTIONS)
        with self.assertRaises(ValueError):
            validate_action({"action": "open_comparison", "arguments": {}})

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tool_name("fetch_arbitrary_url")

    def test_safe_band_action_is_typed(self):
        action = validate_action({"action": "set_radar_band", "arguments": {"band": "HVHV"}})
        self.assertEqual(action["arguments"]["band"], "HVHV")
