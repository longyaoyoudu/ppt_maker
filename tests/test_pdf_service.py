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
        assert "soffice" in cmd[0] or "libreoffice" in cmd[0]
        out_dir = Path(cmd[cmd.index("--outdir") + 1])
        (out_dir / "x.pdf").write_bytes(b"%PDF-1.4 fake")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    service = PDFService(binary="/usr/bin/soffice")
    out = service.convert(pptx_path=pptx, out_dir=tmp_dir)
    assert out == pdf
    assert out.exists()


def test_convert_raises_when_libreoffice_missing(tmp_dir, monkeypatch):
    pptx = tmp_dir / "x.pptx"
    pptx.write_bytes(b"x")

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ARG001
        raise FileNotFoundError("soffice")

    monkeypatch.setattr(subprocess, "run", fake_run)
    service = PDFService(binary="/usr/bin/soffice")
    with pytest.raises(LibreOfficeNotFound):
        service.convert(pptx_path=pptx, out_dir=tmp_dir)


def test_convert_returns_none_on_nonzero(tmp_dir, monkeypatch):
    pptx = tmp_dir / "x.pptx"
    pptx.write_bytes(b"x")

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ARG001
        return subprocess.CompletedProcess(cmd, 1, "boom", "err")

    monkeypatch.setattr(subprocess, "run", fake_run)
    service = PDFService(binary="/usr/bin/soffice")
    with pytest.raises(RuntimeError):
        service.convert(pptx_path=pptx, out_dir=tmp_dir)


def test_construct_without_binary_does_not_resolve(tmp_dir):
    """Constructor must not eagerly look up soffice on PATH; that happens in convert()."""
    service = PDFService()
    assert service._binary is None
