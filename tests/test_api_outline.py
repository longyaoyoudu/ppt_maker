"""Tests for the outline API endpoint (LLM is mocked)."""
import json

import pytest
from fastapi.testclient import TestClient

from app.config_store import ConfigStore
from app.db import init_db
from app.main import app
from app.models import ModelConfig


@pytest.fixture
def client_with_outline_config(tmp_path, monkeypatch):
    db = tmp_path / "app.db"
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
    from app import main

    class StubProvider:
        def chat(self, system, user, *, temperature=0.7, max_tokens=2048):
            return json.dumps({
                "pages": [{"title": "P1", "key_points": ["a"], "layout": "title-content"}]
            })

    monkeypatch.setattr(main, "build_provider", lambda cfg: StubProvider())
    r = client_with_outline_config.post("/api/outline/generate", json={"topic": "AI"})
    assert r.status_code == 200
    data = r.json()
    assert data["outline_id"] >= 1
    assert data["content"]["topic"] == "AI"
    assert data["content"]["pages"][0]["title"] == "P1"
