"""Image generation: placeholder rectangles or AI-generated PNGs.

AI mode delegates to an injected ImageProvider (see app.services.image_providers).
The provider is injected rather than constructed here so callers (the API layer)
can pick the provider based on user-configured model settings.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont


class _ImageCapable(Protocol):
    def generate_image(self, prompt: str, *, n: int = 1, aspect_ratio: str | None = None) -> list[bytes]: ...


class ImageService:
    def __init__(self, image_provider: _ImageCapable | None = None) -> None:
        self._provider = image_provider

    def placeholder(
        self,
        *,
        out_path: Path,
        color: tuple[int, int, int] = (220, 220, 220),
        text: str = "图片占位",
    ) -> Path:
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

    def ai_generate(
        self,
        *,
        out_path: Path,
        prompt: str,
        aspect_ratio: str | None = None,
    ) -> Path:
        if self._provider is None:
            raise RuntimeError(
                "ImageService was constructed without an image_provider; "
                "configure an image model in 模型配置 → 图片生成模型 first."
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._provider.generate_image(prompt, n=1, aspect_ratio=aspect_ratio)
        if not data:
            raise RuntimeError("Image provider returned no images")
        out_path.write_bytes(data[0])
        return out_path