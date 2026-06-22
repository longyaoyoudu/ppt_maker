"""FastAPI application entry point. Wires all HTTP routes."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config_store import ConfigNotFound, ConfigStore
from app.db import default_db_path
from app.errors import map_config_missing, map_llm_error, map_outline_parse
from app.history_store import Generation, HistoryStore
from app.llm.base import LLMError
from app.llm.factory import build_provider
from app.models import (
    ModelConfig,
    Outline,
    OutlineGenerateRequest,
    OutlineGenerateResponse,
    PPTRequest,
)
from app.services.outline_service import OutlineParseError, OutlineService
from app.services.pdf_service import LibreOfficeNotFound, PDFService
from app.services.ppt_service import PPTService

app = FastAPI(title="PPT Maker", version="0.1.0")


# --- helpers ----------------------------------------------------------------

def _outputs_dir() -> Path:
    p = Path(os.environ.get("PPTM_OUTPUTS_DIR", "outputs"))
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
    if stage not in ("outline", "ppt"):
        raise HTTPException(status_code=400, detail="stage must be 'outline' or 'ppt'")
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
    _config_store().save(cfg)
    return {"ok": True}


# outline
@app.post("/api/outline/generate", response_model=OutlineGenerateResponse)
def generate_outline(body: OutlineGenerateRequest):
    provider = _require_provider("outline")
    service = OutlineService(provider)
    try:
        outline = service.generate(topic=body.topic, requirements=body.requirements, style_hint=body.style_hint)
    except OutlineParseError as e:
        raise map_outline_parse(e)
    except LLMError as e:
        raise map_llm_error(e)
    outline_id = _history_store().save_outline(outline, requirements=body.requirements)
    return OutlineGenerateResponse(outline_id=outline_id, content=outline)


@app.put("/api/outline/{outline_id}")
def update_outline(outline_id: int, body: UpdateOutlineRequest):
    if _history_store().get_outline(outline_id) is None:
        raise HTTPException(status_code=404, detail="outline not found")
    _history_store().update_outline(outline_id, body.content)
    return {"ok": True}


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
    service = PPTService()
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


# static (frontend in PR 7)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
