"""Tests for the OpenAI-compatible provider, using respx to mock HTTP."""
import respx
from httpx import Response

import pytest

from app.llm.base import LLMError
from app.llm.openai_provider import OpenAIProvider

BASE_URL = "https://api.example.com/v1"


def _make_provider(api_key: str = "test-key", model: str = "gpt-test") -> OpenAIProvider:
    return OpenAIProvider(api_key=api_key, model=model, base_url=BASE_URL)


@respx.mock
def test_chat_returns_assistant_content():
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": "Hello back"}}]},
        )
    )
    provider = _make_provider()
    out = provider.chat(system="You are helpful.", user="Hi")
    assert out == "Hello back"


@respx.mock
def test_chat_passes_temperature_and_max_tokens():
    route = respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    )
    provider = _make_provider()
    provider.chat(system="s", user="u", temperature=0.2, max_tokens=64)
    body = route.calls.last.request.content.decode()
    assert '"temperature":0.2' in body
    assert '"max_tokens":64' in body


@respx.mock
def test_chat_wraps_http_error_in_llm_error():
    respx.post(f"{BASE_URL}/chat/completions").mock(return_value=Response(500, text="boom"))
    provider = _make_provider()
    with pytest.raises(LLMError):
        provider.chat(system="s", user="u")
