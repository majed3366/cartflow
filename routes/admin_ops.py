# -*- coding: utf-8 -*-
"""Admin ops tools — load testing (auth required)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import Body, Request
from fastapi.responses import JSONResponse

from json_response import j
from services.cartflow_admin_http_auth import (
    admin_cookie_name,
    admin_password_configured,
    admin_session_cookie_valid,
)
from services.admin_cart_event_load_test import run_cart_event_load_test

from routes.admin_operations import router


def _admin_json_auth_or_error(request: Request) -> Optional[JSONResponse]:
    if not admin_password_configured():
        return JSONResponse(
            {"ok": False, "error": "admin_not_configured"},
            status_code=503,
        )
    cookie = request.cookies.get(admin_cookie_name())
    if not admin_session_cookie_valid(cookie):
        return JSONResponse(
            {"ok": False, "error": "unauthorized"},
            status_code=401,
        )
    return None


@router.post("/admin/ops/load-test/cart-event")
def admin_load_test_cart_event(
    request: Request,
    body: dict[str, Any] = Body(default_factory=dict),
) -> Any:
    """
    Safe sequential cart-event load test (admin session required).
    Does not send real WhatsApp when dry_run_whatsapp=true (default).
    """
    denied = _admin_json_auth_or_error(request)
    if denied is not None:
        return denied

    store_slug = str(body.get("store_slug") or "demo").strip() or "demo"
    events_count = body.get("events_count", 20)
    dry_run = body.get("dry_run_whatsapp", True)
    if isinstance(dry_run, str):
        dry_run = dry_run.strip().lower() in ("1", "true", "yes", "on")
    reason_tag = body.get("reason_tag")
    if reason_tag is not None:
        reason_tag = str(reason_tag).strip() or None
    phone_present = body.get("phone_present", True)
    if isinstance(phone_present, str):
        phone_present = phone_present.strip().lower() in ("1", "true", "yes", "on")

    summary = run_cart_event_load_test(
        store_slug=store_slug,
        events_count=int(events_count) if events_count is not None else 20,
        dry_run_whatsapp=bool(dry_run),
        reason_tag=reason_tag,
        phone_present=bool(phone_present),
    )
    return j(summary)
