# -*- coding: utf-8 -*-
"""
Dashboard counter source governance — store-level canonical totals.

One Source Of Truth Per Question. See ``services/dashboard_counter_totals_v1.py``.
"""
from __future__ import annotations

COUNTER_GOVERNANCE_VERSION = "v1"

# Merchant question → single canonical field → producer
COUNTER_SOURCE_OF_TRUTH_MAP = {
    "active_total": {
        "merchant_meaning_ar": "عدد السلال النشطة في المتجر (غير مؤرشفة/مكتملة)",
        "api_field": "merchant_store_cart_counts.active_total",
        "filter_bar_key": "all",
        "producer": "build_merchant_cart_counter_totals",
        "scope": "store_total",
    },
    "waiting_total": {
        "merchant_meaning_ar": "سلال بانتظار الإرسال",
        "api_field": "merchant_store_cart_counts.waiting_total",
        "nav_badge": "merchant_nav_badge_abandoned",
        "producer": "build_merchant_cart_counter_totals",
        "scope": "store_total",
    },
    "sent_total": {
        "merchant_meaning_ar": "سلال أُرسلت لها رسالة وتنتظر تفاعل",
        "api_field": "merchant_store_cart_counts.sent_total",
        "filter_bar_key": "sent",
        "producer": "build_merchant_cart_counter_totals",
        "scope": "store_total",
    },
    "engaged_total": {
        "merchant_meaning_ar": "سلال تحتاج متابعة (تفاعل / تدخل)",
        "api_field": "merchant_store_cart_counts.engaged_total",
        "filter_bar_key": "attention",
        "producer": "build_merchant_cart_counter_totals",
        "scope": "store_total",
    },
    "completed_total": {
        "merchant_meaning_ar": "سلال مكتملة — نفس قاعدة صفحة «مكتملة»",
        "api_field": "merchant_store_cart_counts.completed_total",
        "filter_bar_key": "recovered",
        "completed_page": True,
        "rule": "is_completed_dashboard_row",
        "producer": "build_merchant_cart_counter_totals",
        "scope": "store_total",
    },
    "archived_total": {
        "merchant_meaning_ar": "سلال مؤرشفة في المتجر",
        "api_field": "merchant_store_cart_counts.archived_total",
        "producer": "build_merchant_cart_counter_totals",
        "scope": "store_total",
    },
    "no_phone_total": {
        "merchant_meaning_ar": "سلال بدون جوال قبل الإرسال الأول — تبويب عرض فقط (ليس حالة مسار)",
        "api_field": "merchant_store_cart_counts.no_phone_total",
        "filter_bar_key": "nophone",
        "row_facet": "merchant_cart_visible_tabs includes nophone",
        "facet_module": "dashboard_no_phone_facet_v1",
        "producer": "build_merchant_cart_counter_totals",
        "scope": "store_total",
        "ui_hidden_when_zero": True,
    },
    "visible_page_counts": {
        "merchant_meaning_ar": "عدد الصفوف في الصفحة الحالية فقط — للتدقيق وليس للتاجر",
        "api_field": "merchant_visible_page_counts",
        "producer": "visible_page_counts_from_rows",
        "scope": "page_window",
        "merchant_facing": False,
    },
}

# Internal-only metrics (different questions — not interchangeable with cart tab counters)
INTERNAL_ONLY_METRICS = {
    "messages_sent_count": "إجمالي سجلات الإرسال في المتجر (سجلات وليس سلال)",
    "normal_recovered_count": "سلال بحالة recovered في قاعدة البيانات",
    "stopped_flow_count": "سجلات توقف/تخطي في مسار الاسترجاع",
    "merchant_kpi_abandoned_fmt": "سلال متروكة اليوم (KPI)",
}

__all__ = [
    "COUNTER_GOVERNANCE_VERSION",
    "COUNTER_SOURCE_OF_TRUTH_MAP",
    "INTERNAL_ONLY_METRICS",
]
