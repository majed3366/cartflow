# -*- coding: utf-8 -*-
"""
Decision Workspace V2 budget — Information Budget + Cards Constitution.

- Exactly one Primary Decision
- ≤3 Next Decisions
- No KPI landscape / band counts in paint payload
- Card fields: Diagnosis → Reasoning → Evidence → Consequence → Commitment → Outcome
"""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_workspace_v2.flag_v1 import decision_workspace_v2_enabled

MAX_NEXT_DECISIONS_V2 = 3

_SOFT_OPENERS = (
    "راجع",
    "حسّن",
    "حسن",
    "تحقق",
    "فكّر",
    "فكر",
    "review",
    "improve",
    "check",
    "consider",
)


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _is_constitution_card(card: Mapping[str, Any]) -> bool:
    if card.get("constitution_v1") or card.get("gate_2b_composition") or card.get(
        "gate_commerce_situations"
    ):
        return True
    kind = _norm(card.get("card_kind"))
    return kind in {
        "business_finding",
        "operational_truth",
        "composed_decision",
        "commerce_situation",
    }


def _looks_like_soft_opener(text: str) -> bool:
    t = _norm(text).casefold()
    if not t:
        return False
    for p in _SOFT_OPENERS:
        if t.startswith(p.casefold()):
            return True
    return False


def _evidence_text(card: Mapping[str, Any]) -> str:
    ev = _norm(card.get("evidence_summary"))
    if ev:
        return ev
    facts = card.get("supporting_facts_ar")
    if isinstance(facts, list):
        parts = [_norm(x) for x in facts if _norm(x)]
        if parts:
            return " · ".join(parts[:5])
    if card.get("has_decision") is False:
        return "لا توجد أدلة كافية لإصدار قرار."
    return ""


def _diagnosis_text(card: Mapping[str, Any]) -> str:
    for key in (
        "diagnosis_ar",
        "business_meaning_ar",
        "situation_summary_ar",
        "observation_ar",
    ):
        v = _norm(card.get(key))
        if v and not _looks_like_soft_opener(v):
            return v
    subject = _norm(
        card.get("subject_ar")
        or card.get("affected_area_ar")
        or card.get("product_name_ar")
    )
    why = _norm(card.get("why_ar") or (card.get("explanation") or {}).get("why_here"))
    if subject and why:
        return f"{subject}: {why}" if not why.startswith(subject) else why
    if why and not _looks_like_soft_opener(why):
        return why
    if subject:
        return f"هناك قرار مطلوب بخصوص {subject}."
    decision = _norm(
        card.get("decision_ar") or card.get("title_ar") or card.get("merchant_decision")
    )
    if decision and not _looks_like_soft_opener(decision):
        # Prefer not to use pure action text as diagnosis when commitment matches.
        commitment = _norm(
            card.get("commitment_ar")
            or card.get("first_step_ar")
            or card.get("required_merchant_action")
        )
        if commitment and decision == commitment:
            return "هناك موقف تجاري يحتاج قرارك الآن."
        return decision
    return "هناك موقف تجاري يحتاج قرارك الآن."


def _reasoning_text(card: Mapping[str, Any], diagnosis: str) -> str:
    why = _norm(card.get("why_ar") or (card.get("explanation") or {}).get("why_here"))
    why_now = _norm(card.get("why_now_ar"))
    # Prefer why; use why_now only when it adds distinct belief (not Home repeat).
    if why and why != diagnosis:
        return why
    if why_now and why_now != diagnosis and why_now != why:
        return why_now
    if why:
        return why
    return "CartFlow يرى هذا الموقف بناءً على ملاحظات المتجر الحالية."


def _consequence_text(card: Mapping[str, Any]) -> str:
    for key in (
        "ignore_consequence_ar",
        "business_consequence_ar",
        "business_impact_ar",
        "expected_business_impact",
    ):
        v = _norm(card.get(key))
        if v:
            return v
    return "إذا لم يُتخذ قرار، قد يستمر التأثير على المتجر دون معالجة واضحة."


def _commitment_text(card: Mapping[str, Any]) -> str:
    for key in (
        "commitment_ar",
        "first_step_ar",
        "required_merchant_action",
        "action_label_ar",
        "recommended_action",
    ):
        v = _norm(card.get(key))
        if v:
            return v
    if card.get("has_decision") is False:
        return "انتظر حتى تتوفر أدلة كافية — لا تلتزم بإجراء غير مدعوم."
    return "حدّد إجراءً واحداً واضحاً بناءً على التشخيص."


def _outcome_text(card: Mapping[str, Any]) -> str:
    for key in ("expected_outcome_ar", "expected_business_impact"):
        v = _norm(card.get(key))
        if v:
            return v
    ex = card.get("explanation") if isinstance(card.get("explanation"), Mapping) else {}
    return _norm(ex.get("expected_after")) or "بعد الالتزام، يصبح الإجراء التالي واضحاً وقابلاً للتنفيذ."


