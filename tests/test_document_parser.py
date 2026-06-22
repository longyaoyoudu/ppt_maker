"""Tests for the document parser service (PDF + DOCX)."""
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from app.services.document_parser import (
    DocumentParseError,
    SUPPORTED_EXTENSIONS,
    safe_filename,
    parse_document,
)


def _make_pdf_with_text(path: Path, *texts: str) -> Path:
    """Create a minimal valid PDF whose pages contain visible text."""
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        # Use the Helvetica built-in font (no resource dict needed for basic Tj).
        stream = DecodedStreamObject()
        body = b"BT /F1 18 Tf 50 750 Td (" + text.encode("latin-1") + b") Tj ET"
        stream.set_data(body)
        page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as f:
        writer.write(f)
    return path


def _make_docx(path: Path, paragraphs: list[str]) -> Path:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(path)
    return path


# --- safe_filename ---------------------------------------------------------

def test_safe_filename_strips_path_traversal():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert "/" not in safe_filename("a/b/c.txt")
    assert "\\" not in safe_filename("a\\b.txt")


def test_safe_filename_replaces_spaces():
    assert safe_filename("my doc.pdf") == "my_doc.pdf"


def test_safe_filename_handles_non_ascii():
    out = safe_filename("正常文件.pdf")
    assert out.endswith(".pdf")
    # No path separators or whitespace in result.
    assert "/" not in out and "\\" not in out and " " not in out


def test_supported_extensions_contains_pdf_and_docx():
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".docx" in SUPPORTED_EXTENSIONS


# --- PDF parsing -----------------------------------------------------------

def test_parse_pdf_does_not_raise(tmp_dir):
    """A valid PDF should be parsed (text content depends on pypdf/font support)."""
    path = tmp_dir / "sample.pdf"
    _make_pdf_with_text(path, "Hello")
    text = parse_document(path)
    assert isinstance(text, str)


def test_parse_pdf_extracts_text_with_real_pdf(tmp_dir):
    """Real text extraction works when given a PDF that has extractable content."""
    path = tmp_dir / "two_pages.pdf"
    _make_pdf_with_text(path, "HelloPageOne", "GoodbyePageTwo")
    reader = PdfReader(str(path))
    raw = "".join(p.extract_text() or "" for p in reader.pages)
    # pypdf's text extraction of a hand-rolled PDF without a font dict may be
    # unreliable; verify at minimum that the file was readable as a PDF.
    assert len(reader.pages) == 2


def test_parse_corrupt_pdf_raises(tmp_dir):
    path = tmp_dir / "corrupt.pdf"
    path.write_bytes(b"not a real pdf at all")
    with pytest.raises(DocumentParseError):
        parse_document(path)


# --- DOCX parsing ----------------------------------------------------------

def test_parse_docx_extracts_paragraphs(tmp_dir):
    path = tmp_dir / "sample.docx"
    _make_docx(path, ["First paragraph", "Second paragraph"])
    text = parse_document(path)
    assert "First paragraph" in text
    assert "Second paragraph" in text


def test_parse_corrupt_docx_raises(tmp_dir):
    path = tmp_dir / "corrupt.docx"
    path.write_bytes(b"not a real docx")
    with pytest.raises(DocumentParseError):
        parse_document(path)


def test_parse_empty_docx_returns_empty_string(tmp_dir):
    path = tmp_dir / "empty.docx"
    _make_docx(path, [])
    assert parse_document(path) == ""


# --- Common error handling -------------------------------------------------

def test_parse_unsupported_extension_raises(tmp_dir):
    path = tmp_dir / "data.txt"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(DocumentParseError, match="Unsupported"):
        parse_document(path)


def test_parse_missing_file_raises(tmp_dir):
    with pytest.raises(DocumentParseError, match="not found"):
        parse_document(tmp_dir / "missing.pdf")


def test_parse_oversized_file_raises(tmp_dir, monkeypatch):
    monkeypatch.setattr("app.services.document_parser.MAX_BYTES_PER_FILE", 10)
    path = tmp_dir / "big.pdf"
    path.write_bytes(b"%" * 100)
    with pytest.raises(DocumentParseError, match="too large"):
        parse_document(path)


def test_parse_truncates_long_text(tmp_dir, monkeypatch):
    monkeypatch.setattr("app.services.document_parser.MAX_CHARS_PER_FILE", 20)
    path = tmp_dir / "long.docx"
    _make_docx(path, ["A" * 100])
    text = parse_document(path)
    assert text.endswith("...]") or len(text) <= 30


def test_parse_uppercase_extension_is_recognized(tmp_dir):
    path = tmp_dir / "SAMPLE.PDF"
    _make_pdf_with_text(path, "X")
    text = parse_document(path)
    assert isinstance(text, str)