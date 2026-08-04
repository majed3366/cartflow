# -*- coding: utf-8 -*-
"""Public checkout redirect — track click then 302 (fail-open)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from services.recovery_checkout_redirect_v1 import resolve_checkout_redirect_token
from services.recovery_click_tracking_v1 import record_checkout_button_click

router = APIRouter(tags=["meta-recovery-checkout-redirect"])


def _client_ip(request: Request) -> str:
    # Prefer first X-Forwarded-For hop when present (Railway / proxies)
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        return xff.split(",")[0].strip()[:64]
    if request.client and request.client.host:
        return str(request.client.host)[:64]
    return ""


def _safe_error_body(error_code: str) -> dict[str, Any]:
    return {"ok": False, "error": error_code}


@router.get("/wa/checkout/{token}")
def wa_checkout_redirect(token: str, request: Request):
    """
    Resolve token → record checkout_button_clicked → 302 to merchant checkout.

    Tracking failures never block redirect.
    Error responses never include destination_url.
    """
    resolved = resolve_checkout_redirect_token(token)
    if not resolved.ok or resolved.claims is None:
        return JSONResponse(
            status_code=400,
            content=_safe_error_body(resolved.error_code or "invalid_checkout_token"),
        )

    claims = resolved.claims
    try:
        record_checkout_button_click(
            claims=claims,
            redirect_token=token,
            user_agent=str(request.headers.get("user-agent") or "")[:500],
            ip_address=_client_ip(request),
            referer=str(request.headers.get("referer") or "")[:500],
            allow_duplicate=True,
        )
    except Exception:  # noqa: BLE001 — customer experience wins
        pass

    return RedirectResponse(url=claims.destination_url, status_code=302)


@router.get("/wa/checkout/")
def wa_checkout_missing_token():
    return JSONResponse(status_code=400, content=_safe_error_body("missing_token"))
