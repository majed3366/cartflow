# -*- coding: utf-8 -*-
"""مسار ‎get_recovery_phone‎ — جلسة، احتياطي تطوير، أو إنتاج عبر ‎WHATSAPP_RECOVERY_TO_PHONE‎."""
from __future__ import annotations

import pytest

from main import (
    DEV_TEST_PHONE,
    _assert_recovery_phone_not_stale_forbidden,
    get_recovery_phone,
)


def test_session_phone_used(monkeypatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("WHATSAPP_RECOVERY_TO_PHONE", raising=False)
    p = get_recovery_phone("sid-1", "9665111222333")
    assert p == "9665111222333"


def test_dev_fallback_when_no_session_phone(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("WHATSAPP_RECOVERY_TO_PHONE", raising=False)
    p = get_recovery_phone("sid-2", None)
    assert p == DEV_TEST_PHONE


def test_dev_short_env_dev(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.delenv("WHATSAPP_RECOVERY_TO_PHONE", raising=False)
    p = get_recovery_phone("sid-3", None)
    assert p == DEV_TEST_PHONE


def test_prod_no_session_requires_env_override(monkeypatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("WHATSAPP_RECOVERY_TO_PHONE", raising=False)
    monkeypatch.delenv("ENABLE_DEV_PHONE_FALLBACK", raising=False)
    assert get_recovery_phone("sid-4", None) is None


def test_enable_dev_phone_fallback_flag_without_env(monkeypatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("WHATSAPP_RECOVERY_TO_PHONE", raising=False)
    monkeypatch.setenv("ENABLE_DEV_PHONE_FALLBACK", "true")
    assert get_recovery_phone("sid-railway", None) == DEV_TEST_PHONE


def test_enable_dev_phone_fallback_flag_false(monkeypatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("WHATSAPP_RECOVERY_TO_PHONE", raising=False)
    monkeypatch.setenv("ENABLE_DEV_PHONE_FALLBACK", "false")
    assert get_recovery_phone("sid-flag-off", None) is None


def test_prod_env_override(monkeypatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("WHATSAPP_RECOVERY_TO_PHONE", "9665999888777")
    assert get_recovery_phone("sid-5", None) == "9665999888777"


def test_forbidden_literal_raises() -> None:
    with pytest.raises(RuntimeError, match="STALE PHONE BUG"):
        _assert_recovery_phone_not_stale_forbidden("966501234567")


def test_forbidden_local_form_raises() -> None:
    with pytest.raises(RuntimeError, match="STALE PHONE BUG"):
        _assert_recovery_phone_not_stale_forbidden("0501234567")
