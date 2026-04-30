# -*- coding: utf-8 -*-
"""قواعد ‎_resolve_cartflow_recovery_phone‎ — متجر ‎demo‎ مقابل الإنتاج والمصادر الموثّقة."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from main import (
    _assert_forbidden_stale_recovery_phone,
    _cartflow_demo_test_phone,
    _resolve_cartflow_recovery_phone,
)


def test_demo_missing_phone_demo_config(monkeypatch) -> None:
    monkeypatch.setenv("CARTFLOW_DEMO_TEST_PHONE", "966579706669")
    phone, src, ok = _resolve_cartflow_recovery_phone(
        store_slug="demo",
        session_id="s1",
        cart_id=None,
        store_obj=None,
        abandon_event_phone=None,
        recovery_key="demo:s1",
        reason_row=None,
    )
    assert src == "demo_config"
    assert phone == "966579706669"
    assert ok is True


def test_non_demo_no_phone_not_allowed(monkeypatch) -> None:
    monkeypatch.setenv("CARTFLOW_DEMO_TEST_PHONE", "966579706669")
    phone, src, ok = _resolve_cartflow_recovery_phone(
        store_slug="live-store",
        session_id="s2",
        cart_id=None,
        store_obj=None,
        abandon_event_phone=None,
        recovery_key="live-store:s2",
        reason_row=None,
    )
    assert phone is None
    assert src == "none"
    assert ok is False


def test_abandoned_cart_verified_non_demo(monkeypatch) -> None:
    monkeypatch.setenv("CARTFLOW_DEMO_TEST_PHONE", "966579706669")
    phone, src, ok = _resolve_cartflow_recovery_phone(
        store_slug="acme",
        session_id="s3",
        cart_id="c1",
        store_obj=None,
        abandon_event_phone="9665111222333",
        recovery_key="acme:s3",
        reason_row=None,
    )
    assert src == "abandoned_cart"
    assert phone == "9665111222333"
    assert ok is True


def test_non_demo_blocks_demo_test_phone_even_from_abandon(monkeypatch) -> None:
    monkeypatch.setenv("CARTFLOW_DEMO_TEST_PHONE", "966579706669")
    phone, src, ok = _resolve_cartflow_recovery_phone(
        store_slug="acme",
        session_id="s4",
        cart_id=None,
        store_obj=None,
        abandon_event_phone="966579706669",
        recovery_key="acme:s4",
        reason_row=None,
    )
    assert src == "abandoned_cart"
    assert phone == "966579706669"
    assert ok is False


def test_customer_profile_from_reason_row(monkeypatch) -> None:
    monkeypatch.setenv("CARTFLOW_DEMO_TEST_PHONE", "966579706669")
    row = SimpleNamespace(customer_phone="9665000111222")
    phone, src, ok = _resolve_cartflow_recovery_phone(
        store_slug="acme",
        session_id="s5",
        cart_id=None,
        store_obj=None,
        abandon_event_phone=None,
        recovery_key="acme:s5",
        reason_row=row,
    )
    assert src == "customer_profile"
    assert phone == "9665000111222"
    assert ok is True


def test_forbidden_stale_literal_raises() -> None:
    with pytest.raises(RuntimeError, match="Forbidden stale test phone"):
        _assert_forbidden_stale_recovery_phone("966501234567")


def test_cartflow_demo_phone_default(monkeypatch) -> None:
    monkeypatch.delenv("CARTFLOW_DEMO_TEST_PHONE", raising=False)
    assert _cartflow_demo_test_phone() == "966579706669"
