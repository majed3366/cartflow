# -*- coding: utf-8 -*-
"""
Decision Workspace Refinement V2 — Executive Decision Room.

CartFlow owns: observation, evidence, diagnosis, confidence,
execution readiness, reality validation.
Merchant owns: commercial judgement, execution, business trade-offs.

Never ask the merchant to investigate, diagnose, or collect evidence.
Integrates Execution Methodology V1 (EM-001 / EM-002) without new engines.
"""
from __future__ import annotations

from typing import Any, Mapping

# Execution domains (methodology Types A / B / C)
EXEC_DOMAIN_INTERNAL = "internal"
EXEC_DOMAIN_PLATFORM = "platform"
EXEC_DOMAIN_BUSINESS = "business"

# EM-001 readiness
READY = "READY"
NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
BLOCKED = "BLOCKED"
EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"

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


def _blob(card: Mapping[str, Any]) -> str:
    return " ".join(
        [
            _norm(card.get("business_domain")),
            _norm(card.get("decision_category")),
            _norm(card.get("diagnostic_family")),
            _norm(card.get("diagnosis_ar")),
            _norm(card.get("situation_kind")),
            _norm(card.get("decision_type")),
            _norm(card.get("card_kind")),
        ]
    ).casefold()


def execution_domain_v1(card: Mapping[str, Any]) -> str:
    """Map Decision → Internal / Platform / Business (methodology Types A/B/C)."""
    explicit = _norm(card.get("execution_domain") or card.get("execution_type")).casefold()
    if explicit in {"internal", "a", "type_a", "type-a"}:
        return EXEC_DOMAIN_INTERNAL
    if explicit in {"platform", "b", "type_b", "type-b", "external"}:
        return EXEC_DOMAIN_PLATFORM
    if explicit in {"business", "c", "type_c", "type-c", "ops_business"}:
        return EXEC_DOMAIN_BUSINESS

    blob = _blob(card)
    # Type A — inside CartFlow
    if any(
        k in blob
        for k in (
            "cart",
            "recover",
            "سلال",
            "سلة",
            "communicat",
            "تواصل",
            "whatsapp",
            "conversation",
            "محادث",
            "followup",
            "follow_up",
            "contact",
        )
    ):
        return EXEC_DOMAIN_INTERNAL
    # Type C — merchant business (not platform UI)
    if any(
        k in blob
        for k in (
            "packag",
            "تغليف",
            "photograph",
            "تصوير",
            "negotiat",
            "تفاوض",
            "contract",
            "عقد",
            "promotion",
            "ترويج",
            "policy",
            "سياسة تشغيل",
        )
    ):
        return EXEC_DOMAIN_BUSINESS
    # Type B — commerce platform (shipping, product, pricing, payment, settings)
    return EXEC_DOMAIN_PLATFORM


def execution_readiness_v1(card: Mapping[str, Any]) -> str:
    """EM-001 — one readiness state per Decision."""
    explicit = _norm(card.get("execution_readiness") or card.get("readiness_state"))
    if explicit in {READY, NEEDS_MORE_EVIDENCE, BLOCKED, EXTERNAL_DEPENDENCY}:
        return explicit

    status = _norm(
        card.get("diagnosis_status") or card.get("decision_status") or ""
    ).casefold()
    if status in {"insufficient_evidence", "insufficient"} or card.get("has_decision") is False:
        return NEEDS_MORE_EVIDENCE
    if status in {"conflicting_evidence", "conflicting"}:
        return NEEDS_MORE_EVIDENCE
    if status in {"blocked", "prerequisite_missing"}:
        return BLOCKED

    domain = execution_domain_v1(card)
    if domain in {EXEC_DOMAIN_PLATFORM, EXEC_DOMAIN_BUSINESS}:
        return EXTERNAL_DEPENDENCY
    return READY


