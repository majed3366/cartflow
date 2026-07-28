# -*- coding: utf-8 -*-
"""
Decision Workspace Operational Language V1.

Observation → Operational Meaning → Operational Guidance → Execution (when ready).
Consumes Diagnostic Reasoning, Execution Methodology, Decision Playbooks,
Executive Compression. No new engines. No constitution expansion.
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

# Card identities (WP8)
IDENTITY_OBSERVATION = "observation"
IDENTITY_GUIDANCE = "guidance"
IDENTITY_ACTION = "action"
IDENTITY_MONITORING = "monitoring"
IDENTITY_OPPORTUNITY = "opportunity"
IDENTITY_RISK = "risk"
IDENTITY_EXECUTION = "execution"
IDENTITY_RESULT = "result"

_IDENTITY_LABEL_AR = {
    IDENTITY_OBSERVATION: "ملاحظة",
    IDENTITY_GUIDANCE: "توجيه",
    IDENTITY_ACTION: "إجراء",
    IDENTITY_MONITORING: "مراقبة",
    IDENTITY_OPPORTUNITY: "فرصة",
    IDENTITY_RISK: "مخاطر",
    IDENTITY_EXECUTION: "تنفيذ",
    IDENTITY_RESULT: "نتيجة",
}

# Forbidden: investigative CartFlow work + management jargon
_FORBIDDEN_GUIDANCE_MARKERS = (
    "جمع الأدل",
    "جمع المزيد",
    "مزيد من الأدل",
    "اكتشف السبب",
    "مسار التحويل",
    "مسار شراء",
    "أدلة الطلب",
    "investigat",
    "funnel",
    "diagnos",
    "موقفاً تجارياً",
    "موقفا تجاريا",
    "قراراً تجارياً",
    "قرارا تجاريا",
    "حكم تجاري",
    "الحكم التجاري",
    "بوعي",
    "Commercial judgement",
    "business judgement",
    "business strategy",
)

_INVESTIGATIVE_OPENERS = (
    "اجمع",
    "اكتشف",
    "فكّر",
    "فكر",
    "investigat",
    "consider",
    "collect",
    "discover",
    "diagnos",
)


def _norm(v: Any) -> str:
    return str(v or "").strip()


def looks_like_cartflow_work(text: str) -> bool:
    """True when guidance is investigative / management jargon (forbidden)."""
    t = _norm(text)
    if not t:
        return False
    low = t.casefold()
    for p in _INVESTIGATIVE_OPENERS:
        if low.startswith(p.casefold()):
            return True
    for m in _FORBIDDEN_GUIDANCE_MARKERS:
        if m.casefold() in low:
            return True
    return False


def execution_is_ready_v1(readiness: str) -> bool:
    """Compat: destination eligibility when merchant can act (READY or external)."""
    return readiness in {READY, EXTERNAL_DEPENDENCY}


def action_is_ready_v1(readiness: str) -> bool:
    """Storytelling Action CTA — only when EM-001 READY (CEO / DS-001)."""
    return readiness == READY


def sanitize_merchant_story_text_v1(text: str) -> str:
    """Strip engine IDs / system crumbs from merchant-visible story text."""
    import re

    t = _norm(text)
    if not t:
        return ""
    # Remove common internal identifiers
    t = re.sub(r"\bcs:[A-Za-z0-9_\-:.]+\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bdiagnostic:[A-Za-z0-9_\-:.]+\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bdce:[A-Za-z0-9_\-:.]+\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\borv\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bpbl-?\d+\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t).strip(" -—·|")
    return t


def _blob(card: Mapping[str, Any]) -> str:
    return " ".join(
        [
            _norm(card.get("business_domain")),
            _norm(card.get("decision_category")),
            _norm(card.get("diagnostic_family")),
            _norm(card.get("diagnosis_ar")),
            _norm(card.get("observation_ar")),
            _norm(card.get("situation_kind")),
            _norm(card.get("decision_type")),
            _norm(card.get("card_kind")),
            _norm(card.get("subject_ar")),
        ]
    ).casefold()


def _subject_short(card: Mapping[str, Any]) -> str:
    subject = _norm(
        card.get("subject_ar")
        or card.get("product_name_ar")
        or card.get("affected_area_ar")
    )
    return subject.split("—")[0].strip() if subject else ""


def _affected_volume_hint(card: Mapping[str, Any]) -> str:
    for key in (
        "affected_customers_count",
        "customer_count",
        "cohort_size",
        "impact_volume",
        "cart_count",
        "affected_count",
    ):
        raw = card.get(key)
        if raw is None:
            continue
        try:
            n = int(raw)
        except (TypeError, ValueError):
            continue
        if n > 0:
            return str(n)
    return ""


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


def act_now_ar_v1(card: Mapping[str, Any], readiness: str) -> str:
    """Compat — not painted as a separate face row (merged into guidance/execution)."""
    if readiness == NEEDS_MORE_EVIDENCE:
        return "ليس الآن"
    if readiness == BLOCKED:
        return "ليس الآن"
    return "نعم"


def readiness_ar_v1(card: Mapping[str, Any], readiness: str) -> str:
    return act_now_ar_v1(card, readiness)


def confidence_ar_v1(card: Mapping[str, Any]) -> str:
    """Internal/compat — not painted on operational face."""
    return ""


def cartflow_responsibility_ar_v1(card: Mapping[str, Any]) -> str:
    return ""


def observation_ar_v1(card: Mapping[str, Any]) -> str:
    """Observable reality only — no diagnosis lecture, no engine IDs."""
    for key in (
        "observation_ar",
        "diagnosis_ar",
        "business_meaning_ar",
        "situation_summary_ar",
    ):
        v = sanitize_merchant_story_text_v1(_norm(card.get(key)))
        if v and not looks_like_cartflow_work(v):
            return v
    why = sanitize_merchant_story_text_v1(
        _norm(card.get("why_ar") or (card.get("explanation") or {}).get("why_here"))
    )
    subject = sanitize_merchant_story_text_v1(_subject_short(card))
    if why and not looks_like_cartflow_work(why):
        if subject and subject not in why and not subject.startswith("cs:"):
            return f"{subject}: {why}"
        return why
    if subject and not subject.startswith("cs:"):
        return f"العملاء يتفاعلون مع {subject} دون إتمام الشراء بوضوح."
    return "يغادر العملاء قبل إتمام الشراء."


def diagnosis_ar_v1(card: Mapping[str, Any]) -> str:
    """Compat alias — observation is the discovery face."""
    return observation_ar_v1(card)


def operational_meaning_ar_v1(card: Mapping[str, Any], observation: str) -> str:
    """Why this matters — must not repeat the observation verbatim."""
    for key in (
        "operational_meaning_ar",
        "ignore_consequence_ar",
        "business_consequence_ar",
        "business_impact_ar",
        "why_now_ar",
    ):
        v = _norm(card.get(key))
        if (
            v
            and v != observation
            and not looks_like_cartflow_work(v)
            and not v.endswith("؟")
            and not v.endswith("?")
        ):
            return v

    blob = _blob(card)
    subject = _subject_short(card)
    if "شحن" in (observation + blob) or "ship" in blob:
        if subject:
            return f"هذه الخطوة تضغط على إتمام شراء {subject}."
        return "هذه الخطوة تمثّل اختناقاً في مسار الشراء."
    if "اهتمام" in observation or "دون شراء" in observation or "interest" in blob:
        return "الاهتمام موجود بينما إتمام الشراء لا يتحقق."
    if "تواصل" in observation or "رقم" in observation or "contact" in blob:
        return "بدون وسيلة تواصل صالحة تتوقف استعادة السلات."
    if "دفع" in observation or "payment" in blob:
        return "تعثّر الدفع يمنع إكمال الطلبات الجاهزة للشراء."
    if "استعاد" in observation or "recover" in blob or "رسال" in observation:
        return "الفرصة موجودة في الرسالة لكن العودة للشراء ضعيفة."
    status = _norm(card.get("diagnosis_status") or "").casefold()
    if status in {"insufficient_evidence", "insufficient", "conflicting_evidence", "conflicting"}:
        return "أي تغيير الآن قد يعالج السبب الخطأ."
    return "تركه معلّقاً يبقي ضغط الإيراد دون معالجة واضحة."


def why_believe_ar_v1(card: Mapping[str, Any], diagnosis: str) -> str:
    """Compat — maps to operational meaning."""
    return operational_meaning_ar_v1(card, diagnosis)


def consequence_ar_v1(card: Mapping[str, Any]) -> str:
    return operational_meaning_ar_v1(card, observation_ar_v1(card))


def priority_reason_ar_v1(card: Mapping[str, Any], *, is_primary: bool) -> str:
    """
    One sentence: why this is today's highest priority.
    Must use store-specific evidence — not repeat diagnosis.
    """
    if not is_primary:
        return ""
    explicit = _norm(card.get("priority_reason_ar") or card.get("why_priority_ar"))
    if explicit and not looks_like_cartflow_work(explicit):
        return explicit

    observation = observation_ar_v1(card)
    blob = _blob(card)
    subject = _subject_short(card)
    vol = _affected_volume_hint(card)
    readiness = execution_readiness_v1(card)
    conf = _norm(
        card.get("confidence_level")
        or card.get("decision_confidence")
        or card.get("confidence")
        or ""
    ).casefold()

    if vol:
        return f"هذا القرار يؤثر على أكبر مجموعة عملاء اليوم ({vol})."
    if "شحن" in (observation + blob) or "ship" in blob:
        if subject:
            return f"مرحلة الشحن لـ {subject} هي أكبر اختناق ظاهر في رحلة العميل اليوم."
        return "هذه المرحلة تمثّل أكبر اختناق ظاهر في رحلة العميل اليوم."
    if any(k in blob for k in ("recover", "رسال", "whatsapp", "استعاد")):
        return "تأخير هذا القرار قد يقلل فرص الاستعادة اليوم."
    if "اهتمام" in observation or "دون شراء" in observation or "interest" in blob:
        if subject:
            return f"هذه أعلى فرصة ظاهرة اليوم لتحسين التحويل على {subject}."
        return "هذه أعلى فرصة ظاهرة اليوم لتحسين التحويل."
    if "تواصل" in observation or "رقم" in observation or "contact" in blob:
        return "تأخير هذا القرار قد يقلل فرص الاستعادة اليوم."
    if readiness == NEEDS_MORE_EVIDENCE and conf in {"high", "عال", "عالية", "supported"}:
        return "هذا أقوى دليل متاح حالياً رغم أن التنفيذ غير جاهز بعد."
    if conf in {"high", "عال", "عالية", "supported"}:
        return "هذا أقوى دليل متاح حالياً لتوجيه العمل اليوم."
    if subject:
        return f"هذا أعلى أولوية ظاهرة اليوم بخصوص {subject}."
    return "هذا أعلى أولوية ظاهرة من أدلة المتجر اليوم."


def cartflow_continues_ar_v1(card: Mapping[str, Any], readiness: str) -> str:
    """Shown only when not executable — what CartFlow keeps doing."""
    if execution_is_ready_v1(readiness):
        return ""
    if readiness == BLOCKED:
        return "CartFlow يراقب المتطلب الناقص ولن يقترح تنفيذاً قبل اكتماله."
    blob = _blob(card)
    if "شحن" in blob or "ship" in blob:
        return (
            "CartFlow يواصل التمييز بين تكلفة الشحن ووقت التوصيل وخيارات الشحن "
            "قبل أي توجيه تنفيذي."
        )
    if "payment" in blob or "دفع" in blob:
        return "CartFlow يواصل رصد تعثّر الدفع وطرق الدفع الظاهرة عند الدفع."
    if "interest" in blob or "product" in blob:
        return "CartFlow يواصل ربط اهتمام المنتج بسبب المغادرة قبل الشراء."
    if "contact" in blob or "تواصل" in blob:
        return "CartFlow يواصل تتبع أين ينقطع التقاط وسيلة التواصل."
    return "CartFlow يواصل جمع الأدلة حتى يصبح التوجيه التنفيذي واضحاً."


def operational_guidance_ar_v1(card: Mapping[str, Any]) -> str:
    """Decision sentence (one action) — storytelling Decision beat."""
    return decision_sentence_ar_v1(card)


def decision_sentence_ar_v1(card: Mapping[str, Any]) -> str:
    """Exactly one Decision sentence — no report, no engine language."""
    readiness = execution_readiness_v1(card)
    if readiness == NEEDS_MORE_EVIDENCE:
        blob = _blob(card)
        if "شحن" in blob or "ship" in blob:
            return "لا تغيّر سياسة الشحن الآن."
        return "لا تُجرِ تغييراً الآن."
    if readiness == BLOCKED:
        return "أرجئ التنفيذ حتى يُستكمل المتطلب الناقص."

    for key in (
        "decision_sentence_ar",
        "operational_guidance_ar",
        "commitment_ar",
        "merchant_commitment_ar",
        "recommended_action",
        "first_step_ar",
        "required_merchant_action",
        "action_label_ar",
        "recommendation_ar",
    ):
        v = sanitize_merchant_story_text_v1(_norm(card.get(key)))
        if v and not looks_like_cartflow_work(v):
            # Keep one sentence
            for sep in ("。", ". ", "۔", "\n"):
                if sep in v:
                    v = v.split(sep)[0].strip()
                    break
            return v

    domain = execution_domain_v1(card)
    subject = sanitize_merchant_story_text_v1(_subject_short(card))
    diagnosis = observation_ar_v1(card)
    blob = _blob(card)

    if domain == EXEC_DOMAIN_INTERNAL:
        if "تواصل" in diagnosis or "رقم" in diagnosis or "contact" in blob:
            return "افتح السلال بلا أرقام."
        if "recover" in blob or "رسال" in diagnosis:
            return "راجع الرسالة الأولى للاسترجاع."
        return "افتح السلال المعنية."
    if "شحن" in (subject + diagnosis + blob) or "ship" in blob:
        return "افتح إعدادات الشحن في المنصة."
    if "دفع" in diagnosis or "payment" in blob:
        return "راجع طرق الدفع المتاحة أثناء الدفع."
    if "interest" in blob or "اهتمام" in diagnosis:
        if subject:
            return f"راجع صفحة المنتج {subject}."
        return "راجع صفحة المنتج."
    if subject:
        return f"راجع {subject} في المنصة."
    if domain == EXEC_DOMAIN_BUSINESS:
        return "نفّذ الخطوة المطلوبة في عملك."
    return "راجع العنصر المحدد في المنصة."


def commitment_ar_v1(card: Mapping[str, Any]) -> str:
    """Compat — Decision sentence is the merchant task."""
    return decision_sentence_ar_v1(card)


def where_execute_ar_v1(card: Mapping[str, Any], domain: str, readiness: str) -> str:
    if not execution_is_ready_v1(readiness):
        return ""
    if domain == EXEC_DOMAIN_INTERNAL:
        blob = _blob(card)
        if any(k in blob for k in ("communicat", "تواصل", "whatsapp", "محادث", "contact")):
            return "التواصل داخل CartFlow"
        if any(k in blob for k in ("recover", "رسال")):
            return "رسائل الاستعادة داخل CartFlow"
        return "السلال داخل CartFlow"
    if domain == EXEC_DOMAIN_BUSINESS:
        return "العمل التشغيلي خارج المنصة"
    blob = _blob(card)
    if any(k in blob for k in ("ship", "شحن", "deliver", "توصيل")):
        return "إعدادات الشحن في منصة المتجر"
    if any(k in blob for k in ("payment", "دفع")):
        return "إعدادات الدفع في منصة المتجر"
    return "صفحة المنتج أو التسعير في منصة المتجر"


def how_execute_ar_v1(card: Mapping[str, Any], domain: str, readiness: str) -> str:
    if not execution_is_ready_v1(readiness):
        return ""
    explicit = _norm(card.get("execution_how_ar") or card.get("how_ar"))
    if explicit and not looks_like_cartflow_work(explicit):
        return explicit
    guidance = operational_guidance_ar_v1(card)
    blob = _blob(card)
    if "شحن" in blob or "ship" in blob:
        return "قارن تكلفة الشحن ووقت التوصيل وخيارات الشحن للشريحة المتأثرة."
    if "payment" in blob or "دفع" in blob:
        return "تحقق من تفعيل طرق الدفع الظاهرة عند الدفع وأي أخطاء تظهر للعميل."
    if "recover" in blob or "رسال" in blob:
        return "راجع وضوح العرض وزر العودة في رسالة الاستعادة الأولى."
    if "contact" in blob or "تواصل" in blob:
        return "حدد خطوة المسار التي تفقد رقم الجوال قبل المتابعة."
    if domain == EXEC_DOMAIN_INTERNAL:
        return "افتح الحالات المعنية ونفّذ المتابعة على السلات المحددة."
    return f"راجع العنصر المذكور ثم غيّر ما يلزم: {guidance}"


def avoid_ar_v1(card: Mapping[str, Any], readiness: str) -> str:
    return ""


def verify_ar_v1(card: Mapping[str, Any], readiness: str) -> str:
    return expected_outcome_ar_v1(card, "") if execution_is_ready_v1(readiness) else ""


def expected_outcome_ar_v1(card: Mapping[str, Any], consequence: str) -> str:
    if not execution_is_ready_v1(execution_readiness_v1(card)):
        return ""
    for key in (
        "expected_outcome_ar",
        "reality_validation_ar",
        "success_metric_ar",
    ):
        v = _norm(card.get(key))
        if v and not looks_like_cartflow_work(v):
            return v
    blob = _blob(card)
    subject = _subject_short(card)
    if "شحن" in blob or "ship" in blob:
        return "انخفاض المغادرة بعد خطوة الشحن وارتفاع إتمام الشراء."
    if "payment" in blob or "دفع" in blob:
        return "انخفاض التعثّر عند الدفع وارتفاع إكمال الطلب."
    if "recover" in blob or "رسال" in blob:
        return "ارتفاع العودة من رسالة الاستعادة إلى إتمام الشراء."
    if "contact" in blob or "تواصل" in blob:
        return "ارتفاع السلات القابلة للمتابعة برقم صالح."
    if subject:
        return f"ارتفاع إتمام الشراء لـ {subject}."
    if consequence and not looks_like_cartflow_work(consequence):
        return consequence
    return "تحسن واضح في إتمام الشراء على المسار المتأثر."


def execution_what_ar_v1(card: Mapping[str, Any], readiness: str) -> str:
    """WHAT exactly should change — only when executable."""
    if not execution_is_ready_v1(readiness):
        return ""
    return operational_guidance_ar_v1(card)


def card_identity_v1(card: Mapping[str, Any], readiness: str) -> str:
    """WP8 — not every card is forced into Decision."""
    explicit = _norm(card.get("card_identity") or card.get("operational_identity")).casefold()
    for key in (
        IDENTITY_OBSERVATION,
        IDENTITY_GUIDANCE,
        IDENTITY_ACTION,
        IDENTITY_MONITORING,
        IDENTITY_OPPORTUNITY,
        IDENTITY_RISK,
        IDENTITY_EXECUTION,
        IDENTITY_RESULT,
    ):
        if explicit == key or explicit == key[:4]:
            return key

    blob = _blob(card)
    if readiness == NEEDS_MORE_EVIDENCE:
        return IDENTITY_OBSERVATION
    if readiness == BLOCKED:
        return IDENTITY_MONITORING
    if any(k in blob for k in ("risk", "مخاطر", "vip", "فقد")):
        return IDENTITY_RISK
    if any(k in blob for k in ("interest", "opportunity", "فرصة", "اهتمام")):
        return IDENTITY_OPPORTUNITY
    if execution_is_ready_v1(readiness):
        return IDENTITY_EXECUTION if readiness == READY else IDENTITY_ACTION
    return IDENTITY_GUIDANCE


def card_identity_label_ar_v1(identity: str) -> str:
    return _IDENTITY_LABEL_AR.get(identity, "توجيه")


def destination_for_commitment_v1(card: Mapping[str, Any]) -> tuple[str, str]:
    """
    Action destination — only when READY (storytelling Action beat).
    Never #workspace loops. Never fake destinations when not READY.
    """
    readiness = execution_readiness_v1(card)
    if not action_is_ready_v1(readiness):
        return "", ""

    domain = execution_domain_v1(card)
    blob = _blob(card)
    inbound = _norm(card.get("view_details_href"))
    if inbound.startswith("#workspace"):
        inbound = ""

    if domain == EXEC_DOMAIN_INTERNAL:
        if any(
            k in blob
            for k in ("communicat", "تواصل", "whatsapp", "محادث", "contact", "followup")
        ):
            href = inbound if inbound.startswith("#communication") else "#communication"
            return href, "افتح التواصل"
        href = inbound if inbound.startswith("#carts") else "#carts"
        return href, "افتح السلال"

    if domain == EXEC_DOMAIN_BUSINESS:
        return "", "نفّذ في عملك"

    if any(k in blob for k in ("ship", "شحن", "payment", "دفع", "deliver", "توصيل")):
        href = inbound if inbound.startswith("#settings") else "#settings"
        return href, "افتح إعدادات الشحن أو الدفع"
    if inbound.startswith("#products") or inbound.startswith("#settings"):
        return inbound, "افتح العنصر في المنصة"
    return "#products", "افتح صفحة المنتج"


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
        "observation_ar": _norm(p.get("observation_ar")) or diagnosis,
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
    "IDENTITY_ACTION",
    "IDENTITY_EXECUTION",
    "IDENTITY_GUIDANCE",
    "IDENTITY_MONITORING",
    "IDENTITY_OBSERVATION",
    "IDENTITY_OPPORTUNITY",
    "IDENTITY_RESULT",
    "IDENTITY_RISK",
    "NEEDS_MORE_EVIDENCE",
    "READY",
    "action_is_ready_v1",
    "act_now_ar_v1",
    "avoid_ar_v1",
    "card_from_diagnostic_publication_v1",
    "card_identity_label_ar_v1",
    "card_identity_v1",
    "cartflow_continues_ar_v1",
    "cartflow_responsibility_ar_v1",
    "commitment_ar_v1",
    "confidence_ar_v1",
    "consequence_ar_v1",
    "decision_sentence_ar_v1",
    "destination_for_commitment_v1",
    "diagnosis_ar_v1",
    "execution_domain_v1",
    "execution_is_ready_v1",
    "execution_readiness_v1",
    "execution_what_ar_v1",
    "expected_outcome_ar_v1",
    "how_execute_ar_v1",
    "looks_like_cartflow_work",
    "observation_ar_v1",
    "operational_guidance_ar_v1",
    "operational_meaning_ar_v1",
    "priority_reason_ar_v1",
    "readiness_ar_v1",
    "sanitize_merchant_story_text_v1",
    "verify_ar_v1",
    "where_execute_ar_v1",
    "why_believe_ar_v1",
]
