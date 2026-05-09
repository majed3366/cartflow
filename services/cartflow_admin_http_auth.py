# -*- coding: utf-8 -*-
"""
Signed cookie gate for CartFlow admin HTML surfaces only.

Does not alter recovery, merchant dashboards, or operational summary math.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from secrets import compare_digest

_ADMIN_COOKIE = "cartflow_admin_session"
_TTL_S = 8 * 3600
_PREAMBLE = b"cartflow-admin-v1|"


def admin_cookie_name() -> str:
    return _ADMIN_COOKIE


def admin_password_configured() -> bool:
    return bool((os.getenv("CARTFLOW_ADMIN_PASSWORD") or "").strip())


def verify_admin_password(attempt: str) -> bool:
    expected = (os.getenv("CARTFLOW_ADMIN_PASSWORD") or "").strip()
    if not expected:
        return False
    return compare_digest(
        (attempt or "").strip().encode("utf-8"),
        expected.encode("utf-8"),
    )


def _signing_secret() -> bytes:
    return (
        os.getenv("SECRET_KEY") or "dev-only-change-in-production"
    ).strip().encode("utf-8")


def issue_admin_session_cookie_value() -> str:
    exp = int(time.time()) + _TTL_S
    payload = _PREAMBLE + str(exp).encode("ascii")
    sig = hmac.new(_signing_secret(), payload, hashlib.sha256).hexdigest()
    return f"{exp}:{sig}"


def admin_session_cookie_valid(raw: str | None) -> bool:
    if not raw or ":" not in raw:
        return False
    exp_s, sig = raw.rsplit(":", 1)
    try:
        exp = int(exp_s)
    except ValueError:
        return False
    if exp < int(time.time()):
        return False
    payload = _PREAMBLE + str(exp).encode("ascii")
    expected = hmac.new(_signing_secret(), payload, hashlib.sha256).hexdigest()
    return compare_digest(sig.encode("ascii"), expected.encode("ascii"))


__all__ = [
    "admin_cookie_name",
    "admin_password_configured",
    "admin_session_cookie_valid",
    "issue_admin_session_cookie_value",
    "verify_admin_password",
]
