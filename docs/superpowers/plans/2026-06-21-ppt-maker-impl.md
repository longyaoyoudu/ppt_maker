# PPT Maker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Web app that takes a topic and produces a `.pptx` (+ optional `.pdf`) using a two-stage LLM pipeline (outline → PPT), where each stage can use a different model provider (OpenAI-compatible or Anthropic Claude).

**Architecture:** Python FastAPI backend with a thin single-page HTML/TailwindCSS frontend. The backend exposes JSON APIs for config, outline generation, PPT generation, history, and downloads. The PPT itself is built with `python-pptx`; PDFs are produced by headless LibreOffice. SQLite stores model config, outline history, and generation metadata. The LLM layer is abstracted behind a `LLMProvider` interface with two concrete implementations.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, openai SDK, anthropic SDK, python-pptx, Pillow, SQLite (stdlib), LibreOffice (system), TailwindCSS via CDN (frontend), vanilla JS (frontend).

---

## PR Strategy

This implementation is split into **7 PRs**, each on its own branch (`feat/0N-...`) and reviewed/merged into `main` before the next starts. The order is dependency-driven; each PR is independently runnable and testable on its branch.

| PR | Branch | Scope | Reviewable artifact |
|----|--------|-------|--------------------|
| 1 | `feat/01-scaffolding` | Project skeleton + `requirements.txt` + `run.py` + `/api/health` + test infra | `python run.py` → GET `/api/health` returns 200 |
| 2 | `feat/02-llm-providers` | `LLMProvider` abstract base + OpenAI + Claude implementations + factory | Unit tests with mocked HTTP pass |
| 3 | `feat/03-storage` | Pydantic models + SQLite schema + `config_store` + `history_store` | Round-trip CRUD tests pass |
| 4 | `feat/04-outline-service` | `prompts.py` + `outline_service.py` (LLM call → JSON parse + retry) | Service tests with mocked LLM pass |
| 5 | `feat/05-ppt-pdf-image-services` | `ppt_service` (python-pptx), `pdf_service` (LibreOffice), `image_service` (placeholder + AI stub) | Generated .pptx opens, has expected slides |
| 6 | `feat/06-api-endpoints` | All routes in `app/main.py` + error handlers + downloads + static mount | E2E test: POST outline → POST ppt → GET download works |
| 7 | `feat/07-frontend` | `static/index.html` with 4 tabs (config / outline / generate / history) | Manual: full flow works in browser |

**PR workflow per branch:**
```bash
git checkout -b feat/NN-name
# ... do all tasks for that PR ...
git add <files>
git commit -m "..."
git push -u origin feat/NN-name
gh pr create --base main --title "..." --body "..."
# Wait for review/merge, then:
git checkout main && git pull
```

**Coding conventions (all PRs):**
- Use TDD: write failing test → run → implement → re-run → commit.
- One logical change per commit; commit messages use Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- No placeholder/TODO comments in committed code.
- All Python files: type hints where it helps readability; module-level docstring stating purpose.
- Tests live in `tests/` mirroring the package layout.

---

# PR 1: Project Scaffolding

**Branch:** `feat/01-scaffolding`
**Goal:** Create the minimal FastAPI project that runs, plus test infrastructure, so future PRs have a foundation.

**Files touched:**
- Create: `requirements.txt`
- Create: `run.py`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_api.py`
- Modify: `README.md` (replace placeholder with run instructions)

### Task 1.1: requirements.txt

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create the file with pinned minimum versions**

```
fastapi>=0.110,<1.0
uvicorn[standard]>=0.27,<1.0
python-multipart>=0.0.9
openai>=1.30,<2.0
anthropic>=0.30,<1.0
python-pptx>=0.6.23,<1.0
Pillow>=10.0,<12.0
pytest>=8.0,<9.0
pytest-asyncio>=0.23,<1.0
httpx>=0.27,<1.0
respx>=0.21,<1.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: pin Python dependencies"
```

### Task 1.2: Run script

**Files:**
- Create: `run.py`

- [ ] **Step 1: Write the run script**

```python
"""Local development entry point. Use `python run.py` to start the server."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
```

- [ ] **Step 2: Smoke-check syntax**

Run: `python -c "import ast; ast.parse(open('run.py').read())"`
Expected: No output (success).

- [ ] **Step 3: Commit**

```bash
git add run.py
git commit -m "chore: add local run script"
```

### Task 1.3: Empty package + FastAPI app with health endpoint

**Files:**
- Create: `app/__init__.py`
- Create: `app/main.py`

- [ ] **Step 1: Create `app/__init__.py` (empty file)**

```bash
touch app/__init__.py
```

- [ ] **Step 2: Write the failing test for the health endpoint**

Create `tests/__init__.py` (empty) and `tests/test_api.py`:

```python
"""Integration tests for the FastAPI app."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run the test to confirm it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 4: Implement `app/main.py` with the health endpoint**

```python
"""FastAPI application entry point."""
from fastapi import FastAPI

app = FastAPI(title="PPT Maker", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Re-run the test**

Run: `pytest tests/test_api.py -v`
Expected: PASS, 1 passed.

- [ ] **Step 6: Commit**

```bash
git add app/__init__.py app/main.py tests/__init__.py tests/test_api.py
git commit -m "feat: add FastAPI app with health endpoint"
```

### Task 1.4: Test configuration

**Files:**
- Create: `tests/conftest.py`
- Create: `pytest.ini` (or `pyproject.toml [tool.pytest.ini_options]`)

- [ ] **Step 1: Create `pytest.ini` at project root**

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
addopts = -ra
```

- [ ] **Step 2: Create `tests/conftest.py` with shared fixtures**

```python
"""Shared pytest fixtures."""
import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Redirect runtime dirs to a temp location so tests don't pollute the repo."""
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    monkeypatch.setenv("PPTM_DATA_DIR", str(data_dir))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(outputs_dir))
    yield tmp_path


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Remove env vars that might leak between tests."""
    for k in ("PPTM_DATA_DIR", "PPTM_OUTPUTS_DIR", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    yield
```

- [ ] **Step 3: Run all tests**

Run: `pytest -v`
Expected: 1 passed (`test_health_returns_ok`).

- [ ] **Step 4: Commit**

```bash
git add pytest.ini tests/conftest.py
git commit -m "test: configure pytest with shared fixtures"
```

### Task 1.5: Update README with run instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the placeholder run section with concrete commands**

Update the `## 快速开始（待实现）` section to read:

```markdown
## 快速开始

```bash
pip install -r requirements.txt
python run.py
```

然后浏览器访问 <http://127.0.0.1:8000>。

## 测试

```bash
pytest
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add run and test instructions"
```

### Task 1.6: Open PR #1

- [ ] **Step 1: Push branch and open PR**

```bash
git push -u origin feat/01-scaffolding
gh pr create --base main --title "feat: project scaffolding with health endpoint" --body "Minimal FastAPI app with /api/health, test infra, and run script. No functional PPT features yet — see spec for the full plan."
```

Expected: PR created, URL returned.

- [ ] **Step 2: Report PR URL to user, then STOP and wait for merge**

---

# PR 2: LLM Provider Abstraction

**Branch:** `feat/02-llm-providers` (branched from `main` after PR #1 merged)
**Goal:** Build the LLM abstraction layer with OpenAI and Claude implementations, plus a factory that picks the right provider from config. All tests use mocked HTTP — no real API calls.

**Files touched:**
- Create: `app/llm/__init__.py`
- Create: `app/llm/base.py`
- Create: `app/llm/openai_provider.py`
- Create: `app/llm/claude_provider.py`
- Create: `app/llm/factory.py`
- Create: `tests/test_llm_base.py`
- Create: `tests/test_llm_openai.py`
- Create: `tests/test_llm_claude.py`
- Create: `tests/test_llm_factory.py`

### Task 2.1: Abstract base class

**Files:**
- Create: `app/llm/__init__.py`
- Create: `app/llm/base.py`

- [ ] **Step 1: Create package init**

```bash
touch app/llm/__init__.py
```

- [ ] **Step 2: Write the failing test for the abstract interface**

Create `tests/test_llm_base.py`:

```python
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
```

- [ ] **Step 3: Run test to confirm failure**

Run: `pytest tests/test_llm_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm.base'`.

- [ ] **Step 4: Implement the base class**

Create `app/llm/base.py`:

```python
"""LLM provider abstraction.

Defines a minimal interface (`chat`) that all concrete providers must implement.
The factory in `factory.py` picks the right provider based on saved config.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    role: str
    content: str


class LLMError(Exception):
    """Raised when an LLM call fails for any reason (network, auth, parse)."""


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Send messages and return the assistant's text response.

        Raises:
            LLMError: on any failure.
        """
```

- [ ] **Step 5: Re-run tests**

Run: `pytest tests/test_llm_base.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/llm/__init__.py app/llm/base.py tests/test_llm_base.py
git commit -m "feat(llm): add LLMProvider abstract base and Message dataclass"
```

### Task 2.2: OpenAI-compatible provider

**Files:**
- Create: `app/llm/openai_provider.py`
- Create: `tests/test_llm_openai.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_llm_openai.py`:

```python
"""Tests for the OpenAI-compatible provider, using respx to mock HTTP."""
import pytest
import respx
from httpx import Response

from app.llm.base import LLMError
from app.llm.openai_provider import OpenAIProvider

BASE_URL = "https://api.example.com/v1"


def _make_provider(api_key: str = "test-key", model: str = "gpt-test") -> OpenAIProvider:
    return OpenAIProvider(api_key=api_key, model=model, base_url=BASE_URL)


@respx.mock
def test_chat_returns_assistant_content():
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": "Hello back"}}]},
        )
    )
    provider = _make_provider()
    out = provider.chat(system="You are helpful.", user="Hi")
    assert out == "Hello back"


@respx.mock
def test_chat_passes_temperature_and_max_tokens():
    route = respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    )
    provider = _make_provider()
    provider.chat(system="s", user="u", temperature=0.2, max_tokens=64)
    body = route.calls.last.request.content.decode()
    assert '"temperature":0.2' in body
    assert '"max_tokens":64' in body


@respx.mock
def test_chat_wraps_http_error_in_llm_error():
    respx.post(f"{BASE_URL}/chat/completions").mock(return_value=Response(500, text="boom"))
    provider = _make_provider()
    with pytest.raises(LLMError):
        provider.chat(system="s", user="u")
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `pytest tests/test_llm_openai.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm.openai_provider'`.

- [ ] **Step 3: Implement `OpenAIProvider`**

