"""Document text extraction for uploaded source files (PDF / DOCX).

Reads user-uploaded PDFs and Word documents, extracts plain text, and
returns it for inclusion in the outline prompt. Enforces a size cap and
a per-file character cap so a single large upload cannot blow past LLM
context limits.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx"})

MAX_BYTES_PER_FILE: int = 20 * 1024 * 1024  # 20 MB
MAX_CHARS_PER_FILE: int = 30_000

_TRUNCATION_MARKER = "\n[... truncated ...]"


class DocumentParseError(ValueError):
    """Raised when a document cannot be parsed (missing, too large, corrupt,
    or unsupported extension)."""


_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._\-]")


def safe_filename(name: str) -> str:
    """Return a basename-only, ASCII-safe filename suitable for writing to disk.

    Strips any path components, replaces any character outside [A-Za-z0-9._-]
    with an underscore, and trims leading dots.
    """
    base = name.replace("\\", "/").split("/")[-1] or "upload"
    safe = _FILENAME_SAFE_RE.sub("_", base)
    safe = safe.lstrip(".") or "upload"
    return safe


def _assert_within_size(path: Path) -> None:
    if not path.exists():
        raise DocumentParseError(f"File not found: {path.name}")
    size = path.stat().st_size
    if size > MAX_BYTES_PER_FILE:
        mb = MAX_BYTES_PER_FILE / (1024 * 1024)
        raise DocumentParseError(
            f"File too large: {path.name} is {size} bytes; max is {mb:.0f} MB"
        )


def _truncate(text: str) -> str:
    if len(text) <= MAX_CHARS_PER_FILE:
        return text
    return text[:MAX_CHARS_PER_FILE] + _TRUNCATION_MARKER


def _extract_pdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        raise DocumentParseError(f"Failed to read PDF {path.name}: {e}") from e
    try:
        chunks = [(page.extract_text() or "") for page in reader.pages]
    except Exception as e:
        raise DocumentParseError(f"Failed to extract PDF text from {path.name}: {e}") from e
    return "\n".join(chunks).strip()


def _extract_docx(path: Path) -> str:
    try:
        doc = DocxDocument(str(path))
    except Exception as e:
        raise DocumentParseError(f"Failed to read DOCX {path.name}: {e}") from e
    try:
        chunks = [p.text for p in doc.paragraphs]
    except Exception as e:
        raise DocumentParseError(f"Failed to extract DOCX text from {path.name}: {e}") from e
    return "\n".join(chunks).strip()


def parse_document(path: Path) -> str:
    """Extract plain text from a PDF or DOCX file.

    Raises DocumentParseError on missing/unsupported/oversize/corrupt input.
    Truncates extracted text to MAX_CHARS_PER_FILE characters.
    """
    _assert_within_size(path)
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DocumentParseError(
            f"Unsupported file type: {path.name} (allowed: {sorted(SUPPORTED_EXTENSIONS)})"
        )
    if ext == ".pdf":
        text = _extract_pdf(path)
    else:
        text = _extract_docx(path)
    return _truncate(text)