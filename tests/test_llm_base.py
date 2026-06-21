"""Tests for the LLM provider abstract base."""
import pytest

from app.llm.base import LLMProvider, Message, LLMError


def test_cannot_instantiate_abstract_base():
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


def test_message_dataclass():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_llm_error_is_exception():
    assert issubclass(LLMError, Exception)
