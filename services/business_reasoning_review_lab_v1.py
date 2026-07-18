# -*- coding: utf-8 -*-
"""
Business Reasoning Review Lab V1 — Product acceptance presentation.

Maps reasoning cards + merchant guidance briefs to merchant-only cards.
No engines, registries, graphs, contracts, or internal IDs on the surface.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.business_findings_contract_v1 import norm
from services.business_findings_engine_v1 import run_business_findings_engine_v1
from services.business_findings_evidence_v1 import (
    build_demo_rich_evidence_bundle_v1,
    load_evidence_bundle_from_db_v1,
)
from services.business_reasoning_contract_v1 import (
    TYPE_CONFLICT,
    TYPE_CONSTRAINT,
    TYPE_OPPORTUNITY,
    TYPE_PRIORITY,
    TYPE_RELATIONSHIP,
    certainty_label_ar,
    confidence_label_ar,
)
from services.business_reasoning_engine_v1 import run_business_reasoning_engine_v1

# Merchant labels only — never expose internal type keys on the page.
_REASONING_TYPE_AR = {
    TYPE_RELATIONSHIP: "ربط بين ملاحظات",
    TYPE_PRIORITY: "أولوية القرار",
    TYPE_CONFLICT: "تعارض يحتاج حسماً",
    TYPE_CONSTRAINT: "عائق يسبق الباقي",
    TYPE_OPPORTUNITY: "فرصة قابلة للتحسين",
}


def reasoning_type_label_ar(reasoning_type: Any) -> str:
    key = norm(reasoning_type)
    return _REASONING_TYPE_AR.get(key, "استنتاج تجاري")


def reasoning_to_review_card_v1(
    card: Mapping[str, Any], *, index: int
) -> dict[str, Any]:
    """Merchant-facing reasoning card only."""
    supporting = [
        norm(x)
        for x in (card.get("supporting_finding_labels") or [])
        if norm(x)
    ]
    return {
        "card_index": index,
        "headline": norm(card.get("headline")),
        "business_meaning": norm(card.get("business_meaning")),
        "merchant_priority": norm(card.get("recommended_priority")),
        "expected_impact": norm(card.get("expected_impact")),
        "confidence_ar": confidence_label_ar(card.get("confidence_level")),
        "certainty_ar": certainty_label_ar(card.get("certainty")),
        "reasoning_type_ar": reasoning_type_label_ar(card.get("reasoning_type")),
        "supporting_findings": supporting,
        # Stable key for localStorage — not shown as engineering jargon.
        "review_key": norm(card.get("reasoning_id")) or f"card-{index}",
    }


def build_reasoning_review_lab_payload_v1(
    *,
    store_slug: str = "demo",
    source: str = "fixture",
    window_days: int = 14,
) -> dict[str, Any]:
    """
    Build Product Review Lab payload for Business Reasoning.

    Pipeline only:
      Approved Business Findings → Business Reasoning Engine → Merchant Guidance

    source:
      - fixture: findings demo fixture, then reasoning (default for Product review)
      - db: bounded live findings load, then reasoning (falls back if sparse)
    """
    slug = norm(store_slug) or "demo"
    src = norm(source).lower() or "fixture"

    findings_package: Optional[Mapping[str, Any]] = None
    if src == "db":
        try:
            evidence = load_evidence_bundle_from_db_v1(
                store_slug=slug, window_days=window_days
            )
            if int(evidence.hesitation_total or 0) < 3 and len(evidence.products or {}) < 2:
                evidence = build_demo_rich_evidence_bundle_v1(
                    store_slug=slug, window_days=window_days
                )
                src = "fixture_fallback"
            findings_package = run_business_findings_engine_v1(
                store_slug=slug, evidence=evidence, window_days=window_days
            )
        except Exception:  # noqa: BLE001
            findings_package = run_business_findings_engine_v1(
                store_slug=slug, demo_fixture=True, window_days=window_days
            )
            src = "fixture_fallback"
        package = run_business_reasoning_engine_v1(
            store_slug=slug,
            findings_package=findings_package,
            window_days=window_days,
        )
    else:
        package = run_business_reasoning_engine_v1(
            store_slug=slug, demo_fixture=True, window_days=window_days
        )
        src = "fixture"

    cards = [
        reasoning_to_review_card_v1(c, index=i + 1)
        for i, c in enumerate(package.get("reasoning_cards") or [])
        if isinstance(c, Mapping) and norm(c.get("headline"))
    ]
    return {
        "ok": True,
        "lab": "business_reasoning_review_lab_v1",
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
                "صنّف كل استنتاج. الموافقة تتطلب 5 استنتاجات Useful أو Wow على الأقل، "
                "ومنها 3 Wow على الأقل. Wow يعني: ربطاً لم تكن لتصل إليه بنفسك من النتائج منفصلة."
            ),
        },
    }
