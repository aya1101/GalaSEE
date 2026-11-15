import unittest

from api.copilot import SERVER_TOOLS, TOOL_SCHEMAS, _infer_ui_action, _is_comparison_request, _needs_knowledge_base, sse_event


class CopilotApiTests(unittest.TestCase):
    def test_comparison_intent_is_detected_before_provider(self):
        self.assertTrue(_is_comparison_request("chạy so sánh hai scene"))
        self.assertTrue(_is_comparison_request("run change detection"))
        self.assertFalse(_is_comparison_request("HVHV là gì?"))

    def test_sse_event_is_json_and_not_buffered(self):
        self.assertEqual(sse_event("status", {"stage": "retrieving_sources"}), 'event: status\ndata: {"stage":"retrieving_sources"}\n\n')

    def test_knowledge_retrieval_is_reserved_for_concept_questions(self):
        self.assertTrue(_needs_knowledge_base("HVHV là gì?"))
        self.assertTrue(_needs_knowledge_base("giải thích dB"))
        self.assertFalse(_needs_knowledge_base("scene này có dữ liệu không?"))
        self.assertFalse(_needs_knowledge_base("mở thống kê khu vực"))

    def test_tool_schemas_exclude_comparison_and_include_read_only_tools(self):
        names = {item["function"]["name"] for item in TOOL_SCHEMAS}
        self.assertIn("get_current_map_context", names)
        self.assertIn("get_radar_profile", names)
        self.assertNotIn("get_comparison_status", names)

    def test_web_search_is_domain_limited(self):
        self.assertEqual(len(SERVER_TOOLS), 1)
        tool = SERVER_TOOLS[0]
        self.assertEqual(tool["type"], "openrouter:web_search")
        self.assertIn("docs.asf.alaska.edu", tool["parameters"]["allowed_domains"])
        self.assertIn("earthdata.nasa.gov", tool["parameters"]["allowed_domains"])
        self.assertEqual(tool["parameters"]["max_uses"], 2)

    def test_safe_map_commands_become_typed_actions(self):
        action = _infer_ui_action("chuyển sang HVHV", 2)
        self.assertEqual(action["action"], "set_radar_band")
        self.assertEqual(action["arguments"]["band"], "HVHV")
        self.assertEqual(action["arguments"]["contextVersion"], 2)
        self.assertEqual(_infer_ui_action("chạy so sánh hai scene", 2), None)


if __name__ == "__main__":
    unittest.main()
