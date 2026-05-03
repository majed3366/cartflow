# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

import pytest

from services.decision_engine import decide_recovery_action
from services.recovery_message_templates import (
    DEFAULT_WHATSAPP_TEMPLATE_MESSAGE,
    WHATSAPP_REASON_TEMPLATES,
    resolve_whatsapp_recovery_template_message,
)


def test_template_shipping_and_price_high() -> None:
    assert (
        resolve_whatsapp_recovery_template_message("shipping")
        == WHATSAPP_REASON_TEMPLATES["shipping"]
    )
    assert (
        resolve_whatsapp_recovery_template_message("price_high")
        == WHATSAPP_REASON_TEMPLATES["price"]
    )


def test_template_unknown_falls_back_default() -> None:
    assert (
        resolve_whatsapp_recovery_template_message("unknown_xyz")
        == DEFAULT_WHATSAPP_TEMPLATE_MESSAGE
    )


def test_decide_recovery_action_uses_template_message() -> None:
    r = decide_recovery_action("shipping_cost", store=None)
    assert r["action"] == "highlight_shipping"
    assert r["message"] == WHATSAPP_REASON_TEMPLATES["shipping"]
    assert r["send_customer"] is True
    assert r["send_merchant"] is False


def test_decide_recovery_action_respects_store_template() -> None:
    class _S:
        template_shipping = "شحن مخصص من المتجر"

    r = decide_recovery_action("shipping_cost", store=_S())
    assert r["message"] == "شحن مخصص من المتجر"
    assert r["send_customer"] is True
    assert r["send_merchant"] is False


def test_decide_recovery_action_vip_overrides_engine() -> None:
    r = decide_recovery_action("price_high", store=None, is_vip_cart_flag=True)
    assert r["action"] == "vip_manual_handling"
    assert r["message"] == ""
    assert r["send_customer"] is False
    assert r["send_merchant"] is True


def test_template_selected_log_lines() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        resolve_whatsapp_recovery_template_message("delivery_time")
    out = buf.getvalue()
    assert "[TRIGGER TEMPLATE USED]" in out
    assert "[TEMPLATE SOURCE]" in out
    assert "delivery_time" in out
    assert "source=" in out
    assert WHATSAPP_REASON_TEMPLATES["delivery"] in out


def test_store_template_overrides_builtin() -> None:
    class _FakeStore:
        template_price = "رسالة مخصصة من لوحة التحكم"

    msg = resolve_whatsapp_recovery_template_message(
        "price_high",
        store=_FakeStore(),
    )
    assert msg == "رسالة مخصصة من لوحة التحكم"


def test_trigger_template_overrides_when_enabled() -> None:
    class _FakeStore:
        trigger_templates_json = json.dumps(
            {"price": {"enabled": True, "message": "نص من القالب المشغّل"}}
        )

    msg = resolve_whatsapp_recovery_template_message(
        "price_high",
        store=_FakeStore(),
    )
    assert msg == "نص من القالب المشغّل"


def test_trigger_wins_over_dashboard_template_column() -> None:
    class _FakeStore:
        template_price = "نص عمود لوحة التحكم"
        trigger_templates_json = json.dumps(
            {"price": {"enabled": True, "message": "أولوية القالب المشغّل"}}
        )

    msg = resolve_whatsapp_recovery_template_message("price", store=_FakeStore())
    assert msg == "أولوية القالب المشغّل"


def test_trigger_disabled_falls_back_to_dashboard_column() -> None:
    class _FakeStore:
        trigger_templates_json = json.dumps(
            {"price": {"enabled": False, "message": "معطّل"}}
        )
        template_price = "من عمود لوحة التحكم"

    msg = resolve_whatsapp_recovery_template_message(
        "price",
        store=_FakeStore(),
    )
    assert msg == "من عمود لوحة التحكم"


def test_thinking_maps_to_other_builtin_template() -> None:
    msg = resolve_whatsapp_recovery_template_message("thinking")
    assert msg == WHATSAPP_REASON_TEMPLATES["other"]

def test_empty_store_template_falls_back() -> None:
    class _FakeStore:
        template_price = "   "

    msg = resolve_whatsapp_recovery_template_message(
        "price",
        store=_FakeStore(),
    )
    assert msg == WHATSAPP_REASON_TEMPLATES["price"]


@pytest.mark.parametrize(
    "tag,expected_key",
    [
        ("shipping_cost", "shipping"),
        ("quality_uncertainty", "quality"),
        ("warranty", "warranty"),
    ],
)
def test_layer_d_tags_map(tag: str, expected_key: str) -> None:
    assert resolve_whatsapp_recovery_template_message(
        tag
    ) == WHATSAPP_REASON_TEMPLATES[expected_key]
