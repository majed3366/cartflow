# -*- coding: utf-8 -*-
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models import AbandonedCart
from services.cartflow_reply_intent_engine import (
    CONTINUATION_ACTION_ESCALATE,
    CONTINUATION_ACTION_EXPLAIN_SHIPPING,
    CONTINUATION_ACTION_GRACEFUL_EXIT,
    CONTINUATION_ACTION_REASSURANCE,
    CONTINUATION_ACTION_SEND_CHECKOUT,
    CONTINUATION_ACTION_SEND_CHEAPER,
    CONTINUATION_ACTION_WAIT,
    decide_continuation,
    detect_base_intent_v1,
    normalize_inbound_text_v1,
    process_continuation_after_customer_reply,
    reset_continuation_engine_for_tests,
    resolve_contextual_intent,
)
from services.recovery_conversation_tracker import conversation_dashboard_extras


def test_normalize_inbound_text_arabic_punctuation() -> None:
    assert normalize_inbound_text_v1("  نعم!!  ") == "نعم!"
    assert "ايوه" in normalize_inbound_text_v1("أيوه")


@pytest.mark.parametrize(
    "body,expected",
    [
        ("نعم", "confirmation_yes"),
        ("yes", "confirmation_yes"),
        ("الرابط", "wants_link"),
        ("link", "wants_link"),
        ("أرخص", "wants_cheaper"),
        ("cheaper", "wants_cheaper"),
        ("بكم", "asks_price"),
        ("الشحن", "asks_shipping"),
        ("shipping", "asks_shipping"),
        ("بفكر", "hesitation"),
        ("لا شكرا", "rejection"),
        ("خدمة العملاء", "human_help"),
        ("xyz_unknown_12345", "unknown_reply"),
    ],
)
def test_detect_base_intent_v1(body: str, expected: str) -> None:
    assert detect_base_intent_v1(body) == expected


def test_contextual_yes_price_abandonment_without_prior_strategy_key() -> None:
    """First reply after outbound-only recovery: infer prior path from reason_tag."""
    ac = MagicMock(spec=AbandonedCart)
    ac.zid_cart_id = "c1"
    ac.recovery_session_id = "s1"
    ac.cart_url = ""
    d = decide_continuation(
        inbound_body="نعم",
        behavioral={"recovery_previous_offer_strategy": ""},
        reason_tag="price",
        ac=ac,
        prior_behavioral_before_reply={},
    )
    assert d.contextual_intent == "yes_to_cheaper_alternative"
    assert d.action == CONTINUATION_ACTION_SEND_CHEAPER


def test_contextual_intent_yes_differs_by_prior_strategy() -> None:
    assert (
        resolve_contextual_intent(
            "confirmation_yes",
            prior_strategy="checkout_push",
            reason_tag="",
        )
        == "ready_for_checkout"
    )
    assert (
        resolve_contextual_intent(
            "confirmation_yes",
            prior_strategy="cheaper_alternative",
            reason_tag="",
        )
        == "yes_to_cheaper_alternative"
    )


def test_decide_confirmation_yes_after_checkout_push() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.zid_cart_id = "c1"
    ac.recovery_session_id = "s1"
    ac.cart_url = "https://store.example/cart"
    bh = {"recovery_previous_offer_strategy": "checkout_push"}
    d = decide_continuation(
        inbound_body="نعم",
        behavioral=bh,
        reason_tag="other",
        ac=ac,
    )
    assert d.base_intent == "confirmation_yes"
    assert d.contextual_intent == "ready_for_checkout"
    assert d.action == CONTINUATION_ACTION_SEND_CHECKOUT
    assert "رابط إكمال" in d.message_to_send
    assert d.summary_ar == "العميل جاهز للإكمال"


def test_decide_wants_link_summary_merchant_friendly() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.zid_cart_id = "c1"
    ac.recovery_session_id = "s1"
    ac.cart_url = ""
    d = decide_continuation(
        inbound_body="ارسل الرابط",
        behavioral={"recovery_previous_offer_strategy": "checkout_push"},
        reason_tag="",
        ac=ac,
    )
    assert d.contextual_intent == "wants_checkout_link"
    assert d.summary_ar == "العميل يطلب رابط الإكمال"


