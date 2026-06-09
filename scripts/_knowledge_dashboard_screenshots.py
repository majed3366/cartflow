# -*- coding: utf-8 -*-
"""Screenshot capture for Knowledge Layer dashboard section (mocked API)."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8011"
OUT = Path(__file__).resolve().parent / "_knowledge_dashboard_out"
OUT.mkdir(parents=True, exist_ok=True)

EMPTY_PAYLOAD = {
    "ok": True,
    "store_slug": "demo",
    "window_days": 7,
    "generated_at": "2026-06-07T12:00:00+00:00",
    "insights": [
        {
            "insight_key": "traffic_visitor_unavailable",
            "category": "traffic",
            "severity": "notice",
            "title_ar": "بيانات الزوار غير متوفرة",
            "message_ar": "CartFlow لا يرى عدد زوار المتجر حالياً.",
            "evidence": {"visitor_data_available": False},
            "confidence": "insufficient",
            "data_window": {"days": 7},
            "sample_size": 0,
            "source_tables": ["abandoned_carts"],
            "recommended_action_ar": "قد تحتاج إلى مراجعة إعدادات التتبع.",
        }
    ],
    "metrics_snapshot": {},
}

INSIGHT_PAYLOAD = {
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
            "message_ar": "خلال الفترة الأخيرة كان السعر هو السبب الأكثر تكراراً بين أسباب التردد المسجلة.",
            "evidence": {"top_reason": "price", "top_count": 42, "hesitation_total": 75},
            "confidence": "medium",
            "data_window": {"days": 7},
            "sample_size": 75,
            "source_tables": ["cart_recovery_reasons"],
            "recommended_action_ar": "راقب هذا المؤشر خلال الأيام القادمة.",
        },
        {
            "insight_key": "recovery_activity_summary",
            "category": "recovery",
            "severity": "info",
            "title_ar": "ملخص نشاط الاسترجاع",
            "message_ar": "رسائل مُرسَلة: 10؛ ردود: 3؛ مشتريات: 2.",
            "evidence": {"messages_sent": 10, "replies": 3, "purchases": 2, "returns": 1},
            "confidence": "medium",
            "data_window": {"days": 7},
            "sample_size": 10,
            "source_tables": ["cart_recovery_logs"],
            "recommended_action_ar": "راقب هذا المؤشر خلال الأيام القادمة.",
        },
        {
            "insight_key": "recovery_bottleneck",
            "category": "recovery",
            "severity": "notice",
            "title_ar": "عنق زجاجة في الاسترجاع",
            "message_ar": "أبرز نقطة ضغط مسجّلة: no_reply (4 حدث).",
            "evidence": {"bottlenecks": [{"key": "no_reply", "label": "no_reply", "count": 4}]},
            "confidence": "low",
            "data_window": {"days": 7},
            "sample_size": 10,
            "source_tables": ["cart_recovery_logs"],
            "recommended_action_ar": "تأكد أن بيانات المتجر تصل بشكل صحيح.",
        },
        {
            "insight_key": "traffic_cart_demand_trend",
            "category": "traffic",
            "severity": "info",
            "title_ar": "اتجاه الطلب (سلات مهجورة)",
            "message_ar": "سلات الفترة الحالية: 12؛ الفترة السابقة: 8.",
            "evidence": {"cart_count": 12, "prev_cart_count": 8, "trend": "up"},
            "confidence": "low",
            "data_window": {"days": 7},
            "sample_size": 12,
            "source_tables": ["abandoned_carts"],
            "recommended_action_ar": "راقب هذا المؤشر خلال الأيام القادمة.",
        },
    ],
    "metrics_snapshot": {},
}


def _capture(page, payload: dict, name: str, viewport: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False)

    def _route(route):
        route.fulfill(
            status=200,
            content_type="application/json; charset=utf-8",
            body=body,
        )

    page.route("**/api/knowledge/report**", _route)
    page.set_viewport_size(viewport)
    page.goto(f"{BASE}/dashboard", wait_until="domcontentloaded")
    page.wait_for_selector("#ma-knowledge-root", timeout=15000)
    page.wait_for_function(
        "document.querySelector('#ma-knowledge-body .ma-knowledge-empty, #ma-knowledge-body .ma-knowledge-cards')",
        timeout=15000,
    )
    page.wait_for_timeout(400)
    el = page.locator("#ma-knowledge-root")
    el.screenshot(path=str(OUT / name))


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(device_scale_factor=1)
        page = ctx.new_page()

        _capture(page, EMPTY_PAYLOAD, "knowledge_empty_desktop.png", {"width": 1280, "height": 900})
        _capture(page, INSIGHT_PAYLOAD, "knowledge_insights_desktop.png", {"width": 1280, "height": 900})
        _capture(page, EMPTY_PAYLOAD, "knowledge_empty_mobile.png", {"width": 390, "height": 844})
        _capture(page, INSIGHT_PAYLOAD, "knowledge_insights_mobile.png", {"width": 390, "height": 844})

        (OUT / "api_sample_insights.json").write_text(
            json.dumps(INSIGHT_PAYLOAD, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (OUT / "api_sample_empty.json").write_text(
            json.dumps(EMPTY_PAYLOAD, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        ctx.close()
        browser.close()
    print("screenshots written to", OUT)


if __name__ == "__main__":
    main()
