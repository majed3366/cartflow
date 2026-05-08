# -*- coding: utf-8 -*-
"""
آلة حالات مسار المحادثة التفاعلية — تتبع وانتقال دون إرسال تلقائي.
تُحدَّث عبر ‎cf_behavioral‎ فقط عند رد العميل.
"""
from __future__ import annotations

from typing import Any, Optional

STAGE_PRICE_OBJECTION = "price_objection"
STAGE_VALUE_REASSURANCE = "value_reassurance"
STAGE_ALTERNATIVE_CONSIDERATION = "alternative_consideration"
STAGE_CHECKOUT_READY = "checkout_ready"
STAGE_SHIPPING_QUESTIONS = "shipping_questions"
STAGE_HESITATION_FOLLOWUP = "hesitation_followup"

_STAGE_LABELS_AR: dict[str, str] = {
    STAGE_PRICE_OBJECTION: "اعتراض سعر — بداية المسار",
    STAGE_VALUE_REASSURANCE: "طمأنة قيمة",
    STAGE_ALTERNATIVE_CONSIDERATION: "مقارنة بدائل",
    STAGE_CHECKOUT_READY: "جاهز لإكمال الطلب",
    STAGE_SHIPPING_QUESTIONS: "أسئلة شحن وتوصيل",
    STAGE_HESITATION_FOLLOWUP: "متابعة تردد لطيفة",
}


def stage_label_ar(stage_key: str) -> str:
    k = (stage_key or "").strip()
    return _STAGE_LABELS_AR.get(k, k or "مسار تفاعلي")


def _norm_msg(msg: str) -> str:
    t = (msg or "").strip().lower()
    for a, b in (
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ى", "ي"),
        ("ة", "ه"),
    ):
        t = t.replace(a, b)
    return " ".join(t.split())


def asks_alternative_or_comparison(message: str) -> bool:
    m = _norm_msg(message)
    return any(
        k in m
        for k in (
            "ارخص",
            "أرخص",
            "اغلى",
            "أغلى",
            "خيار",
            "بديل",
            "بدل",
            "غيره",
            "غيرها",
            "ثاني",
            "ثانيه",
            "ثانية",
            "مقارنه",
            "مقارنة",
            "افكر",
            "أفكر",
            "اشوف",
            "أشوف",
            "في غير",
            "فيه غير",
        )
    )


def _norm_intent_key(intent: str) -> str:
    k = (intent or "").strip().lower()
    return "delivery" if k == "shipping" else k


def initial_stage_for_intent(intent: str) -> str:
    eff = _norm_intent_key(intent)
    if eff == "price":
        return STAGE_PRICE_OBJECTION
    if eff in ("delivery", "shipping"):
        return STAGE_SHIPPING_QUESTIONS
    if eff == "ready_to_buy":
        return STAGE_CHECKOUT_READY
    if eff == "hesitation":
        return STAGE_HESITATION_FOLLOWUP
    if eff in ("warranty", "quality"):
        return STAGE_VALUE_REASSURANCE
    return STAGE_HESITATION_FOLLOWUP


def path_label_for_stage(stage: str, intent: str) -> str:
    eff = _norm_intent_key(intent)
    if stage == STAGE_ALTERNATIVE_CONSIDERATION:
        return "قيمة → بدائل → إغلاق"
    if stage == STAGE_CHECKOUT_READY or eff == "ready_to_buy":
        return "دفع نحو إكمال الطلب"
    if stage == STAGE_SHIPPING_QUESTIONS or eff in ("delivery", "shipping"):
        return "شحن → توضيح → إغلاق"
    if stage == STAGE_PRICE_OBJECTION:
        return "اعتراض سعر → طمأنة → (بديل / عرض ناعم)"
    if stage == STAGE_VALUE_REASSURANCE:
        return "طمأنة قيمة → بديل اختياري → إغلاق"
    return "مسار مرن حسب ردود العميل"


