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

from services.cartflow_admin_http_auth import (
    admin_cookie_name,
    admin_password_configured,
    admin_session_cookie_valid,
    issue_admin_session_cookie_value,
    verify_admin_password,
)
from services.admin_operational_health import build_admin_operational_health_readonly

_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_ROOT / "templates"))

router = APIRouter(tags=["admin"])

# Sidebar nav keys (presentation only — no business logic).
ADMIN_NAV_OVERVIEW = "overview"
ADMIN_NAV_OPS_HEALTH = "ops-health"
ADMIN_NAV_OPS_CONTROL = "ops-control"

_ADMIN_PLACEHOLDER_PAGES: tuple[tuple[str, str, str, str], ...] = (
    (
        "/admin/alerts",
        "ops-alerts",
        "التنبيهات",
        "عرض التنبيهات التشغيلية المركزية — قريباً.",
    ),
    (
        "/admin/stores",
        "stores-all",
        "جميع المتاجر",
        "عرض المتاجر وحالة التشغيل — قريباً.",
    ),
    (
        "/admin/stores/paused",
        "stores-paused",
        "المتاجر المتوقفة",
        "المتاجر المتوقفة أو المعطّلة — قريباً.",
    ),
    (
        "/admin/stores/integration",
        "stores-integration",
        "حالة التكامل",
        "حالة تكامل المتاجر مع المنصة — قريباً.",
    ),
    (
        "/admin/subscriptions/plans",
        "subs-plans",
        "الباقات",
        "إدارة باقات الاشتراك — قريباً.",
    ),
    (
        "/admin/subscriptions/trial",
        "subs-trial",
        "التجريبي",
        "حالة الفترة التجريبية للمتاجر — قريباً.",
    ),
    (
        "/admin/subscriptions/renewals",
        "subs-renewals",
        "التجديدات",
        "تجديدات الاشتراك والمواعيد — قريباً.",
    ),
    (
        "/admin/reports/recovery",
        "reports-recovery",
        "تقارير الاسترجاع",
        "تقارير الاسترجاع والأداء — قريباً.",
    ),
    (
        "/admin/reports/whatsapp",
        "reports-whatsapp",
        "تقارير واتساب",
        "تقارير إرسال واتساب — قريباً.",
    ),
    (
        "/admin/reports/stores",
        "reports-stores",
        "تقارير المتاجر",
        "تقارير أداء المتاجر — قريباً.",
    ),
    (
        "/admin/system/health",
        "system-health",
        "صحة النظام",
        "ملخص صحة النظام — للتفاصيل التشغيلية الفورية استخدم مركز التشغيل.",
    ),
    (
        "/admin/system/logs",
        "system-logs",
        "السجلات",
        "عرض سجلات النظام للدعم — قريباً.",
    ),
    (
        "/admin/system/technical",
        "system-technical",
        "تفاصيل تقنية",
        "تشخيصات تقنية للدعم — قريباً.",
    ),
)

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


def _admin_placeholder_page(
    request: Request,
    *,
    path: str,
    nav_key: str,
    title_ar: str,
    description_ar: str,
) -> Any:
    denied = _admin_session_or_redirect(request, next_path=path)
    if denied is not None:
        return denied
    return templates.TemplateResponse(
        request,
        "admin_placeholder.html",
        {
            "admin_active_nav": nav_key,
            "admin_page_title_ar": title_ar,
            "admin_page_subtitle_ar": description_ar,
            "page_title_ar": title_ar,
            "page_description_ar": description_ar,
        },
    )


