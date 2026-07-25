# -*- coding: utf-8 -*-
"""
Gate 2E — Business Meaning → Business Impact → Decision Priority.

Operational truth is input. Business understanding is output.
Priority follows business impact domains — never counter size alone.
"""
from __future__ import annotations

from typing import Any, Mapping

# Executive decision ranking (Workspace). Lower index = higher business priority.
BUSINESS_IMPACT_DOMAIN_ORDER_V1 = (
    "revenue",
    "products",
    "pricing",
    "shipping",
    "customer_behaviour",
    "recovery",
    "communication",
    "operations",
    "store_health",
    "configuration",
)

BUSINESS_IMPACT_VERSION_V1 = "business_impact_v1"

# Domain weight: material threat to business performance (0–40).
_DOMAIN_IMPACT_WEIGHT = {
    "revenue": 40,
    "products": 36,
    "pricing": 34,
    "shipping": 32,
    "customer_behaviour": 30,
    "recovery": 26,
    "communication": 18,
    "operations": 14,
    "store_health": 12,
    "configuration": 8,
}

_MEANING_AR = {
    "recovery": "فرص استرجاع الإيرادات تتأثر عندما يتعذّر إكمال مسار المتابعة.",
    "operations": "مسار الاسترجاع يحتاج تدخلاً بشرياً لإبقاء فرص الإتمام مفتوحة.",
    "products": "أداء المنتج يؤثر مباشرة على التحويل والإيراد.",
    "pricing": "التسعير يؤثر على قرار الشراء والإيراد.",
    "shipping": "تكلفة أو تجربة الشحن قد تحد من إتمام الشراء.",
    "customer_behaviour": "سلوك العملاء يكشف فرصة لتحسين التحويل.",
    "communication": "متابعة العملاء محدودة عندما يتعثر مسار التواصل.",
    "revenue": "فرصة إيراد تحتاج قراراً تنفيذياً.",
    "store_health": "حالة المتجر تؤثر على استقرار الأداء التجاري.",
    "configuration": "إعداد ناقص قد يحد من قدرة المتجر على العمل.",
}

_IMPACT_AR = {
    "recovery": "انخفاض فرص استعادة المبيعات المعلّقة.",
    "operations": "تأخر إتمام الشراء في الحالات التي تحتاج تدخلاً.",
    "products": "فرصة تحسين تحويل المنتج أو ضياع اهتمام قائم.",
    "pricing": "أثر محتمل على قرار الشراء والإيراد.",
    "shipping": "أثر محتمل على إتمام الشراء.",
    "customer_behaviour": "فرصة تحسين التحويل من الاهتمام الحالي.",
    "communication": "حدّ من قدرة المتابعة على استعادة العملاء.",
    "revenue": "أثر مباشر على الإيراد.",
    "store_health": "أثر على استقرار تشغيل المتجر تجارياً.",
    "configuration": "أثر على جاهزية القنوات التجارية.",
}


def _norm(v: Any) -> str:
    return str(v or "").strip().lower()


def domain_rank_v1(domain: str) -> int:
    d = _norm(domain)
    try:
        return BUSINESS_IMPACT_DOMAIN_ORDER_V1.index(d)
    except ValueError:
        return len(BUSINESS_IMPACT_DOMAIN_ORDER_V1)


def domain_impact_weight_v1(domain: str) -> int:
    return int(_DOMAIN_IMPACT_WEIGHT.get(_norm(domain), 10))


def business_meaning_ar_v1(domain: str) -> str:
    return _MEANING_AR.get(_norm(domain), "يوجد أمر تجاري يحتاج مراجعة.")


def business_impact_ar_v1(domain: str) -> str:
    return _IMPACT_AR.get(_norm(domain), "أثر تجاري يحتاج تقييماً.")


def attach_business_impact_v1(candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Stamp business meaning + impact before priority finalization.

    Does not invent new decisions — only reframes an existing candidate.
    """
    domain = _norm(
        candidate.get("business_domain")
        or candidate.get("decision_category")
        or "store_health"
    )
    meaning = business_meaning_ar_v1(domain)
    impact = business_impact_ar_v1(domain)
    weight = domain_impact_weight_v1(domain)

    candidate["business_domain"] = domain
    candidate["business_meaning_ar"] = meaning
    candidate["business_impact_ar"] = impact
    candidate["business_impact_weight"] = weight
    candidate["business_impact_rank"] = domain_rank_v1(domain)
    candidate["gate_2e_business_impact"] = True
    candidate["business_impact_version"] = BUSINESS_IMPACT_VERSION_V1

    # Prefer executive decision language already on title; never invent counters.
    title = str(
        candidate.get("merchant_decision") or candidate.get("title") or ""
    ).strip()
    if title:
        candidate["executive_decision_ar"] = title
    return candidate


def apply_business_impact_to_candidates_v1(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [attach_business_impact_v1(dict(c)) for c in candidates]


__all__ = [
    "BUSINESS_IMPACT_DOMAIN_ORDER_V1",
    "BUSINESS_IMPACT_VERSION_V1",
    "apply_business_impact_to_candidates_v1",
    "attach_business_impact_v1",
    "business_impact_ar_v1",
    "business_meaning_ar_v1",
    "domain_impact_weight_v1",
    "domain_rank_v1",
]
