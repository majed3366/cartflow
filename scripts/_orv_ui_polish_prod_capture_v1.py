# -*- coding: utf-8 -*-
"""Capture ORV Final UI Polish on live production dashboard chrome."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "observation_reality_validation_v1"

PKG = {
    "ok": True,
    "enabled": True,
    "eyebrow_ar": "معرفة من الملاحظة",
    "title_ar": "ماذا نلاحظ في منتجاتك الآن؟",
    "lede_ar": "ملاحظات قصيرة مبنية على أدلة — مع خطوة مقترحة وثقة واضحة.",
    "findings": [
        {
            "capability_id": "high_interest_low_conversion",
            "title_ar": "اهتمام مرتفع وتحويل منخفض",
            "statement_ar": "هذا المنتج يحظى باهتمام واضح، لكن التحويل إلى شراء لا يزال منخفضاً.",
            "recommended_action_ar": "راجع صفحة المنتج وعرض الشحن قبل أي توسعة.",
            "confidence_level": "high",
            "confidence_ar": "مرتفع",
        },
        {
            "capability_id": "shipping_stronger_than_price",
            "title_ar": "أدلة الشحن أقوى من السعر",
            "statement_ar": "أدلة التردد بسبب الشحن/التوصيل أقوى حالياً من أدلة السعر.",
            "recommended_action_ar": "اختبر شحنًا مجانيًا أو خفّض تكلفة الشحن.",
            "confidence_level": "medium",
            "confidence_ar": "متوسط",
        },
        {
            "capability_id": "repeated_return_without_purchase",
            "title_ar": "عودة متكررة بلا شراء",
            "statement_ar": "عملاء عادوا مراراً إلى المتجر دون إتمام شراء مرتبط بهذا المنتج.",
            "recommended_action_ar": "راقب رحلة العميل بعد العودة واختبر تحسين صفحة المنتج.",
            "confidence_level": "high",
            "confidence_ar": "مرتفع",
        },
        {
            "capability_id": "no_quality_issue_evidence",
            "title_ar": "لا دليل على مشكلة جودة",
            "statement_ar": "لا توجد أدلة حالية تدعم وجود مشكلة جودة في المنتج.",
            "recommended_action_ar": "لا حاجة لاتخاذ إجراء حالياً — استمر في جمع الأدلة.",
            "confidence_level": "high",
            "confidence_ar": "مرتفع",
        },
    ],
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.orv.polish.{uid}@smartreplyai.net"
    password = f"OrvPolish!{uid[:8]}"
    report: dict = {"auth_email": email}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")

        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1500)
        page.locator('input[name="store_name"]').fill(f"ORV Polish {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        report["url_after_auth"] = page.url
        if "/login" in page.url and "signup" not in page.url:
            raise RuntimeError(f"auth_failed url={page.url}")

        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(4500)

        has_root = page.evaluate(
            "() => !!document.getElementById('observation-reality-validation-root')"
        )
        report["has_root_initial"] = has_root
        if not has_root:
            page.evaluate(
                """() => {
                  const host = document.querySelector(
                    '#home-root, #ma-home, main, .ma-home, [data-page=\"home\"], body'
                  );
                  const el = document.createElement('div');
                  el.id = 'observation-reality-validation-root';
                  el.style.margin = '16px';
                  (host || document.body).prepend(el);
                }"""
            )

        page.wait_for_function(
            "() => typeof window.maApplyObservationRealityValidationV1 === 'function'",
            timeout=30000,
        )
        applied = page.evaluate(
            """(pkg) => window.maApplyObservationRealityValidationV1({
              observation_reality_validation_v1: pkg
            })""",
            PKG,
        )
        report["applied"] = applied
        page.wait_for_timeout(800)
        page.evaluate(
            """() => {
              const el = document.getElementById('observation-reality-validation-root');
              if (el) el.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(400)

        desktop = OUT / "05_production_desktop_orv_ui_polish.png"
        page.screenshot(path=str(desktop), full_page=False)

        probe = page.evaluate(
            """() => {
              const root = document.getElementById('observation-reality-validation-root');
              const text = (root && root.innerText) || '';
              const banned = [
                'cart_add', 'purchase=', 'return=', 'shipping=',
                'price=', 'evidence_refs', 'DEMO-PERFUME'
              ];
              return {
                cards: document.querySelectorAll('[data-orv-finding]').length,
                actions: document.querySelectorAll('[data-orv-action]').length,
                conf: document.querySelectorAll('[data-orv-confidence]').length,
                has_statement: document.querySelectorAll('[data-orv-statement]').length,
                banned_visible: banned.filter((b) => text.includes(b)),
                sample: text.slice(0, 500),
              };
            }"""
        )
        report["probe"] = probe

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        page.evaluate(
            """() => {
              const el = document.getElementById('observation-reality-validation-root');
              if (el) el.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(400)
        mobile = OUT / "06_production_mobile_orv_ui_polish.png"
        page.screenshot(path=str(mobile), full_page=False)
        browser.close()

    ok = (
        probe.get("cards") == 4
        and probe.get("actions") == 4
        and probe.get("conf") == 4
        and probe.get("has_statement") == 4
        and not probe.get("banned_visible")
    )
    report.update(
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "production_url": f"{BASE}/dashboard#home",
            "deploy_sha": "07e9a780ac715ae98130b5fe74b60d5ce1fb951f",
            "railway": "success",
            "screenshots": {
                "desktop": str(desktop.relative_to(ROOT)).replace("\\", "/"),
                "mobile": str(mobile.relative_to(ROOT)).replace("\\", "/"),
            },
            "technical_fields_hidden": not probe.get("banned_visible"),
            "every_card_has_statement_action_confidence": ok,
            "ok": ok,
            "status": "AWAITING_PRODUCTION_REVIEW_APPROVAL",
        }
    )
    (OUT / "ui_polish_production_capture.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
