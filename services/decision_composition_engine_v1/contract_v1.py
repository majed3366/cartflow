# -*- coding: utf-8 -*-
"""Canonical Decision Composition Contract V1."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

COMPOSITION_VERSION_V1 = "decision_composition_engine_v1"
GENERIC_PRODUCT_BANNED = ("هذا المنتج", "this product", "المنتج هذا")

REQUIRED_PUBLISH_FIELDS = (
    "decision_id",
    "store_slug",
    "decision_type",
    "decision_subject_type",
    "title",
    "merchant_decision",
    "why",
    "why_now",
    "evidence_summary",
    "ignore_consequence",
    "recommended_action",
    "first_step",
    "expected_outcome",
    "confidence",
    "priority",
    "source_truth_types",
    "generated_at",
    "composition_version",
)

DECISION_TYPE_RECOVERABILITY_GAP = "recoverability_gap"
DECISION_TYPE_WAITING_RECOVERY = "waiting_recovery_work"
DECISION_TYPE_VERIFIED_FINDING = "verified_existing_finding"

BAND_NEEDS_ACTION = "needs_action_now"
BAND_MONITOR = "monitor"
BAND_NONE = "no_decision_supported"

SUPPRESS_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
SUPPRESS_CONFLICTING_EVIDENCE = "conflicting_evidence"
SUPPRESS_SUBJECT_UNIDENTIFIED = "subject_unidentified"
SUPPRESS_ACTION_UNSUPPORTED = "action_unsupported"
SUPPRESS_STALE = "stale_finding"
SUPPRESS_DUPLICATE = "duplicate_decision"
SUPPRESS_NORMAL_STATE = "normal_state_no_merchant_action"
SUPPRESS_GENERIC_PRODUCT = "generic_product_language"
SUPPRESS_CONTRACT_INCOMPLETE = "contract_incomplete"
SUPPRESS_COUNTER_ONLY = "raw_counter_not_a_decision"


def _norm(v: Any) -> str:
    return str(v or "").strip()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_valid_until(*, hours: int = 24) -> str:
    return (
        datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=hours)
    ).isoformat()


def contains_generic_product_language(*texts: str) -> bool:
    blob = " ".join(_norm(t).lower() for t in texts)
    return any(tok in blob for tok in GENERIC_PRODUCT_BANNED)


def confidence_ar(level: str) -> str:
    raw = _norm(level).lower()
    if raw in {"high", "مرتفع", "strong"}:
        return "مرتفع"
    if raw in {"medium", "متوسط", "moderate"}:
        return "متوسط"
    if raw in {"low", "منخفض", "weak"}:
        return "منخفض"
    return ""


def new_candidate(**fields: Any) -> dict[str, Any]:
    """Build a candidate shell with required defaults."""
    now = utc_now_iso()
    base: dict[str, Any] = {
        "decision_id": "",
        "store_slug": "",
        "decision_type": "",
        "decision_subject_type": "store",
        "decision_subject_id": "",
        "title": "",
        "merchant_decision": "",
        "why": "",
        "why_now": "",
        "evidence_summary": "",
        "evidence_refs": [],
        "ignore_consequence": "",
        "recommended_action": "",
        "first_step": "",
        "expected_outcome": "",
        "confidence": "",
        "priority": 0,
        "priority_band": BAND_NONE,
        "source_truth_types": [],
        "generated_at": now,
        "valid_until": default_valid_until(),
        "composition_version": COMPOSITION_VERSION_V1,
        "published": False,
        "suppressed": False,
        "suppression_reason": "",
    }
    base.update(fields)
    return base


def validate_publish_contract(candidate: Mapping[str, Any]) -> tuple[bool, str]:
    """Return (ok, reason). Fail closed — missing required field suppresses."""
    if not isinstance(candidate, Mapping):
        return False, SUPPRESS_CONTRACT_INCOMPLETE
    for key in REQUIRED_PUBLISH_FIELDS:
        val = candidate.get(key)
        if val is None:
            return False, SUPPRESS_CONTRACT_INCOMPLETE
        if key == "priority":
            try:
                int(val)
            except (TypeError, ValueError):
                return False, SUPPRESS_CONTRACT_INCOMPLETE
            continue
        if key == "source_truth_types":
            if not isinstance(val, (list, tuple)) or not val:
                return False, SUPPRESS_CONTRACT_INCOMPLETE
            continue
        if key == "decision_subject_id":
            # Optional for store-level; required for product subject.
            continue
        if not _norm(val) and key not in {"decision_subject_id"}:
            return False, SUPPRESS_CONTRACT_INCOMPLETE

    subject_type = _norm(candidate.get("decision_subject_type")).lower()
    if subject_type == "product":
        sid = _norm(candidate.get("decision_subject_id"))
        title = _norm(candidate.get("title"))
        decision = _norm(candidate.get("merchant_decision"))
        if not sid:
            return False, SUPPRESS_SUBJECT_UNIDENTIFIED
        if contains_generic_product_language(title, decision, _norm(candidate.get("why"))):
            return False, SUPPRESS_GENERIC_PRODUCT

    conf = _norm(candidate.get("confidence")).lower()
    if conf in {"", "none", "unknown"}:
        return False, SUPPRESS_INSUFFICIENT_EVIDENCE

    if not _norm(candidate.get("recommended_action")) or not _norm(
        candidate.get("first_step")
    ):
        return False, SUPPRESS_ACTION_UNSUPPORTED

    return True, ""


__all__ = [
    "BAND_MONITOR",
    "BAND_NEEDS_ACTION",
    "BAND_NONE",
    "COMPOSITION_VERSION_V1",
    "DECISION_TYPE_RECOVERABILITY_GAP",
    "DECISION_TYPE_VERIFIED_FINDING",
    "DECISION_TYPE_WAITING_RECOVERY",
    "REQUIRED_PUBLISH_FIELDS",
    "SUPPRESS_ACTION_UNSUPPORTED",
    "SUPPRESS_CONFLICTING_EVIDENCE",
    "SUPPRESS_CONTRACT_INCOMPLETE",
    "SUPPRESS_COUNTER_ONLY",
    "SUPPRESS_DUPLICATE",
    "SUPPRESS_GENERIC_PRODUCT",
    "SUPPRESS_INSUFFICIENT_EVIDENCE",
    "SUPPRESS_NORMAL_STATE",
    "SUPPRESS_STALE",
    "SUPPRESS_SUBJECT_UNIDENTIFIED",
    "confidence_ar",
    "contains_generic_product_language",
    "new_candidate",
    "utc_now_iso",
    "validate_publish_contract",
]
