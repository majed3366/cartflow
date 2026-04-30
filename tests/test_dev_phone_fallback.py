# -*- coding: utf-8 -*-
"""سلوك ‎_resolve_recovery_session_phone‎ — احتياطي رقم التطوير فقط."""
from __future__ import annotations

from types import SimpleNamespace

from main import _resolve_recovery_session_phone


def test_real_phone_from_cart_payload_skips_dev_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "development")
    phone, src = _resolve_recovery_session_phone(
        recovery_key="test-key",
        reason_row=None,
        abandon_event_phone="9665111222333",
    )
    assert phone == "9665111222333"
    assert src == "cart_event_payload"


def test_dev_env_uses_test_fallback_when_no_session_phone(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "development")
    phone, src = _resolve_recovery_session_phone(
        recovery_key="test-key",
        reason_row=None,
        abandon_event_phone=None,
    )
    assert phone == "966579706669"
    assert src == "dev_fallback"


def test_dev_short_env_dev(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "dev")
    phone, src = _resolve_recovery_session_phone(
        recovery_key="test-key",
        reason_row=None,
        abandon_event_phone=None,
    )
    assert phone == "966579706669"
    assert src == "dev_fallback"


def test_db_reason_phone_skips_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "development")
    row = SimpleNamespace(customer_phone="9665000111222")
    phone, src = _resolve_recovery_session_phone(
        recovery_key="test-key",
        reason_row=row,
        abandon_event_phone=None,
    )
    assert phone == "9665000111222"
    assert src == "db_reason_row"


def test_unset_env_no_dev_fallback(monkeypatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    phone, src = _resolve_recovery_session_phone(
        recovery_key="test-key",
        reason_row=None,
        abandon_event_phone=None,
    )
    assert phone == "966501234567"
    assert src == "default_destination"
