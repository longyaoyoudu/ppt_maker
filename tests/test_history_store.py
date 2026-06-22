"""Tests for the outline and generation history store."""
import pytest

from app.history_store import HistoryStore, Generation
from app.models import Outline, OutlinePage, SourceFile


def test_save_and_get_outline(tmp_dir):
    store = HistoryStore(db_path=tmp_dir / "test.db")
    outline = Outline(topic="T", pages=[OutlinePage(title="P1", key_points=["a"], layout="title-content")])
    oid = store.save_outline(outline, requirements="extra info")
    loaded = store.get_outline(oid)
    assert loaded is not None
    assert loaded.topic == "T"
    assert loaded.content.pages[0].title == "P1"
    assert loaded.source_files == []  # default empty


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
    assert loaded.content.pages[0].title == "P1-updated"


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


def test_save_outline_with_source_files_roundtrip(tmp_dir):
    store = HistoryStore(db_path=tmp_dir / "test.db")
    outline = Outline(topic="T", pages=[OutlinePage(title="P", layout="title-content")])
    files = [
        SourceFile(filename="a.pdf", stored_path="outputs/uploads/1/a.pdf", char_count=1200, mime_type="application/pdf"),
        SourceFile(filename="b.docx", stored_path="outputs/uploads/1/b.docx", char_count=800, mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ]
    oid = store.save_outline(outline, requirements=None, source_files=files)
    loaded = store.get_outline(oid)
    assert loaded is not None
    assert len(loaded.source_files) == 2
    assert loaded.source_files[0].filename == "a.pdf"
    assert loaded.source_files[1].char_count == 800
    # Roundtrip via list_outlines too
    listed = store.list_outlines()
    assert listed[0].source_files[0].stored_path == "outputs/uploads/1/a.pdf"
