# -*- coding: utf-8 -*-
"""Signed cookie sessions for merchant dashboard auth (HTML surfaces only)."""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from secrets import compare_digest
from typing import Optional

_MERCHANT_COOKIE = "cartflow_merchant_session"
_TTL_S = 14 * 24 * 3600
_PREAMBLE = b"cartflow-merchant-v1|"


def merchant_cookie_name() -> str:
    return _MERCHANT_COOKIE


def _signing_secret() -> bytes:
    return (
        os.getenv("SECRET_KEY") or "dev-only-change-in-production"
    ).strip().encode("utf-8")


def issue_merchant_session_cookie_value(merchant_user_id: int) -> str:
    exp = int(time.time()) + _TTL_S
    mid = int(merchant_user_id)
    payload = _PREAMBLE + f"{mid}:{exp}".encode("ascii")
    sig = hmac.new(_signing_secret(), payload, hashlib.sha256).hexdigest()
    return f"{mid}:{exp}:{sig}"


def parse_merchant_session_cookie_value(raw: str | None) -> Optional[int]:
    if not raw or raw.count(":") != 2:
        return None
    mid_s, exp_s, sig = raw.split(":", 2)
    try:
        mid = int(mid_s)
        exp = int(exp_s)
    except ValueError:
        return None
    if exp < int(time.time()) or mid <= 0:
        return None
    payload = _PREAMBLE + f"{mid}:{exp}".encode("ascii")
    expected = hmac.new(_signing_secret(), payload, hashlib.sha256).hexdigest()
    if not compare_digest(sig.encode("ascii"), expected.encode("ascii")):
        return None
    return mid


def merchant_session_cookie_valid(raw: str | None) -> bool:
    return parse_merchant_session_cookie_value(raw) is not None


__all__ = [
    "issue_merchant_session_cookie_value",
    "merchant_cookie_name",
    "merchant_session_cookie_valid",
    "parse_merchant_session_cookie_value",
]