def compute_adaptive_transition(
    *,
    prev_stage: str,
    prev_intent: str,
    new_intent: str,
    customer_message: str,
    turn_index: int,
) -> tuple[str, str, str]:
    """
    يُرجع (المرحلة الجديدة، سبب الانتقال بالعربية، وصف المسار المختصر).
    """
    msg = (customer_message or "").strip()
    p_st = (prev_stage or "").strip()
    p_in = _norm_intent_key(prev_intent)
    n_in = _norm_intent_key(new_intent)

    if turn_index <= 1 or not p_st:
        st = initial_stage_for_intent(new_intent)
        return (
            st,
            "أول رد تفاعلي — بداية المسار وفق نية آخر رسالة.",
            path_label_for_stage(st, new_intent),
        )

    # طلب بديل بعد اعتراض سعر — حتى لو لُخّص النص كـ ‎other‎ خارج نية السعر
    if (
        p_st == STAGE_PRICE_OBJECTION
        and asks_alternative_or_comparison(msg)
        and n_in not in ("ready_to_buy", "delivery", "shipping")
    ):
        return (
            STAGE_ALTERNATIVE_CONSIDERATION,
            "انتقال إلى مقارنة البدائل — العميل طلب خياراً أو سعراً أخف.",
            path_label_for_stage(STAGE_ALTERNATIVE_CONSIDERATION, "price"),
        )

    # تغيير محور واضح
    if p_in and n_in and p_in != n_in and n_in not in (p_in,):
        st2 = initial_stage_for_intent(new_intent)
        return (
            st2,
            f"تغيير محور الاهتمام من مسار سابق إلى «{n_in}» — إعادة ضبط المرحلة.",
            path_label_for_stage(st2, new_intent),
        )

    if p_st == STAGE_PRICE_OBJECTION and n_in == "price":
        if asks_alternative_or_comparison(msg):
            return (
                STAGE_ALTERNATIVE_CONSIDERATION,
                "انتقال إلى مقارنة البدائل — العميل طلب خياراً أو سعراً أخف.",
                path_label_for_stage(STAGE_ALTERNATIVE_CONSIDERATION, new_intent),
            )
        return (
            STAGE_VALUE_REASSURANCE,
            "اعتراض السعر ما زال قائماً — تعميق الطمأنة والقيمة دون تكرار نفس النبرة.",
            path_label_for_stage(STAGE_VALUE_REASSURANCE, new_intent),
        )

    if p_st == STAGE_VALUE_REASSURANCE and n_in == "price" and asks_alternative_or_comparison(
        msg
    ):
        return (
            STAGE_ALTERNATIVE_CONSIDERATION,
            "انتقال إلى مقارنة البدائل بعد اهتمام بخيار أرخص.",
            path_label_for_stage(STAGE_ALTERNATIVE_CONSIDERATION, new_intent),
        )

    if p_st == STAGE_ALTERNATIVE_CONSIDERATION and n_in == "ready_to_buy":
        return (
            STAGE_CHECKOUT_READY,
            "انتقال إلى تهيئة إكمال الطلب — العميل مهتم بالشراء.",
            path_label_for_stage(STAGE_CHECKOUT_READY, new_intent),
        )

    if p_st == STAGE_ALTERNATIVE_CONSIDERATION and n_in == "price":
        return (
            STAGE_ALTERNATIVE_CONSIDERATION,
            "متابعة مقارنة البدائل — خفّف التكرار وقرّب العميل من قرار واضح.",
            path_label_for_stage(STAGE_ALTERNATIVE_CONSIDERATION, new_intent),
        )

    if p_st == STAGE_VALUE_REASSURANCE and n_in == "price":
        return (
            STAGE_VALUE_REASSURANCE,
            "متابعة مسار الطمأنة — عزّز القيمة أو أضف تفصيلاً يخدم الإغلاق.",
            path_label_for_stage(STAGE_VALUE_REASSURANCE, new_intent),
        )

    if p_st == STAGE_SHIPPING_QUESTIONS and n_in in ("delivery", "shipping"):
        return (
            STAGE_SHIPPING_QUESTIONS,
            "متابعة استفسار الشحن — طمأنة تدريجية ثم دفع للإغلاق عند اللزوم.",
            path_label_for_stage(STAGE_SHIPPING_QUESTIONS, new_intent),
        )

    if p_st == STAGE_CHECKOUT_READY and n_in == "ready_to_buy":
        return (
            STAGE_CHECKOUT_READY,
            "العميل ما زال في خانة إكمال الطلب — ثبّت الرابط والخطوة التالية يدوياً.",
            path_label_for_stage(STAGE_CHECKOUT_READY, new_intent),
        )

    st_new = initial_stage_for_intent(new_intent)
    return (
        st_new,
        "تحديث المسار وفق آخر رد لتبقى المحادثة متقدمة خطوة بخطوة.",
        path_label_for_stage(st_new, new_intent),
    )


def append_adaptive_fields_to_patch(
    patch: dict[str, Any],
    inbound_body: str,
    prior_behavioral: Optional[dict[str, Any]],
) -> None:
    """يعدّل ‎patch‎ مكاناً بحقول التكيّف والذاكرة قصيرة المدى."""
    prior = dict(prior_behavioral) if isinstance(prior_behavioral, dict) else {}
    new_intent = str(patch.get("recovery_reply_intent") or "").strip().lower()
    prev_intent = str(prior.get("recovery_reply_intent") or "").strip().lower()
    prev_stage = str(prior.get("recovery_adaptive_stage") or "").strip()
    turn = int(prior.get("recovery_adaptive_turn_count") or 0) + 1
    body = (inbound_body or "").strip()

    st, reason_ar, path_ar = compute_adaptive_transition(
        prev_stage=prev_stage,
        prev_intent=prev_intent,
        new_intent=new_intent,
        customer_message=body,
        turn_index=turn,
    )

    patch["recovery_adaptive_turn_count"] = turn
    patch["recovery_previous_intent"] = prev_intent
    patch["recovery_previous_customer_reply_preview"] = str(
        prior.get("last_customer_reply_preview") or ""
    ).strip()
    patch["recovery_previous_offer_strategy"] = str(
        prior.get("recovery_last_offer_strategy_key") or ""
    ).strip()
    patch["recovery_adaptive_stage"] = st
    patch["recovery_last_transition_reason_ar"] = reason_ar
    patch["recovery_adaptive_path_label_ar"] = path_ar
