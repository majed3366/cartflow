# -*- coding: utf-8 -*-
"""
Decision Workspace Refinement V1 — ownership language + commitment redesign.

CartFlow owns: observation, evidence, diagnosis, confidence, reality validation.
Merchant owns: business decision, execution, commercial judgement.
"""
from __future__ import annotations

from typing import Any, Mapping

_SOFT_OPENERS = (
    "راجع",
    "حسّن",
    "حسن",
    "تحقق",
    "افحص",
    "اجمع",
    "اكتشف",
    "حقّق",
    "حقق",
    "حققي",
    "فكّر",
    "فكر",
    "investigat",
    "review",
    "improve",
    "check",
    "consider",
    "collect",
    "discover",
    "diagnos",
)

_CARTFLOW_WORK_MARKERS = (
    "جمع الأدل",
    "جمع المزيد",
    "مزيد من الأدل",
    "اكتشف السبب",
    "تشخيص",
    "مسار التحويل",
    "مسار شراء",
    "أدلة الطلب",
    "تحقق من",
    "investigat",
    "funnel",
)


def _norm(v: Any) -> str:
    return str(v or "").strip()


def looks_like_cartflow_work(text: str) -> bool:
    t = _norm(text)
    if not t:
        return False
    low = t.casefold()
    for p in _SOFT_OPENERS:
        if low.startswith(p.casefold()):
            return True
    for m in _CARTFLOW_WORK_MARKERS:
        if m.casefold() in low:
            return True
    return False


def confidence_ar_v1(card: Mapping[str, Any]) -> str:
    status = _norm(
        card.get("diagnosis_status") or card.get("decision_status") or ""
    ).casefold()
    level = _norm(
        card.get("confidence_level")
        or card.get("decision_confidence")
        or card.get("confidence")
        or ""
    ).casefold()
    if status in {"insufficient_evidence", "insufficient"} or card.get("has_decision") is False:
        return "الثقة الحالية غير كافية لتبرير تغيير تجاري."
    if status in {"conflicting_evidence", "conflicting"}:
        return "الأدلة متعارضة — لا يمكن تأكيد سبب واحد بثقة كافية."
    if level in {"high", "عال", "عالية", "supported"}:
        return "الثقة كافية لدعم قرار تجاري واضح."
    if level in {"low", "منخفض", "منخفضة"}:
        return "الثقة محدودة — القرار التجاري يجب أن يبقى حذراً."
    explicit = _norm(card.get("confidence_ar") or card.get("decision_confidence_ar"))
    if explicit and not looks_like_cartflow_work(explicit):
        return explicit
    return "الثقة متوسطة — يمكن البناء عليها بحذر."


def cartflow_responsibility_ar_v1(card: Mapping[str, Any]) -> str:
    status = _norm(card.get("diagnosis_status") or "").casefold()
    if status in {"insufficient_evidence", "insufficient"} or card.get("has_decision") is False:
        return (
            "CartFlow يتولى الآن توسيع الأدلة والتحقق من الواقع "
            "حتى يصبح التشخيص جاهزاً لقرارك."
        )
    if status in {"conflicting_evidence", "conflicting"}:
        return "CartFlow يعيد مقارنة الأدلة المتعارضة قبل أي توصية تجارية."
    return (
        "CartFlow أكمل الملاحظة والتشخيص. "
        "مسؤوليتك الآن حكم تجاري واحد — لا إعادة التشخيص."
    )


def diagnosis_ar_v1(card: Mapping[str, Any]) -> str:
    for key in (
        "diagnosis_ar",
        "business_meaning_ar",
        "situation_summary_ar",
        "observation_ar",
    ):
        v = _norm(card.get(key))
        if v and not looks_like_cartflow_work(v):
            return v
    why = _norm(card.get("why_ar") or (card.get("explanation") or {}).get("why_here"))
    subject = _norm(
        card.get("subject_ar")
        or card.get("product_name_ar")
        or card.get("affected_area_ar")
    )
    if why and not looks_like_cartflow_work(why):
        if subject and subject.split("—")[0].strip() not in why:
            return f"{subject.split('—')[0].strip()}: {why}"
        return why
    if subject:
        return f"هناك موقف تجاري واضح حول {subject.split('—')[0].strip()}."
    return "هناك موقف تجاري يحتاج قراراً الآن."