def readiness_ar_v1(card: Mapping[str, Any], readiness: str) -> str:
    if readiness == NEEDS_MORE_EVIDENCE:
        return (
            "لست جاهزاً للتنفيذ بعد — الأدلة غير كافية. "
            "CartFlow يكمل جمع الأدلة والتحقق."
        )
    if readiness == BLOCKED:
        return (
            "التنفيذ متوقف الآن لوجود متطلب ناقص "
            "(إعداد أو قدرة أو دليل إلزامي)."
        )
    if readiness == EXTERNAL_DEPENDENCY:
        domain = execution_domain_v1(card)
        if domain == EXEC_DOMAIN_BUSINESS:
            return (
                "جاهز كحكم تجاري — التنفيذ يتم في عملك، "
                "وليس داخل CartFlow أو لوحة التحكم فقط."
            )
        return (
            "جاهز كحكم تجاري — التنفيذ يتم في منصة المتجر "
            "(زد / سلة / Shopify)، وCartFlow يتحقق لاحقاً من النتيجة."
        )
    return "جاهز للتنفيذ — التشخيص والأدلة يكفيان لقرار تجاري واضح."


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
        return "لذلك لا نطلب منك تغييراً تجارياً قبل اكتمال الأدلة."
    if status in {"conflicting_evidence", "conflicting"}:
        return "لذلك نؤجل الالتزام بسبب تعارض الأدلة — لا تُحسم سبباً واحداً بنفسك."
    if level in {"high", "عال", "عالية", "supported"}:
        return "لذلك يمكن البناء على هذا التشخيص بثقة كافية لقرار واضح."
    if level in {"low", "منخفض", "منخفضة"}:
        return "لذلك يبقى الحكم التجاري حذراً رغم وضوح الاتجاه."
    explicit = _norm(card.get("confidence_ar") or card.get("decision_confidence_ar"))
    if explicit and not looks_like_cartflow_work(explicit):
        return explicit
    return "لذلك يمكن البناء على التشخيص بحذر مناسب."