def _destination_href(card: Mapping[str, Any]) -> str:
    href = _norm(card.get("view_details_href"))
    if href:
        return href
    domain = _norm(card.get("business_domain") or card.get("decision_category")).casefold()
    if "product" in domain or "منتج" in domain:
        return "#products"
    if "communicat" in domain or "تواصل" in domain or "whatsapp" in domain:
        return "#communication"
    if "cart" in domain or "recover" in domain or "سلّ" in domain or "سلال" in domain:
        return "#carts"
    if "ship" in domain or "شحن" in domain or "pricing" in domain or "سعر" in domain:
        return "#products"
    return "#products"


def hydrate_decision_card_v2(card: dict[str, Any], *, is_primary: bool) -> dict[str, Any]:
    """Stamp constitutional face fields; preserve underlying ids."""
    out = dict(card)
    diagnosis = _diagnosis_text(out)
    commitment = _commitment_text(out)
    out["diagnosis_ar"] = diagnosis
    out["reasoning_ar"] = _reasoning_text(out, diagnosis)
    out["evidence_summary"] = _evidence_text(out) or "لا توجد أدلة كافية لإصدار قرار."
    out["ignore_consequence_ar"] = _consequence_text(out)
    out["business_consequence_ar"] = out["ignore_consequence_ar"]
    out["commitment_ar"] = commitment
    out["first_step_ar"] = commitment
    out["required_merchant_action"] = commitment
    out["expected_outcome_ar"] = _outcome_text(out)
    out["decision_workspace_v2"] = True
    out["is_primary_decision"] = bool(is_primary)
    if is_primary:
        out["priority_rank_label_ar"] = "القرار الذي تلتزم به الآن"
        out["priority_rank_role"] = "primary"
    else:
        out["priority_rank_label_ar"] = "القرار التالي"
        out["priority_rank_role"] = "next"
    href = _destination_href(out)
    out["view_details_href"] = href
    out["view_details_ar"] = "تنفيذ الالتزام"
    # Do not keep action text as the leading diagnosis fields.
    if _norm(out.get("decision_ar")) == commitment:
        out["decision_ar"] = diagnosis
    if _norm(out.get("title_ar")) == commitment:
        out["title_ar"] = diagnosis
    if _norm(out.get("merchant_decision")) == commitment:
        out["merchant_decision"] = diagnosis
    return out


def apply_decision_workspace_v2_budget(
    projection: dict[str, Any] | None,
) -> dict[str, Any]:
    """Enforce 1 Primary + ≤3 Next; strip KPI chrome from paint payload."""
    if not isinstance(projection, dict):
        return {}
    if not decision_workspace_v2_enabled():
        return projection

    zone_b = [c for c in list(projection.get("zone_b") or []) if isinstance(c, dict)]
    zone_a = [c for c in list(projection.get("zone_a") or []) if isinstance(c, dict)]

    constitution = [c for c in zone_b if _is_constitution_card(c)]
    if not constitution:
        # Fall back to any zone_b / zone_a business-ish cards.
        constitution = list(zone_b) or list(zone_a)

    primary: dict[str, Any] | None = None
    rest: list[dict[str, Any]] = []
    for c in constitution:
        if c.get("is_primary_decision") and primary is None:
            primary = c
        else:
            rest.append(c)
    if primary is None and constitution:
        primary = constitution[0]
        rest = constitution[1:]

    next_cards = rest[:MAX_NEXT_DECISIONS_V2]
    painted: list[dict[str, Any]] = []
    if primary is not None:
        painted.append(hydrate_decision_card_v2(primary, is_primary=True))
    for c in next_cards:
        painted.append(hydrate_decision_card_v2(c, is_primary=False))

    projection["zone_a"] = []
    projection["zone_b"] = painted
    projection["quiet"] = not painted
    if painted:
        projection["attention_focus_decision_id"] = painted[0].get("decision_id")
    else:
        projection["attention_focus_decision_id"] = None

    projection["mission_question"] = "ما القرار الذي يجب أن أتخذه الآن، ولماذا؟"
    projection["decision_workspace_v2"] = True
    projection["decision_workspace_v2_budget"] = {
        "primary": 1 if painted else 0,
        "next": max(0, len(painted) - 1),
        "max_next": MAX_NEXT_DECISIONS_V2,
        "future_waiting": max(0, len(rest) - MAX_NEXT_DECISIONS_V2),
    }

    # Strip KPI / report chrome from composition paint helpers.
    comp = projection.get("decision_composition_v1")
    if isinstance(comp, dict):
        comp = dict(comp)
        comp["category_landscape"] = []
        comp["needs_action_now"] = 1 if painted else 0
        comp["monitor"] = 0
        projection["decision_composition_v1"] = comp
    else:
        projection["decision_composition_v1"] = {
            "category_landscape": [],
            "needs_action_now": 1 if painted else 0,
            "monitor": 0,
        }

    return projection


__all__ = [
    "MAX_NEXT_DECISIONS_V2",
    "apply_decision_workspace_v2_budget",
    "hydrate_decision_card_v2",
]