@router.get("/admin", response_class=HTMLResponse)
def admin_root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/admin/operations", status_code=302)


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
    try:
        health = build_admin_operational_health_readonly()
    except Exception:
        from services.admin_cart_event_load_test import LOAD_TEST_DISPLAY_UNAVAILABLE_AR

        health = {
            "version": "admin_operational_control_v2",
            "latest_load_test_ar": LOAD_TEST_DISPLAY_UNAVAILABLE_AR,
            "latest_multi_store_load_test_ar": (
                "آخر اختبار تعدد متاجر: غير متاح مؤقتاً"
            ),
            "latest_mixed_behavior_load_test_ar": (
                "آخر اختبار سلوك مختلط: غير متاح مؤقتاً"
            ),
            "latest_failure_simulation_ar": "آخر محاكاة أعطال: غير متاح مؤقتاً",
            "admin_risk_summary": {
                "risk_level": 0,
                "status_emoji": "🟢",
                "status_label_ar": "سليم",
                "headline_ar": "تعذر تحميل ملخص التشغيل بالكامل",
                "subheadline_ar": "",
                "metrics": {},
                "metrics_labels_ar": {},
            },
            "admin_impact_layer": {"has_issues": False, "empty_message_ar": "—"},
            "admin_actions_layer": {"has_actions": False, "empty_message_ar": "—"},
            "admin_verification_layer": {"has_recoveries": False, "empty_message_ar": "—"},
            "admin_revenue_protection": {
                "headline_ar": "—",
                "protected": [],
                "risk": [],
                "summary_stable_ar": "—",
                "summary_fail_ar": "—",
            },
            "admin_operational_timeline": {
                "items": [
                    {
                        "time_ar": "—",
                        "message_ar": "تعذر بناء الخط الزمني",
                        "kind": "empty",
                        "severity": "warning",
                        "severity_emoji": "🟡",
                    }
                ]
            },
            "quick_answers": {
                "is_healthy_ar": "غير معروف",
                "what_failing_ar": "—",
                "who_affected_ar": "—",
                "what_to_do_ar": "أعد تحميل الصفحة",
                "did_recover_ar": "—",
            },
            "diagnostics_v1": {"cards": {}, "warnings": []},
            "cards": {},
            "warnings": [],
            "headlines": {},
        }
    oc = health.get("operations_center") or {}
    return templates.TemplateResponse(
        request,
        "admin_operational_health.html",
        {
            "health": health,
            "admin_active_nav": ADMIN_NAV_OPS_HEALTH,
            "admin_page_title_ar": str(oc.get("title_ar") or "مركز التشغيل"),
            "admin_page_subtitle_ar": (
                "قرارات تشغيل خلال ثوانٍ: مشكلة → أثر → من المتأثر → ماذا نفعل → كيف نتحقق"
            ),
        },
    )


@router.get("/admin/operations", response_class=HTMLResponse)
def admin_operations_dashboard(request: Request) -> Any:
    denied = _admin_session_or_redirect(request, next_path="/admin/operations")
    if denied is not None:
        return denied
    try:
        from services.admin_operations_center_v1 import (  # noqa: PLC0415
            build_admin_operations_center_v1_readonly,
        )

        ops = build_admin_operations_center_v1_readonly()
    except Exception:  # noqa: BLE001
        ops = {
            "version": "admin_operations_center_v1_6",
            "generated_at_utc": None,
            "system_health_summary": {
                "status_key": "stable",
                "status_ar": "مستقرة",
                "description_ar": "لا توجد تنبيهات تشغيلية ظاهرة حاليًا.",
                "highest_severity": "none",
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "total_alerts": 0,
            },
            "store_health_snapshot": {
                "stores": [],
                "total_stores": 0,
                "available": True,
            },
            "operational_trends": {
                "window_hours": 24,
                "trends": [],
                "available": True,
            },
            "scheduler": {
                "role": "غير متوفر",
                "overdue_scheduled_count": 0,
                "running_stale_count": 0,
                "resume_enabled": False,
                "due_scanner_enabled": False,
                "ok": False,
            },
            "recovery": {
                "scheduled": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "expired": 0,
                "available": False,
            },
            "store_readiness": {
                "total_stores": 0,
                "ready_stores": 0,
                "stores_missing_whatsapp": 0,
                "stores_no_recent_cart_events": 0,
                "stores_needing_setup": 0,
                "available": False,
            },
            "alerts": [],
            "health_scheduler_path": "/health/scheduler",
        }
    return templates.TemplateResponse(
        request,
        "admin_operations_center_v1.html",
        {
            "admin_active_nav": ADMIN_NAV_OVERVIEW,
            "admin_page_title_ar": "مركز العمليات",
            "admin_page_subtitle_ar": "قراءة تشغيلية موحّدة — مجدول، استرجاع، متاجر، تنبيهات.",
            "ops": ops,
        },
    )


def _register_admin_placeholder_routes() -> None:
    for path, nav_key, title_ar, description_ar in _ADMIN_PLACEHOLDER_PAGES:

        def _handler(
            request: Request,
            *,
            _path: str = path,
            _nav: str = nav_key,
            _title: str = title_ar,
            _desc: str = description_ar,
        ) -> Any:
            return _admin_placeholder_page(
                request,
                path=_path,
                nav_key=_nav,
                title_ar=_title,
                description_ar=_desc,
            )

        router.add_api_route(
            path,
            _handler,
            methods=["GET"],
            response_class=HTMLResponse,
        )


_register_admin_placeholder_routes()
