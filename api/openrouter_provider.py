import os
import json
from typing import Any, AsyncIterator

import httpx

from .llm_provider import LlmEvent, ProviderDisabledError, parse_openrouter_sse_line


def extract_url_citations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            annotations = value.get("annotations")
            if isinstance(annotations, list):
                for annotation in annotations:
                    if not isinstance(annotation, dict) or annotation.get("type") != "url_citation":
                        continue
                    url = annotation.get("url") or annotation.get("source_url")
                    if isinstance(url, str) and url.strip():
                        citations.append({
                            "url": url.strip(),
                            "title": str(annotation.get("title") or url).strip(),
                            "content": str(annotation.get("content") or "").strip(),
                        })
            for child in value.values():
                if child is not annotations:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    unique: dict[str, dict[str, Any]] = {}
    for citation in citations:
        unique.setdefault(citation["url"], citation)
    return list(unique.values())


class OpenRouterProvider:
    def __init__(self, env: dict[str, str] | None = None) -> None:
        values = env or os.environ
        self.api_key = values.get("OPENROUTER_API_KEY", "").strip()
        self.model = values.get("OPENROUTER_MODEL", "").strip()
        self.base_url = values.get("OPENROUTER_BASE_URL", values.get("OPENROUTER_API_URL", "https://openrouter.ai/api/v1")).rstrip("/")
        self.site_url = values.get("OPENROUTER_SITE_URL", "").strip()
        self.site_name = values.get("OPENROUTER_SITE_NAME", "TideAware").strip()
        self.enabled = bool(self.api_key and self.model)

    def require_enabled(self) -> None:
        if not self.enabled:
            raise ProviderDisabledError("OpenRouter copilot is not configured")

    async def stream(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AsyncIterator[LlmEvent]:
        self.require_enabled()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.site_name:
            headers["X-Title"] = self.site_name
        body = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "stream": True,
        }
        timeout = httpx.Timeout(connect=10, read=45, write=10, pool=10)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=body) as response:
                response.raise_for_status()
                tool_buffer: dict[int, dict[str, Any]] = {}
                async for line in response.aiter_lines():
                    payload = parse_openrouter_sse_line(line)
                    if not payload:
                        continue
                    choices = payload.get("choices") or []
                    delta = choices[0].get("delta", {}) if choices else {}
                    text = delta.get("content") or ""
                    if text:
                        yield LlmEvent(kind="token", text=text, raw=payload)
                    citations = extract_url_citations(payload)
                    if citations:
                        yield LlmEvent(kind="citations", citations=tuple(citations), raw=payload)
                    for index, call in enumerate(delta.get("tool_calls") or []):
                        target = tool_buffer.setdefault(index, {"id": "", "name": "", "arguments": ""})
                        if call.get("id"):
                            target["id"] = call["id"]
                        function = call.get("function") or {}
                        if function.get("name"):
                            target["name"] = function["name"]
                        target["arguments"] += function.get("arguments") or ""
                    finish_reason = choices[0].get("finish_reason") if choices else None
                    if finish_reason == "tool_calls":
                        calls = []
                        for call in tool_buffer.values():
                            calls.append({"id": call["id"], "name": call["name"], "arguments": json.loads(call["arguments"] or "{}")})
                        yield LlmEvent(kind="tool_calls", tool_calls=tuple(calls), raw=payload)
                yield LlmEvent(kind="done")
