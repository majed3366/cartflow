# -*- coding: utf-8 -*-
from __future__ import annotations

import json

from services.recovery_multi_message import (
    delay_to_seconds,
    multi_message_slots_for_abandon,
    resolve_configured_message_count,
    resolve_recovery_schedule_timing,
)
from services.store_reason_templates import apply_reason_templates_from_body, parse_reason_templates_column


class _Row:
    reason_templates_json = None


def test_delay_to_seconds_minute_and_hour() -> None:
    assert delay_to_seconds(2, "minute") == 120.0
    assert delay_to_seconds(2, "hour") == 7200.0


def test_resolve_schedule_timing_price_one_minute() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {
                "price": {
                    "enabled": True,
                    "message": "نص",
                    "message_count": 1,
                    "messages": [{"delay": 1, "unit": "minute", "text": "نص"}],
                }
            }
        )

    t = resolve_recovery_schedule_timing("price_high", _S(), stage_index=0)
    assert t["effective_delay_seconds"] == 60.0
    assert t["source"] == "reason_templates.messages"
    assert multi_message_slots_for_abandon("price_high", _S()) is None


def test_resolve_schedule_timing_other_two_hours() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {
                "other": {
                    "enabled": True,
                    "message": "نص",
                    "message_count": 1,
                    "messages": [{"delay": 2, "unit": "hour", "text": "نص"}],
                }
            }
        )

    t = resolve_recovery_schedule_timing("other", _S(), stage_index=0)
    assert t["effective_delay_seconds"] == 7200.0
    assert t["source"] == "reason_templates.messages"


def test_resolve_schedule_timing_warranty_five_minutes() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {
                "warranty": {
                    "enabled": True,
                    "message": "نص",
                    "message_count": 1,
                    "messages": [{"delay": 5, "unit": "minute", "text": "نص"}],
                }
            }
        )

    t = resolve_recovery_schedule_timing("warranty", _S(), stage_index=0)
    assert t["effective_delay_seconds"] == 300.0
    assert t["source"] == "reason_templates.messages"


def test_resolve_schedule_timing_delay_poll_paths() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {
                "other": {
                    "enabled": True,
                    "message": "نص",
                    "message_count": 1,
                    "messages": [{"delay": 2, "unit": "hour", "text": "نص"}],
                },
                "price": {
                    "enabled": True,
                    "message": "نص",
                    "message_count": 1,
                    "messages": [{"delay": 1, "unit": "minute", "text": "نص"}],
                },
            }
        )

    other = resolve_recovery_schedule_timing(
        "other", _S(), path="delay_poll_dispatch"
    )
    assert other["effective_delay_seconds"] == 7200.0
    assert other["source"] == "reason_templates.messages"

    price = resolve_recovery_schedule_timing(
        "price_high", _S(), path="delay_poll_arm"
    )
    assert price["effective_delay_seconds"] == 60.0


def test_resolve_schedule_timing_legacy_when_no_template() -> None:
    class _S:
        reason_templates_json = None

    t = resolve_recovery_schedule_timing("other", _S(), stage_index=0)
    assert t["effective_delay_seconds"] == 240.0
    assert t["source"] == "legacy_recovery_delay"
    assert t["fallback_reason"] == "no_template_entry"


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


def test_multi_slots_when_message_count_stale_but_two_messages() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {
                "price": {
                    "enabled": True,
                    "message": "أساسية",
                    "message_count": 1,
                    "messages": [
                        {"delay": 1, "unit": "minute", "text": "أولى"},
                        {"delay": 2, "unit": "minute", "text": "ثانية"},
                    ],
                }
            }
        )

    slots = multi_message_slots_for_abandon("price_high", _S())
    assert slots is not None
    assert len(slots) == 2
    assert slots[0]["index"] == 1
    assert slots[1]["index"] == 2


def test_multi_slots_when_messages_missing_but_message_count_two() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {"price": {"enabled": True, "message": "x", "message_count": 2}}
        )

    slots = multi_message_slots_for_abandon("price_high", _S())
    assert slots is not None
    assert len(slots) == 2


def test_multi_slots_from_guided_attempts_without_messages_array() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {
                "price": {
                    "enabled": True,
                    "message": "أساسية",
                    "message_count": 2,
                    "guided_attempts": {"1": "أولى", "2": "ثانية"},
                }
            }
        )

    slots = multi_message_slots_for_abandon("price", _S())
    assert slots is not None
    assert len(slots) == 2
    assert "أولى" in slots[0]["text"]
    assert "ثانية" in slots[1]["text"]


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


def test_guided_attempts_parse_and_apply() -> None:
    row = _Row()
    body = {
        "reason_templates": {
            "price": {
                "enabled": True,
                "message": "",
                "message_count": 1,
                "guided_attempts": {"1": "خط مخصص", "2": "", 3: "ثالثة"},
            }
        }
    }
    apply_reason_templates_from_body(row, body)
    parsed = parse_reason_templates_column(row.reason_templates_json)
    ga = parsed["price"].get("guided_attempts") or {}
    assert ga.get("1") == "خط مخصص"
    assert ga.get("3") == "ثالثة"
    assert "2" not in ga


def test_parse_widget_reason_label_ar_roundtrip() -> None:
    row = _Row()
    row.reason_templates_json = json.dumps(
        {
            "price": {
                "enabled": True,
                "message": "نص استرجاع طويل للواتساب",
                "widget_reason_label_ar": "السعر",
            }
        }
    )
    p = parse_reason_templates_column(row.reason_templates_json)
    assert p["price"]["message"] == "نص استرجاع طويل للواتساب"
    assert p["price"]["widget_reason_label_ar"] == "السعر"


def test_resolve_configured_message_count_prefers_context_then_templates() -> None:
    class _S:
        reason_templates_json = json.dumps(
            {
                "price": {
                    "enabled": True,
                    "message": "أساسية",
                    "message_count": 2,
                    "messages": [
                        {"delay": 1, "unit": "minute", "text": "أولى"},
                        {"delay": 1, "unit": "minute", "text": "ثانية"},
                    ],
                }
            }
        )
        recovery_attempts = 1

    n_tpl, src_tpl = resolve_configured_message_count("price", _S())
    assert n_tpl == 2
    assert src_tpl == "reason_templates.multi"

    n_ctx, src_ctx = resolve_configured_message_count(
        "shipping",
        _S(),
        recovery_context={
            "configured_message_count": 3,
            "configured_message_count_source": "reason_templates.multi",
        },
    )
    assert n_ctx == 3
    assert src_ctx == "recovery_context"

    n_stale, src_stale = resolve_configured_message_count(
        "price",
        _S(),
        recovery_context={
            "configured_message_count": 1,
            "configured_message_count_source": "store.recovery_attempts",
        },
    )
    assert n_stale == 2
    assert src_stale == "reason_templates.multi"


def test_apply_widget_label_only_preserves_recovery_message() -> None:
    row = _Row()
    long_recovery = "RECOVERY_BODY_" * 20
    row.reason_templates_json = json.dumps(
        {"price": {"enabled": True, "message": long_recovery, "message_count": 1}}
    )
    apply_reason_templates_from_body(
        row,
        {
            "reason_templates": {
                "price": {
                    "enabled": True,
                    "widget_reason_label_ar": "السعر للعميل",
                }
            }
        },
    )
    p = parse_reason_templates_column(row.reason_templates_json)
    assert p["price"]["message"] == long_recovery
    assert p["price"]["widget_reason_label_ar"] == "السعر للعميل"
