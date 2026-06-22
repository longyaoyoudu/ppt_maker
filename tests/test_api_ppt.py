"""Tests for the PPT generation endpoint (LibreOffice is mocked)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.history_store import HistoryStore
from app.main import app
from app.models import Outline, OutlinePage


@pytest.fixture
def client(tmp_path, monkeypatch):
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

    # Patch PDF conversion so we don't need LibreOffice.
    from app import main as app_main

    class StubPDF:
        def convert(self, *, pptx_path, out_dir):
            target = out_dir / (pptx_path.stem + ".pdf")
            target.write_bytes(b"%PDF-1.4 fake")
            return target

    monkeypatch.setattr(app_main, "PDFService", StubPDF)
    with TestClient(app) as c:
        yield c, oid


def test_generate_ppt_returns_download_links(client):
    c, oid = client
    r = c.post(
        "/api/ppt/generate",
        json={"outline_id": oid, "style": "business", "image_mode": "none"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["generation_id"] >= 1
    assert data["pptx_path"] is not None
    assert Path(data["pptx_path"]).exists()
    assert data["pdf_path"] is not None
    assert Path(data["pdf_path"]).exists()


def test_generate_ppt_404_for_missing_outline(client):
    c, _ = client
    r = c.post(
        "/api/ppt/generate",
        json={"outline_id": 9999, "style": "business", "image_mode": "none"},
    )
    assert r.status_code == 404
