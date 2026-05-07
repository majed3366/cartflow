# -*- coding: utf-8 -*-
"""قواعد ‎_resolve_cartflow_recovery_phone‎ — رقم عميل فقط دون خط التاجر."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from datetime import datetime, timezone

from extensions import db
from main import (
    _assert_forbidden_stale_recovery_phone,
    _cartflow_demo_test_phone,
    _resolve_cartflow_recovery_phone,
)
from models import CartRecoveryLog


def test_demo_missing_phone_has_no_demo_fallback(monkeypatch) -> None:
    monkeypatch.setenv("CARTFLOW_DEMO_TEST_PHONE", "966579706669")
    phone, src, ok = _resolve_cartflow_recovery_phone(
        store_slug="demo",
        session_id="demo-isolated-s1-phonetest",
        cart_id=None,
        store_obj=None,
        abandon_event_phone=None,
        recovery_key="demo:demo-isolated-s1-phonetest",
        reason_row=None,
    )
    assert src == "none"
    assert phone is None
    assert ok is False


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


def test_non_demo_blocks_merchant_line_even_from_abandon(monkeypatch) -> None:
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
    assert src == "none"
    assert phone is None
    assert ok is False


def test_store_whatsapp_blocks_matching_customer_candidate(monkeypatch) -> None:
    monkeypatch.delenv("CARTFLOW_DEMO_TEST_PHONE", raising=False)
    monkeypatch.delenv("DEFAULT_MERCHANT_PHONE", raising=False)
    monkeypatch.delenv("TWILIO_WHATSAPP_FROM", raising=False)
    st = SimpleNamespace(
        store_whatsapp_number="+966579706669",
        whatsapp_support_url=None,
    )
    phone, src, ok = _resolve_cartflow_recovery_phone(
        store_slug="acme",
        session_id="s4b",
        cart_id=None,
        store_obj=st,
        abandon_event_phone="966579706669",
        recovery_key="acme:s4b",
        reason_row=None,
    )
    assert phone is None
    assert src == "none"
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


def test_non_demo_resolves_phone_from_prior_successful_recovery_log(
    monkeypatch,
) -> None:
    """المحاولة الثانية ترجع رقم آخر إرسال ناجح من ‎CartRecoveryLog‎."""
    monkeypatch.setenv("CARTFLOW_DEMO_TEST_PHONE", "966579706669")
    sid = "ext-recovery-log-phone-1"
    db.create_all()
    row = CartRecoveryLog(
        store_slug="acme",
        session_id=sid,
        cart_id="z-ext-1",
        phone="9665000111222",
        message="first",
        status="mock_sent",
        created_at=datetime.now(timezone.utc),
        sent_at=datetime.now(timezone.utc),
    )
    db.session.add(row)
    db.session.commit()
    try:
        phone, src, ok = _resolve_cartflow_recovery_phone(
            store_slug="acme",
            session_id=sid,
            cart_id="z-ext-1",
            store_obj=None,
            abandon_event_phone=None,
            recovery_key=f"acme:{sid}",
            reason_row=None,
        )
        assert src == "cart_recovery_log_sent"
        assert phone == "9665000111222"
        assert ok is True
    finally:
        db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.session_id == sid
        ).delete(synchronize_session=False)
        db.session.commit()
