# -*- coding: utf-8 -*-
"""
Merchant Insight Layer V1 — meaning before evidence.

Transforms existing platform truths into operational understanding.
Never invents, predicts, or replaces Truth.

Stack position:
  Truth → MI → Value → Product Language → **Insight Layer** → UI
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Optional, TypedDict

from services.merchant_insight_layer_templates import (
    CARTS_ACTION_ALL_MERCHANT_NEXT_STEP,
    CARTS_ACTION_HOLDING,
    CARTS_ACTION_MONITORING_REPLIES,
    CARTS_ACTION_OBSERVING,
    CARTS_ACTION_WAITING_DECISION,
    CARTS_INSIGHT_ALL_NEED_MERCHANT,
    CARTS_INSIGHT_AUTOMATIC_UNDERWAY,
    CARTS_INSIGHT_MONITORING_EMPTY,
    CARTS_INSIGHT_NO_ACTION,
    CARTS_INSIGHT_ONE_NEEDS_MERCHANT,
    CARTS_INSIGHT_SOME_NEED_MERCHANT,
    CARTS_REASON_ALL_INTERVENTION,
    CARTS_REASON_AUTOMATIC,
    CARTS_REASON_CALM,
    CARTS_REASON_MONITORING,
    CARTS_REASON_ONE_INTERVENTION,
    CARTS_REASON_PARTIAL_INTERVENTION,
    GENERIC_ACTION_MONITORING,
    GENERIC_INSIGHT_MONITORING,
    GENERIC_REASON_INSUFFICIENT,
    HOME_ACTION_ROUTINE,
    HOME_INSIGHT_NEEDS_LOOK,
    HOME_INSIGHT_NO_URGENCY,
    HOME_REASON_ATTENTION,
    HOME_REASON_CALM,
    INSIGHT_ATTENTION,
    INSIGHT_AUTOMATIC_PROGRESS,
    INSIGHT_HEALTHY,
    INSIGHT_MERCHANT_REQUIRED,
    INSIGHT_MONITORING_ONLY,
    INSIGHT_TYPE_LABEL_AR,
)
from services.merchant_product_language_v1 import build_carts_page_evidence_v1

INSIGHT_VERSION = "v1"
AUTHORITY = "merchant_insight_layer_v1"

VALID_PAGE_KEYS = frozenset(
    {"home", "carts", "messages", "whatsapp", "widget", "settings", "plans"}
)

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCE_INSUFFICIENT = "insufficient"


class EvidenceSummary(TypedDict, total=False):
    monitored_count: int
    attention_count: int
    automatic_count: int
    needs_review_count: int
    story_count: int
    group_count: int


class PageInsightPayload(TypedDict):
    version: str
    authority: str
    page_key: str
    insight_type: str
    insight_type_label_ar: str
    primary_insight: str
    reason: str
    cartflow_action: str
    evidence_summary: EvidenceSummary
    source_refs: list[str]
    confidence: str
    composition_order: list[str]


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _refs(*keys: str) -> list[str]:
    return sorted({_norm(k) for k in keys if _norm(k)})


def _confidence_from_evidence(evidence: Mapping[str, Any], *, min_fields: int = 1) -> str:
    supplied = [k for k in evidence.keys() if not str(k).startswith("_")]
    if len(supplied) < min_fields:
        return CONFIDENCE_INSUFFICIENT
    if evidence.get("has_sufficient_evidence") is False:
        return CONFIDENCE_INSUFFICIENT
    if _int(evidence.get("monitored_count")) > 0 or evidence.get("attention_count") is not None:
        return CONFIDENCE_HIGH
    if evidence.get("channel_ready") is not None or evidence.get("setup_complete") is not None:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def build_page_insight_evidence_v1(
    page_key: str,
    payload: Mapping[str, Any],
    rows: Optional[Iterable[Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    """Build explicit insight evidence from existing dashboard payload (no minting)."""
    key = _norm(page_key).lower()
    if key == "carts":
        return build_carts_page_evidence_v1(payload, rows)
    return dict(payload.get("insight_evidence") or {})


def _carts_evidence_summary(evidence: Mapping[str, Any]) -> EvidenceSummary:
    summary: EvidenceSummary = {}
    for field in ("monitored_count", "attention_count", "automatic_count"):
        if evidence.get(field) is not None:
            summary[field] = _int(evidence.get(field))  # type: ignore[literal-required]
    return summary


def _classify_carts_insight_type(evidence: Mapping[str, Any]) -> str:
    monitored = _int(evidence.get("monitored_count"))
    attention = _int(evidence.get("attention_count"))
    automatic = _int(evidence.get("automatic_count"))

    if monitored <= 0:
        return INSIGHT_MONITORING_ONLY
    if attention <= 0:
        if automatic > 0:
            return INSIGHT_AUTOMATIC_PROGRESS
        return INSIGHT_HEALTHY
    if attention >= monitored:
        return INSIGHT_MERCHANT_REQUIRED
    return INSIGHT_ATTENTION


def compose_carts_insight_v1(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Carts page — meaning-first insight (Insight → Reason → Action → Evidence summary)."""
    if not evidence.get("has_sufficient_evidence"):
        return {
            "insight_type": INSIGHT_MONITORING_ONLY,
            "primary_insight": CARTS_INSIGHT_MONITORING_EMPTY,
            "reason": CARTS_REASON_MONITORING,
            "cartflow_action": CARTS_ACTION_OBSERVING,
            "evidence_summary": {},
            "source_refs": _refs("has_sufficient_evidence"),
            "confidence": CONFIDENCE_INSUFFICIENT,
        }

    monitored = _int(evidence.get("monitored_count"))
    attention = _int(evidence.get("attention_count"))
    automatic = _int(evidence.get("automatic_count"))
    insight_type = _classify_carts_insight_type(evidence)

    if insight_type == INSIGHT_MERCHANT_REQUIRED:
        primary = CARTS_INSIGHT_ALL_NEED_MERCHANT
        reason = CARTS_REASON_ALL_INTERVENTION
        action = CARTS_ACTION_ALL_MERCHANT_NEXT_STEP
        refs = _refs("monitored_count", "attention_count")
    elif insight_type == INSIGHT_ATTENTION:
        if attention == 1:
            primary = CARTS_INSIGHT_ONE_NEEDS_MERCHANT
            reason = CARTS_REASON_ONE_INTERVENTION
        else:
            primary = CARTS_INSIGHT_SOME_NEED_MERCHANT
            reason = CARTS_REASON_PARTIAL_INTERVENTION.format(
                attention_count=attention,
                monitored_count=monitored,
            )
        action = CARTS_ACTION_WAITING_DECISION
        refs = _refs("monitored_count", "attention_count")
    elif insight_type == INSIGHT_AUTOMATIC_PROGRESS:
        primary = CARTS_INSIGHT_AUTOMATIC_UNDERWAY
        reason = CARTS_REASON_AUTOMATIC.format(automatic_count=automatic)
        action_key = _norm(evidence.get("cartflow_action_key"))
        action = (
            CARTS_ACTION_MONITORING_REPLIES
            if action_key == "monitoring_replies"
            else CARTS_ACTION_OBSERVING
        )
        refs = _refs("monitored_count", "automatic_count", "cartflow_action_key")
    else:
        primary = CARTS_INSIGHT_NO_ACTION
        reason = CARTS_REASON_CALM
        action = CARTS_ACTION_HOLDING
        refs = _refs("monitored_count", "attention_count")

    return {
        "insight_type": insight_type,
        "primary_insight": primary,
        "reason": reason,
        "cartflow_action": action.strip(),
        "evidence_summary": _carts_evidence_summary(evidence),
        "source_refs": refs,
        "confidence": _confidence_from_evidence(evidence),
    }


