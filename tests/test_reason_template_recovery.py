# -*- coding: utf-8 -*-
from __future__ import annotations

import json

from services.reason_template_recovery import (
    canonical_reason_template_key,
    reason_template_blocks_recovery_whatsapp,
    resolve_recovery_whatsapp_message_with_reason_templates,
)
from services.recovery_message_templates import WHATSAPP_REASON_TEMPLATES


def test_canonical_reason_keys() -> None:
    assert canonical_reason_template_key("price_high") == "price"
    assert canonical_reason_template_key("shipping_delay") == "shipping"
    assert canonical_reason_template_key("warranty_issue") == "warranty"
    assert canonical_reason_template_key("thinking") == "thinking"


def test_blocks_when_disabled() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {"price": {"enabled": False, "message": "لا ترسل"}}
        )

    assert reason_template_blocks_recovery_whatsapp("price_high", _S()) is True


def test_no_block_when_missing_entry() -> None:
    class _S:
        reason_templates_json = None

    assert reason_template_blocks_recovery_whatsapp("price_high", _S()) is False


def test_resolve_uses_reason_template_message_when_enabled() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {"shipping": {"enabled": True, "message": "نص سبب الشحن المخصص"}}
        )

    msg = resolve_recovery_whatsapp_message_with_reason_templates(
        "shipping_cost",
        store=_S(),
    )
    assert msg == "نص سبب الشحن المخصص"


def test_resolve_falls_back_when_empty_message() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {"shipping": {"enabled": True, "message": "   "}}
        )

    msg = resolve_recovery_whatsapp_message_with_reason_templates(
        "shipping_cost",
        store=_S(),
    )
    assert msg == WHATSAPP_REASON_TEMPLATES["shipping"]