def why_believe_ar_v1(card: Mapping[str, Any], diagnosis: str) -> str:
    why = _norm(card.get("why_ar") or (card.get("explanation") or {}).get("why_here"))
    why_now = _norm(card.get("why_now_ar") or card.get("reasoning_ar"))
    for candidate in (why, why_now):
        if (
            candidate
            and candidate != diagnosis
            and not looks_like_cartflow_work(candidate)
            and not candidate.endswith("؟")
            and not candidate.endswith("?")
        ):
            return candidate
    # Advisor tone — never interrogate the merchant.
    if "شحن" in diagnosis:
        return "هذا الاستنتاج مبني على مغادرة متكررة عند مرحلة الشحن دون سبب قابل للفصل بعد."
    if "اهتمام" in diagnosis or "دون شراء" in diagnosis:
        return "الاهتمام بالمنتج واضح، لكن إتمام الشراء لا يتحقق بنفس الوضوح."
    if "تواصل" in diagnosis or "رقم" in diagnosis:
        return "مسار المتابعة يتعطل عندما لا تتوفر وسيلة تواصل صالحة."
    return "هذا الاستنتاج مبني على ملاحظات المتجر الحالية بعد استبعاد التفسيرات الأضعف."


def consequence_ar_v1(card: Mapping[str, Any]) -> str:
    for key in (
        "ignore_consequence_ar",
        "business_consequence_ar",
        "business_impact_ar",
    ):
        v = _norm(card.get(key))
        if v and v not in {
            _norm(card.get("expected_outcome_ar")),
            _norm(card.get("diagnosis_ar")),
        }:
            return v
    status = _norm(card.get("diagnosis_status") or "").casefold()
    if status in {"insufficient_evidence", "insufficient"}:
        return "بدون أدلة أوضح، أي تغيير تجاري الآن قد يعالج السبب الخطأ."
    return "إذا لم يُحسم الأمر، يستمر الأثر على الإيراد دون قرار واضح."


def commitment_ar_v1(card: Mapping[str, Any]) -> str:
    """
    Merchant commitment only — never CartFlow investigative work.
    """
    status = _norm(card.get("diagnosis_status") or "").casefold()
    if status in {"insufficient_evidence", "insufficient"} or card.get("has_decision") is False:
        return (
            "لا تغيّر السياسة الآن. "
            "انتظر حتى يُكمل CartFlow الأدلة ويقدّم توصية مدعومة."
        )
    if status in {"conflicting_evidence", "conflicting"}:
        return "لا تعتمد سبباً واحداً بعد. أرجئ القرار التجاري حتى يحسم CartFlow التعارض."

    # Prefer explicit commercial actions that are not CartFlow work.
    for key in (
        "commitment_ar",
        "merchant_commitment_ar",
        "recommended_action",
        "first_step_ar",
        "required_merchant_action",
        "action_label_ar",
    ):
        v = _norm(card.get(key))
        if v and not looks_like_cartflow_work(v):
            return v

    domain = _norm(card.get("business_domain") or card.get("decision_category")).casefold()
    subject = _norm(card.get("subject_ar") or card.get("product_name_ar"))
    short = subject.split("—")[0].strip() if subject else ""

    if "ship" in domain or "شحن" in (subject + _norm(card.get("diagnosis_ar"))):
        return "عندما تصبح الأدلة كافية: قرّر إن كنت ستعدّل سياسة الشحن أم تبقيها."
    if "communicat" in domain or "تواصل" in _norm(card.get("diagnosis_ar")):
        return "قرّر أولوية إصلاح التقاط وسيلة التواصل في مسار الشراء."
    if short:
        return f"قرّر الموقف التجاري بخصوص {short} بناءً على التشخيص الحالي."
    return "اتخذ قراراً تجارياً واحداً بناءً على التشخيص — أو أرجئه بوعي."


