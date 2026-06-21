"""Tests for the LLM provider factory."""
import pytest

from app.llm.base import LLMProvider
from app.llm.factory import build_provider


def test_build_openai_provider():
    p = build_provider({"provider": "openai", "api_key": "k", "model_name": "gpt-x", "base_url": None})
    assert isinstance(p, LLMProvider)
    assert type(p).__name__ == "OpenAIProvider"


def test_build_claude_provider():
    p = build_provider({"provider": "claude", "api_key": "k", "model_name": "claude-x"})
    assert type(p).__name__ == "ClaudeProvider"


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        build_provider({"provider": "wat", "api_key": "k", "model_name": "m"})


def test_missing_fields_raises():
    with pytest.raises(ValueError):
        build_provider({"provider": "openai", "model_name": "m"})  # no api_key
