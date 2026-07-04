# -*- coding: utf-8 -*-
"""
Merchant Evidence Registry v1 — governed merchant-visible evidence language.

Single source of truth for evidence source labels consumed by every merchant
proof surface (Proof of Value Governance PG-3, PG-8, PV-7).

Presentation layers MUST resolve labels through this registry — never hard-code
evidence wording in JavaScript, templates, or dashboard components.

Tier-0 engineering truth keys (lifecycle_truth, purchase_truth, …) map to stable
merchant evidence IDs; internal module names never reach merchants.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

REGISTRY_VERSION = "v1"

STATUS_ACTIVE = "active"
STATUS_FUTURE = "future"

# Stable merchant evidence identifiers (extend here — no presentation rewrite)
EVIDENCE_CUSTOMER_JOURNEY = "customer_journey"
EVIDENCE_PURCHASE_RECORD = "purchase_record"
EVIDENCE_RECOVERY_RECORD = "recovery_record"
EVIDENCE_MESSAGE_DELIVERY = "message_delivery"
EVIDENCE_CUSTOMER_RESPONSE = "customer_response"
EVIDENCE_STORE_ACTIVITY = "store_activity"
EVIDENCE_CARTFLOW_ANALYTICS = "cartflow_analytics"
EVIDENCE_BEHAVIOR_TRUTH = "behavior_truth"
EVIDENCE_PRODUCT_HISTORY = "product_history"
EVIDENCE_CAMPAIGN_DATA = "campaign_data"
EVIDENCE_VISITOR_BEHAVIOR = "visitor_behavior"
EVIDENCE_PRICING_HISTORY = "pricing_history"
EVIDENCE_SUPPORT_HISTORY = "support_history"
EVIDENCE_ATTRIBUTION_RECORD = "attribution_record"

# Proof domains (foundation §2 — eligibility only)
DOMAIN_RECOVERY = "recovery"
DOMAIN_UNDERSTANDING = "understanding"
DOMAIN_DECISION = "decision"
DOMAIN_OPERATIONAL = "operational"
DOMAIN_COMMERCIAL = "commercial"

# Confidence vocabularies compatible with each surface
_CONF_PROOF = frozenset({"confirmed", "high", "medium", "low", "unknown"})
_CONF_KL = frozenset({"high", "medium", "low", "insufficient"})

# Tier-0 internal evidence keys → registry ID (engineering side only)
TIER0_EVIDENCE_KEY_TO_ID: dict[str, str] = {
    "lifecycle_truth": EVIDENCE_CUSTOMER_JOURNEY,
    "purchase_truth": EVIDENCE_PURCHASE_RECORD,
    "recovery_truth": EVIDENCE_RECOVERY_RECORD,
    "provider_truth": EVIDENCE_MESSAGE_DELIVERY,
    "reason_capture": EVIDENCE_CUSTOMER_RESPONSE,
}

# Surface context → default section evidence ID
SURFACE_CONTEXT_EVIDENCE_ID: dict[str, str] = {
    "knowledge_layer": EVIDENCE_STORE_ACTIVITY,
    "daily_brief": EVIDENCE_CARTFLOW_ANALYTICS,
    "merchant_understanding": EVIDENCE_BEHAVIOR_TRUTH,
    "product_intelligence": EVIDENCE_PRODUCT_HISTORY,
    "decision_engine": EVIDENCE_CARTFLOW_ANALYTICS,
    "attribution": EVIDENCE_ATTRIBUTION_RECORD,
}


@dataclass(frozen=True)
class MerchantEvidenceEntry:
    evidence_id: str
    label_ar: str
    description_ar: str
    eligible_domains: frozenset[str]
    confidence_compat: frozenset[str]
    status: str = STATUS_ACTIVE
    tier0_keys: frozenset[str] = frozenset()
    # store = merchant-operational facts; platform = CartFlow-composed intelligence
    evidence_origin: str = "store"

    def to_merchant_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "label_ar": self.label_ar,
            "description_ar": self.description_ar,
            "eligible_domains": sorted(self.eligible_domains),
            "status": self.status,
            "evidence_origin": self.evidence_origin,
        }


_MERCHANT_EVIDENCE_REGISTRY: dict[str, MerchantEvidenceEntry] = {
    EVIDENCE_CUSTOMER_JOURNEY: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_CUSTOMER_JOURNEY,
        label_ar="مسار العميل",
        description_ar="حالة متابعة العميل ومراحل السلة من سجل المتجر",
        eligible_domains=frozenset({DOMAIN_UNDERSTANDING, DOMAIN_DECISION}),
        confidence_compat=_CONF_PROOF,
        tier0_keys=frozenset({"lifecycle_truth"}),
        evidence_origin="store",
    ),
    EVIDENCE_PURCHASE_RECORD: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_PURCHASE_RECORD,
        label_ar="سجل الشراء",
        description_ar="تأكيد إتمام الشراء من سجل المتجر",
        eligible_domains=frozenset({DOMAIN_RECOVERY, DOMAIN_COMMERCIAL}),
        confidence_compat=_CONF_PROOF,
        tier0_keys=frozenset({"purchase_truth"}),
        evidence_origin="store",
    ),
    EVIDENCE_RECOVERY_RECORD: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_RECOVERY_RECORD,
        label_ar="سجل الاسترجاع",
        description_ar="جدولة الإرسال وسجل رسائل الاسترجاع للمتجر",
        eligible_domains=frozenset({DOMAIN_RECOVERY}),
        confidence_compat=_CONF_PROOF,
        tier0_keys=frozenset({"recovery_truth"}),
        evidence_origin="store",
    ),
    EVIDENCE_MESSAGE_DELIVERY: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_MESSAGE_DELIVERY,
        label_ar="حالة رسائل WhatsApp",
        description_ar="قبول المزود وتسليم الرسالة للعميل عند توفر الدليل",
        eligible_domains=frozenset({DOMAIN_RECOVERY, DOMAIN_OPERATIONAL}),
        confidence_compat=_CONF_PROOF,
        tier0_keys=frozenset({"provider_truth"}),
        evidence_origin="store",
    ),
    EVIDENCE_CUSTOMER_RESPONSE: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_CUSTOMER_RESPONSE,
        label_ar="سبب التردد أو رد العميل",
        description_ar="سبب التردد المُسجَّل من واجهة المتجر أو رد العميل",
        eligible_domains=frozenset({DOMAIN_UNDERSTANDING, DOMAIN_DECISION}),
        confidence_compat=_CONF_PROOF,
        tier0_keys=frozenset({"reason_capture"}),
        evidence_origin="store",
    ),
    EVIDENCE_STORE_ACTIVITY: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_STORE_ACTIVITY,
        label_ar="بيانات المتجر",
        description_ar="سلات مهجورة وأسباب التردد وسجل الاسترجاع من متجرك — بيانات تشغيلية مباشرة",
        eligible_domains=frozenset({DOMAIN_UNDERSTANDING}),
        confidence_compat=_CONF_KL,
        evidence_origin="store",
    ),
    EVIDENCE_CARTFLOW_ANALYTICS: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_CARTFLOW_ANALYTICS,
        label_ar="بيانات CartFlow",
        description_ar="استنتاجات وملخصات يُجمّعها CartFlow من بيانات متجرك (مثل الموجز اليومي)",
        eligible_domains=frozenset({DOMAIN_UNDERSTANDING, DOMAIN_COMMERCIAL}),
        confidence_compat=_CONF_KL | _CONF_PROOF,
        status=STATUS_FUTURE,
        evidence_origin="platform",
    ),
    EVIDENCE_BEHAVIOR_TRUTH: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_BEHAVIOR_TRUTH,
        label_ar="سلوك العملاء",
        description_ar="إشارات العودة للموقع وتفاعل الجلسة (Behavior Truth)",
        eligible_domains=frozenset({DOMAIN_UNDERSTANDING}),
        confidence_compat=_CONF_PROOF,
        status=STATUS_FUTURE,
        evidence_origin="store",
    ),
    EVIDENCE_PRODUCT_HISTORY: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_PRODUCT_HISTORY,
        label_ar="سجل المنتجات",
        description_ar="بيانات المنتجات وأداؤها عبر الزمن في المتجر",
        eligible_domains=frozenset({DOMAIN_UNDERSTANDING, DOMAIN_COMMERCIAL}),
        confidence_compat=_CONF_KL,
        status=STATUS_FUTURE,
        evidence_origin="store",
    ),
    EVIDENCE_CAMPAIGN_DATA: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_CAMPAIGN_DATA,
        label_ar="بيانات الحملات",
        description_ar="أداء الحملات التسويقية المرتبطة بالمتجر",
        eligible_domains=frozenset({DOMAIN_OPERATIONAL, DOMAIN_COMMERCIAL}),
        confidence_compat=_CONF_KL,
        status=STATUS_FUTURE,
        evidence_origin="store",
    ),
    EVIDENCE_VISITOR_BEHAVIOR: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_VISITOR_BEHAVIOR,
        label_ar="حركة الزيارات",
        description_ar="حجم الزيارات والطلب على السلات (مؤشرات الزيارات)",
        eligible_domains=frozenset({DOMAIN_UNDERSTANDING}),
        confidence_compat=_CONF_KL,
        status=STATUS_FUTURE,
        evidence_origin="store",
    ),
    EVIDENCE_PRICING_HISTORY: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_PRICING_HISTORY,
        label_ar="سجل الأسعار",
        description_ar="تغيّرات التسعير في المتجر وتأثيرها على التردد",
        eligible_domains=frozenset({DOMAIN_UNDERSTANDING, DOMAIN_COMMERCIAL}),
        confidence_compat=_CONF_KL,
        status=STATUS_FUTURE,
        evidence_origin="store",
    ),
    EVIDENCE_SUPPORT_HISTORY: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_SUPPORT_HISTORY,
        label_ar="سجل الدعم",
        description_ar="تفاعلات الدعم المرتبطة بعملاء المتجر",
        eligible_domains=frozenset({DOMAIN_OPERATIONAL}),
        confidence_compat=_CONF_KL,
        status=STATUS_FUTURE,
        evidence_origin="store",
    ),
    EVIDENCE_ATTRIBUTION_RECORD: MerchantEvidenceEntry(
        evidence_id=EVIDENCE_ATTRIBUTION_RECORD,
        label_ar="ربط الإيراد بالاسترجاع",
        description_ar="ربط المبيعات المسترجعة بمسارات الاسترجاع في المتجر",
        eligible_domains=frozenset({DOMAIN_RECOVERY, DOMAIN_COMMERCIAL}),
        confidence_compat=_CONF_PROOF,
        status=STATUS_FUTURE,
        evidence_origin="store",
    ),
}


def get_merchant_evidence_entry(evidence_id: str) -> Optional[MerchantEvidenceEntry]:
    key = (evidence_id or "").strip()
    if not key:
        return None
    return _MERCHANT_EVIDENCE_REGISTRY.get(key)


def merchant_evidence_label_ar(evidence_id: str, *, fallback: str = "—") -> str:
    entry = get_merchant_evidence_entry(evidence_id)
    if entry is None:
        return fallback
    return entry.label_ar


def merchant_evidence_for_tier0_key(tier0_key: str) -> dict[str, Any]:
    """Resolve Tier-0 engineering key to governed merchant evidence metadata."""
    tk = (tier0_key or "").strip().lower()
    eid = TIER0_EVIDENCE_KEY_TO_ID.get(tk, EVIDENCE_CUSTOMER_JOURNEY)
    entry = get_merchant_evidence_entry(eid)
    if entry is None:
        return {
            "evidence_id": EVIDENCE_CUSTOMER_JOURNEY,
            "label_ar": "—",
            "tier0_key": tk or None,
        }
    return {
        "evidence_id": entry.evidence_id,
        "label_ar": entry.label_ar,
        "description_ar": entry.description_ar,
        "tier0_key": tk or None,
        "status": entry.status,
    }


def merchant_evidence_section_source_ar(evidence_id: str) -> str:
    """Full section footnote — «مصدر الدليل: …» from registry."""
    label = merchant_evidence_label_ar(evidence_id, fallback="")
    if not label or label == "—":
        return ""
    return f"مصدر الدليل: {label}"


def build_merchant_evidence_registry_payload(
    *,
    surface_context: str = "",
    section_evidence_id: str = "",
    claim_catalog_only: bool = False,
) -> dict[str, Any]:
    """Serializable registry slice for merchant UI consumption."""
    ctx = (surface_context or "").strip().lower()
    sec_id = (section_evidence_id or "").strip()
    if not claim_catalog_only:
        if not sec_id and ctx:
            sec_id = SURFACE_CONTEXT_EVIDENCE_ID.get(ctx, EVIDENCE_STORE_ACTIVITY)
    section_entry = (
        None
        if claim_catalog_only
        else (get_merchant_evidence_entry(sec_id) if sec_id else None)
    )
    active_entries = [
        e.to_merchant_dict()
        for e in _MERCHANT_EVIDENCE_REGISTRY.values()
        if e.status == STATUS_ACTIVE
    ]
    payload: dict[str, Any] = {
        "version": REGISTRY_VERSION,
        "entries": active_entries,
    }
    if section_entry is not None:
        payload["section_evidence_id"] = section_entry.evidence_id
        payload["section_source_ar"] = merchant_evidence_section_source_ar(
            section_entry.evidence_id
        )
        payload["section_label_ar"] = section_entry.label_ar
    return payload


def attach_merchant_evidence_registry_v1(
    target: Mapping[str, Any] | dict[str, Any],
    *,
    surface_context: str = "",
    section_evidence_id: str = "",
) -> None:
    """Attach registry payload to an API/dashboard dict (additive)."""
    if not isinstance(target, dict):
        return
    target["merchant_evidence_registry_v1"] = build_merchant_evidence_registry_payload(
        surface_context=surface_context,
        section_evidence_id=section_evidence_id,
    )


def enrich_proof_evidence_fields(
    bundle: dict[str, Any],
    *,
    tier0_key: str,
) -> None:
    """Add governed evidence_id + merchant labels to a proof bundle in-place."""
    meta = merchant_evidence_for_tier0_key(tier0_key)
    bundle["evidence_id"] = meta["evidence_id"]
    bundle["evidence_source_ar"] = meta["label_ar"]
    bundle["evidence_label_ar"] = meta["label_ar"]


def enrich_step_evidence_fields(step: dict[str, Any]) -> None:
    """Add governed evidence fields to a recovery proof step in-place."""
    tier0 = str(step.get("evidence_type") or "").strip().lower()
    meta = merchant_evidence_for_tier0_key(tier0)
    step["evidence_id"] = meta["evidence_id"]
    step["evidence_label_ar"] = meta["label_ar"]


__all__ = [
    "REGISTRY_VERSION",
    "EVIDENCE_ATTRIBUTION_RECORD",
    "EVIDENCE_BEHAVIOR_TRUTH",
    "EVIDENCE_CARTFLOW_ANALYTICS",
    "EVIDENCE_CUSTOMER_JOURNEY",
    "EVIDENCE_CUSTOMER_RESPONSE",
    "EVIDENCE_MESSAGE_DELIVERY",
    "EVIDENCE_PURCHASE_RECORD",
    "EVIDENCE_RECOVERY_RECORD",
    "EVIDENCE_STORE_ACTIVITY",
    "TIER0_EVIDENCE_KEY_TO_ID",
    "attach_merchant_evidence_registry_v1",
    "build_merchant_evidence_registry_payload",
    "enrich_proof_evidence_fields",
    "enrich_step_evidence_fields",
    "get_merchant_evidence_entry",
    "merchant_evidence_for_tier0_key",
    "merchant_evidence_label_ar",
    "merchant_evidence_section_source_ar",
]
