"""LLM поверх Anthropic API (модель — settings.llm_model, по умолчанию Claude Sonnet 5.5).

Перед каждым вызовом проверяем, что в запросе нет ПИНФЛ, паспорта и телефона (NFR-A-02), и пишем
запрос в лог storozh.assistant.llm.requests — по этому логу тест проверяет, что персональные данные не уходят.
"""

import json
import logging
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

import anthropic

from storozh.assistant.llm.port import Effort, LLMError
from storozh.assistant.pii import contains_hard_pii
from storozh.shared.config import settings

requests_log = logging.getLogger("storozh.assistant.llm.requests")

# Серверный fallback при отказе (safety refusal) есть только у этих моделей.
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}


def _thinking(model: str, think: bool) -> dict[str, str]:
    """Быстрые вызовы (переписывание, объяснение тревоги, чат) идут без размышлений, если модель это позволяет."""
    if think or model.startswith("claude-opus-5-5") or model.startswith("claude-fable"):
        return {"type": "adaptive"}
    if model.startswith("claude-sonnet-5-5"):
        return {"type": "between_tools"}
    return {"type": "disabled"}


class AnthropicLLM:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.llm_model
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    def _request(self, system: str, messages: list[dict[str, Any]], *, max_tokens: int, effort: Effort,
                 think: bool, fmt: dict | None = None) -> dict[str, Any]:
        texts = [system] + [m["content"] if isinstance(m["content"], str) else json.dumps(m["content"])
                            for m in messages]
        if any(contains_hard_pii(t) for t in texts):
            raise LLMError("request contains personal data (PINFL/passport/phone)")
        requests_log.info("llm request", extra={"model": self.model, "system": system[:2000],
                                                "messages": [t[:4000] for t in texts[1:]]})
        output_config: dict[str, Any] = {"effort": effort}
        if fmt:
            output_config["format"] = fmt
        kw: dict[str, Any] = {"model": self.model, "max_tokens": max_tokens, "system": system,
                              "messages": messages, "thinking": _thinking(self.model, think),
                              "output_config": output_config}
        if self.model in _FALLBACK_MODELS:
            kw |= {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        return kw

    @staticmethod
    def _text(resp) -> str:
        if resp.stop_reason == "refusal":
            raise LLMError("model refused")
        return "".join(b.text for b in resp.content if b.type == "text")

    async def complete(self, system: str, user: str, *, max_tokens: int = 1024, timeout_s: float = 30,
                       effort: Effort = "low", think: bool = False) -> str:
        kw = self._request(system, [{"role": "user", "content": user}], max_tokens=max_tokens, effort=effort,
                           think=think)
        try:
            resp = await self.client.beta.messages.create(**kw, timeout=timeout_s)
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e
        return self._text(resp)

    async def complete_json(self, system: str, user: str, schema: dict[str, Any], *, max_tokens: int = 4096,
                            timeout_s: float = 60, effort: Effort = "medium", think: bool = True) -> dict[str, Any]:
        kw = self._request(system, [{"role": "user", "content": user}], max_tokens=max_tokens, effort=effort,
                           think=think, fmt={"type": "json_schema", "schema": schema})
        try:
            resp = await self.client.beta.messages.create(**kw, timeout=timeout_s)
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e
        try:
            return json.loads(self._text(resp))
        except json.JSONDecodeError as e:
            raise LLMError(f"bad JSON from model (stop_reason={resp.stop_reason})") from e

    async def stream(self, system: str, messages: list[dict[str, Any]], *, max_tokens: int = 4096,
                     effort: Effort = "low") -> AsyncIterator[str]:
        kw = self._request(system, messages, max_tokens=max_tokens, effort=effort, think=False)
        try:
            async with self.client.beta.messages.stream(**kw) as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e
        if final.stop_reason == "refusal":
            raise LLMError("model refused")


@lru_cache(maxsize=4)
def get_llm(model: str | None = None) -> AnthropicLLM:
    return AnthropicLLM(model)
