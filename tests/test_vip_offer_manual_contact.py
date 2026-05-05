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
    assert (
        vip_offer_manual_contact_whatsapp_body(st)
        == "هلا 👋 لاحظنا إن عندك سلة مميزة، ونقدر نقدم لك شحن مجاني لإكمال الطلب 🚚"
    )


def test_hint_and_message_discount() -> None:
    st = SimpleNamespace(
        vip_offer_enabled=True,
        vip_offer_type="discount",
        vip_offer_value="10",
    )
    assert vip_offer_card_hint_ar(st) == "العرض المقترح: خصم 10%"
    assert "خصم 10%" in (vip_offer_manual_contact_whatsapp_body(st) or "")


def test_fallback_none_when_offer_disabled() -> None:
    st = SimpleNamespace(vip_offer_enabled=False)
    assert vip_offer_card_hint_ar(st) == ""
    assert vip_offer_manual_contact_whatsapp_body(st) is None