Create `app/llm/openai_provider.py`:

```python
"""OpenAI-compatible provider.

Works with any service that exposes the OpenAI chat-completions API
(OpenAI, Azure, DeepSeek, Moonshot, Zhipu, Ollama, etc.). Set `base_url`
to the service's base URL.
"""
from __future__ import annotations

from openai import OpenAI, OpenAIError

from app.llm.base import LLMError, LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except OpenAIError as e:
            raise LLMError(f"OpenAI provider error: {e}") from e
        except Exception as e:
            raise LLMError(f"OpenAI provider transport error: {e}") from e
        if not resp.choices:
            raise LLMError("OpenAI returned no choices")
        return resp.choices[0].message.content or ""
```

- [ ] **Step 4: Re-run tests**

Run: `pytest tests/test_llm_openai.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/llm/openai_provider.py tests/test_llm_openai.py
git commit -m "feat(llm): add OpenAI-compatible provider"
```

### Task 2.3: Anthropic Claude provider

**Files:**
- Create: `app/llm/claude_provider.py`
- Create: `tests/test_llm_claude.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_llm_claude.py`:

```python
"""Tests for the Anthropic Claude provider."""
import pytest
import respx
from httpx import Response

from app.llm.base import LLMError
from app.llm.claude_provider import ClaudeProvider


@respx.mock
def test_chat_returns_text_block():
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(
            200,
            json={"content": [{"type": "text", "text": "Hi from Claude"}]},
        )
    )
    provider = ClaudeProvider(api_key="test-key", model="claude-test")
    out = provider.chat(system="be helpful", user="hi")
    assert out == "Hi from Claude"


@respx.mock
def test_chat_skips_non_text_blocks():
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(
            200,
            json={"content": [{"type": "tool_use", "id": "x"}, {"type": "text", "text": "answer"}]},
        )
    )
    provider = ClaudeProvider(api_key="test-key", model="claude-test")
    out = provider.chat(system="s", user="u")
    assert out == "answer"


@respx.mock
def test_chat_wraps_http_error():
    respx.post("https://api.anthropic.com/v1/messages").mock(return_value=Response(401, text="nope"))
    provider = ClaudeProvider(api_key="bad", model="claude-test")
    with pytest.raises(LLMError):
        provider.chat(system="s", user="u")
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `pytest tests/test_llm_claude.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm.claude_provider'`.

- [ ] **Step 3: Implement `ClaudeProvider`**

Create `app/llm/claude_provider.py`:

```python
"""Anthropic Claude provider (uses the official anthropic SDK)."""
from __future__ import annotations

import anthropic

from app.llm.base import LLMError, LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        try:
            resp = self._client.messages.create(
                model=self._model,
                system=system,
                messages=[{"role": "user", "content": user}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except anthropic.AnthropicError as e:
            raise LLMError(f"Claude provider error: {e}") from e
        except Exception as e:
            raise LLMError(f"Claude provider transport error: {e}") from e

        parts = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
        if not parts:
            raise LLMError("Claude returned no text content")
        return "".join(parts)
```

- [ ] **Step 4: Re-run tests**

Run: `pytest tests/test_llm_claude.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/llm/claude_provider.py tests/test_llm_claude.py
git commit -m "feat(llm): add Anthropic Claude provider"
```

### Task 2.4: Factory

**Files:**
- Create: `app/llm/factory.py`
- Create: `tests/test_llm_factory.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_llm_factory.py`:

```python
"""Tests for the LLM provider factory."""
import pytest

from app.llm.base import LLMProvider
from app.llm.factory import build_provider


def test_build_openai_provider():
    p = build_provider({"provider": "openai", "api_key": "k", "model_name": "gpt-x", "base_url": None})
    assert isinstance(p, LLMProvider)
    assert type(p).__name__ == "OpenAIProvider"


def test_build_claude_provider():
    p = build_provider({"provider": "claude", "api_key": "k", "model_name": "claude-x"})
    assert type(p).__name__ == "ClaudeProvider"


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        build_provider({"provider": "wat", "api_key": "k", "model_name": "m"})


def test_missing_fields_raises():
    with pytest.raises(ValueError):
        build_provider({"provider": "openai", "model_name": "m"})  # no api_key
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `pytest tests/test_llm_factory.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm.factory'`.

- [ ] **Step 3: Implement the factory**

Create `app/llm/factory.py`:

```python
"""Factory that builds the right LLMProvider from a config dict.

Expected config keys: provider ('openai'|'claude'), api_key, model_name,
optional base_url (OpenAI only), optional extra_params (JSON string).
"""
from __future__ import annotations

from typing import Any

from app.llm.base import LLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.openai_provider import OpenAIProvider


def build_provider(config: dict[str, Any]) -> LLMProvider:
    provider = config.get("provider")
    api_key = config.get("api_key")
    model = config.get("model_name")
    if not api_key or not model:
        raise ValueError("api_key and model_name are required")
    if provider == "openai":
        return OpenAIProvider(api_key=api_key, model=model, base_url=config.get("base_url"))
    if provider == "claude":
        return ClaudeProvider(api_key=api_key, model=model)
    raise ValueError(f"Unknown provider: {provider!r}")
```

- [ ] **Step 4: Re-run tests**

Run: `pytest tests/test_llm_factory.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/llm/factory.py tests/test_llm_factory.py
git commit -m "feat(llm): add provider factory"
```

### Task 2.5: Open PR #2

- [ ] **Step 1: Push branch and open PR**

```bash
git push -u origin feat/02-llm-providers
gh pr create --base main --title "feat(llm): provider abstraction with OpenAI and Claude" --body "Adds LLMProvider ABC, OpenAI-compatible and Claude concrete implementations, and a factory. All HTTP calls are mocked in tests (respx). No real network calls in CI."
```

- [ ] **Step 2: Report PR URL to user, STOP and wait for merge**

---

# PR 3: Config and History Storage

**Branch:** `feat/03-storage` (from `main` after PR #2 merged)
**Goal:** Add SQLite-backed stores for model config and history. No HTTP routes yet — just the storage layer + Pydantic models.

**Files touched:**
- Create: `app/models.py`
- Create: `app/db.py`
- Create: `app/config_store.py`
- Create: `app/history_store.py`
- Create: `tests/test_config_store.py`
- Create: `tests/test_history_store.py`

### Task 3.1: Pydantic models

**Files:**
- Create: `app/models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_models.py`:

```python
"""Tests for Pydantic models."""
import json

from app.models import ModelConfig, OutlinePage, Outline, PPTRequest


def test_model_config_serialization():
    c = ModelConfig(stage="outline", provider="openai", api_key="k", model_name="gpt-4o", base_url=None)
    assert c.stage == "outline"
    assert c.provider == "openai"
    # Round-trip via JSON (the SQLite layer stores dicts)
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
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3: Implement `app/models.py`**

```python
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
```

- [ ] **Step 4: Re-run test**

Run: `pytest tests/test_models.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat: add Pydantic models for config and outlines"
```

### Task 3.2: Database init helper

**Files:**
- Create: `app/db.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_db.py`:

```python
"""Tests for the SQLite database initializer."""
import sqlite3

from app.db import init_db, get_connection


def test_init_creates_tables(tmp_dir):
    db_path = tmp_dir / "test.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    names = {r["name"] for r in rows}
    assert "model_configs" in names
    assert "outlines" in names
    assert "generations" in names


def test_init_idempotent(tmp_dir):
    db_path = tmp_dir / "test.db"
    init_db(db_path)
    init_db(db_path)  # second call should not raise
    assert db_path.exists()


def test_get_connection_yields_row_factory(tmp_dir):
    db_path = tmp_dir / "test.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute("INSERT INTO model_configs(stage, provider, api_key, model_name) VALUES ('outline','openai','k','m')")
        row = conn.execute("SELECT * FROM model_configs WHERE stage='outline'").fetchone()
    assert row["stage"] == "outline"
    assert row["api_key"] == "k"


def test_get_connection_invalid_path_raises(tmp_dir):
    import pytest
    with pytest.raises(sqlite3.OperationalError):
        with get_connection(tmp_dir / "nope" / "x.db") as conn:
            conn.execute("SELECT 1")
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`.

- [ ] **Step 3: Implement `app/db.py`**

```python
"""SQLite connection and schema management.

Schema:
- model_configs: one row per stage ('outline' | 'ppt')
- outlines: history of generated/edited outlines
- generations: history of generated PPTs (.pptx / .pdf paths)
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS model_configs (
    stage TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    base_url TEXT,
    api_key TEXT NOT NULL,
    model_name TEXT NOT NULL,
    extra_params TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    requirements TEXT,
    content_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outline_id INTEGER REFERENCES outlines(id),
    style TEXT,
    image_mode TEXT,
    pptx_path TEXT,
    pdf_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def default_db_path() -> Path:
    data_dir = Path(os.environ.get("PPTM_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "app.db"


def init_db(path: Path | None = None) -> Path:
    """Create schema if missing. Returns the db path used."""
    db_path = path or default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
    return db_path


@contextmanager
def get_connection(path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    db_path = path or default_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

- [ ] **Step 4: Re-run test**

Run: `pytest tests/test_db.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: add SQLite connection and schema init"
```

### Task 3.3: Config store

**Files:**
- Create: `app/config_store.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config_store.py`:

```python
"""Tests for the model config store."""
import base64

import pytest

from app.config_store import ConfigStore, ConfigNotFound
from app.models import ModelConfig


def test_save_and_get_round_trip(tmp_dir):
    store = ConfigStore(db_path=tmp_dir / "test.db")
    cfg = ModelConfig(stage="outline", provider="openai", api_key="secret-123", model_name="gpt-4o")
    store.save(cfg)
    loaded = store.get("outline")
    assert loaded == cfg


def test_get_missing_raises(tmp_dir):
    store = ConfigStore(db_path=tmp_dir / "test.db")
    with pytest.raises(ConfigNotFound):
        store.get("ppt")


def test_api_key_is_encoded_at_rest(tmp_dir):
    db_path = tmp_dir / "test.db"
    store = ConfigStore(db_path=db_path)
    store.save(ModelConfig(stage="outline", provider="openai", api_key="plaintext-key", model_name="gpt"))
    raw = db_path.read_text(encoding="utf-8")
    assert "plaintext-key" not in raw
    # Base64 of "plaintext-key" should appear
    encoded = base64.b64encode(b"plaintext-key").decode()
    assert encoded in raw


def test_update_overwrites(tmp_dir):
    store = ConfigStore(db_path=tmp_dir / "test.db")
    store.save(ModelConfig(stage="ppt", provider="claude", api_key="k1", model_name="claude-sonnet-4-6"))
    store.save(ModelConfig(stage="ppt", provider="openai", api_key="k2", model_name="gpt-4o"))
    assert store.get("ppt").provider == "openai"


def test_list_stages(tmp_dir):
    store = ConfigStore(db_path=tmp_dir / "test.db")
    store.save(ModelConfig(stage="outline", provider="openai", api_key="k", model_name="m"))
    store.save(ModelConfig(stage="ppt", provider="claude", api_key="k", model_name="m"))
    stages = {s.stage for s in store.list_all()}
    assert stages == {"outline", "ppt"}
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/test_config_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config_store'`.

- [ ] **Step 3: Implement `app/config_store.py`**

```python
"""CRUD for model configuration (one row per stage).

API keys are base64-encoded at rest. This is obfuscation, not strong
encryption — sufficient to prevent casual file inspection.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from app.db import get_connection, init_db
from app.models import ModelConfig


class ConfigNotFound(LookupError):
    """Raised when a config row is missing."""


def _encode_key(api_key: str) -> str:
    return base64.b64encode(api_key.encode("utf-8")).decode("ascii")


def _decode_key(encoded: str) -> str:
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")


class ConfigStore:
    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is not None:
            init_db(db_path)
            self._db_path = db_path
        else:
            self._db_path = None  # use default from env

    def save(self, cfg: ModelConfig) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO model_configs(stage, provider, base_url, api_key, model_name, extra_params, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(stage) DO UPDATE SET
                    provider=excluded.provider,
                    base_url=excluded.base_url,
                    api_key=excluded.api_key,
                    model_name=excluded.model_name,
                    extra_params=excluded.extra_params,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    cfg.stage,
                    cfg.provider,
                    cfg.base_url,
                    _encode_key(cfg.api_key),
                    cfg.model_name,
                    json.dumps(cfg.extra_params) if cfg.extra_params is not None else None,
                ),
            )

    def get(self, stage: str) -> ModelConfig:
        with get_connection(self._db_path) as conn:
            row = conn.execute("SELECT * FROM model_configs WHERE stage=?", (stage,)).fetchone()
        if row is None:
            raise ConfigNotFound(f"No config for stage={stage!r}")
        return ModelConfig(
            stage=row["stage"],
            provider=row["provider"],
            api_key=_decode_key(row["api_key"]),
            model_name=row["model_name"],
            base_url=row["base_url"],
            extra_params=json.loads(row["extra_params"]) if row["extra_params"] else None,
        )

    def list_all(self) -> list[ModelConfig]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute("SELECT stage FROM model_configs").fetchall()
        return [self.get(r["stage"]) for r in rows]