def compose_home_insight_v1(evidence: Mapping[str, Any]) -> dict[str, Any]:
    attention = _int(evidence.get("attention_count"))
    if attention <= 0:
        return {
            "insight_type": INSIGHT_HEALTHY,
            "primary_insight": HOME_INSIGHT_NO_URGENCY,
            "reason": HOME_REASON_CALM,
            "cartflow_action": HOME_ACTION_ROUTINE,
            "evidence_summary": {"attention_count": 0},
            "source_refs": _refs("attention_count"),
            "confidence": _confidence_from_evidence(evidence),
        }
    return {
        "insight_type": INSIGHT_ATTENTION,
        "primary_insight": HOME_INSIGHT_NEEDS_LOOK,
        "reason": HOME_REASON_ATTENTION.format(attention_count=attention),
        "cartflow_action": HOME_ACTION_ROUTINE,
        "evidence_summary": {"attention_count": attention},
        "source_refs": _refs("attention_count"),
        "confidence": _confidence_from_evidence(evidence),
    }


def compose_generic_insight_v1(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "insight_type": INSIGHT_MONITORING_ONLY,
        "primary_insight": GENERIC_INSIGHT_MONITORING,
        "reason": GENERIC_REASON_INSUFFICIENT,
        "cartflow_action": GENERIC_ACTION_MONITORING,
        "evidence_summary": {},
        "source_refs": [],
        "confidence": CONFIDENCE_INSUFFICIENT,
    }


