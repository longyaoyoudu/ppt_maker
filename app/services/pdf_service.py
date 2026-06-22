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
        self._binary = binary  # resolved lazily in convert() if None
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
        binary = self._binary or self._find_binary()
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            binary, "--headless", "--convert-to", "pdf",
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
