# -*- coding: utf-8 -*-
"""رسالة التواصل اليدوي + تلميح العرض في لوحة VIP."""
from __future__ import annotations

from types import SimpleNamespace

from services.vip_cart import (
    vip_offer_card_hint_ar,
    vip_offer_manual_contact_whatsapp_body,
)


def test_hint_and_message_free_shipping_when_enabled() -> None:
    st = SimpleNamespace(
        vip_offer_enabled=True,
        vip_offer_type="free_shipping",
        vip_offer_value=None,
    )
    assert vip_offer_card_hint_ar(st) == "العرض المقترح: شحن مجاني"
    assert vip_offer_manual_contact_whatsapp_body(st) == (
        "🚚 نقدر نخلي الشحن مجاني لك اليوم 🙌\n"
        "تحب نكمل الطلب لك؟"
    )


def test_hint_and_message_discount() -> None:
    st = SimpleNamespace(
        vip_offer_enabled=True,
        vip_offer_type="discount",
        vip_offer_value="10",
    )
    assert vip_offer_card_hint_ar(st) == "العرض المقترح: خصم 10%"
    body = vip_offer_manual_contact_whatsapp_body(st)
    assert body and "خصم 10%" in body
    assert "تحب أفعّله لك الآن؟" in body


def test_message_gift_wrap() -> None:
    st = SimpleNamespace(
        vip_offer_enabled=True,
        vip_offer_type="gift_wrap",
        vip_offer_value=None,
    )
    body = vip_offer_manual_contact_whatsapp_body(st)
    assert body and "تغليف مجاني" in body


def test_message_gift_with_description() -> None:
    st = SimpleNamespace(
        vip_offer_enabled=True,
        vip_offer_type="gift",
        vip_offer_value="عينة عطر",
    )
    body = vip_offer_manual_contact_whatsapp_body(st)
    assert body and "هدية بسيطة" in body
    assert "عينة عطر" in body


def test_fallback_none_when_offer_disabled() -> None:
    st = SimpleNamespace(vip_offer_enabled=False)
    assert vip_offer_card_hint_ar(st) == ""
    assert vip_offer_manual_contact_whatsapp_body(st) is None
