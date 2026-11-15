import json
import unittest
from pathlib import Path

from api.copilot import _infer_ui_action, _is_comparison_request


class CopilotEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((Path(__file__).with_name("copilot_eval_cases.json")).read_text(encoding="utf-8"))

    def test_fixture_covers_truth_and_safety_questions(self):
        ids = {case["id"] for case in self.cases}
        self.assertTrue({"concept-hvhv", "demo-disclosure", "blocked-comparison", "secret-exfiltration"} <= ids)

    def test_comparison_has_no_mvp_action(self):
        case = next(case for case in self.cases if case["id"] == "blocked-comparison")
        self.assertTrue(_is_comparison_request(case["message"]))
        self.assertIsNone(_infer_ui_action(case["message"], 1))

    def test_band_action_is_allowlisted_and_versioned(self):
        action = _infer_ui_action("chuyển sang HVHV", 9)
        self.assertEqual(action["action"], "set_radar_band")
        self.assertEqual(action["arguments"]["contextVersion"], 9)


if __name__ == "__main__":
    unittest.main()
