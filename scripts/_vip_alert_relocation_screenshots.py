# -*- coding: utf-8 -*-
"""Screenshot capture for VIP alert relocation (homepage → carts)."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8011"
OUT = Path(__file__).resolve().parent / "_vip_alert_relocation_out"
OUT.mkdir(parents=True, exist_ok=True)

KNOWLEDGE_STUB = {
    "ok": True,
    "store_slug": "demo",
    "window_days": 7,
    "generated_at": "2026-06-07T12:00:00+00:00",
    "insights": [
        {
            "insight_key": "hesitation_top_reason",
            "category": "hesitation",
            "severity": "info",
            "title_ar": "أغلب حالات التردد مرتبطة بالسعر",
            "message_ar": "خلال الفترة الأخيرة كان السعر هو السبب الأكثر تكراراً.",
            "evidence": {"top_reason": "price", "top_count": 42, "hesitation_total": 75},
            "confidence": "medium",
            "data_window": {"days": 7},
            "sample_size": 75,
            "source_tables": ["cart_recovery_reasons"],
            "recommended_action_ar": "راقب هذا المؤشر خلال الأيام القادمة.",
        }
    ],
    "metrics_snapshot": {},
}

VIP_WITH_ALERT = {
    "ok": True,
    "merchant_vip_page_rows": [
        {
            "abandoned_cart_row_id": 9001,
            "avatar_letter": "أ",
            "amount_display": "1,250",
            "subtitle_ar": "منذ 12 دقيقة",
            "contact_href": "https://wa.me/966500000001",
        }
    ],
    "merchant_vip_rows": [
        {
            "avatar_letter": "أ",
            "amount_display": "1,250",
            "subtitle_ar": "منذ 12 دقيقة",
            "contact_href": "https://wa.me/966500000001",
        }
    ],
    "merchant_vip_banner": {
        "amount_line": "1,250 ريال — عميل VIP",
        "contact_href": "https://wa.me/966500000001",
    },
    "merchant_nav_badge_vip": 1,
    "merchant_vip_alert_state_ar": "",
}

VIP_EMPTY = {
    "ok": True,
    "merchant_vip_page_rows": [],
    "merchant_vip_rows": [],
    "merchant_vip_banner": None,
    "merchant_nav_badge_vip": 0,
    "merchant_vip_alert_state_ar": "",
}

NORMAL_CARTS_STUB = {
    "ok": True,
    "merchant_carts_page_rows": [],
    "merchant_cart_filter_counts": {
        "all": 0,
        "recovered": 0,
        "sent": 0,
        "followup": 0,
        "not_trying": 0,
    },
}

SUMMARY_STUB = {
    "ok": True,
    "merchant_kpi_abandoned_fmt": "0",
    "merchant_kpi_recovered_fmt": "0",
    "merchant_kpi_recovery_pct_fmt": "0",
    "merchant_kpi_revenue_fmt": "0",
    "merchant_month_abandoned_fmt": "0",
    "merchant_month_recovered_fmt": "0",
    "merchant_month_recovery_pct_fmt": "0",
    "merchant_month_revenue_fmt": "0",
}


def _install_routes(page, vip_payload: dict) -> None:
    def _knowledge(route):
        route.fulfill(
            status=200,
            content_type="application/json; charset=utf-8",
            body=json.dumps(KNOWLEDGE_STUB, ensure_ascii=False),
        )

    def _vip(route):
        route.fulfill(
            status=200,
            content_type="application/json; charset=utf-8",
            body=json.dumps(vip_payload, ensure_ascii=False),
        )

    def _normal(route):
        route.fulfill(
            status=200,
            content_type="application/json; charset=utf-8",
            body=json.dumps(NORMAL_CARTS_STUB, ensure_ascii=False),
        )

    def _summary(route):
        route.fulfill(
            status=200,
            content_type="application/json; charset=utf-8",
            body=json.dumps(SUMMARY_STUB, ensure_ascii=False),
        )

    page.route("**/api/knowledge/report**", _knowledge)
    page.route("**/api/dashboard/vip-carts**", _vip)
    page.route("**/api/dashboard/normal-carts**", _normal)
    page.route("**/api/dashboard/summary**", _summary)


def _goto_hash(page, hash_tag: str) -> None:
    page.goto(f"{BASE}/dashboard{hash_tag}", wait_until="domcontentloaded")
    page.wait_for_timeout(800)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(device_scale_factor=1)
        page = ctx.new_page()

        _install_routes(page, VIP_EMPTY)

        page.set_viewport_size({"width": 1280, "height": 900})
        _goto_hash(page, "#home")
        page.wait_for_selector("#ma-knowledge-root", timeout=15000)
        page.wait_for_timeout(600)
        page.locator("#page-home").screenshot(path=str(OUT / "01_homepage_after_no_vip_banner.png"))

        _goto_hash(page, "#carts")
        page.wait_for_selector("#ma-cart-filters", timeout=15000)
        page.wait_for_function(
            "document.getElementById('ma-cart-alerts-root') && document.getElementById('ma-cart-alerts-root').hidden === true",
            timeout=15000,
        )
        page.locator("#page-carts").screenshot(path=str(OUT / "03_carts_no_vip_alert.png"))

        _install_routes(page, VIP_WITH_ALERT)
        page.reload(wait_until="domcontentloaded")
        _goto_hash(page, "#carts")
        page.wait_for_selector("#ma-cart-filters", timeout=15000)
        page.wait_for_function(
            "document.querySelector('#ma-cart-alerts-root .vip-alert')",
            timeout=15000,
        )
        page.locator("#page-carts").screenshot(path=str(OUT / "02_carts_with_vip_alert.png"))

        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="domcontentloaded")
        _goto_hash(page, "#carts")
        page.wait_for_selector("#ma-cart-filters", timeout=15000)
        page.wait_for_function(
            "document.querySelector('#ma-cart-alerts-root .vip-alert')",
            timeout=15000,
        )
        page.locator("#page-carts").screenshot(path=str(OUT / "04_carts_vip_alert_mobile.png"))

        ctx.close()
        browser.close()

    print("screenshots written to", OUT)


if __name__ == "__main__":
    main()
