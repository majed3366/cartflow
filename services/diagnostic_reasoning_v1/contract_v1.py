# -*- coding: utf-8 -*-
"""
Diagnostic Reasoning Contract V1.

Observation → Evidence → Competing Causes → Best-Supported Diagnosis
→ Confidence → Recommendation → Merchant Publication.
"""
from __future__ import annotations

from typing import Any, Mapping

DIAGNOSTIC_VERSION_V1 = "diagnostic_reasoning_v1"
CONTRACT_SCHEMA_V1 = "diagnostic_contract_v1"

DIAGNOSIS_STATUS_SUPPORTED = "supported"
DIAGNOSIS_STATUS_PARTIALLY_SUPPORTED = "partially_supported"
DIAGNOSIS_STATUS_INSUFFICIENT = "insufficient_evidence"
DIAGNOSIS_STATUS_CONFLICTING = "conflicting_evidence"
DIAGNOSIS_STATUS_SUPPRESSED = "suppressed"

DIAGNOSIS_STATUSES = frozenset(
    {
        DIAGNOSIS_STATUS_SUPPORTED,
        DIAGNOSIS_STATUS_PARTIALLY_SUPPORTED,
        DIAGNOSIS_STATUS_INSUFFICIENT,
        DIAGNOSIS_STATUS_CONFLICTING,
        DIAGNOSIS_STATUS_SUPPRESSED,
    }
)

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCE_INSUFFICIENT = "insufficient"

CONFIDENCE_LEVELS = frozenset(
    {
        CONFIDENCE_HIGH,
        CONFIDENCE_MEDIUM,
        CONFIDENCE_LOW,
        CONFIDENCE_INSUFFICIENT,
    }
)

FAMILY_CHECKOUT_AFTER_SHIPPING = "checkout_abandonment_after_shipping"
FAMILY_INTEREST_WITHOUT_PURCHASE = "interest_without_purchase"
FAMILY_PAYMENT_FRICTION = "payment_friction_at_checkout"
FAMILY_CONTACT_FOLLOWUP_BLOCKED = "contact_followup_blocked"

DIAGNOSTIC_FAMILIES = frozenset(
    {
        FAMILY_CHECKOUT_AFTER_SHIPPING,
        FAMILY_INTEREST_WITHOUT_PURCHASE,
        FAMILY_PAYMENT_FRICTION,
        FAMILY_CONTACT_FOLLOWUP_BLOCKED,
    }
)

# Merchant Arabic — evidence language (never "CartFlow believes").
AR_INSUFFICIENT_SHIPPING_STAGE = (
    "يغادر العملاء بعد خطوة الشحن، لكن الأدلة الحالية لا تكفي لتحديد ما إذا كان "
    "السبب تكلفة الشحن أو مدة التوصيل أو خيارات الشحن المتاحة."
)
AR_INSUFFICIENT_GENERIC = (
    "الأدلة الحالية غير كافية لتحديد السبب الدقيق."
)
AR_INSUFFICIENT_INTEREST = (
    "يظهر العملاء اهتماماً متكرراً بالمنتج، لكن الأدلة الحالية غير كافية لتحديد "
    "سبب مغادرتهم قبل الشراء."
)
AR_CONFLICTING = (
    "الأدلة متعارضة بين أسباب محتملة ولم يُحسم السبب بعد."
)
AR_SHIPPING_COST = (
    "الأدلة تشير إلى أن تكلفة الشحن هي السبب الأكثر احتمالاً لمغادرة العملاء."
)
AR_PAYMENT_FRICTION = (
    "الأدلة تشير إلى أن احتكاك الدفع هو السبب الأكثر احتمالاً لمغادرة العملاء."
)
AR_CONTACT_BLOCKED = (
    "الأدلة تشير إلى أن متابعة العملاء مقيدة لأن معلومات التواصل غير متاحة."
)
AR_REC_CONTINUE = "لا يُوصى بتغيير تجاري بعد؛ واصل جمع الأدلة."
AR_REC_SHIPPING_COST = "راجع تكلفة الشحن أو وضّحها قبل إتمام الطلب."
AR_REC_PAYMENT = "راجع طرق الدفع المتاحة عند نقطة مغادرة العملاء."
AR_REC_CONTACT = "راجع التواصل."
AR_REC_NONE = ""


