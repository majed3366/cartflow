# -*- coding: utf-8 -*-
"""Commercial Opportunity Layer V1 — priority (internal, explainable)."""
from __future__ import annotations

from typing import Any, Mapping

from services.commercial_opportunity_layer_v1.contract_v1 import (
    FAMILY_COMMUNICATION_FOLLOWUP,
    FAMILY_PRICE_HESITATION,
    FAMILY_PRODUCT_CONFIDENCE,
    FAMILY_RECOVERY_HESITATION,
    FAMILY_SHIPPING_FRICTION,
    TRUTH_PRODUCTION_PARTIAL,
    TRUTH_PRODUCTION_READY,
)

# Commercial weight — not shown raw to merchant.
_FAMILY_WEIGHT = {
    FAMILY_SHIPPING_FRICTION: 90,
    FAMILY_PRICE_HESITATION: 85,
    FAMILY_COMMUNICATION_FOLLOWUP: 80,
    FAMILY_RECOVERY_HESITATION: 70,
    FAMILY_PRODUCT_CONFIDENCE: 75,
}

_TRUTH_WEIGHT = {
    TRUTH_PRODUCTION_READY: 100,
    TRUTH_PRODUCTION_PARTIAL: 40,
}


def score_opportunity_v1(opp: Mapping[str, Any]) -> int:
    fam = str(opp.get("family") or "")
    tc = str(opp.get("truth_class") or "")
    base = int(_FAMILY_WEIGHT.get(fam, 50))
    tw = int(_TRUTH_WEIGHT.get(tc, 0))
    urgency = int(opp.get("_urgency") or 0)
    evidence = int(opp.get("_evidence_strength") or 0)
    return base + tw + min(20, urgency) + min(20, evidence)


def priority_explanation_ar(opp: Mapping[str, Any]) -> str:
    """Merchant-facing commercial explanation — never raw score."""
    fam = str(opp.get("family") or "")
    tc = str(opp.get("truth_class") or "")
    if fam == FAMILY_SHIPPING_FRICTION:
        core = "احتكاك الشحن يقطع الشراء قبل الدفع."
    elif fam == FAMILY_PRICE_HESITATION:
        core = "تردّد السعر متكرر — الخصم غير مثبت كحل."
    elif fam == FAMILY_COMMUNICATION_FOLLOWUP:
        core = "بلا تواصل صالح لا تُنفَّذ متابعة استرجاع."
    elif fam == FAMILY_PRODUCT_CONFIDENCE:
        core = "ضعف ثقة المنتج يظهر كتردّد متكرر."
    elif fam == FAMILY_RECOVERY_HESITATION:
        core = "تردّد قبل الشراء — المتابعة قابلة للتحسين."
    else:
        core = "فرصة من سلوك شراء مسجّل في متجرك."
    if tc == TRUTH_PRODUCTION_PARTIAL:
        return core + " أدلة جزئية."
    return core


__all__ = ["priority_explanation_ar", "score_opportunity_v1"]
