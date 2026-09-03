# -*- coding: utf-8 -*-
"""
Commercial Intelligence Preview V1 — founder-only flag-gated route.

GET /preview/commercial-intelligence  → 404 when flag OFF (default)
GET /preview/commercial-intelligence  → preview page when flag ON
GET /preview/commercial-intelligence/api → JSON payload (flag gated)

Server-side gate: CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW env var.
Simulation truth only — never production merchant data.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import Response

from services.commercial_intelligence_preview_v1 import (
    FLAG,
    SIMULATION_TRUTH_LABEL,
    build_preview_payload_v1,
    commercial_intelligence_preview_enabled,
    verify_no_production_truth_leak,
)
from services.merchant_setup_render_build import MERCHANT_SETUP_RENDER_BUILD

router = APIRouter(tags=["commercial-intelligence-preview"])

_TEMPLATES = Jinja2Templates(directory="templates")

_PREVIEW_HEADER = "commercial-intelligence-v1"
_FLAG_OFF_BODY: dict[str, Any] = {
    "ok": False,
    "reason": "flag_off",
    "flag": FLAG,
    "flag_enabled": False,
    "preview": True,
    "simulation_only": True,
    "production_home": False,
    "message": (
        f"Commercial Intelligence Preview is disabled ({FLAG} default OFF). "
        "Set the env var to '1' in Railway environment (API service only) for founder preview."
    ),
}


def _flag_off() -> JSONResponse:
    return JSONResponse(
        _FLAG_OFF_BODY,
        status_code=404,
        headers={
            "X-CartFlow-Preview": _PREVIEW_HEADER + "-disabled",
            "Cache-Control": "no-store",
        },
    )


@router.get("/preview/commercial-intelligence")
@router.get("/preview/commercial-intelligence/")
def commercial_intelligence_preview_page(request: Request) -> Response:
    """
    Founder-only Commercial Intelligence Preview.

    Returns 404 when CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW is OFF.
    Simulation truth only — production Merchant UI shell — no real merchant data.
    """
    if not commercial_intelligence_preview_enabled():
        return _flag_off()
    payload = build_preview_payload_v1()
    violations = verify_no_production_truth_leak(payload)
    if violations:
        return JSONResponse(
            {
                "ok": False,
                "reason": "truth_boundary_violation",
                "violations": violations,
            },
            status_code=500,
        )
    build = MERCHANT_SETUP_RENDER_BUILD + "-cip1"
    return _TEMPLATES.TemplateResponse(
        request,
        "commercial_intelligence_preview_v1.html",
        {
            "request": request,
            "payload": payload,
            "build": build,
            "merchant_setup_render_build": build,
        },
        headers={
            "X-CartFlow-Preview": _PREVIEW_HEADER,
            "X-CartFlow-Truth-Source": SIMULATION_TRUTH_LABEL,
            "X-CartFlow-Production-Home": "false",
            "Cache-Control": "no-store",
        },
    )


@router.get("/preview/commercial-intelligence/api")
def commercial_intelligence_preview_api() -> JSONResponse:
    """
    JSON payload for founder inspection.
    404 when flag OFF.
    """
    if not commercial_intelligence_preview_enabled():
        return _flag_off()
    payload = build_preview_payload_v1()
    violations = verify_no_production_truth_leak(payload)
    if violations:
        return JSONResponse(
            {"ok": False, "reason": "truth_boundary_violation", "violations": violations},
            status_code=500,
        )
    return JSONResponse(
        payload,
        headers={
            "X-CartFlow-Preview": _PREVIEW_HEADER,
            "X-CartFlow-Truth-Source": SIMULATION_TRUTH_LABEL,
            "Cache-Control": "no-store",
        },
    )
