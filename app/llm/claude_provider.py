"""Anthropic Claude provider (uses the official anthropic SDK)."""
from __future__ import annotations

import anthropic

from app.llm.base import LLMError, LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        try:
            resp = self._client.messages.create(
                model=self._model,
                system=system,
                messages=[{"role": "user", "content": user}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except anthropic.AnthropicError as e:
            raise LLMError(f"Claude provider error: {e}") from e
        except Exception as e:
            raise LLMError(f"Claude provider transport error: {e}") from e

        parts = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
        if not parts:
            raise LLMError("Claude returned no text content")
        return "".join(parts)
