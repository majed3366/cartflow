# -*- coding: utf-8 -*-
"""Public marketing pages and legacy redirects."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, RedirectResponse

router = APIRouter(tags=["public"])


@router.get("/")
def home(request: Request):
    """الصفحة العامة — واجهة تسويق CartFlow (عربي، RTL مع تخطيط مطابق للمرجع)."""
    from main import templates  # lazy — avoid circular import at module load

    return templates.TemplateResponse(
        request,
        "cartflow_landing.html",
        {"request": request},
    )


@router.get("/register")
def register_placeholder(request: Request):
    """إعادة توجيه — التسجيل الفعلي عند ‎/signup‎."""
    return RedirectResponse(url="/signup", status_code=302)


class LandingEventIn(BaseModel):
    event: str = Field(..., min_length=1, max_length=64)
    section: Optional[str] = Field(default=None, max_length=64)
    device: Optional[str] = Field(default=None, max_length=16)
    session_key: Optional[str] = Field(default=None, max_length=64)


@router.post("/api/landing/event")
async def landing_event(request: Request) -> JSONResponse:
    """Anonymous landing behavioural beacon — Reality Validation V1. No PII."""
    from services.landing_telemetry_v1 import record_landing_event

    payload: dict[str, Any] = {}
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)

    if not isinstance(payload, dict):
        return JSONResponse({"ok": False, "error": "invalid_body"}, status_code=400)

    try:
        body = LandingEventIn(
            event=str(payload.get("event") or ""),
            section=payload.get("section"),
            device=payload.get("device"),
            session_key=payload.get("session_key"),
        )
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid_fields"}, status_code=400)

    result = record_landing_event(
        event=body.event,
        section=body.section,
        device=body.device,
        session_key=body.session_key,
    )
    status = 200 if result.get("ok") else 400
    return JSONResponse(result, status_code=status)


@router.get("/api/landing/summary")
def landing_summary(
    hours: int = 168,
    x_cartflow_admin: Optional[str] = Header(default=None, alias="X-CartFlow-Admin"),
) -> JSONResponse:
    """Aggregate counters for Reality Validation reports (admin password required)."""
    from services.cartflow_admin_http_auth import (
        admin_password_configured,
        verify_admin_password,
    )
    from services.landing_telemetry_v1 import summarize_landing_telemetry

    if not admin_password_configured():
        return JSONResponse(
            {"ok": False, "error": "admin_not_configured"},
            status_code=503,
        )
    if not verify_admin_password(x_cartflow_admin or ""):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)

    return JSONResponse(summarize_landing_telemetry(hours=hours))
