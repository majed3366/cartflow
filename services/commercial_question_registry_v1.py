# -*- coding: utf-8 -*-
"""
Commercial Question Registry V1 — governed commercial questions Home may answer.

Home admission requires an insight to answer one registered commercial question
with Evidence + Confidence + Merchant Meaning. Operational counts alone are rejected.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

REGISTRY_VERSION = "commercial_question_registry_v1"

# Dimensions (knowledge diversity)
DIM_PRODUCTS = "products"
DIM_HESITATION = "hesitation"
DIM_TRAFFIC = "traffic"
DIM_CONVERSION = "conversion"
DIM_RECOVERY = "recovery"
DIM_WHATSAPP = "whatsapp"
DIM_GUIDANCE = "merchant_guidance"
DIM_KNOWLEDGE = "knowledge"
DIM_DATA = "missing_evidence"
DIM_CONTACT = "contact"  # recovery gate — allowed but must not dominate alone

# Finding type / CIL id → question_id
FINDING_TYPE_TO_QUESTION: dict[str, str] = {
    "high_interest_low_purchase_product_v1": "CQ-P01",
    "repeated_interest_v1": "CQ-P02",
    "low_product_interest_v1": "CQ-P03",
    "dominant_hesitation_reason_v1": "CQ-H01",
    "hesitation_resolution_effectiveness_v1": "CQ-H04",
    "traffic_versus_conversion_v1": "CQ-T01",
    "return_without_purchase_v1": "CQ-R01",
    "recovery_channel_effectiveness_v1": "CQ-R02",
    "whatsapp_message_timing_test_v1": "CQ-W01",
    "missing_contact_blocks_recovery_v1": "CQ-C01",
    "insufficient_or_conflicting_evidence_v1": "CQ-D01",
}

# Canonical registry entries
COMMERCIAL_QUESTIONS_V1: dict[str, dict[str, Any]] = {
    "CQ-P01": {
        "question_id": "CQ-P01",
        "dimension": DIM_PRODUCTS,
        "question_ar": "أي منتجات تجذب الانتباه لكنها تفشل في التحويل؟",
        "question_en": "Which products attract attention but fail to convert?",
        "home_slots": ("business_understanding", "biggest_opportunity"),
        "growth": True,
    },
    "CQ-P02": {
        "question_id": "CQ-P02",
        "dimension": DIM_PRODUCTS,
        "question_ar": "أي منتجات تدخل السلة مراراً دون شراء؟",
        "question_en": "Which products repeatedly enter carts without purchase?",
        "home_slots": ("business_understanding", "biggest_opportunity"),
        "growth": True,
    },
    "CQ-P03": {
        "question_id": "CQ-P03",
        "dimension": DIM_PRODUCTS,
        "question_ar": "أي منتجات تولّد تردداً أو اهتماماً ضعيفاً؟",
        "question_en": "Which products generate hesitation or weak interest?",
        "home_slots": ("business_understanding",),
        "growth": True,
    },
    "CQ-H01": {
        "question_id": "CQ-H01",
        "dimension": DIM_HESITATION,
        "question_ar": "ما أكثر سبب يسبب تردد العملاء؟",
        "question_en": "What causes hesitation most often?",
        "home_slots": ("business_understanding", "todays_priority"),
        "growth": True,
    },
    "CQ-H02": {
        "question_id": "CQ-H02",
        "dimension": DIM_HESITATION,
        "question_ar": "هل أصبحت تكلفة الشحن العائق الأبرز؟",
        "question_en": "Is shipping becoming the dominant blocker?",
        "home_slots": ("business_understanding",),
        "growth": True,
    },
    "CQ-H03": {
        "question_id": "CQ-H03",
        "dimension": DIM_HESITATION,
        "question_ar": "هل الأسعار تدفع للتخلي عن الشراء؟",
        "question_en": "Are prices creating abandonment?",
        "home_slots": ("business_understanding",),
        "growth": True,
    },
    "CQ-H04": {
        "question_id": "CQ-H04",
        "dimension": DIM_HESITATION,
        "question_ar": "هل يعالج الاسترجاع أسباب التردد فعلاً؟",
        "question_en": "Does recovery resolve hesitation effectively?",
        "home_slots": ("business_understanding", "learning_progress"),
        "growth": True,
    },
    "CQ-T01": {
        "question_id": "CQ-T01",
        "dimension": DIM_TRAFFIC,
        "question_ar": "هل لدينا أدلة كافية لتقييم جودة الزيارات؟",
        "question_en": "Do we have enough evidence to judge traffic quality?",
        "home_slots": ("business_understanding", "learning_progress"),
        "growth": True,
        "allows_insufficient": True,
    },
    "CQ-T02": {
        "question_id": "CQ-T02",
        "dimension": DIM_TRAFFIC,
        "question_ar": "هل الزيارات تتحسّن أم تصبح أكثر تأهيلاً؟",
        "question_en": "Are visits improving or becoming more qualified?",
        "home_slots": ("learning_progress",),
        "growth": True,
        "allows_insufficient": True,
    },
    "CQ-R01": {
        "question_id": "CQ-R01",
        "dimension": DIM_RECOVERY,
        "question_ar": "أي مسار استرجاع يغيّر النتائج فعلاً؟",
        "question_en": "Which recovery path actually changes outcomes?",
        "home_slots": ("business_understanding", "biggest_opportunity"),
        "growth": True,
    },
    "CQ-R02": {
        "question_id": "CQ-R02",
        "dimension": DIM_RECOVERY,
        "question_ar": "هل قناة الاسترجاع ترفع المشتريات أم العودة فقط؟",
        "question_en": "Does the recovery channel increase purchases or only returns?",
        "home_slots": ("business_understanding", "learning_progress"),
        "growth": True,
    },
    "CQ-W01": {
        "question_id": "CQ-W01",
        "dimension": DIM_WHATSAPP,
        "question_ar": "هل توقيت رسالة واتساب يستحق اختباراً تجارياً؟",
        "question_en": "Does WhatsApp message timing deserve a commercial test?",
        "home_slots": ("biggest_opportunity", "learning_progress"),
        "growth": True,
    },
    "CQ-G01": {
        "question_id": "CQ-G01",
        "dimension": DIM_GUIDANCE,
        "question_ar": "أي قضية تستحق الانتباه أولاً؟",
        "question_en": "Which issue deserves attention first?",
        "home_slots": ("todays_priority", "business_health"),
        "growth": True,
    },
    "CQ-G02": {
        "question_id": "CQ-G02",
        "dimension": DIM_GUIDANCE,
        "question_ar": "أي قضية أدلتها ضعيفة ولا يجب التصرف عليها الآن؟",
        "question_en": "Which issue has weak evidence?",
        "home_slots": ("learning_progress",),
        "growth": True,
        "allows_insufficient": True,
    },
    "CQ-K01": {
        "question_id": "CQ-K01",
        "dimension": DIM_KNOWLEDGE,
        "question_ar": "ماذا تعلّم CartFlow مؤخراً عن المتجر؟",
        "question_en": "What has CartFlow learned recently?",
        "home_slots": ("learning_progress",),
        "growth": True,
    },
    "CQ-K02": {
        "question_id": "CQ-K02",
        "dimension": DIM_KNOWLEDGE,
        "question_ar": "أي استنتاجات أصبحت أقوى أو أضعف؟",
        "question_en": "Which conclusions became stronger or lost confidence?",
        "home_slots": ("learning_progress",),
        "growth": True,
    },
    "CQ-D01": {
        "question_id": "CQ-D01",
        "dimension": DIM_DATA,
        "question_ar": "ماذا ما زلنا لا نعرف — وأين نحتاج أدلة؟",
        "question_en": "What do we still not know?",
        "home_slots": ("learning_progress", "business_understanding"),
        "growth": True,
        "allows_insufficient": True,
    },
    "CQ-C01": {
        "question_id": "CQ-C01",
        "dimension": DIM_CONTACT,
        "question_ar": "هل نقص بيانات التواصل يعيق استرجاع الإيراد؟",
        "question_en": "Does missing contact data block recovery?",
        "home_slots": ("todays_priority", "business_health"),
        "growth": True,
    },
}


def _norm(v: Any) -> str:
    return str(v or "").strip()


def get_question_v1(question_id: str) -> Optional[dict[str, Any]]:
    return COMMERCIAL_QUESTIONS_V1.get(_norm(question_id))


def resolve_question_for_finding_v1(finding: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """Map a Business Finding / CIL id to a registry question."""
    ftype = _norm(finding.get("finding_type") or finding.get("commercial_interpretation_id"))
    qid = FINDING_TYPE_TO_QUESTION.get(ftype)
    # Hesitation reason refinement
    if qid == "CQ-H01":
        blob = " ".join(
            _norm(finding.get(k))
            for k in ("title", "merchant_summary", "scope_reference", "evidence_summary")
        ).lower()
        if "شحن" in blob or "shipping" in blob:
            qid = "CQ-H02"
        elif "سعر" in blob or "price" in blob:
            qid = "CQ-H03"
    if not qid:
        fam = _norm(finding.get("family_key")).lower()
        if fam.startswith("product"):
            qid = "CQ-P01"
        elif "hesitation" in fam:
            qid = "CQ-H01"
        elif "traffic" in fam:
            qid = "CQ-T01"
        elif "whatsapp" in fam or "channel" in fam:
            qid = "CQ-R02"
        elif "insufficient" in fam or "meta_evidence" in fam:
            qid = "CQ-D01"
        elif "contact" in fam:
            qid = "CQ-C01"
    if not qid:
        return None
    q = get_question_v1(qid)
    return dict(q) if q else None


def list_questions_v1(*, dimension: str = "") -> list[dict[str, Any]]:
    dim = _norm(dimension).lower()
    out = list(COMMERCIAL_QUESTIONS_V1.values())
    if dim:
        out = [q for q in out if _norm(q.get("dimension")).lower() == dim]
    return sorted(out, key=lambda q: _norm(q.get("question_id")))


def registry_stats_v1() -> dict[str, Any]:
    dims: dict[str, int] = {}
    for q in COMMERCIAL_QUESTIONS_V1.values():
        d = _norm(q.get("dimension")) or "unknown"
        dims[d] = dims.get(d, 0) + 1
    return {
        "registry_version": REGISTRY_VERSION,
        "question_count": len(COMMERCIAL_QUESTIONS_V1),
        "dimensions": dims,
        "success_metric": (
            "Home is measured by the number of different commercial questions "
            "CartFlow can answer with evidence."
        ),
    }


__all__ = [
    "COMMERCIAL_QUESTIONS_V1",
    "DIM_CONTACT",
    "DIM_CONVERSION",
    "DIM_DATA",
    "DIM_GUIDANCE",
    "DIM_HESITATION",
    "DIM_KNOWLEDGE",
    "DIM_PRODUCTS",
    "DIM_RECOVERY",
    "DIM_TRAFFIC",
    "DIM_WHATSAPP",
    "FINDING_TYPE_TO_QUESTION",
    "REGISTRY_VERSION",
    "get_question_v1",
    "list_questions_v1",
    "registry_stats_v1",
    "resolve_question_for_finding_v1",
]
