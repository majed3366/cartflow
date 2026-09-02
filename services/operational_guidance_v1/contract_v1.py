# -*- coding: utf-8 -*-
"""Operational Guidance Layer V1 — contract constants and validation."""
from __future__ import annotations

from typing import Any, Mapping

GUIDANCE_VERSION_V1 = "operational_guidance_v1"
GUIDANCE_SCHEMA_V1 = "operational_guidance_object_v1"

STATE_ACTIVE = "active"
STATE_INSUFFICIENT = "insufficient_evidence"
STATE_ABSTAINED = "abstained"

GUIDANCE_STATES = frozenset({STATE_ACTIVE, STATE_INSUFFICIENT, STATE_ABSTAINED})

REQUIRED_FIELDS = (
    "guidance_id",
    "store_slug",
    "subject",
    "evidence_refs",
    "diagnosis",
    "recommendation",
    "reasoning_summary",
    "merchant_action",
    "recheck_condition",
    "confidence_state",
    "generated_at",
)

# Bare generic verbs/phrases forbidden unless the object is fully grounded
# (WHAT / WHY / UNTIL / THRESHOLD present via required fields).
BARE_GENERIC_PHRASES_AR = (
    "راجع",
    "راقب",
    "انتظر",
    "حاول",
    "قد يكون",
    "اجمع المزيد من البيانات",
)

FAMILY_SHIPPING_FRICTION = "shipping_friction"
FAMILY_PRICE_HESITATION = "price_hesitation"
FAMILY_PRODUCT_CONFIDENCE = "product_confidence_quality"
FAMILY_WAIT_INSUFFICIENT = "wait_insufficient_evidence"
FAMILY_COMMUNICATION_FOLLOWUP = "communication_followup"

SUPPORTED_FAMILIES_NOW = frozenset(
    {
        FAMILY_SHIPPING_FRICTION,
        FAMILY_PRICE_HESITATION,
        FAMILY_PRODUCT_CONFIDENCE,
        FAMILY_WAIT_INSUFFICIENT,
        FAMILY_COMMUNICATION_FOLLOWUP,
    }
)

# Audit classification (docs + gates) — do not implement unsupported.
FAMILY_AUDIT_V1 = {
    FAMILY_SHIPPING_FRICTION: "SUPPORTED_NOW",
    FAMILY_PRICE_HESITATION: "SUPPORTED_NOW",
    FAMILY_PRODUCT_CONFIDENCE: "SUPPORTED_NOW",
    FAMILY_WAIT_INSUFFICIENT: "SUPPORTED_NOW",
    FAMILY_COMMUNICATION_FOLLOWUP: "SUPPORTED_NOW",
}


def _norm(text: Any) -> str:
    return " ".join(str(text or "").strip().split())


def empty_guidance_object_v1(
    *,
    store_slug: str = "",
    subject: str = "store",
    guidance_id: str = "ogl:none",
    generated_at: str = "",
) -> dict[str, Any]:
    return {
        "ok": False,
        "schema": GUIDANCE_SCHEMA_V1,
        "guidance_version": GUIDANCE_VERSION_V1,
        "guidance_id": guidance_id,
        "store_slug": str(store_slug or ""),
        "subject": str(subject or "store"),
        "family": FAMILY_WAIT_INSUFFICIENT,
        "evidence_refs": [],
        "diagnosis": "",
        "recommendation": "",
        "reasoning_summary": "",
        "merchant_action": "",
        "recheck_condition": "",
        "confidence_state": STATE_INSUFFICIENT,
        "generated_at": generated_at,
        "expected_monitored_outcome": "",
        "home_surface": {},
        "workspace_surface": {},
    }


def validate_guidance_object_v1(raw: Mapping[str, Any] | None) -> list[str]:
    """Return validation errors; empty list means contract-valid."""
    g = raw if isinstance(raw, Mapping) else {}
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field == "evidence_refs":
            refs = g.get("evidence_refs")
            if not isinstance(refs, list):
                errors.append("evidence_refs")
            continue
        if field == "confidence_state":
            if str(g.get(field) or "") not in GUIDANCE_STATES:
                errors.append("confidence_state")
            continue
        if not _norm(g.get(field)):
            errors.append(field)
    family = str(g.get("family") or "")
    if family and family not in SUPPORTED_FAMILIES_NOW:
        errors.append("unsupported_family")
    # No hidden chain-of-thought fields on merchant object.
    for banned in ("chain_of_thought", "hidden_reasoning", "raw_model_trace"):
        if banned in g and g.get(banned):
            errors.append(banned)
    return errors


def is_bare_generic_recommendation_ar(text: Any) -> bool:
    """True when recommendation is only a bare generic phrase."""
    t = _norm(text)
    if not t:
        return True
    # Strip trailing punctuation
    bare = t.rstrip(" .،.")
    return bare in BARE_GENERIC_PHRASES_AR or any(
        bare == p or bare.startswith(p + " ") and len(bare) <= len(p) + 8
        for p in BARE_GENERIC_PHRASES_AR
    )


__all__ = [
    "BARE_GENERIC_PHRASES_AR",
    "FAMILY_AUDIT_V1",
    "FAMILY_COMMUNICATION_FOLLOWUP",
    "FAMILY_PRICE_HESITATION",
    "FAMILY_PRODUCT_CONFIDENCE",
    "FAMILY_SHIPPING_FRICTION",
    "FAMILY_WAIT_INSUFFICIENT",
    "GUIDANCE_SCHEMA_V1",
    "GUIDANCE_STATES",
    "GUIDANCE_VERSION_V1",
    "REQUIRED_FIELDS",
    "STATE_ABSTAINED",
    "STATE_ACTIVE",
    "STATE_INSUFFICIENT",
    "SUPPORTED_FAMILIES_NOW",
    "empty_guidance_object_v1",
    "is_bare_generic_recommendation_ar",
    "validate_guidance_object_v1",
]
