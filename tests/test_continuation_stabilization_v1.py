# -*- coding: utf-8 -*-
from __future__ import annotations

import io
from contextlib import redirect_stdout
from unittest.mock import MagicMock

import pytest

from services.cartflow_reply_intent_engine import (
    CONTINUATION_ACTION_REASSURANCE,
    CONTINUATION_ACTION_SEND_CHEAPER,
    CONTINUATION_ACTION_WAIT,
    decide_continuation,
)
from services.continuation_stabilization_v1 import (
    CONTINUATION_TYPE_REASSURANCE,
    CONTINUATION_TYPE_STOPPED,
    DELIVERY_SAFE_REASSURANCE_AR,
    PRICE_REASSURANCE_MESSAGE_AR,
)
from services.reply_intent_handling import INTENT_PRICE, INTENT_PURCHASE, INTENT_STOP


def _mock_ac() -> MagicMock:
    ac = MagicMock()
    ac.zid_cart_id = "c-stab"
    ac.recovery_session_id = "s-stab"
    ac.cart_url = ""
    ac.store_id = None
    ac.raw_payload = None
    return ac


def test_ghali_no_cheaper_alternative_only_reassurance() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        d = decide_continuation(
            inbound_body="غالي",
            behavioral={},
            reason_tag="price",
            ac=_mock_ac(),
        )
    assert d.action != CONTINUATION_ACTION_SEND_CHEAPER
    assert d.action == CONTINUATION_ACTION_REASSURANCE
    assert PRICE_REASSURANCE_MESSAGE_AR in d.message_to_send
    assert "لقينا لك خيار" not in d.message_to_send
    assert "بسعر أقل" not in d.message_to_send
    assert d.lifecycle_intent == INTENT_PRICE
    assert d.continuation_type == CONTINUATION_TYPE_REASSURANCE
    out = buf.getvalue()
    assert "[CONTINUATION DECISION]" in out
    assert "intent=PRICE" in out
    assert "continuation_type=reassurance" in out


def test_purchase_stops_continuation() -> None:
    d = decide_continuation(
        inbound_body="تم الطلب",
        behavioral={},
        reason_tag="price",
        ac=_mock_ac(),
    )
    assert d.stop_continuation is True
    assert d.should_send is False
    assert d.lifecycle_intent == INTENT_PURCHASE
    assert d.continuation_type == CONTINUATION_TYPE_STOPPED


def test_stop_intent_stops_continuation() -> None:
    d = decide_continuation(
        inbound_body="لا أريد",
        behavioral={},
        reason_tag="price",
        ac=_mock_ac(),
    )
    assert d.stop_continuation is True
    assert d.should_send is False
    assert d.lifecycle_intent == INTENT_STOP


def test_delivery_safe_reassurance_no_fake_promise() -> None:
    d = decide_continuation(
        inbound_body="متى التوصيل",
        behavioral={},
        reason_tag="shipping",
        ac=_mock_ac(),
    )
    assert DELIVERY_SAFE_REASSURANCE_AR in d.message_to_send
    assert "أيام عمل بسيطة" not in d.message_to_send
    assert "غالباً يكون خلال" not in d.message_to_send


def test_wants_cheaper_phrase_maps_to_safe_reassurance_not_product_intel() -> None:
    d = decide_continuation(
        inbound_body="عندك بديل أرخص؟",
        behavioral={},
        reason_tag="price",
        ac=_mock_ac(),
        prior_behavioral_before_reply={},
    )
    assert d.base_intent == "wants_cheaper"
    assert d.action == CONTINUATION_ACTION_REASSURANCE
    assert d.action != CONTINUATION_ACTION_SEND_CHEAPER