_PAGE_COMPOSERS = {
    "carts": compose_carts_insight_v1,
    "home": compose_home_insight_v1,
}


def compose_page_insight_v1(
    page_key: str,
    evidence: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """
    Compose governed page insight: meaning before evidence.

    Returns Insight → Reason → CartFlow Action → evidence_summary (counts last).
    """
    key = _norm(page_key).lower()
    if key not in VALID_PAGE_KEYS:
        raise ValueError(f"unknown merchant page key: {page_key!r}")

    ev: Mapping[str, Any] = evidence or {}
    composer = _PAGE_COMPOSERS.get(key, compose_generic_insight_v1)
    block = composer(ev)

    insight_type = _norm(block.get("insight_type")) or INSIGHT_MONITORING_ONLY
    composition_order = [
        "primary_insight",
        "reason",
        "cartflow_action",
        "evidence_summary",
    ]

    return {
        "version": INSIGHT_VERSION,
        "authority": AUTHORITY,
        "page_key": key,
        "insight_type": insight_type,
        "insight_type_label_ar": INSIGHT_TYPE_LABEL_AR.get(insight_type, insight_type),
        "primary_insight": _norm(block.get("primary_insight")),
        "reason": _norm(block.get("reason")),
        "cartflow_action": _norm(block.get("cartflow_action")),
        "evidence_summary": dict(block.get("evidence_summary") or {}),
        "source_refs": list(block.get("source_refs") or []),
        "confidence": _norm(block.get("confidence")) or CONFIDENCE_INSUFFICIENT,
        "composition_order": composition_order,
        "observability": {
            "evidence_keys_supplied": sorted(_norm(k) for k in ev.keys() if _norm(k)),
            "meaning_before_evidence": True,
        },
    }


def validate_page_insight_v1(insight: Mapping[str, Any]) -> list[str]:
    """Certification violations; empty list means valid."""
    violations: list[str] = []

    if _norm(insight.get("version")) != INSIGHT_VERSION:
        violations.append("invalid version")
    if _norm(insight.get("authority")) != AUTHORITY:
        violations.append("invalid authority")

    page_key = _norm(insight.get("page_key")).lower()
    if page_key not in VALID_PAGE_KEYS:
        violations.append("unknown page_key")

    for field in ("primary_insight", "reason", "cartflow_action"):
        if not _norm(insight.get(field)):
            violations.append(f"missing {field}")

    insight_type = _norm(insight.get("insight_type"))
    if insight_type not in INSIGHT_TYPE_LABEL_AR:
        violations.append("unknown insight_type")

    order = insight.get("composition_order") or []
    if list(order) != ["primary_insight", "reason", "cartflow_action", "evidence_summary"]:
        violations.append("composition_order must be insight-before-evidence")

    combined = " ".join(
        _norm(insight.get(f))
        for f in ("primary_insight", "reason", "cartflow_action")
    ).lower()

    forbidden_tokens = (
        "lifecycle_state",
        "group_key",
        "reason_tag",
        "bucket",
        "decision_key",
        "snapshot",
        "roi",
        "revenue",
        "probability",
        "prediction",
    )
    for token in forbidden_tokens:
        if token in combined:
            violations.append(f"forbidden token: {token}")

    forbidden_phrases = (
        "استعدنا",
        "حققنا لك",
        "ريال",
        "توقع",
        "احتمال",
        "ننصحك",
    )
    for phrase in forbidden_phrases:
        if phrase in combined:
            violations.append(f"forbidden phrase: {phrase}")

    primary = _norm(insight.get("primary_insight"))
    if re.match(r"^\d+\s", primary):
        violations.append("primary_insight must not lead with raw count")

    summary = insight.get("evidence_summary") or {}
    if not isinstance(summary, dict):
        violations.append("evidence_summary must be object")

    if _norm(insight.get("confidence")) not in {
        CONFIDENCE_HIGH,
        CONFIDENCE_MEDIUM,
        CONFIDENCE_LOW,
        CONFIDENCE_INSUFFICIENT,
    }:
        violations.append("invalid confidence")

    return violations
