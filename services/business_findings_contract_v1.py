# -*- coding: utf-8 -*-
"""
BusinessFindingV1 — canonical governed finding contract.

Surfaces consume this contract. They must not invent commercial conclusions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

FINDING_VERSION = "v1"
ENGINE_VERSION = "business_findings_engine_v1"

# Scopes
SCOPE_STORE = "store"
SCOPE_CATEGORY = "category"
SCOPE_PRODUCT = "product"
SCOPE_CUSTOMER_SEGMENT = "customer_segment"
SCOPE_RECOVERY_CHANNEL = "recovery_channel"
SCOPE_HESITATION_REASON = "hesitation_reason"

# Status
STATUS_EMERGING = "emerging"
STATUS_CONFIRMED = "confirmed"
STATUS_STRENGTHENING = "strengthening"
STATUS_WEAKENING = "weakening"
STATUS_RESOLVED = "resolved"
STATUS_INSUFFICIENT = "insufficient_evidence"
STATUS_CONFLICTING = "conflicting_evidence"

# Recommendation types
REC_ACT_NOW = "act_now"
REC_TEST = "test"
REC_INVESTIGATE = "investigate"
REC_MONITOR = "monitor"
REC_NO_ACTION = "no_action"
REC_INSUFFICIENT = "insufficient_evidence"

# Finding family / type ids
TYPE_DOMINANT_HESITATION = "dominant_hesitation_reason_v1"
TYPE_HIGH_INTEREST_LOW_PURCHASE = "high_interest_low_purchase_product_v1"
TYPE_LOW_PRODUCT_INTEREST = "low_product_interest_v1"
TYPE_RETURN_WITHOUT_PURCHASE = "return_without_purchase_v1"
TYPE_RECOVERY_CHANNEL_EFFECTIVENESS = "recovery_channel_effectiveness_v1"
TYPE_WHATSAPP_TEST_CANDIDATE = "whatsapp_message_timing_test_v1"
TYPE_TRAFFIC_VS_CONVERSION = "traffic_versus_conversion_v1"
TYPE_REPEATED_INTEREST = "repeated_interest_v1"
TYPE_HESITATION_RESOLUTION = "hesitation_resolution_effectiveness_v1"
TYPE_INSUFFICIENT_OR_CONFLICTING = "insufficient_or_conflicting_evidence_v1"
TYPE_MISSING_CONTACT_BLOCKS = "missing_contact_blocks_recovery_v1"

# Authoritative surfaces for routing
SURFACE_HOME = "merchant_home"
SURFACE_KNOWLEDGE = "knowledge_layer"
SURFACE_PRODUCTS = "products"
SURFACE_CARTS = "carts"
SURFACE_WHATSAPP = "whatsapp"
SURFACE_CUSTOMERS = "customers"

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCE_INSUFFICIENT = "insufficient"

REASON_AR = {
    "shipping": "تكلفة الشحن",
    "shipping_cost": "تكلفة الشحن",
    "price": "السعر",
    "price_high": "السعر",
    "thinking": "التفكير قبل الشراء",
    "payment": "طريقة الدفع",
    "warranty": "الضمان",
    "delivery_time": "وقت التوصيل",
    "other": "سبب آخر",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm(value: Any) -> str:
    return str(value or "").strip()


def reason_label_ar(reason_key: str) -> str:
    key = norm(reason_key).lower()
    return REASON_AR.get(key, reason_key or "سبب غير مصنّف")


def empty_finding(
    *,
    finding_id: str,
    store_slug: str,
    finding_type: str,
    finding_scope: str = SCOPE_STORE,
    status: str = STATUS_INSUFFICIENT,
) -> dict[str, Any]:
    now = utc_now_iso()
    return {
        "finding_id": finding_id,
        "store_slug": norm(store_slug),
        "finding_type": finding_type,
        "finding_scope": finding_scope,
        "scope_reference": "",
        "title": "",
        "merchant_summary": "",
        "commercial_meaning": "",
        "evidence_summary": "",
        "evidence_refs": [],
        "observed_period": {},
        "comparison_period": {},
        "sample_size": 0,
        "confidence_level": CONFIDENCE_INSUFFICIENT,
        "confidence_score": 0.0,
        "business_impact": "",
        "recommended_direction": "",
        "recommendation_type": REC_INSUFFICIENT,
        "status": status,
        "first_detected_at": now,
        "last_confirmed_at": now,
        "finding_version": FINDING_VERSION,
        "source_version": ENGINE_VERSION,
        "authoritative_surface": SURFACE_KNOWLEDGE,
        "home_eligible": False,
        "family_key": finding_type,
        "rank_score": 0.0,
        "is_hypothesis": False,
        "is_confirmed_cause": False,
        "ai_used": False,
        "probabilistic": False,
    }


def finalize_finding(finding: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize and validate required BusinessFindingV1 fields."""
    base = empty_finding(
        finding_id=norm(finding.get("finding_id")) or "finding:unknown",
        store_slug=norm(finding.get("store_slug")),
        finding_type=norm(finding.get("finding_type")) or "unknown",
        finding_scope=norm(finding.get("finding_scope")) or SCOPE_STORE,
        status=norm(finding.get("status")) or STATUS_EMERGING,
    )
    out = dict(base)
    for key in base:
        if key in finding and finding[key] is not None:
            out[key] = finding[key]
    out["finding_id"] = norm(out["finding_id"])
    out["store_slug"] = norm(out["store_slug"])
    out["evidence_refs"] = list(out.get("evidence_refs") or [])
    out["sample_size"] = int(out.get("sample_size") or 0)
    try:
        out["confidence_score"] = round(float(out.get("confidence_score") or 0.0), 3)
    except (TypeError, ValueError):
        out["confidence_score"] = 0.0
    try:
        out["rank_score"] = round(float(out.get("rank_score") or 0.0), 3)
    except (TypeError, ValueError):
        out["rank_score"] = 0.0
    out["ai_used"] = False
    out["probabilistic"] = False
    out["finding_version"] = FINDING_VERSION
    out["source_version"] = ENGINE_VERSION
    return out


def is_merchant_worthy(finding: Mapping[str, Any]) -> bool:
    """Raw counters / empty titles are not findings."""
    title = norm(finding.get("title"))
    summary = norm(finding.get("merchant_summary"))
    meaning = norm(finding.get("commercial_meaning"))
    if not title or not summary:
        return False
    if not meaning and norm(finding.get("status")) not in (
        STATUS_INSUFFICIENT,
        STATUS_CONFLICTING,
    ):
        return False
    # Reject bare operational facts presented as findings.
    banned_starts = (
        "عدد السلال",
        "تمت إضافة",
        "تم إرسال",
        "phone =",
        "no_phone",
    )
    blob = f"{title} {summary}".lower()
    if any(blob.startswith(b.lower()) for b in banned_starts):
        return False
    return True
