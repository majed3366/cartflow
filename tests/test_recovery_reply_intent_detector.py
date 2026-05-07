# -*- coding: utf-8 -*-
from __future__ import annotations

from services.recovery_reply_intent_detector import detect_recovery_reply_intent
from services.recovery_reply_intent_labels import recovery_reply_intent_badge_ar


def test_ghali_price() -> None:
    assert detect_recovery_reply_intent("غالي شوي") == "price"


def test_delivery_question() -> None:
    assert detect_recovery_reply_intent("متى التوصيل؟") == "delivery"


def test_ready_to_buy_ar() -> None:
    assert detect_recovery_reply_intent("أبي أكمل الطلب") == "ready_to_buy"


def test_badge_labels_exist() -> None:
    assert "سعر" in recovery_reply_intent_badge_ar("price")
    assert "التوصيل" in recovery_reply_intent_badge_ar("delivery")
    assert "الشراء" in recovery_reply_intent_badge_ar("ready_to_buy")
