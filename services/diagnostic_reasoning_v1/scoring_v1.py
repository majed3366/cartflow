# -*- coding: utf-8 -*-
"""
Evidence scoring V1 — deterministic, explainable.

Raw event counts alone never select a diagnosis.
Tie within margin → conflicting_evidence.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.diagnostic_reasoning_v1.cause_registry_v1 import causes_for_family_v1
from services.diagnostic_reasoning_v1.contract_v1 import (
    CONFIDENCE_HIGH,
    CONFIDENCE_INSUFFICIENT,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    DIAGNOSIS_STATUS_CONFLICTING,
    DIAGNOSIS_STATUS_INSUFFICIENT,
    DIAGNOSIS_STATUS_SUPPORTED,
)

# Selection margin: if top two causal scores are within this absolute gap → conflict.
TIE_MARGIN_V1 = 2.0
# Weak (generic) signals never alone satisfy a subtype cause.
WEAK_SIGNAL_WEIGHT = 0.35
STRONG_SIGNAL_WEIGHT = 1.0
CONTRADICT_WEIGHT = 0.9
DIVERSITY_BONUS = 0.5
RECURRENCE_BONUS = 0.25
IDENTITY_BONUS = 0.5


def _signal_count(bag: Mapping[str, Any], key: str) -> int:
    signals = bag.get("signals") if isinstance(bag.get("signals"), Mapping) else {}
    try:
        return max(0, int(signals.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def score_cause_v1(
    cause: Mapping[str, Any],
    *,
    evidence_bag: Mapping[str, Any],
) -> dict[str, Any]:
    """Score one candidate cause against a bounded evidence bag."""
    support_n = 0
    weak_n = 0
    for sig in list(cause.get("supporting_signals") or []):
        support_n += _signal_count(evidence_bag, str(sig))
    for sig in list(cause.get("weak_supporting_signals") or []):
        weak_n += _signal_count(evidence_bag, str(sig))
    contradict_n = 0
    for sig in list(cause.get("contradicting_signals") or []):
        contradict_n += _signal_count(evidence_bag, str(sig))

    diversity = 0
    for sig in list(cause.get("supporting_signals") or []) + list(
        cause.get("weak_supporting_signals") or []
    ):
        if _signal_count(evidence_bag, str(sig)) > 0:
            diversity += 1

    recurrence = int(evidence_bag.get("recurrence_days") or 0)
    has_identity = bool(evidence_bag.get("product_identity_ok"))
    identity_required = bool(cause.get("identity_required"))

    score = (
        support_n * STRONG_SIGNAL_WEIGHT
        + weak_n * WEAK_SIGNAL_WEIGHT
        - contradict_n * CONTRADICT_WEIGHT
    )
    if diversity >= 2:
        score += DIVERSITY_BONUS
    if recurrence >= 2:
        score += RECURRENCE_BONUS
    if has_identity and identity_required:
        score += IDENTITY_BONUS
    if identity_required and not has_identity:
        score -= 1.0

    min_ev = int(cause.get("minimum_evidence") or 0)
    # Strong support must meet minimum; weak-only never qualifies a subtype.
    meets_minimum = support_n >= min_ev if min_ev > 0 else True
    subtype = str(cause.get("cause_key") or "") != "insufficient_evidence"
    if subtype and support_n <= 0:
        meets_minimum = False

    return {
        "cause_key": cause.get("cause_key"),
        "score": round(score, 3),
        "support_n": support_n,
        "weak_n": weak_n,
        "contradict_n": contradict_n,
        "diversity": diversity,
        "meets_minimum": meets_minimum,
        "safe_recommendation_ar": cause.get("safe_recommendation_ar") or "",
    }


def select_diagnosis_v1(
    family: str,
    *,
    evidence_bag: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Evaluate all competing causes. Never pick arbitrarily.

    Returns selection payload with status + confidence.
    """
    scored = [
        score_cause_v1(c, evidence_bag=evidence_bag)
        for c in causes_for_family_v1(family)
    ]
    causal = [
        s
        for s in scored
        if s.get("cause_key") != "insufficient_evidence" and s.get("meets_minimum")
    ]
    causal_sorted = sorted(
        causal,
        key=lambda s: (-float(s.get("score") or 0), str(s.get("cause_key") or "")),
    )

    sample_n = int(evidence_bag.get("sample_n") or 0)
    min_sample = int(evidence_bag.get("minimum_sample") or 3)

    if sample_n < min_sample and not causal_sorted:
        return {
            "selected_diagnosis": "insufficient_evidence",
            "diagnosis_status": DIAGNOSIS_STATUS_INSUFFICIENT,
            "confidence_level": CONFIDENCE_INSUFFICIENT,
            "confidence_reason": "insufficient_sample",
            "candidate_scores": scored,
            "recommendation_cause": "insufficient_evidence",
        }

    if not causal_sorted:
        return {
            "selected_diagnosis": "insufficient_evidence",
            "diagnosis_status": DIAGNOSIS_STATUS_INSUFFICIENT,
            "confidence_level": CONFIDENCE_INSUFFICIENT,
            "confidence_reason": "no_distinguishing_evidence",
            "candidate_scores": scored,
            "recommendation_cause": "insufficient_evidence",
        }

    top = causal_sorted[0]
    second = causal_sorted[1] if len(causal_sorted) > 1 else None
    if second is not None:
        gap = float(top["score"]) - float(second["score"])
        if gap <= TIE_MARGIN_V1 and float(second["score"]) > 0:
            return {
                "selected_diagnosis": None,
                "diagnosis_status": DIAGNOSIS_STATUS_CONFLICTING,
                "confidence_level": CONFIDENCE_LOW,
                "confidence_reason": "tie_within_margin",
                "candidate_scores": scored,
                "recommendation_cause": "insufficient_evidence",
                "tied_causes": [top["cause_key"], second["cause_key"]],
            }

    # Confidence from support vs contradict + sample.
    support = int(top.get("support_n") or 0)
    contradict = int(top.get("contradict_n") or 0)
    if support >= 8 and contradict == 0 and sample_n >= 8:
        conf = CONFIDENCE_HIGH
    elif support >= 3 and contradict <= 1:
        conf = CONFIDENCE_MEDIUM
    else:
        conf = CONFIDENCE_LOW

    return {
        "selected_diagnosis": top["cause_key"],
        "diagnosis_status": DIAGNOSIS_STATUS_SUPPORTED,
        "confidence_level": conf,
        "confidence_reason": "top_cause_distinguished",
        "candidate_scores": scored,
        "recommendation_cause": top["cause_key"],
        "top_score": top,
    }


__all__ = [
    "TIE_MARGIN_V1",
    "score_cause_v1",
    "select_diagnosis_v1",
]