def cartflow_responsibility_ar_v1(card: Mapping[str, Any]) -> str:
    readiness = execution_readiness_v1(card)
    if readiness == NEEDS_MORE_EVIDENCE:
        return (
            "CartFlow يتولى الملاحظة والأدلة والتشخيص وجاهزية التنفيذ. "
            "لا تُحقّق ولا تجمع أدلة بنفسك."
        )
    if readiness == BLOCKED:
        return "CartFlow يحدد المتطلب الناقص ويُبقي التشخيص تحت المراقبة حتى يُرفع الحظر."
    return (
        "CartFlow أنجز الملاحظة والأدلة والتشخيص وجاهزية التنفيذ. "
        "دورك حكم تجاري واحد — لا إعادة التشخيص."
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
    if "شحن" in diagnosis:
        return "لأن المغادرة تتكرر عند الشحن دون سبب قابل للفصل بعد."
    if "اهتمام" in diagnosis or "دون شراء" in diagnosis:
        return "لأن الاهتمام بالمنتج واضح بينما إتمام الشراء لا يتحقق بنفس الوضوح."
    if "تواصل" in diagnosis or "رقم" in diagnosis:
        return "لأن المتابعة تتعطل عندما لا تتوفر وسيلة تواصل صالحة."
    return "لأن ملاحظات المتجر الحالية تدعم هذا التشخيص بعد استبعاد التفسيرات الأضعف."


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
    return "إذا بقي الأمر معلّقاً، يستمر ضغط الإيراد دون قرار واضح."


def where_execute_ar_v1(card: Mapping[str, Any], domain: str, readiness: str) -> str:
    if readiness == NEEDS_MORE_EVIDENCE:
        return "لا وجهة تنفيذ الآن — انتظر اكتمال الأدلة داخل CartFlow."
    if readiness == BLOCKED:
        return "لا وجهة تنفيذ حتى يُستكمل المتطلب الناقص."
    if domain == EXEC_DOMAIN_INTERNAL:
        blob = _blob(card)
        if any(k in blob for k in ("communicat", "تواصل", "whatsapp", "محادث", "contact")):
            return "داخل CartFlow — صفحة التواصل."
        return "داخل CartFlow — صفحة السلال."
    if domain == EXEC_DOMAIN_BUSINESS:
        return "داخل عملك التشغيلي (خارج CartFlow وخارج لوحة المنصة)."
    # platform
    blob = _blob(card)
    if any(k in blob for k in ("ship", "شحن", "payment", "دفع", "setting")):
        return "في منصة المتجر — إعدادات الشحن أو الدفع أو التوصيل."
    return "في منصة المتجر — صفحة المنتج أو التسعير أو العرض."


def how_execute_ar_v1(card: Mapping[str, Any], domain: str, readiness: str) -> str:
    if readiness == NEEDS_MORE_EVIDENCE:
        return "لا خطوات تنفيذ — CartFlow يواصل الأدلة حتى تصبح جاهزية التنفيذ READY."
    if readiness == BLOCKED:
        return "أكمل المتطلب الناقص أولاً، ثم يعود القرار لجاهزية التنفيذ."
    if domain == EXEC_DOMAIN_INTERNAL:
        return (
            "افتح الوجهة أدناه ونفّذ الالتزام التشغيلي هناك. "
            "لا تعد إلى مساحة القرار لإعادة التشخيص."
        )
    if domain == EXEC_DOMAIN_BUSINESS:
        return (
            "نفّذ القرار في عملك (تصوير، تغليف، تفاوض، ترويج، سياسة). "
            "CartFlow لا ينفّذ عنك — ويراقب النتيجة لاحقاً."
        )
    return (
        "ادخل منصة المتجر وطبق التغيير المطلوب هناك. "
        "CartFlow لا يتحكم في المنصة — ويتحقق من أثر القرار عبر الأدلة."
    )


def avoid_ar_v1(card: Mapping[str, Any], readiness: str) -> str:
    if readiness == NEEDS_MORE_EVIDENCE:
        return "تجنّب تغيير السياسة أو التسعير أو الشحن قبل اكتمال الأدلة."
    if readiness == BLOCKED:
        return "تجنّب الالتفاف على المتطلب الناقص بحلول مؤقتة غير موثوقة."
    return (
        "تجنّب إعادة التشخيص بنفسك، وتجنّب فتح مساحة القرار كحلقة مغلقة، "
        "وتجنّب تنفيذ عدة تغييرات دفعة واحدة قبل التحقق."
    )


def verify_ar_v1(card: Mapping[str, Any], readiness: str) -> str:
    """EM-002 — how CartFlow will know whether it worked."""
    if readiness == NEEDS_MORE_EVIDENCE:
        return (
            "يتحقق CartFlow بتعزيز الأدلة أولاً، ثم يعيد تقييم جاهزية التنفيذ "
            "قبل أي التزام تجاري."
        )
    if readiness == BLOCKED:
        return "يتحقق CartFlow بزوال الحظر وظهور الأدلة الكافية لإعادة فتح التنفيذ."
    return (
        "بعد التنفيذ يقارن CartFlow قبل/بعد: الأدلة، التحويل، التخلي، "
        "وقوة التشخيص — ثم يحدّث حالة القرار (محسوم / مراقبة / تصعيد)."
    )


def commitment_ar_v1(card: Mapping[str, Any]) -> str:
    """Merchant commercial judgement only — never CartFlow investigative work."""
    readiness = execution_readiness_v1(card)
    if readiness == NEEDS_MORE_EVIDENCE:
        return (
            "لا تغيّر السياسة الآن. "
            "انتظر حتى يُكمل CartFlow الأدلة ويعلن جاهزية التنفيذ."
        )
    if readiness == BLOCKED:
        return "أرجئ التنفيذ حتى يُرفع الحظر — لا تفتح مسارات بديلة غير مضمونة."

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

    domain = execution_domain_v1(card)
    subject = _norm(card.get("subject_ar") or card.get("product_name_ar"))
    short = subject.split("—")[0].strip() if subject else ""
    diagnosis = _norm(card.get("diagnosis_ar"))

    if domain == EXEC_DOMAIN_INTERNAL:
        if "تواصل" in diagnosis or "رقم" in diagnosis or "communicat" in _blob(card):
            return "قرّر أولوية إصلاح التقاط وسيلة التواصل في مسار الشراء."
        return "قرّر التعامل التشغيلي المطلوب على السلال المعنية الآن."
    if "شحن" in (subject + diagnosis) or "ship" in _blob(card):
        return "قرّر إن كنت ستعدّل سياسة الشحن في المنصة أم تبقيها."
    if short:
        return f"قرّر الموقف التجاري بخصوص {short} بناءً على التشخيص الحالي."
    if domain == EXEC_DOMAIN_BUSINESS:
        return "قرّر الإجراء التشغيلي في عملك — ثم دع CartFlow يتحقق من الأثر."
    return "اتخذ قراراً تجارياً واحداً بناءً على التشخيص — أو أرجئه بوعي."


def expected_outcome_ar_v1(card: Mapping[str, Any], consequence: str) -> str:
    """Kept for compatibility; verify_ar_v1 is the executive verification line."""
    return verify_ar_v1(card, execution_readiness_v1(card))


def destination_for_commitment_v1(card: Mapping[str, Any]) -> tuple[str, str]:
    """
    Route by execution domain — never fixed Products, never #workspace loops.
    Empty href = no in-app navigation (business wait / business ops).
    """
    readiness = execution_readiness_v1(card)
    if readiness == NEEDS_MORE_EVIDENCE:
        return "#home", "العودة للملخص — CartFlow يكمل الأدلة"
    if readiness == BLOCKED:
        return "#settings", "راجع الإعدادات المطلوبة"

    domain = execution_domain_v1(card)
    blob = _blob(card)
    inbound = _norm(card.get("view_details_href"))

    # Never loop into Workspace explanation.
    if inbound.startswith("#workspace"):
        inbound = ""

    if domain == EXEC_DOMAIN_INTERNAL:
        if any(
            k in blob
            for k in ("communicat", "تواصل", "whatsapp", "محادث", "contact", "followup")
        ):
            href = "#communication"
            if inbound.startswith("#communication"):
                href = inbound
            return href, "نفّذ داخل CartFlow — التواصل"
        href = "#carts"
        if inbound.startswith("#carts"):
            href = inbound
        return href, "نفّذ داخل CartFlow — السلال"

    if domain == EXEC_DOMAIN_BUSINESS:
        # No fake Products dump — merchant acts outside the app.
        return "", "نفّذ في عملك — CartFlow يتحقق لاحقاً"

    # Platform
    if any(k in blob for k in ("ship", "شحن", "payment", "دفع", "deliver", "توصيل")):
        href = "#settings"
        if inbound.startswith("#settings"):
            href = inbound
        return href, "نفّذ في منصة المتجر — عبر الإعدادات"
    if inbound.startswith("#products") or inbound.startswith("#settings"):
        return inbound, "نفّذ في منصة المتجر"
    return "#products", "نفّذ في منصة المتجر — المنتج"


def card_from_diagnostic_publication_v1(pub: Mapping[str, Any]) -> dict[str, Any]:
    """Build a Workspace primary card aligned with Home's diagnostic story."""
    p = dict(pub) if isinstance(pub, Mapping) else {}
    status = _norm(p.get("diagnosis_status"))
    diagnosis = _norm(p.get("diagnosis_ar") or p.get("observation_ar"))
    family = _norm(p.get("diagnostic_family"))
    domain = "shipping"
    href = "#settings"
    exec_domain = EXEC_DOMAIN_PLATFORM
    if "contact" in family or "followup" in family:
        domain = "communication"
        href = "#communication"
        exec_domain = EXEC_DOMAIN_INTERNAL
    elif "interest" in family or "product" in family:
        domain = "products"
        href = "#products"
        exec_domain = EXEC_DOMAIN_PLATFORM
    elif "payment" in family:
        domain = "operations"
        href = "#settings"
        exec_domain = EXEC_DOMAIN_PLATFORM
    elif "cart" in family or "recover" in family:
        domain = "carts"
        href = "#carts"
        exec_domain = EXEC_DOMAIN_INTERNAL
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
        "execution_domain": exec_domain,
        "business_meaning_ar": diagnosis,
        "ignore_consequence_ar": "",
        "expected_outcome_ar": "",
        "view_details_href": href,
        "subject_ar": _norm(p.get("subject_id")),
        "diagnostic_family": family,
        "source_truth_types": ["diagnostic_reasoning_v1"],
    }


__all__ = [
    "BLOCKED",
    "EXEC_DOMAIN_BUSINESS",
    "EXEC_DOMAIN_INTERNAL",
    "EXEC_DOMAIN_PLATFORM",
    "EXTERNAL_DEPENDENCY",
    "NEEDS_MORE_EVIDENCE",
    "READY",
    "avoid_ar_v1",
    "card_from_diagnostic_publication_v1",
    "cartflow_responsibility_ar_v1",
    "commitment_ar_v1",
    "confidence_ar_v1",
    "consequence_ar_v1",
    "destination_for_commitment_v1",
    "diagnosis_ar_v1",
    "execution_domain_v1",
    "execution_readiness_v1",
    "expected_outcome_ar_v1",
    "how_execute_ar_v1",
    "looks_like_cartflow_work",
    "readiness_ar_v1",
    "verify_ar_v1",
    "where_execute_ar_v1",
    "why_believe_ar_v1",
]
