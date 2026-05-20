# -*- coding: utf-8 -*-
"""Scheduling and final gate must share one effective_delay_seconds."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from services.recovery_delay_unified import (
    effective_delay_for_gate,
    timing_from_recovery_context,
)
from services.recovery_multi_message import resolve_recovery_schedule_timing
from services.whatsapp_send import should_send_whatsapp


class _StoreOther1m:
    reason_templates_json = json.dumps(
        {
            "other": {
                "enabled": True,
                "message": "x",
                "message_count": 1,
                "messages": [{"delay": 1, "unit": "minute", "text": "x"}],
            }
        }
    )
    recovery_delay = 2
    recovery_delay_unit = "minutes"
    recovery_attempts = 3
    whatsapp_recovery_enabled = True


class _StoreOther2h:
    reason_templates_json = json.dumps(
        {
            "other": {
                "enabled": True,
                "message": "x",
                "message_count": 1,
                "messages": [{"delay": 2, "unit": "hour", "text": "x"}],
            }
        }
    )
    recovery_delay = 2
    recovery_delay_unit = "minutes"
    recovery_attempts = 3
    whatsapp_recovery_enabled = True


def test_timing_from_context_roundtrip() -> None:
    timing = {
        "effective_delay_seconds": 60.0,
        "source": "reason_templates.messages",
        "reason_tag": "other",
        "stage": 1,
    }
    ctx = {"schedule_timing": timing}
    got = timing_from_recovery_context(ctx)
    assert got is not None
    assert got["effective_delay_seconds"] == 60.0
    assert got["source"] == "reason_templates.messages"


def test_gate_uses_context_not_store_legacy_minutes() -> None:
    """Template 1m: after 90s idle, store legacy 2m would block; effective 60s allows."""
    now = datetime.now(timezone.utc)
    last = now - timedelta(seconds=90)
    timing = {
        "effective_delay_seconds": 60.0,
        "source": "reason_templates.messages",
        "reason_tag": "other",
        "stage": 1,
    }
    assert should_send_whatsapp(
        last,
        now=now,
        store=_StoreOther1m(),
        sent_count=0,
        effective_delay_seconds=60.0,
        delay_source=timing["source"],
    )
    assert not should_send_whatsapp(
        last,
        now=now,
        store=_StoreOther1m(),
        sent_count=0,
        effective_delay_seconds=None,
    )


def test_resolve_other_one_minute_matches_gate() -> None:
    timing = resolve_recovery_schedule_timing("other", _StoreOther1m(), stage_index=0)
    assert timing["effective_delay_seconds"] == 60.0
    assert timing["source"] == "reason_templates.messages"
    assert timing.get("fallback_reason") is None

    ctx = {"schedule_timing": timing}
    gate = effective_delay_for_gate(
        recovery_context=ctx,
        delay_seconds_scheduled=60.0,
        multi_slot_index=None,
        step_num=1,
        reason_tag="other",
        store_obj=_StoreOther1m(),
        recovery_key="demo:s1",
        resolve_timing_fn=resolve_recovery_schedule_timing,
    )
    assert gate["effective_delay_seconds"] == 60.0
    assert gate["source"] == "reason_templates.messages"


def test_resolve_other_two_hours_blocks_early_send() -> None:
    timing = resolve_recovery_schedule_timing("other", _StoreOther2h(), stage_index=0)
    assert timing["effective_delay_seconds"] == 7200.0

    now = datetime.now(timezone.utc)
    last = now - timedelta(seconds=3600)
    assert not should_send_whatsapp(
        last,
        now=now,
        store=_StoreOther2h(),
        effective_delay_seconds=7200.0,
        delay_source=timing["source"],
    )

    last_ok = now - timedelta(seconds=7300)
    assert should_send_whatsapp(
        last_ok,
        now=now,
        store=_StoreOther2h(),
        effective_delay_seconds=7200.0,
        delay_source=timing["source"],
    )
