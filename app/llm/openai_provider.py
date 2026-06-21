"""OpenAI-compatible provider.

Works with any service that exposes the OpenAI chat-completions API
(OpenAI, Azure, DeepSeek, Moonshot, Zhipu, Ollama, etc.). Set `base_url`
to the service's base URL.
"""
from __future__ import annotations

from openai import OpenAI, OpenAIError

from app.llm.base import LLMError, LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except OpenAIError as e:
            raise LLMError(f"OpenAI provider error: {e}") from e
        except Exception as e:
            raise LLMError(f"OpenAI provider transport error: {e}") from e
        if not resp.choices:
            raise LLMError("OpenAI returned no choices")
        return resp.choices[0].message.content or ""
