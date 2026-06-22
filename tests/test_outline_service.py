"""Tests for the outline generation service. LLM is mocked."""
import json
import pytest

from app.llm.base import LLMProvider, LLMError
from app.services.outline_service import OutlineService, OutlineParseError


class FakeProvider(LLMProvider):
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def chat(self, system, user, *, temperature=0.7, max_tokens=2048) -> str:
        self.calls += 1
        if not self._responses:
            raise LLMError("no more responses")
        return self._responses.pop(0)


def test_parses_valid_json():
    payload = {
        "pages": [
            {"title": "Cover", "key_points": [], "layout": "title"},
            {"title": "Agenda", "key_points": ["a", "b"], "layout": "title-content"},
        ]
    }
    provider = FakeProvider([json.dumps(payload)])
    service = OutlineService(provider)
    outline = service.generate(topic="T", requirements=None, style_hint=None)
    assert outline.topic == "T"
    assert len(outline.pages) == 2
    assert outline.pages[0].layout == "title"
    assert provider.calls == 1


def test_strips_markdown_fences():
    payload = {"pages": [{"title": "P", "key_points": [], "layout": "title-content"}]}
    wrapped = "```json\n" + json.dumps(payload) + "\n```"
    provider = FakeProvider([wrapped])
    service = OutlineService(provider)
    outline = service.generate(topic="T", requirements=None, style_hint=None)
    assert len(outline.pages) == 1


def test_retries_then_succeeds():
    bad = "this is not json"
    good = json.dumps({"pages": [{"title": "P", "key_points": [], "layout": "title-content"}]})
    provider = FakeProvider([bad, good])
    service = OutlineService(provider)
    outline = service.generate(topic="T", requirements=None, style_hint=None)
    assert len(outline.pages) == 1
    assert provider.calls == 2


def test_raises_after_two_failed_parses():
    provider = FakeProvider(["nope", "still nope"])
    service = OutlineService(provider)
    with pytest.raises(OutlineParseError):
        service.generate(topic="T", requirements=None, style_hint=None)
    assert provider.calls == 2


def test_llm_error_propagates_immediately():
    class BoomProvider(LLMProvider):
        def chat(self, system, user, *, temperature=0.7, max_tokens=2048) -> str:
            raise LLMError("network down")
    service = OutlineService(BoomProvider())
    with pytest.raises(LLMError):
        service.generate(topic="T", requirements=None, style_hint=None)
