"""Outline generation: build prompt, call LLM, parse JSON with one retry."""
from __future__ import annotations

import json
import re

from app.llm.base import LLMError, LLMProvider
from app.models import Outline
from app.prompts import OUTLINE_SYSTEM, build_outline_user


class OutlineParseError(LLMError):
    """Raised when the LLM does not return parseable JSON after the retry."""


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


class OutlineService:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate(
        self,
        topic: str,
        requirements: str | None,
        style_hint: str | None,
        document_text: str | None = None,
    ) -> Outline:
        user_msg = build_outline_user(
            topic=topic,
            requirements=requirements,
            style_hint=style_hint,
            document_excerpt=document_text,
        )
        last_err: Exception | None = None
        for attempt in range(2):
            prompt = user_msg if attempt == 0 else (
                user_msg
                + "\n\nREMINDER: Your previous reply was not valid JSON. Return ONLY the JSON object, no markdown, no commentary."
            )
            raw = self._provider.chat(system=OUTLINE_SYSTEM, user=prompt)
            try:
                data = json.loads(_strip_fences(raw))
            except json.JSONDecodeError as e:
                last_err = e
                continue
            if not isinstance(data, dict) or "pages" not in data or not isinstance(data["pages"], list):
                last_err = ValueError("missing 'pages' list")
                continue
            pages = []
            for p in data["pages"]:
                pages.append({
                    "title": str(p.get("title", "")),
                    "key_points": [str(x) for x in p.get("key_points", [])],
                    "layout": p.get("layout", "title-content"),
                })
            return Outline(topic=topic, requirements=requirements, pages=pages)  # type: ignore[arg-type]
        raise OutlineParseError(f"Could not parse outline JSON after retry: {last_err}")
