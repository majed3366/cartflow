# -*- coding: utf-8 -*-
"""
Verify CartFlow reads Store.recovery_delay_minutes (not a fixed delay).

Manual QA (demo deploy): set stores.recovery_delay_minutes = 1 for the demo row,
restart app, fresh session → cart → shipping reason → wait ~1 min → WhatsApp path.

Automated checks below: log shape + delay gate math only (no widget / WA changes).
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from services.whatsapp_send import _recovery_delay_minutes_from_store, should_send_whatsapp


def _demo_store_recovery_delay_one_minute():
    """Mirrors DB: recovery_delay_minutes=1, store key demo (zid_store_id)."""
    return SimpleNamespace(
        recovery_delay_minutes=1,
        zid_store_id="demo",
        recovery_delay_unit="minutes",
        recovery_delay=99,
        recovery_attempts=1,
    )


def test_delay_config_logs_demo_and_one_minute() -> None:
    store = _demo_store_recovery_delay_one_minute()
    buf = io.StringIO()
    with redirect_stdout(buf):
        mins = _recovery_delay_minutes_from_store(store)
    assert mins == 1
    out = buf.getvalue()
    assert "[DELAY CONFIG]" in out
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    store_line = next((ln for ln in lines if ln.startswith("store=")), "")
    delay_line = next((ln for ln in lines if ln.startswith("delay_minutes=")), "")
    assert "demo" in store_line
    assert "1" in delay_line.split("=")[-1].strip()


def test_should_send_after_one_full_minute_when_config_is_one() -> None:
    """No purchase / no return: gate opens once now >= last_activity + 1 minute."""
    store = _demo_store_recovery_delay_one_minute()
    now = datetime.now(timezone.utc)
    last_before = now - timedelta(seconds=59)
    last_after = now - timedelta(minutes=2)

    assert (
        should_send_whatsapp(
            last_before,
            user_returned_to_site=False,
            now=now,
            store=store,
            sent_count=0,
        )
        is False
    )
    assert (
        should_send_whatsapp(
            last_after,
            user_returned_to_site=False,
            now=now,
            store=store,
            sent_count=0,
        )
        is True
    )


@pytest.mark.parametrize(
    "minutes_cfg,expect_minutes",
    [(1, 1), (5, 5)],
)
def test_recovery_delay_minutes_overrides_config_layer(
    minutes_cfg: int, expect_minutes: int
) -> None:
    """Column wins over config_system demo default (2) when set."""
    store = SimpleNamespace(
        recovery_delay_minutes=minutes_cfg,
        zid_store_id="demo",
        recovery_delay_unit="minutes",
        recovery_delay=2,
        recovery_attempts=1,
    )
    assert _recovery_delay_minutes_from_store(store) == expect_minutes
