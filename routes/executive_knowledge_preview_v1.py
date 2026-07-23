# -*- coding: utf-8 -*-
"""
Executive Knowledge Preview routes — WP-ET-10.5 validation surface.

Flag-gated (CARTFLOW_EXECUTIVE_KNOWLEDGE_PREVIEW default OFF).
READ ONLY. Not Home. Not production merchant experience.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse

from services.evidence_truth.executive_knowledge_preview_v1 import (
    FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW,
    build_executive_knowledge_preview_v1,
    executive_knowledge_preview_enabled,
)

router = APIRouter(tags=["executive-knowledge-preview"])

_ROOT = Path(__file__).resolve().parents[1]
_PAGE = (_ROOT / "static" / "executive_knowledge_preview_v1.html").resolve()


def _flag_off_response() -> JSONResponse:
    return JSONResponse(
        {
            "ok": False,
            "reason": "flag_off",
            "flag": FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW,
            "flag_enabled": False,
            "preview": True,
            "production_home": False,
            "message": (
                "Executive Knowledge Preview is disabled "
                f"({FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW} default OFF)."
            ),
        },
        status_code=404,
        headers={"X-CartFlow-Preview": "executive-knowledge-v1-disabled"},
    )


@router.get("/preview/executive-knowledge")
@router.get("/preview/executive-knowledge/")
def executive_knowledge_preview_page() -> Any:
    """HTML validation surface. 404 when flag OFF."""
    if not executive_knowledge_preview_enabled():
        return _flag_off_response()
    if not _PAGE.is_file():
        return JSONResponse(
            {"ok": False, "reason": "preview_page_missing"},
            status_code=500,
        )
    return FileResponse(
        _PAGE,
        media_type="text/html; charset=utf-8",
        headers={
            "X-CartFlow-Preview": "executive-knowledge-v1",
            "X-CartFlow-Production-Home": "false",
            "Cache-Control": "no-store",
        },
    )


@router.get("/preview/executive-knowledge/api")
def executive_knowledge_preview_api(
    store_slug: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> JSONResponse:
    """
    JSON preview payload from Shadow Knowledge only.

    404 when flag OFF (production-unchanged posture).
    """
    if not executive_knowledge_preview_enabled():
        return _flag_off_response()
    payload = build_executive_knowledge_preview_v1(
        store_slug=(store_slug or "").strip(),
        limit=int(limit),
    )
    return JSONResponse(
        payload,
        headers={
            "X-CartFlow-Preview": "executive-knowledge-v1",
            "X-CartFlow-Production-Home": "false",
            "Cache-Control": "no-store",
        },
    )
