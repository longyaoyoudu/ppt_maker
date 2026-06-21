"""Tests for the Anthropic Claude provider.

The official anthropic SDK manages its own httpx client, which makes
mocking at the HTTP layer (respx) unreliable. We mock the SDK's
messages.create method directly instead.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.llm.base import LLMError
from app.llm.claude_provider import ClaudeProvider


def _fake_response(text_blocks):
    """Build a fake messages.create response object."""
    resp = MagicMock()
    blocks = []
    for item in text_blocks:
        block = MagicMock()
        block.type = item["type"]
        if item["type"] == "text":
            block.text = item["text"]
        else:
            block.text = ""
        blocks.append(block)
    resp.content = blocks
    return resp


def test_chat_returns_text_block():
    fake = _fake_response([{"type": "text", "text": "Hi from Claude"}])
    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = fake
        provider = ClaudeProvider(api_key="test-key", model="claude-test")
        out = provider.chat(system="be helpful", user="hi")
    assert out == "Hi from Claude"


def test_chat_skips_non_text_blocks():
    fake = _fake_response([
        {"type": "tool_use", "text": ""},
        {"type": "text", "text": "answer"},
    ])
    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = fake
        provider = ClaudeProvider(api_key="test-key", model="claude-test")
        out = provider.chat(system="s", user="u")
    assert out == "answer"


def test_chat_wraps_sdk_error():
    import anthropic
    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.side_effect = anthropic.AuthenticationError(
            message="bad key", response=MagicMock(status_code=401), body=None
        )
        provider = ClaudeProvider(api_key="bad", model="claude-test")
        with pytest.raises(LLMError):
            provider.chat(system="s", user="u")