def empty_contract_v1(
    *,
    diagnostic_id: str,
    store_slug: str,
    subject_type: str,
    subject_id: str,
    family: str,
) -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA_V1,
        "diagnostic_id": diagnostic_id,
        "store_slug": store_slug,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "diagnostic_family": family,
        "observation_refs": [],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "candidate_causes": [],
        "selected_diagnosis": None,
        "diagnosis_status": DIAGNOSIS_STATUS_INSUFFICIENT,
        "confidence_level": CONFIDENCE_INSUFFICIENT,
        "confidence_reason": "no_evidence",
        "recommendation": {"cause_key": "insufficient_evidence", "text_ar": AR_REC_CONTINUE},
        "observation_ar": "",
        "diagnosis_ar": AR_INSUFFICIENT_GENERIC,
        "recommendation_ar": AR_REC_CONTINUE,
        "evidence_window": {},
        "generated_at": None,
        "expires_at": None,
        "diagnostic_version": DIAGNOSTIC_VERSION_V1,
    }


def validate_contract_v1(raw: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(raw, Mapping):
        return False, ["not_a_mapping"]
    if raw.get("schema") != CONTRACT_SCHEMA_V1:
        errors.append("schema")
    status = str(raw.get("diagnosis_status") or "")
    if status not in DIAGNOSIS_STATUSES:
        errors.append("diagnosis_status")
    conf = str(raw.get("confidence_level") or "")
    if conf not in CONFIDENCE_LEVELS:
        errors.append("confidence_level")
    selected = raw.get("selected_diagnosis")
    rec = raw.get("recommendation") if isinstance(raw.get("recommendation"), Mapping) else {}
    # No recommendation that introduces a cause absent from diagnosis.
    if status == DIAGNOSIS_STATUS_INSUFFICIENT:
        if selected not in (None, "", "insufficient_evidence"):
            errors.append("selected_on_insufficient")
        if str(rec.get("cause_key") or "") not in ("", "insufficient_evidence"):
            errors.append("rec_cause_on_insufficient")
    elif status in {
        DIAGNOSIS_STATUS_SUPPORTED,
        DIAGNOSIS_STATUS_PARTIALLY_SUPPORTED,
    }:
        if not selected:
            errors.append("missing_selected_diagnosis")
        if not list(raw.get("supporting_evidence") or []):
            errors.append("diagnosis_without_evidence")
        if str(rec.get("cause_key") or "") and str(rec.get("cause_key")) != str(selected):
            errors.append("rec_cause_mismatch")
    return (len(errors) == 0), errors


__all__ = [
    "AR_CONFLICTING",
    "AR_CONTACT_BLOCKED",
    "AR_INSUFFICIENT_GENERIC",
    "AR_INSUFFICIENT_INTEREST",
    "AR_INSUFFICIENT_SHIPPING_STAGE",
    "AR_PAYMENT_FRICTION",
    "AR_REC_CONTACT",
    "AR_REC_CONTINUE",
    "AR_REC_NONE",
    "AR_REC_PAYMENT",
    "AR_REC_SHIPPING_COST",
    "AR_SHIPPING_COST",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_INSUFFICIENT",
    "CONFIDENCE_LEVELS",
    "CONFIDENCE_LOW",
    "CONFIDENCE_MEDIUM",
    "CONTRACT_SCHEMA_V1",
    "DIAGNOSIS_STATUS_CONFLICTING",
    "DIAGNOSIS_STATUS_INSUFFICIENT",
    "DIAGNOSIS_STATUS_PARTIALLY_SUPPORTED",
    "DIAGNOSIS_STATUS_SUPPORTED",
    "DIAGNOSIS_STATUS_SUPPRESSED",
    "DIAGNOSIS_STATUSES",
    "DIAGNOSTIC_FAMILIES",
    "DIAGNOSTIC_VERSION_V1",
    "FAMILY_CHECKOUT_AFTER_SHIPPING",
    "FAMILY_CONTACT_FOLLOWUP_BLOCKED",
    "FAMILY_INTEREST_WITHOUT_PURCHASE",
    "FAMILY_PAYMENT_FRICTION",
    "empty_contract_v1",
    "validate_contract_v1",
]
