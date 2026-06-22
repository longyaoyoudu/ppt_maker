"""Tests for the image model config + AI image generation in PPT pipeline."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config_store import ConfigStore
from app.db import init_db
from app.history_store import HistoryStore
from app.main import app
from app.models import ModelConfig, Outline, OutlinePage


@pytest.fixture
def client_with_image_config(tmp_path, monkeypatch):
    db = tmp_path / "app.db"
    init_db(db)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(outputs))
    store = HistoryStore(db_path=db)
    outline = Outline(
        topic="T",
        pages=[OutlinePage(title="P1", key_points=["a"], layout="title-content")],
    )
    oid = store.save_outline(outline, requirements=None)
    ConfigStore(db_path=db).save(
        ModelConfig(stage="image", provider="minimax", api_key="k", model_name="image-01")
    )
    with TestClient(app) as c:
        yield c, oid, tmp_path


def test_get_image_config_returns_200(client_with_image_config):
    c, _, _ = client_with_image_config
    r = c.get("/api/config/image")
    assert r.status_code == 200
    data = r.json()
    assert data["stage"] == "image"
    assert data["provider"] == "minimax"
    assert data["model_name"] == "image-01"


def test_put_image_config_returns_ok(client_with_image_config):
    c, _, _ = client_with_image_config
    r = c.put("/api/config/image", json={
        "stage": "image",
        "provider": "openai",
        "api_key": "k2",
        "model_name": "dall-e-3",
        "base_url": None,
    })
    assert r.status_code == 200
    again = c.get("/api/config/image").json()
    assert again["model_name"] == "dall-e-3"


def test_get_config_rejects_unknown_stage(client_with_image_config):
    c, _, _ = client_with_image_config
    r = c.get("/api/config/bogus")
    assert r.status_code == 400


def test_get_image_config_400_when_missing(tmp_path, monkeypatch):
    db = tmp_path / "app.db"
    init_db(db)
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(tmp_path / "outputs"))
    (tmp_path / "outputs").mkdir()
    with TestClient(app) as c:
        r = c.get("/api/config/image")
    assert r.status_code == 400


def test_generate_ppt_uses_ai_image_when_configured(tmp_path, monkeypatch):
    """When image model is configured and image_mode=ai, builder calls ai_generate."""
    from app import main as app_main
    from app.services import image_service as isvc

    db = tmp_path / "app.db"
    init_db(db)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(outputs))
    ConfigStore(db_path=db).save(
        ModelConfig(stage="image", provider="minimax", api_key="k", model_name="image-01")
    )
    oid = HistoryStore(db_path=db).save_outline(
        Outline(topic="T", pages=[OutlinePage(title="P1", key_points=["a"], layout="title-content")]),
        requirements=None,
    )

    from io import BytesIO

    from PIL import Image

    captured = {}

    def _png_bytes() -> bytes:
        buf = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
        return buf.getvalue()

    class FakeProvider:
        def generate_image(self, prompt, *, n=1, aspect_ratio=None):
            captured["prompt"] = prompt
            return [_png_bytes()]

    class StubImageService:
        def placeholder(self, **kw): return None
        def ai_generate(self, *, out_path, prompt, aspect_ratio=None):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(_png_bytes())
            captured["prompt"] = prompt
            return out_path

    monkeypatch.setattr(app_main, "PDFService", lambda: _FakePDF())
    monkeypatch.setattr(app_main, "_build_image_service", lambda: StubImageService())

    with TestClient(app) as c:
        r = c.post("/api/ppt/generate", json={"outline_id": oid, "style": "business", "image_mode": "ai"})
    assert r.status_code == 200
    # Verify the AI prompt referenced the slide title
    assert "P1" in captured["prompt"]
    assert "T" in captured["prompt"]


def test_generate_ppt_works_without_image_config(tmp_path, monkeypatch):
    """When no image model configured and image_mode=ai, builder silently falls back."""
    from app import main as app_main

    db = tmp_path / "app.db"
    init_db(db)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(outputs))
    oid = HistoryStore(db_path=db).save_outline(
        Outline(topic="T", pages=[OutlinePage(title="P1", key_points=["a"], layout="title-content")]),
        requirements=None,
    )

    monkeypatch.setattr(app_main, "PDFService", lambda: _FakePDF())
    monkeypatch.setattr(app_main, "_build_image_service", lambda: None)

    with TestClient(app) as c:
        r = c.post("/api/ppt/generate", json={"outline_id": oid, "style": "business", "image_mode": "ai"})
    assert r.status_code == 200


class _FakePDF:
    def convert(self, *, pptx_path, out_dir):
        target = out_dir / (pptx_path.stem + ".pdf")
        target.write_bytes(b"%PDF-1.4 fake")
        return target