# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from models import AbandonedCart
from services.recovery_conversation_state_machine import (
    COOLDOWN_CHECKOUT_SILENCE,
    COOLDOWN_COOLING_DOWN,
    COOLDOWN_GENTLE_FOLLOWUP_CANDIDATE,
    STAGE_CHECKOUT_READY,
    STAGE_PRICE_OBJECTION,
    compute_conversational_cooldown,
)
from services.recovery_conversation_tracker import conversation_dashboard_extras
from services.recovery_product_suggestions import _apply_cooldown_to_suggestion


def _iso_minutes_ago(now: datetime, minutes: float) -> str:
    dt = now - timedelta(minutes=minutes)
    s = dt.isoformat()
    if s.endswith("+00:00"):
        return s.replace("+00:00", "Z")
    return s


def test_checkout_ready_silence_is_checkout_silence() -> None:
    now = datetime(2026, 5, 6, 14, 0, tzinfo=timezone.utc)
    iso = _iso_minutes_ago(now, 30)
    d = compute_conversational_cooldown(
        last_customer_reply_iso=iso,
        adaptive_stage_key=STAGE_CHECKOUT_READY,
        adaptive_turn_count=2,
        now_utc=now,
    )
    assert d["cooldown_state"] == COOLDOWN_CHECKOUT_SILENCE
    assert d["recommend_followup"] is True
    assert "اختفى" in d["cooldown_context_ar"] or "الإكمال" in d["cooldown_context_ar"]


def test_price_objection_silence_is_cooling_down() -> None:
    now = datetime(2026, 5, 6, 14, 0, tzinfo=timezone.utc)
    iso = _iso_minutes_ago(now, 40)
    d = compute_conversational_cooldown(
        last_customer_reply_iso=iso,
        adaptive_stage_key=STAGE_PRICE_OBJECTION,
        adaptive_turn_count=2,
        now_utc=now,
    )
    assert d["cooldown_state"] == COOLDOWN_COOLING_DOWN


def test_price_short_silence_is_gentle_or_active() -> None:
    now = datetime(2026, 5, 6, 14, 0, tzinfo=timezone.utc)
    iso = _iso_minutes_ago(now, 25)
    d = compute_conversational_cooldown(
        last_customer_reply_iso=iso,
        adaptive_stage_key=STAGE_PRICE_OBJECTION,
        adaptive_turn_count=1,
        now_utc=now,
    )
    assert d["cooldown_state"] in (
        COOLDOWN_GENTLE_FOLLOWUP_CANDIDATE,
        COOLDOWN_COOLING_DOWN,
    )


def test_cooldown_adjusts_checkout_suggestion() -> None:
    snap = compute_conversational_cooldown(
        last_customer_reply_iso=_iso_minutes_ago(
            datetime(2026, 5, 6, 14, 0, tzinfo=timezone.utc), 30
        ),
        adaptive_stage_key=STAGE_CHECKOUT_READY,
        adaptive_turn_count=1,
        now_utc=datetime(2026, 5, 6, 14, 0, tzinfo=timezone.utc),
    )
    base = {
        "suggested_reply": "ممتاز 👍 هذا رابط",
        "suggested_strategy": "x",
        "optional_offer_type": "checkout_cta",
        "suggestion_reason_ar": "y",
        "ux_badge_ar": "z",
        "checkout_cta_mode": "calm_checkout_push",
    }
    out = _apply_cooldown_to_suggestion(base, snap)
    assert "تذكير هادئ" in str(out.get("suggested_reply") or "")
    assert out.get("checkout_cta_mode") == "cooldown_checkout_nudge"


def test_dashboard_exposes_cooldown_fields() -> None:
    ac = MagicMock(spec=AbandonedCart)
    ac.status = "abandoned"
    ac.customer_phone = "+966501234567"

    now = datetime(2026, 5, 6, 14, 0, tzinfo=timezone.utc)
    iso = _iso_minutes_ago(now, 45)

    bh = {
        "customer_replied": True,
        "interactive_mode": True,
        "recovery_conversation_state": "engaged",
        "recovery_reply_intent": "price",
        "recovery_adaptive_stage": STAGE_CHECKOUT_READY,
        "recovery_adaptive_turn_count": 1,
        "recovery_adaptive_path_label_ar": "",
        "recovery_last_transition_reason_ar": "",
        "last_customer_reply_preview": "أرسل الرابط",
        "latest_customer_message": "أرسل الرابط",
        "last_customer_reply_at": iso,
        "latest_customer_reply_at": iso,
    }

    fake_snap = compute_conversational_cooldown(
        last_customer_reply_iso=iso,
        adaptive_stage_key=STAGE_CHECKOUT_READY,
        adaptive_turn_count=1,
        now_utc=now,
    )

    with patch(
        "services.recovery_conversation_tracker.behavioral_dict_for_abandoned_cart",
        return_value=bh,
    ), patch(
        "services.recovery_conversation_tracker.compute_conversational_cooldown",
        return_value=fake_snap,
    ):
        extras = conversation_dashboard_extras(ac)

    assert extras.get("normal_recovery_cooldown_panel") is True
    assert extras.get("normal_recovery_cooldown_state_key") == COOLDOWN_CHECKOUT_SILENCE
    assert extras.get("normal_recovery_silence_duration_display_ar")
    assert extras.get("normal_recovery_activity_level_ar")
    assert extras.get("normal_recovery_followup_recommendation_ar")
