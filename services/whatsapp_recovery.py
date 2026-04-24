# -*- coding: utf-8 -*-
"""
نصوص واتساب للاسترجاع — قصيرة (٢–٣ أسطر)، لغة بسيطة وطنية.
تُرجع نصاً فقط؛ لا إرسال فعلي.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

VALID_CUSTOMER = frozenset({"new", "returning"})
VALID_OBJECTION = frozenset({"price", "quality"})


def _first_name(cart: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not cart:
        return None
    raw = (cart.get("customer_name") or cart.get("name") or "").strip()
    if not raw:
        return None
    return raw.split()[0]


def _cta(cart: Mapping[str, Any]) -> str:
    u = (cart.get("cart_url") or cart.get("checkout_url") or "").strip()
    if u:
        return f"تبي تكمل؟ ادخل السلة: {u}"
    return "تبي تكمل؟ رجع لسلة المشتريات واضغط إكمال الطلب."


def build_whatsapp_recovery_message(
    customer_type: str,
    objection_type: str,
    cart: Optional[Mapping[str, Any]] = None,
) -> str:
    """
    ٢–٣ أسطر: ترحيب/وضع (جديد/عائد) + سعر/جودة + كوبون، ثم دعوة واضحة للرجوع للسلة.
    """
    ct = (customer_type or "").strip().lower()
    ot = (objection_type or "").strip().lower()
    cart = cart or {}
    who = _first_name(cart)

    if ct not in VALID_CUSTOMER or ot not in VALID_OBJECTION:
        if ot == "quality":
            return _quality_fallback(who, cart)
        return _price_fallback(who, cart)

    if ct == "returning" and ot == "price":
        return _returning_price(who, cart)
    if ct == "returning" and ot == "quality":
        return _returning_quality(who, cart)
    if ct == "new" and ot == "price":
        return _new_price(who, cart)
    return _new_quality(who, cart)


def _open(who: Optional[str], line: str) -> str:
    if who:
        return f"يا {who}، {line}"
    return line


def _price_fallback(who: Optional[str], cart: Mapping[str, Any]) -> str:
    a = _open(who, "نبي تكمّل اختيارك—ميزانك يهمنّا.")
    return f"{a}\n{_cta(cart)}"


def _quality_fallback(who: Optional[str], cart: Mapping[str, Any]) -> str:
    a = _open(who, "للتأكد من الجودة: ردّي هنا، وإن حاب تكمل—تحت أمرك.")
    return f"{a}\n{_cta(cart)}"


def _returning_price(who: Optional[str], cart: Mapping[str, Any]) -> str:
    # راجع + سعر: كود أقوى
    a = _open(
        who,
        "نورتنا مرّة ثانية—نقدّرك. كود خاص: BACK20",
    )
    return f"{a}\n{_cta(cart)}"


def _returning_quality(who: Optional[str], cart: Mapping[str, Any]) -> str:
    a = _open(
        who,
        "ثقتك واجب علينا. خصم تقدير: AMEEN18",
    )
    return f"{a}\n{_cta(cart)}"


def _new_price(who: Optional[str], cart: Mapping[str, Any]) -> str:
    a = _open(
        who,
        "هلا فيك—أول مرة؟ مفاجأة خفيفة: FIRST8",
    )
    return f"{a}\n{_cta(cart)}"


def _new_quality(who: Optional[str], cart: Mapping[str, Any]) -> str:
    a = _open(
        who,
        "ودّنا ترتاح من الجودة. كود بسيط: TRUST5",
    )
    return f"{a}\n{_cta(cart)}"
