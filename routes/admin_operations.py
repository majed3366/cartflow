# -*- coding: utf-8 -*-
"""
Admin operational control center (HTML) — reads existing operational summary only.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from json_response import j

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
ADMIN_NAV_CURRENT_ISSUES = "current-issues"
ADMIN_NAV_STORES = "stores"
ADMIN_NAV_WHATSAPP = "whatsapp"
ADMIN_NAV_INTEGRATIONS = "integrations"
ADMIN_NAV_SUPPORT_DIAG = "support-diagnostics"
# Retained for deep diagnostics surfaces reached from Support Diagnostics.
ADMIN_NAV_OPS_HEALTH = ADMIN_NAV_SUPPORT_DIAG
ADMIN_NAV_OPS_CONTROL = ADMIN_NAV_SUPPORT_DIAG

_ADMIN_PLACEHOLDER_PAGES: tuple[tuple[str, str, str, str], ...] = (
    (
        "/admin/stores",
        ADMIN_NAV_STORES,
        "المتاجر",
        "إدارة ومتابعة المتاجر — قريباً.",
    ),
    (
        "/admin/integrations",
        ADMIN_NAV_INTEGRATIONS,
        "التكاملات",
        "حالة تكامل المتاجر مع المنصة — قريباً.",
    ),
    # Legacy paths kept reachable (no longer in primary navigation).
    (
        "/admin/alerts",
        ADMIN_NAV_CURRENT_ISSUES,
        "التنبيهات",
        "عرض التنبيهات التشغيلية المركزية — قريباً.",
    ),
    (
        "/admin/stores/paused",
        ADMIN_NAV_STORES,
        "المتاجر المتوقفة",
        "المتاجر المتوقفة أو المعطّلة — قريباً.",
    ),
    (
        "/admin/stores/integration",
        ADMIN_NAV_INTEGRATIONS,
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
        ADMIN_NAV_WHATSAPP,
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
        ADMIN_NAV_SUPPORT_DIAG,
        "صحة النظام",
        "ملخص صحة النظام — للتفاصيل التشغيلية استخدم تشخيص الدعم.",
    ),
    (
        "/admin/system/logs",
        ADMIN_NAV_SUPPORT_DIAG,
        "السجلات",
        "عرض سجلات النظام للدعم — قريباً.",
    ),
    (
        "/admin/system/technical",
        ADMIN_NAV_SUPPORT_DIAG,
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


def _admin_json_auth(request: Request) -> Optional[JSONResponse]:
    if not admin_password_configured():
        return JSONResponse({"ok": False, "error": "admin_not_configured"}, status_code=503)
    cookie = request.cookies.get(admin_cookie_name())
    if not admin_session_cookie_valid(cookie):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
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


_OPS_LAZY_SECTION_ERROR_HTML = (
    '<p class="text-sm text-rose-700 py-6 text-center">تعذر تحميل هذا القسم الآن.</p>'
)


@router.get("/admin/operations", response_class=HTMLResponse)
def admin_operations_dashboard(request: Request) -> Any:
    denied = _admin_session_or_redirect(request, next_path="/admin/operations")
    if denied is not None:
        return denied
    try:
        from services.admin_operations_center_v1 import (  # noqa: PLC0415
            build_admin_operations_command_center_readonly,
        )

        ops = build_admin_operations_command_center_readonly()
    except Exception:  # noqa: BLE001
        ops = {
            "version": "admin_operations_center_v2_5",
            "generated_at_utc": None,
            "executive_summary": {
                "platform_status_key": "stable",
                "platform_status_ar": "مستقرة",
                "platform_status_tone": "ok",
                "platform_description_ar": "لا توجد تنبيهات تشغيلية ظاهرة حاليًا.",
                "active_stores": 0,
                "ready_stores": 0,
                "affected_stores": 0,
                "production_affected_stores": 0,
                "production_critical_stores": 0,
                "production_warning_stores": 0,
                "production_healthy_stores": 0,
                "open_alerts": 0,
                "open_issues": 0,
                "recoveries_today": 0,
            },
            "current_issues": {"issues": [], "total": 0, "available": True},
            "critical_alerts": {
                "section": "critical_alerts",
                "status": "healthy",
                "summary": {
                    "total": 0,
                    "highest_severity": "healthy",
                    "highest_severity_emoji": "🟢",
                    "highest_severity_label": "Healthy",
                    "critical_count": 0,
                    "warning_count": 0,
                    "information_count": 0,
                },
                "healthy": {
                    "status_label": "Healthy",
                    "message_en": "No critical operational issues detected.",
                    "verification_en": "All monitored systems are operating normally.",
                },
                "alerts": [],
            },
            "store_action_center": {
                "section": "store_action_center",
                "status": "healthy",
                "summary": {
                    "affected_count": 0,
                    "highest_severity": "healthy",
                    "highest_severity_emoji": "🟢",
                    "highest_severity_label": "Healthy",
                    "critical_count": 0,
                    "warning_count": 0,
                    "information_count": 0,
                    "healthy_count": 0,
                    "production_store_count": 0,
                    "demo_test_store_count": 0,
                    "production_affected_count": 0,
                    "production_critical_count": 0,
                    "production_warning_count": 0,
                    "production_healthy_count": 0,
                    "demo_test_affected_count": 0,
                    "root_cause_count": 0,
                    "critical_root_cause_count": 0,
                    "warning_root_cause_count": 0,
                    "critical_priority_store_count": 0,
                    "high_priority_store_count": 0,
                    "medium_priority_store_count": 0,
                    "monitoring_store_count": 0,
                },
                "dev_test": {
                    "demo_stores": 0,
                    "loadtest_stores": 0,
                    "sandbox_stores": 0,
                    "other_test_stores": 0,
                    "affected_in_scan": 0,
                },
                "healthy": {
                    "status_label": "Healthy",
                    "message_en": "No production stores currently require intervention.",
                    "verification_en": "All monitored production stores are operating normally.",
                },
                "stores": [],
                "production_queue": [],
                "production_action_queue": [],
                "demo_test_queue": [],
            },
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
                "production_only": True,
                "available": True,
            },
            "top_risks": {
                "risks": [],
                "total_candidates": 0,
                "shown_count": 0,
                "max_shown": 5,
                "available": True,
            },
            "health_scheduler_path": "/health/scheduler",
        }
    return templates.TemplateResponse(
        request,
        "admin_operations_center_v1.html",
        {
            "admin_active_nav": ADMIN_NAV_OVERVIEW,
            "admin_page_title_ar": "نظرة عامة تنفيذية",
            "admin_page_subtitle_ar": (
                "حالة المنصة · المشاكل الحالية · المتأثرون · ماذا نفعل الآن"
            ),
            "ops": ops,
        },
    )


@router.get("/admin/operations/issues", response_class=HTMLResponse)
def admin_operations_current_issues(request: Request) -> Any:
    denied = _admin_session_or_redirect(
        request, next_path="/admin/operations/issues"
    )
    if denied is not None:
        return denied
    try:
        from services.admin_operations_center_v1 import (  # noqa: PLC0415
            build_admin_operations_current_issues_readonly,
        )

        ops = build_admin_operations_current_issues_readonly()
    except Exception:  # noqa: BLE001
        ops = {
            "version": "admin_operations_center_v2_2",
            "generated_at_utc": None,
            "system_health_summary": {
                "status_key": "stable",
                "status_ar": "مستقرة",
                "description_ar": "لا توجد تنبيهات تشغيلية ظاهرة حاليًا.",
                "total_alerts": 0,
            },
            "current_issues": {"issues": [], "total": 0, "available": True},
            "health_scheduler_path": "/health/scheduler",
        }
    return templates.TemplateResponse(
        request,
        "admin_operations_current_issues.html",
        {
            "admin_active_nav": ADMIN_NAV_CURRENT_ISSUES,
            "admin_page_title_ar": "المشاكل الحالية",
            "admin_page_subtitle_ar": (
                "مشكلة → الأثر → المتأثر → المسؤول → الإجراء المقترح → التحقق"
            ),
            "ops": ops,
        },
    )


@router.get("/admin/diagnostics", response_class=HTMLResponse)
def admin_support_diagnostics_overview(request: Request) -> Any:
    denied = _admin_session_or_redirect(request, next_path="/admin/diagnostics")
    if denied is not None:
        return denied
    try:
        from services.admin_operations_center_v1 import (  # noqa: PLC0415
            build_admin_support_diagnostics_overview_readonly,
        )

        ops = build_admin_support_diagnostics_overview_readonly()
    except Exception:  # noqa: BLE001
        ops = {
            "version": "admin_operations_center_v2_2",
            "generated_at_utc": None,
            "recovery_resume_health": {},
            "health_scheduler_path": "/health/scheduler",
        }
    return templates.TemplateResponse(
        request,
        "admin_support_diagnostics_overview.html",
        {
            "admin_active_nav": ADMIN_NAV_SUPPORT_DIAG,
            "admin_page_title_ar": "تشخيص الدعم",
            "admin_page_subtitle_ar": (
                "أدوات تقنية للدعم فقط — صحة الاستئناف، المجدول، الإحصاءات، والاتجاهات."
            ),
            "ops": ops,
        },
    )


@router.get("/admin/operations/section/investigation", response_class=HTMLResponse)
def admin_operations_section_investigation(request: Request) -> Any:
    denied = _admin_session_or_redirect(
        request, next_path="/admin/operations/section/investigation"
    )
    if denied is not None:
        return denied
    try:
        from services.admin_operations_center_v1 import (  # noqa: PLC0415
            build_admin_operations_investigation_section_readonly,
        )

        ops = build_admin_operations_investigation_section_readonly()
    except Exception:  # noqa: BLE001
        return HTMLResponse(_OPS_LAZY_SECTION_ERROR_HTML, status_code=500)
    return templates.TemplateResponse(
        request,
        "partials/admin_operations_investigation_section.html",
        {"ops": ops},
    )


@router.get("/admin/operations/section/analytics", response_class=HTMLResponse)
def admin_operations_section_analytics(request: Request) -> Any:
    denied = _admin_session_or_redirect(
        request, next_path="/admin/operations/section/analytics"
    )
    if denied is not None:
        return denied
    try:
        from services.admin_operations_center_v1 import (  # noqa: PLC0415
            build_admin_operations_analytics_section_readonly,
        )

        ops = build_admin_operations_analytics_section_readonly()
    except Exception:  # noqa: BLE001
        return HTMLResponse(_OPS_LAZY_SECTION_ERROR_HTML, status_code=500)
    return templates.TemplateResponse(
        request,
        "partials/admin_operations_analytics_section.html",
        {"ops": ops},
    )


def _widget_health_issue_groups(issues: Any) -> list[dict[str, Any]]:
    """Presentation-only aggregation: group detected issues by kind.

    Does NOT touch detection/scoring (services/widget_health_v1.py). Builds a
    grouped view so one platform-wide problem shows once with an affected-store
    count + expandable list, ordered by severity then affected count.
    """
    order = {"critical": 2, "warning": 1, "healthy": 0}
    groups: dict[str, dict[str, Any]] = {}
    for it in issues or []:
        kind = it.get("kind")
        grp = groups.get(kind)
        if grp is None:
            from services.admin_operations_action_engine_v1 import (  # noqa: PLC0415
                resolve_widget_issue_guidance,
            )

            en = resolve_widget_issue_guidance(str(kind or ""))
            grp = {
                "kind": kind,
                "severity": it.get("severity"),
                "severity_ar": it.get("severity_ar"),
                "severity_emoji": it.get("severity_emoji"),
                "problem_ar": it.get("problem_ar"),
                "impact_ar": it.get("impact_ar"),
                "suggested_action_ar": it.get("suggested_action_ar"),
                "verification_ar": it.get("verification_ar"),
                "problem_en": en.get("problem_en"),
                "impact_en": en.get("impact_en"),
                "where_en": en.get("where_en"),
                "suggested_action_en": en.get("suggested_action_en"),
                "verification_en": en.get("verification_en"),
                "stores": [],
            }
            groups[kind] = grp
        grp["stores"].append(
            {
                "store_slug": it.get("store_slug"),
                "store_name": it.get("store_name"),
                "where_ar": it.get("where_ar"),
                "technical_details": it.get("technical_details"),
            }
        )
    out = list(groups.values())
    for grp in out:
        grp["count"] = len(grp["stores"])
    out.sort(
        key=lambda g: (order.get(g.get("severity"), 1), g.get("count", 0)),
        reverse=True,
    )
    return out


# Business-language summaries for the manager-first operational view (V4).
# Presentation-only mapping; never used by detection/scoring.
_WIDGET_HEALTH_HEADLINE_AR: dict[str, str] = {
    "runtime_beacon_missing": "لا تصل إشارات التشغيل",
    "widget_not_seen": "الودجت لا يظهر للعملاء",
    "widget_bootstrap_blocked": "تعذر تشغيل الودجت",
    "widget_module_failed": "تعذر تشغيل الودجت",
    "widget_runtime_object_missing": "تعذر تشغيل الودجت",
    "public_config_not_loaded": "إعدادات الودجت غير مكتملة",
    "cart_event_bridge_missing": "لا يتم رصد نشاط السلة",
    "store_identity_mismatch": "مشكلة في ربط المتجر",
    "widget_settings_mismatch": "إعدادات الودجت غير متطابقة",
    "widget_not_shown_after_cart_event": "الودجت لا يظهر للعملاء",
    "hesitation_not_armed": "لا يظهر الودجت بعد إضافة منتج",
    "cart_event_false_positive": "رصد نشاط سلة غير دقيق",
    "widget_cors_error": "مشكلة في حفظ بيانات التشغيل",
}
_WIDGET_HEALTH_PRIORITY: dict[str, str] = {
    "widget_module_failed": "high",
    "widget_bootstrap_blocked": "high",
    "widget_runtime_object_missing": "high",
    "widget_not_seen": "high",
    "widget_not_shown_after_cart_event": "high",
    "runtime_beacon_missing": "medium",
    "public_config_not_loaded": "medium",
    "cart_event_bridge_missing": "medium",
    "hesitation_not_armed": "medium",
    "widget_settings_mismatch": "low",
    "store_identity_mismatch": "low",
    "cart_event_false_positive": "low",
    "widget_cors_error": "low",
}
_PRIORITY_AR = {"high": "عالية", "medium": "متوسطة", "low": "منخفضة"}
_PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}


def _widget_health_needs_attention(stores: Any) -> list[dict[str, Any]]:
    """Presentation-only: one business-language row per affected store.

    Picks each store's single most important detected issue and renders it in
    operational language (no beacon/runtime/API terms). Built from existing
    Widget Health data; no detection/scoring changes.
    """
    sev_rank = {"critical": 2, "warning": 1, "healthy": 0}
    rows: list[dict[str, Any]] = []
    for st in stores or []:
        if st.get("status") == "healthy":
            continue
        issues = st.get("issues") or []
        if not issues:
            continue
        top = max(
            issues,
            key=lambda it: (
                sev_rank.get(it.get("severity"), 0),
                _PRIORITY_RANK.get(
                    _WIDGET_HEALTH_PRIORITY.get(it.get("kind"), "medium"), 2
                ),
            ),
        )
        kind = top.get("kind")
        prio = _WIDGET_HEALTH_PRIORITY.get(kind, "medium")
        rows.append(
            {
                "store_name": st.get("store_name"),
                "store_slug": st.get("store_slug"),
                "status": st.get("status"),
                "headline_ar": _WIDGET_HEALTH_HEADLINE_AR.get(
                    kind, top.get("problem_ar") or ""
                ),
                "priority_key": prio,
                "priority_ar": _PRIORITY_AR.get(prio, prio),
            }
        )
    rows.sort(
        key=lambda r: (
            _PRIORITY_RANK.get(r.get("priority_key"), 2),
            sev_rank.get(r.get("status"), 0),
        ),
        reverse=True,
    )
    return rows


@router.get("/admin/operations/section/db-ready-health", response_class=HTMLResponse)
def admin_operations_section_db_ready_health(request: Request) -> Any:
    denied = _admin_session_or_redirect(
        request, next_path="/admin/operations/section/db-ready-health"
    )
    if denied is not None:
        return denied
    try:
        from services.db_ready_admin_v1 import (  # noqa: PLC0415
            build_admin_db_ready_health_section_readonly,
        )

        health = build_admin_db_ready_health_section_readonly()
    except Exception:  # noqa: BLE001
        return HTMLResponse(_OPS_LAZY_SECTION_ERROR_HTML, status_code=500)
    return templates.TemplateResponse(
        request,
        "partials/admin_operations_db_ready_section.html",
        {"health": health},
    )


@router.get("/admin/operations/section/widget-health", response_class=HTMLResponse)
def admin_operations_section_widget_health(request: Request) -> Any:
    denied = _admin_session_or_redirect(
        request, next_path="/admin/operations/section/widget-health"
    )
    if denied is not None:
        return denied
    try:
        from services.widget_health_v1 import (  # noqa: PLC0415
            build_admin_widget_health_section_readonly,
        )

        health = build_admin_widget_health_section_readonly()
        # Presentation-only: grouped issue view + manager-first summary
        # (no detection changes).
        health = dict(health)
        health["issue_groups"] = _widget_health_issue_groups(health.get("issues"))
        health["needs_attention"] = _widget_health_needs_attention(health.get("stores"))
    except Exception:  # noqa: BLE001
        return HTMLResponse(_OPS_LAZY_SECTION_ERROR_HTML, status_code=500)
    return templates.TemplateResponse(
        request,
        "partials/admin_operations_widget_health_section.html",
        {"health": health},
    )


@router.get("/admin/operations/snapshot")
def admin_operations_snapshot_export(
    request: Request,
    store_slug: str = Query(""),
) -> Any:
    """Read-only operational snapshot JSON for support and incident investigation."""
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_operational_snapshot_v1 import (  # noqa: PLC0415
        build_admin_operational_snapshot_v1,
    )

    snapshot = build_admin_operational_snapshot_v1(
        store_slug=(store_slug or "").strip(),
        generated_by="admin_session",
    )
    return j({"ok": True, "snapshot": snapshot})


@router.get("/api/admin/operations/widget-configuration-trust")
def admin_widget_configuration_trust(
    request: Request,
    storefront_slug: str = Query("", max_length=255),
    store_slug: str = Query("", max_length=255),
) -> Any:
    """Read-only widget configuration trust recovery JSON (foundation — no UI)."""
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.widget_configuration_trust_v1 import (  # noqa: PLC0415
        build_widget_configuration_trust_report,
    )

    sf = (storefront_slug or store_slug or "").strip()
    try:
        from main import _ensure_cartflow_api_db_warmed, _dashboard_recovery_store_row  # noqa: PLC0415

        _ensure_cartflow_api_db_warmed()
        dash_row = _dashboard_recovery_store_row()
        if not sf and dash_row is not None:
            sf = str(getattr(dash_row, "zid_store_id", "") or "").strip()
        report = build_widget_configuration_trust_report(
            dash_row,
            storefront_slug=sf or None,
        )
        status_code = 200 if report.get("ok") else 503
        return j(report, status_code=status_code)
    except Exception as exc:  # noqa: BLE001
        from extensions import db  # noqa: PLC0415

        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/api/admin/operations/pilot-foundation")
def admin_pilot_operational_foundation(
    request: Request,
    include_demo: int = Query(0),
) -> Any:
    """Read-only pilot operational visibility foundation JSON."""
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.pilot_operational_foundation_v1 import (  # noqa: PLC0415
        build_pilot_operational_foundation_readonly,
    )

    payload = build_pilot_operational_foundation_readonly(
        include_demo=bool(int(include_demo or 0)),
    )
    status_code = 200 if payload.get("ok") else 503
    return j(payload, status_code=status_code)


@router.get("/admin/operations/recovery-resume-inspect")
def admin_recovery_resume_inspect(
    request: Request,
    store_slug: str = Query(""),
    status: str = Query(""),
    resume_only: int = Query(0),
    stale_only: int = Query(0),
    limit: int = Query(100),
) -> Any:
    """Read-only recovery resume inspect — no DB writes."""
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_recovery_resume_inspect_scan_v1 import (  # noqa: PLC0415
        build_recovery_resume_inspect_readonly,
    )

    payload = build_recovery_resume_inspect_readonly(
        store_slug=(store_slug or "").strip(),
        status=(status or "").strip(),
        resume_only=bool(int(resume_only or 0)),
        stale_only=bool(int(stale_only or 0)),
        limit=int(limit or 100),
    )
    return j({"ok": True, **payload})


@router.get("/admin/operations/recovery-resume-scan")
def admin_recovery_resume_scan(
    request: Request,
    store_slug: str = Query(""),
    limit: int = Query(100),
) -> Any:
    """Dry-run recovery resume scan simulation — no execution or DB writes."""
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_recovery_resume_inspect_scan_v1 import (  # noqa: PLC0415
        build_recovery_resume_scan_readonly,
    )

    payload = build_recovery_resume_scan_readonly(
        store_slug=(store_slug or "").strip(),
        limit=int(limit or 100),
    )
    return j({"ok": True, **payload})


@router.get("/admin/subscriptions/control", response_class=HTMLResponse)
def admin_subscription_control_page(request: Request) -> Any:
    denied = _admin_session_or_redirect(
        request, next_path="/admin/subscriptions/control"
    )
    if denied is not None:
        return denied
    return templates.TemplateResponse(
        request,
        "admin_subscription_control.html",
        {
            "admin_active_nav": "subs-control",
            "admin_page_title_ar": "التحكم باشتراك المتاجر",
            "admin_page_subtitle_ar": "تعيين الباقات والتجربة يدوياً — بدون دفع أو فواتير",
        },
    )


@router.get("/api/admin/subscriptions")
def api_admin_subscriptions_list(
    request: Request,
    q: str = "",
    limit: int = 50,
) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_subscription_control_v1 import list_admin_subscription_rows  # noqa: PLC0415

    rows = list_admin_subscription_rows(query=q, limit=limit)
    return j({"ok": True, "rows": [r.to_api_dict() for r in rows]})


@router.get("/api/admin/subscriptions/{merchant_user_id}/audit")
def api_admin_subscription_audit(
    request: Request,
    merchant_user_id: int,
    limit: int = 20,
) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_subscription_control_v1 import (  # noqa: PLC0415
        list_subscription_audit_logs,
    )

    logs = list_subscription_audit_logs(merchant_user_id, limit=limit)
    return j({"ok": True, "audit_logs": logs})


@router.post("/api/admin/subscriptions/{merchant_user_id}/action")
async def api_admin_subscription_action(
    request: Request,
    merchant_user_id: int,
) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_subscription_control_v1 import (  # noqa: PLC0415
        apply_admin_subscription_action,
    )

    try:
        body = await request.json()
    except (TypeError, ValueError):
        body = {}
    if not isinstance(body, dict):
        body = {}
    result = apply_admin_subscription_action(
        int(merchant_user_id),
        action=str(body.get("action") or ""),
        admin_source="admin_session",
        reason=str(body.get("reason") or ""),
        plan=body.get("plan"),
        trial_days=body.get("trial_days"),
        extend_days=body.get("extend_days"),
        plan_expires_at=body.get("plan_expires_at"),
        trial_expires_at=body.get("trial_expires_at"),
        plan_started_at=body.get("plan_started_at"),
    )
    code = 200 if result.ok else 400
    return JSONResponse(result.to_api_dict(), status_code=code)


@router.get("/admin/whatsapp", response_class=HTMLResponse)
def admin_whatsapp_visibility_page(request: Request) -> Any:
    denied = _admin_session_or_redirect(request, next_path="/admin/whatsapp")
    if denied is not None:
        return denied
    return templates.TemplateResponse(
        request,
        "admin_whatsapp_visibility.html",
        {
            "admin_active_nav": ADMIN_NAV_WHATSAPP,
            "admin_page_title_ar": "واتساب — رؤية تشغيلية",
            "admin_page_subtitle_ar": "وضع واتساب وحالة الاتصال — بدون إرسال أو Meta",
        },
    )


@router.get("/api/admin/whatsapp/stores")
def api_admin_whatsapp_stores_list(
    request: Request,
    q: str = "",
    limit: int = 50,
) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_whatsapp_visibility_v1 import list_admin_whatsapp_store_rows  # noqa: PLC0415

    rows = list_admin_whatsapp_store_rows(query=q, limit=limit)
    return j({"ok": True, "rows": [r.to_api_dict() for r in rows]})


@router.get("/api/admin/whatsapp/templates")
def api_admin_whatsapp_templates_registry(request: Request) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_whatsapp_template_visibility_v1 import (  # noqa: PLC0415
        list_admin_template_registry_rows,
    )

    rows = list_admin_template_registry_rows()
    return j({"ok": True, "rows": [r.to_api_dict() for r in rows]})


@router.get("/api/admin/whatsapp/store-templates")
def api_admin_whatsapp_store_templates(
    request: Request,
    q: str = "",
    store_id: int = 0,
    limit: int = 50,
) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_whatsapp_template_visibility_v1 import (  # noqa: PLC0415
        list_admin_store_template_rows,
    )

    sid = int(store_id) if store_id else None
    rows = list_admin_store_template_rows(query=q, store_id=sid, limit=limit)
    return j({"ok": True, "rows": [r.to_api_dict() for r in rows]})


@router.get("/api/admin/whatsapp/execution-policy")
def api_admin_whatsapp_execution_policy(request: Request) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.merchant_whatsapp_template_execution_policy_v1 import (  # noqa: PLC0415
        execution_policy_summary_for_api,
    )

    return j({"ok": True, **execution_policy_summary_for_api()})


@router.get("/api/admin/whatsapp/template-library")
def api_admin_whatsapp_template_library(
    request: Request,
    logical_key: str = "",
) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.admin_whatsapp_template_library_visibility_v1 import (  # noqa: PLC0415
        admin_template_library_api_payload,
    )

    lk = (logical_key or "").strip() or None
    return j(admin_template_library_api_payload(logical_key=lk))


@router.get("/api/admin/whatsapp/connection-readiness")
def api_admin_whatsapp_connection_readiness(
    request: Request,
    store_id: int = 0,
) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from extensions import db  # noqa: PLC0415
    from models import Store  # noqa: PLC0415
    from services.admin_whatsapp_visibility_v1 import build_admin_whatsapp_store_row  # noqa: PLC0415
    from services.merchant_whatsapp_connection_readiness_v1 import (  # noqa: PLC0415
        connection_readiness_for_admin_row,
        meta_future_placeholders_for_api,
    )

    if store_id > 0:
        row = db.session.get(Store, int(store_id))
        if row is None:
            return j({"ok": False, "error": "store_not_found"}, status_code=404)
        from services.cartflow_onboarding_readiness import (  # noqa: PLC0415
            evaluate_onboarding_readiness,
        )
        from services.merchant_whatsapp_readiness_diagnostic_v1 import (  # noqa: PLC0415
            build_whatsapp_readiness_diagnostic_temp,
        )

        admin_row = build_admin_whatsapp_store_row(row)
        detail = connection_readiness_for_admin_row(row)
        ob = evaluate_onboarding_readiness(row)
        detail["readiness_diagnostic_temp"] = build_whatsapp_readiness_diagnostic_temp(
            detail,
            row,
            action_first={},
            onboarding_flags=dict(ob.get("flags") or {}),
            blocking_steps=list(ob.get("blocking_steps") or []),
        )
        return j(
            {
                "ok": True,
                "store": admin_row.to_api_dict(),
                "connection_readiness": detail,
                "meta_future_placeholders": meta_future_placeholders_for_api(
                    visible=False
                ),
            }
        )
    return j(
        {
            "ok": True,
            "architecture_only": True,
            "meta_future_placeholders": meta_future_placeholders_for_api(
                visible=False
            ),
        }
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
