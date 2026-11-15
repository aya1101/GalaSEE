from typing import Any, AsyncIterator

from .llm_provider import LlmEvent


class MockLlmProvider:
    enabled = True

    async def stream(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AsyncIterator[LlmEvent]:
        user_message = next((item.get("content", "") for item in reversed(messages) if item.get("role") == "user"), "").lower()
        if "so sánh" in user_message or "change detection" in user_message:
            yield LlmEvent(kind="token", text="Comparison hiện chưa được bật trong copilot MVP.")
            yield LlmEvent(kind="done")
            return
        if "hvhv" in user_message and "gì" in user_message:
            yield LlmEvent(kind="token", text="HVHV là thành phần covariance phân cực chéo của GCOV.")
        else:
            yield LlmEvent(kind="token", text="Mình cần đọc thêm dữ liệu scene hiện tại để trả lời chính xác.")
        yield LlmEvent(kind="done")