def test_decide_wants_cheaper() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.zid_cart_id = "c1"
    ac.recovery_session_id = "s1"
    ac.cart_url = ""
    bh: dict = {}
    d = decide_continuation(
        inbound_body="عندك بديل أرخص؟",
        behavioral=bh,
        reason_tag="price",
        ac=ac,
        prior_behavioral_before_reply={},
    )
    assert d.base_intent == "wants_cheaper"
    assert d.action == CONTINUATION_ACTION_SEND_CHEAPER
    assert "سعر أقل" in d.message_to_send


def test_decide_asks_shipping() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.zid_cart_id = "c1"
    ac.recovery_session_id = "s1"
    ac.cart_url = ""
    bh: dict = {}
    d = decide_continuation(
        inbound_body="الشحن كم؟",
        behavioral=bh,
        reason_tag="shipping",
        ac=ac,
    )
    assert d.base_intent == "asks_shipping"
    assert d.action == CONTINUATION_ACTION_EXPLAIN_SHIPPING
    assert "الشحن متاح" in d.message_to_send
    assert d.summary_ar == "العميل يسأل عن الشحن"


def test_decide_hesitation() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.zid_cart_id = "c1"
    ac.recovery_session_id = "s1"
    ac.cart_url = ""
    d = decide_continuation(
        inbound_body="بفكر",
        behavioral={},
        reason_tag="",
        ac=ac,
    )
    assert d.action == CONTINUATION_ACTION_REASSURANCE
    assert "خذ راحتك" in d.message_to_send
    assert d.summary_ar == "العميل متردد"


def test_decide_rejection() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.zid_cart_id = "c1"
    ac.recovery_session_id = "s1"
    ac.cart_url = ""
    d = decide_continuation(
        inbound_body="لا شكرا",
        behavioral={},
        reason_tag="",
        ac=ac,
    )
    assert d.action == CONTINUATION_ACTION_GRACEFUL_EXIT
    assert d.summary_ar == "العميل جاهز للإغلاق"


def test_decide_escalation_to_human() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.zid_cart_id = "c1"
    ac.recovery_session_id = "s1"
    ac.cart_url = ""
    d = decide_continuation(
        inbound_body="أبغى موظف",
        behavioral={},
        reason_tag="",
        ac=ac,
    )
    assert d.action == CONTINUATION_ACTION_ESCALATE
    assert "فريق المتابعة" in d.message_to_send
    assert d.summary_ar == "طلب تدخل بشري"


def test_dashboard_continuation_summary_merchant_friendly() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.status = "abandoned"
    ac.customer_phone = "+966501234567"
    bh = {
        "continuation_summary_ar": "العميل يسأل عن الشحن",
        "continuation_state": "customer_asking_shipping",
    }
    extras = conversation_dashboard_extras(ac, behavioral_payload=bh)
    assert extras.get("normal_recovery_continuation_summary_ar") == "العميل يسأل عن الشحن"
    assert extras.get("normal_recovery_continuation_state_key") == "customer_asking_shipping"
    assert "continuation_base_intent" not in extras


def test_process_duplicate_reply_prevents_second_send() -> None:
    reset_continuation_engine_for_tests()
    ac = MagicMock(spec=AbandonedCart)
    ac.vip_mode = False
    ac.recovery_session_id = "sess-dup"
    ac.zid_cart_id = "cart-dup"
    ac.store_id = None
    phone_key = "966501112233"

    merged_bh = {"recovery_previous_offer_strategy": "checkout_push"}

    with patch(
        "services.behavioral_recovery.state_store.normal_recovery_message_was_sent_for_abandoned",
        return_value=True,
    ), patch(
        "services.behavioral_recovery.state_store.behavioral_dict_for_abandoned_cart",
        return_value=merged_bh,
    ), patch(
        "services.behavioral_recovery.state_store.merge_behavioral_state",
    ) as mm, patch(
        "services.cartflow_reply_intent_engine._reason_tag_for_abandoned_cart",
        return_value="other",
    ), patch(
        "services.whatsapp_send.send_whatsapp",
        return_value={"ok": True},
    ) as sw, patch(
        "services.cartflow_reply_intent_engine.continuation_auto_reply_enabled",
        return_value=True,
    ), patch(
        "services.cartflow_reply_intent_engine.continuation_cooldown_seconds",
        return_value=15.0,
    ), patch(
        "services.cartflow_reply_intent_engine.continuation_dedup_seconds",
        return_value=300.0,
    ):
        process_continuation_after_customer_reply(
            ac,
            inbound_body="نعم",
            customer_phone_key=phone_key,
            prior_behavioral_before_reply={},
        )
        process_continuation_after_customer_reply(
            ac,
            inbound_body="نعم",
            customer_phone_key=phone_key,
            prior_behavioral_before_reply={},
        )

    assert sw.call_count == 1
    assert mm.call_count == 1


