"""Shared error-handling utilities for the API layer."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.config_store import ConfigNotFound
from app.llm.base import LLMError
from app.services.document_parser import DocumentParseError
from app.services.outline_service import OutlineParseError


def map_llm_error(e: LLMError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


def map_config_missing(e: ConfigNotFound) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"请先在'模型配置'中配置 {e.args[0] if e.args else '对应'} 模型",
    )


def map_outline_parse(e: OutlineParseError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def map_document_parse(e: DocumentParseError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
