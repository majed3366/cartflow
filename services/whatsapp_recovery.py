# -*- coding: utf-8 -*-
"""
نصوص واتساب للاسترجاع — ليست نسخة من الودجيت ولا من ‎ai_message_builder‎.
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


def build_whatsapp_recovery_message(
    customer_type: str,
    objection_type: str,
    cart: Optional[Mapping[str, Any]] = None,
) -> str:
    """
    يبني رسالة واتساب دافئة، شخصية، بلهجة تصلح للسعودية.
    - عميل جديد: ترحيب أخف وكوبون أخف
    - عائد: تقدير أوضح وكوبون أقوى
    - سعر / جودة: زوايا نصيّة مختلفة بالكامل عن الودجيت
    """
    ct = (customer_type or "").strip().lower()
    ot = (objection_type or "").strip().lower()
    cart = cart or {}
    who = _first_name(cart)

    if ct not in VALID_CUSTOMER or ot not in VALID_OBJECTION:
        if ot == "quality":
            return _quality_fallback(who)
        return _price_fallback(who)

    if ct == "returning" and ot == "price":
        return _returning_price(who, cart)
    if ct == "returning" and ot == "quality":
        return _returning_quality(who, cart)
    if ct == "new" and ot == "price":
        return _new_price(who, cart)
    return _new_quality(who, cart)


def _greet(who: Optional[str], default_open: str) -> str:
    if who:
        return f"حياك الله يا {who}.\n{default_open}"
    return f"{default_open}\n"


def _price_fallback(who: Optional[str]) -> str:
    t = f"يا {who}، " if who else ""
    return (
        f"{t}نبي نطمّنك: اللي اخترتَه يستاهل—ولو بغيت تغيّر رايك "
        f"لاحقاً تقدر تتصل علينا. شكراً لأنك معنا."
    )


def _quality_fallback(who: Optional[str]) -> str:
    t = f"يا {who}، " if who else ""
    return (
        f"{t}نختار موردينا بعناية—ودوم نحب نسمع رأيك لو في أي استفسار عن القطعة."
    )


def _returning_price(who: Optional[str], _cart: Mapping[str, Any]) -> str:
    # كوبون أقوى: مختلف عن ‎SAVE10 / WELCOME‎ في الودجيت
    line = _greet(
        who,
        "نورتنا مرّة ثانية، وما ننسى اللي اختارناك قبل. "
        "لو السعر يوم كان يمّا على بالك: حطينا لك مزايا خاصة للي رجعوا—استخدم: BACK20",
    )
    return line.strip() + (
        "\n\nنقدّر وقفتك معنا وما نبي يفوتك عرض يناسب ميزانيتك—اكتب لي لو تحب تعدّل الطلب."
    )


def _returning_quality(who: Optional[str], _cart: Mapping[str, Any]) -> str:
    line = _greet(
        who,
        "رجوعك لنا بحد ذاته يعني إنك تثق باللي نوصله لك. "
        "نفس الخامة ونفس الشي اللي دوم تطلبه—نضيفه لك بخصم تقدير: AMEEN18",
    )
    return line.strip() + "\n\nلو بغيت مواصفات أدق لأي قطعة، بعث لي باسم المنتج وأنا ردّي فوري."


def _new_price(who: Optional[str], _cart: Mapping[str, Any]) -> str:
    line = _greet(
        who,
        "مسرورين بزيارة أولى لك عندنا. ميزان السعر مهم؟ ومن حقّك—وهذي مفاجأة خفيفة: FIRST8",
    )
    return line.strip() + (
        "\n\nما نحب الضغط: إذا بغيت توازن السعر والكمية، قلّي وأنا أرتّب لك اقتراح واضح."
    )


def _new_quality(who: Optional[str], _cart: Mapping[str, Any]) -> str:
    line = _greet(
        who,
        "أهلاً فيك—أول خطوة معنا نبيها تطمّنك. جودة القطع عندنا خط أحمر، "
        "وإذا بغيت تتأكد: هذي لمسة بسيطة منا TRUST5",
    )
    return line.strip() + "\n\nاسأل عن التفصيلة اللي تبغاها: صور ومواصفات—أنا هنا."

