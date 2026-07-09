# -*- coding: utf-8 -*-
"""Merchant dashboard HTML pages and legacy redirect routes."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

from services.merchant_dashboard_reference_ui import merchant_ar_weekday_date_header

router = APIRouter(tags=["merchant-pages"])


@router.get("/dashboard")
def dashboard(request: Request):
    """لوحة التاجر — هيكل فوري؛ الأقسام الثقيلة تُحمّل لاحقاً عبر ‎JavaScript‎."""
    from services.db_request_audit import stall_trace_checkpoint
    from main import (
        _dashboard_recovery_store_row,
        _log_dashboard_shell_profile,
        _merchant_dashboard_db_ready,
        _merchant_dashboard_shell_store_fields,
        templates,
    )

    stall_trace_checkpoint("dashboard_entry")
    wall0 = time.perf_counter()
    _merchant_dashboard_db_ready()
    stall_trace_checkpoint("dashboard_after_merchant_db_ready")
    dash_store = _dashboard_recovery_store_row()
    now_utc = datetime.now(timezone.utc)
    shell_store = _merchant_dashboard_shell_store_fields(
        dash_store, cookies=dict(request.cookies)
    )
    stall_trace_checkpoint("dashboard_before_template_render")
    from services.merchant_setup_render_build import (  # noqa: PLC0415
        MERCHANT_SETUP_RENDER_BUILD,
    )
    from services.cart_page_v2_ui_flag_v1 import (  # noqa: PLC0415
        carts_v2_ui_enabled,
    )

    resp = templates.TemplateResponse(
        request,
        "merchant_app.html",
        {
            "request": request,
            "merchant_html_title": "CartFlow — لوحة التاجر",
            "merchant_setup_render_build": MERCHANT_SETUP_RENDER_BUILD,
            "merchant_dashboard_lazy_shell": True,
            "merchant_carts_v2_ui": carts_v2_ui_enabled(),
            "merchant_ar_date_header": merchant_ar_weekday_date_header(now_utc),
            "merchant_nav_badge_abandoned": 0,
            "merchant_nav_badge_followup": 0,
            "merchant_nav_badge_vip": 0,
            "wa_badge_ar": "…",
            "wa_state_key": "",
            "merchant_kpi_abandoned_fmt": "…",
            "merchant_kpi_recovered_fmt": "…",
            "merchant_kpi_wa_sent_fmt": "…",
            "merchant_kpi_revenue_fmt": "…",
            "merchant_kpi_recovered_pct_vs_abandoned": 0.0,
            "merchant_kpi_wa_sub_ar": "سجلات إرسال اليوم",
            "merchant_reason_rows_week": [],
            "merchant_reason_insight_ar": "",
            "merchant_reason_rows_month": [],
            "merchant_reason_recommendations_ar": [],
            "merchant_table_rows": [],
            "merchant_carts_page_rows": [],
            "merchant_cart_filter_counts": {
                "all": 0,
                "recovered": 0,
                "sent": 0,
                "attention": 0,
                "nophone": 0,
            },
            "merchant_followup_rows": [],
            "merchant_vip_rows": [],
            "merchant_vip_page_rows": [],
            "merchant_vip_banner": None,
            "merchant_message_history_rows": [],
            "merchant_wa_last_send_ar": "—",
            "merchant_widget_title_ar": "مساعد المتجر",
            "merchant_widget_question_ar": "ما الذي منعك من إكمال الطلب؟",
            "merchant_widget_reason_rows": [],
            "merchant_widget_panel": {},
            "merchant_widget_installed": True,
            "merchant_month_abandoned_fmt": "…",
            "merchant_month_recovered_fmt": "…",
            "merchant_month_recovery_pct_fmt": "…",
            "merchant_month_revenue_fmt": "…",
            **shell_store,
        },
    )
    stall_trace_checkpoint("dashboard_after_template_before_shell_profile")
    _log_dashboard_shell_profile(wall_perf_start=wall0)
    stall_trace_checkpoint("dashboard_response_ready")
    return resp


@router.get("/dashboard/analytics")
def dashboard_analytics(request: Request):
    """عرض الرسوم والتفاصيل الإضافية — يحتفظ ببث ‎live_feed‎ الكامل للفريق."""
    from main import (
        _dashboard_recovery_store_row,
        _dashboard_v1_financial_context,
        _log_dashboard_profile,
        _merchant_dashboard_db_ready,
        templates,
    )

    wall0 = time.perf_counter()
    _merchant_dashboard_db_ready()
    dash_store = _dashboard_recovery_store_row()
    ctx = _dashboard_v1_financial_context(dash_store)
    resp = templates.TemplateResponse(
        request,
        "dashboard_v1.html",
        {"request": request, **ctx},
    )
    _log_dashboard_profile(
        endpoint="GET /dashboard/analytics",
        section="analytics_page",
        wall_perf_start=wall0,
    )
    return resp


@router.get("/dashboard/recovery-settings")
def dashboard_recovery_settings(request: Request):
    """توافق خلفي — التوقيت والقوالب داخل تطبيق التاجر."""
    return RedirectResponse(url="/dashboard#whatsapp", status_code=302)


@router.get("/dashboard/whatsapp-connect")
def dashboard_whatsapp_connect(request: Request):
    """Embedded Signup connect shell — merchant-owned WhatsApp onboarding (foundation V1)."""
    return RedirectResponse(url="/dashboard#whatsapp-connect", status_code=302)


@router.get("/dashboard/normal-carts")
def dashboard_normal_carts(request: Request):
    """السلال العادية — واجهة التاجر؛ معاملات ‎session/cart/test_run‎ تُوجَّه للوحة العمليات."""
    nr_sess = (request.query_params.get("nr_session") or "").strip()
    nr_cid = (request.query_params.get("nr_cart") or "").strip()
    nr_tr = (request.query_params.get("nr_test_run") or "").strip()
    if nr_sess or nr_cid or nr_tr:
        raw_q = str(getattr(request.url, "query", None) or "").strip()
        dest = "/dashboard/normal-carts/operations"
        if raw_q:
            dest += "?" + raw_q
        return RedirectResponse(url=dest, status_code=302)
    return RedirectResponse(url="/dashboard#carts", status_code=302)


@router.get("/dashboard/normal-recovery")
def dashboard_normal_recovery_legacy(request: Request):
    """توافق خلفي لمسار العنوان السابق."""
    return RedirectResponse(url="/dashboard#carts", status_code=302)


@router.get("/dashboard/normal")
def dashboard_normal_alias(request: Request):
    """توافق عنوان مختصر — لوحة التاجر الموحدة."""
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/dashboard/vip-cart-settings")
def dashboard_vip_cart_settings(request: Request):
    """توافق خلفي — إعدادات ‎VIP‎ داخل تطبيق التاجر."""
    return RedirectResponse(url="/dashboard#vip", status_code=302)


@router.get("/dashboard/cartflow-messages")
def dashboard_cartflow_messages(request: Request):
    """إعادة توجيه — دمج إعدادات استعادة السلة ضمن تطبيق التاجر."""
    return RedirectResponse(url="/dashboard#whatsapp", status_code=302)


@router.get("/dashboard/cart-recovery-messages")
def dashboard_cart_recovery_messages(request: Request):
    """توافق خلفي — القوالب ضمن تطبيق التاجر."""
    return RedirectResponse(url="/dashboard#whatsapp", status_code=302)


@router.get("/dashboard/widget-customization")
def dashboard_widget_customization(request: Request):
    """توافق خلفي — تخصيص الودجيت داخل تطبيق التاجر."""
    return RedirectResponse(url="/dashboard#widget", status_code=302)


@router.get("/dashboard/exit-intent-settings")
def dashboard_exit_intent_settings(request: Request):
    """رسالة قبل الخروج فقط — نفس ‎GET/POST /api/recovery-settings‎ (تحديث جزئي)."""
    from main import templates

    return templates.TemplateResponse(
        request,
        "exit_intent_settings.html",
        {"request": request},
    )


@router.get("/dashboard/general-settings")
def dashboard_general_settings(request: Request):
    """إعدادات عامة — واتساب المتجر، ظهور الودجيت، ومظهر الودجيت."""
    from main import templates

    base = str(request.base_url)
    if base.endswith("/"):
        base = base[:-1]
    return templates.TemplateResponse(
        request,
        "general_settings.html",
        {"request": request, "cartflow_public_origin": base},
    )


@router.get("/dashboard/test-widget")
def dashboard_test_widget(request: Request):
    """مسار تجربة موجّه — متجر تجريبي بمعرّف التاجر (جلسة مطلوبة)."""
    from services.merchant_activation_v1 import merchant_activation_test_store_url  # noqa: PLC0415
    from services.merchant_onboarding_store import resolve_merchant_onboarding_store  # noqa: PLC0415

    store, _meta = resolve_merchant_onboarding_store(cookies=dict(request.cookies))
    if store is None:
        return RedirectResponse(url="/login?next=/dashboard/test-widget", status_code=302)
    slug = (getattr(store, "zid_store_id", None) or "").strip()
    if not slug:
        return RedirectResponse(url="/dashboard#settings", status_code=302)
    return RedirectResponse(url=merchant_activation_test_store_url(slug), status_code=302)
