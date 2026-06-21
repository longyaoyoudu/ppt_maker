"""Factory that builds the right LLMProvider from a config dict.

Expected config keys: provider ('openai'|'claude'), api_key, model_name,
optional base_url (OpenAI only), optional extra_params (JSON string).
"""
from __future__ import annotations

from typing import Any

from app.llm.base import LLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.openai_provider import OpenAIProvider


def build_provider(config: dict[str, Any]) -> LLMProvider:
    provider = config.get("provider")
    api_key = config.get("api_key")
    model = config.get("model_name")
    if not api_key or not model:
        raise ValueError("api_key and model_name are required")
    if provider == "openai":
        return OpenAIProvider(api_key=api_key, model=model, base_url=config.get("base_url"))
    if provider == "claude":
        return ClaudeProvider(api_key=api_key, model=model)
    raise ValueError(f"Unknown provider: {provider!r}")
