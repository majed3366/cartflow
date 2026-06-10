# -*- coding: utf-8 -*-
"""Admin targeted operational control v1 — HTML + JSON (session auth)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from json_response import j
from services.operational_control_v1 import (
    CONTROL_PAUSE_CONTINUATION,
    CONTROL_PAUSE_PROVIDER,
    CONTROL_PAUSE_REASON,
    CONTROL_PAUSE_SCHEDULING,
    CONTROL_PAUSE_STORE,
    CONTROL_PAUSE_WA,
    apply_operational_control,
    build_operational_control_verification,
    get_operational_control_state,
    resume_operational_control,
)
from services.cartflow_admin_http_auth import (
    admin_cookie_name,
    admin_password_configured,
    admin_session_cookie_valid,
)

from routes.admin_operations import (
    ADMIN_NAV_OPS_CONTROL,
    _admin_session_or_redirect,
    router,
    templates,
)


def _admin_json_auth(request: Request) -> Optional[JSONResponse]:
    if not admin_password_configured():
        return JSONResponse({"ok": False, "error": "admin_not_configured"}, status_code=503)
    cookie = request.cookies.get(admin_cookie_name())
    if not admin_session_cookie_valid(cookie):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    return None


@router.get("/admin/control", response_class=HTMLResponse)
def admin_operational_control_page(request: Request) -> Any:
    denied = _admin_session_or_redirect(request, next_path="/admin/control")
    if denied is not None:
        return denied
    state = get_operational_control_state()
    verification = build_operational_control_verification()
    return templates.TemplateResponse(
        request,
        "admin_operational_control.html",
        {
            "admin_active_nav": ADMIN_NAV_OPS_CONTROL,
            "admin_page_title_ar": "التحكم التشغيلي",
            "admin_page_subtitle_ar": "إيقاف مكوّن محدّد دون إيقاف المنصة بالكامل — كل الخيارات معطّلة افتراضياً.",
            "control_state": state,
            "verification": verification,
            "controls": [
                ("pause_wa", "إيقاف إرسال واتساب", CONTROL_PAUSE_WA),
                ("pause_scheduling", "إيقاف جدولة استرجاع جديدة", CONTROL_PAUSE_SCHEDULING),
                ("pause_store", "إيقاف متجر", CONTROL_PAUSE_STORE),
                ("pause_reason", "إيقاف سبب", CONTROL_PAUSE_REASON),
                ("pause_continuation", "إيقاف المتابعة التلقائية", CONTROL_PAUSE_CONTINUATION),
                ("pause_provider", "إيقاف المزوّد", CONTROL_PAUSE_PROVIDER),
            ],
        },
    )


@router.get("/api/admin/operational-control/state")
def api_operational_control_state(request: Request) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    return j(get_operational_control_state())


@router.get("/api/admin/operational-control/verification")
def api_operational_control_verification(request: Request) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    return j(build_operational_control_verification())


@router.get("/api/admin/operational-health")
def api_admin_operational_health(request: Request, store_slug: str = "") -> Any:
    """Operational Truth Center — read-only JSON health composition."""
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_operational_health_json_v1 import build_admin_operational_health_json

    payload = build_admin_operational_health_json(
        store_slug=(store_slug or "").strip() or None,
    )
    status = 200 if payload.get("ok") else 503
    return JSONResponse(payload, status_code=status)


@router.post("/admin/control/apply")
def admin_operational_control_apply(
    request: Request,
    control: str = Form(...),
    enabled: str = Form("0"),
    operator: str = Form("admin"),
    reason: str = Form(""),
    duration: str = Form("until_resume"),
    dry_run: str = Form("0"),
    store_slug: str = Form(""),
    reason_tag: str = Form(""),
    provider: str = Form("twilio"),
) -> Any:
    denied = _admin_session_or_redirect(request, next_path="/admin/control")
    if denied is not None:
        return denied
    is_dry = (dry_run or "").strip().lower() in ("1", "true", "yes", "on")
    is_on = (enabled or "").strip().lower() in ("1", "true", "yes", "on")
    result = apply_operational_control(
        control=control,
        enabled=is_on,
        operator=operator,
        reason=reason,
        duration=duration,
        dry_run=is_dry,
        store_slug=store_slug or None,
        reason_tag=reason_tag or None,
        provider=provider or None,
    )
    if not result.get("ok"):
        return RedirectResponse(
            url=f"/admin/control?e={result.get('error', 'failed')}",
            status_code=303,
        )
    return RedirectResponse(url="/admin/control?applied=1", status_code=303)


@router.post("/admin/control/resume")
def admin_operational_control_resume(
    request: Request,
    target: str = Form("all"),
    operator: str = Form("admin"),
    reason: str = Form("resume"),
    dry_run: str = Form("0"),
    store_slug: str = Form(""),
    reason_tag: str = Form(""),
) -> Any:
    denied = _admin_session_or_redirect(request, next_path="/admin/control")
    if denied is not None:
        return denied
    is_dry = (dry_run or "").strip().lower() in ("1", "true", "yes", "on")
    resume_operational_control(
        target=target,
        store_slug=store_slug or None,
        reason_tag=reason_tag or None,
        operator=operator,
        reason=reason,
        dry_run=is_dry,
    )
    return RedirectResponse(url="/admin/control?resumed=1", status_code=303)
