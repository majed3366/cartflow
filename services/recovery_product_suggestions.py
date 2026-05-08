# -*- coding: utf-8 -*-
"""
اقتراحات استرجاع تراعي المنتج — للتاجر فقط (لا إرسال تلقائي).
تبني فوق كشف النية العام مع سياق السلة عند توفره.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Optional, TypedDict

from services.recovery_conversation_state_machine import STAGE_CHECKOUT_READY
from services.recovery_offer_decision import decide_recovery_offer_strategy
from services.behavioral_recovery.state_store import behavioral_dict_for_abandoned_cart
from services.recovery_product_context import (
    recovery_product_context_from_abandoned_cart,
    resolved_category_label,
)
from services.recovery_reply_suggestions import get_recovery_reply_suggestion

if TYPE_CHECKING:
    from models import AbandonedCart


class ProductAwareRecoverySuggestion(TypedDict, total=False):
    suggested_reply: str
    suggested_strategy: str
    optional_offer_type: Optional[str]
    suggestion_reason_ar: str
    ux_badge_ar: Optional[str]
    checkout_cta_mode: Optional[str]
    offer_decision: dict[str, Any]


def _norm_intent(intent: str) -> str:
    k = (intent or "").strip().lower()
    if k == "shipping":
        return "delivery"
    return k


def _fmt_name(name: Optional[str]) -> str:
    s = (name or "").strip()
    return s[:56] + "…" if len(s) > 56 else s


def _ux_badge_from_decision(od: Mapping[str, Any]) -> Optional[str]:
    st = str(od.get("strategy_type") or "")
    if st == "soft_discount_path":
        return "فرصة تحويل مرتفعة"
    if st == "alternative_first":
        return "اقتراح بديل"
    if st in ("reassurance_only", "value_framing_premium"):
        return "تهدئة اعتراض"
    if st == "soft_offer_window":
        return "لا يُنصح بخصم مباشر"
    if st == "checkout_push":
        return "فرصة تحويل عالية"
    return None


def get_product_aware_recovery_suggestion(
    intent: str,
    product_name: Optional[str],
    product_price: Optional[float],
    product_category: Optional[str],
    customer_message: str = "",
    *,
    cheaper_alternative_name: Optional[str] = None,
    cheaper_alternative_price: Optional[float] = None,
    offer_decision: Optional[Mapping[str, Any]] = None,
    adaptive_stage: str = "",
) -> ProductAwareRecoverySuggestion:
    _ = (customer_message or "").strip()
    eff = _norm_intent(intent)
    pn = _fmt_name(product_name)
    cat = (product_category or "").strip()
    adapt = (adaptive_stage or "").strip().lower()
    od0 = dict(offer_decision) if offer_decision else {}
    checkout_layer = (
        eff == "ready_to_buy"
        or adapt == STAGE_CHECKOUT_READY
        or str(od0.get("strategy_type") or "").strip() == "checkout_push"
    )
    if checkout_layer:
        return {
            "suggested_reply": (
                "ممتاز 👍 هذا رابط إكمال الطلب مباشرة، وإذا احتجت أي مساعدة أنا حاضر."
            ),
            "suggested_strategy": "إغلاق هادئ — رابط إكمال بدون تكرار طمأنة سابقة",
            "optional_offer_type": "checkout_cta",
            "suggestion_reason_ar": (
                "العميل في مرحلة إكمال — ردّ قصير يركّز على الرابط وخطوة الدفع يدوياً."
            ),
            "ux_badge_ar": "فرصة تحويل مرتفعة",
            "checkout_cta_mode": "calm_checkout_push",
        }

    if eff == "price":
        od = dict(offer_decision) if offer_decision else {}
        alt = (cheaper_alternative_name or "").strip()
        alt_ok_line = bool(alt and cheaper_alternative_price is not None)
        push_alt = bool(
            alt_ok_line and (not od or bool(od.get("should_offer_alternative")))
        )

        if push_alt:
            alt_short = _fmt_name(alt)
            reply = (
                "نفهمك 👍 فيه خيار قريب من نفس الفكرة بسعر أخف، تحب أرسله لك؟"
            )
            if pn:
                reply = (
                    f"نفهمك 👍 عندنا «{alt_short}» بسعر أخف مقارنة بـ«{pn}»، "
                    "تحب أرسله لك ونشوف يناسبك؟"
                )
            ub = _ux_badge_from_decision(od) if od else "اقتراح بيع"
            return {
                "suggested_reply": reply,
                "suggested_strategy": "توجيه لخيار أقل سعراً",
                "optional_offer_type": "alternative_product",
                "suggestion_reason_ar": (
                    "في السلة منتج بسعر أقل يصلح كبديل تقريبي دون خصم تلقائي — "
                    "بعد مسار قرار يفضّل البديل على الخصم عندما يناسب الهامش."
                ),
                "ux_badge_ar": ub or "اقتراح بديل",
                "checkout_cta_mode": None,
            }

        reply = (
            "نفهمك 👍 كثير يختارونه بسبب الجودة والقيمة مقارنة بالسعر."
        )
        if pn:
            reply = (
                f"نفهمك 👍 كثير يختارون «{pn}» بسبب الجودة والقيمة مقارنة بالسعر."
            )
        if od.get("should_offer_discount"):
            reply += (
                " وإذا تحب نقدّر نشوف لك عرض يناسبك — أنت اللي تقرر وتطبّقه يدوياً 👍"
            )
        reason = "لا يظهر في السلة بديل أوضح بسعر أقل؛ ركّز على القيمة والثقة."
        if product_price is not None and product_price > 0:
            reason += " السعر ظاهر من بيانات السلة للمرجعية فقط — ردّك يبقى يدوياً."
        opt_type: Optional[str] = "value_framing"
        if od.get("should_offer_discount"):
            opt_type = "soft_offer"
        ub2 = _ux_badge_from_decision(od) if od else "تهدئة اعتراض"
        return {
            "suggested_reply": reply,
            "suggested_strategy": "تأكيد قيمة مقابل السعر",
            "optional_offer_type": opt_type,
            "suggestion_reason_ar": reason,
            "ux_badge_ar": ub2 or "تهدئة اعتراض",
            "checkout_cta_mode": None,
        }

    if eff == "delivery":
        reply = (
            "التوصيل عادة سريع 👍 وإذا تحب أرسل لك تفاصيل الوصول لمنطقتك."
        )
        if cat:
            reply = (
                f"التوصيل عادة سريع 👍 ومع «{cat}» نرسل لك تفاصيل الوصول لمنطقتك إذا تحب."
            )
        return {
            "suggested_reply": reply,
            "suggested_strategy": "طمأنة التوصيل وسرعة الشحن",
            "optional_offer_type": "delivery_reassurance",
            "suggestion_reason_ar": "استفسار عن التوصيل — اعرض سرعة تسليم واقعية وتفاصيل المنطقة يدوياً.",
            "ux_badge_ar": "تهدئة اعتراض",
            "checkout_cta_mode": None,
        }

    if eff == "warranty":
        reply = "أكيد 👍 المنتج مغطى بضمان، وإذا تحب ألخص لك النقاط المهمة باختصار."
        if pn:
            reply = (
                f"أكيد 👍 «{pn}» يشمل ضمان، وإذا تحب ألخص لك أهم النقاط باختصار."
            )
        return {
            "suggested_reply": reply,
            "suggested_strategy": "شرح الضمان وبناء الثقة",
            "optional_offer_type": "warranty_trust",
            "suggestion_reason_ar": "العميل يسأل عن الضمان؛ ردّ قصير يعزز المصداقية دون أسلوب دعم فني طويل.",
            "ux_badge_ar": "تهدئة اعتراض",
            "checkout_cta_mode": None,
        }

    if eff == "quality":
        reply = (
            "منتجاتنا أصلية والتقييمات مرتاحة 👍 وإذا تحب أرسل لك أي تفاصيل تزيد راحتك."
        )
        if pn:
            reply = (
                f"«{pn}» أصلي والعملاء يرجعون لنا عليه 👍 "
                "إذا تحب أزودك بتفاصيل تزيد راحتك."
            )
        return {
            "suggested_reply": reply,
            "suggested_strategy": "تعزيز الجودة والمصداقية",
            "optional_offer_type": "quality_proof",
            "suggestion_reason_ar": "سؤال عن الجودة أو الأصالة — دليل خفيف بدل إطالة.",
            "ux_badge_ar": "تهدئة اعتراض",
            "checkout_cta_mode": None,
        }

    if eff == "hesitation":
        base = get_recovery_reply_suggestion("hesitation", customer_message)
        return {
            "suggested_reply": base["suggested_reply"],
            "suggested_strategy": "إبقاء الباب مفتوحاً بلطف",
            "optional_offer_type": None,
            "suggestion_reason_ar": "تردد عام — أعطِ مساحة مع بقاء خط البيع دافئاً.",
            "ux_badge_ar": None,
            "checkout_cta_mode": None,
        }

    base = get_recovery_reply_suggestion(intent, customer_message)
    return {
        "suggested_reply": base["suggested_reply"],
        "suggested_strategy": "متابعة ودية عامة",
        "optional_offer_type": None,
        "suggestion_reason_ar": "لم تُحدد نية دقيقة؛ ردّ آمن يفتح مجال الإغلاق.",
        "ux_badge_ar": None,
        "checkout_cta_mode": None,
    }


def get_product_aware_recovery_suggestion_for_abandoned_cart(
    ac: "AbandonedCart",
    intent: str,
    customer_message: str = "",
) -> ProductAwareRecoverySuggestion:
    ctx = recovery_product_context_from_abandoned_cart(ac)
    cat = resolved_category_label(ctx)
    bh = behavioral_dict_for_abandoned_cart(ac)
    adaptive_stage = str(bh.get("recovery_adaptive_stage") or "").strip()
    decision = decide_recovery_offer_strategy(
        intent,
        ctx.current_product_price,
        cat or "",
        customer_message,
        has_cheaper_alternative=bool(ctx.cheaper_alternative_name),
        adaptive_stage=adaptive_stage,
    )
    result = get_product_aware_recovery_suggestion(
        intent,
        ctx.current_product_name,
        ctx.current_product_price,
        cat,
        customer_message,
        cheaper_alternative_name=ctx.cheaper_alternative_name,
        cheaper_alternative_price=ctx.cheaper_alternative_price,
        offer_decision=decision,
        adaptive_stage=adaptive_stage,
    )
    out: dict[str, Any] = dict(result)
    out["offer_decision"] = dict(decision)
    return out  # type: ignore[return-value]
