"""Shared pytest fixtures."""
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir() -> Generator[Path, None, None]:
    with __import__("tempfile").TemporaryDirectory() as d:
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
