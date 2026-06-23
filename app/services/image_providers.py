"""Pluggable image generation providers (MiniMax, OpenAI).

Both implement the `ImageProvider` protocol: `generate_image(prompt, *, n, aspect_ratio) -> list[bytes]`.
Bytes are returned (rather than URLs) so callers can write them to disk and
PPT files don't depend on short-lived hosted URLs.
"""
from __future__ import annotations

import base64
from typing import Protocol, runtime_checkable

import httpx


DEFAULT_MINIMAX_BASE_URL = "https://api.minimaxi.com"


def _normalize_base_url(base_url: str | None, default: str | None) -> str | None:
    """Validate and normalize an API base URL.

    Returns the URL with trailing slash stripped and whitespace removed.
    Raises ValueError if a non-empty URL does not start with http:// or https://,
    so callers fail fast (instead of httpx crashing at request time with an
    obscure UnsupportedProtocol error).
    """
    raw = (base_url or default or "").strip()
    if not raw:
        return default  # type: ignore[return-value]
    cleaned = raw.rstrip("/")
    if not cleaned.lower().startswith(("http://", "https://")):
        raise ValueError(
            f"base_url must start with http:// or https:// (got: {base_url!r})"
        )
    return cleaned


@runtime_checkable
class ImageProvider(Protocol):
    def generate_image(
        self, prompt: str, *, n: int = 1, aspect_ratio: str | None = None
    ) -> list[bytes]: ...


# ---------------------------------------------------------------------------
# MiniMax
# ---------------------------------------------------------------------------

class MiniMaxImageProvider:
    """MiniMax image generation API.

    Spec: https://platform.minimaxi.com/docs/api-reference/image-generation
    Always uses response_format=base64 so we get inline image bytes (URLs
    expire after 24h). aspect_ratio is passed through when provided.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "image-01",
        base_url: str = DEFAULT_MINIMAX_BASE_URL,
        timeout: float = 120.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self._api_key = api_key
        self._model = model
        self._base_url = _normalize_base_url(base_url, DEFAULT_MINIMAX_BASE_URL)
        self._timeout = timeout

    def generate_image(
        self, prompt: str, *, n: int = 1, aspect_ratio: str | None = None
    ) -> list[bytes]:
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "n": n,
            "response_format": "base64",
        }
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self._base_url}/v1/image_generation",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if resp.status_code >= 400:
            raise RuntimeError(
                f"MiniMax image API HTTP {resp.status_code}: {resp.text[:200]}"
            )
        data = resp.json()
        base_resp = data.get("base_resp", {}) or {}
        if base_resp.get("status_code", 0) != 0:
            msg = base_resp.get("status_msg", "unknown error")
            raise RuntimeError(f"MiniMax image API error: {msg}")

        body = data.get("data", {}) or {}
        b64_list = body.get("image_base64") or []
        return [base64.b64decode(b) for b in b64_list]


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIImageProvider:
    """OpenAI Images API (works for any compatible endpoint via base_url).

    dall-e-3 only supports a fixed set of sizes, so we map aspect_ratio
    onto them. Unknown aspects fall back to 1024x1024.
    """

    _ASPECT_TO_SIZE = {
        "1:1": "1024x1024",
        "16:9": "1792x1024",
        "9:16": "1024x1792",
        "4:3": "1024x1024",
        "3:4": "1024x1024",
    }

    def __init__(
        self,
        api_key: str,
        model: str = "dall-e-3",
        base_url: str | None = None,
        timeout: float = 120.0,
        client: object | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("api_key is required")
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI

            normalized = _normalize_base_url(base_url, None)
            self._client = OpenAI(api_key=api_key, base_url=normalized)
        self._model = model
        self._timeout = timeout

    def _aspect_to_size(self, aspect_ratio: str | None) -> str:
        return self._ASPECT_TO_SIZE.get(aspect_ratio or "1:1", "1024x1024")

    def generate_image(
        self, prompt: str, *, n: int = 1, aspect_ratio: str | None = None
    ) -> list[bytes]:
        resp = self._client.images.generate(
            model=self._model,
            prompt=prompt,
            n=n,
            size=self._aspect_to_size(aspect_ratio),
            response_format="b64_json",
            timeout=self._timeout,
        )
        return [base64.b64decode(d.b64_json) for d in resp.data]


# ---------------------------------------------------------------------------
# factory
# ---------------------------------------------------------------------------

def build_image_provider(config: dict) -> ImageProvider:
    """Construct an image provider from a config dict (matches ModelConfig shape).

    Required keys: provider ('minimax'|'openai'), api_key, model_name.
    Optional: base_url.
    """
    provider = config.get("provider")
    api_key = config.get("api_key")
    model = config.get("model_name")
    if not api_key or not model:
        raise ValueError("api_key and model_name are required")
    if provider == "minimax":
        return MiniMaxImageProvider(
            api_key=api_key, model=model, base_url=config.get("base_url") or DEFAULT_MINIMAX_BASE_URL,
        )
    if provider == "openai":
        return OpenAIImageProvider(
            api_key=api_key, model=model, base_url=config.get("base_url"),
        )
    raise ValueError(f"Unknown image provider: {provider!r}")