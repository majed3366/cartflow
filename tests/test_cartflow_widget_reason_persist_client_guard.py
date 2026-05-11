# -*- coding: utf-8 -*-
"""
Regression: persistCartRecoveryReasonBackend must stay free of forward refs
that broke reason-button clicks (see git 0f5043f baseline vs c5b8a1d).
"""
from __future__ import annotations

from pathlib import Path


def _widget_js() -> str:
    root = Path(__file__).resolve().parent.parent
    return (root / "static" / "cartflow_widget.js").read_text(encoding="utf-8")


def test_persist_cart_recovery_reason_has_no_ls_phone_forward_ref() -> None:
    t = _widget_js()
    start = t.find("function persistCartRecoveryReasonBackend")
    assert start > 0
    end = t.find("function persistSessionAbandonReason", start)
    assert end > start
    block = t[start:end]
    assert "getCartflowStoredCustomerPhoneNorm" not in block
    assert "cartflowPayloadAttachStoredCustomerPhone" not in block


def test_persist_session_abandon_calls_backend_directly() -> None:
    t = _widget_js()
    start = t.find("function persistSessionAbandonReason")
    end = t.find("function clearCartRecoverySuppressed", start)
    fn = t[start:end]
    assert "persistCartRecoveryReasonBackend(reasonTag, customTextOptional)" in fn
    assert "CART_RECOVERY_REASON_PERSIST_EXCEPTION" not in fn
