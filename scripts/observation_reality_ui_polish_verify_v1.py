# -*- coding: utf-8 -*-
"""ORV Final UI Polish — render polished cards and capture Desktop/Mobile shots."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "observation_reality_validation_v1"
JS = ROOT / "static" / "observation_reality_validation_v1.js"

# Evidence-backed sample (same capabilities as Reality Validation lab)
SAMPLE_FINDINGS = [
    {
        "capability_id": "high_interest_low_conversion",
        "title_ar": "اهتمام مرتفع وتحويل منخفض",
        "statement_ar": "هذا المنتج يحظى باهتمام واضح، لكن التحويل إلى شراء لا يزال منخفضاً.",
        "recommended_action_ar": "راجع صفحة المنتج وعرض الشحن قبل أي توسعة.",
        "confidence_level": "medium",
        "confidence_ar": "متوسط",
    },
    {
        "capability_id": "shipping_stronger_than_price",
        "title_ar": "أدلة الشحن أقوى من السعر",
        "statement_ar": "أدلة التردد بسبب الشحن/التوصيل أقوى حالياً من أدلة السعر.",
        "recommended_action_ar": "اختبر شحنًا مجانيًا أو خفّض تكلفة الشحن.",
        "confidence_level": "high",
        "confidence_ar": "مرتفع",
    },
    {
        "capability_id": "repeated_return_without_purchase",
        "title_ar": "عودة متكررة بلا شراء",
        "statement_ar": "عملاء عادوا مراراً إلى المتجر دون إتمام شراء مرتبط بهذا المنتج.",
        "recommended_action_ar": "راقب رحلة العميل بعد العودة واختبر تحسين صفحة المنتج.",
        "confidence_level": "medium",
        "confidence_ar": "متوسط",
    },
    {
        "capability_id": "no_quality_issue_evidence",
        "title_ar": "لا دليل على مشكلة جودة",
        "statement_ar": "لا توجد أدلة حالية تدعم وجود مشكلة جودة في المنتج.",
        "recommended_action_ar": "لا حاجة لاتخاذ إجراء حالياً — استمر في جمع الأدلة.",
        "confidence_level": "low",
        "confidence_ar": "منخفض",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # Prefer live projector when importable (keeps confidence from engine thresholds)
    try:
        import sys

        sys.path.insert(0, str(ROOT))
        from services.observation_foundation_v1.merchant_findings_v1 import (
            project_merchant_observation_findings_v1,
        )

        # Minimal correlations mirroring lab DEMO-PERFUME mass
        corrs = [
            {
                "statement_capability": "high_interest_low_conversion",
                "product_key": "DEMO-PERFUME",
                "correlation_kind": "product_interest_conversion_v1",
                "counts": {"cart_add": 2, "purchase": 0},
                "evidence_refs": [{"id": i} for i in range(6)],
            },
            {
                "statement_capability": "shipping_stronger_than_price",
                "product_key": "DEMO-PERFUME",
                "correlation_kind": "reason_strength_compare_v1",
                "compare": {"shipping": 1, "price": 0},
                "evidence_refs": [{"id": i} for i in range(6)],
            },
            {
                "statement_capability": "repeated_return_without_purchase",
                "product_key": "DEMO-PERFUME",
                "correlation_kind": "repeat_return_without_purchase_v1",
                "counts": {"return": 2, "purchase": 0},
                "evidence_refs": [{"id": i} for i in range(6)],
            },
            {
                "statement_capability": "no_quality_issue_evidence",
                "product_key": "DEMO-PERFUME",
                "correlation_kind": "absent_reason_evidence_v1",
                "reason_counts": {"shipping": 1, "thinking": 1},
                "absent_family": "quality",
                "evidence_refs": [{"id": i} for i in range(6)],
            },
        ]
        findings = project_merchant_observation_findings_v1(
            {"correlations": corrs, "store_slug": "demo"}, store_slug="demo"
        )
    except Exception:
        findings = SAMPLE_FINDINGS

    pkg = {
        "ok": True,
        "enabled": True,
        "eyebrow_ar": "معرفة من الملاحظة",
        "title_ar": "ماذا نلاحظ في منتجاتك الآن؟",
        "lede_ar": "ملاحظات قصيرة مبنية على أدلة — مع خطوة مقترحة وثقة واضحة.",
        "findings": findings,
    }

    css = """
    body{font-family:Tahoma,Arial,sans-serif;background:#f3f5f4;margin:0;padding:24px;direction:rtl}
    .shell{max-width:920px;margin:0 auto}
    .orv-surface{padding:14px 16px;border-radius:12px;background:linear-gradient(180deg,#f7faf8 0%,#fff 55%);border:1px solid rgba(31,61,47,.14)}
    .orv-eyebrow{margin:0 0 4px;font-size:11px;font-weight:700;opacity:.7}
    .orv-surface h3{margin:0 0 6px;font-size:18px;line-height:1.35;color:#1f3d2f}
    .orv-lede{margin:0 0 12px;font-size:13px;line-height:1.5;opacity:.8}
    .orv-cards{display:grid;gap:10px}
    .orv-card{padding:12px 14px;border-radius:10px;background:#fff;border:1px solid rgba(53,92,125,.16);border-inline-start:3px solid #2f6f4e}
    .orv-card__head{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px}
    .orv-card__eyebrow{margin:0;font-size:11px;font-weight:700;opacity:.7}
    .orv-conf{display:inline-block;font-size:11px;font-weight:700;padding:3px 8px;border-radius:999px;background:rgba(0,0,0,.06)}
    .orv-conf--high{background:rgba(47,111,78,.12);color:#1f3d2f}
    .orv-conf--medium{background:rgba(140,100,60,.12);color:#5a3d1a}
    .orv-conf--low{background:rgba(0,0,0,.06);color:#444}
    .orv-card__title{margin:0 0 6px;font-size:15px;line-height:1.4;font-weight:700}
    .orv-card__statement{margin:0;font-size:14px;line-height:1.5}
    .orv-card__action{margin:10px 0 0;padding-top:8px;border-top:1px dashed rgba(0,0,0,.08);font-size:13px;line-height:1.5}
    """

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.set_content(
            "<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
            f"<style>{css}</style></head><body><div class='shell'>"
            "<div id='observation-reality-validation-root'></div></div>"
            f"<script>{JS.read_text(encoding='utf-8')}</script></body></html>"
        )
        page.evaluate(
            """(pkg) => window.maApplyObservationRealityValidationV1({
              observation_reality_validation_v1: pkg
            })""",
            pkg,
        )
        page.wait_for_timeout(400)
        desktop = OUT / "03_desktop_orv_ui_polish.png"
        page.screenshot(path=str(desktop), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        mobile = OUT / "04_mobile_orv_ui_polish.png"
        page.screenshot(path=str(mobile), full_page=True)
        probe = page.evaluate(
            """() => {
              const text = document.body.innerText || '';
              const banned = ['cart_add','purchase=','return=','shipping=','price=','evidence_refs','DEMO-PERFUME','product='];
              return {
                cards: document.querySelectorAll('[data-orv-finding]').length,
                actions: document.querySelectorAll('[data-orv-action]').length,
                conf: document.querySelectorAll('[data-orv-confidence]').length,
                banned_visible: banned.filter((b) => text.includes(b)),
                titles: Array.from(document.querySelectorAll('[data-orv-title]')).map(e=>e.textContent.trim()),
              };
            }"""
        )
        browser.close()

    ok = (
        probe.get("cards") == 4
        and probe.get("actions") == 4
        and probe.get("conf") == 4
        and not probe.get("banned_visible")
    )
    report = {
        "task": "Observation Reality Validation V1 — Final UI Polish",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "production_url": "https://smartreplyai.net/dashboard#home",
        "screenshots": {
            "desktop": str(desktop.relative_to(ROOT)),
            "mobile": str(mobile.relative_to(ROOT)),
        },
        "probe": probe,
        "technical_fields_hidden": not probe.get("banned_visible"),
        "every_card_has_statement_action_confidence": ok,
        "ok": ok,
        "status": "AWAITING_PRODUCTION_REVIEW_APPROVAL",
    }
    (OUT / "ui_polish_verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