def expected_outcome_ar_v1(card: Mapping[str, Any], consequence: str) -> str:
    for key in ("expected_outcome_ar",):
        v = _norm(card.get(key))
        if v and v != consequence and not looks_like_cartflow_work(v):
            return v
    status = _norm(card.get("diagnosis_status") or "").casefold()
    if status in {"insufficient_evidence", "insufficient"}:
        return "بعد اكتمال الأدلة، ستحصل على توصية تجارية أوضح وأأمن للتنفيذ."
    if status in {"conflicting_evidence", "conflicting"}:
        return "بعد حسم التعارض، يصبح القرار التجاري قابلاً للتنفيذ بثقة أعلى."
    return "بعد قرارك، ينتقل التنفيذ إلى الصفحة المناسبة دون إعادة فتح التشخيص."


def destination_for_commitment_v1(card: Mapping[str, Any]) -> tuple[str, str]:
    """Return (href, label). Empty href = no navigation (commitment is wait)."""
    status = _norm(card.get("diagnosis_status") or "").casefold()
    if status in {"insufficient_evidence", "insufficient", "conflicting_evidence", "conflicting"}:
        return "#home", "العودة للملخص"
    href = _norm(card.get("view_details_href"))
    domain = _norm(card.get("business_domain") or card.get("decision_category")).casefold()
    diagnosis = _norm(card.get("diagnosis_ar"))
    if not href:
        if "communicat" in domain or "تواصل" in diagnosis or "رقم" in diagnosis:
            href = "#communication"
        elif "cart" in domain or "recover" in domain or "سلال" in diagnosis:
            href = "#carts"
        else:
            href = "#products"
    # Avoid looping back to Workspace explanation.
    if href.startswith("#workspace"):
        href = "#products"
    return href, "متابعة التنفيذ"


def card_from_diagnostic_publication_v1(pub: Mapping[str, Any]) -> dict[str, Any]:
    """Build a Workspace primary card aligned with Home's diagnostic story."""
    p = dict(pub) if isinstance(pub, Mapping) else {}
    status = _norm(p.get("diagnosis_status"))
    diagnosis = _norm(p.get("diagnosis_ar") or p.get("observation_ar"))
    family = _norm(p.get("diagnostic_family"))
    domain = "shipping"
    href = "#products"
    if "contact" in family or "followup" in family:
        domain = "communication"
        href = "#communication"
    elif "interest" in family or "product" in family:
        domain = "products"
        href = "#products"
    elif "payment" in family:
        domain = "operations"
        href = "#products"
    return {
        "decision_id": f"diagnostic:{_norm(p.get('diagnostic_id') or family or 'primary')}",
        "card_kind": "composed_decision",
        "constitution_v1": True,
        "gate_diagnostic_continuity_v1": True,
        "is_primary_decision": True,
        "has_decision": status not in {"insufficient_evidence", "conflicting_evidence"},
        "diagnosis_status": status,
        "diagnosis_ar": diagnosis,
        "observation_ar": _norm(p.get("observation_ar")),
        "why_ar": _norm(p.get("observation_ar")),
        "confidence_level": _norm(p.get("confidence_level")),
        "recommendation_ar": _norm(p.get("recommendation_ar")),
        "business_domain": domain,
        "decision_category": domain,
        "business_meaning_ar": diagnosis,
        "ignore_consequence_ar": "",
        "expected_outcome_ar": "",
        "view_details_href": href,
        "subject_ar": _norm(p.get("subject_id")),
        "diagnostic_family": family,
        "source_truth_types": ["diagnostic_reasoning_v1"],
    }


__all__ = [
    "card_from_diagnostic_publication_v1",
    "cartflow_responsibility_ar_v1",
    "commitment_ar_v1",
    "confidence_ar_v1",
    "consequence_ar_v1",
    "destination_for_commitment_v1",
    "diagnosis_ar_v1",
    "expected_outcome_ar_v1",
    "looks_like_cartflow_work",
    "why_believe_ar_v1",
]
