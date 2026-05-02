# -*- coding: utf-8 -*-
from __future__ import annotations

import json

from services.recovery_multi_message import delay_to_seconds, multi_message_slots_for_abandon
from services.store_reason_templates import apply_reason_templates_from_body, parse_reason_templates_column


class _Row:
    reason_templates_json = None


def test_delay_to_seconds_minute_and_hour() -> None:
    assert delay_to_seconds(2, "minute") == 120.0
    assert delay_to_seconds(2, "hour") == 7200.0


def test_multi_slots_none_when_single_message_mode() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {
                "price": {
                    "enabled": True,
                    "message": "واحدة",
                    "message_count": 1,
                    "messages": [{"delay": 2, "unit": "minute", "text": "أ"}],
                }
            }
        )

    assert multi_message_slots_for_abandon("price_high", _S()) is None


def test_multi_slots_none_when_messages_missing() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {"price": {"enabled": True, "message": "x", "message_count": 2}}
        )

    assert multi_message_slots_for_abandon("price_high", _S()) is None


def test_multi_slots_returns_two_with_defaults_padding() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {
                "price": {
                    "enabled": True,
                    "message": "الأساسية",
                    "message_count": 2,
                    "messages": [{"delay": 3, "unit": "minute", "text": ""}],
                }
            }
        )

    slots = multi_message_slots_for_abandon("price_high", _S())
    assert slots is not None
    assert len(slots) == 2
    assert slots[0]["index"] == 1
    assert slots[1]["index"] == 2
    assert slots[0]["delay_seconds"] == 180.0
    assert slots[1]["unit_display"] == "hour"


def test_parse_and_apply_preserves_messages() -> None:
    row = _Row()
    body = {
        "reason_templates": {
            "shipping": {
                "enabled": True,
                "message": "أولى",
                "message_count": 2,
                "messages": [
                    {"delay": 5, "unit": "minute", "text": "م1"},
                    {"delay": 1, "unit": "hour", "text": "م2"},
                ],
            }
        }
    }
    apply_reason_templates_from_body(row, body)
    parsed = parse_reason_templates_column(row.reason_templates_json)
    ship = parsed["shipping"]
    assert ship["message_count"] == 2
    assert len(ship["messages"]) == 2
    assert ship["messages"][1]["unit"] == "hour"
