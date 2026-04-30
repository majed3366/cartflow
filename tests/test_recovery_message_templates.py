# -*- coding: utf-8 -*-
from __future__ import annotations

import io
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


def test_decide_recovery_action_respects_store_template() -> None:
    class _S:
        template_shipping = "شحن مخصص من المتجر"

    r = decide_recovery_action("shipping_cost", store=_S())
    assert r["message"] == "شحن مخصص من المتجر"


def test_template_selected_log_lines() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        resolve_whatsapp_recovery_template_message("delivery_time")
    out = buf.getvalue()
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
