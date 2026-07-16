# -*- coding: utf-8 -*-
"""Admin Product Investigations dashboard (read-only) — session auth."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from json_response import j
from services.cartflow_admin_http_auth import (
    admin_cookie_name,
    admin_password_configured,
    admin_session_cookie_valid,
)
from services.product_investigation_registry_v1 import (
    build_investigation_dashboard_payload,
    get_investigation_detail,
)
from routes.admin_operations import (
    _admin_session_or_redirect,
    router,
    templates,
)

ADMIN_NAV_INVESTIGATIONS = "investigations"


def _admin_json_auth(request: Request) -> Optional[JSONResponse]:
    if not admin_password_configured():
        return JSONResponse({"ok": False, "error": "admin_not_configured"}, status_code=503)
    cookie = request.cookies.get(admin_cookie_name())
    if not admin_session_cookie_valid(cookie):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    return None


def _filter_kwargs(request: Request) -> dict[str, Optional[str]]:
    q = request.query_params
    return {
        "status": (q.get("status") or "").strip() or None,
        "severity": (q.get("severity") or "").strip() or None,
        "category": (q.get("category") or "").strip() or None,
        "wave": (q.get("wave") or "").strip() or None,
        "parent": (q.get("parent") or "").strip() or None,
        "merchant_trust": (q.get("merchant_trust") or "").strip() or None,
    }


@router.get("/admin/investigations", response_class=HTMLResponse)
def admin_investigations_page(request: Request) -> Any:
    denied = _admin_session_or_redirect(request, next_path="/admin/investigations")
    if denied is not None:
        return denied
    filters = _filter_kwargs(request)
    payload = build_investigation_dashboard_payload(**filters)
    return templates.TemplateResponse(
        request,
        "admin_investigations.html",
        {
            "admin_active_nav": ADMIN_NAV_INVESTIGATIONS,
            "admin_page_title_ar": "تحقيقات المنتج",
            "admin_page_subtitle_ar": "سجل التحقيقات الدائم — للقراءة فقط · لا تعديل من الواجهة",
            "dash": payload,
            "filters": filters,
        },
    )


@router.get("/admin/investigations/{inv_id}", response_class=HTMLResponse)
def admin_investigation_detail_page(request: Request, inv_id: str) -> Any:
    denied = _admin_session_or_redirect(
        request, next_path=f"/admin/investigations/{inv_id}"
    )
    if denied is not None:
        return denied
    detail = get_investigation_detail(inv_id)
    if detail is None:
        return templates.TemplateResponse(
            request,
            "admin_investigations_detail.html",
            {
                "admin_active_nav": ADMIN_NAV_INVESTIGATIONS,
                "admin_page_title_ar": "تحقيق غير موجود",
                "admin_page_subtitle_ar": inv_id,
                "detail": None,
                "inv_id": inv_id,
            },
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "admin_investigations_detail.html",
        {
            "admin_active_nav": ADMIN_NAV_INVESTIGATIONS,
            "admin_page_title_ar": detail.get("id") or inv_id,
            "admin_page_subtitle_ar": detail.get("title") or "",
            "detail": detail,
            "inv_id": inv_id,
        },
    )


@router.get("/api/admin/investigations")
def api_admin_investigations(request: Request) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    return j(build_investigation_dashboard_payload(**_filter_kwargs(request)))


@router.get("/api/admin/investigations/{inv_id}")
def api_admin_investigation_detail(request: Request, inv_id: str) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    detail = get_investigation_detail(inv_id)
    if detail is None:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    return j({"ok": True, "read_only": True, "investigation": detail})


# Explicitly reject mutations in V1
@router.post("/api/admin/investigations/{inv_id}")
@router.put("/api/admin/investigations/{inv_id}")
@router.patch("/api/admin/investigations/{inv_id}")
@router.delete("/api/admin/investigations/{inv_id}")
def api_admin_investigations_mutations_forbidden(
    request: Request, inv_id: str
) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    return JSONResponse(
        {
            "ok": False,
            "error": "read_only",
            "message": "Investigation Dashboard V1 is read-only. Update canonical docs.",
        },
        status_code=405,
    )
