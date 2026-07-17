# -*- coding: utf-8 -*-
"""
Merchant Findings Review Lab V1 — Product acceptance presentation.

Maps engine findings to merchant-only cards. No contracts, JSON fields,
or engineering vocabulary on the review surface.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.business_findings_contract_v1 import norm
from services.business_findings_engine_v1 import run_business_findings_engine_v1
from services.business_findings_evidence_v1 import (
    build_demo_rich_evidence_bundle_v1,
    load_evidence_bundle_from_db_v1,
)

_CONF_AR = {
    "high": "مرتفعة",
    "confirmed": "مرتفعة",
    "medium": "متوسطة",
    "low": "منخفضة",
    "insufficient": "غير كافية بعد",
    "unknown": "غير كافية بعد",
}


def confidence_badge_ar(level: Any) -> str:
    key = norm(level).lower()
    return _CONF_AR.get(key, "غير كافية بعد")


def merchant_evidence_lines_ar(finding: Mapping[str, Any]) -> list[str]:
    """Human evidence bullets — never dump raw field dumps as the primary line."""
    lines: list[str] = []
    summary = norm(finding.get("evidence_summary"))
    sample = int(finding.get("sample_size") or 0)
    if sample > 0:
        lines.append(f"حجم الحالات المعتمدة في هذا الاستنتاج: {sample}.")
    # Soften common technical fragments for merchant reading.
    soft = summary
    replacements = (
        ("add_to_cart=", "مرات الإضافة إلى السلة="),
        ("unique_carts=", "سلال فريدة="),
        ("purchases=", "مشتريات="),
        ("store_baseline=", "متوسط المتجر="),
        ("sent=", "رسائل أُرسلت="),
        ("returned=", "عودة="),
        ("purchased=", "شراء="),
        ("failed=", "فشل="),
        ("suppressed=", "موقوف="),
        ("distribution=", "توزيع الأسباب="),
        ("hesitation_total=", "إجمالي أسباب التردد="),
        ("visitor_total=unavailable", "بيانات الزيارات غير متاحة"),
        ("carts_not_used_as_traffic_proxy", "لا نستخدم عدد السلال كبديل عن الزيارات"),
        ("reasons=", "أسباب مسجّلة="),
        ("contacts=", "بيانات تواصل مكتملة="),
        ("unresolved=", "غير محلولة="),
        ("repeat_adds=", "إضافات متكررة="),
        ("revisits=", "عودة متكررة="),
        ("returns=", "حالات عودة="),
        ("without_purchase=", "بدون شراء="),
        ("with_purchase=", "مع شراء="),
        ("wa_sent=", "رسائل واتساب="),
        ("product_atc=", "إضافات المنتج="),
        ("peer_median_atc=", "متوسط منتجات مقارنة="),
        ("top=", "الأبرز="),
        ("compared_against=", "مقارنة مع="),
        ("failed_share=", "نسبة الفشل="),
    )
    for a, b in replacements:
        soft = soft.replace(a, b)
    if soft and soft not in lines:
        lines.append(soft)
    if not lines:
        lines.append("التفاصيل الداعمة محدودة في هذه النافذة.")
    return lines[:6]


def finding_to_review_card_v1(finding: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    """Merchant-facing card only."""
    return {
        "card_index": index,
        "title": norm(finding.get("title")),
        "summary": norm(finding.get("merchant_summary")),
        "why_it_matters": norm(finding.get("commercial_meaning")),
        "next_step": norm(finding.get("recommended_direction")),
        "confidence_ar": confidence_badge_ar(finding.get("confidence_level")),
        "evidence_lines": merchant_evidence_lines_ar(finding),
        # Stable key for localStorage review answers — not shown as engineering jargon.
        "review_key": norm(finding.get("finding_id")) or f"card-{index}",
    }


def build_review_lab_payload_v1(
    *,
    store_slug: str = "demo",
    source: str = "fixture",
    window_days: int = 14,
) -> dict[str, Any]:
    """
    Build Product Review Lab payload.

    source:
      - fixture: demo-rich evidence (default for Product review)
      - db: bounded live store load (when available)
    """
    slug = norm(store_slug) or "demo"
    src = norm(source).lower() or "fixture"
    if src == "db":
        try:
            evidence = load_evidence_bundle_from_db_v1(
                store_slug=slug, window_days=window_days
            )
            # If DB is empty/sparse, fall back so Product always has a reviewable set.
            if int(evidence.hesitation_total or 0) < 3 and len(evidence.products or {}) < 2:
                evidence = build_demo_rich_evidence_bundle_v1(
                    store_slug=slug, window_days=window_days
                )
                src = "fixture_fallback"
        except Exception:  # noqa: BLE001
            evidence = build_demo_rich_evidence_bundle_v1(
                store_slug=slug, window_days=window_days
            )
            src = "fixture_fallback"
        package = run_business_findings_engine_v1(
            store_slug=slug, evidence=evidence, window_days=window_days
        )
    else:
        package = run_business_findings_engine_v1(
            store_slug=slug, demo_fixture=True, window_days=window_days
        )
        src = "fixture"

    findings = list(package.get("findings") or [])
    cards = [
        finding_to_review_card_v1(f, index=i + 1)
        for i, f in enumerate(findings)
        if isinstance(f, Mapping) and norm(f.get("title"))
    ]
    return {
        "ok": True,
        "lab": "merchant_findings_review_lab_v1",
        "store_label_ar": "متجر العرض" if slug == "demo" else slug,
        "source_label_ar": (
            "بيانات العرض المرجعية"
            if src.startswith("fixture")
            else "بيانات المتجر الحالية"
        ),
        "card_count": len(cards),
        "cards": cards,
        "acceptance": {
            "useful_or_wow_needed": 5,
            "wow_needed": 3,
            "instruction_ar": (
                "صنّف كل نتيجة. الموافقة تتطلب 5 نتائج Useful أو Wow على الأقل، "
                "ومنها 3 Wow على الأقل."
            ),
        },
    }
