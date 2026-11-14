import unittest

from api.copilot_schemas import CopilotAnswer, UiAction
from api.llm_provider import ProviderDisabledError, parse_openrouter_sse_line
from api.openrouter_provider import OpenRouterProvider, extract_url_citations


class LlmProviderTests(unittest.TestCase):
    def test_parses_openrouter_sse_data_line(self):
        event = parse_openrouter_sse_line('data: {"choices":[{"delta":{"content":"HVHV"}}]}')
        self.assertEqual(event["choices"][0]["delta"]["content"], "HVHV")

    def test_done_line_is_ignored(self):
        self.assertIsNone(parse_openrouter_sse_line("data: [DONE]"))

    def test_extracts_and_deduplicates_web_citations(self):
        citations = extract_url_citations({
            "choices": [{"delta": {"annotations": [
                {"type": "url_citation", "url": "https://docs.asf.alaska.edu/gcov", "title": "ASF GCOV"},
                {"type": "url_citation", "url": "https://docs.asf.alaska.edu/gcov", "title": "ASF GCOV duplicate"},
            ]}}],
        })
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["url"], "https://docs.asf.alaska.edu/gcov")

    def test_missing_key_disables_provider(self):
        provider = OpenRouterProvider({"OPENROUTER_API_KEY": "", "OPENROUTER_MODEL": "qwen/test"})
        self.assertFalse(provider.enabled)
        with self.assertRaises(ProviderDisabledError):
            provider.require_enabled()

    def test_supports_api_url_alias_without_exposing_credentials(self):
        provider = OpenRouterProvider({
            "OPENROUTER_API_KEY": "secret",
            "OPENROUTER_MODEL": "openai/test",
            "OPENROUTER_API_URL": "https://openrouter.ai/api/v1",
        })
        self.assertTrue(provider.enabled)
        self.assertEqual(provider.base_url, "https://openrouter.ai/api/v1")

    def test_actions_reject_comparison(self):
        with self.assertRaises(ValueError):
            UiAction.model_validate({"action": "open_comparison", "arguments": {}})

    def test_answer_schema_requires_status(self):
        answer = CopilotAnswer.model_validate({"text": "Không có dữ liệu", "status": "UNKNOWN"})
        self.assertEqual(answer.status, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
