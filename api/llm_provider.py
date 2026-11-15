import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol


class ProviderDisabledError(RuntimeError):
    pass


def parse_openrouter_sse_line(line: str) -> dict[str, Any] | None:
    if not line.startswith("data:"):
        return None
    payload = line.removeprefix("data:").strip()
    if not payload or payload == "[DONE]":
        return None
    value = json.loads(payload)
    return value if isinstance(value, dict) else None


@dataclass(frozen=True)
class LlmEvent:
    kind: str
    text: str = ""
    tool_calls: tuple[dict[str, Any], ...] = ()
    citations: tuple[dict[str, Any], ...] = ()
    raw: dict[str, Any] | None = None


class LlmProvider(Protocol):
    async def stream(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AsyncIterator[LlmEvent]: ...
