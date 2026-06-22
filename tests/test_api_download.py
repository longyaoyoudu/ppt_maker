"""Tests for the download endpoint."""
import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.history_store import Generation, HistoryStore
from app.main import app
from app.models import Outline, OutlinePage


@pytest.fixture
def client_with_gen(tmp_path, monkeypatch):
    db = tmp_path / "app.db"
    init_db(db)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    pptx = outputs / "a.pptx"
    pptx.write_bytes(b"fake pptx")
    pdf = outputs / "a.pdf"
    pdf.write_bytes(b"%PDF fake")
    monkeypatch.setenv("PPTM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PPTM_OUTPUTS_DIR", str(outputs))
    store = HistoryStore(db_path=db)
    outline = Outline(
        topic="T",
        pages=[OutlinePage(title="P1", key_points=["a"], layout="title-content")],
    )
    oid = store.save_outline(outline, requirements=None)
    gid = store.save_generation(
        Generation(
            outline_id=oid,
            style="business",
            image_mode="none",
            pptx_path=str(pptx),
            pdf_path=str(pdf),
        )
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
