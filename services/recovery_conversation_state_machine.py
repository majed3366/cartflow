# -*- coding: utf-8 -*-
"""
آلة حالات مسار المحادثة التفاعلية — تتبع وانتقال دون إرسال تلقائي.
تُحدَّث عبر ‎cf_behavioral‎ فقط عند رد العميل.

تبريد المحادثة وإعادة الربط: تُستنتج من وقت آخر رد (last_customer_reply_at /
latest_customer_reply_at) + المرحلة التكيّفية — للإرشاد في اللوحة فقط؛ لا إرسال ولا جدولة.

جاهز لاحقاً: توقيت نداء ذكي، إيقاع تكيّفي، إرهاق عميل، محرك سلوك زمني — تغذية إرشاد فقط.

سلوك العودة للموقع: يُحدَّث عبر ‎merge_behavioral_state‎ (حدث الويدجت) ويُدمج مع المسار التكيّفي
عند وجود محادثة تفاعلية — إرشاد للتاجر فقط.

جاهز لاحقاً: behavioral automation، rescue للدفع، وكلاء مبيعات لحظيين — دون إرسال تلقائي من هذه الطبقة.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

STAGE_PRICE_OBJECTION = "price_objection"
STAGE_VALUE_REASSURANCE = "value_reassurance"
STAGE_ALTERNATIVE_CONSIDERATION = "alternative_consideration"
STAGE_CHECKOUT_READY = "checkout_ready"
STAGE_SHIPPING_QUESTIONS = "shipping_questions"
STAGE_HESITATION_FOLLOWUP = "hesitation_followup"
STAGE_RETURNED_BROWSING = "returned_browsing"
STAGE_RETURNED_CHECKOUT = "returned_checkout"
STAGE_PASSIVE_RETURN = "passive_return"

RETURN_STAGES: frozenset[str] = frozenset(
    {
        STAGE_RETURNED_BROWSING,
        STAGE_RETURNED_CHECKOUT,
        STAGE_PASSIVE_RETURN,
    }
)

COOLDOWN_ACTIVE_CONVERSATION = "active_conversation"
COOLDOWN_COOLING_DOWN = "cooling_down"
COOLDOWN_CHECKOUT_SILENCE = "checkout_silence"
COOLDOWN_DISENGAGED = "disengaged"
COOLDOWN_GENTLE_FOLLOWUP_CANDIDATE = "gentle_followup_candidate"

FOLLOWUP_REMINDER_LIGHT = "reminder_light"
FOLLOWUP_SUPPORT_OFFER = "support_offer"
FOLLOWUP_CHECKOUT_NUDGE = "checkout_nudge"
FOLLOWUP_CONVERSATION_PAUSE = "conversation_pause"

# عتبات بالدقائق — إرشاد فقط؛ لا تربط بجدولة الإرسال الآلي
_SILENCE_ACTIVE_MAX_MIN: float = 20.0
_SILENCE_CHECKOUT_SILENCE_MIN_MIN: float = 20.0
_SILENCE_OBJECTION_COOLING_MIN_MIN: float = 35.0
_SILENCE_DISENGAGED_MIN_MIN: float = 24.0 * 60.0
_OBJECTION_HEAVY_TURNS: int = 4

_PRICE_OR_OBJECTION_STAGES: frozenset[str] = frozenset(
    {
        STAGE_PRICE_OBJECTION,
        STAGE_VALUE_REASSURANCE,
        STAGE_ALTERNATIVE_CONSIDERATION,
    }
)

_COOLDOWN_LABELS_AR: dict[str, str] = {
    COOLDOWN_ACTIVE_CONVERSATION: "محادثة نشطة — آخر رد حديث",
    COOLDOWN_COOLING_DOWN: "المحادثة تبرد تدريجيًا (اعتراض/تفاوض)",
    COOLDOWN_CHECKOUT_SILENCE: "صمت بعد اهتمام بالإكمال أو طلب الرابط",
    COOLDOWN_DISENGAGED: "انقطاع طويل — محادثة باردة",
    COOLDOWN_GENTLE_FOLLOWUP_CANDIDATE: "نافذة متابعة لطيفة",
}

_FOLLOWUP_LABELS_AR: dict[str, str] = {
    FOLLOWUP_REMINDER_LIGHT: "تذكير خفيف",
    FOLLOWUP_SUPPORT_OFFER: "عرض مساعدة بدون ضغط",
    FOLLOWUP_CHECKOUT_NUDGE: "تذكير بهادئ لإكمال الطلب",
    FOLLOWUP_CONVERSATION_PAUSE: "إيقاف/تخفيف ضغط بيعي",
}

_STAGE_LABELS_AR: dict[str, str] = {
    STAGE_PRICE_OBJECTION: "اعتراض سعر — بداية المسار",
    STAGE_VALUE_REASSURANCE: "طمأنة قيمة",
    STAGE_ALTERNATIVE_CONSIDERATION: "مقارنة بدائل",
    STAGE_CHECKOUT_READY: "جاهز لإكمال الطلب",
    STAGE_SHIPPING_QUESTIONS: "أسئلة شحن وتوصيل",
    STAGE_HESITATION_FOLLOWUP: "متابعة تردد لطيفة",
    STAGE_RETURNED_BROWSING: "عاد للتصفح في المتجر",
    STAGE_RETURNED_CHECKOUT: "عاد لصفحة الدفع — مساعدة إكمال",
    STAGE_PASSIVE_RETURN: "عودة لطيفة — تخفيف ضغط بعد اعتراض",
}


def stage_label_ar(stage_key: str) -> str:
    k = (stage_key or "").strip()
    return _STAGE_LABELS_AR.get(k, k or "مسار تفاعلي")


def _parse_customer_reply_iso_to_utc(iso_s: Optional[str]) -> Optional[datetime]:
    if not iso_s or not str(iso_s).strip():
        return None
    s = str(iso_s).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _format_silence_duration_ar(minutes: float) -> str:
    if minutes < 1:
        return "أقل من دقيقة"
    if minutes < 60:
        n = int(round(minutes))
        return f"حوالي {n} دقيقة"
    h = int(minutes // 60)
    m = int(minutes % 60)
    if m <= 0:
        return f"حوالي {h} ساعة"
    return f"حوالي {h} ساعة و {m} دقيقة"


def compute_conversational_cooldown(
    *,
    last_customer_reply_iso: str,
    adaptive_stage_key: str = "",
    adaptive_turn_count: int = 0,
    now_utc: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    يُستنتج من طابع آخر رد عميل (في ‎cf_behavioral‎) + المرحلة التكيّفية.
    لا يُرسل ولا يُفعّل أتمتة — للإرشاد في لوحة التاجر فقط.
    """
    stage = (adaptive_stage_key or "").strip()
    iso = (last_customer_reply_iso or "").strip()
    last_dt = _parse_customer_reply_iso_to_utc(iso)
    now = now_utc or datetime.now(timezone.utc)
    if last_dt is None:
        return {
            "last_customer_reply_at": iso,
            "silence_duration_minutes": 0.0,
            "cooldown_state": COOLDOWN_ACTIVE_CONVERSATION,
            "cooldown_state_ar": _COOLDOWN_LABELS_AR[COOLDOWN_ACTIVE_CONVERSATION],
            "activity_level_key": "high",
            "activity_level_ar": "مرتفع",
            "recommend_followup": False,
            "followup_recommendation_ar": "لا حاجة لمتابعة مزعجة الآن",
            "recommended_followup_key": "",
            "recommended_followup_type_ar": "—",
            "cooldown_context_ar": "لا يتوفر وقت دقيق لآخر رد — تعامل كتفاعل حديث.",
            "pressure_note_ar": "",
            "reduce_sales_pressure": False,
            "silence_duration_display_ar": "—",
        }

    silence_min = max(0.0, (now - last_dt).total_seconds() / 60.0)

    if silence_min >= _SILENCE_DISENGAGED_MIN_MIN:
        cooldown_state = COOLDOWN_DISENGAGED
    elif stage == STAGE_CHECKOUT_READY and silence_min >= _SILENCE_CHECKOUT_SILENCE_MIN_MIN:
        cooldown_state = COOLDOWN_CHECKOUT_SILENCE
    elif stage in _PRICE_OR_OBJECTION_STAGES and silence_min >= _SILENCE_OBJECTION_COOLING_MIN_MIN:
        cooldown_state = COOLDOWN_COOLING_DOWN
    elif silence_min >= _SILENCE_ACTIVE_MAX_MIN:
        cooldown_state = COOLDOWN_GENTLE_FOLLOWUP_CANDIDATE
    else:
        cooldown_state = COOLDOWN_ACTIVE_CONVERSATION

    if silence_min < _SILENCE_ACTIVE_MAX_MIN:
        activity_level_key = "high"
        activity_level_ar = "مرتفع"
    elif silence_min < 180:
        activity_level_key = "medium"
        activity_level_ar = "متوسط"
    else:
        activity_level_key = "low"
        activity_level_ar = "منخفض"

    recommended_followup_key = ""
    recommend_followup = False
    reduce_sales_pressure = False
    pressure_note_ar = ""
    cooldown_context_ar = ""
    recommend_followup_ar = ""

    if cooldown_state == COOLDOWN_DISENGAGED:
        recommended_followup_key = FOLLOWUP_CONVERSATION_PAUSE
        recommend_followup = False
        reduce_sales_pressure = True
        pressure_note_ar = "يُفضّل إيقاف الضغط البيعي."
        cooldown_context_ar = "صمت طويل — المحادثة باردة."
        recommend_followup_ar = "لا يُنصح بمتابعة قريبة إلا لضرورة واضحة."
    elif cooldown_state == COOLDOWN_CHECKOUT_SILENCE:
        recommended_followup_key = FOLLOWUP_CHECKOUT_NUDGE
        recommend_followup = True
        cooldown_context_ar = "العميل اختفى بعد مرحلة الإكمال أو طلب الرابط."
        pressure_note_ar = "يوصى بتذكير هادئ؛ تجنّب إعادة الإقناع المكثّف."
        recommend_followup_ar = "نعم — تذكير هادئ مناسب."
    elif cooldown_state == COOLDOWN_COOLING_DOWN:
        heavy = int(adaptive_turn_count) >= _OBJECTION_HEAVY_TURNS
        reduce_sales_pressure = True
        if heavy:
            recommended_followup_key = FOLLOWUP_CONVERSATION_PAUSE
            recommend_followup = False
            pressure_note_ar = "عدة تفاعلات اعتراضية وصمت — يفضّل إيقاف الضغط البيعي."
            cooldown_context_ar = "المحادثة تبرد تدريجيًا بعد نقاش سعر."
            recommend_followup_ar = "لا — يُفضّل الهدوء أو تأجيل المتابعة."
        else:
            recommended_followup_key = FOLLOWUP_SUPPORT_OFFER
            recommend_followup = True
            pressure_note_ar = "تخفيف الضغط؛ أنسب صياغة دعم تقلّ من البيع المباشر."
            cooldown_context_ar = "لا رد بعد اعتراض أو تفاوض — المحادثة تهدأ."
            recommend_followup_ar = "يمكن متابعة خفيفة كعرض مساعدة دون ضغط."
    elif cooldown_state == COOLDOWN_GENTLE_FOLLOWUP_CANDIDATE:
        recommended_followup_key = FOLLOWUP_REMINDER_LIGHT
        recommend_followup = True
        cooldown_context_ar = "مرّ وقت معتدل دون رد — نافذة لتذكير لطيف."
        recommend_followup_ar = "نعم — تذكير لطيف مناسب."
    else:
        recommend_followup_ar = "لا حاجة لمتابعة مزعجة الآن."
        cooldown_context_ar = "آخر رد حديث نسبياً."

    recommended_followup_type_ar = _FOLLOWUP_LABELS_AR.get(
        recommended_followup_key,
        "",
    )

    return {
        "last_customer_reply_at": iso,
        "silence_duration_minutes": round(silence_min, 2),
        "cooldown_state": cooldown_state,
        "cooldown_state_ar": _COOLDOWN_LABELS_AR.get(
            cooldown_state,
            cooldown_state,
        ),
        "activity_level_key": activity_level_key,
        "activity_level_ar": activity_level_ar,
        "recommend_followup": recommend_followup,
        "followup_recommendation_ar": recommend_followup_ar,
        "recommended_followup_key": recommended_followup_key,
        "recommended_followup_type_ar": recommended_followup_type_ar or "—",
        "cooldown_context_ar": cooldown_context_ar,
        "pressure_note_ar": pressure_note_ar,
        "reduce_sales_pressure": reduce_sales_pressure,
        "silence_duration_display_ar": _format_silence_duration_ar(silence_min),
    }


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


