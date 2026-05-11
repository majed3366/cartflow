# -*- coding: utf-8 -*-
"""Regression: widget reason persist must not reference forward-only helpers unsafely."""
from __future__ import annotations

from pathlib import Path


def _widget_js() -> str:
    root = Path(__file__).resolve().parent.parent
    return (root / "static" / "cartflow_widget.js").read_text(encoding="utf-8")


def test_cartflow_payload_attach_stored_phone_helper_present() -> None:
    t = _widget_js()
    assert "function cartflowPayloadAttachStoredCustomerPhone(payload)" in t
    assert "cartflowPayloadAttachStoredCustomerPhone(payload)" in t


def test_persist_session_abandon_reason_guards_backend_persist() -> None:
    t = _widget_js()
    assert "CART_RECOVERY_REASON_PERSIST_EXCEPTION" in t
    start = t.find("function persistSessionAbandonReason")
    assert start > 0
    end = t.find("function clearCartRecoverySuppressed", start)
    assert end > start
    fn = t[start:end]
    assert "persistCartRecoveryReasonBackend(reasonTag, customTextOptional)" in fn
    assert "try" in fn and "CART_RECOVERY_REASON_PERSIST_EXCEPTION" in fn


def test_no_direct_get_cartflow_stored_in_persist_cart_recovery_block() -> None:
    """Avoid calling getCartflowStoredCustomerPhoneNorm from persistCartRecoveryReasonBackend (hoist/order)."""
    t = _widget_js()
    start = t.find("function persistCartRecoveryReasonBackend")
    assert start > 0
    end = t.find("function persistSessionAbandonReason", start)
    assert end > start
    block = t[start:end]
    assert "getCartflowStoredCustomerPhoneNorm" not in block
