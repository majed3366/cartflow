# -*- coding: utf-8 -*-
"""
BusinessReasoningV1 — canonical governed reasoning contract.

Reasoning connects validated Business Findings only.
It never creates facts, never reads raw evidence, never uses AI.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from services.business_findings_contract_v1 import (
    CONFIDENCE_HIGH,
    CONFIDENCE_INSUFFICIENT,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    is_merchant_worthy,
    norm,
)

REASONING_VERSION = "v1"
ENGINE_VERSION = "business_reasoning_engine_v1"

# Reasoning categories (internal keys — never show these to merchants)
TYPE_RELATIONSHIP = "finding_relationship_v1"
TYPE_PRIORITY = "priority_detection_v1"
TYPE_CONFLICT = "conflict_detection_v1"
TYPE_CONSTRAINT = "constraint_detection_v1"
TYPE_OPPORTUNITY = "opportunity_detection_v1"

CERTAINTY_OBSERVED = "observed"
CERTAINTY_LIKELY = "likely"
CERTAINTY_UNKNOWN = "unknown"

# Merchant-facing certainty labels (Arabic)
CERTAINTY_AR = {
    CERTAINTY_OBSERVED: "ملاحظ",
    CERTAINTY_LIKELY: "مرجّح",
    CERTAINTY_UNKNOWN: "غير محسوم بعد",
}

CONFIDENCE_AR = {
    CONFIDENCE_HIGH: "مرتفعة",
    CONFIDENCE_MEDIUM: "متوسطة",
    CONFIDENCE_LOW: "منخفضة",
    CONFIDENCE_INSUFFICIENT: "غير كافية بعد",
}

# Banned engineering vocabulary in merchant-facing strings
_BANNED_MERCHANT_TERMS = (
    "finding",
    "pattern",
    "correlation",
    "businessfinding",
    "engine",
    "reasoning",
    "registry",
    "confidence model",
    "finding_id",
    "family_key",
    "businessfindingv1",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def confidence_label_ar(level: Any) -> str:
    return CONFIDENCE_AR.get(norm(level).lower(), "غير كافية بعد")


def certainty_label_ar(level: Any) -> str:
    return CERTAINTY_AR.get(norm(level).lower(), CERTAINTY_AR[CERTAINTY_UNKNOWN])


def merchant_text_is_clean(text: Any) -> bool:
    blob = norm(text).lower()
    if not blob:
        return False
    return not any(term in blob for term in _BANNED_MERCHANT_TERMS)


def empty_reasoning(
    *,
    reasoning_id: str,
    store_slug: str,
    reasoning_type: str,
) -> dict[str, Any]:
    now = utc_now_iso()
    return {
        "reasoning_id": reasoning_id,
        "store_slug": norm(store_slug),
        "reasoning_type": reasoning_type,
        "headline": "",
        "business_meaning": "",
        "recommended_priority": "",
        "expected_impact": "",
        "confidence_level": CONFIDENCE_INSUFFICIENT,
        "confidence_score": 0.0,
        "certainty": CERTAINTY_UNKNOWN,
        "supporting_finding_ids": [],
        "supporting_finding_labels": [],
        "quality_gates": {
            "multiple_findings": False,
            "creates_business_decision": False,
            "merchant_can_act_today": False,
            "removal_reduces_value": False,
            "passed": False,
        },
        "first_detected_at": now,
        "last_confirmed_at": now,
        "reasoning_version": REASONING_VERSION,
        "source_version": ENGINE_VERSION,
        "source_findings_engine": "business_findings_engine_v1",
        "rank_score": 0.0,
        "ai_used": False,
        "probabilistic": False,
        "invented_evidence": False,
    }


def evaluate_quality_gates_v1(
    *,
    supporting_finding_ids: Sequence[str],
    creates_business_decision: bool,
    merchant_can_act_today: bool,
    removal_reduces_value: bool = True,
) -> dict[str, Any]:
    """All four gates must pass for a reasoning card to ship."""
    multiple = len([x for x in supporting_finding_ids if norm(x)]) >= 2
    gates = {
        "multiple_findings": multiple,
        "creates_business_decision": bool(creates_business_decision),
        "merchant_can_act_today": bool(merchant_can_act_today),
        "removal_reduces_value": bool(removal_reduces_value),
    }
    gates["passed"] = all(
        (
            gates["multiple_findings"],
            gates["creates_business_decision"],
            gates["merchant_can_act_today"],
            gates["removal_reduces_value"],
        )
    )
    return gates


def finalize_reasoning(card: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize and freeze safety flags."""
    base = empty_reasoning(
        reasoning_id=norm(card.get("reasoning_id")) or "reasoning:unknown",
        store_slug=norm(card.get("store_slug")),
        reasoning_type=norm(card.get("reasoning_type")) or "unknown",
    )
    out = dict(base)
    for key in base:
        if key in card and card[key] is not None:
            out[key] = card[key]
    out["reasoning_id"] = norm(out["reasoning_id"])
    out["store_slug"] = norm(out["store_slug"])
    out["supporting_finding_ids"] = [
        norm(x) for x in (out.get("supporting_finding_ids") or []) if norm(x)
    ]
    out["supporting_finding_labels"] = [
        norm(x) for x in (out.get("supporting_finding_labels") or []) if norm(x)
    ]
    try:
        out["confidence_score"] = round(float(out.get("confidence_score") or 0.0), 3)
    except (TypeError, ValueError):
        out["confidence_score"] = 0.0
    try:
        out["rank_score"] = round(float(out.get("rank_score") or 0.0), 3)
    except (TypeError, ValueError):
        out["rank_score"] = 0.0
    gates = out.get("quality_gates") or {}
    if not isinstance(gates, dict) or "passed" not in gates:
        out["quality_gates"] = evaluate_quality_gates_v1(
            supporting_finding_ids=out["supporting_finding_ids"],
            creates_business_decision=bool(gates.get("creates_business_decision", True)),
            merchant_can_act_today=bool(gates.get("merchant_can_act_today", True)),
            removal_reduces_value=bool(gates.get("removal_reduces_value", True)),
        )
    out["ai_used"] = False
    out["probabilistic"] = False
    out["invented_evidence"] = False
    out["reasoning_version"] = REASONING_VERSION
    out["source_version"] = ENGINE_VERSION
    return out


def is_reasoning_worthy(card: Mapping[str, Any]) -> bool:
    """Merchant-facing completeness + quality gates + clean language."""
    if not merchant_text_is_clean(card.get("headline")):
        return False
    if not merchant_text_is_clean(card.get("business_meaning")):
        return False
    if not merchant_text_is_clean(card.get("recommended_priority")):
        return False
    if not merchant_text_is_clean(card.get("expected_impact")):
        return False
    gates = card.get("quality_gates") or {}
    if not gates.get("passed"):
        return False
    if len(card.get("supporting_finding_ids") or []) < 2:
        return False
    return True


def select_approved_findings_v1(findings: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """
    Reasoning may consume only merchant-worthy findings from the Findings Engine.

    V1 treats engine-produced merchant-worthy findings as the approval boundary.
    Product may later narrow this set; the engine must never read evidence/truth.
    """
    out: list[dict[str, Any]] = []
    for raw in findings or []:
        if not isinstance(raw, Mapping):
            continue
        f = dict(raw)
        if not is_merchant_worthy(f):
            continue
        if not norm(f.get("finding_id")):
            continue
        if not norm(f.get("title")):
            continue
        out.append(f)
    return out
