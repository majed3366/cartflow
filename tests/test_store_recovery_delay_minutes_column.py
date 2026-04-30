# -*- coding: utf-8 -*-
"""‎Store.recovery_delay_minutes‎ يفسّر تأخير الاسترجاع بالدقائق عند التعيين فقط."""
from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from services.whatsapp_send import _min_quiet_from_store_settings


def test_recovery_delay_minutes_override_when_set() -> None:
    store = SimpleNamespace(
        recovery_delay_minutes=7,
        recovery_delay_unit="minutes",
        recovery_delay=99,
        zid_store_id="demo",
        recovery_attempts=1,
    )
    assert _min_quiet_from_store_settings(store) == timedelta(minutes=7)


def test_recovery_delay_minutes_zero_falls_back_to_two() -> None:
    store = SimpleNamespace(
        recovery_delay_minutes=0,
        recovery_delay_unit="minutes",
        zid_store_id="demo",
        recovery_attempts=1,
    )
    assert _min_quiet_from_store_settings(store) == timedelta(minutes=2)


def test_recovery_delay_minutes_null_uses_config_layer() -> None:
    """‎NULL‎ على العمود يُبقي مسار ‎get_cartflow_config‎ كما كان."""
    store = SimpleNamespace(
        recovery_delay_minutes=None,
        recovery_delay_unit="minutes",
        recovery_delay=2,
        zid_store_id="demo",
        recovery_attempts=1,
    )
    assert _min_quiet_from_store_settings(store) == timedelta(minutes=2)
