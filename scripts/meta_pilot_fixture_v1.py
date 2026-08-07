# -*- coding: utf-8 -*-
"""
Meta Pilot Fixture V1 — canonical phone persistence helpers.

Uses customer_phone on POST /api/cartflow/reason (production path).
Does not rely on cf_test_phone for durable phone persistence.
Does not write AbandonedCart.customer_phone directly.
"""
from __future__ import annotations

from typing import Any

PILOT_PHONE_E164 = "+966546518011"
PILOT_PHONE_DIGITS = "966546518011"
PILOT_STORE = "demo"
PILOT_REASON = "other"
PILOT_CUSTOM_TEXT = "سبب اخر"
PILOT_CHECKOUT_URL = "https://smartreplyai.net/demo/store/checkout"


def build_cartflow_reason_payload(
    *,
    session_id: str,
    cart_id: str,
    store_slug: str = PILOT_STORE,
    customer_phone: str = PILOT_PHONE_E164,
    custom_text: str = PILOT_CUSTOM_TEXT,
    checkout_url: str = PILOT_CHECKOUT_URL,
) -> dict[str, Any]:
    """
    Canonical reason body for Meta pilot / real widget phone capture.

    Must include customer_phone — /api/cartflow/reason ignores cf_test_phone.
    """
    return {
        "store": store_slug,
        "store_slug": store_slug,
        "session_id": session_id,
        "cart_id": cart_id,
        "reason": PILOT_REASON,
        "custom_text": custom_text,
        "customer_phone": customer_phone,
        "checkout_url": checkout_url,
        "cart_url": checkout_url,
    }


def build_abandon_payload(
    *,
    session_id: str,
    cart_id: str,
    store_slug: str = PILOT_STORE,
    checkout_url: str = PILOT_CHECKOUT_URL,
) -> dict[str, Any]:
    """Abandon without phone — durable phone comes from reason capture."""
    return {
        "event": "cart_abandoned",
        "store": store_slug,
        "store_slug": store_slug,
        "session_id": session_id,
        "cart_id": cart_id,
        "cart_value": 189.0,
        "currency": "SAR",
        "checkout_url": checkout_url,
        "cart_url": checkout_url,
        "items": [{"name": "Meta Pilot Product", "price": 189.0, "qty": 1}],
    }


def mask_phone_digits(raw: str | None) -> str | None:
    digits = "".join(c for c in str(raw or "") if c.isdigit())
    if not digits:
        return None
    if len(digits) <= 4:
        return "****"
    return f"{digits[:3]}…{digits[-2:]}"


def evaluate_phone_persistence_ready(
    *,
    recovery_key: str,
    expected_digits: str = PILOT_PHONE_DIGITS,
    crr_phone: str | None,
    ac_phone: str | None,
    schedule_id: int | None,
    schedule_recovery_key: str | None = None,
) -> dict[str, Any]:
    """Sanitized readiness from durable DB values (not process memory)."""
    crr_digits = "".join(c for c in str(crr_phone or "") if c.isdigit())
    ac_digits = "".join(c for c in str(ac_phone or "") if c.isdigit())
    rk_ok = bool(recovery_key) and (
        schedule_recovery_key is None or schedule_recovery_key == recovery_key
    )
    ready = bool(
        rk_ok
        and schedule_id
        and crr_digits == expected_digits
        and ac_digits == expected_digits
    )
    return {
        "recovery_key": recovery_key,
        "schedule_id": schedule_id,
        "crr_phone_masked": mask_phone_digits(crr_phone),
        "abandoned_cart_phone_masked": mask_phone_digits(ac_phone),
        "phone_normalized_ok": crr_digits == expected_digits and ac_digits == expected_digits,
        "identity_linked": rk_ok,
        "phone_persistence_ready": ready,
    }
