"""Image generation: placeholder rectangles or AI-generated PNGs.

AI mode uses the OpenAI Images API (works for any compatible endpoint).
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont


class _ImageCapable(Protocol):
    model: str

    def generate_image(self, prompt: str, *, size: str, n: int) -> list[bytes]: ...


class ImageService:
    def __init__(self, openai_provider: _ImageCapable | None = None) -> None:
        self._provider = openai_provider

    def placeholder(self, *, out_path: Path, color: tuple[int, int, int] = (220, 220, 220), text: str = "图片占位") -> Path:
        img = Image.new("RGB", (800, 450), color=color)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((800 - w) / 2, (450 - h) / 2), text, fill=(80, 80, 80), font=font)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, format="PNG")
        return out_path

    def ai_generate(self, *, out_path: Path, prompt: str, api_key: str, base_url: str | None, model: str = "dall-e-3") -> Path:
        if self._provider is None:
            raise RuntimeError(
                "ImageService was constructed without an openai_provider; "
                "inject one (e.g. _OpenAIImageProvider) before calling ai_generate."
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._provider.generate_image(prompt, size="1024x1024", n=1)
        out_path.write_bytes(data[0])
        return out_path


class _OpenAIImageProvider:
    def __init__(self, images_client) -> None:
        self._client = images_client
        self.model = "dall-e-3"

    def generate_image(self, prompt: str, *, size: str, n: int) -> list[bytes]:
        import base64
        resp = self._client.generate(model=self.model, prompt=prompt, size=size, n=n, response_format="b64_json")
        return [base64.b64decode(d.b64_json) for d in resp.data]
