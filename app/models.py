"""Pydantic models used across the app: API requests/responses and storage rows."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Provider = Literal["openai", "claude"]
Layout = Literal["title", "title-content", "two-column", "quote", "section"]
Style = Literal["business", "academic", "minimal", "creative"]
ImageMode = Literal["placeholder", "ai", "none"]


class ModelConfig(BaseModel):
    stage: Literal["outline", "ppt"]
    provider: Provider
    api_key: str
    model_name: str
    base_url: str | None = None
    extra_params: dict | None = None


class OutlinePage(BaseModel):
    title: str
    key_points: list[str] = Field(default_factory=list)
    layout: Layout = "title-content"


class Outline(BaseModel):
    topic: str
    requirements: str | None = None
    pages: list[OutlinePage]


class OutlineGenerateRequest(BaseModel):
    topic: str
    requirements: str | None = None
    style_hint: str | None = None


class OutlineGenerateResponse(BaseModel):
    outline_id: int
    content: Outline


class PPTRequest(BaseModel):
    outline_id: int
    style: Style = "business"
    image_mode: ImageMode = "placeholder"
