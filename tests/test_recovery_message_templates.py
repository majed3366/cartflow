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
    r = decide_recovery_action("shipping_cost")
    assert r["action"] == "highlight_shipping"
    assert r["message"] == WHATSAPP_REASON_TEMPLATES["shipping"]


def test_template_selected_log_lines() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        resolve_whatsapp_recovery_template_message("delivery_time")
    out = buf.getvalue()
    assert "[TEMPLATE SELECTED]" in out
    assert "delivery_time" in out
    assert WHATSAPP_REASON_TEMPLATES["delivery"] in out


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