def wants_checkout_completion(message: str, intent_key: str = "") -> bool:
    """إن كان العميل يطلب رابطاً أو خطوة إكمال واضحة — بغض النظر عن تصنيف النية أحياناً."""
    if _norm_intent_key(intent_key) == "ready_to_buy":
        return True
    m = _norm_msg(message)
    if not m:
        return False
    return any(
        k in m
        for k in (
            "كيف اطلب",
            "كيف أطلب",
            "اشطلب",
            "أشطلب",
            "ارسل الرابط",
            "أرسل الرابط",
            "ارسلني الرابط",
            "وين الرابط",
            "وين رابط",
            "أين الرابط",
            "اين الرابط",
            "فين الرابط",
            "فين رابط",
            "ابغى اكمل",
            "أبغى أكمل",
            "ابي اكمل",
            "أبي أكمل",
            "اكمل الطلب",
            "أكمل الطلب",
            "رابط الطلب",
            "رابط الدفع",
            "تمام كيف",
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
    if stage == STAGE_RETURNED_CHECKOUT:
        return "مساعدة إكمال — دون ضغط بيعي أو خصم مفاجئ"
    if stage == STAGE_PASSIVE_RETURN:
        return "تصفح المنتج — تخفيف ضغط بعد اعتراض"
    if stage == STAGE_RETURNED_BROWSING:
        return "تصفح بعد العودة — إيقاع هادئ"
    if stage == STAGE_CHECKOUT_READY or eff == "ready_to_buy":
        return "دفع نحو إكمال الطلب"
    if stage == STAGE_SHIPPING_QUESTIONS or eff in ("delivery", "shipping"):
        return "شحن → توضيح → إغلاق"
    if stage == STAGE_PRICE_OBJECTION:
        return "اعتراض سعر → طمأنة → (بديل / عرض ناعم)"
    if stage == STAGE_VALUE_REASSURANCE:
        return "طمأنة قيمة → بديل اختياري → إغلاق"
    return "مسار مرن حسب ردود العميل"


def compute_return_to_site_adaptive_transition(
    *,
    prior_conversational_stage: str,
    prior_intent: str,
    returned_checkout_page: bool,
    returned_product_page: bool,
) -> tuple[str, str, str]:
    """انتقال عند إبلاغ الويدجت عن عودة العميل للموقع — للدمج في ‎cf_behavioral‎ فقط."""
    ps = (prior_conversational_stage or "").strip()
    pi = _norm_intent_key(prior_intent)

    if returned_checkout_page:
        if ps == STAGE_CHECKOUT_READY or pi == "ready_to_buy":
            return (
                STAGE_RETURNED_CHECKOUT,
                "العميل عاد لصفحة الدفع بعد اهتمام بالإكمال — مساعدة هادئة دون إقناع مكرر.",
                path_label_for_stage(STAGE_RETURNED_CHECKOUT, "ready_to_buy"),
            )
        return (
            STAGE_RETURNED_CHECKOUT,
            "العميل وصل صفحة الدفع من الموقع — ركّز على المساندة والوضوح.",
            path_label_for_stage(STAGE_RETURNED_CHECKOUT, prior_intent),
        )

    if returned_product_page:
        if ps in _PRICE_OR_OBJECTION_STAGES or pi == "price":
            return (
                STAGE_PASSIVE_RETURN,
                "عودة لصفحة المنتج بعد اعتراض أو تفاوض — خفّف الضغط البيعي والخصومات المفاجئة.",
                path_label_for_stage(STAGE_PASSIVE_RETURN, "price"),
            )
        return (
            STAGE_RETURNED_BROWSING,
            "العميل يتصفح صفحة المنتج بعد العودة — أسلوب هادئ دون عروض عدوانية.",
            path_label_for_stage(STAGE_RETURNED_BROWSING, prior_intent),
        )

    return (
        STAGE_RETURNED_BROWSING,
        "العميل عاد للموقع — حافظ على محادثة دافئة دون مضايقة.",
        path_label_for_stage(STAGE_RETURNED_BROWSING, prior_intent),
    )


def should_fuse_return_into_adaptive_recovery(prior_behavioral: dict[str, Any]) -> bool:
    """دمج عودة الموقع مع المسار التكيّفي فقط عند وجود سياق محادثة/استرجاع تفاعلي."""
    if not isinstance(prior_behavioral, dict):
        return False
    if prior_behavioral.get("customer_replied") is True:
        return True
    if prior_behavioral.get("interactive_mode") is True:
        return True
    if str(prior_behavioral.get("recovery_adaptive_stage") or "").strip():
        return True
    return False


def build_return_to_site_behavioral_patch(
    prior_behavioral: dict[str, Any],
    *,
    returned_product_page: bool,
    returned_checkout_page: bool,
    return_timestamp_iso: str,
    fuse_adaptive: bool = True,
) -> dict[str, Any]:
    """
    حقول ‎cf_behavioral‎ لطبقة العودة للموقع — بدون نظام تتبع جديد.
    """
    prior = dict(prior_behavioral) if isinstance(prior_behavioral, dict) else {}
    try:
        rc = int(prior.get("recovery_site_return_count") or 0)
    except (TypeError, ValueError):
        rc = 0
    rc = max(0, rc) + 1

    out: dict[str, Any] = {
        "customer_returned_to_site": True,
        "recovery_return_timestamp": str(return_timestamp_iso or "").strip(),
        "recovery_returned_product_page": bool(returned_product_page),
        "recovery_returned_checkout_page": bool(returned_checkout_page),
        "recovery_site_return_count": rc,
    }

    if fuse_adaptive and should_fuse_return_into_adaptive_recovery(prior):
        prev_stage = str(prior.get("recovery_adaptive_stage") or "").strip()
        prev_intent = str(prior.get("recovery_reply_intent") or "").strip()
        st, reason_ar, path_ar = compute_return_to_site_adaptive_transition(
            prior_conversational_stage=prev_stage,
            prior_intent=prev_intent,
            returned_checkout_page=bool(returned_checkout_page),
            returned_product_page=bool(returned_product_page),
        )
        out["recovery_adaptive_stage"] = st
        out["recovery_last_transition_reason_ar"] = reason_ar
        out["recovery_adaptive_path_label_ar"] = path_ar

    return out


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
        if wants_checkout_completion(msg, new_intent):
            return (
                STAGE_CHECKOUT_READY,
                "بداية المسار بوضع إكمال الطلب — العميل طلب رابطاً أو خطوة الطلب.",
                path_label_for_stage(STAGE_CHECKOUT_READY, "ready_to_buy"),
            )
        st = initial_stage_for_intent(new_intent)
        return (
            st,
            "أول رد تفاعلي — بداية المسار وفق نية آخر رسالة.",
            path_label_for_stage(st, new_intent),
        )

    if wants_checkout_completion(msg, new_intent):
        return (
            STAGE_CHECKOUT_READY,
            "انتقال إلى وضع إكمال الطلب — العميل جاهز لخطوة الدفع أو الرابط.",
            path_label_for_stage(STAGE_CHECKOUT_READY, "ready_to_buy"),
        )

    # بعد مرحلة عودة للموقع (سلوك المتجر) — أعد المسار وفق نية الرسالة
    if p_st in RETURN_STAGES:
        if wants_checkout_completion(msg, new_intent):
            return (
                STAGE_CHECKOUT_READY,
                "بعد عودة للموقع — العميل يطلب إكمالاً أو الرابط.",
                path_label_for_stage(STAGE_CHECKOUT_READY, "ready_to_buy"),
            )
        st3 = initial_stage_for_intent(new_intent)
        if p_st == STAGE_RETURNED_CHECKOUT:
            reason_rt = "بعد عودة لصفحة الدفع — متابعة المحادثة وفق نية الرسالة."
        elif p_st == STAGE_PASSIVE_RETURN:
            reason_rt = "بعد عودة لطيفة لصفحة المنتج — أعد ضبط المسار وفق الرد."
        else:
            reason_rt = "بعد تصفح في الموقع — تابع بلطف دون ضغط مفاجئ."
        return (st3, reason_rt, path_label_for_stage(st3, new_intent))

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
        if wants_checkout_completion(msg, new_intent):
            return (
                STAGE_CHECKOUT_READY,
                "بعد طمأنة الشحن — دفع هادئ لإكمال الطلب.",
                path_label_for_stage(STAGE_CHECKOUT_READY, "ready_to_buy"),
            )
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