def test_process_escalation_sets_flags_and_skips_later() -> None:
    reset_continuation_engine_for_tests()
    ac = MagicMock(spec=AbandonedCart)
    ac.vip_mode = False
    ac.recovery_session_id = "sess-esc"
    ac.zid_cart_id = "cart-esc"
    ac.store_id = None
    phone_key = "966501112244"

    bh_escalated = {
        "continuation_escalated_human": True,
        "recovery_previous_offer_strategy": "checkout_push",
    }

    with patch(
        "services.behavioral_recovery.state_store.normal_recovery_message_was_sent_for_abandoned",
        return_value=True,
    ), patch(
        "services.behavioral_recovery.state_store.behavioral_dict_for_abandoned_cart",
        return_value=bh_escalated,
    ), patch(
        "services.whatsapp_send.send_whatsapp",
        return_value={"ok": True},
    ) as sw, patch(
        "services.behavioral_recovery.state_store.merge_behavioral_state",
    ):
        process_continuation_after_customer_reply(
            ac,
            inbound_body="نعم",
            customer_phone_key=phone_key,
            prior_behavioral_before_reply={},
        )

    sw.assert_not_called()


def test_no_second_auto_send_within_cooldown_different_body() -> None:
    reset_continuation_engine_for_tests()
    ac = MagicMock(spec=AbandonedCart)
    ac.vip_mode = False
    ac.recovery_session_id = "sess-cd"
    ac.zid_cart_id = "cart-cd"
    ac.store_id = None
    phone_key = "966501112255"
    merged_bh = {"recovery_previous_offer_strategy": "checkout_push"}

    with patch(
        "services.behavioral_recovery.state_store.normal_recovery_message_was_sent_for_abandoned",
        return_value=True,
    ), patch(
        "services.behavioral_recovery.state_store.behavioral_dict_for_abandoned_cart",
        return_value=merged_bh,
    ), patch(
        "services.cartflow_reply_intent_engine._reason_tag_for_abandoned_cart",
        return_value="other",
    ), patch(
        "services.behavioral_recovery.state_store.merge_behavioral_state",
    ), patch(
        "services.whatsapp_send.send_whatsapp",
        return_value={"ok": True},
    ) as sw, patch(
        "services.cartflow_reply_intent_engine.continuation_auto_reply_enabled",
        return_value=True,
    ), patch(
        "services.cartflow_reply_intent_engine.continuation_cooldown_seconds",
        return_value=3600.0,
    ), patch(
        "services.cartflow_reply_intent_engine.continuation_dedup_seconds",
        return_value=10.0,
    ):
        process_continuation_after_customer_reply(
            ac,
            inbound_body="نعم",
            customer_phone_key=phone_key,
            prior_behavioral_before_reply={},
        )
        process_continuation_after_customer_reply(
            ac,
            inbound_body="تمام",
            customer_phone_key=phone_key,
            prior_behavioral_before_reply={},
        )

    assert sw.call_count == 1


def test_unknown_reply_waits_without_template_send_flag() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.zid_cart_id = "c1"
    ac.recovery_session_id = "s1"
    ac.cart_url = ""
    d = decide_continuation(
        inbound_body="zzz_no_match_999",
        behavioral={"recovery_previous_offer_strategy": "checkout_push"},
        reason_tag="",
        ac=ac,
    )
    assert d.action == CONTINUATION_ACTION_WAIT
    assert d.should_send is False
