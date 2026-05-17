# -*- coding: utf-8 -*-
"""
Admin operational control center (HTML) — reads existing operational summary only.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.cartflow_admin_operational_guidance import derive_admin_operational_guidance
from services.cartflow_admin_action_guidance import (
    actionable_panel_meta,
    derive_actionable_operational_items,
)
from services.cartflow_admin_http_auth import (
    admin_cookie_name,
    admin_password_configured,
    admin_session_cookie_valid,
    issue_admin_session_cookie_value,
    verify_admin_password,
)
from services.admin_operational_health import build_admin_operational_health_readonly
from services.cartflow_admin_operational_summary import (
    ADMIN_PLATFORM_CATEGORY_DEGRADED,
    ADMIN_PLATFORM_CATEGORY_HEALTHY,
    ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED,
    ADMIN_PLATFORM_CATEGORY_OPERATIONAL_ATTENTION,
    ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION,
    ADMIN_PLATFORM_CATEGORY_RUNTIME_WARNING,
    ADMIN_PLATFORM_CATEGORY_SANDBOX_ONLY,
    TRUST_DEGRADED,
    TRUST_PARTIAL,
    TRUST_READY,
    TRUST_UNSTABLE,
    build_admin_operational_summary_readonly,
)

_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_ROOT / "templates"))

router = APIRouter(tags=["admin"])

_PLATFORM_CATEGORY_LABEL_AR: dict[str, str] = {
    ADMIN_PLATFORM_CATEGORY_HEALTHY: "سليم",
    ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED: "إعداد معطّل",
    ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION: "مزود",
    ADMIN_PLATFORM_CATEGORY_RUNTIME_WARNING: "تشغيل",
    ADMIN_PLATFORM_CATEGORY_OPERATIONAL_ATTENTION: "تشغيل دقيق",
    ADMIN_PLATFORM_CATEGORY_DEGRADED: "متدهور",
    ADMIN_PLATFORM_CATEGORY_SANDBOX_ONLY: "تجربة فقط",
}

_TRUST_BUCKET_LABEL_AR: dict[str, str] = {
    TRUST_READY: "جاهز",
    TRUST_PARTIAL: "جزئي",
    TRUST_DEGRADED: "ضعيف",
    TRUST_UNSTABLE: "غير مستقر",
}


def _render_login(request: Request, *, error: bool, next_path: str) -> Any:
    return templates.TemplateResponse(
        request,
        "admin_operations_login.html",
        {
            "error": error,
            "next_path": next_path,
            "admin_configured": admin_password_configured(),
            "missing_config": False,
        },
    )


@router.get("/admin/operations/login", response_class=HTMLResponse)
def admin_operations_login_page(
    request: Request,
    next: str = "/admin/operations",
    e: str = "",
) -> Any:
    if not admin_password_configured():
        return templates.TemplateResponse(
            request,
            "admin_operations_login.html",
            {
                "error": False,
                "next_path": next,
                "admin_configured": False,
                "missing_config": True,
            },
        )
    safe_next = (next or "/admin/operations").strip() or "/admin/operations"
    if not safe_next.startswith("/admin/"):
        safe_next = "/admin/operations"
    return _render_login(request, error=bool(e), next_path=safe_next)


@router.post("/admin/operations/login")
def admin_operations_login_submit(
    request: Request,
    password: str = Form(...),
    next: str = Form("/admin/operations"),
) -> Any:
    if not admin_password_configured():
        return HTMLResponse(
            "Admin password not configured (set CARTFLOW_ADMIN_PASSWORD).",
            status_code=503,
        )
    safe_next = (next or "/admin/operations").strip() or "/admin/operations"
    if not safe_next.startswith("/admin/"):
        safe_next = "/admin/operations"
    if not verify_admin_password(password):
        return RedirectResponse(
            url=f"/admin/operations/login?e=1&next={safe_next}",
            status_code=303,
        )
    resp = RedirectResponse(url=safe_next, status_code=303)
    resp.set_cookie(
        admin_cookie_name(),
        issue_admin_session_cookie_value(),
        httponly=True,
        samesite="lax",
        max_age=8 * 3600,
        secure=(os.getenv("CARTFLOW_ADMIN_COOKIE_SECURE") or "").strip().lower()
        in ("1", "true", "yes", "on"),
        path="/",
    )
    return resp


def _admin_session_or_redirect(request: Request, *, next_path: str) -> Optional[Any]:
    if not admin_password_configured():
        return HTMLResponse(
            "Admin password not configured — set CARTFLOW_ADMIN_PASSWORD.",
            status_code=503,
        )
    cookie = request.cookies.get(admin_cookie_name())
    if not admin_session_cookie_valid(cookie):
        return RedirectResponse(
            url=f"/admin/operations/login?next={next_path}",
            status_code=302,
        )
    return None


@router.post("/admin/operations/logout")
def admin_operations_logout() -> RedirectResponse:
    resp = RedirectResponse(url="/admin/operations/login", status_code=303)
    resp.delete_cookie(admin_cookie_name(), path="/")
    return resp


@router.get("/admin/operational-health", response_class=HTMLResponse)
def admin_operational_health_page(request: Request) -> Any:
    denied = _admin_session_or_redirect(
        request, next_path="/admin/operational-health"
    )
    if denied is not None:
        return denied
    health = build_admin_operational_health_readonly()
    return templates.TemplateResponse(
        request,
        "admin_operational_health.html",
        {"health": health},
    )


@router.get("/admin/operations", response_class=HTMLResponse)
def admin_operations_dashboard(request: Request) -> Any:
    denied = _admin_session_or_redirect(request, next_path="/admin/operations")
    if denied is not None:
        return denied
    summary = build_admin_operational_summary_readonly()
    guidance = derive_admin_operational_guidance(summary)
    action_items = derive_actionable_operational_items(
        summary, priority_key=str(guidance.get("priority_key") or "")
    )
    action_meta = actionable_panel_meta(
        summary,
        priority_key=str(guidance.get("priority_key") or ""),
        action_items=action_items,
    )
    agg = summary.get("aggregate_onboarding") or {}
    tcounts = agg.get("trust_bucket_counts") or {}
    platform_cat = str(summary.get("platform_admin_category") or "")
    return templates.TemplateResponse(
        request,
        "admin_operations.html",
        {
            "summary": summary,
            "platform_category_label_ar": _PLATFORM_CATEGORY_LABEL_AR.get(
                platform_cat,
                platform_cat or "—",
            ),
            "trust_bucket_labels_ar": _TRUST_BUCKET_LABEL_AR,
            "trust_ready_n": int(tcounts.get(TRUST_READY, 0)),
            "trust_partial_n": int(tcounts.get(TRUST_PARTIAL, 0)),
            "trust_degraded_n": int(tcounts.get(TRUST_DEGRADED, 0)),
            "trust_unstable_n": int(tcounts.get(TRUST_UNSTABLE, 0)),
            "guidance": guidance,
            "action_items": action_items,
            "action_meta": action_meta,
        },
    )
