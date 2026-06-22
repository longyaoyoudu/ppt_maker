"""Tests for Pydantic models."""
import json

from app.models import ModelConfig, OutlinePage, Outline, PPTRequest


def test_model_config_serialization():
    c = ModelConfig(stage="outline", provider="openai", api_key="k", model_name="gpt-4o", base_url=None)
    assert c.stage == "outline"
    assert c.provider == "openai"
    d = c.model_dump()
    assert d["stage"] == "outline"
    c2 = ModelConfig(**d)
    assert c2 == c


def test_outline_page_validation():
    p = OutlinePage(title="Hello", key_points=["a", "b"], layout="title-content")
    assert p.title == "Hello"
    assert p.layout == "title-content"


def test_outline_pages_list():
    pages = [OutlinePage(title=f"P{i}", key_points=[], layout="title-content") for i in range(3)]
    o = Outline(topic="T", pages=pages)
    assert len(o.pages) == 3
    j = json.dumps(o.model_dump())
    o2 = Outline.model_validate_json(j)
    assert o2 == o


def test_ppt_request_defaults():
    r = PPTRequest(outline_id=1, style="business", image_mode="placeholder")
    assert r.style == "business"
    assert r.image_mode == "placeholder"