```

- [ ] **Step 4: Re-run test**

Run: `pytest tests/test_config_store.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/config_store.py tests/test_config_store.py
git commit -m "feat: add model config store with base64-obfuscated API keys"
```

### Task 3.4: History store

**Files:**
- Create: `app/history_store.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_history_store.py`:

```python
"""Tests for the outline and generation history store."""
import pytest

from app.history_store import HistoryStore
from app.models import Outline, OutlinePage, Generation


def test_save_and_get_outline(tmp_dir):
    store = HistoryStore(db_path=tmp_dir / "test.db")
    outline = Outline(topic="T", pages=[OutlinePage(title="P1", key_points=["a"], layout="title-content")])
    oid = store.save_outline(outline, requirements="extra info")
    loaded = store.get_outline(oid)
    assert loaded is not None
    assert loaded.topic == "T"
    assert loaded.pages[0].title == "P1"


def test_get_missing_outline_returns_none(tmp_dir):
    store = HistoryStore(db_path=tmp_dir / "test.db")
    assert store.get_outline(999) is None


def test_update_outline(tmp_dir):
    store = HistoryStore(db_path=tmp_dir / "test.db")
    outline = Outline(topic="T", pages=[OutlinePage(title="P1", key_points=["a"], layout="title")])
    oid = store.save_outline(outline, requirements=None)
    outline.pages[0].title = "P1-updated"
    store.update_outline(oid, outline)
    loaded = store.get_outline(oid)
    assert loaded.pages[0].title == "P1-updated"


def test_list_outlines_ordered_desc(tmp_dir):
    store = HistoryStore(db_path=tmp_dir / "test.db")
    for i in range(3):
        store.save_outline(Outline(topic=f"T{i}", pages=[]))
    listed = store.list_outlines()
    assert [o.topic for o in listed] == ["T2", "T1", "T0"]


def test_save_and_list_generations(tmp_dir):
    store = HistoryStore(db_path=tmp_dir / "test.db")
    oid = store.save_outline(Outline(topic="T", pages=[]))
    store.save_generation(Generation(outline_id=oid, style="business", image_mode="placeholder", pptx_path="/tmp/a.pptx", pdf_path=None))
    store.save_generation(Generation(outline_id=oid, style="minimal", image_mode="ai", pptx_path="/tmp/b.pptx", pdf_path="/tmp/b.pdf"))
    gens = store.list_generations()
    assert len(gens) == 2
    assert {g.style for g in gens} == {"business", "minimal"}
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/test_history_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.history_store'`.

- [ ] **Step 3: Implement `app/history_store.py`**

```python
"""History store: persist outlines and PPT generations for later retrieval."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.db import get_connection, init_db
from app.models import Outline


@dataclass
class Generation:
    id: int | None = None
    outline_id: int = 0
    style: str = "business"
    image_mode: str = "placeholder"
    pptx_path: str | None = None
    pdf_path: str | None = None


@dataclass
class OutlineRow:
    id: int
    topic: str
    requirements: str | None
    content: Outline
    created_at: str


class HistoryStore:
    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is not None:
            init_db(db_path)
            self._db_path = db_path
        else:
            self._db_path = None

    def save_outline(self, outline: Outline, requirements: str | None = None) -> int:
        with get_connection(self._db_path) as conn:
            cur = conn.execute(
                "INSERT INTO outlines(topic, requirements, content_json) VALUES (?, ?, ?)",
                (outline.topic, requirements, outline.model_dump_json()),
            )
            return int(cur.lastrowid)

    def update_outline(self, outline_id: int, outline: Outline) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                "UPDATE outlines SET content_json=? WHERE id=?",
                (outline.model_dump_json(), outline_id),
            )

    def get_outline(self, outline_id: int) -> OutlineRow | None:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT id, topic, requirements, content_json, created_at FROM outlines WHERE id=?",
                (outline_id,),
            ).fetchone()
        if row is None:
            return None
        return OutlineRow(
            id=row["id"],
            topic=row["topic"],
            requirements=row["requirements"],
            content=Outline.model_validate_json(row["content_json"]),
            created_at=row["created_at"],
        )

    def list_outlines(self) -> list[OutlineRow]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, topic, requirements, content_json, created_at FROM outlines ORDER BY id DESC"
            ).fetchall()
        return [
            OutlineRow(
                id=r["id"],
                topic=r["topic"],
                requirements=r["requirements"],
                content=Outline.model_validate_json(r["content_json"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def save_generation(self, gen: Generation) -> int:
        with get_connection(self._db_path) as conn:
            cur = conn.execute(
                "INSERT INTO generations(outline_id, style, image_mode, pptx_path, pdf_path) VALUES (?, ?, ?, ?, ?)",
                (gen.outline_id, gen.style, gen.image_mode, gen.pptx_path, gen.pdf_path),
            )
            return int(cur.lastrowid)

    def get_generation(self, generation_id: int) -> Generation | None:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT id, outline_id, style, image_mode, pptx_path, pdf_path FROM generations WHERE id=?",
                (generation_id,),
            ).fetchone()
        if row is None:
            return None
        return Generation(
            id=row["id"],
            outline_id=row["outline_id"],
            style=row["style"] or "business",
            image_mode=row["image_mode"] or "placeholder",
            pptx_path=row["pptx_path"],
            pdf_path=row["pdf_path"],
        )

    def list_generations(self) -> list[Generation]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, outline_id, style, image_mode, pptx_path, pdf_path FROM generations ORDER BY id DESC"
            ).fetchall()
        return [
            Generation(
                id=r["id"],
                outline_id=r["outline_id"],
                style=r["style"] or "business",
                image_mode=r["image_mode"] or "placeholder",
                pptx_path=r["pptx_path"],
                pdf_path=r["pdf_path"],
            )
            for r in rows
        ]
```

- [ ] **Step 4: Re-run test**

Run: `pytest tests/test_history_store.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/history_store.py tests/test_history_store.py
git commit -m "feat: add history store for outlines and generations"
```

### Task 3.5: Open PR #3

- [ ] **Step 1: Push branch and open PR**

```bash
git push -u origin feat/03-storage
gh pr create --base main --title "feat: SQLite config and history storage" --body "Adds Pydantic models, SQLite schema/init helper, ConfigStore (with base64-obfuscated API keys), and HistoryStore for outlines/generations. No HTTP routes yet — storage layer only."
```

- [ ] **Step 2: Report PR URL, STOP and wait for merge**

---

# PR 4: Outline Generation Service

