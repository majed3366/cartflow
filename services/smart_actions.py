# -*- coding: utf-8 -*-
"""Rule-based smart action hints for merchant dashboard (v1 — advisory only)."""

from __future__ import annotations

from typing import Any, Mapping, Optional, TypedDict


class CartSmartActionPayload(TypedDict):
    action_key: str
    title_ar: str
    reason_ar: str
    cta_ar: str


def normalize_smart_action_reason_tag(reason_tag: Optional[str]) -> Optional[str]:
    """
    Canonical price token for الإجراء المقترح — بدون تغيير سلاسل أخرى غير الأسعار.

    السعر‎ /‎ price_high‎ /‎ العربية المعتمدة‎ →‎ ``price_high``.
    """
    if reason_tag is None:
        return None
    raw = str(reason_tag).strip()
    if not raw:
        return None
    lk = raw.casefold()
    if lk == "price" or lk == "price_high":
        return "price_high"
    if "".join(raw.split()) == "السعرمرتفع":
        return "price_high"
    return raw


def _normalized_price_related(reason_tag: Optional[str]) -> bool:
    t = (reason_tag or "").strip().lower()
    return t == "price_high" or t in {"price"}


def _resolve_cart_smart_action(
    *,
    is_vip: bool,
    reason_tag: Optional[str],
    vip_lifecycle_effective: str,
    has_customer_phone: bool,
) -> CartSmartActionPayload:
    """
    Resolve the suggested next merchant action.

    Evaluation order matches product spec:
    VIP + price → VIP contacted → VIP no phone → normal + price → default.
    """
    lc = (vip_lifecycle_effective or "").strip().lower()

    if is_vip and _normalized_price_related(reason_tag):
        return {
            "action_key": "vip_suggest_simple_offer",
            "title_ar": "اقترح عرض بسيط",
            "reason_ar": "العميل متردد بسبب السعر، والسلة عالية القيمة.",
            "cta_ar": "استخدم عرض جاهز",
        }
    if is_vip and lc == "contacted":
        return {
            "action_key": "vip_gentle_followup",
            "title_ar": "تابع بلطف",
            "reason_ar": "تم التواصل مع العميل، والخطوة المناسبة الآن تذكير خفيف.",
            "cta_ar": "إرسال تذكير لطيف",
        }
    if is_vip and not has_customer_phone:
        return {
            "action_key": "vip_wait_for_phone",
            "title_ar": "انتظر رقم العميل",
            "reason_ar": "السلة مميزة لكن لا يوجد رقم للتواصل حتى الآن.",
            "cta_ar": "لا يوجد إجراء الآن",
        }
    if (not is_vip) and _normalized_price_related(reason_tag):
        return {
            "action_key": "normal_standard_recovery_price",
            "title_ar": "استرجاع عادي",
            "reason_ar": "السلة عادية، لا تستخدم خصم قوي في البداية.",
            "cta_ar": "إرسال تذكير عادي",
        }

    return {
        "action_key": "default_gentle_followup",
        "title_ar": "متابعة تلقائية",
        "reason_ar": "لا توجد إشارة قوية تستدعي تدخلاً يدوياً.",
        "cta_ar": "النظام يتابع تلقائياً",
    }


def get_cart_smart_action(cart: Mapping[str, Any]) -> CartSmartActionPayload:
    """
    Rule-based hint for the merchant dashboard.

    Expected snapshot keys on ``cart``:
    ``is_vip`` (bool), ``reason_tag`` (optional str),
    ``vip_lifecycle_effective`` (str), ``has_customer_phone`` (bool).
    """
    raw_rt = cart.get("reason_tag")
    resolved_tag: Optional[str] = None
    if raw_rt is not None:
        s_rt = str(raw_rt).strip()
        resolved_tag = normalize_smart_action_reason_tag(s_rt if s_rt else None)

    return _resolve_cart_smart_action(
        is_vip=bool(cart.get("is_vip")),
        reason_tag=resolved_tag,
        vip_lifecycle_effective=str(cart.get("vip_lifecycle_effective") or "abandoned"),
        has_customer_phone=bool(cart.get("has_customer_phone")),
    )


def smart_action_cta_target(action_key: str) -> str:
    """Stable hint for highlighting an existing manual control (UX only)."""
    return {
        "vip_suggest_simple_offer": "offer_prefill",
        "vip_gentle_followup": "reminder_prefill",
        "normal_standard_recovery_price": "reminder_prefill",
        "default_gentle_followup": "contact",
        "vip_wait_for_phone": "none",
    }.get(action_key, "none")
