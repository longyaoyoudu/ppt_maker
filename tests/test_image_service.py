"""Tests for the image service (placeholder and AI modes)."""
from pathlib import Path

from PIL import Image

from app.services.image_service import ImageService


def test_placeholder_image_writes_file(tmp_dir):
    service = ImageService()
    out = tmp_dir / "ph.png"
    service.placeholder(out_path=out, color=(200, 200, 200), text="IMG")
    assert out.exists()
    img = Image.open(out)
    assert img.size == (800, 450)


def test_ai_image_calls_provider(tmp_dir):
    captured = {}

    class FakeProvider:
        def generate_image(self, prompt, *, n=1, aspect_ratio=None):  # noqa: ARG002
            captured["prompt"] = prompt
            captured["aspect_ratio"] = aspect_ratio
            return [b"fake-bytes"]

    service = ImageService(image_provider=FakeProvider())
    out = tmp_dir / "ai.png"
    service.ai_generate(out_path=out, prompt="a cat")
    assert captured["prompt"] == "a cat"
    assert out.read_bytes() == b"fake-bytes"


def test_ai_image_raises_without_provider(tmp_dir):
    service = ImageService()
    import pytest
    with pytest.raises(RuntimeError):
        service.ai_generate(out_path=tmp_dir / "x.png", prompt="x")