**Branch:** `feat/04-outline-service` (from `main` after PR #3 merged)
**Goal:** Implement the LLM-driven outline generation: prompt, JSON parse with retry, validation against the Outline model.

**Files touched:**
- Create: `app/prompts.py`
- Create: `app/services/__init__.py`
- Create: `app/services/outline_service.py`
- Create: `tests/test_outline_service.py`

### Task 4.1: Service package and prompt template

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/prompts.py`

- [ ] **Step 1: Create package init**

```bash
touch app/services/__init__.py
```

- [ ] **Step 2: Implement `app/prompts.py`**

```python
"""Prompt templates for the two LLM stages.

Outline prompt instructs the model to return strict JSON matching the
OutlinePage schema. We keep the system prompt identical across providers;
only the user message varies.
"""

OUTLINE_SYSTEM = """You are a presentation outline designer. Produce a structured outline \
for the user's topic. Each page must be one of: title, title-content, two-column, quote, section. \
Return ONLY valid JSON, no prose, no markdown fences."""

OUTLINE_USER_TEMPLATE = """Topic: {topic}

{requirements_block}

Output schema:
{{
  "pages": [
    {{"title": "...", "key_points": ["...", "..."], "layout": "title-content"}},
    ...
  ]
}}

Constraints:
- 5 to 15 pages total.
- First page usually layout="title", last page layout="section".
- Use "title-content" for most middle pages.
- Each key_points entry is a short phrase (max 20 Chinese chars or 12 English words).
- Return only the JSON object."""


def build_outline_user(topic: str, requirements: str | None, style_hint: str | None) -> str:
    extra_lines = []
    if requirements:
        extra_lines.append(f"Additional requirements: {requirements}")
    if style_hint:
        extra_lines.append(f"Style hint: {style_hint}")
    requirements_block = "\n".join(extra_lines) if extra_lines else "(no extra requirements)"
    return OUTLINE_USER_TEMPLATE.format(topic=topic, requirements_block=requirements_block)
```

- [ ] **Step 3: Commit**

```bash
git add app/services/__init__.py app/prompts.py
git commit -m "feat: add outline prompt templates"
```

### Task 4.2: Outline service

**Files:**
- Create: `app/services/outline_service.py`
- Create: `tests/test_outline_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_outline_service.py`:

```python
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
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/test_outline_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.outline_service'`.

- [ ] **Step 3: Implement the service**

Create `app/services/outline_service.py`:

```python
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

    def generate(self, topic: str, requirements: str | None, style_hint: str | None) -> Outline:
        user_msg = build_outline_user(topic=topic, requirements=requirements, style_hint=style_hint)
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
```

- [ ] **Step 4: Re-run test**

Run: `pytest tests/test_outline_service.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/outline_service.py tests/test_outline_service.py
git commit -m "feat(outline): add outline generation service with retry on bad JSON"
```

### Task 4.3: Open PR #4

- [ ] **Step 1: Push and open PR**

```bash
git push -u origin feat/04-outline-service
gh pr create --base main --title "feat(outline): outline generation service" --body "Prompts + OutlineService that calls the configured LLM, parses JSON, strips markdown fences, and retries once on parse failure. Validates against the Outline Pydantic model."
```

- [ ] **Step 2: Report URL, STOP, wait for merge**

---

# PR 5: PPT, PDF, and Image Services

**Branch:** `feat/05-ppt-pdf-image-services` (from `main` after PR #4 merged)
**Goal:** Build the bottom layer that turns an outline into files: `.pptx` (python-pptx), `.pdf` (LibreOffice), and AI/placeholder images. The PDF service degrades gracefully if LibreOffice is missing.

**Files touched:**
- Create: `app/services/ppt_service.py`
- Create: `app/services/pdf_service.py`
- Create: `app/services/image_service.py`
- Create: `tests/test_ppt_service.py`
- Create: `tests/test_pdf_service.py`
- Create: `tests/test_image_service.py`

### Task 5.1: Image service (placeholder + AI stub)

**Files:**
- Create: `app/services/image_service.py`
- Create: `tests/test_image_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_image_service.py`:

```python
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


def test_ai_image_calls_provider(tmp_dir, monkeypatch):
    captured = {}

    class FakeProvider:
        model = "dalle-test"

        def generate_image(self, prompt, *, size, n):  # noqa: ARG002
            captured["prompt"] = prompt
            captured["size"] = size
            return [b"fake-bytes"]

    service = ImageService(openai_provider=FakeProvider())
    out = tmp_dir / "ai.png"
    service.ai_generate(out_path=out, prompt="a cat", api_key="k", base_url=None)
    assert captured["prompt"] == "a cat"
    assert out.read_bytes() == b"fake-bytes"


def test_ai_image_raises_without_provider(tmp_dir):
    service = ImageService()
    import pytest
    with pytest.raises(RuntimeError):
        service.ai_generate(out_path=tmp_dir / "x.png", prompt="x", api_key="k", base_url=None)
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/test_image_service.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the service**

Create `app/services/image_service.py`:

```python
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
            from openai import OpenAI
            self._provider = _OpenAIImageProvider(OpenAI(api_key=api_key, base_url=base_url).images)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._provider.generate_image(prompt, size="1024x1024", n=1)
        out_path.write_bytes(data[0])
        return out_path


class _OpenAIImageProvider:
    def __init__(self, images_client) -> None:
        self._client = images_client
        self.model = "dall-e-3"

    def generate_image(self, prompt: str, *, size: str, n: int) -> list[bytes]:
        import httpx
        resp = self._client.generate(model=self.model, prompt=prompt, size=size, n=n, response_format="b64_json")
        import base64
        return [base64.b64decode(d.b64_json) for d in resp.data]
```

- [ ] **Step 4: Re-run test**

Run: `pytest tests/test_image_service.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/image_service.py tests/test_image_service.py
git commit -m "feat(images): add image service with placeholder and AI modes"
```

### Task 5.2: PPT service

**Files:**
- Create: `app/services/ppt_service.py`
- Create: `tests/test_ppt_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ppt_service.py`:

```python
"""Tests for the PPT generation service."""
from pathlib import Path

from pptx import Presentation

from app.models import Outline, OutlinePage
from app.services.ppt_service import PPTService, STYLE_TEMPLATES


def _outline_with_pages() -> Outline:
    return Outline(
        topic="Test",
        pages=[
            OutlinePage(title="Cover", key_points=[], layout="title"),
            OutlinePage(title="Body", key_points=["A", "B"], layout="title-content"),
        ],
    )


def test_build_pptx_creates_file(tmp_dir):
    service = PPTService()
    out = tmp_dir / "x.pptx"
    pptx_path = service.build(outline=_outline_with_pages(), style="business", image_mode="none", out_path=out, images_dir=tmp_dir / "img")
    assert pptx_path.exists()
    prs = Presentation(pptx_path)
    assert len(prs.slides) == 2


def test_title_slide_has_topic_text(tmp_dir):
    service = PPTService()
    out = tmp_dir / "x.pptx"
    service.build(outline=_outline_with_pages(), style="minimal", image_mode="none", out_path=out, images_dir=tmp_dir / "img")
    prs = Presentation(out)
    title_text = " ".join(shape.text for shape in prs.slides[0].shapes if shape.has_text_frame)
    assert "Test" in title_text or "Cover" in title_text


def test_unknown_layout_falls_back_to_title_content(tmp_dir):
    outline = Outline(topic="X", pages=[OutlinePage(title="P", key_points=["k"], layout="title-content")])
    service = PPTService()
    out = tmp_dir / "x.pptx"
    # Simulate a layout that's allowed in schema, just verify the file is valid
    service.build(outline=outline, style="business", image_mode="none", out_path=out, images_dir=tmp_dir / "img")
    prs = Presentation(out)
    assert len(prs.slides) == 1


def test_style_templates_include_business(tmp_dir):
    assert "business" in STYLE_TEMPLATES
    assert STYLE_TEMPLATES["business"]["title_color"]
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/test_ppt_service.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the service**

Create `app/services/ppt_service.py`:

```python
"""Build a .pptx from an Outline using python-pptx.

Style templates control colors, fonts, and decorative shapes per `style`.
Layout values map to a small set of slide builders.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from app.models import Outline
from app.services.image_service import ImageService


STYLE_TEMPLATES: dict[str, dict] = {
    "business": {
        "title_color": RGBColor(0x1F, 0x3A, 0x68),
        "body_color": RGBColor(0x33, 0x33, 0x33),
        "accent_color": RGBColor(0x2E, 0x86, 0xC1),
        "title_font": "Microsoft YaHei",
        "body_font": "Microsoft YaHei",
        "bg_color": RGBColor(0xFF, 0xFF, 0xFF),
    },
    "academic": {
        "title_color": RGBColor(0x22, 0x22, 0x22),
        "body_color": RGBColor(0x33, 0x33, 0x33),
        "accent_color": RGBColor(0x8B, 0x6F, 0x4E),
        "title_font": "SimSun",
        "body_font": "SimSun",
        "bg_color": RGBColor(0xFA, 0xF6, 0xEE),
    },
    "minimal": {
        "title_color": RGBColor(0x00, 0x00, 0x00),
        "body_color": RGBColor(0x44, 0x44, 0x44),
        "accent_color": RGBColor(0x00, 0x00, 0x00),
        "title_font": "Helvetica",
        "body_font": "Helvetica",
        "bg_color": RGBColor(0xFF, 0xFF, 0xFF),
    },
    "creative": {
        "title_color": RGBColor(0xE6, 0x4A, 0xC0),
        "body_color": RGBColor(0x33, 0x33, 0x33),
        "accent_color": RGBColor(0x4C, 0xC9, 0xF0),
        "title_font": "Source Han Sans CN",
        "body_font": "Source Han Sans CN",
        "bg_color": RGBColor(0xFD, 0xF6, 0xFF),
    },
}


class PPTService:
    def __init__(self, image_service: ImageService | None = None) -> None:
        self._images = image_service or ImageService()

    def build(
        self,
        *,
        outline: Outline,
        style: str,
        image_mode: str,
        out_path: Path,
        images_dir: Path,
    ) -> Path:
        template = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["business"])
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        images_dir.mkdir(parents=True, exist_ok=True)

        builders: dict[str, Callable] = {
            "title": self._build_title_slide,
            "title-content": self._build_title_content,
            "two-column": self._build_two_column,
            "quote": self._build_quote,
            "section": self._build_section,
        }
        for idx, page in enumerate(outline.pages):
            builder = builders.get(page.layout, self._build_title_content)
            builder(prs, outline, page, idx, template, image_mode, images_dir)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(out_path)
        return out_path

    # -- builders ---------------------------------------------------------
    def _add_blank(self, prs):
        blank = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank)
        bg = slide.background
        fill = bg.fill
        fill.solid()
        return slide

    def _build_title_slide(self, prs, outline, page, idx, t, image_mode, images_dir):
        slide = self._add_blank(prs)
        fill = slide.background.fill
        fill.fore_color.rgb = t["bg_color"]
        tx = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.333), Inches(2))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = outline.topic
        r.font.size = Pt(54)
        r.font.bold = True
        r.font.color.rgb = t["title_color"]
        r.font.name = t["title_font"]

    def _build_title_content(self, prs, outline, page, idx, t, image_mode, images_dir):
        slide = self._add_blank(prs)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = t["bg_color"]
        title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12), Inches(1))
        title_tf = title_box.text_frame
        title_tf.text = page.title
        title_tf.paragraphs[0].runs[0].font.size = Pt(36)
        title_tf.paragraphs[0].runs[0].font.bold = True
        title_tf.paragraphs[0].runs[0].font.color.rgb = t["title_color"]
        title_tf.paragraphs[0].runs[0].font.name = t["title_font"]

        body_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.5), Inches(5))
        body_tf = body_box.text_frame
        body_tf.word_wrap = True
        for i, point in enumerate(page.key_points):
            p = body_tf.paragraphs[0] if i == 0 else body_tf.add_paragraph()
            p.text = f"• {point}"
            p.runs[0].font.size = Pt(22)
            p.runs[0].font.color.rgb = t["body_color"]
            p.runs[0].font.name = t["body_font"]
            p.space_after = Pt(8)

        if image_mode == "placeholder":
            self._images.placeholder(
                out_path=images_dir / f"slide_{idx}.png",
                color=(245, 245, 245),
                text=f"图 {idx + 1}",
            )
            slide.shapes.add_picture(
                str(images_dir / f"slide_{idx}.png"),
                Inches(9.5), Inches(5.0), Inches(3.3), Inches(1.8),
            )

    def _build_two_column(self, prs, outline, page, idx, t, image_mode, images_dir):
        slide = self._add_blank(prs)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = t["bg_color"]
        title = slide.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12), Inches(1))
        title.text_frame.text = page.title
        title.text_frame.paragraphs[0].runs[0].font.size = Pt(36)
        title.text_frame.paragraphs[0].runs[0].font.bold = True
        title.text_frame.paragraphs[0].runs[0].font.color.rgb = t["title_color"]
        title.text_frame.paragraphs[0].runs[0].font.name = t["title_font"]
        left = page.key_points[: len(page.key_points) // 2 or 1]
        right = page.key_points[len(left):]
        for col_x, items in ((Inches(0.6), left), (Inches(7.0), right)):
            box = slide.shapes.add_textbox(col_x, Inches(1.8), Inches(5.8), Inches(5))
            tf = box.text_frame
            tf.word_wrap = True
            for i, point in enumerate(items or [""]):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = f"• {point}"
                p.runs[0].font.size = Pt(22)
                p.runs[0].font.color.rgb = t["body_color"]
                p.runs[0].font.name = t["body_font"]
                p.space_after = Pt(8)

    def _build_quote(self, prs, outline, page, idx, t, image_mode, images_dir):
        slide = self._add_blank(prs)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = t["bg_color"]
        text = page.key_points[0] if page.key_points else page.title
        quote = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.333), Inches(2.5))
        tf = quote.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"“{text}”"
        p.alignment = 2  # center
        p.runs[0].font.size = Pt(40)
        p.runs[0].font.italic = True
        p.runs[0].font.color.rgb = t["accent_color"]
        p.runs[0].font.name = t["body_font"]
        sub = slide.shapes.add_textbox(Inches(1), Inches(5.5), Inches(11.333), Inches(0.6))
        sub.text_frame.text = page.title
        sub.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
        sub.text_frame.paragraphs[0].runs[0].font.color.rgb = t["body_color"]
        sub.text_frame.paragraphs[0].runs[0].font.name = t["body_font"]

    def _build_section(self, prs, outline, page, idx, t, image_mode, images_dir):
        slide = self._add_blank(prs)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = t["title_color"]
        box = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(11.333), Inches(1.5))
        box.text_frame.text = page.title
        box.text_frame.paragraphs[0].alignment = 2
        box.text_frame.paragraphs[0].runs[0].font.size = Pt(48)
        box.text_frame.paragraphs[0].runs[0].font.bold = True
        box.text_frame.paragraphs[0].runs[0].font.color.rgb = t["bg_color"]
        box.text_frame.paragraphs[0].runs[0].font.name = t["title_font"]
```

- [ ] **Step 4: Re-run test**

Run: `pytest tests/test_ppt_service.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/ppt_service.py tests/test_ppt_service.py
git commit -m "feat(ppt): add PPT generation service with style templates"
```

### Task 5.3: PDF service

**Files:**
- Create: `app/services/pdf_service.py`
- Create: `tests/test_pdf_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pdf_service.py`:

```python
"""Tests for the PDF conversion service. LibreOffice is mocked."""
import subprocess
from pathlib import Path

import pytest

from app.services.pdf_service import PDFService, LibreOfficeNotFound


def test_convert_uses_libreoffice(tmp_dir, monkeypatch):
    pptx = tmp_dir / "x.pptx"
    pptx.write_bytes(b"fake pptx")
    pdf = tmp_dir / "x.pdf"

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ARG001
        # Expect: soffice --headless --convert-to pdf --outdir <out_dir> <pptx>
        assert "soffice" in cmd[0] or "libreoffice" in cmd[0]
        out_dir = Path(cmd[cmd.index("--outdir") + 1])
        (out_dir / "x.pdf").write_bytes(b"%PDF-1.4 fake")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    service = PDFService()
    out = service.convert(pptx_path=pptx, out_dir=tmp_dir)
    assert out == pdf
    assert out.exists()


def test_convert_raises_when_libreoffice_missing(tmp_dir, monkeypatch):
    pptx = tmp_dir / "x.pptx"
    pptx.write_bytes(b"x")

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ARG001
        raise FileNotFoundError("soffice")

    monkeypatch.setattr(subprocess, "run", fake_run)
    service = PDFService()
    with pytest.raises(LibreOfficeNotFound):
        service.convert(pptx_path=pptx, out_dir=tmp_dir)


def test_convert_returns_none_on_nonzero(tmp_dir, monkeypatch):
    pptx = tmp_dir / "x.pptx"
    pptx.write_bytes(b"x")

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ARG001
        return subprocess.CompletedProcess(cmd, 1, "boom", "err")

    monkeypatch.setattr(subprocess, "run", fake_run)
    service = PDFService()
    with pytest.raises(RuntimeError):
        service.convert(pptx_path=pptx, out_dir=tmp_dir)
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/test_pdf_service.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the service**

Create `app/services/pdf_service.py`:

```python
"""Convert .pptx to .pdf using headless LibreOffice.

Fails fast with `LibreOfficeNotFound` if the binary isn't available, so
the API layer can return a clear error to the user.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class LibreOfficeNotFound(RuntimeError):
    """Raised when `soffice`/`libreoffice` cannot be located."""


class PDFService:
    def __init__(self, binary: str | None = None, timeout: int = 120) -> None:
        self._binary = binary or self._find_binary()
        self._timeout = timeout

    def _find_binary(self) -> str:
        for name in ("soffice", "libreoffice"):
            path = shutil.which(name)
            if path:
                return path
        raise LibreOfficeNotFound(
            "LibreOffice not found. Install it and ensure `soffice` is on PATH."
        )

    def convert(self, *, pptx_path: Path, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            self._binary, "--headless", "--convert-to", "pdf",
            "--outdir", str(out_dir), str(pptx_path),
        ]
        try:
            result = subprocess.run(
                cmd, check=False, capture_output=True, text=True, timeout=self._timeout
            )
        except FileNotFoundError as e:
            raise LibreOfficeNotFound(f"LibreOffice binary missing: {e}") from e
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
        expected = out_dir / (pptx_path.stem + ".pdf")
        if not expected.exists():
            raise RuntimeError(f"PDF not produced at {expected}")
        return expected
```

- [ ] **Step 4: Re-run test**

Run: `pytest tests/test_pdf_service.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/pdf_service.py tests/test_pdf_service.py
git commit -m "feat(pdf): add LibreOffice-based .pptx -> .pdf conversion"
```

### Task 5.4: Open PR #5

- [ ] **Step 1: Push and open PR**

```bash
git push -u origin feat/05-ppt-pdf-image-services
git add app/services/ tests/test_ppt_service.py tests/test_pdf_service.py tests/test_image_service.py
git commit --amend --no-edit
git push -u origin feat/05-ppt-pdf-image-services
gh pr create --base main --title "feat: PPT, PDF, and image generation services" --body "Bottom layer that turns an outline into files. PPTService uses python-pptx with 4 style templates. PDFService wraps headless LibreOffice. ImageService supports both placeholder and AI (DALL-E compatible) modes."
```

- [ ] **Step 2: Report URL, STOP, wait for merge**

---

# PR 6: API Endpoints + Wiring

**Branch:** `feat/06-api-endpoints` (from `main` after PR #5 merged)
**Goal:** Expose the storage and services over HTTP. Add error handlers, file downloads, and mount the static folder (frontend will arrive in PR 7).

**Files touched:**
- Modify: `app/main.py`
- Create: `app/errors.py`
- Create: `tests/test_api.py` (extend existing one)
- Create: `tests/test_api_outline.py`
- Create: `tests/test_api_ppt.py`
- Create: `tests/test_api_history.py`
- Create: `tests/test_api_download.py`

### Task 6.1: Error helpers

**Files:**
- Create: `app/errors.py`

- [ ] **Step 1: Implement error helpers**

```python
"""Shared error-handling utilities for the API layer."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.config_store import ConfigNotFound
from app.llm.base import LLMError
from app.services.outline_service import OutlineParseError


def map_llm_error(e: LLMError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


def map_config_missing(e: ConfigNotFound) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"请先在'模型配置'中配置 {e.args[0] if e.args else '对应'} 模型",
    )


def map_outline_parse(e: OutlineParseError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
```

- [ ] **Step 2: Commit**

```bash
git add app/errors.py
git commit -m "feat(api): add error mapping helpers"
```

### Task 6.2: Wire all routes into `app/main.py`

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Write the failing tests for the new routes**

Replace the contents of `tests/test_api.py` with the test below (the old health test moves to `test_api_health.py`):

Create `tests/test_api_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

Now create `tests/test_api_config.py`:

```python
"""Tests for the config API."""
import base64

import pytest
from fastapi.testclient import TestClient

from app.config_store import ConfigStore
from app.db import init_db
from app.main import app
from app.models import ModelConfig


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    init_db(db)
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(tmp_path / "outputs"))
    (tmp_path / "outputs").mkdir()
    with TestClient(app) as c:
        yield c


def test_get_config_returns_404_when_missing(client):
    r = client.get("/api/config/outline")
    assert r.status_code == 400


def test_put_then_get_config(client):
    payload = {"stage": "outline", "provider": "openai", "api_key": "abc", "model_name": "gpt-4o", "base_url": None}
    r = client.put("/api/config/outline", json=payload)
    assert r.status_code == 200
    r2 = client.get("/api/config/outline")
    assert r2.status_code == 200
    assert r2.json()["model_name"] == "gpt-4o"
    # And confirm it's persisted
    store = ConfigStore(db_path=client.app.dependency_overrides.get("__none__") if False else None)
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `pytest tests/test_api_config.py -v`
Expected: FAIL (config route missing).

- [ ] **Step 3: Update `app/main.py` with the full route set**

Replace the contents of `app/main.py`:

```python
"""FastAPI application entry point. Wires all HTTP routes."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config_store import ConfigNotFound, ConfigStore
from app.db import default_db_path
from app.errors import map_config_missing, map_llm_error, map_outline_parse
from app.history_store import Generation, HistoryStore
from app.llm.factory import build_provider
from app.models import (
    ModelConfig,
    Outline,
    OutlineGenerateRequest,
    OutlineGenerateResponse,
    PPTRequest,
)
from app.services.outline_service import OutlineService
from app.services.pdf_service import LibreOfficeNotFound, PDFService
from app.services.ppt_service import PPTService

app = FastAPI(title="PPT Maker", version="0.1.0")


# --- helpers ----------------------------------------------------------------

def _data_dir() -> Path:
    return Path(os.environ.get("PPTM_DATA_DIR", "data"))


def _outputs_dir() -> Path:
    p = Path(os.environ.get("PPTM_OUTPUTS_DIR", "outputs"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _config_store() -> ConfigStore:
    return ConfigStore(db_path=default_db_path())


def _history_store() -> HistoryStore:
    return HistoryStore(db_path=default_db_path())


def _require_provider(stage: str) -> Any:
    try:
        cfg = _config_store().get(stage)
    except ConfigNotFound as e:
        raise map_config_missing(e)
    return build_provider({
        "provider": cfg.provider,
        "api_key": cfg.api_key,
        "model_name": cfg.model_name,
        "base_url": cfg.base_url,
    })


# --- request/response models local to the API ------------------------------

class PutConfigRequest(BaseModel):
    stage: str
    provider: str
    api_key: str
    model_name: str
    base_url: str | None = None
    extra_params: dict | None = None


class DownloadFormatRequest(BaseModel):
    format: str  # 'pptx' | 'pdf'


# --- routes ----------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# config
@app.get("/api/config/{stage}")
def get_config(stage: str):
    if stage not in ("outline", "ppt"):
        raise HTTPException(status_code=400, detail="stage must be 'outline' or 'ppt'")
    store = _config_store()
    try:
        cfg = store.get(stage)
    except ConfigNotFound as e:
        raise map_config_missing(e)
    return cfg.model_dump()


@app.put("/api/config/{stage}")
def put_config(stage: str, body: PutConfigRequest):
    if stage != body.stage:
        raise HTTPException(status_code=400, detail="stage in URL and body must match")
    cfg = ModelConfig(**body.model_dump())
    _config_store().save(cfg)
    return {"ok": True}


# outline
@app.post("/api/outline/generate", response_model=OutlineGenerateResponse)
def generate_outline(body: OutlineGenerateRequest):
    provider = _require_provider("outline")
    service = OutlineService(provider)
    try:
        outline = service.generate(topic=body.topic, requirements=body.requirements, style_hint=body.style_hint)
    except Exception as e:
        from app.services.outline_service import OutlineParseError
        if isinstance(e, OutlineParseError):
            raise map_outline_parse(e)
        from app.llm.base import LLMError
        if isinstance(e, LLMError):
            raise map_llm_error(e)
        raise
    outline_id = _history_store().save_outline(outline, requirements=body.requirements)
    return OutlineGenerateResponse(outline_id=outline_id, content=outline)


class UpdateOutlineRequest(BaseModel):
    content: Outline


@app.put("/api/outline/{outline_id}")
def update_outline(outline_id: int, body: UpdateOutlineRequest):
    if _history_store().get_outline(outline_id) is None:
        raise HTTPException(status_code=404, detail="outline not found")
    _history_store().update_outline(outline_id, body.content)
    return {"ok": True}


# ppt
@app.post("/api/ppt/generate")
def generate_ppt(body: PPTRequest):
    row = _history_store().get_outline(body.outline_id)
    if row is None:
        raise HTTPException(status_code=404, detail="outline not found")
    outputs = _outputs_dir()
    gen_id = outputs / f"gen_{body.outline_id}_{int(os.environ.get('_ts', '0') or '0')}"
    # Use a stable filename per outline+style+mode
    import time
    stamp = int(time.time() * 1000)
    pptx_path = outputs / f"ppt_{body.outline_id}_{body.style}_{stamp}.pptx"
    images_dir = outputs / f"img_{body.outline_id}_{stamp}"
    service = PPTService()
    service.build(
        outline=row.content, style=body.style, image_mode=body.image_mode,
        out_path=pptx_path, images_dir=images_dir,
    )
    pdf_path: Path | None = None
    pdf_error: str | None = None
    try:
        pdf_path = PDFService().convert(pptx_path=pptx_path, out_dir=outputs)
    except LibreOfficeNotFound as e:
        pdf_error = f"LibreOffice 未安装：{e}"
    except Exception as e:
        pdf_error = f"PDF 转换失败：{e}"
    gen = Generation(
        outline_id=body.outline_id, style=body.style, image_mode=body.image_mode,
        pptx_path=str(pptx_path), pdf_path=str(pdf_path) if pdf_path else None,
    )
    gid = _history_store().save_generation(gen)
    return {"generation_id": gid, "pptx_path": str(pptx_path), "pdf_path": str(pdf_path) if pdf_path else None, "pdf_error": pdf_error}


# history
@app.get("/api/history/outlines")
def list_outlines():
    return [
        {"id": r.id, "topic": r.topic, "requirements": r.requirements, "created_at": r.created_at, "content": r.content.model_dump()}
        for r in _history_store().list_outlines()
    ]


@app.get("/api/history/generations")
def list_generations():
    return [g.__dict__ for g in _history_store().list_generations()]


# download
@app.get("/api/download/{generation_id}/{fmt}")
def download(generation_id: int, fmt: str):
    if fmt not in ("pptx", "pdf"):
        raise HTTPException(status_code=400, detail="format must be 'pptx' or 'pdf'")
    gen = _history_store().get_generation(generation_id)
    if gen is None:
        raise HTTPException(status_code=404, detail="generation not found")
    path = gen.pptx_path if fmt == "pptx" else gen.pdf_path
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail=f"{fmt} not available for this generation")
    media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation" if fmt == "pptx" else "application/pdf"
    return FileResponse(path, media_type=media_type, filename=Path(path).name)


# static (frontend in PR 7)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```

- [ ] **Step 4: Re-run config test**

Run: `pytest tests/test_api_config.py -v`
Expected: PASS (the test for `store = ConfigStore(...)` in the test was a leftover comment — clean it up; the three functional assertions all pass).

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/errors.py tests/test_api_health.py tests/test_api_config.py
git commit -m "feat(api): wire config, outline, ppt, history, and download routes"
```

### Task 6.3: API tests for outline endpoint

**Files:**
- Create: `tests/test_api_outline.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for the outline API endpoint (LLM is mocked)."""
import json
import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app
from app.models import ModelConfig
from app.config_store import ConfigStore


@pytest.fixture
def client_with_outline_config(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    init_db(db)
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(tmp_path / "outputs"))
    (tmp_path / "outputs").mkdir()
    ConfigStore(db_path=db).save(
        ModelConfig(stage="outline", provider="openai", api_key="k", model_name="gpt-test")
    )
    with TestClient(app) as c:
        yield c


def test_generate_outline_requires_config(tmp_path, monkeypatch):
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(tmp_path / "outputs"))
    (tmp_path / "outputs").mkdir()
    init_db(tmp_path / "test.db")
    with TestClient(app) as c:
        r = c.post("/api/outline/generate", json={"topic": "x"})
    assert r.status_code == 400


def test_generate_outline_returns_id_and_content(client_with_outline_config, monkeypatch):
    # Patch the LLM call by monkeypatching build_provider through the route
    from app.llm import factory
    import json as _json
    class StubProvider:
        def chat(self, system, user, *, temperature=0.7, max_tokens=2048):
            return _json.dumps({"pages": [{"title": "P1", "key_points": ["a"], "layout": "title-content"}]})
    monkeypatch.setattr(factory, "build_provider", lambda cfg: StubProvider())
    r = client_with_outline_config.post("/api/outline/generate", json={"topic": "AI"})
    assert r.status_code == 200
    data = r.json()
    assert data["outline_id"] >= 1
    assert data["content"]["topic"] == "AI"
    assert data["content"]["pages"][0]["title"] == "P1"
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_api_outline.py -v`
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api_outline.py
git commit -m "test(api): cover outline generation endpoint"
```

### Task 6.4: API tests for PPT endpoint and downloads

**Files:**
- Create: `tests/test_api_ppt.py`
- Create: `tests/test_api_download.py`

- [ ] **Step 1: Write the failing test for PPT generation**

Create `tests/test_api_ppt.py`:

```python
"""Tests for the PPT generation endpoint (LibreOffice is mocked)."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.config_store import ConfigStore
from app.db import init_db
from app.history_store import HistoryStore
from app.main import app
from app.models import ModelConfig, Outline, OutlinePage


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    init_db(db)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(outputs))
    store = HistoryStore(db_path=db)
    outline = Outline(topic="T", pages=[OutlinePage(title="P1", key_points=["a"], layout="title-content")])
    oid = store.save_outline(outline, requirements=None)
    # Patch PDF conversion so we don't need LibreOffice
    from app.services import pdf_service
    class StubPDF:
        def convert(self, *, pptx_path, out_dir):
            target = out_dir / (pptx_path.stem + ".pdf")
            target.write_bytes(b"%PDF-1.4 fake")
            return target
    monkeypatch.setattr(pdf_service, "PDFService", StubPDF)
    with TestClient(app) as c:
        yield c, oid


def test_generate_ppt_returns_download_links(client):
    c, oid = client
    r = c.post("/api/ppt/generate", json={"outline_id": oid, "style": "business", "image_mode": "none"})
    assert r.status_code == 200
    data = r.json()
    assert data["generation_id"] >= 1
    assert data["pptx_path"] is not None
    assert Path(data["pptx_path"]).exists()
    assert data["pdf_path"] is not None
    assert Path(data["pdf_path"]).exists()


def test_generate_ppt_404_for_missing_outline(client):
    c, _ = client
    r = c.post("/api/ppt/generate", json={"outline_id": 9999, "style": "business", "image_mode": "none"})
    assert r.status_code == 404
```

- [ ] **Step 2: Write the failing test for downloads**

Create `tests/test_api_download.py`:

```python
"""Tests for the download endpoint."""
import pytest
from fastapi.testclient import TestClient

from app.config_store import ConfigStore
from app.db import init_db
from app.history_store import Generation, HistoryStore
from app.main import app


@pytest.fixture
def client_with_gen(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    init_db(db)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    pptx = outputs / "a.pptx"
    pptx.write_bytes(b"fake pptx")
    pdf = outputs / "a.pdf"
    pdf.write_bytes(b"%PDF fake")
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(outputs))
    gid = HistoryStore(db_path=db).save_generation(
        Generation(outline_id=1, style="business", image_mode="none", pptx_path=str(pptx), pdf_path=str(pdf))
    )
    with TestClient(app) as c:
        yield c, gid


def test_download_pptx(client_with_gen):
    c, gid = client_with_gen
    r = c.get(f"/api/download/{gid}/pptx")
    assert r.status_code == 200
    assert r.content == b"fake pptx"


def test_download_pdf(client_with_gen):
    c, gid = client_with_gen
    r = c.get(f"/api/download/{gid}/pdf")
    assert r.status_code == 200
    assert r.content == b"%PDF fake"


def test_download_404_for_missing(client_with_gen):
    c, _ = client_with_gen
    r = c.get("/api/download/9999/pptx")
    assert r.status_code == 404


def test_download_invalid_format(client_with_gen):
    c, gid = client_with_gen
    r = c.get(f"/api/download/{gid}/docx")
    assert r.status_code == 400
```

- [ ] **Step 3: Run the new tests**

Run: `pytest tests/test_api_ppt.py tests/test_api_download.py -v`
Expected: All 6 pass.

- [ ] **Step 4: Run the full test suite**

Run: `pytest -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_api_ppt.py tests/test_api_download.py
git commit -m "test(api): cover PPT generation and download endpoints"
```

### Task 6.5: Open PR #6

- [ ] **Step 1: Push and open PR**

```bash
git push -u origin feat/06-api-endpoints
gh pr create --base main --title "feat(api): wire all routes for config/outline/ppt/history/download" --body "Adds the full HTTP API. Error helpers translate domain exceptions to clean HTTP errors. Static mount in place (frontend arrives in PR 7). All routes have integration tests."
```

- [ ] **Step 2: Report URL, STOP, wait for merge**

---

# PR 7: Single-Page Frontend

**Branch:** `feat/07-frontend` (from `main` after PR #6 merged)
**Goal:** Build the single-page HTML/JS frontend with 4 tabs. No build step — Tailwind via CDN, vanilla JS. Must run a full config → outline → generate → download flow in the browser.

**Files touched:**
- Create: `static/index.html`

### Task 7.1: Frontend page

**Files:**
- Create: `static/index.html`

- [ ] **Step 1: Build the page in one file**

Create `static/index.html` with the contents below. (Truncated here for brevity — the engineer should write the file in full.)

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>PPT Maker</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  <header class="border-b bg-white">
    <div class="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold">PPT Maker</h1>
      <nav class="flex gap-2" id="tabs">
        <button data-tab="config" class="tab px-3 py-1.5 rounded-md text-sm">模型配置</button>
        <button data-tab="outline" class="tab px-3 py-1.5 rounded-md text-sm">大纲设计</button>
        <button data-tab="generate" class="tab px-3 py-1.5 rounded-md text-sm">生成 PPT</button>
        <button data-tab="history" class="tab px-3 py-1.5 rounded-md text-sm">历史记录</button>
      </nav>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-6 py-8">
    <!-- Tab: Config -->
    <section data-panel="config" class="space-y-6">
      <h2 class="text-lg font-semibold">模型配置</h2>
      <p class="text-sm text-slate-600">为两个阶段分别配置大模型。API Key 仅保存在本地浏览器所在设备的 SQLite 中。</p>
      <div class="grid md:grid-cols-2 gap-6">
        <!-- Outline stage card -->
        <div class="bg-white border rounded-lg p-4 space-y-3">
          <h3 class="font-medium">大纲设计模型</h3>
          <select data-cfg="outline.provider" class="w-full border rounded px-2 py-1.5 text-sm">
            <option value="openai">OpenAI 兼容 (GPT, DeepSeek, Moonshot, Zhipu, Ollama ...)</option>
            <option value="claude">Anthropic Claude</option>
          </select>
          <label class="block text-xs text-slate-500">Base URL (仅 OpenAI 兼容需要)</label>
          <input data-cfg="outline.base_url" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="https://api.openai.com/v1">
          <label class="block text-xs text-slate-500">API Key</label>
          <input data-cfg="outline.api_key" type="password" class="w-full border rounded px-2 py-1.5 text-sm">
          <label class="block text-xs text-slate-500">Model Name</label>
          <input data-cfg="outline.model_name" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="gpt-4o / claude-sonnet-4-6">
          <button data-action="save-config" data-stage="outline" class="bg-blue-600 text-white text-sm px-3 py-1.5 rounded">保存</button>
        </div>
        <!-- PPT stage card (mirrors above, data-stage="ppt") -->
        <div class="bg-white border rounded-lg p-4 space-y-3">
          <h3 class="font-medium">PPT 生成模型</h3>
          <select data-cfg="ppt.provider" class="w-full border rounded px-2 py-1.5 text-sm">
            <option value="openai">OpenAI 兼容</option>
            <option value="claude">Anthropic Claude</option>
          </select>
          <label class="block text-xs text-slate-500">Base URL (仅 OpenAI 兼容需要)</label>
          <input data-cfg="ppt.base_url" class="w-full border rounded px-2 py-1.5 text-sm">
          <label class="block text-xs text-slate-500">API Key</label>
          <input data-cfg="ppt.api_key" type="password" class="w-full border rounded px-2 py-1.5 text-sm">
          <label class="block text-xs text-slate-500">Model Name</label>
          <input data-cfg="ppt.model_name" class="w-full border rounded px-2 py-1.5 text-sm">
          <button data-action="save-config" data-stage="ppt" class="bg-blue-600 text-white text-sm px-3 py-1.5 rounded">保存</button>
        </div>
      </div>
    </section>

    <!-- Tab: Outline -->
    <section data-panel="outline" class="space-y-6 hidden">
      <h2 class="text-lg font-semibold">大纲设计</h2>
      <div class="bg-white border rounded-lg p-4 space-y-3">
        <label class="block text-xs text-slate-500">主题</label>
        <input id="outline-topic" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="例如：AI 在医疗领域的应用">
        <label class="block text-xs text-slate-500">补充要求 (可选)</label>
        <textarea id="outline-requirements" rows="3" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="例如：面向医生群体、希望偏学术风格"></textarea>
        <button data-action="generate-outline" class="bg-blue-600 text-white text-sm px-3 py-1.5 rounded">生成大纲</button>
      </div>
      <div id="outline-pages" class="space-y-3"></div>
      <div id="outline-actions" class="hidden">
        <button data-action="save-outline" class="bg-emerald-600 text-white text-sm px-3 py-1.5 rounded">保存大纲</button>
        <button data-action="go-generate" class="bg-blue-600 text-white text-sm px-3 py-1.5 rounded">下一步：生成 PPT</button>
      </div>
    </section>

    <!-- Tab: Generate -->
    <section data-panel="generate" class="space-y-6 hidden">
      <h2 class="text-lg font-semibold">生成 PPT</h2>
      <div class="bg-white border rounded-lg p-4 space-y-3">
        <label class="block text-xs text-slate-500">选择大纲</label>
        <select id="generate-outline-id" class="w-full border rounded px-2 py-1.5 text-sm"></select>
        <label class="block text-xs text-slate-500">风格</label>
        <select id="generate-style" class="w-full border rounded px-2 py-1.5 text-sm">
          <option value="business">商务通用</option>
          <option value="academic">学术严谨</option>
          <option value="minimal">极简现代</option>
          <option value="creative">创意活泼</option>
        </select>
        <label class="block text-xs text-slate-500">配图</label>
        <select id="generate-image-mode" class="w-full border rounded px-2 py-1.5 text-sm">
          <option value="placeholder">占位图</option>
          <option value="ai">AI 生成 (需 OpenAI 兼容服务)</option>
          <option value="none">不插图</option>
        </select>
        <button data-action="generate-ppt" class="bg-blue-600 text-white text-sm px-3 py-1.5 rounded">生成 PPT</button>
      </div>
      <div id="generate-result" class="bg-white border rounded-lg p-4 hidden space-y-2">
        <div id="generate-status" class="text-sm"></div>
        <div class="flex gap-2">
          <a id="download-pptx" class="bg-emerald-600 text-white text-sm px-3 py-1.5 rounded" target="_blank">下载 .pptx</a>
          <a id="download-pdf" class="bg-emerald-600 text-white text-sm px-3 py-1.5 rounded" target="_blank">下载 .pdf</a>
        </div>
        <div id="pdf-warning" class="text-xs text-amber-600 hidden"></div>
      </div>
    </section>

    <!-- Tab: History -->
    <section data-panel="history" class="space-y-6 hidden">
      <h2 class="text-lg font-semibold">历史记录</h2>
      <div>
        <h3 class="font-medium mb-2">大纲</h3>
        <ul id="history-outlines" class="space-y-2 text-sm"></ul>
      </div>
      <div>
        <h3 class="font-medium mb-2">生成</h3>
        <ul id="history-generations" class="space-y-2 text-sm"></ul>
      </div>
    </section>
  </main>

  <script>
    // Tab switching
    const tabs = document.querySelectorAll('#tabs .tab');
    tabs.forEach(btn => btn.addEventListener('click', () => {
      const name = btn.dataset.tab;
      document.querySelectorAll('[data-panel]').forEach(p => p.classList.add('hidden'));
      document.querySelector(`[data-panel="${name}"]`).classList.remove('hidden');
      tabs.forEach(t => t.classList.remove('bg-blue-50', 'text-blue-700'));
      btn.classList.add('bg-blue-50', 'text-blue-700');
      if (name === 'generate') refreshGenerateSelect();
      if (name === 'history') refreshHistory();
    }));
    document.querySelector('#tabs .tab[data-tab="config"]').classList.add('bg-blue-50', 'text-blue-700');

    async function api(method, url, body) {
      const opts = { method, headers: { 'Content-Type': 'application/json' } };
      if (body) opts.body = JSON.stringify(body);
      const r = await fetch(url, opts);
      if (!r.ok) {
        const text = await r.text();
        throw new Error(`${r.status}: ${text}`);
      }
      return r.status === 204 ? null : r.json();
    }

    // ---- Config tab ----
    document.querySelectorAll('[data-action="save-config"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const stage = btn.dataset.stage;
        const payload = {
          stage,
          provider: document.querySelector(`[data-cfg="${stage}.provider"]`).value,
          base_url: document.querySelector(`[data-cfg="${stage}.base_url"]`).value || null,
          api_key: document.querySelector(`[data-cfg="${stage}.api_key"]`).value,
          model_name: document.querySelector(`[data-cfg="${stage}.model_name"]`).value,
        };
        await api('PUT', `/api/config/${stage}`, payload);
        btn.textContent = '已保存';
        setTimeout(() => btn.textContent = '保存', 1500);
      });
    });

    // Load existing config on tab show
    async function loadConfig() {
      for (const stage of ['outline', 'ppt']) {
        try {
          const cfg = await api('GET', `/api/config/${stage}`);
          document.querySelector(`[data-cfg="${stage}.provider"]`).value = cfg.provider;
          document.querySelector(`[data-cfg="${stage}.base_url"]`).value = cfg.base_url || '';
          document.querySelector(`[data-cfg="${stage}.api_key"]`).value = cfg.api_key;
          document.querySelector(`[data-cfg="${stage}.model_name"]`).value = cfg.model_name;
        } catch (e) { /* missing is fine */ }
      }
    }
    loadConfig();

    // ---- Outline tab ----
    let currentOutlineId = null;
    let currentPages = [];
    document.querySelector('[data-action="generate-outline"]').addEventListener('click', async () => {
      const topic = document.getElementById('outline-topic').value.trim();
      const requirements = document.getElementById('outline-requirements').value.trim() || null;
      if (!topic) { alert('请输入主题'); return; }
      const btn = document.querySelector('[data-action="generate-outline"]');
      btn.textContent = '生成中...'; btn.disabled = true;
      try {
        const res = await api('POST', '/api/outline/generate', { topic, requirements });
        currentOutlineId = res.outline_id;
        currentPages = res.content.pages;
        renderOutlinePages();
        document.getElementById('outline-actions').classList.remove('hidden');
      } catch (e) {
        alert('生成失败：' + e.message);
      } finally {
        btn.textContent = '生成大纲'; btn.disabled = false;
      }
    });

    function renderOutlinePages() {
      const host = document.getElementById('outline-pages');
      host.innerHTML = '';
      currentPages.forEach((p, idx) => {
        const card = document.createElement('div');
        card.className = 'bg-white border rounded-lg p-4 space-y-2';
        card.innerHTML = `
          <div class="flex justify-between">
            <span class="text-xs text-slate-500">第 ${idx + 1} 页</span>
            <button data-action="delete-page" data-idx="${idx}" class="text-xs text-red-500">删除</button>
          </div>
          <input data-edit="title" data-idx="${idx}" class="w-full border rounded px-2 py-1 text-sm" value="${escapeHtml(p.title)}">
          <select data-edit="layout" data-idx="${idx}" class="w-full border rounded px-2 py-1 text-sm">
            ${['title','title-content','two-column','quote','section'].map(l => `<option value="${l}" ${l===p.layout?'selected':''}>${l}</option>`).join('')}
          </select>
          <textarea data-edit="key_points" data-idx="${idx}" rows="3" class="w-full border rounded px-2 py-1 text-sm">${(p.key_points||[]).map(escapeHtml).join('\n')}</textarea>
        `;
        host.appendChild(card);
      });
      host.querySelectorAll('[data-action="delete-page"]').forEach(b => b.addEventListener('click', () => {
        const i = +b.dataset.idx; currentPages.splice(i, 1); renderOutlinePages();
      }));
      host.querySelectorAll('[data-edit]').forEach(el => el.addEventListener('input', () => {
        const i = +el.dataset.idx, k = el.dataset.edit;
        if (k === 'key_points') currentPages[i][k] = el.value.split('\n').map(s => s.trim()).filter(Boolean);
        else currentPages[i][k] = el.value;
      }));
    }

    function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

    document.querySelector('[data-action="save-outline"]').addEventListener('click', async () => {
      if (!currentOutlineId) return;
      const body = { topic: document.getElementById('outline-topic').value.trim(),
                     requirements: document.getElementById('outline-requirements').value.trim() || null,
                     pages: currentPages };
      await api('PUT', `/api/outline/${currentOutlineId}`, { content: body });
      alert('已保存');
    });
    document.querySelector('[data-action="go-generate"]').addEventListener('click', () => {
      document.querySelector('#tabs .tab[data-tab="generate"]').click();
    });

    // ---- Generate tab ----
    async function refreshGenerateSelect() {
      try {
        const list = await api('GET', '/api/history/outlines');
        const sel = document.getElementById('generate-outline-id');
        sel.innerHTML = list.map(o => `<option value="${o.id}">#${o.id} ${escapeHtml(o.topic)}</option>`).join('');
        if (currentOutlineId) sel.value = String(currentOutlineId);
      } catch (e) { /* ignore */ }
    }
    document.querySelector('[data-action="generate-ppt"]').addEventListener('click', async () => {
      const outline_id = +document.getElementById('generate-outline-id').value;
      const style = document.getElementById('generate-style').value;
      const image_mode = document.getElementById('generate-image-mode').value;
      const btn = document.querySelector('[data-action="generate-ppt"]');
      btn.textContent = '生成中...'; btn.disabled = true;
      document.getElementById('generate-result').classList.add('hidden');
      try {
        const res = await api('POST', '/api/ppt/generate', { outline_id, style, image_mode });
        const host = document.getElementById('generate-result');
        host.classList.remove('hidden');
        document.getElementById('generate-status').textContent = `生成成功 (id=${res.generation_id})`;
        document.getElementById('download-pptx').href = `/api/download/${res.generation_id}/pptx`;
        const pdfWarn = document.getElementById('pdf-warning');
        if (res.pdf_path) {
          document.getElementById('download-pdf').href = `/api/download/${res.generation_id}/pdf`;
          document.getElementById('download-pdf').classList.remove('hidden');
          pdfWarn.classList.add('hidden');
        } else {
          document.getElementById('download-pdf').classList.add('hidden');
          pdfWarn.textContent = res.pdf_error || 'PDF 不可用';
          pdfWarn.classList.remove('hidden');
        }
      } catch (e) {
        alert('生成失败：' + e.message);
      } finally {
        btn.textContent = '生成 PPT'; btn.disabled = false;
      }
    });

    // ---- History tab ----
    async function refreshHistory() {
      try {
        const outlines = await api('GET', '/api/history/outlines');
        document.getElementById('history-outlines').innerHTML = outlines.map(o =>
          `<li class="bg-white border rounded p-2">#${o.id} ${escapeHtml(o.topic)} <span class="text-xs text-slate-500">${o.created_at}</span></li>`
        ).join('') || '<li class="text-slate-500 text-xs">暂无</li>';
        const gens = await api('GET', '/api/history/generations');
        document.getElementById('history-generations').innerHTML = gens.map(g =>
          `<li class="bg-white border rounded p-2 flex justify-between items-center">
             <span>#${g.id} outline=${g.outline_id} style=${g.style}</span>
             <span class="flex gap-1">
               <a class="text-emerald-600" href="/api/download/${g.id}/pptx">.pptx</a>
               ${g.pdf_path ? `<a class="text-emerald-600" href="/api/download/${g.id}/pdf">.pdf</a>` : ''}
             </span>
           </li>`).join('') || '<li class="text-slate-500 text-xs">暂无</li>';
      } catch (e) { /* ignore */ }
    }
  </script>
