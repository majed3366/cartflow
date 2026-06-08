# -*- coding: utf-8 -*-
"""Merchant dashboard HTML pages and legacy redirect routes."""
from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

router = APIRouter(tags=["merchant-pages"])


@router.get("/dashboard/recovery-settings")
def dashboard_recovery_settings(request: Request):
    """توافق خلفي — التوقيت والقوالب داخل تطبيق التاجر."""
    return RedirectResponse(url="/dashboard#whatsapp", status_code=302)


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
