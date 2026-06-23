"""Tests for pluggable image providers (MiniMax, OpenAI)."""
import base64
from pathlib import Path

import httpx
import pytest

from app.services.image_providers import (
    ImageProvider,
    MiniMaxImageProvider,
    OpenAIImageProvider,
    build_image_provider,
)


# --- MiniMax ---------------------------------------------------------------

def test_minimax_provider_uses_default_base_url():
    p = MiniMaxImageProvider(api_key="k")
    assert p._base_url == "https://api.minimaxi.com"


def test_minimax_provider_sends_bearer_and_json(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        def json(self):
            return {
                "data": {"image_base64": [base64.b64encode(b"PNG1").decode()]},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }

    def fake_post(self, url, *, headers, json):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    p = MiniMaxImageProvider(api_key="secret-key", model="image-01")
    out = p.generate_image("a cat", n=1)
    assert out == [b"PNG1"]
    assert captured["url"] == "https://api.minimaxi.com/v1/image_generation"
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["headers"]["Content-Type"] == "application/json"
    body = captured["json"]
    assert body["model"] == "image-01"
    assert body["prompt"] == "a cat"
    assert body["n"] == 1
    assert body["response_format"] == "base64"


def test_minimax_provider_passes_aspect_ratio(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"data": {"image_base64": []}, "base_resp": {"status_code": 0}}

    def fake_post(self, url, *, headers, json):
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    MiniMaxImageProvider(api_key="k").generate_image("x", aspect_ratio="16:9")
    assert captured["json"]["aspect_ratio"] == "16:9"


def test_minimax_provider_returns_multiple_images(monkeypatch):
    class FakeResponse:
        status_code = 200
        def json(self):
            return {
                "data": {
                    "image_base64": [
                        base64.b64encode(b"A").decode(),
                        base64.b64encode(b"B").decode(),
                    ]
                },
                "base_resp": {"status_code": 0},
            }

    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: FakeResponse())
    out = MiniMaxImageProvider(api_key="k").generate_image("x", n=2)
    assert out == [b"A", b"B"]


def test_minimax_provider_raises_on_api_error(monkeypatch):
    class FakeResponse:
        status_code = 200
        def json(self):
            return {
                "data": {"image_base64": []},
                "base_resp": {"status_code": 1008, "status_msg": "insufficient balance"},
            }

    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: FakeResponse())
    with pytest.raises(RuntimeError, match="insufficient balance"):
        MiniMaxImageProvider(api_key="k").generate_image("x")


def test_minimax_provider_raises_on_http_error(monkeypatch):
    class FakeResponse:
        status_code = 401
        text = "auth failed"
        def json(self_inner):
            return {"base_resp": {"status_code": 1004}}

    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: FakeResponse())
    with pytest.raises(RuntimeError):
        MiniMaxImageProvider(api_key="bad").generate_image("x")


def test_minimax_provider_custom_base_url():
    p = MiniMaxImageProvider(api_key="k", base_url="https://proxy.example.com/")
    assert p._base_url == "https://proxy.example.com"  # trailing slash stripped


def test_minimax_provider_rejects_base_url_without_protocol():
    """User-entered hostnames without http(s):// must fail fast at construction."""
    with pytest.raises(ValueError, match="http"):
        MiniMaxImageProvider(api_key="k", base_url="api.minimaxi.com")
    with pytest.raises(ValueError, match="http"):
        MiniMaxImageProvider(api_key="k", base_url="://broken")
    with pytest.raises(ValueError, match="http"):
        MiniMaxImageProvider(api_key="k", base_url="  api.minimaxi.com  ")  # whitespace only stripped


def test_minimax_provider_strips_whitespace_around_url():
    p = MiniMaxImageProvider(api_key="k", base_url="  https://api.minimaxi.com/  ")
    assert p._base_url == "https://api.minimaxi.com"


def test_minimax_provider_falls_back_to_default_for_empty():
    p = MiniMaxImageProvider(api_key="k", base_url="")
    assert p._base_url == "https://api.minimaxi.com"


# --- OpenAI ---------------------------------------------------------------

def test_openai_provider_uses_injected_client(monkeypatch):
    captured = {}

    class _Item:
        b64_json = base64.b64encode(b"OPENAI-PNG").decode()

    class _Resp:
        data = [_Item()]

    class FakeImagesAPI:
        def generate(self, *, model, prompt, n, size, response_format, timeout):
            captured["model"] = model
            captured["prompt"] = prompt
            captured["n"] = n
            captured["size"] = size
            captured["response_format"] = response_format
            captured["timeout"] = timeout
            return _Resp()

    class FakeClient:
        images = FakeImagesAPI()

    p = OpenAIImageProvider(api_key="k", model="dall-e-3", client=FakeClient())
    out = p.generate_image("a dog")
    assert out == [b"OPENAI-PNG"]
    assert captured["model"] == "dall-e-3"
    assert captured["prompt"] == "a dog"
    assert captured["response_format"] == "b64_json"


def test_openai_provider_constructs_real_client_when_none_injected():
    """Without an injected client, OpenAIImageProvider must build an OpenAI client."""
    from openai import OpenAI

    p = OpenAIImageProvider(api_key="real-key-for-construction", model="dall-e-3")
    assert isinstance(p._client, OpenAI)


def test_openai_provider_requires_api_key_or_client():
    with pytest.raises(ValueError, match="api_key"):
        OpenAIImageProvider(api_key="")


def test_openai_provider_maps_aspect_ratio_to_size():
    """dall-e-3 supports limited sizes; verify the mapping is sensible."""
    p = OpenAIImageProvider(api_key="k")
    assert p._aspect_to_size("1:1") == "1024x1024"
    assert p._aspect_to_size("16:9") == "1792x1024"
    assert p._aspect_to_size("9:16") == "1024x1792"
    assert p._aspect_to_size(None) == "1024x1024"


def test_openai_provider_rejects_base_url_without_protocol():
    with pytest.raises(ValueError, match="http"):
        OpenAIImageProvider(api_key="k", base_url="api.openai.com")


# --- factory --------------------------------------------------------------

def test_build_image_provider_minimax():
    cfg = {"provider": "minimax", "api_key": "k", "model_name": "image-01", "base_url": None}
    p = build_image_provider(cfg)
    assert isinstance(p, MiniMaxImageProvider)


def test_build_image_provider_openai():
    cfg = {"provider": "openai", "api_key": "k", "model_name": "dall-e-3", "base_url": None}
    p = build_image_provider(cfg)
    assert isinstance(p, OpenAIImageProvider)


def test_build_image_provider_unknown_raises():
    with pytest.raises(ValueError, match="Unknown image provider"):
        build_image_provider({"provider": "sd", "api_key": "k", "model_name": "m"})


def test_build_image_provider_missing_api_key():
    with pytest.raises(ValueError, match="api_key"):
        build_image_provider({"provider": "minimax", "api_key": "", "model_name": "image-01"})


def test_build_image_provider_implements_protocol():
    p = build_image_provider({"provider": "minimax", "api_key": "k", "model_name": "image-01"})
    assert isinstance(p, ImageProvider)