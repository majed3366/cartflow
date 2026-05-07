# -*- coding: utf-8 -*-
from __future__ import annotations

from services.recovery_interaction_state import truncate_preview_text
from services.recovery_transition_engine import inbound_patch_for_recovery_reply


def test_truncate_reply_preview() -> None:
    assert truncate_preview_text("هلا", max_chars=10) == "هلا"
    long = "أ" * 50
    out = truncate_preview_text(long, max_chars=10)
    assert len(out) <= 10
    assert out.endswith("…")


def test_inbound_patch_sets_engaged_and_preview() -> None:
    p = inbound_patch_for_recovery_reply("كم مدة التوصيل؟")
    assert p["customer_replied"] is True
    assert p["interactive_mode"] is True
    assert p["recovery_conversation_state"] == "engaged"
    assert p["recovery_reply_intent"] == "delivery"
    assert "توصيل" in (p.get("latest_customer_message") or "")
    assert p.get("latest_customer_reply_at")
    assert p.get("waiting_merchant") is True


def test_inbound_patch_no_question() -> None:
    p = inbound_patch_for_recovery_reply("تمام شكرا")
    assert p.get("waiting_merchant") is False