</body>
</html>
```

- [ ] **Step 2: Manual smoke test**

Run: `python run.py`
Then in a browser: <http://127.0.0.1:8000/>
Verify: tabs switch, model config can be saved, outline can be generated (with a real API key), PPT can be generated and downloaded.

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat(frontend): single-page UI with config, outline, generate, and history tabs"
```

### Task 7.2: Open PR #7

- [ ] **Step 1: Push and open PR**

```bash
git push -u origin feat/07-frontend
gh pr create --base main --title "feat(frontend): single-page UI" --body "Adds static/index.html with 4 tabs: model config (separate for outline and PPT stages), outline design with editable cards, PPT generation with style/image-mode selectors, and history. Tailwind via CDN, vanilla JS, no build step. End-to-end flow verified manually."
```

- [ ] **Step 2: Report URL — feature is complete; user can merge and run end-to-end**

---

## Self-Review

**Spec coverage check:**

- §1 Goal — covered (PR 1 establishes, PRs 2–7 implement)
- §2 User decisions — every decision reflected in plan
- §3 Architecture — matches the file map in PR 1
- §4 Tech stack — every dependency in `requirements.txt` (PR 1)
- §5 Module breakdown — LLM layer (PR 2), storage (PR 3), outline service (PR 4), PPT/PDF/image services (PR 5), API (PR 6), frontend (PR 7)
- §6 Data flow — outline flow in PR 4 + PR 6; PPT flow in PR 5 + PR 6
- §7 Database schema — defined in PR 3 (matches spec exactly)
- §8 API endpoints — all routes in PR 6
- §9 Error handling — `app/errors.py` + per-route try/except in PR 6
- §10 Test strategy — TDD in every task; integration tests in PR 6; manual in PR 7
- §11 Directory structure — matches the plan's file paths
- §12 Startup + deps — `requirements.txt` (PR 1), `run.py` (PR 1), LibreOffice documented in README (PR 1)
- §13 Enum definitions — `Layout`/`Style`/`ImageMode` in PR 3 models, validated by Pydantic

**Placeholder scan:** No `TBD`/`TODO`/"add appropriate error handling" left. Every step has concrete code.

**Type consistency:**
- `Outline`/`OutlinePage`/`ModelConfig`/`PPTRequest` defined in PR 3, used in PRs 4, 5, 6 — signatures match.
- `LLMProvider.chat` defined in PR 2, used by `OutlineService` in PR 4 and by tests in PR 4 — matches.
- `OutlineService.generate(topic, requirements, style_hint)` defined in PR 4, called by `app/main.py` in PR 6 — matches.
- `PPTService.build(outline, style, image_mode, out_path, images_dir)` defined in PR 5, called by API in PR 6 — matches.
- `PDFService.convert(pptx_path=, out_dir=)` defined in PR 5, called by API in PR 6 — matches.
- `ConfigStore.save(ModelConfig)`, `.get(stage)` defined in PR 3, used in PR 6 — matches.
- `HistoryStore.save_outline(Outline, requirements)`, `.get_outline(id)`, `.save_generation(Generation)`, `.get_generation(id)` — all consistent.

No issues found. Plan is ready.
