# -*- coding: utf-8 -*-
"""
Conversational continuation layer v1 — rule-first, recovery-focused, isolated.

Does not alter recovery scheduling, delay gates, or return-to-site qualification.
Inbound hook sends at most one auto-reply per customer message event when enabled.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryReason, Store

from services.cartflow_product_intelligence import (
    CHEAPER_DIAG_BUILD,
    FALLBACK_CHEAPER_MESSAGE_AR,
)

log = logging.getLogger("cartflow")


def _absolute_url_for_customer_share(raw: str) -> str:
    """يحوّل مساراً نسبياً من الكتالوج إلى رابط كامل عند توفر قاعدة عامة."""
    u = (raw or "").strip()
    if not u:
        return u
    if u.lower().startswith(("http://", "https://")):
        return u
    base = (
        os.getenv("CARTFLOW_PUBLIC_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or ""
    ).strip().rstrip("/")
    if not base:
        return u
    return base + (u if u.startswith("/") else "/" + u)


_continuation_lock = threading.RLock()
# phone_key -> monotonic time of last auto-reply
_last_auto_reply_mono: dict[str, float] = {}
# phone_key -> (normalized_body_hash, monotonic time) last processed inbound
_last_inbound_dedup: list[tuple[str, tuple[str, float]]] = []

def _dedup_list_trim() -> None:
    global _last_inbound_dedup
    if len(_last_inbound_dedup) > 2000:
        _last_inbound_dedup = _last_inbound_dedup[-800:]


def reset_continuation_engine_for_tests() -> None:
    with _continuation_lock:
        _last_auto_reply_mono.clear()
        _last_inbound_dedup.clear()


def continuation_auto_reply_enabled() -> bool:
    v = (os.getenv("CARTFLOW_CONTINUATION_AUTO_REPLY") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def continuation_cooldown_seconds() -> float:
    raw = (os.getenv("CARTFLOW_CONTINUATION_COOLDOWN_SECONDS") or "90").strip()
    try:
        return max(15.0, float(raw))
    except (TypeError, ValueError):
        return 90.0


def continuation_dedup_seconds() -> float:
    raw = (os.getenv("CARTFLOW_CONTINUATION_DEDUP_SECONDS") or "120").strip()
    try:
        return max(10.0, float(raw))
    except (TypeError, ValueError):
        return 120.0


# --- Normalization & base intents (v1) ---

_AR_NORM = (
    ("أ", "ا"),
    ("إ", "ا"),
    ("آ", "ا"),
    ("ٱ", "ا"),
    ("ى", "ي"),
    ("ی", "ي"),
    ("ة", "ه"),
)


def normalize_inbound_text_v1(raw: str) -> str:
    t = (raw or "").strip().lower()
    for a, b in _AR_NORM:
        t = t.replace(a, b)
    t = re.sub(r"([!?؟.,])\1+", r"\1", t)
    t = " ".join(t.split())
    return t


def _contains_any(norm: str, phrases: frozenset[str]) -> bool:
    if not norm:
        return False
    for p in phrases:
        pn = normalize_inbound_text_v1(p)
        if not pn:
            continue
        if norm == pn:
            return True
        if len(pn) > 2 and pn in norm:
            return True
    return False


_CONFIRMATION_YES = frozenset(
    {
        "نعم",
        "نعم ",
        "اوكي",
        "اوك",
        "ok",
        "okay",
        "تمام",
        "موافق",
        "ايوه",
        "اي",
        "yes",
        "yep",
        "👍",
        "✅",
    }
)
_WANTS_LINK = frozenset(
    {
        "الرابط",
        "رابط",
        "ارسل الرابط",
        "أرسل الرابط",
        "ارسال الرابط",
        "link",
        "checkout",
        "الدفع",
        "اكمل الطلب",
        "أكمل الطلب",
    }
)
_WANTS_CHEAPER = frozenset(
    {
        "ارخص",
        "أرخص",
        "ابغي ارخص",
        "أبغى أرخص",
        "ابغي اقل",
        "أبغى أقل",
        "عندكم اقل",
        "عندكم أقل",
        "اغلى",
        "أغلى",
        "غالي",
        "غاليا",
        "اقل سعر",
        "أقل سعر",
        "cheaper",
        "بديل",
        "عندك بديل",
        "خصم",
    }
)
_ASKS_PRICE = frozenset(
    {
        "بكم",
        "كم سعر",
        "السعر",
        "سعره",
        "price",
        "how much",
    }
)
_ASKS_DELIVERY = frozenset(
    {
        "متى يوصل",
        "متى يصل",
        "موعد التوصيل",
        "موعد الوصول",
        "وقت التوصيل",
        "يوصل متى",
        "كم ياخذ التوصيل",
        "كم يأخذ التوصيل",
        "طلبي وين",
        "وين الطلب",
    }
)
_ASKS_SHIPPING = frozenset(
    {
        "الشحن",
        "شحن",
        "التوصيل",
        "توصيل",
        "رسوم الشحن",
        "سعر الشحن",
        "شحن مجاني",
        "shipping",
    }
)
_ASKS_WARRANTY = frozenset(
    {
        "الضمان",
        "ضمان",
        "ضمانات",
        "warranty",
    }
)
_ASKS_QUALITY = frozenset(
    {
        "الجودة",
        "جودة",
        "جوده",
        "اصلي",
        "أصلي",
        "تقليد",
        "original",
        "quality",
        "موثوق",
    }
)
_HESITATION = frozenset(
    {
        "بفكر",
        "بفكر ",
        "بعدين",
        "لاحقا",
        "لاحقاً",
        "مو متأكد",
        "مش متأكد",
        "ما ادري",
        "مدري",
        "think",
    }
)
_REJECTION = frozenset(
    {
        "لا",
        "لأ",
        "لا شكرا",
        "لا شكراً",
        "مو مهتم",
        "مش مهتم",
        "not interested",
        "no thanks",
    }
)
_HUMAN_HELP = frozenset(
    {
        "خدمة العملاء",
        "خدمه العملاء",
        "موظف",
        "موظفين",
        "اكلم احد",
        "أكلم أحد",
        "ادمين",
        "human",
        "agent",
        "support",
    }
)


def detect_base_intent_v1(body: str) -> str:
    n = normalize_inbound_text_v1(body)
    if not n:
        return "unknown_reply"
    if n in _CONFIRMATION_YES or (len(n) <= 4 and n.strip("👍✅.! ") in ("نعم", "ايه", "اي", "ok", "yes")):
        return "confirmation_yes"
    if _contains_any(n, _HUMAN_HELP):
        return "human_help"
    if _contains_any(n, _REJECTION) and len(n) < 40:
        return "rejection"
    if _contains_any(n, _WANTS_CHEAPER):
        return "wants_cheaper"
    if _contains_any(n, _WANTS_LINK):
        return "wants_link"
    if _contains_any(n, _ASKS_WARRANTY):
        return "asks_warranty"
    if _contains_any(n, _ASKS_QUALITY):
        return "asks_quality"
    if _contains_any(n, _ASKS_PRICE):
        return "asks_price"
    if _contains_any(n, _ASKS_DELIVERY):
        return "asks_delivery"
    if _contains_any(n, _ASKS_SHIPPING):
        return "asks_shipping"
    if _contains_any(n, _HESITATION):
        return "hesitation"
    if _contains_any(n, _CONFIRMATION_YES):
        return "confirmation_yes"
    return "unknown_reply"


def infer_prior_outbound_strategy(
    behavioral: dict[str, Any],
    reason_tag: str,
    *,
    prior_behavioral_before_reply: Optional[dict[str, Any]] = None,
) -> str:
    """
    Bucket the recovery context *before* this customer message.

    Uses recovery_previous_offer_strategy (captured on inbound from the prior
    recovery_last_offer_strategy_key). On the first reply after an outbound-only
    recovery, that key is often empty — fall back to abandonment reason_tag.
    """
    prev_offer = str(behavioral.get("recovery_previous_offer_strategy") or "").strip().lower()
    if not prev_offer and isinstance(prior_behavioral_before_reply, dict):
        prev_offer = str(
            prior_behavioral_before_reply.get("recovery_last_offer_strategy_key") or ""
        ).strip().lower()
    rt = (reason_tag or "").strip().lower()
    if not prev_offer:
        if rt in ("shipping", "delivery"):
            return "shipping_focus"
        if rt == "price" or rt.startswith("price"):
            return "cheaper_alternative"
        return "checkout_push"

    st = prev_offer
    if st in ("checkout_push", "completion_assistance"):
        return "checkout_push"
    if st in (
        "alternative_first",
        "value_framing_premium",
        "soft_discount_path",
    ) or behavioral.get("recovery_offer_flag_alternative") is True:
        return "cheaper_alternative"
    if st == "delivery_reassurance" or rt in ("shipping", "delivery"):
        return "shipping_focus"
    if st in ("reassurance_only", "balanced_guidance", "trust_proof", "warranty_trust"):
        return "reassurance"
    return "generic"


def resolve_contextual_intent(
    base_intent: str,
    *,
    prior_strategy: str,
    reason_tag: str,
) -> str:
    b = base_intent
    ps = prior_strategy
    rt = (reason_tag or "").strip().lower()
    if b == "confirmation_yes":
        if ps == "cheaper_alternative":
            return "yes_to_cheaper_alternative"
        if ps == "checkout_push":
            return "ready_for_checkout"
        if ps == "shipping_focus" or rt in ("shipping", "delivery"):
            return "confirmation_after_shipping"
        return "confirmation_generic"
    if b == "wants_link":
        return "wants_checkout_link"
    if b == "wants_cheaper":
        return "wants_cheaper_alternative"
    if b == "asks_price":
        return "asks_price_detail"
    if b == "asks_warranty":
        return "asks_warranty_detail"
    if b == "asks_quality":
        return "asks_quality_detail"
    if b == "asks_delivery":
        return "asks_delivery_detail"
    if b == "asks_shipping":
        return "asks_shipping_detail"
    if b == "hesitation":
        return "customer_hesitating"
    if b == "rejection":
        return "customer_rejecting"
    if b == "human_help":
        return "requests_human"
    return "unknown_reply"


# --- Actions & replies ---

CONTINUATION_ACTION_SEND_CHECKOUT = "send_checkout_link"
CONTINUATION_ACTION_RESEND_CHECKOUT = "resend_checkout_link"
CONTINUATION_ACTION_SEND_CHEAPER = "send_cheaper_alternative"
CONTINUATION_ACTION_EXPLAIN_SHIPPING = "explain_shipping"
CONTINUATION_ACTION_EXPLAIN_DELIVERY = "explain_delivery"
CONTINUATION_ACTION_EXPLAIN_WARRANTY = "explain_warranty"
CONTINUATION_ACTION_EXPLAIN_PRICE = "explain_price"
CONTINUATION_ACTION_EXPLAIN_QUALITY = "explain_quality"
CONTINUATION_ACTION_REASSURANCE = "reassurance_followup"
CONTINUATION_ACTION_GRACEFUL_EXIT = "graceful_exit"
CONTINUATION_ACTION_ESCALATE = "escalate_to_human"
CONTINUATION_ACTION_WAIT = "wait_for_customer_reply"


def resolve_continuation_action(contextual_intent: str) -> str:
    m = {
        "ready_for_checkout": CONTINUATION_ACTION_SEND_CHECKOUT,
        "yes_to_cheaper_alternative": CONTINUATION_ACTION_SEND_CHEAPER,
        "confirmation_generic": CONTINUATION_ACTION_SEND_CHECKOUT,
        "confirmation_after_shipping": CONTINUATION_ACTION_REASSURANCE,
        "wants_checkout_link": CONTINUATION_ACTION_RESEND_CHECKOUT,
        "wants_cheaper_alternative": CONTINUATION_ACTION_SEND_CHEAPER,
        "asks_price_detail": CONTINUATION_ACTION_EXPLAIN_PRICE,
        "asks_warranty_detail": CONTINUATION_ACTION_EXPLAIN_WARRANTY,
        "asks_quality_detail": CONTINUATION_ACTION_EXPLAIN_QUALITY,
        "asks_delivery_detail": CONTINUATION_ACTION_EXPLAIN_DELIVERY,
        "asks_shipping_detail": CONTINUATION_ACTION_EXPLAIN_SHIPPING,
        "customer_hesitating": CONTINUATION_ACTION_REASSURANCE,
        "customer_rejecting": CONTINUATION_ACTION_GRACEFUL_EXIT,
        "requests_human": CONTINUATION_ACTION_ESCALATE,
        "unknown_reply": CONTINUATION_ACTION_WAIT,
    }
    return m.get(contextual_intent, CONTINUATION_ACTION_WAIT)


def continuation_state_key(contextual_intent: str, action: str) -> str:
    if action == CONTINUATION_ACTION_ESCALATE:
        return "customer_needs_human_help"
    if action == CONTINUATION_ACTION_GRACEFUL_EXIT:
        return "recovery_closing"
    if contextual_intent in ("ready_for_checkout", "wants_checkout_link"):
        return "customer_ready_for_checkout"
    if contextual_intent in ("yes_to_cheaper_alternative", "wants_cheaper_alternative"):
        return "customer_interested_in_alternative"
    if contextual_intent == "asks_shipping_detail":
        return "customer_asking_shipping"
    if contextual_intent == "asks_delivery_detail":
        return "customer_asking_delivery"
    if contextual_intent == "asks_warranty_detail":
        return "customer_asking_warranty"
    if contextual_intent == "asks_quality_detail":
        return "customer_asking_quality"
    if contextual_intent == "asks_price_detail":
        return "customer_asking_price"
    if contextual_intent == "customer_hesitating":
        return "customer_hesitating"
    if contextual_intent == "customer_rejecting":
        return "recovery_closing"
    if contextual_intent == "requests_human":
        return "customer_needs_human_help"
    return "customer_replied"


def dashboard_summary_ar(contextual_intent: str, action: str) -> str:
    if action == CONTINUATION_ACTION_ESCALATE:
        return "تم طلب تدخل بشري"
    if action == CONTINUATION_ACTION_GRACEFUL_EXIT:
        return "العميل أنهى المحادثة بلباقة"
    if contextual_intent == "wants_checkout_link":
        return "العميل يطلب رابط الإكمال"
    if contextual_intent in ("ready_for_checkout", "confirmation_generic"):
        return "العميل جاهز للإكمال"
    if contextual_intent in ("yes_to_cheaper_alternative", "wants_cheaper_alternative"):
        return "العميل مهتم بخيار أوفر"
    if contextual_intent == "asks_shipping_detail":
        return "العميل يسأل عن الشحن"
    if contextual_intent == "asks_delivery_detail":
        return "العميل يسأل عن موعد التوصيل"
    if contextual_intent == "asks_price_detail":
        return "العميل يسأل عن السعر"
    if contextual_intent == "asks_warranty_detail":
        return "العميل يسأل عن الضمان"
    if contextual_intent == "asks_quality_detail":
        return "العميل يسأل عن الجودة"
    if contextual_intent == "customer_hesitating":
        return "العميل متردد"
    if contextual_intent == "confirmation_after_shipping":
        return "العميل يؤكد بعد طمأنة الشحن"
    if action in (CONTINUATION_ACTION_SEND_CHECKOUT, CONTINUATION_ACTION_RESEND_CHECKOUT):
        return "العميل يطلب رابط الإكمال"
    return "العميل تفاعل مع الرسالة"


def _template_vars_for_cart(
    ac: AbandonedCart,
    *,
    reason_tag: str,
    contextual_intent: str,
    action: str,
) -> dict[str, str]:
    from services.cartflow_product_intelligence import build_intelligence_continuation_vars
    from services.cartflow_product_intelligence import resolve_store_for_abandoned_cart

    store = resolve_store_for_abandoned_cart(ac)
    return build_intelligence_continuation_vars(
        ac,
        store,
        reason_tag=reason_tag,
        contextual_intent=contextual_intent,
        action=action,
    )


def build_continuation_message(action: str, vars_map: dict[str, str]) -> str:
    cu = vars_map.get("checkout_url") or ""
    altn = vars_map.get("alternative_product_name") or ""
    altu = vars_map.get("alternative_checkout_url") or cu
    se = vars_map.get("shipping_estimate") or ""
    offer = vars_map.get("merchant_offer_line") or ""

    if action == CONTINUATION_ACTION_SEND_CHECKOUT:
        return (
            "ممتاز 👍\n"
            "هذا رابط إكمال الطلب مباشرة:\n"
            f"{cu}\n\n"
            "وإذا احتجت أي مساعدة أنا موجود."
        ) + offer
    if action == CONTINUATION_ACTION_RESEND_CHECKOUT:
        return (
            "أكيد 👍\n"
            "هذا رابط الطلب المباشر:\n"
            f"{cu}"
        ) + offer
    if action == CONTINUATION_ACTION_SEND_CHEAPER:
        if vars_map.get("cheaper_reply_mode") == "real" and altn.strip():
            altp = (vars_map.get("alternative_product_price_display") or "").strip()
            altu_abs = _absolute_url_for_customer_share(altu.strip() or cu)
            lines = [
                "لقينا لك خيار قريب من اللي اخترته 👌",
                "",
                altn,
            ]
            if altp:
                lines.append(f"{altp} ريال")
            lines.extend(["", "تقدر تشوفه هنا:", altu_abs])
            return "\n".join(lines) + offer
        base = FALLBACK_CHEAPER_MESSAGE_AR
        if cu.strip().lower().startswith("http"):
            base += f"\n\nرابط السلة:\n{cu}"
        return base + offer
    if action == CONTINUATION_ACTION_EXPLAIN_SHIPPING:
        return (
            "الشحن متاح 👍\n"
            "مدة التوصيل المتوقعة:\n"
            f"{se}"
        ) + offer
    if action == CONTINUATION_ACTION_EXPLAIN_DELIVERY:
        return (
            "أكيد 👍\n"
            "التوصيل يختلف حسب المدينة، لكن غالباً يكون خلال أيام عمل بسيطة.\n"
            f"تقدير سريع: {se}\n"
            "إذا حاب نثبت لك الموعد بدقة قبل الإكمال نقدر نساعدك."
        ) + offer
    if action == CONTINUATION_ACTION_EXPLAIN_WARRANTY:
        return (
            "أكيد 👍\n"
            "الضمان يختلف حسب المنتج، لكن نقدر نأكد لك التفاصيل قبل إكمال الطلب."
        ) + offer
    if action == CONTINUATION_ACTION_EXPLAIN_PRICE:
        if vars_map.get("has_price_context") == "1":
            pd = vars_map.get("current_product_price_display") or ""
            return (
                "أكيد 👍\n"
                f"السعر المعروض حالياً للمنتج في السلة: {pd}.\n"
                "قبل الدفع يظهر لك الإجمالي النهائي في صفحة الإكمال.\n"
                "إذا حاب توضيح لأي رسوم إضافية، قولنا ونساعدك."
            ) + offer
        return (
            "أكيد 👍\n"
            "السعر اللي شايفه بالسلة هو المعتمد قبل الدفع.\n"
            "إذا حاب توضيح لأي رسوم إضافية قبل الإكمال، قولنا ونساعدك خطوة بخطوة."
        ) + offer
    if action == CONTINUATION_ACTION_EXPLAIN_QUALITY:
        return (
            "أكيد 👍\n"
            "نفهم قلقك على الجودة — التفاصيل الدقيقة تختلف حسب المنتج.\n"
            "قبل الإكمال نقدر نوضح لك المصدر والمواصفات اللي تهمك."
        ) + offer
    if action == CONTINUATION_ACTION_REASSURANCE:
        return "خذ راحتك 👍\nإذا احتجت أي توضيح أنا موجود."
    if action == CONTINUATION_ACTION_GRACEFUL_EXIT:
        return "تمام 👍\nإذا احتجت أي شيء لاحقًا نحن بالخدمة."
    if action == CONTINUATION_ACTION_ESCALATE:
        return "تم تحويل طلبك لفريق المتابعة 👍"
    return ""


def _reason_tag_for_abandoned_cart(ac: AbandonedCart) -> str:
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    if not sid:
        return ""
    try:
        db.create_all()
        row = (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.session_id == sid)
            .order_by(CartRecoveryReason.updated_at.desc())
            .first()
        )
        if row is None:
            return ""
        return str(row.reason or "").strip().lower()
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return ""


def _store_slug_for_ac(ac: AbandonedCart) -> str:
    raw = getattr(ac, "store_id", None)
    if raw is None:
        return ""
    try:
        st = db.session.get(Store, int(raw))
        if st is None:
            return ""
        return str(getattr(st, "zid_store_id", None) or "").strip()
    except (TypeError, ValueError, SQLAlchemyError):
        db.session.rollback()
        return ""


def _continuation_wa_trace_store_slug(ac: AbandonedCart) -> str:
    """
    Same store key recovery uses for CartRecoveryReason / send_whatsapp trace
    (merchant store_slug), not Store.zid_store_id — keeps user_rejected_help
    checks aligned with the recovery pipeline.
    """
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    if not sid:
        return ""
    try:
        db.create_all()
        row = (
            db.session.query(CartRecoveryReason.store_slug)
            .filter(CartRecoveryReason.session_id == sid)
            .order_by(CartRecoveryReason.updated_at.desc())
            .first()
        )
        if row is not None and row[0]:
            return str(row[0]).strip()[:255]
    except RuntimeError:
        # Unit tests / scripts without init_database()
        pass
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
    return _store_slug_for_ac(ac)


def _phone_e164_from_key(phone_key: str) -> str:
    d = "".join(c for c in (phone_key or "") if c.isdigit())
    if len(d) == 10 and d.startswith("05"):
        d = "966" + d[1:]
    elif len(d) == 9 and d.startswith("5"):
        d = "966" + d
    elif len(d) == 10 and d.startswith("5"):
        d = "966" + d
    if len(d) < 11:
        return ""
    return "+" + d


def _phone_e164_from_abandoned_cart(ac: AbandonedCart) -> str:
    raw = (getattr(ac, "customer_phone", None) or "").strip()
    if not raw:
        return ""
    d = "".join(c for c in raw if c.isdigit())
    while d.startswith("00"):
        d = d[2:]
    if len(d) == 10 and d.startswith("05"):
        d = "966" + d[1:]
    elif len(d) == 9 and d.startswith("5"):
        d = "966" + d
    elif len(d) == 10 and d.startswith("5"):
        d = "966" + d
    if len(d) < 11:
        return ""
    return "+" + d


def _resolve_outbound_e164_for_continuation(ac: AbandonedCart, phone_key: str) -> str:
    p = _phone_e164_from_key(phone_key)
    if p:
        return p
    return _phone_e164_from_abandoned_cart(ac)


def _continuation_reply_preview(message: str, *, max_chars: int = 100) -> str:
    t = (message or "").strip().replace("\n", " ")
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1] + "…"


def _log_continuation_auto_reply_terminal(
    *,
    sent: bool,
    session_id: str,
    phone_e164: str,
    action: str,
    preview: str,
    error: Optional[str] = None,
) -> None:
    sid = (session_id or "").strip()
    ph = (phone_e164 or "").strip()
    act = (action or "").strip()
    pv = _continuation_reply_preview(preview, max_chars=100)
    if sent:
        line = (
            f"[CONTINUATION AUTO REPLY SENT] session_id={sid} phone={ph} "
            f"action={act} reply_preview={pv!r}"
        )
    else:
        err = (error or "unknown").strip()[:500]
        line = (
            f"[CONTINUATION AUTO REPLY FAILED] session_id={sid} phone={ph} "
            f"action={act} reply_preview={pv!r} error={err!r}"
        )
    log.info("%s", line)
    try:
        print(line, flush=True)
    except OSError:
        pass


def _inbound_duplicate_recent(phone_key: str, body_norm: str) -> bool:
    h = hashlib.sha256(body_norm.encode("utf-8")).hexdigest()[:24]
    now = time.monotonic()
    win = continuation_dedup_seconds()
    with _continuation_lock:
        for pk, (hh, ts) in _last_inbound_dedup:
            if pk != phone_key:
                continue
            if hh != h:
                continue
            if now - ts <= win:
                return True
        _last_inbound_dedup.append((phone_key, (h, now)))
        _dedup_list_trim()
    return False


def _cooldown_allows_auto_reply(phone_key: str) -> bool:
    now = time.monotonic()
    cd = continuation_cooldown_seconds()
    with _continuation_lock:
        last = _last_auto_reply_mono.get(phone_key)
        if last is not None and (now - last) < cd:
            return False
        return True


def _mark_auto_reply_sent(phone_key: str) -> None:
    with _continuation_lock:
        _last_auto_reply_mono[phone_key] = time.monotonic()


@dataclass
class ContinuationDecision:
    base_intent: str
    contextual_intent: str
    action: str
    continuation_state: str
    summary_ar: str
    message_to_send: str
    should_send: bool
    merchant_offer_applied: bool = False


def _deploy_git_sha_for_logs() -> str:
    """Best-effort commit from common PaaS env vars (for deploy verification in logs)."""
    for key in (
        "RAILWAY_GIT_COMMIT_SHA",
        "RENDER_GIT_COMMIT",
        "SOURCE_VERSION",
        "HEROKU_SLUG_COMMIT",
        "K_REVISION",
    ):
        v = (os.environ.get(key) or "").strip()
        if v:
            return v[:48]
    return ""


def _log_cheaper_continuation_decision(ac: AbandonedCart, vars_map: dict[str, str]) -> None:
    """
    Exactly one [CHEAPER MATCH DEBUG] at INFO + stdout whenever send_cheaper_alternative is chosen,
    so production captures diagnostics even if only console logs are tailed.
    """
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()[:64]
    sha = _deploy_git_sha_for_logs()
    crm = (vars_map.get("cheaper_reply_mode") or "").strip()
    cfb = (vars_map.get("cheaper_fallback_reason") or "").strip()[:200]
    line = (
        f"[CHEAPER MATCH DEBUG] phase=continuation_decision diag_build={CHEAPER_DIAG_BUILD} "
        f"session_id={sid} cheaper_reply_mode={crm} cheaper_fallback_reason={cfb!r} "
        f"deploy_git_sha={sha or 'n/a'}"
    )
    log.info("%s", line)
    try:
        print(line, flush=True)
    except OSError:
        pass


def decide_continuation(
    *,
    inbound_body: str,
    behavioral: dict[str, Any],
    reason_tag: str,
    ac: AbandonedCart,
    prior_behavioral_before_reply: Optional[dict[str, Any]] = None,
) -> ContinuationDecision:
    base = detect_base_intent_v1(inbound_body)
    prior = infer_prior_outbound_strategy(
        behavioral,
        reason_tag,
        prior_behavioral_before_reply=prior_behavioral_before_reply,
    )
    ctx = resolve_contextual_intent(base, prior_strategy=prior, reason_tag=reason_tag)
    action = resolve_continuation_action(ctx)
    st_key = continuation_state_key(ctx, action)
    summary = dashboard_summary_ar(ctx, action)
    vars_map = _template_vars_for_cart(
        ac,
        reason_tag=reason_tag,
        contextual_intent=ctx,
        action=action,
    )
    if action == CONTINUATION_ACTION_SEND_CHEAPER:
        _log_cheaper_continuation_decision(ac, vars_map)
    msg = build_continuation_message(action, vars_map)
    should_send = bool(
        msg.strip()
        and action
        not in (
            CONTINUATION_ACTION_WAIT,
        )
    )
    if action == CONTINUATION_ACTION_WAIT:
        should_send = False
    offer_applied = vars_map.get("merchant_offer_applied") == "1"
    return ContinuationDecision(
        base_intent=base,
        contextual_intent=ctx,
        action=action,
        continuation_state=st_key,
        summary_ar=summary,
        message_to_send=msg,
        should_send=should_send,
        merchant_offer_applied=offer_applied,
    )


def process_continuation_after_customer_reply(
    ac: AbandonedCart,
    *,
    inbound_body: str,
    customer_phone_key: str,
    prior_behavioral_before_reply: Optional[dict[str, Any]] = None,
) -> None:
    """
    Run after apply_interactive_transition_from_customer_reply (same transaction).
    Merges continuation fields; optionally sends one WhatsApp via send_whatsapp.
    """
    from services.behavioral_recovery.state_store import (
        behavioral_dict_for_abandoned_cart,
        merge_behavioral_state,
        normal_recovery_message_was_sent_for_abandoned,
        utc_now_iso,
    )

    body = (inbound_body or "").strip()
    phone_key = (customer_phone_key or "").strip()
    if not body or len(phone_key) < 11:
        return
    if bool(getattr(ac, "vip_mode", False)):
        return
    if not normal_recovery_message_was_sent_for_abandoned(ac):
        return

    bh = behavioral_dict_for_abandoned_cart(ac)
    if bh.get("continuation_escalated_human") is True:
        log.info("[CONTINUATION] skip: already escalated session_id=%s", ac.recovery_session_id)
        return
    if bh.get("continuation_automation_stopped") is True:
        log.info("[CONTINUATION] skip: automation stopped session_id=%s", ac.recovery_session_id)
        return

    norm = normalize_inbound_text_v1(body)
    if _inbound_duplicate_recent(phone_key, norm):
        log.info(
            "[CONTINUATION] duplicate inbound skipped phone_key=%s",
            phone_key[:6],
        )
        return

    reason_tag = _reason_tag_for_abandoned_cart(ac)
    dec = decide_continuation(
        inbound_body=body,
        behavioral=bh,
        reason_tag=reason_tag,
        ac=ac,
        prior_behavioral_before_reply=prior_behavioral_before_reply,
    )

    sid_log = (getattr(ac, "recovery_session_id", None) or "").strip()

    body_hash_curr = ""
    if dec.should_send and dec.action != CONTINUATION_ACTION_ESCALATE:
        body_hash_curr = hashlib.sha256(
            (dec.message_to_send or "").strip().encode("utf-8")
        ).hexdigest()[:48]
    prev_body_h = str(bh.get("continuation_last_autoreply_body_hash") or "")
    prev_ctx_h = str(bh.get("continuation_last_autoreply_contextual_intent") or "")
    suppress_repeat_send = bool(
        body_hash_curr
        and prev_body_h
        and prev_body_h == body_hash_curr
        and prev_ctx_h == dec.contextual_intent
    )
    if suppress_repeat_send:
        try:
            print(
                f"[CONTINUATION REPEAT SUPPRESSED] session_id={sid_log} "
                f"contextual_intent={dec.contextual_intent}",
                flush=True,
            )
        except OSError:
            pass
        log.info(
            "[CONTINUATION REPEAT SUPPRESSED] session_id=%s contextual=%s",
            sid_log,
            dec.contextual_intent,
        )
    log.info(
        "[CONTINUATION INTENT] session_id=%s base=%s contextual=%s action=%s state=%s",
        sid_log,
        dec.base_intent,
        dec.contextual_intent,
        dec.action,
        dec.continuation_state,
    )
    try:
        print(
            f"[CONTINUATION INTENT] session_id={sid_log} detected_intent={dec.base_intent} "
            f"contextual_intent={dec.contextual_intent} continuation_action={dec.action} "
            f"lifecycle_state={dec.continuation_state}",
            flush=True,
        )
    except OSError:
        pass

    summary_ar_out = dec.summary_ar
    if suppress_repeat_send:
        summary_ar_out = f"{dec.summary_ar} — لم نُعد نفس الرد تلقائياً"

    patch: dict[str, Any] = {
        "continuation_base_intent": dec.base_intent,
        "continuation_contextual_intent": dec.contextual_intent,
        "continuation_action": dec.action,
        "continuation_state": dec.continuation_state,
        "continuation_summary_ar": summary_ar_out,
        "continuation_last_evaluated_at": utc_now_iso(),
    }
    if suppress_repeat_send:
        patch["continuation_repeat_suppressed"] = True

    if dec.action == CONTINUATION_ACTION_ESCALATE:
        patch["continuation_escalated_human"] = True
        patch["waiting_merchant"] = True
        patch["continuation_automation_stopped"] = True
        log.info("[CONTINUATION ESCALATION] session_id=%s", sid_log)
        try:
            print(f"[CONTINUATION ESCALATION] session_id={sid_log}", flush=True)
        except OSError:
            pass

    if (
        dec.should_send
        and not suppress_repeat_send
        and continuation_auto_reply_enabled()
        and dec.action != CONTINUATION_ACTION_ESCALATE
        and _cooldown_allows_auto_reply(phone_key)
    ):
        from services.whatsapp_send import send_whatsapp_real

        phone_out = _resolve_outbound_e164_for_continuation(ac, phone_key)
        trace_slug = _continuation_wa_trace_store_slug(ac)
        log.info("[CONTINUATION ACTION] session_id=%s action=%s", sid_log, dec.action)
        try:
            print(
                f"[CONTINUATION ACTION] session_id={sid_log} continuation_action={dec.action}",
                flush=True,
            )
        except OSError:
            pass
        if not phone_out:
            _log_continuation_auto_reply_terminal(
                sent=False,
                session_id=sid_log,
                phone_e164="",
                action=dec.action,
                preview=dec.message_to_send,
                error="missing_outbound_phone",
            )
        else:
            result = send_whatsapp_real(
                phone_out,
                dec.message_to_send,
                reason_tag="continuation",
                wa_trace_path=__file__,
                wa_trace_session_id=sid_log or None,
                wa_trace_store_slug=trace_slug or None,
                wa_trace_delay_passed=True,
            )
            sent_ok = bool(isinstance(result, dict) and result.get("ok") is True)
            if sent_ok:
                _mark_auto_reply_sent(phone_key)
                patch["continuation_last_auto_reply_at"] = utc_now_iso()
                patch["continuation_last_auto_reply_action"] = dec.action
                if dec.merchant_offer_applied:
                    from services.cartflow_product_intelligence import (
                        record_merchant_offer_use,
                        resolve_store_for_abandoned_cart,
                    )

                    st_row = resolve_store_for_abandoned_cart(ac)
                    record_merchant_offer_use(st_row)
                if body_hash_curr:
                    patch["continuation_last_autoreply_body_hash"] = body_hash_curr
                    patch["continuation_last_autoreply_contextual_intent"] = (
                        dec.contextual_intent
                    )
                _log_continuation_auto_reply_terminal(
                    sent=True,
                    session_id=sid_log,
                    phone_e164=phone_out,
                    action=dec.action,
                    preview=dec.message_to_send,
                )
            else:
                err = None
                if isinstance(result, dict):
                    err = str(result.get("error") or result.get("hint") or result)
                _log_continuation_auto_reply_terminal(
                    sent=False,
                    session_id=sid_log,
                    phone_e164=phone_out,
                    action=dec.action,
                    preview=dec.message_to_send,
                    error=err or "send_failed",
                )
    elif dec.action == CONTINUATION_ACTION_ESCALATE and dec.message_to_send:
        # Optional: still send the short escalation ack when Twilio configured
        if continuation_auto_reply_enabled() and _cooldown_allows_auto_reply(phone_key):
            from services.whatsapp_send import send_whatsapp_real

            phone_out = _resolve_outbound_e164_for_continuation(ac, phone_key)
            trace_slug = _continuation_wa_trace_store_slug(ac)
            if not phone_out:
                _log_continuation_auto_reply_terminal(
                    sent=False,
                    session_id=sid_log,
                    phone_e164="",
                    action=CONTINUATION_ACTION_ESCALATE,
                    preview=dec.message_to_send,
                    error="missing_outbound_phone",
                )
            else:
                result = send_whatsapp_real(
                    phone_out,
                    dec.message_to_send,
                    reason_tag="continuation_escalation",
                    wa_trace_path=__file__,
                    wa_trace_session_id=sid_log or None,
                    wa_trace_store_slug=trace_slug or None,
                    wa_trace_delay_passed=True,
                )
                if isinstance(result, dict) and result.get("ok") is True:
                    _mark_auto_reply_sent(phone_key)
                    patch["continuation_last_auto_reply_at"] = utc_now_iso()
                    _log_continuation_auto_reply_terminal(
                        sent=True,
                        session_id=sid_log,
                        phone_e164=phone_out,
                        action=CONTINUATION_ACTION_ESCALATE,
                        preview=dec.message_to_send,
                    )
                else:
                    err = None
                    if isinstance(result, dict):
                        err = str(result.get("error") or result.get("hint") or result)
                    _log_continuation_auto_reply_terminal(
                        sent=False,
                        session_id=sid_log,
                        phone_e164=phone_out,
                        action=CONTINUATION_ACTION_ESCALATE,
                        preview=dec.message_to_send,
                        error=err or "send_failed",
                    )

    merge_behavioral_state(ac, **patch)
