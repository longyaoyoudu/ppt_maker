"""FastAPI application entry point. Wires all HTTP routes."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config_store import ConfigNotFound, ConfigStore
from app.db import default_db_path
from app.errors import (
    map_config_missing,
    map_document_parse,
    map_llm_error,
    map_outline_parse,
)
from app.history_store import Generation, HistoryStore
from app.llm.base import LLMError
from app.llm.factory import build_provider
from app.models import (
    ModelConfig,
    Outline,
    OutlineGenerateResponse,
    PPTRequest,
    SourceFile,
)
from app.services.document_parser import (
    MAX_BYTES_PER_FILE,
    SUPPORTED_EXTENSIONS,
    DocumentParseError,
    parse_document,
    safe_filename,
)
from app.services.image_providers import build_image_provider
from app.services.image_service import ImageService
from app.services.outline_service import OutlineParseError, OutlineService
from app.services.pdf_service import LibreOfficeNotFound, PDFService
from app.services.ppt_service import PPTService

app = FastAPI(title="PPT Maker", version="0.1.0")


# --- helpers ----------------------------------------------------------------

def _outputs_dir() -> Path:
    p = Path(os.environ.get("PPTM_OUTPUTS_DIR", "outputs"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _uploads_dir() -> Path:
    p = _outputs_dir() / "uploads"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _config_store() -> ConfigStore:
    return ConfigStore(db_path=default_db_path())


def _history_store() -> HistoryStore:
    return HistoryStore(db_path=default_db_path())


def _require_provider(stage: str) -> Any:
    try:
        cfg = _config_store().get(stage)
    except ConfigNotFound as e:
        raise map_config_missing(e)
    return build_provider({
        "provider": cfg.provider,
        "api_key": cfg.api_key,
        "model_name": cfg.model_name,
        "base_url": cfg.base_url,
    })


def _build_image_service() -> ImageService | None:
    """Build an ImageService backed by the user-configured image model.

    Returns None when no image model is configured (so PPTService falls
    back to placeholder/none modes). Returns an ImageService with no
    provider if configuration is invalid (AI mode will then raise).
    """
    try:
        cfg = _config_store().get("image")
    except ConfigNotFound:
        return None
    try:
        provider = build_image_provider({
            "provider": cfg.provider,
            "api_key": cfg.api_key,
            "model_name": cfg.model_name,
            "base_url": cfg.base_url,
        })
    except ValueError:
        return None
    return ImageService(image_provider=provider)


# --- request/response models local to the API ------------------------------

class PutConfigRequest(BaseModel):
    stage: str
    provider: str
    api_key: str
    model_name: str
    base_url: str | None = None
    extra_params: dict | None = None


class UpdateOutlineRequest(BaseModel):
    content: Outline


# --- routes ----------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# config
@app.get("/api/config/{stage}")
def get_config(stage: str):
    if stage not in ("outline", "ppt", "image"):
        raise HTTPException(status_code=400, detail="stage must be 'outline', 'ppt', or 'image'")
    store = _config_store()
    try:
        cfg = store.get(stage)
    except ConfigNotFound as e:
        raise map_config_missing(e)
    return cfg.model_dump()


@app.put("/api/config/{stage}")
def put_config(stage: str, body: PutConfigRequest):
    if stage != body.stage:
        raise HTTPException(status_code=400, detail="stage in URL and body must match")
    cfg = ModelConfig(**body.model_dump())
    # Image stage: try to instantiate the provider now so URL / API-key errors
    # are reported at save time (400) instead of crashing later in /api/ppt/generate.
    if stage == "image":
        try:
            build_image_provider({
                "provider": cfg.provider,
                "api_key": cfg.api_key,
                "model_name": cfg.model_name,
                "base_url": cfg.base_url,
            })
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"配图模型配置无效：{e}")
    _config_store().save(cfg)
    return {"ok": True}


# outline
@app.post("/api/outline/generate", response_model=OutlineGenerateResponse)
async def generate_outline(
    topic: str = Form(...),
    requirements: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
):
    if not topic.strip():
        raise HTTPException(status_code=400, detail="topic is required")

    import shutil
    import tempfile

    saved_files: list[tuple[UploadFile, Path]] = []
    tmp_ctx = tempfile.TemporaryDirectory(prefix="pptm_upload_") if files else None

    try:
        if tmp_ctx is not None:
            tmp_dir = Path(tmp_ctx.name)
            for f in files:
                ext = Path(f.filename or "").suffix.lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported file type: {f.filename} "
                               f"(allowed: {sorted(SUPPORTED_EXTENSIONS)})",
                    )
                safe = safe_filename(f.filename or "upload.bin")
                target = tmp_dir / safe
                i = 1
                while target.exists():
                    stem = Path(safe).stem
                    suffix = Path(safe).suffix
                    target = tmp_dir / f"{stem}_{i}{suffix}"
                    i += 1
                content = await f.read()
                if len(content) > MAX_BYTES_PER_FILE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large: {f.filename} exceeds "
                               f"{MAX_BYTES_PER_FILE // (1024 * 1024)} MB",
                    )
                target.write_bytes(content)
                saved_files.append((f, target))

        # Parse documents (after all files are saved so we get clear per-file errors)
        document_chunks: list[str] = []
        source_files: list[SourceFile] = []
        for orig, saved in saved_files:
            try:
                text = parse_document(saved)
            except DocumentParseError as e:
                raise map_document_parse(e)
            document_chunks.append(f"=== {orig.filename} ===\n{text}")
            source_files.append(
                SourceFile(
                    filename=orig.filename or saved.name,
                    stored_path="",  # filled in after save_outline
                    char_count=len(text),
                    mime_type=orig.content_type,
                )
            )
        document_text = "\n\n".join(document_chunks) if document_chunks else None

        provider = _require_provider("outline")
        service = OutlineService(provider)
        try:
            outline = service.generate(
                topic=topic,
                requirements=requirements,
                style_hint=None,
                document_text=document_text,
            )
        except OutlineParseError as e:
            raise map_outline_parse(e)
        except LLMError as e:
            raise map_llm_error(e)

        outline_id = _history_store().save_outline(
            outline, requirements=requirements, source_files=source_files
        )

        if saved_files:
            final_dir = _uploads_dir() / str(outline_id)
            final_dir.mkdir(parents=True, exist_ok=True)
            for idx, (orig, saved) in enumerate(saved_files):
                safe = safe_filename(orig.filename or saved.name)
                target = final_dir / safe
                j = 1
                while target.exists():
                    stem = Path(safe).stem
                    suffix = Path(safe).suffix
                    target = final_dir / f"{stem}_{j}{suffix}"
                    j += 1
                shutil.move(str(saved), str(target))
                source_files[idx].stored_path = str(target)
            _history_store().update_source_files(outline_id, source_files)

        return OutlineGenerateResponse(
            outline_id=outline_id, content=outline, source_files=source_files
        )
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


@app.put("/api/outline/{outline_id}")
def update_outline(outline_id: int, body: UpdateOutlineRequest):
    if _history_store().get_outline(outline_id) is None:
        raise HTTPException(status_code=404, detail="outline not found")
    _history_store().update_outline(outline_id, body.content)
    return {"ok": True}


@app.get("/api/outline/{outline_id}/source/{filename}")
def download_source(outline_id: int, filename: str):
    """Serve an originally-uploaded source file for an outline."""
    row = _history_store().get_outline(outline_id)
    if row is None:
        raise HTTPException(status_code=404, detail="outline not found")
    safe = safe_filename(filename)
    match = next(
        (sf for sf in row.source_files if sf.filename == filename or Path(sf.stored_path).name == safe),
        None,
    )
    if match is None:
        raise HTTPException(status_code=404, detail="source file not found")
    path = Path(match.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="source file missing on disk")
    media_type = match.mime_type or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


# ppt
@app.post("/api/ppt/generate")
def generate_ppt(body: PPTRequest):
    row = _history_store().get_outline(body.outline_id)
    if row is None:
        raise HTTPException(status_code=404, detail="outline not found")
    outputs = _outputs_dir()
    stamp = int(time.time() * 1000)
    pptx_path = outputs / f"ppt_{body.outline_id}_{body.style}_{stamp}.pptx"
    images_dir = outputs / f"img_{body.outline_id}_{stamp}"
    image_service = _build_image_service()
    service = PPTService(image_service=image_service)
    service.build(
        outline=row.content, style=body.style, image_mode=body.image_mode,
        out_path=pptx_path, images_dir=images_dir,
    )
    pdf_path: Path | None = None
    pdf_error: str | None = None
    try:
        pdf_path = PDFService().convert(pptx_path=pptx_path, out_dir=outputs)
    except LibreOfficeNotFound as e:
        pdf_error = f"LibreOffice 未安装：{e}"
    except Exception as e:
        pdf_error = f"PDF 转换失败：{e}"
    gen = Generation(
        outline_id=body.outline_id, style=body.style, image_mode=body.image_mode,
        pptx_path=str(pptx_path), pdf_path=str(pdf_path) if pdf_path else None,
    )
    gid = _history_store().save_generation(gen)
    return {
        "generation_id": gid,
        "pptx_path": str(pptx_path),
        "pdf_path": str(pdf_path) if pdf_path else None,
        "pdf_error": pdf_error,
    }


# history
@app.get("/api/history/outlines")
def list_outlines():
    return [
        {
            "id": r.id,
            "topic": r.topic,
            "requirements": r.requirements,
            "created_at": r.created_at,
            "content": r.content.model_dump(),
            "source_files": [sf.model_dump() for sf in r.source_files],
        }
        for r in _history_store().list_outlines()
    ]


@app.get("/api/history/generations")
def list_generations():
    return [g.__dict__ for g in _history_store().list_generations()]


# download
@app.get("/api/download/{generation_id}/{fmt}")
def download(generation_id: int, fmt: str):
    if fmt not in ("pptx", "pdf"):
        raise HTTPException(status_code=400, detail="format must be 'pptx' or 'pdf'")
    gen = _history_store().get_generation(generation_id)
    if gen is None:
        raise HTTPException(status_code=404, detail="generation not found")
    path = gen.pptx_path if fmt == "pptx" else gen.pdf_path
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail=f"{fmt} not available for this generation")
    media_type = (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        if fmt == "pptx"
        else "application/pdf"
    )
    return FileResponse(path, media_type=media_type, filename=Path(path).name)


# static (frontend)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")