# -*- coding: utf-8 -*-
from __future__ import annotations

from services.recovery_conversation_state_machine import (
    STAGE_CHECKOUT_READY,
    STAGE_PASSIVE_RETURN,
    STAGE_PRICE_OBJECTION,
    STAGE_RETURNED_BROWSING,
    STAGE_RETURNED_CHECKOUT,
    build_return_to_site_behavioral_patch,
    compute_adaptive_transition,
    compute_return_to_site_adaptive_transition,
)
from services.recovery_offer_decision import decide_recovery_offer_strategy
from services.recovery_product_suggestions import get_product_aware_recovery_suggestion


def test_return_checkout_after_checkout_ready() -> None:
    st, reason, path = compute_return_to_site_adaptive_transition(
        prior_conversational_stage=STAGE_CHECKOUT_READY,
        prior_intent="ready_to_buy",
        returned_checkout_page=True,
        returned_product_page=False,
    )
    assert st == STAGE_RETURNED_CHECKOUT
    assert "دفع" in reason or "إكمال" in reason
    assert path


def test_return_product_after_price_objection() -> None:
    st, _, _ = compute_return_to_site_adaptive_transition(
        prior_conversational_stage=STAGE_PRICE_OBJECTION,
        prior_intent="price",
        returned_checkout_page=False,
        returned_product_page=True,
    )
    assert st == STAGE_PASSIVE_RETURN


def test_return_browse_generic_stage() -> None:
    from services.recovery_conversation_state_machine import STAGE_SHIPPING_QUESTIONS

    st, _, _ = compute_return_to_site_adaptive_transition(
        prior_conversational_stage=STAGE_SHIPPING_QUESTIONS,
        prior_intent="delivery",
        returned_checkout_page=False,
        returned_product_page=False,
    )
    assert st == STAGE_RETURNED_BROWSING


def test_build_patch_increments_count_and_sets_flags() -> None:
    prior = {
        "recovery_site_return_count": 2,
        "customer_replied": True,
        "recovery_adaptive_stage": STAGE_PRICE_OBJECTION,
        "recovery_reply_intent": "price",
    }
    p = build_return_to_site_behavioral_patch(
        prior,
        returned_product_page=True,
        returned_checkout_page=False,
        return_timestamp_iso="2026-05-06T10:00:00+00:00",
        fuse_adaptive=True,
    )
    assert p["customer_returned_to_site"] is True
    assert p["recovery_returned_product_page"] is True
    assert p["recovery_site_return_count"] == 3
    assert p.get("recovery_adaptive_stage") == STAGE_PASSIVE_RETURN


def test_build_patch_no_fuse_without_conversation() -> None:
    prior: dict = {}
    p = build_return_to_site_behavioral_patch(
        prior,
        returned_product_page=False,
        returned_checkout_page=False,
        return_timestamp_iso="2026-05-06T10:00:00+00:00",
        fuse_adaptive=True,
    )
    assert "recovery_adaptive_stage" not in p
    assert p["recovery_site_return_count"] == 1


def test_whatsapp_after_returned_checkout_resets_track() -> None:
    st, reason, _ = compute_adaptive_transition(
        prev_stage=STAGE_RETURNED_CHECKOUT,
        prev_intent="ready_to_buy",
        new_intent="price",
        customer_message="لسه غالي",
        turn_index=3,
    )
    assert st == STAGE_PRICE_OBJECTION
    assert "بعد عودة" in reason


def test_offer_completion_assistance_for_returned_checkout_stage() -> None:
    d = decide_recovery_offer_strategy(
        "other",
        50.0,
        "",
        "",
        adaptive_stage=STAGE_RETURNED_CHECKOUT,
    )
    assert d["strategy_type"] == "completion_assistance"
    assert d["should_offer_discount"] is False


def test_suggestion_completion_after_return_checkout() -> None:
    s = get_product_aware_recovery_suggestion(
        "other",
        "ساعة",
        200.0,
        None,
        "",
        adaptive_stage=STAGE_RETURNED_CHECKOUT,
        offer_decision=decide_recovery_offer_strategy(
            "other",
            200.0,
            "",
            "",
            adaptive_stage=STAGE_RETURNED_CHECKOUT,
        ),
    )
    assert "مساعدة" in s["suggested_reply"] or "إكمال" in s["suggested_reply"]
